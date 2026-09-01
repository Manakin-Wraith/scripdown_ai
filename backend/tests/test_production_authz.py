"""Tests for the production-axis authorization primitive.

MockSupabase is the same chainable in-memory stand-in used across the
production test suite (copied from test_production_crew_routes.py).
"""
import os, sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import middleware.production_authz as pa
from middleware.auth import DEV_USER_ID


class MockTable:
    def __init__(self, name, store):
        self.name, self.store = name, store
        self._filters, self._limit = {}, None

    def select(self, *_a, **_k): return self
    def eq(self, c, v): self._filters[c] = v; return self
    def limit(self, n): self._limit = n; return self

    def execute(self):
        rows = [r for r in self.store.get(self.name, [])
                if all(r.get(k) == v for k, v in self._filters.items())]
        if self._limit is not None:
            rows = rows[:self._limit]
        return SimpleNamespace(data=rows)


class MockSupabase:
    def __init__(self, store): self.store = store
    def table(self, name): return MockTable(name, self.store)


def _patch(monkeypatch, store):
    mock = MockSupabase(store)
    monkeypatch.setattr(pa, "get_supabase_admin", lambda: mock)
    return mock


def test_role_owner(monkeypatch):
    _patch(monkeypatch, {"productions": [{"id": "p1", "owner_id": DEV_USER_ID}],
                         "production_members": []})
    assert pa.get_production_role("p1", DEV_USER_ID) == "owner"


def test_role_member(monkeypatch):
    _patch(monkeypatch, {
        "productions": [{"id": "p1", "owner_id": "other"}],
        "production_members": [{"production_id": "p1", "user_id": DEV_USER_ID, "role": "coordinator"}],
    })
    assert pa.get_production_role("p1", DEV_USER_ID) == "coordinator"


def test_role_non_member_is_none(monkeypatch):
    _patch(monkeypatch, {"productions": [{"id": "p1", "owner_id": "other"}],
                         "production_members": []})
    assert pa.get_production_role("p1", DEV_USER_ID) is None


def test_role_missing_production(monkeypatch):
    _patch(monkeypatch, {"productions": [], "production_members": []})
    assert pa.get_production_role("nope", DEV_USER_ID) is pa.PRODUCTION_NOT_FOUND


def test_access_owner_is_all_true(monkeypatch):
    _patch(monkeypatch, {"productions": [{"id": "p1", "owner_id": DEV_USER_ID}],
                         "production_members": []})
    acc = pa.get_production_access("p1", DEV_USER_ID)
    assert acc == {"role": "owner", "can_view_sensitive": True, "can_edit_crew": True,
                   "can_manage_members": True, "can_edit_production": True}


def test_access_member_returns_stored_flags(monkeypatch):
    _patch(monkeypatch, {
        "productions": [{"id": "p1", "owner_id": "other"}],
        "production_members": [{"production_id": "p1", "user_id": DEV_USER_ID,
                               "role": "coordinator", "can_view_sensitive": True,
                               "can_edit_crew": True, "can_manage_members": False,
                               "can_edit_production": False}],
    })
    acc = pa.get_production_access("p1", DEV_USER_ID)
    assert acc["role"] == "coordinator" and acc["can_view_sensitive"] is True
    assert acc["can_manage_members"] is False


def test_access_non_member_is_none(monkeypatch):
    _patch(monkeypatch, {"productions": [{"id": "p1", "owner_id": "other"}],
                         "production_members": []})
    assert pa.get_production_access("p1", DEV_USER_ID) is None
