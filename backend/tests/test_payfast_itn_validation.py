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
