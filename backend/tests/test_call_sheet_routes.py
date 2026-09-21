"""Route tests for call_sheet_bp — auth/role matrix + roster wiring.

MockTable/MockSupabase copied from tests/test_production_crew_routes.py.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_service as cs_svc
import middleware.production_authz as pa
from middleware.auth import DEV_USER_ID
from postgrest.exceptions import APIError


def _ilike_match(cell, pattern):
    c = str(cell or "").lower()
    p = str(pattern).lower()
    if "%" in p:
        return p.strip("%") in c
    return c == p


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
            # NOTE: this mock does not enforce UNIQUE constraints (e.g.
            # call_sheet_crew's UNIQUE (call_sheet_id, crew_id)) -- a second
            # insert() for a row that should collide will silently succeed
            # here instead of raising a postgrest APIError like the real DB
            # would. That's why the "editing a call time causes a duplicate
            # key error" class of bug (see update_crew_call/update_cast_call)
            # can't be caught by a test built on this mock alone; those
            # functions are tested for correct UPDATE-not-INSERT behavior
            # directly instead.
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
    from routes.call_sheet_routes import call_sheet_bp
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(call_sheet_bp)
    return app.test_client()


def _store(**overrides):
    base = {
        "productions": [{"id": "p1", "owner_id": DEV_USER_ID, "title": "Farm Feature"}],
        "shooting_days": [{"id": "d1", "schedule_id": "sch1", "day_number": 1, "shoot_date": "2026-10-01"}],
        "shooting_schedules": [{"id": "sch1", "script_id": "s1"}],
        "scripts": [{"id": "s1", "production_id": "p1"}],
        "call_sheets": [], "call_sheet_crew": [], "call_sheet_cast": [], "call_sheet_locations": [],
        "shooting_day_scenes": [], "scenes": [],
        "production_crew": [], "contacts": [], "casting": [], "locations": [],
        "production_members": [], "production_locations": [],
    }
    base.update(overrides)
    return base


def _patch(monkeypatch, store):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    mock = MockSupabase(store)
    monkeypatch.setattr(cs_svc, "get_supabase_admin", lambda: mock)
    monkeypatch.setattr(pa, "get_supabase_admin", lambda: mock)
    monkeypatch.setattr(pa, "get_user_id", lambda: DEV_USER_ID)


def test_create_call_sheet_owner_ok(monkeypatch):
    _patch(monkeypatch, _store())
    resp = _client().post("/api/shooting-days/d1/call-sheet")
    assert resp.status_code == 200
    assert resp.get_json()["call_sheet"]["shooting_day_id"] == "d1"


def test_create_call_sheet_unassociated_script_is_404(monkeypatch):
    _patch(monkeypatch, _store(scripts=[{"id": "s1", "production_id": None}]))
    resp = _client().post("/api/shooting-days/d1/call-sheet")
    assert resp.status_code == 404


def test_create_call_sheet_anon_is_401(monkeypatch):
    _patch(monkeypatch, _store())
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().post("/api/shooting-days/d1/call-sheet")
    assert resp.status_code == 401


def test_create_call_sheet_non_member_is_403(monkeypatch):
    store = _store(productions=[{"id": "p1", "owner_id": "other", "title": "Theirs"}])
    _patch(monkeypatch, store)
    resp = _client().post("/api/shooting-days/d1/call-sheet")
    assert resp.status_code == 403


def _member_store(role, **flags):
    row = {"production_id": "p1", "user_id": DEV_USER_ID, "role": role,
           "can_view_sensitive": False, "can_edit_crew": False,
           "can_manage_members": False, "can_edit_production": False,
           "can_edit_call_sheets": False}
    row.update(flags)
    return _store(
        productions=[{"id": "p1", "owner_id": "other", "title": "Farm Feature"}],
        production_members=[row],
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
    )


def test_viewer_can_get_call_sheet(monkeypatch):
    _patch(monkeypatch, _member_store("viewer"))
    resp = _client().get("/api/call-sheets/cs1")
    assert resp.status_code == 200


def test_viewer_cannot_patch_call_sheet(monkeypatch):
    _patch(monkeypatch, _member_store("viewer"))
    resp = _client().patch("/api/call-sheets/cs1", json={"weather": "Rainy"})
    assert resp.status_code == 403


def test_viewer_cannot_add_roster(monkeypatch):
    _patch(monkeypatch, _member_store("viewer"))
    assert _client().post("/api/call-sheets/cs1/crew", json={"crew_id": "cr1"}).status_code == 403
    assert _client().post("/api/call-sheets/cs1/cast", json={"casting_id": "ca1"}).status_code == 403
    assert _client().post("/api/call-sheets/cs1/locations", json={"location_id": "l1"}).status_code == 403


def test_coordinator_with_flag_can_edit(monkeypatch):
    _patch(monkeypatch, _member_store("coordinator", can_edit_call_sheets=True))
    resp = _client().patch("/api/call-sheets/cs1", json={"weather": "Rainy"})
    assert resp.status_code == 200
    assert resp.get_json()["call_sheet"]["weather"] == "Rainy"


def test_coordinator_without_flag_cannot_edit(monkeypatch):
    _patch(monkeypatch, _member_store("coordinator", can_edit_call_sheets=False))
    resp = _client().patch("/api/call-sheets/cs1", json={"weather": "Rainy"})
    assert resp.status_code == 403


def test_admin_can_edit(monkeypatch):
    _patch(monkeypatch, _member_store("admin", can_edit_call_sheets=True))
    resp = _client().patch("/api/call-sheets/cs1", json={"weather": "Rainy"})
    assert resp.status_code == 200


def test_call_sheet_in_different_production_is_403_for_non_member(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID}, {"id": "p2", "owner_id": "other"}],
        call_sheets=[{"id": "cs_other", "production_id": "p2", "shooting_day_id": "d2", "status": "draft"}],
    )
    _patch(monkeypatch, store)
    resp = _client().get("/api/call-sheets/cs_other")
    assert resp.status_code == 403  # DEV_USER_ID is not a member of p2


def test_add_and_remove_crew(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID}],
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        production_crew=[{"id": "cr1", "production_id": "p1", "contact_id": "c1"}],
        contacts=[{"id": "c1", "name": "Gary"}],
    )
    _patch(monkeypatch, store)
    resp = _client().post("/api/call-sheets/cs1/crew", json={"crew_id": "cr1", "call_time": "06:00"})
    assert resp.status_code == 201
    resp2 = _client().delete("/api/call-sheets/cs1/crew/cr1")
    assert resp2.status_code == 200
    assert store["call_sheet_crew"] == []


def test_add_cast_cross_script_is_400(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID}],
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        casting=[{"id": "ca_other", "script_id": "different_script"}],
    )
    _patch(monkeypatch, store)
    resp = _client().post("/api/call-sheets/cs1/cast", json={"casting_id": "ca_other"})
    assert resp.status_code == 400


def test_get_pdf_viewer_ok_edit_forbidden(monkeypatch):
    _patch(monkeypatch, _member_store("viewer"))
    resp = _client().get("/api/call-sheets/cs1/pdf")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"


# --- Finding 1: redaction bypass on the crew-add response -----------------

def test_add_crew_response_redacts_rate_for_coordinator_without_sensitive_flag(monkeypatch):
    # Regression: add_call_sheet_crew used to jsonify svc.add_crew's result
    # directly, skipping redact_roster entirely -- so a coordinator denied
    # can_view_sensitive on GET still got job_rate/standard_rate back in the
    # POST response body.
    store = _member_store("coordinator", can_edit_call_sheets=True, can_view_sensitive=False)
    store["production_crew"] = [{"id": "cr1", "production_id": "p1", "contact_id": "c1",
                                  "role": "Gaffer", "job_rate": 4000}]
    store["contacts"] = [{"id": "c1", "name": "Gary", "standard_rate": 4500}]
    _patch(monkeypatch, store)
    resp = _client().post("/api/call-sheets/cs1/crew", json={"crew_id": "cr1"})
    assert resp.status_code == 201
    crew = resp.get_json()["crew"]
    assert "job_rate" not in crew["crew"]
    assert "standard_rate" not in crew["crew"]["contact"]


def test_add_crew_response_shows_rate_for_sensitive_viewer(monkeypatch):
    store = _member_store("coordinator", can_edit_call_sheets=True, can_view_sensitive=True)
    store["production_crew"] = [{"id": "cr1", "production_id": "p1", "contact_id": "c1",
                                  "role": "Gaffer", "job_rate": 4000}]
    store["contacts"] = [{"id": "c1", "name": "Gary", "standard_rate": 4500}]
    _patch(monkeypatch, store)
    resp = _client().post("/api/call-sheets/cs1/crew", json={"crew_id": "cr1"})
    assert resp.status_code == 201
    crew = resp.get_json()["crew"]
    assert crew["crew"]["job_rate"] == 4000
    assert crew["crew"]["contact"]["standard_rate"] == 4500


# --- Finding 2: call-time edits on existing rows must UPDATE, not insert --

def test_patch_crew_call_time_updates_existing_row_no_duplicate(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID}],
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        production_crew=[{"id": "cr1", "production_id": "p1", "contact_id": "c1"}],
        contacts=[{"id": "c1", "name": "Gary"}],
    )
    _patch(monkeypatch, store)
    add_resp = _client().post("/api/call-sheets/cs1/crew", json={"crew_id": "cr1", "call_time": "06:00"})
    assert add_resp.status_code == 201
    patch_resp = _client().patch("/api/call-sheets/cs1/crew/cr1", json={"call_time": "07:30"})
    assert patch_resp.status_code == 200
    assert patch_resp.get_json()["crew"]["call_time"] == "07:30"
    assert len(store["call_sheet_crew"]) == 1  # updated in place, not duplicated


def test_patch_cast_call_time_updates_existing_row_no_duplicate(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID}],
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        casting=[{"id": "ca1", "script_id": "s1", "character_name": "HERO"}],
    )
    _patch(monkeypatch, store)
    add_resp = _client().post("/api/call-sheets/cs1/cast", json={"casting_id": "ca1", "call_time": "07:00"})
    assert add_resp.status_code == 201
    patch_resp = _client().patch("/api/call-sheets/cs1/cast/ca1", json={"call_time": "08:15"})
    assert patch_resp.status_code == 200
    assert patch_resp.get_json()["cast"]["call_time"] == "08:15"
    assert len(store["call_sheet_cast"]) == 1


def test_patch_crew_call_time_missing_row_is_404(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID}],
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
    )
    _patch(monkeypatch, store)
    resp = _client().patch("/api/call-sheets/cs1/crew/cr_missing", json={"call_time": "07:30"})
    assert resp.status_code == 404


def test_viewer_cannot_patch_crew_call_time(monkeypatch):
    _patch(monkeypatch, _member_store("viewer"))
    resp = _client().patch("/api/call-sheets/cs1/crew/cr1", json={"call_time": "07:30"})
    assert resp.status_code == 403


# --- Finding 4: add_location must validate the location is linked to the
# call sheet's production ----------------------------------------------

def test_add_location_not_linked_to_production_is_400(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID}],
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        locations=[{"id": "l_other", "name": "Someone Else's Warehouse"}],
    )
    _patch(monkeypatch, store)
    resp = _client().post("/api/call-sheets/cs1/locations", json={"location_id": "l_other"})
    assert resp.status_code == 400
    assert store["call_sheet_locations"] == []


def test_add_location_linked_to_production_succeeds(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID}],
        call_sheets=[{"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}],
        locations=[{"id": "l1", "name": "Warehouse"}],
        production_locations=[{"id": "pl1", "production_id": "p1", "location_id": "l1"}],
    )
    _patch(monkeypatch, store)
    resp = _client().post("/api/call-sheets/cs1/locations", json={"location_id": "l1"})
    assert resp.status_code == 201


# --- Finding 5: viewers can GET a call sheet by day without creating one --

def test_viewer_can_get_call_sheet_by_day_without_creating(monkeypatch):
    _patch(monkeypatch, _member_store("viewer"))
    resp = _client().get("/api/shooting-days/d1/call-sheet")
    assert resp.status_code == 200
    assert resp.get_json()["call_sheet"]["id"] == "cs1"


def test_viewer_get_call_sheet_by_day_404_when_none_exists_and_creates_nothing(monkeypatch):
    row = {"production_id": "p1", "user_id": DEV_USER_ID, "role": "viewer",
           "can_view_sensitive": False, "can_edit_crew": False,
           "can_manage_members": False, "can_edit_production": False,
           "can_edit_call_sheets": False}
    store = _store(
        productions=[{"id": "p1", "owner_id": "other", "title": "Farm Feature"}],
        production_members=[row],
    )
    _patch(monkeypatch, store)
    resp = _client().get("/api/shooting-days/d1/call-sheet")
    assert resp.status_code == 404
    assert store["call_sheets"] == []  # GET must never create a row as a side effect


def test_get_call_sheet_by_day_anon_is_401(monkeypatch):
    _patch(monkeypatch, _store())
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().get("/api/shooting-days/d1/call-sheet")
    assert resp.status_code == 401
