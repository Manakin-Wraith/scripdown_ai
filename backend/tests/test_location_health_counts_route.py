"""Batch location health-counts endpoint: bounded to the caller's own scripts."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.supabase_routes as sr


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_health_counts_no_identity_returns_empty(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().get("/api/scripts/locations/health-counts")
    # Graceful degradation: never 401/500 on missing identity.
    assert resp.status_code == 200
    assert resp.get_json() == {"counts": {}}


def test_health_counts_resolves_and_not_shadowed(monkeypatch):
    # This asserts the route itself resolves (not swallowed by
    # /api/scripts/<script_id>/... and not 404'd).
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")

    class _Q:
        def __init__(self, table):
            self.table = table

        def select(self, *a, **k):
            return self

        def eq(self, col, val):
            return self

        def execute(self):
            class _R:
                data = []
            if self.table == "scripts":
                _R.data = [{"id": "s1"}]
            elif self.table == "script_members":
                _R.data = [{"script_id": "s2"}]
            elif self.table == "scenes":
                _R.data = [
                    {"setting": "INT. VILLA - 2 7", "int_ext": "INT", "time_of_day": "2 7",
                     "location_hierarchy": None, "location_canonical": None, "is_omitted": False},
                ]
            return _R()

    class _FakeSupa:
        def table(self, name):
            return _Q(name)

    monkeypatch.setattr(sr, "supabase", _FakeSupa())
    resp = _client().get("/api/scripts/locations/health-counts")
    assert resp.status_code != 404
    assert resp.status_code == 200
    body = resp.get_json()
    assert "counts" in body
    assert set(body["counts"].keys()) == {"s1", "s2"}
    assert all(isinstance(v, int) for v in body["counts"].values())
