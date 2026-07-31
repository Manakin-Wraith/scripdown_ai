"""Checkout creates a server-side intent. The client cannot influence the amount."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from decimal import Decimal
import routes.payfast_routes as pr


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_checkout_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().post("/api/billing/checkout", json={'charge_type': 'tier_1_credits'})
    assert resp.status_code == 401


def test_checkout_creates_intent_with_server_amount(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(pr, "get_user_id", lambda: 'u1')
    saved = {}
    monkeypatch.setattr(pr, "_create_intent",
                        lambda uid, ct, q, amt, mpid, cycle=None: saved.update(
                            user=uid, charge=ct, qty=q, amount=amt))
    resp = _client().post("/api/billing/checkout",
                          json={'charge_type': 'tier_1_credits', 'quantity': 3})
    assert resp.status_code == 200
    assert saved['amount'] == Decimal('6750.00')    # 3 x 2250, computed server-side
    assert saved['user'] == 'u1'


def test_client_supplied_amount_is_ignored(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(pr, "get_user_id", lambda: 'u1')
    saved = {}
    monkeypatch.setattr(pr, "_create_intent",
                        lambda uid, ct, q, amt, mpid, cycle=None: saved.update(amount=amt))
    _client().post("/api/billing/checkout",
                   json={'charge_type': 'tier_1_credits', 'quantity': 1, 'amount': '1.00'})
    assert saved['amount'] == Decimal('2250.00')     # not 1.00


def test_response_carries_signed_fields(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(pr, "get_user_id", lambda: 'u1')
    monkeypatch.setattr(pr, "_create_intent", lambda *a: None)
    resp = _client().post("/api/billing/checkout",
                          json={'charge_type': 'tier_1_credits', 'quantity': 1})
    body = resp.get_json()
    assert 'signature' in body['fields']
    assert body['fields']['custom_str1'] == 'u1'
    assert body['process_url'].endswith('/eng/process')


def test_bad_charge_type_is_400(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(pr, "get_user_id", lambda: 'u1')
    resp = _client().post("/api/billing/checkout", json={'charge_type': 'free_stuff'})
    assert resp.status_code == 400


def test_bad_quantity_is_400(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(pr, "get_user_id", lambda: 'u1')
    resp = _client().post("/api/billing/checkout",
                          json={'charge_type': 'tier_1_credits', 'quantity': 0})
    assert resp.status_code == 400


def test_non_integer_quantity_is_400(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(pr, "get_user_id", lambda: 'u1')
    resp = _client().post("/api/billing/checkout",
                          json={'charge_type': 'tier_1_credits', 'quantity': 'lots'})
    assert resp.status_code == 400


def test_entitlement_endpoint_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    assert _client().get("/api/billing/entitlement").status_code == 401


def test_billing_cycle_selects_price_for_license(monkeypatch):
    # Annual is a discounted prepay of the same license, not a separate
    # product — the client picks a cadence, the server prices it.
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(pr, "get_user_id", lambda: 'u1')
    saved = {}
    monkeypatch.setattr(pr, "_create_intent",
                        lambda uid, ct, q, amt, mpid, cycle=None: saved.update(amount=amt, cycle=cycle))
    _client().post("/api/billing/checkout",
                   json={'charge_type': 'tier_2_license', 'quantity': 1, 'billing_cycle': 'monthly'})
    assert saved == {'amount': Decimal('1850.00'), 'cycle': 'monthly'}


def test_billing_cycle_defaults_to_annual(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(pr, "get_user_id", lambda: 'u1')
    saved = {}
    monkeypatch.setattr(pr, "_create_intent",
                        lambda uid, ct, q, amt, mpid, cycle=None: saved.update(amount=amt, cycle=cycle))
    _client().post("/api/billing/checkout",
                   json={'charge_type': 'tier_2_seats', 'quantity': 2})
    assert saved == {'amount': Decimal('5000.00'), 'cycle': 'annual'}


def test_invalid_billing_cycle_is_400(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(pr, "get_user_id", lambda: 'u1')
    resp = _client().post("/api/billing/checkout",
                          json={'charge_type': 'tier_2_license', 'quantity': 1, 'billing_cycle': 'weekly'})
    assert resp.status_code == 400


def test_tier_1_credits_ignores_billing_cycle(monkeypatch):
    # billing_cycle is meaningless for a one-off breakdown purchase — must
    # not be required or affect the price.
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(pr, "get_user_id", lambda: 'u1')
    saved = {}
    monkeypatch.setattr(pr, "_create_intent",
                        lambda uid, ct, q, amt, mpid, cycle=None: saved.update(amount=amt, cycle=cycle))
    resp = _client().post("/api/billing/checkout",
                          json={'charge_type': 'tier_1_credits', 'quantity': 1, 'billing_cycle': 'weekly'})
    assert resp.status_code == 200
    assert saved == {'amount': Decimal('2250.00'), 'cycle': None}
