# backend/tests/test_location_service.py
# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative
# scene-setting resolver in location_resolver.py.
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.location_service as svc


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
    def or_(self, expr): self._f["_or"] = expr; return self
    def limit(self, n): return self
    def order(self, *a, **k): return self
    def _match(self, row):
        for k, v in self._f.items():
            if k == "_or":
                continue
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
            keep = [r for r in rows if not self._match(r)]
            self.store[self.name] = keep
            return type("R", (), {"data": []})
        return type("R", (), {"data": []})


class FakeSupabase:
    def __init__(self):
        self.store = {}
        self._storage = None
    def table(self, name): return FakeTable(self.store, name)

    @property
    def storage(self):
        return self._storage

    @storage.setter
    def storage(self, value):
        self._storage = value


@pytest.fixture
def fake(monkeypatch):
    fs = FakeSupabase()
    monkeypatch.setattr(svc, "get_supabase_admin", lambda: fs)
    monkeypatch.setattr(svc.geocode_service, "geocode", lambda a: None)
    return fs


def test_create_requires_owner_and_name(fake):
    row = svc.create_location("u1", {"name": "  Stage 6  "})
    assert row["owner_id"] == "u1" and row["created_by"] == "u1"
    assert row["name"] == "Stage 6"


def test_list_is_owner_scoped(fake):
    svc.create_location("u1", {"name": "A"})
    svc.create_location("u2", {"name": "B"})
    assert [r["name"] for r in svc.list_locations("u1")] == ["A"]


def test_update_geocodes_on_new_address(fake, monkeypatch):
    monkeypatch.setattr(svc.geocode_service, "geocode",
                        lambda a: {"lat": -33.9, "lng": 18.4})
    loc = svc.create_location("u1", {"name": "X"})
    out = svc.update_location("u1", loc["id"], {"address": "1 Main Rd"})
    assert out["lat"] == -33.9 and out["lng"] == 18.4 and out["geocode_status"] == "ok"


def test_update_failed_geocode_sets_failed_status(fake):
    loc = svc.create_location("u1", {"name": "X"})
    out = svc.update_location("u1", loc["id"], {"address": "??"})
    assert out["geocode_status"] == "failed" and out.get("lat") is None


def test_explicit_coords_skip_geocode_and_mark_manual(fake, monkeypatch):
    called = []
    monkeypatch.setattr(svc.geocode_service, "geocode",
                        lambda a: called.append(a) or {"lat": 1, "lng": 2})
    loc = svc.create_location("u1", {"name": "X"})
    out = svc.update_location("u1", loc["id"],
                              {"address": "1 Main Rd", "lat": 5, "lng": 6})
    assert out["lat"] == 5 and out["geocode_status"] == "manual" and called == []


def test_clearing_address_nulls_coords(fake):
    loc = svc.create_location("u1", {"name": "X", "lat": 1, "lng": 2,
                                     "geocode_status": "manual"})
    out = svc.update_location("u1", loc["id"], {"address": ""})
    assert out.get("lat") is None and out.get("geocode_status") is None


def test_update_other_owner_returns_not_found(fake):
    loc = svc.create_location("u1", {"name": "X"})
    assert svc.update_location("u2", loc["id"], {"name": "Y"}) is svc.NOT_FOUND


def test_delete_blocked_when_linked(fake):
    loc = svc.create_location("u1", {"name": "X"})
    fake.store.setdefault("production_locations", []).append(
        {"id": "pl1", "production_id": "p1", "location_id": loc["id"]})
    assert svc.delete_location("u1", loc["id"]) == "in_use"


def test_delete_ok_when_unlinked(fake):
    loc = svc.create_location("u1", {"name": "X"})
    assert svc.delete_location("u1", loc["id"]) == "ok"
    assert svc.list_locations("u1") == []


def test_get_with_usage_lists_productions(fake):
    loc = svc.create_location("u1", {"name": "X"})
    fake.store.setdefault("production_locations", []).append(
        {"id": "pl1", "production_id": "p1", "location_id": loc["id"],
         "production_notes": "week 2"})
    fake.store.setdefault("productions", []).append({"id": "p1", "title": "Feature"})
    out = svc.get_location_with_usage("u1", loc["id"])
    assert out["used_in"] == [{"production_id": "p1", "production_title": "Feature"}]
