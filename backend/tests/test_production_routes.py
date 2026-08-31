"""
Production CRUD + association route tests.

Mirrors the MockTable/MockSupabase pattern from test_series_routes.py:
a chainable supabase-py stand-in over a shared in-memory store, so route
code and get_script_role() see the same rows.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.production_service as ps
import routes.production_routes as pr
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
    from routes.production_routes import production_bp
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(production_bp)
    return app.test_client()


def _store(**overrides):
    base = {"productions": [], "units": [], "scripts": [], "script_members": []}
    base.update(overrides)
    return base


def _patch(monkeypatch, store):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    mock = MockSupabase(store)
    monkeypatch.setattr(ps, "get_supabase_admin", lambda: mock)
    # get_script_role() in middleware.authorization has its own get_supabase_admin
    monkeypatch.setattr("middleware.authorization.get_supabase_admin", lambda: mock)


def test_create_production_makes_production_and_main_unit(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)

    resp = _client().post("/api/productions", json={"title": "Farm Feature"})

    assert resp.status_code == 201
    body = resp.get_json()
    assert body["production"]["title"] == "Farm Feature"
    assert body["production"]["owner_id"] == DEV_USER_ID
    assert body["production"]["status"] == "development"
    assert body["unit"]["name"] == "Main Unit"
    assert body["unit"]["production_id"] == body["production"]["id"]
    assert len(store["units"]) == 1


def test_create_production_requires_title(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _client().post("/api/productions", json={})
    assert resp.status_code == 400


def test_list_productions_returns_only_callers_own(monkeypatch):
    store = _store(productions=[
        {"id": "p1", "owner_id": DEV_USER_ID, "title": "Mine"},
        {"id": "p2", "owner_id": "other", "title": "Not mine"},
    ])
    _patch(monkeypatch, store)
    resp = _client().get("/api/productions")
    assert resp.status_code == 200
    assert [p["title"] for p in resp.get_json()["productions"]] == ["Mine"]


def test_get_production_owner_sees_all_associated_scripts(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID, "title": "Mine"}],
        scripts=[
            {"id": "s1", "user_id": DEV_USER_ID, "production_id": "p1", "title": "Ep 1"},
            {"id": "s2", "user_id": DEV_USER_ID, "production_id": "p1", "title": "Ep 2"},
        ],
    )
    _patch(monkeypatch, store)
    resp = _client().get("/api/productions/p1")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["production"]["id"] == "p1"
    assert {s["id"] for s in body["scripts"]} == {"s1", "s2"}


def test_get_production_unrelated_user_forbidden(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": "other", "title": "Theirs"}],
        scripts=[{"id": "s1", "user_id": "other", "production_id": "p1", "title": "Ep 1"}],
    )
    _patch(monkeypatch, store)
    resp = _client().get("/api/productions/p1")
    assert resp.status_code == 403


def test_get_production_team_member_sees_only_their_script(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": "other", "title": "Theirs"}],
        scripts=[
            {"id": "s1", "user_id": "other", "production_id": "p1", "title": "Ep 1"},
            {"id": "s2", "user_id": "other", "production_id": "p1", "title": "Ep 2"},
        ],
        script_members=[{"script_id": "s1", "user_id": DEV_USER_ID, "role": "viewer"}],
    )
    _patch(monkeypatch, store)
    resp = _client().get("/api/productions/p1")
    assert resp.status_code == 200
    assert {s["id"] for s in resp.get_json()["scripts"]} == {"s1"}


def test_get_production_missing_is_404(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _client().get("/api/productions/nope")
    assert resp.status_code == 404


def test_patch_production_updates_only_given_fields(monkeypatch):
    store = _store(productions=[
        {"id": "p1", "owner_id": DEV_USER_ID, "title": "Old", "status": "development",
         "notes": "keep me"},
    ])
    _patch(monkeypatch, store)
    resp = _client().patch("/api/productions/p1", json={"title": "New", "status": "prep"})
    assert resp.status_code == 200
    row = store["productions"][0]
    assert row["title"] == "New"
    assert row["status"] == "prep"
    assert row["notes"] == "keep me"


def test_patch_production_non_owner_forbidden(monkeypatch):
    store = _store(productions=[{"id": "p1", "owner_id": "other", "title": "Theirs"}])
    _patch(monkeypatch, store)
    resp = _client().patch("/api/productions/p1", json={"title": "Hijack"})
    assert resp.status_code == 403
    assert store["productions"][0]["title"] == "Theirs"


def test_patch_production_missing_is_404(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _client().patch("/api/productions/nope", json={"title": "x"})
    assert resp.status_code == 404


def test_delete_production_nulls_associated_scripts(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID, "title": "Mine"}],
        scripts=[{"id": "s1", "user_id": DEV_USER_ID, "production_id": "p1", "title": "Ep 1"}],
    )
    _patch(monkeypatch, store)
    resp = _client().delete("/api/productions/p1")
    assert resp.status_code == 200
    assert store["productions"] == []
    # ON DELETE SET NULL is a DB behavior; the route mirrors it explicitly
    assert store["scripts"][0]["production_id"] is None


def test_delete_production_non_owner_forbidden(monkeypatch):
    store = _store(productions=[{"id": "p1", "owner_id": "other", "title": "Theirs"}])
    _patch(monkeypatch, store)
    resp = _client().delete("/api/productions/p1")
    assert resp.status_code == 403
    assert len(store["productions"]) == 1
