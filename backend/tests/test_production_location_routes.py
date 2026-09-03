# backend/tests/test_production_location_routes.py
# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative
# scene-setting resolver in location_resolver.py.
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.production_location_service as pls


class FakeTable:
    def __init__(self, store, name):
        self.store, self.name, self._f, self._payload = store, name, {}, None
        self._op = None
    def select(self, *a): self._op = "select"; return self
    def insert(self, row): self._op, self._payload = "insert", row; return self
    def update(self, row): self._op, self._payload = "update", row; return self
    def delete(self): self._op = "delete"; return self
    def eq(self, k, v): self._f[k] = v; return self
    def in_(self, k, vals): self._f[(k, "in")] = set(vals); return self
    def limit(self, n): return self
    def order(self, *a, **k): return self
    def _match(self, row):
        for k, v in self._f.items():
            if isinstance(k, tuple) and k[1] == "in":
                if row.get(k[0]) not in v: return False
            elif row.get(k) != v:
                return False
        return True
    def execute(self):
        rows = self.store.setdefault(self.name, [])
        if self._op == "insert":
            r = dict(self._payload); r.setdefault("id", f"{self.name}-{len(rows)+1}")
            rows.append(r); return type("R", (), {"data": [r]})
        if self._op == "select":
            return type("R", (), {"data": [dict(r) for r in rows if self._match(r)]})
        if self._op == "update":
            hit = [r for r in rows if self._match(r)]
            for r in hit: r.update(self._payload)
            return type("R", (), {"data": [dict(r) for r in hit]})
        if self._op == "delete":
            self.store[self.name] = [r for r in rows if not self._match(r)]
            return type("R", (), {"data": []})
        return type("R", (), {"data": []})


class FakeSupabase:
    def __init__(self): self.store = {}
    def table(self, name): return FakeTable(self.store, name)


@pytest.fixture
def fake(monkeypatch):
    fs = FakeSupabase()
    monkeypatch.setattr(pls, "get_supabase_admin", lambda: fs)
    return fs


def _seed_location(fake, owner="owner1", lid="loc1"):
    fake.store.setdefault("locations", []).append(
        {"id": lid, "owner_id": owner, "name": "Stage 6", "address": "1 Main"})


def test_link_rejects_location_not_owned_by_production_owner(fake):
    _seed_location(fake, owner="someone_else")
    assert pls.link_location("p1", "loc1", owner_id="owner1") == "not_owned"


def test_link_creates_row(fake):
    _seed_location(fake)
    out = pls.link_location("p1", "loc1", owner_id="owner1", notes="week 2")
    assert out["production_id"] == "p1" and out["production_notes"] == "week 2"


def test_link_duplicate_returns_exists(fake):
    _seed_location(fake)
    pls.link_location("p1", "loc1", owner_id="owner1")
    assert pls.link_location("p1", "loc1", owner_id="owner1") == "exists"


def test_list_for_production_embeds_location_fields(fake):
    _seed_location(fake)
    pls.link_location("p1", "loc1", owner_id="owner1", notes="n")
    rows = pls.list_for_production("p1")
    assert rows[0]["name"] == "Stage 6" and rows[0]["production_notes"] == "n"


def test_unlink(fake):
    _seed_location(fake)
    link = pls.link_location("p1", "loc1", owner_id="owner1")
    assert pls.unlink("p1", link["id"]) == "ok"
    assert pls.list_for_production("p1") == []
    assert pls.unlink("p1", link["id"]) == "not_found"


def test_update_link_rejects_wrong_production(fake):
    _seed_location(fake)
    link = pls.link_location("p1", "loc1", owner_id="owner1")
    assert pls.update_link("p2", link["id"], "notes") == "not_found"
    assert pls.update_link("p1", link["id"], "notes")["production_notes"] == "notes"


# --- route-layer tests (production_bp; mirrors test_production_member_routes.py) ---
from types import SimpleNamespace
from unittest.mock import patch

from postgrest.exceptions import APIError
from middleware.auth import DEV_USER_ID

import services.production_service as ps
import routes.production_routes as pr  # noqa: F401


