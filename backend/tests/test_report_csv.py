"""CSV export: route auth/access mirrors the PDF route, service builds correct rows per type."""
import csv
import io
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.report_routes as rr
import middleware.authorization as authz
from services.report_service import report_service


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def _rows(csv_text):
    reader = csv.reader(io.StringIO(csv_text))
    all_rows = list(reader)
    return all_rows[0], all_rows[1:]


# ============================================
# Route: auth / access / errors
# ============================================

def test_csv_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().get("/api/reports/reports/r1/csv")
    assert resp.status_code == 401


def test_csv_forbidden_for_non_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(rr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(rr, "report_script_id", lambda c, rid: "s1")
    monkeypatch.setattr(rr, "script_access", lambda c, sid, uid: "forbidden")
    monkeypatch.setattr(authz, "_lookup_script_id", lambda table, id_value, **k: "s1")
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: None)
    resp = _client().get("/api/reports/reports/r1/csv")
    assert resp.status_code == 403


def test_csv_ok_for_owner(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(rr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(rr, "report_script_id", lambda c, rid: "s1")
    monkeypatch.setattr(rr, "script_access", lambda c, sid, uid: "ok")
    monkeypatch.setattr(authz, "_lookup_script_id", lambda table, id_value, **k: "s1")
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: "owner")
    monkeypatch.setattr(rr.report_service, "get_report", lambda rid: {
        "id": rid, "title": "My Report", "report_type": "props", "data_snapshot": {"props": {}}
    })
    resp = _client().get("/api/reports/reports/r1/csv")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert 'filename="My_Report.csv"' in resp.headers["Content-Disposition"]


def test_csv_missing_report_is_404(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(rr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(rr, "report_script_id", lambda c, rid: None)
    monkeypatch.setattr(authz, "_lookup_script_id", lambda table, id_value, **k: None)
    resp = _client().get("/api/reports/reports/r1/csv")
    assert resp.status_code == 404


def test_csv_unsupported_type_is_400(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(rr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(rr, "report_script_id", lambda c, rid: "s1")
    monkeypatch.setattr(rr, "script_access", lambda c, sid, uid: "ok")
    monkeypatch.setattr(authz, "_lookup_script_id", lambda table, id_value, **k: "s1")
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: "owner")
    monkeypatch.setattr(rr.report_service, "get_report", lambda rid: {
        "id": rid, "title": "Full", "report_type": "full_breakdown", "data_snapshot": {}
    })
    resp = _client().get("/api/reports/reports/r1/csv")
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False


def test_shared_csv_ok(monkeypatch):
    report = {
        "id": "r1", "title": "Shared Report", "report_type": "location", "data_snapshot": {"locations": {}}
    }
    monkeypatch.setattr(rr.report_service, "get_report_by_token", lambda t: report)
    # generate_csv() re-fetches by id internally, same as generate_pdf() does for the PDF route.
    monkeypatch.setattr(rr.report_service, "get_report", lambda rid: report)
    resp = _client().get("/api/reports/shared/tok123/csv")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"


def test_shared_csv_missing_is_404(monkeypatch):
    monkeypatch.setattr(rr.report_service, "get_report_by_token", lambda t: None)
    resp = _client().get("/api/reports/shared/tok123/csv")
    assert resp.status_code == 404


# ============================================
# Service: generate_csv row shape per report type
# ============================================

def test_generate_csv_report_not_found(monkeypatch):
    monkeypatch.setattr(report_service, "get_report", lambda rid: None)
    try:
        report_service.generate_csv("missing")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_generate_csv_scene_breakdown(monkeypatch):
    report = {
        "id": "r1",
        "title": "Scene Breakdown",
        "report_type": "scene_breakdown",
        "data_snapshot": {
            "scenes": [
                {
                    "id": "sc1", "scene_number": "1", "int_ext": "INT", "setting": "KITCHEN",
                    "time_of_day": "DAY", "story_day": 1, "page_length_eighths": 8,
                    "characters": ["JOHN", "MARY"], "props": ["Knife"], "description": "John cooks.",
                },
            ],
            "user_items_by_scene": {},
        },
    }
    monkeypatch.setattr(report_service, "get_report", lambda rid: report)
    headers, rows = _rows(report_service.generate_csv("r1"))
    assert headers[0] == "Scene"
    assert len(rows) == 1
    assert rows[0][0] == "1"
    assert rows[0][1] == "INT"
    assert rows[0][2] == "KITCHEN"
    assert "JOHN" in rows[0][6] and "MARY" in rows[0][6]
    assert rows[0][7] == "Knife"


def test_generate_csv_one_liner_from_scenes(monkeypatch):
    report = {
        "id": "r1", "title": "One Liner", "report_type": "one_liner",
        "data_snapshot": {
            "scenes": [
                {"scene_number": "2", "int_ext": "EXT", "setting": "PARK", "time_of_day": "NIGHT",
                 "story_day": 2, "page_length_eighths": 4, "characters": ["ANNA"]},
            ],
            # no 'days' key -> falls back to scene-based rendering
        },
    }
    monkeypatch.setattr(report_service, "get_report", lambda rid: report)
    headers, rows = _rows(report_service.generate_csv("r1"))
    assert headers[2] == "Scene"
    assert len(rows) == 1
    assert rows[0][2] == "2"
    assert rows[0][6] == "D2"
    assert rows[0][7] == "ANNA"


def test_generate_csv_one_liner_from_days(monkeypatch):
    report = {
        "id": "r1", "title": "One Liner", "report_type": "one_liner",
        "data_snapshot": {
            "scenes": [],
            "days": [
                {"day_number": 1, "shoot_date": "2026-08-01", "scenes": [
                    {"scene_number": "1", "int_ext": "INT", "setting": "OFFICE", "time_of_day": "DAY",
                     "page_length_eighths": 8, "characters": ["BOB"]},
                ]},
            ],
        },
    }
    monkeypatch.setattr(report_service, "get_report", lambda rid: report)
    headers, rows = _rows(report_service.generate_csv("r1"))
    assert len(rows) == 1
    assert rows[0][0] == "1"  # day number
    assert rows[0][1] == "2026-08-01"
    assert rows[0][7] == "BOB"


def test_generate_csv_shooting_schedule_no_days_is_empty(monkeypatch):
    report = {
        "id": "r1", "title": "Shooting Schedule", "report_type": "shooting_schedule",
        "data_snapshot": {"scenes": []},
    }
    monkeypatch.setattr(report_service, "get_report", lambda rid: report)
    headers, rows = _rows(report_service.generate_csv("r1"))
    assert headers == ["Day", "Date", "Scene", "INT/EXT", "Setting", "Time", "Length", "Cast"]
    assert rows == []


def test_generate_csv_day_out_of_days_from_scenes(monkeypatch):
    report = {
        "id": "r1", "title": "DOOD", "report_type": "day_out_of_days",
        "data_snapshot": {
            "characters": {
                "JOHN": {"count": 3, "scenes": ["1", "2", "3"], "story_days": [1, 2]},
            },
        },
    }
    monkeypatch.setattr(report_service, "get_report", lambda rid: report)
    headers, rows = _rows(report_service.generate_csv("r1"))
    assert headers == ["Character", "Scenes", "Pages", "Story Days", "Scene Numbers"]
    assert rows[0][0] == "JOHN"
    assert rows[0][1] == "3"
    assert rows[0][3] == "D1, D2"


def test_generate_csv_location_report(monkeypatch):
    report = {
        "id": "r1", "title": "Locations", "report_type": "location",
        "data_snapshot": {
            "locations": {
                "KITCHEN": {"count": 2, "scenes": ["1", "3"], "int_ext": ["INT"], "time_of_day": ["DAY"], "story_days": [1]},
            },
        },
    }
    monkeypatch.setattr(report_service, "get_report", lambda rid: report)
    headers, rows = _rows(report_service.generate_csv("r1"))
    assert headers[0] == "Location"
    assert rows[0][0] == "KITCHEN"
    assert rows[0][1] == "INT"
    assert rows[0][3] == "2"


def test_generate_csv_props_report(monkeypatch):
    report = {
        "id": "r1", "title": "Props", "report_type": "props",
        "data_snapshot": {
            "props": {"Knife": {"count": 1, "scenes": ["1"], "story_days": []}},
        },
    }
    monkeypatch.setattr(report_service, "get_report", lambda rid: report)
    headers, rows = _rows(report_service.generate_csv("r1"))
    assert headers == ["Prop", "Appearances", "Story Days", "Scenes"]
    assert rows[0] == ["Knife", "1", "", "1"]


def test_generate_csv_wardrobe_report(monkeypatch):
    report = {
        "id": "r1", "title": "Wardrobe", "report_type": "wardrobe",
        "data_snapshot": {
            "wardrobe": {"Red Dress": {"count": 2, "scenes": ["1", "2"], "characters": ["MARY"]}},
        },
    }
    monkeypatch.setattr(report_service, "get_report", lambda rid: report)
    headers, rows = _rows(report_service.generate_csv("r1"))
    assert headers == ["Item", "Character(s)", "Appearances", "Scenes"]
    assert rows[0] == ["Red Dress", "MARY", "2", "1, 2"]


def test_generate_csv_rejects_full_breakdown(monkeypatch):
    report = {"id": "r1", "title": "Full", "report_type": "full_breakdown", "data_snapshot": {}}
    monkeypatch.setattr(report_service, "get_report", lambda rid: report)
    try:
        report_service.generate_csv("r1")
        assert False, "expected ValueError"
    except ValueError:
        pass
