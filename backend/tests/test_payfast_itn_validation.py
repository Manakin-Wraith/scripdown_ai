"""ITN validation: signature over received order, PayFast source IP, server confirmation."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.payfast_service as pf


def test_valid_signature_accepted():
    form = {"pf_payment_id": "1", "amount_gross": "450.00"}
    form["signature"] = pf.generate_signature(form, "pass")
    assert pf.verify_itn_signature(form, "pass") is True


def test_tampered_amount_rejected():
    form = {"pf_payment_id": "1", "amount_gross": "450.00"}
    form["signature"] = pf.generate_signature(form, "pass")
    form["amount_gross"] = "1.00"
    assert pf.verify_itn_signature(form, "pass") is False


def test_missing_signature_rejected():
    assert pf.verify_itn_signature({"pf_payment_id": "1"}, "pass") is False


def test_wrong_passphrase_rejected():
    form = {"pf_payment_id": "1"}
    form["signature"] = pf.generate_signature(form, "pass")
    assert pf.verify_itn_signature(form, "other") is False


def test_signature_excluded_from_its_own_payload():
    # The signature field must not be part of the string it signs.
    form = {"a": "1", "b": "2"}
    sig = pf.generate_signature(form, None)
    form["signature"] = sig
    assert pf.verify_itn_signature(form, None) is True


def test_valid_ip_accepted(monkeypatch):
    monkeypatch.setattr(pf, "_resolve_payfast_ips", lambda: {"1.2.3.4", "5.6.7.8"})
    assert pf.is_valid_payfast_ip("1.2.3.4") is True


def test_unknown_ip_rejected(monkeypatch):
    monkeypatch.setattr(pf, "_resolve_payfast_ips", lambda: {"1.2.3.4"})
    assert pf.is_valid_payfast_ip("9.9.9.9") is False


def test_dns_failure_fails_closed(monkeypatch):
    def boom():
        raise OSError("dns down")
    monkeypatch.setattr(pf, "_resolve_payfast_ips", boom)
    assert pf.is_valid_payfast_ip("1.2.3.4") is False


def test_confirm_returns_true_on_valid(monkeypatch):
    class Resp:
        status_code = 200
        text = "VALID"
    monkeypatch.setattr(pf.requests, "post", lambda *a, **k: Resp())
    assert pf.confirm_with_payfast({"a": "1"}) is True


def test_confirm_returns_false_on_invalid(monkeypatch):
    class Resp:
        status_code = 200
        text = "INVALID"
    monkeypatch.setattr(pf.requests, "post", lambda *a, **k: Resp())
    assert pf.confirm_with_payfast({"a": "1"}) is False


def test_confirm_fails_closed_on_exception(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(pf.requests, "post", boom)
    assert pf.confirm_with_payfast({"a": "1"}) is False


def test_confirm_rejects_validxyz_prefix_match(monkeypatch):
    """Exact match only — 'VALIDXYZ' must return False, not True."""
    class Resp:
        status_code = 200
        text = "VALIDXYZ"
    monkeypatch.setattr(pf.requests, "post", lambda *a, **k: Resp())
    assert pf.confirm_with_payfast({"a": "1"}) is False


def test_confirm_accepts_valid_with_trailing_newline(monkeypatch):
    """Trailing whitespace is stripped; 'VALID\\n' must return True."""
    class Resp:
        status_code = 200
        text = "VALID\n"
    monkeypatch.setattr(pf.requests, "post", lambda *a, **k: Resp())
    assert pf.confirm_with_payfast({"a": "1"}) is True


def test_empty_signature_rejected():
    """An empty signature string must be rejected (fail_closed)."""
    assert pf.verify_itn_signature({"pf_payment_id": "1", "signature": ""}, "pass") is False


def test_generate_signature_excludes_empty_by_default():
    # Outgoing (checkout) direction: PayFast expects unset fields omitted.
    with_empty_field = {"a": "1", "b": "", "c": "3"}
    without_empty_field = {"a": "1", "c": "3"}
    assert pf.generate_signature(with_empty_field, "pass") == \
        pf.generate_signature(without_empty_field, "pass")


def test_generate_signature_include_empty_signs_the_blank_field():
    # Incoming (ITN) direction: PayFast signs over its own always-sent,
    # often-blank fields (custom_str3, name_first, ...) as e.g. "b=".
    import hashlib
    expected = hashlib.md5(b"a=1&b=&c=3&passphrase=pass").hexdigest()
    got = pf.generate_signature({"a": "1", "b": "", "c": "3"}, "pass", include_empty=True)
    assert got == expected
    # Proven distinct from the exclude-empty (default) signature — this is
    # the actual production bug: verifying an ITN with the wrong one
    # rejects every legitimate notification PayFast sends.
    assert got != pf.generate_signature({"a": "1", "b": "", "c": "3"}, "pass")


def test_verify_itn_signature_accepts_payfasts_always_present_blank_fields():
    # Regression test for the real sandbox bug: PayFast's ITN includes
    # custom_str3-5/custom_int1-5/name_first/name_last/email_address even
    # when blank, and signs over them. verify_itn_signature must match
    # that — not the checkout (exclude-empty) convention.
    form = {
        "pf_payment_id": "1", "amount_gross": "450.00",
        "custom_str3": "", "custom_str4": "", "name_first": "",
    }
    form["signature"] = pf.generate_signature(
        {k: v for k, v in form.items()}, "pass", include_empty=True
    )
    assert pf.verify_itn_signature(form, "pass") is True
