"""analysis_routes.py had no auth at all (see docs/BACKLOG.md, found 2026-07-18):
any anonymous caller who knew/guessed a script_id could read that script's
character breakdown / story-arc and cancel its in-progress analysis. Every
route in this blueprint must now require auth + script access."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.analysis_routes as ar


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


ROUTES = [
    ("GET", "/api/analysis/status"),
    ("GET", "/api/scripts/1/analysis/status"),
    ("POST", "/api/scripts/1/analysis/cancel"),
    ("GET", "/api/scripts/1/analysis/characters"),
    ("GET", "/api/scripts/1/analysis/characters/JOHN"),
    ("GET", "/api/scripts/1/analysis/story-arc"),
]


def test_all_routes_reject_anonymous_callers(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    client = _client()
    for method, path in ROUTES:
        resp = client.open(path, method=method)
        assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}, expected 401"


def test_script_scoped_routes_reject_non_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(ar, "get_user_id", lambda: "u2")
    monkeypatch.setattr(ar, "_user_can_access_script", lambda sid, uid: False)
    client = _client()
    for method, path in ROUTES:
        if path == "/api/analysis/status":
            continue  # global endpoint, not script-scoped
        resp = client.open(path, method=method)
        assert resp.status_code == 403, f"{method} {path} returned {resp.status_code}, expected 403"


def test_script_status_ok_for_authorized_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(ar, "get_user_id", lambda: "u1")
    monkeypatch.setattr(ar, "_user_can_access_script", lambda sid, uid: True)
    monkeypatch.setattr(ar, "get_script_analysis_status", lambda sid: {"status": "complete"})
    resp = _client().get("/api/scripts/1/analysis/status")
    assert resp.status_code == 200
    assert resp.get_json()["data"] == {"status": "complete"}
