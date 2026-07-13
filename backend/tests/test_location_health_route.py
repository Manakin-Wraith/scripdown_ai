"""Location health endpoint requires auth + owner/member access."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.supabase_routes as sr


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_health_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().get("/api/scripts/s1/locations/health")
    # optional_auth mirrors the sibling suggestions route: with no bearer token
    # and DEV_MODE off, get_user_id() yields no identity, so access is denied
    # (401 unauthenticated or 403 forbidden depending on downstream checks).
    assert resp.status_code in (401, 403)


def test_health_forbidden_for_non_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: False)
    resp = _client().get("/api/scripts/s1/locations/health")
    assert resp.status_code == 403


def test_health_ok_returns_report(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)

    class _Q:
        def __init__(self, table):
            self.table = table
        def select(self, *a, **k):
            return self
        def eq(self, col, val):
            return self
        def execute(self):
            class _R:
                data = [
                    {"setting": "INT. VILLA - 2 7", "int_ext": "INT", "time_of_day": "2 7",
                     "location_hierarchy": None, "location_canonical": None, "is_omitted": False},
                ]
            return _R()

    class _FakeSupa:
        def table(self, name):
            return _Q(name)

    monkeypatch.setattr(sr, "supabase", _FakeSupa())
    resp = _client().get("/api/scripts/s1/locations/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["script_id"] == "s1"
    assert "total" in body and "by_key" in body
