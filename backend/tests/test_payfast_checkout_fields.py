"""Checkout fields are server-computed and signed. The client never supplies an amount."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from decimal import Decimal
import pytest

import services.payfast_service as pf


def test_compute_amount_multiplies_by_quantity():
    assert pf.compute_amount('tier_1_credits', 3) == Decimal('1350.00')
    assert pf.compute_amount('tier_2_seats', 4, 'monthly') == Decimal('1000.00')
    assert pf.compute_amount('tier_2_seats', 4, 'annual') == Decimal('10000.00')


def test_license_ignores_quantity():
    # A licence is one licence regardless of what the client asks for.
    # Annual is a discounted prepay of the same product, not a separate one.
    assert pf.compute_amount('tier_2_license', 7, 'monthly') == Decimal('1850.00')
    assert pf.compute_amount('tier_2_license', 7, 'annual') == Decimal('18500.00')


def test_invalid_billing_cycle_raises():
    with pytest.raises(ValueError):
        pf.compute_amount('tier_2_license', 1, 'weekly')


def test_unknown_charge_type_raises():
    with pytest.raises(ValueError):
        pf.compute_amount('free_stuff', 1)


def test_non_positive_quantity_raises():
    with pytest.raises(ValueError):
        pf.compute_amount('tier_1_credits', 0)
    with pytest.raises(ValueError):
        pf.compute_amount('tier_1_credits', -5)


def test_fields_carry_user_and_intent(monkeypatch):
    monkeypatch.setattr(pf, "MERCHANT_ID", "33568687")
    monkeypatch.setattr(pf, "MERCHANT_KEY", "key123")
    monkeypatch.setattr(pf, "PASSPHRASE", "pass")
    fields = pf.build_checkout_fields(
        'tier_1_credits', 'user-abc', 'mpid-123', Decimal('900.00')
    )
    assert fields['custom_str1'] == 'user-abc'      # attribution
    assert fields['custom_str2'] == 'tier_1_credits'
    assert fields['m_payment_id'] == 'mpid-123'
    assert fields['amount'] == '900.00'
    assert 'signature' in fields


def test_signature_is_valid_over_the_fields(monkeypatch):
    monkeypatch.setattr(pf, "MERCHANT_ID", "33568687")
    monkeypatch.setattr(pf, "MERCHANT_KEY", "key123")
    monkeypatch.setattr(pf, "PASSPHRASE", "pass")
    fields = pf.build_checkout_fields(
        'tier_1_credits', 'u1', 'm1', Decimal('450.00')
    )
    sig = fields.pop('signature')
    assert pf.generate_signature(fields, "pass") == sig


def test_license_uses_tokenization(monkeypatch):
    # subscription_type=1 (true recurring billing) isn't enabled on our
    # PayFast account — confirmed via live sandbox testing (an identical
    # request with subscription_type=2 succeeds where =1 signature-mismatches).
    # =2 (tokenization) needs none of billing_date/recurring_amount/
    # frequency/cycles, since we trigger renewal charges ourselves later.
    monkeypatch.setattr(pf, "MERCHANT_ID", "33568687")
    monkeypatch.setattr(pf, "MERCHANT_KEY", "key123")
    monkeypatch.setattr(pf, "PASSPHRASE", "pass")
    fields = pf.build_checkout_fields(
        'tier_2_license', 'u1', 'm1', Decimal('1850.00')
    )
    assert fields['subscription_type'] == '2'
    assert 'recurring_amount' not in fields
    assert 'cycles' not in fields
    assert 'frequency' not in fields


def test_one_off_charges_have_no_subscription_params(monkeypatch):
    monkeypatch.setattr(pf, "MERCHANT_ID", "33568687")
    monkeypatch.setattr(pf, "MERCHANT_KEY", "key123")
    monkeypatch.setattr(pf, "PASSPHRASE", "pass")
    fields = pf.build_checkout_fields(
        'tier_2_seats', 'u1', 'm1', Decimal('300.00')
    )
    assert 'subscription_type' not in fields


def test_no_ai_wording_in_customer_facing_copy(monkeypatch):
    monkeypatch.setattr(pf, "MERCHANT_ID", "33568687")
    monkeypatch.setattr(pf, "MERCHANT_KEY", "key123")
    monkeypatch.setattr(pf, "PASSPHRASE", "pass")
    for ct in ('tier_1_credits', 'tier_2_license', 'tier_2_seats'):
        price = pf.PRICES[ct]
        amount = price['annual'] if isinstance(price, dict) else price
        fields = pf.build_checkout_fields(ct, 'u1', 'm1', amount, 'annual')
        copy = f"{fields['item_name']} {fields['item_description']}".lower()
        assert 'ai' not in copy.split()


def test_no_custom_int1_in_checkout_fields(monkeypatch):
    # Quantity lives in our UI, not PayFast's form (spec §6.1) — the ITN
    # handler must never trust a request field for quantity.
    monkeypatch.setattr(pf, "MERCHANT_ID", "33568687")
    monkeypatch.setattr(pf, "MERCHANT_KEY", "key123")
    monkeypatch.setattr(pf, "PASSPHRASE", "pass")
    fields = pf.build_checkout_fields(
        'tier_1_credits', 'u1', 'm1', Decimal('450.00')
    )
    assert 'custom_int1' not in fields
