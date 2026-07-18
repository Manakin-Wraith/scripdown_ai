"""Team features are tier 2 only, and seat limits are enforced server-side."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.invite_routes as ir


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_tier1_cannot_create_invite(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr("services.entitlement_service.get_user_id", lambda: 'u1')
    monkeypatch.setattr("services.entitlement_service.get_entitlement",
                        lambda uid: {'can_use_teams': False})
    resp = _client().post("/api/scripts/s1/invites", json={'email': 'a@b.com'})
    assert resp.status_code == 403
    assert resp.get_json()['code'] == 'tier_2_required'


def test_departments_list_requires_auth(monkeypatch):
    # Previously had no decorator at all.
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    assert _client().get("/api/invite/departments").status_code == 401
    assert _client().get("/api/departments").status_code == 401


def test_invite_blocked_when_seats_exhausted(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr("services.entitlement_service.get_user_id", lambda: 'owner')
    monkeypatch.setattr("services.entitlement_service.get_entitlement",
                        lambda uid: {'can_use_teams': True})
    monkeypatch.setattr(ir, "get_entitlement",
                        lambda uid: {'can_use_teams': True, 'seats_paid': 2, 'seats_used': 2})
    resp = _client().post("/api/scripts/s1/invites", json={'email': 'a@b.com'})
    assert resp.status_code == 402
    assert resp.get_json()['code'] == 'no_seats_available'


def test_public_invite_token_lookup_stays_public(monkeypatch):
    # An invitee is not yet a member and may not be a tier 2 user — this must
    # NOT be gated, or nobody can ever accept an invite.
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().get("/api/invites/token/sometoken")
    assert resp.status_code != 401
