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
