"""
Entitlement — the single source of truth for "may this user do this?".

Replaces the three copy-pasted `status != 'active'` checks in supabase_routes
and the dead, fail-open `require_active_subscription` that used to live in
subscription_service.py (retired in Task 13b).

Every decorator here fails CLOSED. The old one read `g.user_id`, which
middleware/auth.py never sets, so it passed every request through.
"""

import uuid
from functools import wraps
from datetime import datetime, timezone, timedelta

from flask import jsonify

from db.supabase_client import get_supabase_admin
from middleware.auth import get_user_id

TIER_1 = 'tier_1_pay_per_breakdown'
TIER_2 = 'tier_2_annual_team'

# Using fixed-day advances rather than `datetime.replace(year=year + 1)`,
# which raises ValueError when `now` is 29 Feb and next year is not a leap
# year.
ONE_YEAR = timedelta(days=365)
ONE_MONTH = timedelta(days=30)
THREE_MONTHS = timedelta(days=90)
SIX_MONTHS = timedelta(days=180)

# Longer cadences are a discounted prepay of the same license, not a
# separate product.
LICENSE_TERMS = {
    'monthly': (ONE_MONTH, 1850.00),
    '3month': (THREE_MONTHS, 5500.00),
    '6month': (SIX_MONTHS, 9500.00),
    'annual': (ONE_YEAR, 18500.00),
}

# Seats bundled free with each cadence. Any seat beyond this count is a
# paid add-on (see grant_seats) at a flat R250/month, no discount.
INCLUDED_SEATS = {
    'monthly': 0,
    '3month': 1,
    '6month': 2,
    'annual': 3,
}


class InsufficientCredits(Exception):
    """Tier 1 user tried to run a breakdown with no credits."""


def _fetch_profile(user_id: str):
    resp = get_supabase_admin().table('profiles').select(
        'subscription_plan, subscription_status, subscription_expires_at, '
        'subscription_billing_cycle, signup_plan'
    ).eq('id', user_id).limit(1).execute()
    return resp.data[0] if resp.data else None


def _fetch_balance(user_id: str) -> int:
    resp = get_supabase_admin().table('breakdown_credits').select(
        'delta'
    ).eq('user_id', user_id).execute()
    return sum(row['delta'] for row in (resp.data or []))


