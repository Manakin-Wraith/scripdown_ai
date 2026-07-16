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
