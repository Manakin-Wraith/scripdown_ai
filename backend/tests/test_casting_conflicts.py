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
    conflicts = cs.compute_conflicts("s1", "sch1")["conflicts"]
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c["character_name"] == "JOHN"
    assert c["actor_name"] == "Jon Doe"
    assert c["day_number"] == 1
    assert c["shoot_date"] == "2026-03-12"
    assert c["reason"] == "Other shoot"
    assert c["scene_ids"] == ["sc1"]


def test_conflict_scene_ids_only_include_scenes_with_the_character(wired):
    # Add a second scene to day 1 that does NOT feature JOHN.
    wired["shooting_day_scenes"].append({"shooting_day_id": "d1", "scene_id": "sc3"})
    wired["scenes"].append({"id": "sc3", "script_id": "s1", "characters": ["MARY"]})
    conflicts = cs.compute_conflicts("s1", "sch1")["conflicts"]
    assert len(conflicts) == 1
    assert conflicts[0]["scene_ids"] == ["sc1"]  # sc3 excluded — no JOHN


def test_conflict_scene_ids_resolve_aliases(wired):
    # JOHN only appears in day 1 via the alias "JOHNNY" on sc1.
    conflicts = cs.compute_conflicts("s1", "sch1")["conflicts"]
    assert conflicts[0]["scene_ids"] == ["sc1"]


def test_wishlist_character_never_conflicts(wired):
    # MARY is unavailable the same window but status=wishlist -> ignored
    conflicts = cs.compute_conflicts("s1", "sch1")["conflicts"]
    assert all(c["character_name"] != "MARY" for c in conflicts)


def test_undated_day_is_skipped(wired):
    conflicts = cs.compute_conflicts("s1", "sch1")["conflicts"]
    assert all(c["shooting_day_id"] != "d2" for c in conflicts)


def test_available_character_no_conflict(wired):
    wired["casting_unavailability"][:] = []  # nobody unavailable
    assert cs.compute_conflicts("s1", "sch1") == {"conflicts": [], "acknowledged": []}


def test_background_tier_excluded_from_conflicts(wired):
    wired["casting"][0]["tier"] = "background"
    out = cs.compute_conflicts("s1", "sch1")
    assert out["conflicts"] == []
    assert out["acknowledged"] == []


def test_featured_tier_included(wired):
    wired["casting"][0]["tier"] = "featured"
    out = cs.compute_conflicts("s1", "sch1")
    assert len(out["conflicts"]) == 1


def test_acknowledged_conflict_moves_to_acknowledged_list(wired):
    wired["shooting_day_scenes"][0].update({
        "conflict_ack": True,
        "conflict_ack_reason": "cleared with agent",
        "conflict_ack_by": "u9",
        "conflict_ack_at": "2026-03-01T00:00:00Z",
    })
    out = cs.compute_conflicts("s1", "sch1")
    assert out["conflicts"] == []
    assert len(out["acknowledged"]) == 1
    entry = out["acknowledged"][0]
    assert entry["ack_reason"] == "cleared with agent"
    assert entry["ack_by"] == "u9"
    assert "suggested_day" not in entry


def test_partial_ack_stays_active(wired):
    # JOHN also on a second scene on day 1 that is NOT acked -> still a conflict
    wired["shooting_day_scenes"][0].update({"conflict_ack": True,
                                            "conflict_ack_reason": "x"})
    wired["shooting_day_scenes"].append({"shooting_day_id": "d1", "scene_id": "sc4"})
    wired["scenes"].append({"id": "sc4", "script_id": "s1", "characters": ["JOHN"]})
    out = cs.compute_conflicts("s1", "sch1")
    assert len(out["conflicts"]) == 1
    assert out["acknowledged"] == []


def test_suggested_day_is_earliest_clear_dated_day(wired):
    wired["shooting_days"][1]["shoot_date"] = "2026-03-20"  # outside JOHN's window
    out = cs.compute_conflicts("s1", "sch1")
    c = out["conflicts"][0]
    assert c["suggested_day"]["day_number"] == 2
    assert c["suggested_day"]["shoot_date"] == "2026-03-20"


def test_suggested_day_null_when_no_clear_day(wired):
    wired["shooting_days"][1]["shoot_date"] = "2026-03-14"  # also inside the window
    out = cs.compute_conflicts("s1", "sch1")
    assert out["conflicts"][0]["suggested_day"] is None


@pytest.mark.skip(reason="DB trigger — verified manually against Supabase by controller")
def test_shoot_date_change_clears_ack(wired):
    pass


def test_active_schedule_id(wired):
    assert cs.active_schedule_id("s1") == "sch1"
    wired["shooting_schedules"][:] = []
    assert cs.active_schedule_id("s1") is None
