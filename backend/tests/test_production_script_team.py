"""Attach/detach: moving a script's own team into a production (spec 2026-09-23)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.production_script_team_service as team
import services.production_member_service as pms
from middleware.auth import DEV_USER_ID
from test_production_member_routes import MockSupabase

FUTURE = "2099-01-01T00:00:00+00:00"
PAST = "2000-01-01T00:00:00+00:00"


def _patch(monkeypatch, store, sent=None):
    mock = MockSupabase(store)
    for target in ("services.production_script_team_service",
                   "services.production_member_service",
                   "services.production_service",
                   "middleware.authorization",
                   "middleware.production_authz"):
        monkeypatch.setattr(f"{target}.get_supabase_admin", lambda: mock)
    monkeypatch.setattr("services.email_service.is_configured", lambda: sent is not None)
    if sent is not None:
        monkeypatch.setattr("services.email_service.send_production_invite",
                            lambda **k: sent.append(("prod_invite", k["to_email"])))
        monkeypatch.setattr("services.email_service.send_production_member_added",
                            lambda **k: sent.append(("member_added", k["to_email"])))
        monkeypatch.setattr("services.email_service.send_invite_revoked",
                            lambda **k: sent.append(("revoked", k["to_email"])))
    return mock


def _store(**ov):
    base = {
        "productions": [{"id": "p1", "owner_id": DEV_USER_ID, "title": "Farm"}],
        "scripts": [{"id": "s1", "user_id": DEV_USER_ID, "production_id": None, "title": "Ep 1"}],
        "script_members": [
            {"id": "sm1", "script_id": "s1", "user_id": "jane", "role": "member",
             "department_code": "camera"},
            {"id": "sm2", "script_id": "s1", "user_id": "tom", "role": "viewer",
             "department_code": "props"},
        ],
        "script_invites": [
            {"id": "si1", "script_id": "s1", "email": "new@x.com", "role": "admin",
             "status": "pending", "expires_at": FUTURE},
            {"id": "si2", "script_id": "s1", "email": "old@x.com", "role": "member",
             "status": "pending", "expires_at": PAST},
        ],
        "production_members": [], "production_invites": [], "notifications": [],
        "profiles": [{"id": DEV_USER_ID, "email": "dev@example.com", "full_name": "Owner"},
                     {"id": "jane", "email": "jane@x.com", "full_name": "Jane"},
                     {"id": "tom", "email": "tom@x.com", "full_name": "Tom"}],
    }
    base.update(ov)
    return base


def test_load_script_team_splits_live_and_expired(monkeypatch):
    _patch(monkeypatch, _store())
    members, live, expired = team.load_script_team("s1")
    assert {m["user_id"] for m in members} == {"jane", "tom"}
    assert [i["id"] for i in live] == ["si1"]
    assert [i["id"] for i in expired] == ["si2"]


def test_describe_script_team_names_people(monkeypatch):
    _patch(monkeypatch, _store())
    members, live, _ = team.load_script_team("s1")
    out = team.describe_script_team(members, live)
    assert {m["name"] for m in out["members"]} == {"Jane", "Tom"}
    assert out["invites"] == [{"email": "new@x.com", "role": "admin"}]


def test_move_creates_viewer_members_with_mapped_access(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    out = team.move_script_team_to_production("p1", "s1", DEV_USER_ID)
    pm = {r["user_id"]: r for r in store["production_members"]}
    assert pm["jane"]["role"] == "viewer" and pm["jane"]["script_access"] == "edit"
    assert pm["tom"]["script_access"] == "view"
    assert pm["jane"]["can_edit_crew"] is False
    assert store["script_members"] == []
    assert out == {"moved_members": 2, "moved_invites": 1}


def test_move_raises_but_never_lowers_existing_member(monkeypatch):
    store = _store(production_members=[
        {"id": "pm1", "production_id": "p1", "user_id": "jane", "role": "coordinator",
         "script_access": "view"},
        {"id": "pm2", "production_id": "p1", "user_id": "tom", "role": "admin",
         "script_access": "edit"},
    ])
    _patch(monkeypatch, store)
    team.move_script_team_to_production("p1", "s1", DEV_USER_ID)
    pm = {r["user_id"]: r for r in store["production_members"]}
    assert pm["jane"]["script_access"] == "edit" and pm["jane"]["role"] == "coordinator"
    assert pm["tom"]["script_access"] == "edit" and pm["tom"]["role"] == "admin"


def test_move_converts_live_invites_silently_revokes_script_invite(monkeypatch):
    store = _store()
    sent = []
    _patch(monkeypatch, store, sent)
    team.move_script_team_to_production("p1", "s1", DEV_USER_ID)
    [pi] = store["production_invites"]
    assert pi["email"] == "new@x.com" and pi["role"] == "viewer"
    assert pi["script_access"] == "edit" and pi["status"] == "pending"
    status = {i["id"]: i["status"] for i in store["script_invites"]}
    assert status == {"si1": "revoked", "si2": "revoked"}
    assert ("prod_invite", "new@x.com") in sent
    assert not any(kind == "revoked" for kind, _ in sent)


def test_move_raises_existing_pending_production_invite(monkeypatch):
    store = _store(production_invites=[
        {"id": "pi1", "production_id": "p1", "email": "NEW@x.com", "role": "viewer",
         "status": "pending", "script_access": "view", "expires_at": FUTURE}])
    _patch(monkeypatch, store)
    team.move_script_team_to_production("p1", "s1", DEV_USER_ID)
    assert len(store["production_invites"]) == 1
    assert store["production_invites"][0]["script_access"] == "edit"


def test_move_is_idempotent(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    team.move_script_team_to_production("p1", "s1", DEV_USER_ID)
    team.move_script_team_to_production("p1", "s1", DEV_USER_ID)
    assert len(store["production_members"]) == 2
    assert len(store["production_invites"]) == 1


def test_move_ignores_seat_and_tier_gates(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    def _boom(uid):
        raise AssertionError("move must not consult entitlements")
    monkeypatch.setattr(pms, "get_entitlement", _boom)
    team.move_script_team_to_production("p1", "s1", DEV_USER_ID)
    assert len(store["production_members"]) == 2


def test_drop_deletes_members_and_revokes_with_email(monkeypatch):
    store = _store()
    sent = []
    _patch(monkeypatch, store, sent)
    team.drop_script_team("s1", DEV_USER_ID)
    assert store["script_members"] == []
    assert store["production_members"] == []
    assert {i["status"] for i in store["script_invites"]} == {"revoked"}
    assert ("revoked", "new@x.com") in sent
    assert ("revoked", "old@x.com") not in sent   # expired: silent


def test_keep_members_on_script_maps_roles(monkeypatch):
    store = _store(script_members=[], production_members=[
        {"id": "pm1", "production_id": "p1", "user_id": "jane", "role": "viewer",
         "script_access": "edit"},
        {"id": "pm2", "production_id": "p1", "user_id": "tom", "role": "viewer",
         "script_access": "none"},
    ])
    _patch(monkeypatch, store)
    kept = team.keep_members_on_script("p1", "s1", ["jane", "tom", "ghost"], DEV_USER_ID)
    assert kept == 1
    [row] = store["script_members"]
    assert row["user_id"] == "jane" and row["role"] == "member"
    assert row["invited_by"] == DEV_USER_ID
