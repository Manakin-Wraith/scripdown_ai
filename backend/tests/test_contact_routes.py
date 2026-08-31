"""
Contacts directory CRUD route tests.

Mirrors the MockTable/MockSupabase pattern from test_production_routes.py:
a chainable supabase-py stand-in over a shared in-memory store, so route
code and the service see the same rows.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.contact_service as cs
import routes.contact_routes as cr  # noqa: F401
from middleware.auth import DEV_USER_ID
from postgrest.exceptions import APIError


class MockTable:
    def __init__(self, name, store):
        self.name = name
        self.store = store
        self._filters = {}          # col -> value for .eq
        self._is_null = set()       # cols asserted IS NULL via .is_
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


def _client():
    from flask import Flask
    from routes.contact_routes import contacts_bp
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(contacts_bp)
    return app.test_client()


def _store(**overrides):
    base = {"contacts": [], "production_crew": [], "productions": []}
    base.update(overrides)
    return base


def _patch(monkeypatch, store):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    mock = MockSupabase(store)
    monkeypatch.setattr(cs, "get_supabase_admin", lambda: mock)


def test_anonymous_is_401(monkeypatch):
    _patch(monkeypatch, _store())
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    assert _client().get("/api/contacts").status_code == 401


def test_create_requires_name(monkeypatch):
    _patch(monkeypatch, _store())
    assert _client().post("/api/contacts", json={}).status_code == 400
    assert _client().post("/api/contacts", json={"name": "  "}).status_code == 400


def test_create_rejects_bad_kind_and_rate_unit(monkeypatch):
    _patch(monkeypatch, _store())
    assert _client().post("/api/contacts", json={"name": "A", "kind": "robot"}).status_code == 400
    assert _client().post("/api/contacts", json={"name": "A", "rate_unit": "hour"}).status_code == 400


def test_create_normalizes_role_tags_from_string(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _client().post("/api/contacts", json={"name": "Gaffer Gary", "role_tags": "gaffer, best boy , "})
    assert resp.status_code == 201
    assert resp.get_json()["contact"]["role_tags"] == ["gaffer", "best boy"]
    assert resp.get_json()["contact"]["owner_id"] == DEV_USER_ID


def test_list_returns_only_callers_contacts(monkeypatch):
    store = _store(contacts=[
        {"id": "c1", "owner_id": DEV_USER_ID, "name": "Mine", "kind": "person"},
        {"id": "c2", "owner_id": "other", "name": "Theirs", "kind": "person"},
    ])
    _patch(monkeypatch, store)
    body = _client().get("/api/contacts").get_json()
    assert [c["name"] for c in body["contacts"]] == ["Mine"]


def test_get_patch_delete_other_users_contact_is_404(monkeypatch):
    store = _store(contacts=[{"id": "c2", "owner_id": "other", "name": "Theirs", "kind": "person"}])
    _patch(monkeypatch, store)
    assert _client().get("/api/contacts/c2").status_code == 404
    assert _client().patch("/api/contacts/c2", json={"name": "x"}).status_code == 404
    assert _client().delete("/api/contacts/c2").status_code == 404


def test_patch_updates_only_given_fields(monkeypatch):
    store = _store(contacts=[
        {"id": "c1", "owner_id": DEV_USER_ID, "name": "Old", "phone": "111", "kind": "person"},
    ])
    _patch(monkeypatch, store)
    resp = _client().patch("/api/contacts/c1", json={"phone": "222"})
    assert resp.status_code == 200
    assert store["contacts"][0]["name"] == "Old"
    assert store["contacts"][0]["phone"] == "222"


def test_delete_blocked_when_assigned(monkeypatch):
    store = _store(
        contacts=[{"id": "c1", "owner_id": DEV_USER_ID, "name": "Gary", "kind": "person"}],
        productions=[{"id": "p1", "owner_id": DEV_USER_ID, "title": "Farm Feature"}],
        production_crew=[{"id": "cw1", "production_id": "p1", "contact_id": "c1", "role": "Gaffer"}],
    )
    _patch(monkeypatch, store)
    resp = _client().delete("/api/contacts/c1")
    assert resp.status_code == 409
    assert resp.get_json()["used_in"] == [{"production_id": "p1", "production_title": "Farm Feature"}]
    assert len(store["contacts"]) == 1


def test_delete_unassigned_then_second_delete_404(monkeypatch):
    store = _store(contacts=[{"id": "c1", "owner_id": DEV_USER_ID, "name": "Gary", "kind": "person"}])
    _patch(monkeypatch, store)
    assert _client().delete("/api/contacts/c1").status_code == 200
    assert _client().delete("/api/contacts/c1").status_code == 404


def test_get_contact_with_zero_assignments_returns_empty_list(monkeypatch):
    store = _store(contacts=[{"id": "c1", "owner_id": DEV_USER_ID, "name": "Gary", "kind": "person"}])
    _patch(monkeypatch, store)
    resp = _client().get("/api/contacts/c1")
    assert resp.status_code == 200
    assert resp.get_json()["assignments"] == []


def test_get_contact_lists_assignments(monkeypatch):
    store = _store(
        contacts=[{"id": "c1", "owner_id": DEV_USER_ID, "name": "Gary", "kind": "person"}],
        productions=[{"id": "p1", "owner_id": DEV_USER_ID, "title": "Farm Feature"}],
        production_crew=[{"id": "cw1", "production_id": "p1", "contact_id": "c1", "role": "Gaffer"}],
    )
    _patch(monkeypatch, store)
    body = _client().get("/api/contacts/c1").get_json()
    assert body["assignments"] == [
        {"crew_id": "cw1", "production_id": "p1", "production_title": "Farm Feature", "role": "Gaffer"}
    ]
