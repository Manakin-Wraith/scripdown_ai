import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
import services.casting_service as cs


class FakeTable:
    def __init__(self, store, name):
        self.store, self.name, self._filters, self._payload, self._op = store, name, [], None, None
    def select(self, *a, **k): self._op = 'select'; return self
    def insert(self, payload): self._op, self._payload = 'insert', payload; return self
    def update(self, payload): self._op, self._payload = 'update', payload; return self
    def delete(self): self._op = 'delete'; return self
    def eq(self, col, val): self._filters.append((col, val)); return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def _match(self, row): return all(row.get(c) == v for c, v in self._filters)
    def execute(self):
        rows = self.store.setdefault(self.name, [])
        if self._op == 'select':
            return type("R", (), {"data": [r for r in rows if self._match(r)]})
        if self._op == 'insert':
            payload = self._payload if isinstance(self._payload, list) else [self._payload]
            for p in payload:
                p.setdefault('id', f"{self.name}-{len(rows)+1}")
                rows.append(p)
            return type("R", (), {"data": payload})
        if self._op == 'update':
            hit = [r for r in rows if self._match(r)]
            for r in hit: r.update(self._payload)
            return type("R", (), {"data": hit})
        if self._op == 'delete':
            hit = [r for r in rows if self._match(r)]
            self.store[self.name] = [r for r in rows if not self._match(r)]
            return type("R", (), {"data": hit})


class FakeClient:
    def __init__(self, store): self.store = store
    def table(self, name): return FakeTable(self.store, name)


@pytest.fixture
def fake_db(monkeypatch):
    store = {
        "scenes": [
            {"id": "sc1", "script_id": "s1", "characters": ["JOHN", "MARY"]},
            {"id": "sc2", "script_id": "s1", "characters": ["john", "SARAH"]},
        ],
        "character_aliases": [
            {"script_id": "s1", "alias": "JOHNNY", "canonical_name": "JOHN"},
        ],
        "casting": [],
        "casting_unavailability": [],
    }
    monkeypatch.setattr(cs, "_client", lambda: FakeClient(store))
    return store


def test_norm_name():
    assert cs.norm_name("  john ") == "JOHN"
    assert cs.norm_name(None) == ""


def test_breakdown_characters_counts_and_resolves_case(fake_db):
    counts = cs.breakdown_characters("s1")
    # "JOHN" + "john" collapse to one canonical, appearing in 2 scenes
    assert counts["JOHN"] == 2
    assert counts["MARY"] == 1
    assert counts["SARAH"] == 1


def test_create_casting_then_conflict(fake_db):
    row = cs.create_casting("s1", "john", "u1")
    assert row["character_name"] == "JOHN"
    assert row["status"] == "wishlist"
    with pytest.raises(cs.CastingConflict):
        cs.create_casting("s1", "JOHN", "u1")


def test_serialize_redacts_contact(fake_db):
    row = cs.create_casting("s1", "JOHN", "u1")
    cs.update_casting(row["id"], {"contact_phone": "0821234567", "actor_name": "Jon Doe"})
    full = cs.serialize(cs.get_casting(row["id"]), include_contact=True)
    lite = cs.serialize(cs.get_casting(row["id"]), include_contact=False)
    assert full["contact_phone"] == "0821234567"
    assert "contact_phone" not in lite
    assert lite["actor_name"] == "Jon Doe"


def test_add_unavailability_validates_order(fake_db):
    row = cs.create_casting("s1", "JOHN", "u1")
    with pytest.raises(ValueError):
        cs.add_unavailability(row["id"], "2026-03-10", "2026-03-01", None)
    ok = cs.add_unavailability(row["id"], "2026-03-01", "2026-03-05", "Other shoot")
    assert ok["reason"] == "Other shoot"


def test_update_casting_sets_tier(fake_db):
    row = cs.create_casting("s1", "JOHN", "u1")
    updated = cs.update_casting(row["id"], {"tier": "lead"})
    assert updated["tier"] == "lead"


def test_update_casting_rejects_bad_tier(fake_db):
    row = cs.create_casting("s1", "JOHN", "u1")
    with pytest.raises(ValueError):
        cs.update_casting(row["id"], {"tier": "hero"})


def test_serialize_includes_tier():
    out = cs.serialize(
        {"id": "x", "script_id": "s", "character_name": "SARAH",
         "status": "booked", "tier": "featured"},
        include_contact=False)
    assert out["tier"] == "featured"


def test_serialize_defaults_tier_when_missing():
    out = cs.serialize(
        {"id": "x", "script_id": "s", "character_name": "SARAH", "status": "booked"},
        include_contact=False)
    assert out["tier"] == "supporting"
