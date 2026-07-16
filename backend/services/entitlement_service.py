"""
Entitlement — the single source of truth for "may this user do this?".

Replaces the three copy-pasted `status != 'active'` checks in supabase_routes
and the dead, fail-open `require_active_subscription` in subscription_service.

Every decorator here fails CLOSED. The old one read `g.user_id`, which
middleware/auth.py never sets, so it passed every request through.
"""

from functools import wraps
from datetime import datetime, timezone, timedelta

from flask import jsonify

from db.supabase_client import get_supabase_admin
from middleware.auth import get_user_id

TIER_1 = 'tier_1_pay_per_breakdown'
TIER_2 = 'tier_2_annual_team'

# One-year term length. Using a fixed-day advance rather than
# `datetime.replace(year=year + 1)`, which raises ValueError when `now` is
# 29 Feb and next year is not a leap year.
ONE_YEAR = timedelta(days=365)


class InsufficientCredits(Exception):
    """Tier 1 user tried to run a breakdown with no credits."""


def _fetch_profile(user_id: str):
    resp = get_supabase_admin().table('profiles').select(
        'subscription_plan, subscription_status, subscription_expires_at'
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
    Seats are billed per team MEMBER (per person), not per membership row.
    `script_members` is a per-(script, user) table, so the same person
    invited to three scripts must consume one seat, not three. supabase-py
    has no count-distinct, so select the raw user_id column and dedupe in
    Python.
    """
    resp = get_supabase_admin().table('script_members').select(
        'user_id'
    ).eq('invited_by', owner_id).execute()
    return len({row['user_id'] for row in (resp.data or [])})


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
                'seats_paid': 0, 'seats_used': 0,
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


def activate_license(user_id: str, txn_id: str) -> None:
    expires = datetime.now(timezone.utc) + ONE_YEAR
    get_supabase_admin().table('profiles').update({
        'subscription_plan': TIER_2,
        'subscription_status': 'active',
        'subscription_expires_at': expires.isoformat(),
        'subscription_payment_provider': 'payfast',
        'subscription_amount': 1850.00,
        'subscription_currency': 'ZAR',
    }).eq('id', user_id).execute()


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
                'error': 'Team features require an Annual Team License',
                'code': 'tier_2_required',
            }), 403
        return f(*args, **kwargs)
    return wrapper
