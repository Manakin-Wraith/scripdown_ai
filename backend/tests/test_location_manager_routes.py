"""Location manager endpoints require auth + owner/member access."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.supabase_routes as sr


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_rename_parent_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().post("/api/scripts/s1/locations/rename-parent",
                          json={"from_canonical": "VILLA", "to_name": "SMITH RESIDENCE"})
    assert resp.status_code == 401


def test_rename_parent_forbidden_for_non_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: False)
    resp = _client().post("/api/scripts/s1/locations/rename-parent",
                          json={"from_canonical": "VILLA", "to_name": "SMITH RESIDENCE"})
    assert resp.status_code == 403


def test_rename_parent_ok_calls_helper(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    monkeypatch.setattr(sr, "_rename_parent", lambda script_id, frm, to, uid: 4)
    resp = _client().post("/api/scripts/s1/locations/rename-parent",
                          json={"from_canonical": "VILLA", "to_name": "SMITH RESIDENCE"})
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "scenes_updated": 4}


def test_rename_parent_validates_body(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    resp = _client().post("/api/scripts/s1/locations/rename-parent", json={"to_name": "X"})
    assert resp.status_code == 400


def test_rename_sub_forbidden_for_non_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: False)
    resp = _client().post("/api/scripts/s1/locations/rename-sub",
                          json={"parent_canonical": "VILLA", "from_sub": "POOL", "to_sub": "SWIMMING POOL"})
    assert resp.status_code == 403


def test_rename_sub_ok_calls_helper(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    monkeypatch.setattr(sr, "_rename_sub", lambda script_id, parent, frm, to, uid: 2)
    resp = _client().post("/api/scripts/s1/locations/rename-sub",
                          json={"parent_canonical": "VILLA", "from_sub": "POOL", "to_sub": "SWIMMING POOL"})
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "scenes_updated": 2}


def test_rename_sub_validates_body(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    resp = _client().post("/api/scripts/s1/locations/rename-sub",
                          json={"parent_canonical": "VILLA", "from_sub": "POOL"})
    assert resp.status_code == 400
