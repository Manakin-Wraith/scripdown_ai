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
