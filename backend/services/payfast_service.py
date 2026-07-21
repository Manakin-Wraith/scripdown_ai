"""
PayFast Custom Integration for SlateOne.

Signed server-generated checkout forms + ITN validation. The dashboard's
Pay Now buttons are NOT usable: `require signature` is enabled on merchant
33568687, and unsigned requests are rejected.
"""

import hashlib
import os
from decimal import Decimal
from urllib.parse import quote_plus

import requests

# ZAR, VAT-inclusive. The only authority on price — never take an amount from a client.
PRICES = {
    'tier_1_credits': Decimal('450.00'),   # per breakdown
    'tier_2_license': Decimal('1850.00'),  # per year
    'tier_2_seats': Decimal('150.00'),     # per seat
}


def generate_signature(fields: dict, passphrase: str | None, include_empty: bool = False) -> str:
    """
    MD5 over `key=urlencoded_value` pairs joined by '&', in the given order,
    with `&passphrase=...` appended last.

    Order is significant — a PayFast requirement, not a choice. Values are
    stripped: a stray trailing space silently breaks every signature.

    `include_empty` must match which direction this is signing:
    - False (default) — for OUTGOING checkout fields, which we build.
      PayFast's checkout spec expects unset fields to be omitted entirely.
      A field is excluded when its value is `None`, or when
      `str(value).strip()` is empty. A value that stringifies to `'0'`
      (int 0, `Decimal('0.00')`, `'0'`) is meaningful data, not emptiness,
      and IS included regardless.
    - True — for verifying an INCOMING ITN's signature. PayFast's own ITN
      payload includes every field it always sends (custom_str3-5,
      custom_int1-5, name_first, name_last, email_address) even when
      empty, e.g. `custom_str3=`, and signs over that full set. Excluding
      them here — the outgoing-direction default — silently produces a
      signature PayFast never sent, rejecting every legitimate ITN.

    The passphrase follows the outgoing (False) emptiness rule always: a
    `None` or whitespace-only passphrase is treated as "no passphrase" and
    omitted rather than appended as `&passphrase=`.
    """
    parts = []
    for key, value in fields.items():
        if value is None:
            if include_empty:
                parts.append(f"{key}=")
            continue
        text = str(value).strip()
        if text == '':
            if include_empty:
                parts.append(f"{key}=")
            continue
        parts.append(f"{key}={quote_plus(text)}")

    payload = "&".join(parts)
    passphrase_text = passphrase.strip() if passphrase else ''
    if passphrase_text:
        payload += f"&passphrase={quote_plus(passphrase_text)}"

    return hashlib.md5(payload.encode()).hexdigest()


VALIDATE_URL = os.getenv(
    'PAYFAST_VALIDATE_URL',
    'https://sandbox.payfast.co.za/eng/query/validate'
    if os.getenv('PAYFAST_SANDBOX', 'false').lower() == 'true'
    else 'https://www.payfast.co.za/eng/query/validate'
)


def verify_itn_signature(form: dict, passphrase: str | None) -> bool:
    """
    Recompute the signature over the received fields, in received order,
    excluding `signature` itself.

    include_empty=True: PayFast's own ITN includes its always-sent-but-often-
    blank fields (custom_str3-5, custom_int1-5, name_first, name_last,
    email_address) in what it signs, e.g. `custom_str3=`. See
    generate_signature's docstring for why this differs from checkout.
    """
    received = form.get('signature')
    if not received:
        return False
    payload = {k: v for k, v in form.items() if k != 'signature'}
    return generate_signature(payload, passphrase, include_empty=True) == received


def confirm_with_payfast(form: dict) -> bool:
    """
    Server-to-server confirmation. Fails closed on any error — an
    unconfirmable payment must never grant entitlement.
    """
    payload = {k: v for k, v in form.items() if k != 'signature'}
    try:
        resp = requests.post(VALIDATE_URL, data=payload, timeout=10)
        return resp.status_code == 200 and resp.text.strip() == 'VALID'
    except Exception:
        return False


MERCHANT_ID = os.getenv('PAYFAST_MERCHANT_ID', '')
MERCHANT_KEY = os.getenv('PAYFAST_MERCHANT_KEY', '')
PASSPHRASE = os.getenv('PAYFAST_PASSPHRASE', '')

PROCESS_URL = (
    'https://sandbox.payfast.co.za/eng/process'
    if os.getenv('PAYFAST_SANDBOX', 'false').lower() == 'true'
    else 'https://payment.payfast.io/eng/process'
)

APP_URL = os.getenv('PAYFAST_APP_URL', 'https://app.slateone.studio')
API_URL = os.getenv('PAYFAST_API_URL', 'https://api.slateone.studio')

# Customer-facing copy. Product-owner directive: no "AI" wording.
CHARGE_COPY = {
    'tier_1_credits': ('Script Breakdown', 'Pay-per-breakdown'),
    'tier_2_license': ('Annual Team License', 'Annual team licence'),
    'tier_2_seats': ('Team Member Seat', 'Additional team seat'),
}


def compute_amount(charge_type: str, quantity: int) -> Decimal:
    """The only authority on what a purchase costs."""
    if charge_type not in PRICES:
        raise ValueError(f"Unknown charge_type: {charge_type}")
    if quantity < 1:
        raise ValueError(f"quantity must be >= 1, got {quantity}")
    # A licence is one licence — quantity applies to credits and seats only.
    if charge_type == 'tier_2_license':
        return PRICES[charge_type]
    return PRICES[charge_type] * quantity


def build_checkout_fields(charge_type: str, user_id: str, m_payment_id: str,
                          amount: Decimal) -> dict:
    """
    Build the signed form fields for PayFast's process endpoint.

    `amount` is passed in (already persisted on the intent) rather than
    recomputed, so the signed form and the stored intent cannot drift.

    Quantity lives in our UI, not PayFast's form (see design spec §6.1) —
    it is never sent to PayFast; the ITN handler reads it from our own
    intent row and must never trust request fields.
    """
    item_name, item_description = CHARGE_COPY[charge_type]

    fields = {
        'merchant_id': MERCHANT_ID,
        'merchant_key': MERCHANT_KEY,
        'return_url': f"{APP_URL}/payment/success?type={charge_type}",
        'cancel_url': f"{APP_URL}/payment/cancel?type={charge_type}",
        'notify_url': f"{API_URL}/api/payfast/notify",
        'm_payment_id': m_payment_id,
        'amount': f"{amount:.2f}",
        'item_name': item_name,
        'item_description': item_description,
        'custom_str1': user_id,      # attribution — the whole point
        'custom_str2': charge_type,  # convenience only; the intent is authoritative
    }

    if charge_type == 'tier_2_license':
        # subscription_type=1 (true recurring billing, PayFast auto-charges
        # on schedule) consistently rejects with a signature mismatch on
        # this account — confirmed via live sandbox testing that our
        # signing is correct: an otherwise-identical subscription_type=2
        # (tokenization) request succeeds immediately. Recurring Billing
        # isn't enabled on this merchant; tokenization is available by
        # default. Tokenization means PayFast only charges when WE tell it
        # to via its API, using the token it returns on activation — see
        # entitlement_service.activate_license and profiles.subscription_
        # payfast_token (migration 042). No billing_date/recurring_amount/
        # frequency/cycles: those only apply to true subscriptions.
        fields['subscription_type'] = '2'

    fields['signature'] = generate_signature(fields, PASSPHRASE)
    return fields
