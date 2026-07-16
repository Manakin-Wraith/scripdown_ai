"""
PayFast ITN webhook.

This endpoint is PUBLIC — PayFast calls it, so it cannot require auth.
Everything in the request is therefore untrusted. The charge type, amount
and quantity come from the intent row we created at checkout, NEVER from
the request. `?type=` and `custom_str2` are debug conveniences only.

Always returns 200: PayFast retries indefinitely on anything else, and a
retry storm is worse than a silently-ignored bad request (which we log).
"""

import uuid
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify

from db.supabase_client import get_supabase_admin
from middleware.auth import require_auth, get_user_id
from services.payfast_service import (
    verify_itn_signature, is_valid_payfast_ip, confirm_with_payfast, PASSPHRASE,
    compute_amount, build_checkout_fields, PROCESS_URL,
)
from services.entitlement_service import (
    grant_credits, activate_license, grant_seats, get_entitlement,
)

payfast_bp = Blueprint('payfast', __name__)


def _load_intent(m_payment_id: str):
    resp = get_supabase_admin().table('payfast_transactions').select('*').eq(
        'm_payment_id', m_payment_id
    ).limit(1).execute()
    return resp.data[0] if resp.data else None


def _already_processed(pf_payment_id: str) -> bool:
    resp = get_supabase_admin().table('payfast_transactions').select('id').eq(
        'pf_payment_id', pf_payment_id
    ).limit(1).execute()
    return bool(resp.data)


def _claim_intent(txn_id: str, pf_payment_id: str, payload: dict) -> bool:
    """
    Atomically claim an intent for granting. Returns False if someone else
    already has it.

    This — not `_already_processed` — is what makes granting idempotent.
    Two ITNs for the same payment can both pass that check before either
    writes, so the check alone leaves a double-grant window. Postgres
    serialises concurrent UPDATEs to the same row and re-evaluates the WHERE
    against the winner's committed result, so of two racing callers exactly
    one matches `status = 'pending'` and gets a row back. The loser sees no
    rows and must not grant.

    Claiming *before* granting means the failure mode is a missed grant
    rather than a double grant. `_release_claim` hands the row back so
    PayFast's next retry can redo it.
    """
    resp = get_supabase_admin().table('payfast_transactions').update({
        'pf_payment_id': pf_payment_id,
        'status': 'complete',
        'raw_payload': payload,
    }).eq('id', txn_id).eq('status', 'pending').execute()
    return bool(resp.data)


def _release_claim(txn_id: str) -> None:
    """Return a claimed row to 'pending' so a retry can grant it."""
    get_supabase_admin().table('payfast_transactions').update({
        'pf_payment_id': None,
        'status': 'pending',
    }).eq('id', txn_id).execute()


def _reject(reason: str):
    # 200 so PayFast stops retrying; the body is for our logs only.
    print(f"[payfast-itn] REJECTED: {reason}")
    return jsonify({'status': 'ignored'}), 200


@payfast_bp.route('/api/payfast/notify', methods=['POST'])
def payfast_notify():
    form = request.form.to_dict()

    if not verify_itn_signature(form, PASSPHRASE):
        return _reject('signature mismatch')

    if not is_valid_payfast_ip(request.remote_addr):
        return _reject(f'untrusted source ip {request.remote_addr}')

    pf_payment_id = form.get('pf_payment_id')
    if not pf_payment_id:
        return _reject('missing pf_payment_id')

    if _already_processed(pf_payment_id):
        return jsonify({'status': 'duplicate'}), 200   # idempotent

    intent = _load_intent(form.get('m_payment_id', ''))
    if not intent:
        return _reject(f"unknown m_payment_id {form.get('m_payment_id')}")

    try:
        paid = Decimal(form.get('amount_gross', '0'))
    except (InvalidOperation, TypeError):
        return _reject('unparseable amount_gross')

    expected = Decimal(str(intent['expected_amount']))
    if abs(paid - expected) > Decimal('0.01'):
        return _reject(f'amount mismatch: paid {paid}, expected {expected}')

    if not confirm_with_payfast(form):
        return _reject('payfast did not confirm')

    if form.get('payment_status') != 'COMPLETE':
        return _reject(f"payment_status {form.get('payment_status')}")

    # Authoritative values — from the intent, not the request.
    user_id = intent['user_id']
    charge_type = intent['charge_type']
    quantity = int(intent['quantity'])
    txn_id = intent['id']

    # Validate before claiming, so a bad row is never left marked complete.
    if charge_type not in ('tier_1_credits', 'tier_2_license', 'tier_2_seats'):
        return _reject(f'unknown charge_type {charge_type}')

    # The concurrency boundary: past here we hold the row exclusively.
    if not _claim_intent(txn_id, pf_payment_id, form):
        return jsonify({'status': 'duplicate'}), 200   # someone else has it

    try:
        if charge_type == 'tier_1_credits':
            grant_credits(user_id, quantity, txn_id)
        elif charge_type == 'tier_2_license':
            activate_license(user_id, txn_id)
        elif charge_type == 'tier_2_seats':
            grant_seats(user_id, quantity, txn_id)
    except Exception as exc:
        _release_claim(txn_id)
        return _reject(f'grant failed, released for retry: {exc!r}')

    return jsonify({'status': 'ok'}), 200


def _create_intent(user_id, charge_type, quantity, amount, m_payment_id):
    get_supabase_admin().table('payfast_transactions').insert({
        'm_payment_id': m_payment_id,
        'user_id': user_id,
        'charge_type': charge_type,
        'expected_amount': float(amount),
        'quantity': quantity,
        'status': 'pending',
    }).execute()


@payfast_bp.route('/api/billing/checkout', methods=['POST'])
@require_auth
def create_checkout():
    """
    Create a payment intent and return signed PayFast form fields.

    The amount is computed here and persisted before the user leaves, so the
    ITN can validate against our own record. Any `amount` in the request body
    is ignored on purpose.
    """
    user_id = get_user_id()
    body = request.get_json(silent=True) or {}
    charge_type = body.get('charge_type')

    raw_quantity = body.get('quantity', 1)
    try:
        quantity = int(raw_quantity)
    except (TypeError, ValueError):
        return jsonify({'error': 'quantity must be an integer'}), 400

    try:
        amount = compute_amount(charge_type, quantity)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    m_payment_id = str(uuid.uuid4())
    _create_intent(user_id, charge_type, quantity, amount, m_payment_id)

    fields = build_checkout_fields(charge_type, user_id, m_payment_id, amount)
    return jsonify({'process_url': PROCESS_URL, 'fields': fields}), 200


@payfast_bp.route('/api/billing/entitlement', methods=['GET'])
@require_auth
def read_entitlement():
    return jsonify(get_entitlement(get_user_id())), 200
