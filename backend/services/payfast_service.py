"""
PayFast Custom Integration for SlateOne.

Signed server-generated checkout forms + ITN validation. The dashboard's
Pay Now buttons are NOT usable: `require signature` is enabled on merchant
33568687, and unsigned requests are rejected.
"""

import hashlib
import os
import socket
from decimal import Decimal
from urllib.parse import quote_plus

import requests

# ZAR, VAT-inclusive. The only authority on price — never take an amount from a client.
PRICES = {
    'tier_1_credits': Decimal('450.00'),   # per breakdown
    'tier_2_license': Decimal('1850.00'),  # per year
    'tier_2_seats': Decimal('150.00'),     # per seat
}


def generate_signature(fields: dict, passphrase: str | None) -> str:
    """
    MD5 over `key=urlencoded_value` pairs joined by '&', in the given order,
    with `&passphrase=...` appended last.

    Order is significant — a PayFast requirement, not a choice. Values are
    stripped: a stray trailing space silently breaks every signature.

    A field is excluded from the payload entirely when its value is `None`,
    or when `str(value).strip()` is empty (i.e. `''` or whitespace-only).
    A value that stringifies to `'0'` (int 0, `Decimal('0.00')`, `'0'`) is
    meaningful data, not emptiness, and IS included. The passphrase follows
    the same rule: a `None` or whitespace-only passphrase is treated as "no
    passphrase" and omitted rather than appended as `&passphrase=`.
    """
    parts = []
    for key, value in fields.items():
        if value is None:
            continue
        text = str(value).strip()
        if text == '':
            continue
        parts.append(f"{key}={quote_plus(text)}")

    payload = "&".join(parts)
    passphrase_text = passphrase.strip() if passphrase else ''
    if passphrase_text:
        payload += f"&passphrase={quote_plus(passphrase_text)}"

    return hashlib.md5(payload.encode()).hexdigest()


PAYFAST_HOSTS = [
    'www.payfast.co.za',
    'sandbox.payfast.co.za',
    'w1w.payfast.co.za',
    'w2w.payfast.co.za',
    'payment.payfast.io',
]

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
    """
    received = form.get('signature')
    if not received:
        return False
    payload = {k: v for k, v in form.items() if k != 'signature'}
    return generate_signature(payload, passphrase) == received


def _resolve_payfast_ips() -> set:
    """Resolve PayFast's ITN source hosts. Separated for test injection."""
    ips = set()
    for host in PAYFAST_HOSTS:
        for info in socket.getaddrinfo(host, 443):
            ips.add(info[4][0])
    return ips


def is_valid_payfast_ip(ip: str) -> bool:
    """Fails closed: a DNS failure means we cannot prove the source, so we reject."""
    try:
        return ip in _resolve_payfast_ips()
    except Exception:
        return False


def confirm_with_payfast(form: dict) -> bool:
    """
    Server-to-server confirmation. Fails closed on any error — an
    unconfirmable payment must never grant entitlement.
    """
    payload = {k: v for k, v in form.items() if k != 'signature'}
    try:
        resp = requests.post(VALIDATE_URL, data=payload, timeout=10)
        return resp.status_code == 200 and resp.text.strip().startswith('VALID')
    except Exception:
        return False
