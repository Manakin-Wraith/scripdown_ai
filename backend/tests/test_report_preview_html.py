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


class _FakeTable:
    """Mirrors the subset of the Supabase table builder that report_service.db.client
    uses for persistence (self.db.client.table('reports').insert(...).execute() in
    generate_report). insert() is the real persistence primitive preview must never hit."""

    def __init__(self, calls):
        self._calls = calls

    def insert(self, *a, **k):
        self._calls["insert"] += 1
        raise AssertionError("preview must not persist a report")

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def single(self):
        return self

    def execute(self):
        return type("Result", (), {"data": None})()


class _FakeSupabaseClient:
    def __init__(self, calls):
        self._calls = calls

    def table(self, name):
        return _FakeTable(self._calls)


def test_preview_html_returns_html_and_counts(monkeypatch):
    calls = {"insert": 0}

    monkeypatch.setattr(rr.report_service, "aggregate_scene_data",
                        lambda script_id, filters=None: FAKE_DATA)
    monkeypatch.setattr(rr.report_service, "_render_report_html",
                        lambda report: "<html><body><h1>Preview</h1></body></html>")
    # total_count comes from db.get_scenes (deliberately a longer list than the
    # filtered match_count, so the test distinguishes match vs total).
    monkeypatch.setattr(rr.report_service.db, "get_scenes",
                        lambda script_id: [1, 2, 3, 4, 5])
    # Guard: the real persistence primitive is db.client.table('reports').insert(...)
    # (see generate_report). Swap the whole client so ANY insert during preview fails
    # the test, regardless of which method would have triggered it.
    monkeypatch.setattr(rr.report_service.db, "client", _FakeSupabaseClient(calls))
    # Guard (secondary): generate_report itself must never be called either.
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
    # match_count reflects the filtered summary.total_scenes in FAKE_DATA (3),
    # distinct from total_count which comes from db.get_scenes (5, unfiltered).
    assert body["match_count"] == FAKE_DATA["summary"]["total_scenes"]
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


def test_reports_list_includes_config_and_type(monkeypatch):
    fake_reports = [
        {"id": "r1", "report_type": "scene_breakdown",
         "config": {"filters": {"locations": ["INT. KITCHEN"]}, "group_by": "location"},
         "title": "Wk1", "generated_at": "2026-07-08T00:00:00", "is_public": False},
    ]
    monkeypatch.setattr(rr.report_service, "get_script_reports",
                        lambda script_id: fake_reports)
    from app import app
    app.config["TESTING"] = True
    resp = app.test_client().get("/api/reports/scripts/scr-1/reports")
    assert resp.status_code == 200
    reports = resp.get_json()["reports"]
    assert reports[0]["report_type"] == "scene_breakdown"
    assert reports[0]["config"]["group_by"] == "location"