def _fetch_seats_paid(owner_id: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    resp = get_supabase_admin().table('account_seats').select(
        'seats_granted'
    ).eq('owner_id', owner_id).gt('term_expires_at', now).execute()
    return sum(row['seats_granted'] for row in (resp.data or []))


def _fetch_seats_used(owner_id: str) -> int:
    """
    Seats are billed per team MEMBER (per person), not per membership row
    or per invite. A pending invite reserves a seat immediately — this is
    what prevents overbooking: without it, several pending invites could
    each pass the seats_used < seats_paid check before any of them were
    accepted. Accepting an invite is a no-op for this count; the person
    just moves from the pending half of the tally to the accepted half.

    `script_members` is a per-(script, user) table, so the same person
    invited to three scripts must consume one seat, not three. Pending
    invites are keyed by email (the invitee has no user_id yet); accepted
    memberships are keyed by user_id — so a person pending on one script
    and already accepted on another (same owner) is deduped by matching
    the pending invite's email against `profiles.email` for the accepted
    user_ids. supabase-py has no count-distinct, so dedupe in Python.
    """
    admin = get_supabase_admin()
    now = datetime.now(timezone.utc).isoformat()

    members_resp = admin.table('script_members').select('user_id').eq(
        'invited_by', owner_id
    ).execute()
    accepted_ids = {row['user_id'] for row in (members_resp.data or [])}

    invites_resp = admin.table('script_invites').select('email').eq(
        'invited_by', owner_id
    ).eq('status', 'pending').gt('expires_at', now).execute()
    pending_emails = {
        row['email'].strip().lower()
        for row in (invites_resp.data or []) if row.get('email')
    }

    if not pending_emails:
        return len(accepted_ids)

    accepted_emails = set()
    if accepted_ids:
        profiles_resp = admin.table('profiles').select('id, email').in_(
            'id', list(accepted_ids)
        ).execute()
        accepted_emails = {
            row['email'].strip().lower()
            for row in (profiles_resp.data or []) if row.get('email')
        }

    new_pending = pending_emails - accepted_emails
    return len(accepted_ids) + len(new_pending)


def _script_already_charged(user_id: str, script_id: str) -> bool:
    resp = get_supabase_admin().table('breakdown_credits').select('id').eq(
        'user_id', user_id
    ).eq('script_id', script_id).lt('delta', 0).limit(1).execute()
    return bool(resp.data)


def _insert_spend(user_id: str, script_id: str) -> bool:
    get_supabase_admin().table('breakdown_credits').insert({
        'user_id': user_id,
        'delta': -1,
        'script_id': script_id,
        'reason': 'breakdown',
    }).execute()
    return True


def get_entitlement(user_id: str) -> dict:
    profile = _fetch_profile(user_id)
    if not profile:
        # Unknown user: deny everything.
        return {'tier': 'none', 'status': 'none', 'breakdown_balance': 0,
                'seats_paid': 0, 'seats_used': 0, 'billing_cycle': None,
                'signup_plan': None,
                'can_run_breakdown': False, 'can_use_teams': False}

    tier = profile.get('subscription_plan') or 'none'
    status = profile.get('subscription_status') or 'none'
    balance = _fetch_balance(user_id)
    seats_paid = _fetch_seats_paid(user_id)
    seats_used = _fetch_seats_used(user_id)

    tier2_active = (tier == TIER_2 and status == 'active')

    return {
        'tier': tier,
        'status': status,
        'breakdown_balance': balance,
        'seats_paid': seats_paid,
        'seats_used': seats_used,
        'billing_cycle': profile.get('subscription_billing_cycle'),
        'signup_plan': profile.get('signup_plan'),
        # Tier 2 active is unlimited; everyone else needs credits.
        'can_run_breakdown': tier2_active or balance > 0,
        # Expired tier 2 loses team writes (failed renewal => downgrade).
        'can_use_teams': tier2_active,
    }


def consume_breakdown(user_id: str, script_id: str) -> bool:
    """
    Charge one credit for this script, unless already charged or unlimited.
    Raises InsufficientCredits if the user cannot pay.

    ONE CHARGE PER SCRIPT, EVER: `_script_already_charged` is checked before
    the balance, so an already-paid script succeeds even at zero balance
    (re-analysis after edits is free).
    """
    ent = get_entitlement(user_id)

    if ent['tier'] == TIER_2 and ent['status'] == 'active':
        return True   # unlimited, no ledger write

    if _script_already_charged(user_id, script_id):
        return True   # one charge per script, ever

    if ent['breakdown_balance'] <= 0:
        raise InsufficientCredits("No breakdown credits remaining")

    _insert_spend(user_id, script_id)
    return True


def grant_credits(user_id: str, n: int, txn_id: str) -> None:
    get_supabase_admin().table('breakdown_credits').insert({
        'user_id': user_id, 'delta': n,
        'payfast_transaction_id': txn_id, 'reason': 'purchase',
    }).execute()


def activate_license(user_id: str, txn_id: str, payfast_token: str | None = None,
                      billing_cycle: str = 'annual') -> None:
    """
    payfast_token: the tokenization token PayFast's ITN returns on this
    charge (subscription_type=2 — see payfast_service.build_checkout_fields
    for why tier_2_license uses tokenization, not true recurring billing).
    Needed to charge the next renewal via PayFast's Recurring Billing API;
    None from the admin manual-approval path, which has no ITN.

    billing_cycle: 'monthly', '3month', '6month', or 'annual' — selects the
    term length and amount recorded. Defaults to 'annual' for backward
    compatibility with the admin manual-approval callers in
    routes/admin_routes.py, which predate the monthly option and don't
    pass one.
    """
    term_delta, amount = LICENSE_TERMS.get(billing_cycle, LICENSE_TERMS['annual'])
    expires = datetime.now(timezone.utc) + term_delta
    update = {
        'subscription_plan': TIER_2,
        'subscription_status': 'active',
        'subscription_expires_at': expires.isoformat(),
        'subscription_payment_provider': 'payfast',
        'subscription_amount': amount,
        'subscription_currency': 'ZAR',
        'subscription_billing_cycle': billing_cycle,
    }
    if payfast_token:
        update['subscription_payfast_token'] = payfast_token
    get_supabase_admin().table('profiles').update(update).eq('id', user_id).execute()

    # Seats bundled with this cadence, granted as part of the same purchase.
    # account_seats.seats_granted has a CHECK (seats_granted > 0), so the
    # monthly cadence (0 included) inserts nothing. account_seats.
    # payfast_transaction_id is a real FK to payfast_transactions(id) —
    # the admin manual-approval callers above pass a free-text Wise/beta
    # reference as txn_id, not a row id, so only attach it when it's
    # actually a UUID (the ITN path always passes one).
    included = INCLUDED_SEATS.get(billing_cycle, 0)
    if included > 0:
        try:
            seat_txn_id = str(uuid.UUID(str(txn_id)))
        except (ValueError, AttributeError, TypeError):
            seat_txn_id = None
        get_supabase_admin().table('account_seats').insert({
            'owner_id': user_id, 'seats_granted': included,
            'payfast_transaction_id': seat_txn_id, 'term_expires_at': expires.isoformat(),
        }).execute()


def grant_seats(owner_id: str, n: int, txn_id: str) -> None:
    profile = _fetch_profile(owner_id) or {}
    term = profile.get('subscription_expires_at') or \
        (datetime.now(timezone.utc) + ONE_YEAR).isoformat()
    get_supabase_admin().table('account_seats').insert({
        'owner_id': owner_id, 'seats_granted': n,
        'payfast_transaction_id': txn_id, 'term_expires_at': term,
    }).execute()


def require_breakdown_entitlement(f):
    """Fails closed: no user id means no access."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        if not get_entitlement(user_id)['can_run_breakdown']:
            return jsonify({
                'error': 'No breakdown credits remaining',
                'code': 'insufficient_credits',
            }), 402
        return f(*args, **kwargs)
    return wrapper


def require_team_tier(f):
    """Fails closed: no user id means no access."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        if not get_entitlement(user_id)['can_use_teams']:
            return jsonify({
                'error': 'Team features require a Team License',
                'code': 'tier_2_required',
            }), 403
        return f(*args, **kwargs)
    return wrapper
