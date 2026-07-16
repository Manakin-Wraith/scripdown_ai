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

    Order is significant and empty values are excluded — both are PayFast
    requirements, not choices. Values are stripped: a stray trailing space
    silently breaks every signature.
    """
    parts = []
    for key, value in fields.items():
        text = str(value).strip()
        if text == '':
            continue
        parts.append(f"{key}={quote_plus(text)}")

    payload = "&".join(parts)
    if passphrase:
        payload += f"&passphrase={quote_plus(passphrase.strip())}"

    return hashlib.md5(payload.encode()).hexdigest()
