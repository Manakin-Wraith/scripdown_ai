"""PayFast signature generation — order-sensitive MD5 over urlencoded fields."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import hashlib
from urllib.parse import quote_plus

from services.payfast_service import generate_signature


def _expected(pairs, passphrase=None):
    payload = "&".join(f"{k}={quote_plus(str(v))}" for k, v in pairs)
    if passphrase:
        payload += f"&passphrase={quote_plus(passphrase)}"
    return hashlib.md5(payload.encode()).hexdigest()


def test_signature_matches_urlencoded_md5():
    fields = {"merchant_id": "33568687", "amount": "450.00", "item_name": "Breakdown"}
    assert generate_signature(fields, None) == _expected(list(fields.items()))


def test_passphrase_is_appended_last():
    fields = {"merchant_id": "33568687", "amount": "450.00"}
    got = generate_signature(fields, "Secret-Pass-1")
    assert got == _expected(list(fields.items()), "Secret-Pass-1")
    assert got != generate_signature(fields, None)


def test_field_order_is_significant():
    a = generate_signature({"b": "2", "a": "1"}, None)
    b = generate_signature({"a": "1", "b": "2"}, None)
    assert a != b


def test_empty_values_are_excluded():
    # PayFast excludes empty fields from the signature payload entirely.
    with_empty = generate_signature({"a": "1", "b": "", "c": "3"}, None)
    without = generate_signature({"a": "1", "c": "3"}, None)
    assert with_empty == without


def test_spaces_encode_as_plus_and_hex_is_uppercase():
    sig = generate_signature({"item_name": "Team License"}, None)
    assert sig == hashlib.md5(b"item_name=Team+License").hexdigest()
    # Slashes must be %2F (uppercase), not %2f.
    sig2 = generate_signature({"url": "a/b"}, None)
    assert sig2 == hashlib.md5(b"url=a%2Fb").hexdigest()


def test_values_are_stripped():
    # A trailing space in the passphrase is a classic PayFast footgun.
    assert generate_signature({"a": " 1 "}, None) == generate_signature({"a": "1"}, None)
