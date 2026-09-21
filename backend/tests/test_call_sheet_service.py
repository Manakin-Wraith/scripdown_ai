"""Service-layer tests for call_sheet_service.py.

MockTable/MockSupabase copied from tests/test_production_crew_routes.py —
this repo's standard chainable in-memory supabase-py stand-in.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_service as svc
import services.department_service as ds
from postgrest.exceptions import APIError


class MockTable:
    def __init__(self, name, store):
        self.name = name
        self.store = store
        self._filters = {}
        self._payload = None
        self._op = None
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

    def in_(self, col, values):
        self._filters[col] = ("__in__", set(values)); return self

    def order(self, col, desc=False):
        self._order = (col, desc); return self

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


def _store(**overrides):
    base = {
        "shooting_days": [{"id": "d1", "schedule_id": "sch1", "day_number": 1, "shoot_date": "2026-10-01"}],
        "shooting_schedules": [{"id": "sch1", "script_id": "s1"}],
        "scripts": [{"id": "s1", "production_id": "p1"}],
        "call_sheets": [], "call_sheet_crew": [], "call_sheet_cast": [], "call_sheet_locations": [],
        "shooting_day_scenes": [], "scenes": [],
        "production_crew": [], "contacts": [], "casting": [], "locations": [],
    }
    base.update(overrides)
    return base


def _patch(monkeypatch, store):
    monkeypatch.setattr(svc, "get_supabase_admin", lambda: MockSupabase(store))


def test_get_or_create_creates_row(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    result = svc.get_or_create("d1", "u1")
    assert result["shooting_day_id"] == "d1"
    assert result["production_id"] == "p1"
    assert result["status"] == "draft"
    assert result["created_by"] == "u1"
    assert len(store["call_sheets"]) == 1


def test_get_or_create_is_idempotent(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    first = svc.get_or_create("d1", "u1")
    second = svc.get_or_create("d1", "u2")
    assert first["id"] == second["id"]
    assert len(store["call_sheets"]) == 1


def test_get_or_create_unassociated_script_returns_sentinel(monkeypatch):
    store = _store(scripts=[{"id": "s1", "production_id": None}])
    _patch(monkeypatch, store)
    assert svc.get_or_create("d1", "u1") == "no_production"
    assert store["call_sheets"] == []


def test_get_or_create_missing_day_returns_sentinel(monkeypatch):
    _patch(monkeypatch, _store(shooting_days=[]))
    assert svc.get_or_create("dX", "u1") == "no_production"


def test_get_call_sheet_not_found(monkeypatch):
    _patch(monkeypatch, _store())
    assert svc.get_call_sheet("nope") is svc.NOT_FOUND


def test_get_call_sheet_assembles_roster_locations_scenes(monkeypatch):
    store = _store(
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        production_crew=[{"id": "cr1", "production_id": "p1", "contact_id": "c1", "role": "Gaffer"}],
        contacts=[{"id": "c1", "name": "Gary"}],
        call_sheet_crew=[{"id": "csc1", "call_sheet_id": "cs1", "crew_id": "cr1", "call_time": "06:00"}],
        casting=[{"id": "ca1", "script_id": "s1", "character_name": "HERO", "actor_name": "Jo"}],
        call_sheet_cast=[{"id": "csx1", "call_sheet_id": "cs1", "casting_id": "ca1", "call_time": "07:00"}],
        locations=[{"id": "l1", "name": "Warehouse", "address": "1 Main St", "parking_notes": "Lot B"}],
        call_sheet_locations=[{"id": "csl1", "call_sheet_id": "cs1", "location_id": "l1", "is_primary": True}],
        scenes=[{"id": "sc1", "scene_number": "1", "int_ext": "INT", "setting": "WAREHOUSE",
                 "time_of_day": "DAY", "page_length_eighths": 8}],
        shooting_day_scenes=[{"shooting_day_id": "d1", "scene_id": "sc1", "sort_order": 0}],
    )
    _patch(monkeypatch, store)
    result = svc.get_call_sheet("cs1")
    assert result["id"] == "cs1"
    assert len(result["crew"]) == 1 and result["crew"][0]["crew"]["contact"]["name"] == "Gary"
    assert len(result["cast"]) == 1 and result["cast"][0]["casting"]["character_name"] == "HERO"
    assert len(result["locations"]) == 1 and result["locations"][0]["location"]["name"] == "Warehouse"
    assert len(result["scenes"]) == 1 and result["scenes"][0]["scene_number"] == "1"


def test_update_call_sheet_day_info_fields(monkeypatch):
    store = _store(call_sheets=[{"id": "cs1", "production_id": "p1",
                                 "shooting_day_id": "d1", "status": "draft"}])
    _patch(monkeypatch, store)
    result = svc.update_call_sheet("cs1", {"weather": "Sunny, 24C", "nearest_hospital": "General Hospital"})
    assert result["weather"] == "Sunny, 24C"
    assert result["nearest_hospital"] == "General Hospital"


def test_update_call_sheet_not_found(monkeypatch):
    _patch(monkeypatch, _store())
    assert svc.update_call_sheet("nope", {"weather": "x"}) is svc.NOT_FOUND


def test_update_call_sheet_ignores_unknown_fields(monkeypatch):
    store = _store(call_sheets=[{"id": "cs1", "production_id": "p1",
                                 "shooting_day_id": "d1", "status": "draft"}])
    _patch(monkeypatch, store)
    svc.update_call_sheet("cs1", {"production_id": "HACKED"})
    assert store["call_sheets"][0]["production_id"] == "p1"


def test_update_call_sheet_status_draft_to_published(monkeypatch):
    store = _store(call_sheets=[{"id": "cs1", "production_id": "p1",
                                 "shooting_day_id": "d1", "status": "draft"}])
    _patch(monkeypatch, store)
    result = svc.update_call_sheet("cs1", {"status": "published"})
    assert result["status"] == "published"


def test_update_call_sheet_status_published_to_draft_allowed_at_service_layer(monkeypatch):
    # Spec: rejecting published->draft is a UI-level convenience only, not
    # enforced here -- a correction workflow may want to flip it back.
    store = _store(call_sheets=[{"id": "cs1", "production_id": "p1",
                                 "shooting_day_id": "d1", "status": "published"}])
    _patch(monkeypatch, store)
    result = svc.update_call_sheet("cs1", {"status": "draft"})
    assert result["status"] == "draft"


def test_add_crew_happy_path(monkeypatch):
    store = _store(
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        production_crew=[{"id": "cr1", "production_id": "p1", "contact_id": "c1", "role": "Gaffer"}],
        contacts=[{"id": "c1", "name": "Gary"}],
    )
    _patch(monkeypatch, store)
    result = svc.add_crew("cs1", "cr1", call_time="06:00", notes="bring rain gear")
    assert result["crew"]["contact"]["name"] == "Gary"
    assert result["call_time"] == "06:00"
    assert len(store["call_sheet_crew"]) == 1


def test_add_crew_missing_call_sheet_is_not_found(monkeypatch):
    _patch(monkeypatch, _store())
    assert svc.add_crew("nope", "cr1") == "not_found"


def test_add_crew_from_different_production_is_rejected(monkeypatch):
    store = _store(
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        production_crew=[{"id": "cr9", "production_id": "OTHER", "contact_id": "c1"}],
    )
    _patch(monkeypatch, store)
    assert svc.add_crew("cs1", "cr9") == "cross_production"
    assert store["call_sheet_crew"] == []


def test_remove_crew(monkeypatch):
    store = _store(
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        call_sheet_crew=[{"id": "csc1", "call_sheet_id": "cs1", "crew_id": "cr1"}],
    )
    _patch(monkeypatch, store)
    svc.remove_crew("cs1", "cr1")
    assert store["call_sheet_crew"] == []


def test_add_cast_happy_path(monkeypatch):
    store = _store(
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        casting=[{"id": "ca1", "script_id": "s1", "character_name": "HERO"}],
    )
    _patch(monkeypatch, store)
    result = svc.add_cast("cs1", "ca1", call_time="07:00", status_code="SW")
    assert result["casting"]["character_name"] == "HERO"
    assert result["status_code"] == "SW"


def test_add_cast_missing_call_sheet_is_not_found(monkeypatch):
    _patch(monkeypatch, _store())
    assert svc.add_cast("nope", "ca1") == "not_found"


def test_add_cast_rejects_different_script_same_production(monkeypatch):
    # The bug a loose "same production" check would have allowed: a
    # production can hold multiple scripts (e.g. Episode 1 and Episode 2).
    # This shooting day belongs to script s1; ca1 belongs to script s2 --
    # even though both scripts could be under production p1, casting from
    # s2 must NOT be addable to a call sheet for a s1 shooting day.
    store = _store(
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        casting=[{"id": "ca_other", "script_id": "s2_different_episode", "character_name": "VILLAIN"}],
    )
    _patch(monkeypatch, store)
    assert svc.add_cast("cs1", "ca_other") == "cross_script"
    assert store["call_sheet_cast"] == []


def test_remove_cast(monkeypatch):
    store = _store(
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        call_sheet_cast=[{"id": "csx1", "call_sheet_id": "cs1", "casting_id": "ca1"}],
    )
    _patch(monkeypatch, store)
    svc.remove_cast("cs1", "ca1")
    assert store["call_sheet_cast"] == []


def test_add_location_happy_path(monkeypatch):
    store = _store(
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        locations=[{"id": "l1", "name": "Warehouse"}],
    )
    _patch(monkeypatch, store)
    result = svc.add_location("cs1", "l1", is_primary=True)
    assert result["location"]["name"] == "Warehouse"
    assert result["is_primary"] is True


def test_add_location_missing_call_sheet_is_not_found(monkeypatch):
    _patch(monkeypatch, _store())
    assert svc.add_location("nope", "l1") == "not_found"


def test_add_second_primary_demotes_first(monkeypatch):
    store = _store(
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        locations=[{"id": "l1", "name": "Warehouse"}, {"id": "l2", "name": "Backlot"}],
        call_sheet_locations=[{"id": "csl1", "call_sheet_id": "cs1", "location_id": "l1", "is_primary": True}],
    )
    _patch(monkeypatch, store)
    svc.add_location("cs1", "l2", is_primary=True)
    primaries = [r for r in store["call_sheet_locations"] if r["is_primary"]]
    assert len(primaries) == 1
    assert primaries[0]["location_id"] == "l2"


def test_add_non_primary_does_not_demote_existing_primary(monkeypatch):
    store = _store(
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        locations=[{"id": "l1", "name": "Warehouse"}, {"id": "l2", "name": "Backlot"}],
        call_sheet_locations=[{"id": "csl1", "call_sheet_id": "cs1", "location_id": "l1", "is_primary": True}],
    )
    _patch(monkeypatch, store)
    svc.add_location("cs1", "l2", is_primary=False)
    primaries = [r for r in store["call_sheet_locations"] if r["is_primary"]]
    assert len(primaries) == 1 and primaries[0]["location_id"] == "l1"


def test_remove_location(monkeypatch):
    store = _store(
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        call_sheet_locations=[{"id": "csl1", "call_sheet_id": "cs1", "location_id": "l1"}],
    )
    _patch(monkeypatch, store)
    svc.remove_location("cs1", "l1")
    assert store["call_sheet_locations"] == []


def _full_call_sheet_store():
    return _store(
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1",
                     "status": "draft", "weather": "Sunny", "nearest_hospital": "General"}],
        shooting_days=[{"id": "d1", "schedule_id": "sch1", "day_number": 4, "shoot_date": "2026-10-01"}],
        production_crew=[{"id": "cr1", "production_id": "p1", "contact_id": "c1",
                          "role": "Gaffer", "department_code": "camera",
                          "job_rate": 4000}],
        contacts=[{"id": "c1", "name": "Gary", "phone": "0821112222", "standard_rate": 4500}],
        call_sheet_crew=[{"id": "csc1", "call_sheet_id": "cs1", "crew_id": "cr1", "call_time": "06:00"}],
        casting=[{"id": "ca1", "script_id": "s1", "character_name": "HERO", "actor_name": "Jo"}],
        call_sheet_cast=[{"id": "csx1", "call_sheet_id": "cs1", "casting_id": "ca1",
                          "call_time": "07:00", "status_code": "SW"}],
        locations=[{"id": "l1", "name": "Warehouse", "address": "1 Main St", "parking_notes": "Lot B"}],
        call_sheet_locations=[{"id": "csl1", "call_sheet_id": "cs1", "location_id": "l1", "is_primary": True}],
        scenes=[{"id": "sc1", "scene_number": "1", "int_ext": "INT", "setting": "WAREHOUSE",
                 "time_of_day": "DAY", "page_length_eighths": 8}],
        shooting_day_scenes=[{"shooting_day_id": "d1", "scene_id": "sc1", "sort_order": 0}],
    )


def test_redact_roster_hides_rates_keeps_phone_and_email(monkeypatch):
    store = _full_call_sheet_store()
    _patch(monkeypatch, store)
    data = svc.get_call_sheet("cs1")
    redacted = svc.redact_roster(data, can_view_sensitive=False)
    assert "job_rate" not in redacted["crew"][0]["crew"]
    assert "standard_rate" not in redacted["crew"][0]["crew"]["contact"]
    # Deliberate narrowing vs. the crew-tab behaviour: phone always visible here.
    assert redacted["crew"][0]["crew"]["contact"]["phone"] == "0821112222"


def test_redact_roster_shows_rates_for_sensitive_viewer(monkeypatch):
    store = _full_call_sheet_store()
    _patch(monkeypatch, store)
    data = svc.get_call_sheet("cs1")
    redacted = svc.redact_roster(data, can_view_sensitive=True)
    assert redacted["crew"][0]["crew"]["job_rate"] == 4000
    assert redacted["crew"][0]["crew"]["contact"]["standard_rate"] == 4500


def test_render_call_sheet_pdf_returns_pdf_bytes(monkeypatch):
    store = _full_call_sheet_store()
    _patch(monkeypatch, store)
    monkeypatch.setattr(ds, "get_departments_list", lambda: [{"code": "camera", "name": "Camera", "color": "#1"}])
    pdf_bytes = svc.render_call_sheet_pdf("cs1")
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


def test_render_call_sheet_pdf_not_found(monkeypatch):
    _patch(monkeypatch, _store())
    assert svc.render_call_sheet_pdf("nope") is svc.NOT_FOUND
