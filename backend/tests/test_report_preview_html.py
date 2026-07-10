"""preview-html renders report HTML from unsaved config without persisting."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import routes.report_routes as rr


FAKE_DATA = {
    "script": {"title": "Midnight Run"},
    "summary": {"total_scenes": 3},
    "scenes": [1, 2, 3],
}


def test_preview_html_returns_html_and_counts(monkeypatch):
    calls = {"insert": 0}

    monkeypatch.setattr(rr.report_service, "aggregate_scene_data",
                        lambda script_id, filters=None: FAKE_DATA)
    monkeypatch.setattr(rr.report_service, "_render_report_html",
                        lambda report: "<html><body><h1>Preview</h1></body></html>")
    # total_count comes from db.get_scenes
    monkeypatch.setattr(rr.report_service.db, "get_scenes",
                        lambda script_id: [1, 2, 3, 4, 5])
    # Guard: generating/persisting must never happen on preview
    def _boom(*a, **k):
        calls["insert"] += 1
        raise AssertionError("preview must not persist a report")
    monkeypatch.setattr(rr.report_service, "generate_report", _boom)

    from app import app
    app.config["TESTING"] = True
    resp = app.test_client().post(
        "/api/reports/scripts/scr-1/reports/preview-html",
        json={"report_type": "scene_breakdown", "filters": {"locations": ["INT. KITCHEN"]}},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert "<h1>Preview</h1>" in body["html"]
    assert body["match_count"] == 3
    assert body["total_count"] == 5
    assert calls["insert"] == 0


def test_preview_html_invalid_type_returns_400(monkeypatch):
    from app import app
    app.config["TESTING"] = True
    resp = app.test_client().post(
        "/api/reports/scripts/scr-1/reports/preview-html",
        json={"report_type": "not_a_type"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False
