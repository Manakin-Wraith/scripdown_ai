"""Report data endpoints require auth + owner/member access; share stays public."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.report_routes as rr


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_reports_list_requires_auth(monkeypatch):
    # Force production auth behavior: no bypass, no header -> 401.
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().get("/api/reports/scripts/s1/reports")
    assert resp.status_code == 401


def test_reports_list_forbidden_for_non_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)   # bypass auth layer
    monkeypatch.setattr(rr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(rr, "script_access", lambda c, sid, uid: "forbidden")
    resp = _client().get("/api/reports/scripts/s1/reports")
    assert resp.status_code == 403


def test_reports_list_ok_for_owner(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(rr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(rr, "script_access", lambda c, sid, uid: "ok")
    monkeypatch.setattr(rr.report_service, "get_script_reports", lambda sid: [])
    resp = _client().get("/api/reports/scripts/s1/reports")
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_missing_script_is_404(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(rr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(rr, "script_access", lambda c, sid, uid: "not_found")
    resp = _client().get("/api/reports/scripts/s1/reports")
    assert resp.status_code == 404


def test_shared_route_stays_public(monkeypatch):
    # Public share endpoint must work with NO auth even in production mode.
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    monkeypatch.setattr(rr.report_service, "get_report_by_token", lambda t: None)
    resp = _client().get("/api/reports/shared/sometoken")
    # 404 (token not found) proves the handler ran WITHOUT an auth rejection (not 401).
    assert resp.status_code == 404


def test_print_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().get("/api/reports/reports/r1/print")
    assert resp.status_code == 401


def test_print_forbidden_for_non_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(rr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(rr, "report_script_id", lambda c, rid: "s1")
    monkeypatch.setattr(rr, "script_access", lambda c, sid, uid: "forbidden")
    resp = _client().get("/api/reports/reports/r1/print")
    assert resp.status_code == 403


def test_print_ok_for_owner(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(rr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(rr, "report_script_id", lambda c, rid: "s1")
    monkeypatch.setattr(rr, "script_access", lambda c, sid, uid: "ok")
    monkeypatch.setattr(rr.report_service, "get_report",
                        lambda rid: {"title": "R", "report_type": "scene_breakdown", "data_snapshot": {}})
    monkeypatch.setattr(rr.report_service, "_render_report_html", lambda report: "<html><body>x</body></html>")
    monkeypatch.setattr(rr.report_service, "_get_report_css", lambda: "")
    resp = _client().get("/api/reports/reports/r1/print")
    assert resp.status_code == 200


def test_missing_report_is_404(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(rr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(rr, "report_script_id", lambda c, rid: None)
    resp = _client().get("/api/reports/reports/r1/print")
    assert resp.status_code == 404
