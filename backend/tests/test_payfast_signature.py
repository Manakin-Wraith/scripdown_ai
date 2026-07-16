"""PayFast signature generation — order-sensitive MD5 over urlencoded fields."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import hashlib

from services.payfast_service import generate_signature


def test_signature_matches_urlencoded_md5():
    # Hardcoded oracle: md5("merchant_id=33568687&amount=450.00&item_name=Breakdown")
    fields = {"merchant_id": "33568687", "amount": "450.00", "item_name": "Breakdown"}
    expected = hashlib.md5(
        b"merchant_id=33568687&amount=450.00&item_name=Breakdown"
    ).hexdigest()
    assert expected == "8d404d40e22d77c822b07bae6d26631a"
    assert generate_signature(fields, None) == expected


def test_passphrase_is_appended_last():
    # Hardcoded oracle: md5("merchant_id=33568687&amount=450.00&passphrase=Secret-Pass-1")
    fields = {"merchant_id": "33568687", "amount": "450.00"}
    expected = hashlib.md5(
        b"merchant_id=33568687&amount=450.00&passphrase=Secret-Pass-1"
    ).hexdigest()
    assert expected == "912ca6b35fa346d7c93dfab1517fae1b"
    got = generate_signature(fields, "Secret-Pass-1")
    assert got == expected
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


def test_none_valued_field_is_excluded():
    # A caller writing fields['custom_str1'] = something or None must not
    # produce a payload containing the literal string "None".
    with_none = generate_signature({"a": "1", "b": None, "c": "3"}, None)
    without = generate_signature({"a": "1", "c": "3"}, None)
    assert with_none == without


def test_zero_valued_field_is_included():
    # Zero is meaningful data, not emptiness — unlike None/'' it must stay in the payload.
    with_zero = generate_signature({"a": "1", "b": 0, "c": "3"}, None)
    without = generate_signature({"a": "1", "c": "3"}, None)
    assert with_zero != without
    assert with_zero == generate_signature({"a": "1", "b": "0", "c": "3"}, None)


def test_whitespace_only_passphrase_behaves_as_no_passphrase():
    fields = {"a": "1"}
    assert generate_signature(fields, "   ") == generate_signature(fields, None)
