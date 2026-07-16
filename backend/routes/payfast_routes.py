"""
PayFast ITN webhook.

This endpoint is PUBLIC — PayFast calls it, so it cannot require auth.
Everything in the request is therefore untrusted. The charge type, amount
and quantity come from the intent row we created at checkout, NEVER from
the request. `?type=` and `custom_str2` are debug conveniences only.

Always returns 200: PayFast retries indefinitely on anything else, and a
retry storm is worse than a silently-ignored bad request (which we log).
"""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify

from db.supabase_client import get_supabase_admin
from services.payfast_service import (
    verify_itn_signature, is_valid_payfast_ip, confirm_with_payfast, PASSPHRASE,
)
from services.entitlement_service import grant_credits, activate_license, grant_seats

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


def _mark_complete(txn_id: str, pf_payment_id: str, payload: dict) -> None:
    get_supabase_admin().table('payfast_transactions').update({
        'pf_payment_id': pf_payment_id,
        'status': 'complete',
        'raw_payload': payload,
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

    if charge_type == 'tier_1_credits':
        grant_credits(user_id, quantity, txn_id)
    elif charge_type == 'tier_2_license':
        activate_license(user_id, txn_id)
    elif charge_type == 'tier_2_seats':
        grant_seats(user_id, quantity, txn_id)
    else:
        return _reject(f'unknown charge_type {charge_type}')

    _mark_complete(txn_id, pf_payment_id, form)
    return jsonify({'status': 'ok'}), 200
