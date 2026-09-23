"""Production membership → script access (spec 2026-09-23)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import middleware.production_authz as pauthz
from middleware.production_authz import (
    SCRIPT_ACCESS_RANK, SCRIPT_ACCESS_TO_ROLE, SCRIPT_ROLE_TO_ACCESS,
    get_production_access,
)
from test_production_member_routes import MockSupabase


def _patch_pauthz(monkeypatch, store):
    mock = MockSupabase(store)
    monkeypatch.setattr(pauthz, "get_supabase_admin", lambda: mock)
    return mock


def test_script_access_constants():
    assert SCRIPT_ACCESS_RANK == {'none': 0, 'view': 1, 'edit': 2}
    assert SCRIPT_ACCESS_TO_ROLE == {'view': 'viewer', 'edit': 'member'}
    assert SCRIPT_ROLE_TO_ACCESS == {'viewer': 'view', 'member': 'edit', 'admin': 'edit'}


def test_production_access_owner_has_edit_script_access(monkeypatch):
    _patch_pauthz(monkeypatch, {"productions": [{"id": "p1", "owner_id": "o"}]})
    assert get_production_access("p1", "o")["script_access"] == "edit"


def test_production_access_member_script_access_from_row(monkeypatch):
    _patch_pauthz(monkeypatch, {
        "productions": [{"id": "p1", "owner_id": "o"}],
        "production_members": [{"production_id": "p1", "user_id": "u", "role": "viewer",
                                "script_access": "view"}],
    })
    assert get_production_access("p1", "u")["script_access"] == "view"


def test_production_access_member_missing_column_defaults_none(monkeypatch):
    _patch_pauthz(monkeypatch, {
        "productions": [{"id": "p1", "owner_id": "o"}],
        "production_members": [{"production_id": "p1", "user_id": "u", "role": "viewer"}],
    })
    assert get_production_access("p1", "u")["script_access"] == "none"


import middleware.authorization as authz
from middleware.authorization import (
    get_script_role, SCRIPT_NOT_FOUND, production_derived_role, production_script_roles,
)


def _patch_authz(monkeypatch, store):
    mock = MockSupabase(store)
    monkeypatch.setattr(authz, "get_supabase_admin", lambda: mock)
    return mock


def _prod_store(access, script_production="p1", direct=None):
    store = {
        "scripts": [{"id": "s1", "user_id": "owner", "production_id": script_production}],
        "production_members": [{"production_id": "p1", "user_id": "u", "role": "viewer",
                                "script_access": access}],
        "script_members": [],
    }
    if direct:
        store["script_members"].append({"script_id": "s1", "user_id": "u", "role": direct})
    return store


def test_production_edit_maps_to_member(monkeypatch):
    _patch_authz(monkeypatch, _prod_store("edit"))
    assert get_script_role("s1", "u") == "member"


def test_production_view_maps_to_viewer(monkeypatch):
    _patch_authz(monkeypatch, _prod_store("view"))
    assert get_script_role("s1", "u") == "viewer"


def test_production_none_gives_no_access(monkeypatch):
    _patch_authz(monkeypatch, _prod_store("none"))
    assert get_script_role("s1", "u") is None


def test_standalone_script_ignores_production_rows(monkeypatch):
    _patch_authz(monkeypatch, _prod_store("edit", script_production=None))
    assert get_script_role("s1", "u") is None


def test_direct_and_production_higher_wins(monkeypatch):
    _patch_authz(monkeypatch, _prod_store("view", direct="member"))
    assert get_script_role("s1", "u") == "member"
    _patch_authz(monkeypatch, _prod_store("edit", direct="viewer"))
    assert get_script_role("s1", "u") == "member"


def test_direct_admin_beats_production_edit(monkeypatch):
    _patch_authz(monkeypatch, _prod_store("edit", direct="admin"))
    assert get_script_role("s1", "u") == "admin"


def test_removed_member_loses_access(monkeypatch):
    store = _prod_store("edit")
    store["production_members"] = []
    _patch_authz(monkeypatch, store)
    assert get_script_role("s1", "u") is None


def test_owner_still_owner_and_missing_still_sentinel(monkeypatch):
    _patch_authz(monkeypatch, _prod_store("edit"))
    assert get_script_role("s1", "owner") == "owner"
    assert get_script_role("nope", "u") is SCRIPT_NOT_FOUND


def test_production_derived_role_helper(monkeypatch):
    mock = _patch_authz(monkeypatch, _prod_store("view"))
    assert production_derived_role(mock, "p1", "u") == "viewer"
    assert production_derived_role(mock, None, "u") is None
    assert production_derived_role(mock, "p1", "stranger") is None


def test_production_script_roles_lists_reachable_scripts(monkeypatch):
    mock = _patch_authz(monkeypatch, {
        "production_members": [
            {"production_id": "p1", "user_id": "u", "script_access": "edit"},
            {"production_id": "p2", "user_id": "u", "script_access": "none"},
        ],
        "scripts": [
            {"id": "s1", "user_id": "owner", "production_id": "p1"},
            {"id": "s2", "user_id": "owner", "production_id": "p2"},
            {"id": "s3", "user_id": "u", "production_id": "p1"},   # own script — excluded
        ],
    })
    assert production_script_roles(mock, "u") == {"s1": "member"}


def test_production_script_roles_empty_when_no_memberships(monkeypatch):
    mock = _patch_authz(monkeypatch, {"production_members": [], "scripts": []})
    assert production_script_roles(mock, "u") == {}


import services.production_member_service as pms_task3
from middleware.auth import DEV_USER_ID


def test_resolve_script_access_defaults_and_overrides():
    assert pms_task3.resolve_script_access("admin", {}) == "edit"
    assert pms_task3.resolve_script_access("coordinator", None) == "edit"
    assert pms_task3.resolve_script_access("viewer", {}) == "view"
    assert pms_task3.resolve_script_access("viewer", {"script_access": "none"}) == "none"
    assert pms_task3.resolve_script_access("viewer", {"script_access": "bogus"}) is None
    assert pms_task3.resolve_script_access("admin", {}, current="view") == "view"


def test_script_access_ok():
    assert pms_task3.script_access_ok({"role": "owner"}, "edit") is True
    assert pms_task3.script_access_ok({"role": "admin", "script_access": "view"}, "edit") is False
    assert pms_task3.script_access_ok({"role": "admin", "script_access": "edit"}, "edit") is True
    assert pms_task3.script_access_ok({"role": "admin"}, "view") is False   # missing → none


def _svc_patch(monkeypatch, store):
    mock = MockSupabase(store)
    monkeypatch.setattr(pms_task3, "get_supabase_admin", lambda: mock)
    monkeypatch.setattr(pms_task3, "get_entitlement", lambda uid: {
        "can_use_teams": True, "seats_used": 0, "seats_paid": 10})
    monkeypatch.setattr("services.email_service.is_configured", lambda: False)
    return mock


def _base_store(**ov):
    base = {"productions": [{"id": "p1", "owner_id": DEV_USER_ID, "title": "Farm"}],
            "production_members": [], "production_invites": [], "notifications": [],
            "profiles": [{"id": DEV_USER_ID, "email": "dev@example.com"},
                         {"id": "u2", "email": "jane@x.com", "full_name": "Jane"}]}
    base.update(ov)
    return base


OWNER = {"role": "owner"}


def test_add_member_uses_role_default_script_access(monkeypatch):
    store = _base_store()
    _svc_patch(monkeypatch, store)
    out = pms_task3.add_member("p1", DEV_USER_ID, OWNER, {"email": "jane@x.com", "role": "viewer"})
    assert out["member"]["script_access"] == "view"
    assert store["production_members"][0]["script_access"] == "view"


def test_add_member_explicit_script_access(monkeypatch):
    store = _base_store()
    _svc_patch(monkeypatch, store)
    pms_task3.add_member("p1", DEV_USER_ID, OWNER,
                   {"email": "jane@x.com", "role": "admin", "script_access": "none"})
    assert store["production_members"][0]["script_access"] == "none"


def test_add_member_bad_script_access(monkeypatch):
    _svc_patch(monkeypatch, _base_store())
    out = pms_task3.add_member("p1", DEV_USER_ID, OWNER,
                         {"email": "jane@x.com", "role": "viewer", "script_access": "all"})
    assert out == ("error", "bad_script_access", 400)


def test_add_member_rank_denied_above_own_script_access(monkeypatch):
    _svc_patch(monkeypatch, _base_store())
    actor = {"role": "admin", "script_access": "view", "can_manage_members": True}
    out = pms_task3.add_member("p1", "actor", actor,
                         {"email": "jane@x.com", "role": "viewer", "script_access": "edit"})
    assert out == ("error", "rank_denied", 403)


def test_invite_carries_script_access(monkeypatch):
    store = _base_store()
    _svc_patch(monkeypatch, store)
    out = pms_task3.add_member("p1", DEV_USER_ID, OWNER, {"email": "new@x.com", "role": "coordinator"})
    assert out["invite"]["script_access"] == "edit"
    assert store["production_invites"][0]["script_access"] == "edit"


def test_update_member_role_change_keeps_script_access(monkeypatch):
    store = _base_store(production_members=[{
        "id": "m1", "production_id": "p1", "user_id": "u2", "role": "viewer",
        "script_access": "none"}])
    _svc_patch(monkeypatch, store)
    out = pms_task3.update_member("p1", "m1", DEV_USER_ID, OWNER, {"role": "coordinator"})
    assert out["member"]["script_access"] == "none"


def test_update_member_sets_script_access(monkeypatch):
    store = _base_store(production_members=[{
        "id": "m1", "production_id": "p1", "user_id": "u2", "role": "viewer",
        "script_access": "view"}])
    _svc_patch(monkeypatch, store)
    out = pms_task3.update_member("p1", "m1", DEV_USER_ID, OWNER, {"script_access": "edit"})
    assert out["member"]["script_access"] == "edit"


def test_update_member_unchanged_script_access_not_rank_checked(monkeypatch):
    # Actor holds only 'view' but is not changing the member's 'edit'.
    store = _base_store(production_members=[{
        "id": "m1", "production_id": "p1", "user_id": "u2", "role": "viewer",
        "script_access": "edit"}])
    _svc_patch(monkeypatch, store)
    actor = {"role": "admin", "script_access": "view", "can_manage_members": True}
    out = pms_task3.update_member("p1", "m1", "actor", actor, {"role": "viewer"})
    assert not isinstance(out, tuple)


def test_accept_invite_copies_script_access(monkeypatch):
    store = _base_store(production_invites=[{
        "id": "i1", "production_id": "p1", "email": "jane@x.com", "role": "viewer",
        "token": "t", "status": "pending", "expires_at": "2099-01-01T00:00:00+00:00",
        "script_access": "edit"}])
    _svc_patch(monkeypatch, store)
    pms_task3.accept_invite("t", "u2", "jane@x.com")
    assert store["production_members"][0]["script_access"] == "edit"
