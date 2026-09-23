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
