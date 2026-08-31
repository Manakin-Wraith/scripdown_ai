"""Crew-assignment route tests for production_bp.

MockTable / MockSupabase copied verbatim from test_production_routes.py:
a chainable supabase-py stand-in over a shared in-memory store.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.production_service as ps
import services.production_crew_service as pcs
import services.department_service as ds
import routes.production_routes as pr  # noqa: F401
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
    base = {"productions": [{"id": "p1", "owner_id": DEV_USER_ID, "title": "Farm Feature"}],
            "contacts": [{"id": "c1", "owner_id": DEV_USER_ID, "name": "Gary", "kind": "person"}],
            "production_crew": [], "scripts": [], "script_members": []}
    base.update(overrides)
    return base


def _patch(monkeypatch, store):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    mock = MockSupabase(store)
    for mod in (ps, pcs):
        monkeypatch.setattr(mod, "get_supabase_admin", lambda: mock)
    monkeypatch.setattr("middleware.authorization.get_supabase_admin", lambda: mock)
    monkeypatch.setattr(ds, "get_departments_list", lambda: [{"code": "camera", "name": "Camera", "color": "#1"}])


def test_add_crew_happy_path(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _client().post("/api/productions/p1/crew",
                          json={"contact_id": "c1", "role": "Gaffer", "department_code": "camera"})
    assert resp.status_code == 201
    body = resp.get_json()["crew"]
    assert body["role"] == "Gaffer"
    assert body["contact"]["name"] == "Gary"
    assert len(store["production_crew"]) == 1


def test_add_crew_null_department_ok(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _client().post("/api/productions/p1/crew", json={"contact_id": "c1", "role": "Caterer"})
    assert resp.status_code == 201


def test_add_crew_unknown_department_is_400(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _client().post("/api/productions/p1/crew",
                          json={"contact_id": "c1", "department_code": "wizardry"})
    assert resp.status_code == 400
    assert store["production_crew"] == []


def test_add_crew_contact_not_owned_is_400(monkeypatch):
    store = _store(contacts=[{"id": "c9", "owner_id": "other", "name": "X", "kind": "person"}])
    _patch(monkeypatch, store)
    resp = _client().post("/api/productions/p1/crew", json={"contact_id": "c9"})
    assert resp.status_code == 400


def test_non_owner_forbidden_on_all_crew_routes(monkeypatch):
    store = _store(productions=[{"id": "p1", "owner_id": "other", "title": "Theirs"}],
                   scripts=[{"id": "s1", "user_id": "other", "production_id": "p1"}],
                   script_members=[{"script_id": "s1", "user_id": DEV_USER_ID, "role": "viewer"}])
    _patch(monkeypatch, store)
    assert _client().get("/api/productions/p1/crew").status_code == 403
    assert _client().post("/api/productions/p1/crew", json={"contact_id": "c1"}).status_code == 403
    assert _client().patch("/api/productions/p1/crew/cw1", json={"role": "x"}).status_code == 403
    assert _client().delete("/api/productions/p1/crew/cw1").status_code == 403


def test_missing_production_is_404(monkeypatch):
    _patch(monkeypatch, _store(productions=[]))
    assert _client().get("/api/productions/pX/crew").status_code == 404


def test_list_crew_orders_by_department_then_name(monkeypatch):
    store = _store(
        contacts=[
            {"id": "c1", "owner_id": DEV_USER_ID, "name": "Zed", "kind": "person"},
            {"id": "c2", "owner_id": DEV_USER_ID, "name": "Amy", "kind": "person"},
            {"id": "c3", "owner_id": DEV_USER_ID, "name": "Bob", "kind": "person"},
        ],
        production_crew=[
            {"id": "w1", "production_id": "p1", "contact_id": "c1", "department_code": "camera"},
            {"id": "w2", "production_id": "p1", "contact_id": "c2", "department_code": "camera"},
            {"id": "w3", "production_id": "p1", "contact_id": "c3", "department_code": None},
        ],
    )
    _patch(monkeypatch, store)
    names = [c["contact"]["name"] for c in _client().get("/api/productions/p1/crew").get_json()["crew"]]
    assert names == ["Amy", "Zed", "Bob"]  # camera (Amy,Zed) then null-dept (Bob)


def test_patch_ignores_contact_id(monkeypatch):
    store = _store(production_crew=[
        {"id": "w1", "production_id": "p1", "contact_id": "c1", "role": "Gaffer"}])
    _patch(monkeypatch, store)
    resp = _client().patch("/api/productions/p1/crew/w1",
                           json={"role": "Best Boy", "contact_id": "cHACK"})
    assert resp.status_code == 200
    assert store["production_crew"][0]["contact_id"] == "c1"
    assert store["production_crew"][0]["role"] == "Best Boy"


def test_delete_then_redelete_is_noop_200(monkeypatch):
    store = _store(production_crew=[{"id": "w1", "production_id": "p1", "contact_id": "c1"}])
    _patch(monkeypatch, store)
    assert _client().delete("/api/productions/p1/crew/w1").status_code == 200
    assert _client().delete("/api/productions/p1/crew/w1").status_code == 200


def test_same_contact_two_roles_both_persist(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    _client().post("/api/productions/p1/crew", json={"contact_id": "c1", "role": "Gaffer"})
    _client().post("/api/productions/p1/crew", json={"contact_id": "c1", "role": "Best Boy"})
    assert len(store["production_crew"]) == 2


def test_delete_production_cascade_is_simulated_by_route(monkeypatch):
    # The DB cascades production_crew on production delete; the delete route
    # already nulls scripts explicitly. Assert crew rows are cleared too.
    store = _store(production_crew=[{"id": "w1", "production_id": "p1", "contact_id": "c1"}])
    _patch(monkeypatch, store)
    assert _client().delete("/api/productions/p1").status_code == 200
    assert store["production_crew"] == []
    assert len(store["contacts"]) == 1


import io


def _post_csv(client, pid, text):
    return client.post(f"/api/productions/{pid}/crew/import",
                       data={"file": (io.BytesIO(text.encode()), "crew.csv")},
                       content_type="multipart/form-data")


def test_import_happy_path_counts(monkeypatch):
    store = _store(contacts=[
        {"id": "c1", "owner_id": DEV_USER_ID, "name": "Existing", "email": "e@x.com", "kind": "person"}])
    _patch(monkeypatch, store)
    csv_text = (
        "name,email,role,department,rate,rate_unit\n"
        "New One,new@x.com,Gaffer,camera,800,day\n"
        "Existing,e@x.com,Best Boy,camera,,\n"
        ",,,,,\n"
    )
    resp = _post_csv(_client(), "p1", csv_text)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["created_contacts"] == 1
    assert body["matched_contacts"] == 1
    assert body["assignments_created"] == 2
    assert body["skipped"] == [{"line": 4, "reason": "missing name"}]
    assert len(store["production_crew"]) == 2


def test_import_is_idempotent_on_rerun(monkeypatch):
    store = _store(contacts=[])
    _patch(monkeypatch, store)
    csv_text = "name,role\nGary,Gaffer\n"
    _post_csv(_client(), "p1", csv_text)
    resp = _post_csv(_client(), "p1", csv_text)
    body = resp.get_json()
    assert body["assignments_created"] == 0
    assert body["skipped"] and "already on crew" in body["skipped"][0]["reason"]
    assert len(store["production_crew"]) == 1


def test_import_email_match_scoped_to_owner(monkeypatch):
    store = _store(contacts=[
        {"id": "cX", "owner_id": "other", "name": "Stranger", "email": "dup@x.com", "kind": "person"}])
    _patch(monkeypatch, store)
    _post_csv(_client(), "p1", "name,email\nMine,dup@x.com\n")
    # a new contact is created for the caller, the stranger's row is untouched
    mine = [c for c in store["contacts"] if c["owner_id"] == DEV_USER_ID]
    assert len(mine) == 1 and mine[0]["name"] == "Mine"


def test_import_no_name_column_is_400(monkeypatch):
    _patch(monkeypatch, _store())
    resp = _post_csv(_client(), "p1", "email,role\na@b.com,Gaffer\n")
    assert resp.status_code == 400


def test_import_non_owner_forbidden(monkeypatch):
    store = _store(productions=[{"id": "p1", "owner_id": "other", "title": "Theirs"}])
    _patch(monkeypatch, store)
    resp = _post_csv(_client(), "p1", "name\nGary\n")
    assert resp.status_code == 403
