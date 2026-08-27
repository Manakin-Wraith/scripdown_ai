# backend/tests/test_casting_conflicts.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
import services.casting_service as cs


class FakeQ:
    def __init__(self, rows): self._rows = rows; self._f = []
    def select(self, *a, **k): return self
    def eq(self, c, v): self._f.append((c, v)); return self
    def in_(self, c, vals): self._f.append((c, set(vals))); return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def execute(self):
        out = []
        for r in self._rows:
            ok = True
            for c, v in self._f:
                ok = ok and (r.get(c) in v if isinstance(v, set) else r.get(c) == v)
            if ok:
                out.append(r)
        return type("R", (), {"data": out})


@pytest.fixture
def wired(monkeypatch):
    tables = {
        "shooting_schedules": [
            {"id": "sch1", "script_id": "s1", "status": "active", "updated_at": "2026-01-02"},
        ],
        "shooting_days": [
            {"id": "d1", "schedule_id": "sch1", "day_number": 1, "shoot_date": "2026-03-12"},
            {"id": "d2", "schedule_id": "sch1", "day_number": 2, "shoot_date": None},
        ],
        "shooting_day_scenes": [
            {"shooting_day_id": "d1", "scene_id": "sc1"},
            {"shooting_day_id": "d2", "scene_id": "sc2"},
        ],
        "scenes": [
            {"id": "sc1", "script_id": "s1", "characters": ["JOHNNY", "MARY"]},
            {"id": "sc2", "script_id": "s1", "characters": ["JOHN"]},
        ],
        "character_aliases": [
            {"script_id": "s1", "alias": "JOHNNY", "canonical_name": "JOHN"},
        ],
        "casting": [
            {"id": "c1", "script_id": "s1", "character_name": "JOHN",
             "actor_name": "Jon Doe", "status": "booked"},
            {"id": "c2", "script_id": "s1", "character_name": "MARY",
             "actor_name": "May Poe", "status": "wishlist"},
        ],
        "casting_unavailability": [
            {"id": "u1", "casting_id": "c1", "start_date": "2026-03-10",
             "end_date": "2026-03-15", "reason": "Other shoot"},
            {"id": "u2", "casting_id": "c2", "start_date": "2026-03-10",
             "end_date": "2026-03-15", "reason": "Holiday"},
        ],
    }

    class FakeClient:
        def table(self, name): return FakeQ(tables[name])

    monkeypatch.setattr(cs, "_client", lambda: FakeClient())
    return tables


def test_conflict_on_dated_day_for_booked_character(wired):
    conflicts = cs.compute_conflicts("s1", "sch1")
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c["character_name"] == "JOHN"
    assert c["actor_name"] == "Jon Doe"
    assert c["day_number"] == 1
    assert c["shoot_date"] == "2026-03-12"
    assert c["reason"] == "Other shoot"


def test_wishlist_character_never_conflicts(wired):
    # MARY is unavailable the same window but status=wishlist -> ignored
    conflicts = cs.compute_conflicts("s1", "sch1")
    assert all(c["character_name"] != "MARY" for c in conflicts)


def test_undated_day_is_skipped(wired):
    conflicts = cs.compute_conflicts("s1", "sch1")
    assert all(c["shooting_day_id"] != "d2" for c in conflicts)


def test_available_character_no_conflict(wired):
    wired["casting_unavailability"][:] = []  # nobody unavailable
    assert cs.compute_conflicts("s1", "sch1") == []


def test_active_schedule_id(wired):
    assert cs.active_schedule_id("s1") == "sch1"
    wired["shooting_schedules"][:] = []
    assert cs.active_schedule_id("s1") is None
