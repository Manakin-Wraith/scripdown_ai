"""Breakdown routes must be gated — including for anonymous callers."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.supabase_routes as sr
import middleware.authorization as authz


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_anonymous_analysis_is_rejected(monkeypatch):
    # The old gate was `if user_id:` under @optional_auth — anonymous callers
    # skipped the paywall entirely and got free analysis.
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().post("/api/scenes/scene-1/analyze")
    assert resp.status_code == 401


def test_anonymous_bulk_is_rejected(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().post("/api/scripts/script-1/analyze/bulk")
    assert resp.status_code == 401


def test_tier1_without_credits_gets_402(monkeypatch, fake_supabase):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    # require_script_role(resolver=from_scene) runs before the entitlement gate —
    # supply a resolvable scene/role so the request reaches the credits check.
    fake_supabase.set_table("scenes", [{"id": "scene-1", "script_id": "scr-1"}])
    monkeypatch.setattr(authz, "get_supabase_client", lambda: fake_supabase)
    monkeypatch.setattr(authz, "get_script_role", lambda script_id, user_id: "member")
    monkeypatch.setattr("services.entitlement_service.get_user_id", lambda: 'u1')
    monkeypatch.setattr("services.entitlement_service.get_entitlement",
                        lambda uid: {'can_run_breakdown': False})
    resp = _client().post("/api/scenes/scene-1/analyze")
    assert resp.status_code == 402
    assert resp.get_json()['code'] == 'insufficient_credits'


def test_legacy_sqlite_analysis_routes_are_gone(monkeypatch):
    # These were dead SQLite-legacy code: <int:script_id> converters that a
    # real (UUID) script_id can never match, so they already 404'd on every
    # real request — deleted outright rather than gated. Confirm removal,
    # not just a gate, so they can't be silently reintroduced as a free
    # back door.
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    for path in ("/api/scripts/1/analysis/start",
                 "/api/scripts/1/analysis/retry",
                 "/api/scripts/1/reanalyze",
                 "/api/scripts/1/analyze/characters",
                 "/api/scripts/1/analyze/locations",
                 "/api/scripts/1/analysis/queue-character",
                 "/api/scripts/1/analysis/queue-location",
                 "/analyze_script/1",
                 "/analyze_script_stream/1"):
        resp = _client().post(path)
        assert resp.status_code == 404, f"{path} still exists (got {resp.status_code})"