class MockTable:
    def __init__(self, name, store):
        self.name, self.store = name, store
        self._filters, self._op, self._payload, self._single, self._limit = {}, None, None, False, None
    def select(self, *_a, **_k): self._op = "select"; return self
    def insert(self, data): self._op, self._payload = "insert", data; return self
    def update(self, data): self._op, self._payload = "update", data; return self
    def delete(self): self._op = "delete"; return self
    def eq(self, c, v): self._filters[c] = v; return self
    def in_(self, c, vs): self._filters[c] = ("__in__", set(vs)); return self
    def single(self): self._single = True; return self
    def limit(self, n): self._limit = n; return self
    def order(self, *_a, **_k): return self
    def _rows(self): return self.store.setdefault(self.name, [])
    def _match(self, r):
        for k, v in self._filters.items():
            if isinstance(v, tuple) and v and v[0] == "__in__":
                if r.get(k) not in v[1]: return False
            elif r.get(k) != v: return False
        return True
    def _filtered(self): return [r for r in self._rows() if self._match(r)]
    def execute(self):
        if self._op == "select":
            rows = self._filtered()
            if self._limit is not None: rows = rows[:self._limit]
            if self._single:
                if not rows:
                    raise APIError({"message": "no rows", "code": "PGRST116",
                                    "hint": None, "details": None})
                return SimpleNamespace(data=rows[0])
            return SimpleNamespace(data=rows)
        if self._op == "insert":
            row = dict(self._payload); row.setdefault("id", f"{self.name}-{len(self._rows())+1}")
            self._rows().append(row); return SimpleNamespace(data=[row])
        if self._op == "update":
            rows = self._filtered()
            for r in rows: r.update(self._payload)
            return SimpleNamespace(data=rows)
        if self._op == "delete":
            rows = self._filtered()
            self.store[self.name] = [r for r in self._rows() if r not in rows]
            return SimpleNamespace(data=rows)
        return SimpleNamespace(data=None)


class MockSupabase:
    def __init__(self, store): self.store = store
    def table(self, name): return MockTable(name, self.store)


def _client():
    from flask import Flask
    from routes.production_routes import production_bp
    app = Flask(__name__); app.config["TESTING"] = True
    app.register_blueprint(production_bp)
    return app.test_client()


def _rt_patch(monkeypatch, store):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    mock = MockSupabase(store)
    monkeypatch.setattr(pls, "get_supabase_admin", lambda: mock)
    monkeypatch.setattr(ps, "get_supabase_admin", lambda: mock)
    monkeypatch.setattr("middleware.production_authz.get_supabase_admin", lambda: mock)
    monkeypatch.setattr("middleware.production_authz.get_user_id", lambda: DEV_USER_ID)


def _owned_store(**ov):
    base = {"productions": [{"id": "p1", "owner_id": DEV_USER_ID, "title": "Farm Feature"}],
            "production_members": [], "production_locations": [], "locations": []}
    base.update(ov)
    return base


def test_list_requires_membership(monkeypatch):
    _rt_patch(monkeypatch, {"productions": [{"id": "p1", "owner_id": "other"}],
                            "production_members": []})
    assert _client().get("/api/productions/p1/locations").status_code == 403


def test_viewer_cannot_link(monkeypatch):
    _rt_patch(monkeypatch, {
        "productions": [{"id": "p1", "owner_id": "other"}],
        "production_members": [{"id": "m1", "production_id": "p1", "user_id": DEV_USER_ID,
                               "role": "viewer", "can_edit_production": False}]})
    r = _client().post("/api/productions/p1/locations", json={"location_id": "loc1"})
    assert r.status_code == 403


def test_owner_links_location(monkeypatch):
    _rt_patch(monkeypatch, _owned_store())
    with patch.object(pls, "link_location", return_value={"id": "pl1", "production_id": "p1"}):
        r = _client().post("/api/productions/p1/locations",
                           json={"location_id": "loc1", "production_notes": "n"})
    assert r.status_code == 201


def test_link_not_owned_is_404(monkeypatch):
    _rt_patch(monkeypatch, _owned_store())
    with patch.object(pls, "link_location", return_value="not_owned"):
        r = _client().post("/api/productions/p1/locations", json={"location_id": "x"})
    assert r.status_code == 404


def test_link_duplicate_is_409(monkeypatch):
    _rt_patch(monkeypatch, _owned_store())
    with patch.object(pls, "link_location", return_value="exists"):
        r = _client().post("/api/productions/p1/locations", json={"location_id": "loc1"})
    assert r.status_code == 409


def test_post_requires_location_id(monkeypatch):
    _rt_patch(monkeypatch, _owned_store())
    assert _client().post("/api/productions/p1/locations", json={}).status_code == 400


def test_unlink_route_ok(monkeypatch):
    _rt_patch(monkeypatch, _owned_store(
        production_locations=[{"id": "pl1", "production_id": "p1", "location_id": "loc1"}]))
    r = _client().delete("/api/productions/p1/locations/pl1")
    assert r.status_code == 200 and r.get_json() == {"success": True}
