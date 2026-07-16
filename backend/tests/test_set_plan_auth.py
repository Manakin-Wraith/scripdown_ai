"""set-plan must never take user_id from the request body (account takeover)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.auth_routes as ar


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_set_plan_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().post("/api/auth/set-plan",
                          json={'user_id': 'victim', 'plan': 'tier_2_annual_team'})
    assert resp.status_code == 401


def test_body_user_id_is_ignored(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(ar, "get_user_id", lambda: 'attacker')
    written = {}
    monkeypatch.setattr(ar, "_upsert_profile", lambda uid, data: written.update(uid=uid))
    _client().post("/api/auth/set-plan",
                   json={'user_id': 'victim', 'plan': 'tier_1_pay_per_breakdown'})
    assert written['uid'] == 'attacker'      # the token's user, never the body's


def test_invalid_plan_rejected(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(ar, "get_user_id", lambda: 'u1')
    resp = _client().post("/api/auth/set-plan", json={'plan': 'free_forever'})
    assert resp.status_code == 400


def test_landing_tier_params_map_to_full_ids(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(ar, "get_user_id", lambda: 'u1')
    written = {}
    monkeypatch.setattr(ar, "_upsert_profile", lambda uid, data: written.update(data))
    _client().post("/api/auth/set-plan", json={'plan': 'tier_1'})
    assert written['signup_plan'] == 'tier_1_pay_per_breakdown'


def test_created_at_is_not_overwritten(monkeypatch):
    # The old upsert reset created_at, which get_subscription_status used as the
    # trial-start fallback — effectively renewing an expired trial.
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(ar, "get_user_id", lambda: 'u1')
    written = {}
    monkeypatch.setattr(ar, "_upsert_profile", lambda uid, data: written.update(data))
    _client().post("/api/auth/set-plan", json={'plan': 'tier_2'})
    assert 'created_at' not in written


def test_profile_keeps_email_and_full_name(monkeypatch):
    # set-plan is the only thing that creates profiles — no auth.users trigger
    # does it — so dropping these would leave profiles with no email at all.
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(ar, "get_user_id", lambda: 'u1')
    monkeypatch.setattr(ar, "get_current_user", lambda: {'id': 'u1', 'email': 'real@example.com'})
    written = {}
    monkeypatch.setattr(ar, "_upsert_profile", lambda uid, data: written.update(data))
    _client().post("/api/auth/set-plan",
                   json={'plan': 'tier_1', 'full_name': 'Ada Lovelace'})
    assert written['email'] == 'real@example.com'
    assert written['full_name'] == 'Ada Lovelace'


def test_body_email_cannot_override_the_token(monkeypatch):
    # Same reasoning as user_id: the body is attacker-controlled.
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(ar, "get_user_id", lambda: 'u1')
    monkeypatch.setattr(ar, "get_current_user", lambda: {'id': 'u1', 'email': 'real@example.com'})
    written = {}
    monkeypatch.setattr(ar, "_upsert_profile", lambda uid, data: written.update(data))
    _client().post("/api/auth/set-plan",
                   json={'plan': 'tier_1', 'email': 'victim@example.com'})
    assert written['email'] == 'real@example.com'
