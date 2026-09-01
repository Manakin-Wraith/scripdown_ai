"""Production member + invite tests.

MockTable / MockSupabase are the chainable in-memory stand-in shared across
the production suite (copied from test_production_crew_routes.py).
"""
import os, sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.production_member_service as pms
from middleware.auth import DEV_USER_ID


def _ilike_match(cell, pattern):
    c = str(cell or "").lower()
    p = str(pattern).lower()
    if "%" in p:
        return p.strip("%") in c
    return c == p


def _or_match(row, expr):
    for clause in expr.split(","):
        col, op, val = clause.split(".", 2)
        if op == "ilike" and _ilike_match(row.get(col), val):
            return True
    return False


class MockTable:
    def __init__(self, name, store):
        self.name = name
        self.store = store
        self._filters = {}          # col -> value for .eq
        self._is_null = set()       # cols asserted IS NULL via .is_
        self._ilike = []            # (col, pattern) from .ilike
        self._or = None             # raw PostgREST or_ expression
        self._op = None
        self._payload = None
        self._single = False
        self._order = None
        self._limit = None

    def select(self, *_a, **_k):
        self._op = "select"; return self

    def insert(self, data):
        self._op = "insert"; self._payload = data; return self

    def update(self, data):
        self._op = "update"; self._payload = data; return self

    def delete(self):
        self._op = "delete"; return self

    def eq(self, col, val):
        self._filters[col] = val; return self

    def is_(self, col, _val):        # only ever .is_(col, "null") in this codebase
        self._is_null.add(col); return self

    def in_(self, col, values):
        self._filters[col] = ("__in__", set(values)); return self

    def ilike(self, col, pattern):
        self._ilike.append((col, pattern)); return self

    def or_(self, expr):
        self._or = expr; return self

    def order(self, col, desc=False):
        self._order = (col, desc); return self

    def single(self):
        self._single = True; return self

    def limit(self, n):
        self._limit = n; return self

    def _rows(self):
        return self.store.setdefault(self.name, [])

    def _match(self, r):
        for k, v in self._filters.items():
            if isinstance(v, tuple) and v and v[0] == "__in__":
                if r.get(k) not in v[1]:
                    return False
            elif r.get(k) != v:
                return False
        for col in self._is_null:
            if r.get(col) is not None:
                return False
        for col, pattern in self._ilike:
            if not _ilike_match(r.get(col), pattern):
                return False
        if self._or is not None and not _or_match(r, self._or):
            return False
        return True

    def _filtered(self):
        rows = [r for r in self._rows() if self._match(r)]
        if self._order:
            col, desc = self._order
            rows = sorted(rows, key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
        return rows

    def execute(self):
        if self._op == "select":
            rows = self._filtered()
            if self._limit is not None:
                rows = rows[: self._limit]
            if self._single:
                from postgrest.exceptions import APIError
                if not rows:
                    raise APIError({"message": "no rows", "code": "PGRST116",
                                    "hint": None, "details": None})
                return SimpleNamespace(data=rows[0])
            return SimpleNamespace(data=rows)
        if self._op == "insert":
            row = dict(self._payload)
            row.setdefault("id", f"{self.name}-{len(self._rows()) + 1}")
            self._rows().append(row)
            return SimpleNamespace(data=[row])
        if self._op == "update":
            rows = self._filtered()
            for r in rows:
                r.update(self._payload)
            return SimpleNamespace(data=rows)
        if self._op == "delete":
            rows = self._filtered()
            keep = [r for r in self._rows() if r not in rows]
            self.store[self.name] = keep
            return SimpleNamespace(data=rows)
        return SimpleNamespace(data=None)


class MockSupabase:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        return MockTable(name, self.store)


def _patch(monkeypatch, store):
    mock = MockSupabase(store)
    monkeypatch.setattr(pms, "get_supabase_admin", lambda: mock)
    return mock


def test_apply_role_preset_admin():
    assert pms.apply_role_preset("admin", None) == {
        "can_view_sensitive": True, "can_edit_crew": True,
        "can_manage_members": True, "can_edit_production": True}


def test_apply_role_preset_coordinator():
    assert pms.apply_role_preset("coordinator", None) == {
        "can_view_sensitive": False, "can_edit_crew": True,
        "can_manage_members": False, "can_edit_production": False}


def test_apply_role_preset_with_override():
    out = pms.apply_role_preset("coordinator", {"can_view_sensitive": True})
    assert out["can_view_sensitive"] is True and out["can_edit_crew"] is True


def test_rank_ok_owner_can_anything():
    owner = {"role": "owner", "can_manage_members": True, "can_edit_crew": True,
             "can_view_sensitive": True, "can_edit_production": True}
    assert pms.rank_ok(owner, "admin", pms.apply_role_preset("admin", None)) is True


def test_rank_ok_admin_cannot_create_admin():
    admin = {"role": "admin", "can_manage_members": True, "can_edit_crew": True,
             "can_view_sensitive": True, "can_edit_production": True}
    assert pms.rank_ok(admin, "admin", pms.apply_role_preset("admin", None)) is False


def test_rank_ok_admin_can_create_coordinator():
    admin = {"role": "admin", "can_manage_members": True, "can_edit_crew": True,
             "can_view_sensitive": True, "can_edit_production": True}
    assert pms.rank_ok(admin, "coordinator", pms.apply_role_preset("coordinator", None)) is True


def test_rank_ok_actor_cannot_grant_flag_they_lack():
    admin_no_manage = {"role": "admin", "can_manage_members": False, "can_edit_crew": True,
                       "can_view_sensitive": True, "can_edit_production": True}
    flags = pms.apply_role_preset("coordinator", {"can_manage_members": True})
    assert pms.rank_ok(admin_no_manage, "coordinator", flags) is False


def test_list_members_joins_profile_name(monkeypatch):
    _patch(monkeypatch, {
        "production_members": [{"id": "m1", "production_id": "p1", "user_id": "u1",
                               "role": "coordinator", "can_view_sensitive": False,
                               "can_edit_crew": True, "can_manage_members": False,
                               "can_edit_production": False}],
        "profiles": [{"id": "u1", "full_name": "Lee Producer", "email": "lee@x.com"}],
        "production_invites": [{"id": "i1", "production_id": "p1", "email": "new@x.com",
                              "role": "viewer", "status": "pending", "expires_at": "2099-01-01"}],
    })
    out = pms.list_members_and_invites("p1")
    assert out["members"][0]["name"] == "Lee Producer"
    assert out["members"][0]["email"] == "lee@x.com"
    assert len(out["invites"]) == 1 and out["invites"][0]["email"] == "new@x.com"
