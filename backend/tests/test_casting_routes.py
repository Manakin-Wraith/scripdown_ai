# backend/tests/test_casting_routes.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
import routes.casting_routes as cr
import middleware.authorization as authz


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture(autouse=True)
def _bypass_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(cr, "get_user_id", lambda: "u1")


def _as_role(monkeypatch, role):
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: role)


def test_list_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    assert _client().get("/api/scripts/s1/casting").status_code == 401


def test_list_forbidden_for_non_member(monkeypatch):
    _as_role(monkeypatch, None)
    assert _client().get("/api/scripts/s1/casting").status_code == 403


def test_list_ok_for_viewer(monkeypatch):
    _as_role(monkeypatch, "viewer")
    monkeypatch.setattr(cr.casting_service, "list_casting", lambda sid: [])
    monkeypatch.setattr(cr.casting_service, "breakdown_characters", lambda sid: {"JOHN": 3})
    resp = _client().get("/api/scripts/s1/casting")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["characters"] == [{"name": "JOHN", "scene_count": 3, "casting_id": None}]
    assert body["casting"] == []


def test_list_omits_contact_for_viewer(monkeypatch):
    _as_role(monkeypatch, "viewer")
    monkeypatch.setattr(cr.casting_service, "list_casting", lambda sid: [
        {"id": "c1", "script_id": "s1", "character_name": "JOHN",
         "actor_name": "Jon", "status": "booked", "contact_phone": "0821",
         "headshot_path": None, "notes": None, "unavailability": []},
    ])
    monkeypatch.setattr(cr.casting_service, "breakdown_characters", lambda sid: {"JOHN": 3})
    monkeypatch.setattr(cr.casting_service, "_headshot_url", lambda p: None)
    body = _client().get("/api/scripts/s1/casting").get_json()
    assert "contact_phone" not in body["casting"][0]


def test_list_includes_contact_for_admin(monkeypatch):
    _as_role(monkeypatch, "admin")
    monkeypatch.setattr(cr.casting_service, "list_casting", lambda sid: [
        {"id": "c1", "script_id": "s1", "character_name": "JOHN",
         "actor_name": "Jon", "status": "booked", "contact_phone": "0821",
         "headshot_path": None, "notes": None, "unavailability": []},
    ])
    monkeypatch.setattr(cr.casting_service, "breakdown_characters", lambda sid: {"JOHN": 3})
    monkeypatch.setattr(cr.casting_service, "_headshot_url", lambda p: None)
    body = _client().get("/api/scripts/s1/casting").get_json()
    assert body["casting"][0]["contact_phone"] == "0821"


def test_create_forbidden_for_member(monkeypatch):
    _as_role(monkeypatch, "member")
    resp = _client().post("/api/scripts/s1/casting", json={"character_name": "JOHN"})
    assert resp.status_code == 403


def test_create_ok_for_admin(monkeypatch):
    _as_role(monkeypatch, "admin")
    monkeypatch.setattr(cr.casting_service, "create_casting",
                        lambda sid, name, uid: {"id": "c1", "script_id": sid,
                        "character_name": "JOHN", "status": "wishlist",
                        "actor_name": None, "headshot_path": None, "notes": None,
                        "unavailability": []})
    monkeypatch.setattr(cr.casting_service, "_headshot_url", lambda p: None)
    resp = _client().post("/api/scripts/s1/casting", json={"character_name": "john"})
    assert resp.status_code == 201
    assert resp.get_json()["casting"]["character_name"] == "JOHN"


def test_create_conflict_returns_409(monkeypatch):
    _as_role(monkeypatch, "admin")
    def _boom(sid, name, uid): raise cr.casting_service.CastingConflict(name)
    monkeypatch.setattr(cr.casting_service, "create_casting", _boom)
    resp = _client().post("/api/scripts/s1/casting", json={"character_name": "JOHN"})
    assert resp.status_code == 409


def test_patch_ok_for_admin(monkeypatch):
    _as_role(monkeypatch, "admin")
    monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")
    monkeypatch.setattr(cr.casting_service, "update_casting",
                        lambda cid, fields: {"id": cid, "script_id": "s1",
                        "character_name": "JOHN", "status": fields.get("status", "wishlist"),
                        "actor_name": fields.get("actor_name"), "headshot_path": None,
                        "notes": None, "unavailability": []})
    monkeypatch.setattr(cr.casting_service, "_headshot_url", lambda p: None)
    resp = _client().patch("/api/casting/c1", json={"status": "booked"})
    assert resp.status_code == 200
    assert resp.get_json()["casting"]["status"] == "booked"


def test_delete_ok_for_admin(monkeypatch):
    _as_role(monkeypatch, "admin")
    monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")
    monkeypatch.setattr(cr.casting_service, "delete_casting", lambda cid: {"id": cid, "headshot_path": None})
    resp = _client().delete("/api/casting/c1")
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
