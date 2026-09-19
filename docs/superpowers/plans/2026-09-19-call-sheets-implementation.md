# Call Sheets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship build-sequence step 4 — a per-shooting-day call sheet (day info,
roster, locations, live scene list) with PDF export, gated by the newer
production-role authz system.

**Architecture:** New migration (`054_call_sheets.sql`) adds four tables plus
one capability column on two existing tables. A new `services/call_sheet_service.py`
holds all data logic (get-or-create, roster/location CRUD, PDF rendering); a
new `routes/call_sheet_routes.py` blueprint exposes it, gated entirely by
`middleware.production_authz.require_production_role`. Two new resolvers
(`from_call_sheet_id`, `from_shooting_day_id`) bridge the call sheet's
`shooting_day_id` anchor into the production-role world. The frontend adds a
`CallSheetEditor` reachable from each shoot-day column in the existing
Kanban schedule UI (`ShootingSchedulePage.jsx` / `DayColumn.jsx`), plus one
new checkbox row in the existing `ProductionMembersTab.jsx`.

**Tech Stack:** Flask (Python 3.13) + supabase-py (service-role key) on the
backend; WeasyPrint for PDF rendering (already a dependency via
`report_service.py`); React 18 + Vite (plain JS/JSX) on the frontend.

**Spec:** `docs/superpowers/specs/2026-09-18-call-sheets-design.md`

## Global Constraints

- Migrations are applied **manually** against the Supabase project — `run_migration.py` is dead. This plan does not run migration 054 against a live DB; it only writes the file and validates it against the spec's table definitions.
- Every new table uses `gen_random_uuid()` PKs and reuses the `update_shooting_updated_at()` trigger function from migration 030 — do not write a new trigger function.
- RLS on all four new tables is an **owner-only backstop**, never relied on by the app (service-role key bypasses it).
- Call sheet routes are gated by `require_production_role` (production axis), never `require_script_role` — this is a deliberate, named fork (see spec's "permission-system fork" section).
- Spec calls the CSS helper `report_service._get_pdf_css()`; the **real** method on `ReportService` is `_get_report_css()` (verified by reading `backend/services/report_service.py:2074`). Use the real name — `report_service.report_service._get_report_css()` (the module-level singleton at `report_service.py:2947`).
- `production_crew_service._redact()` is NOT reused for the call-sheet roster — it bundles fields in a way that can't isolate "hide rate, keep phone." Write a small call-sheet-specific redaction helper instead.
- Backend tests use the repo's existing `MockTable`/`MockSupabase` chainable in-memory stand-in (copied verbatim across `tests/test_production_crew_routes.py`, `tests/test_production_authz.py`, etc.) — do not add a new mocking approach.
- Gate frontend work on `npm run build` (not `npm run lint`, which is broken repo-wide per project memory); gate backend work on `pytest tests/`.

---

## File Structure

**Backend — new files:**
- `backend/db/migrations/054_call_sheets.sql` — schema.
- `backend/services/call_sheet_service.py` — all call-sheet data logic.
- `backend/routes/call_sheet_routes.py` — `call_sheet_bp`.
- `backend/tests/test_call_sheet_service.py`
- `backend/tests/test_call_sheet_routes.py`

**Backend — modified files:**
- `backend/middleware/production_authz.py` — add `can_edit_call_sheets` to `CAPABILITIES`, add `from_call_sheet_id`, `from_shooting_day_id`.
- `backend/services/production_member_service.py` — add `can_edit_call_sheets: True` to the hardcoded `'coordinator'` preset.
- `backend/tests/test_production_member_routes.py` — update `test_apply_role_preset_admin` / `test_apply_role_preset_coordinator` for the new key; add a coordinator-preset-contains-key regression test.
- `backend/tests/test_production_authz.py` — add resolver tests.
- `backend/tests/test_route_enforcement.py` — extend with a `call_sheet_bp` marker-coverage test.
- `backend/app.py` — register `call_sheet_bp`.

**Frontend — new files:**
- `frontend/src/components/schedule/CallSheetEditor.jsx` — day-info form + roster/location pickers + publish + PDF download.
- `frontend/src/components/schedule/CallSheetEditor.css` — styling (new file; the schedule folder has no shared stylesheet for modals beyond `ShootingSchedule.css`, so a dedicated file keeps this self-contained).

**Frontend — modified files:**
- `frontend/src/services/apiService.js` — new call-sheet functions block.
- `frontend/src/components/schedule/DayColumn.jsx` — "Call Sheet" action in the column header.
- `frontend/src/components/schedule/ShootingSchedulePage.jsx` — owns the open/close state for `CallSheetEditor` and passes a handler down to `DayColumn`.
- `frontend/src/components/productions/ProductionMembersTab.jsx` — add `can_edit_call_sheets` to `CAP_LABELS` and `PRESETS`.

---

### Task 1: Migration `054_call_sheets.sql`

**Files:**
- Create: `backend/db/migrations/054_call_sheets.sql`

**Interfaces:**
- Produces: tables `call_sheets`, `call_sheet_locations`, `call_sheet_crew`, `call_sheet_cast`; columns `production_members.can_edit_call_sheets`, `production_invites.can_edit_call_sheets`. All later tasks assume these exact names/columns exist.

- [ ] **Step 1: Write the migration file**

```sql
-- Migration 054: Call sheets (build-sequence step 4)
-- See docs/superpowers/specs/2026-09-18-call-sheets-design.md
-- Apply manually against the Supabase project (run_migration.py is dead).
--
-- Call sheets are anchored to a shooting_day (script-role world) but their
-- content (crew, cast, locations) belongs to the production-role world.
-- Gated by require_production_role, not require_script_role -- see the
-- spec's "permission-system fork" section. production_id is denormalized
-- onto call_sheets at creation time so every permission check afterwards
-- is a single-column lookup, not a join chain.

-- ============================================
-- 0. New capability column on the existing production-role tables
-- ============================================
ALTER TABLE production_members
    ADD COLUMN IF NOT EXISTS can_edit_call_sheets boolean NOT NULL DEFAULT false;
ALTER TABLE production_invites
    ADD COLUMN IF NOT EXISTS can_edit_call_sheets boolean NOT NULL DEFAULT false;

-- ============================================
-- 1. call_sheets -- one per shooting_day (single-unit scope: UNIQUE)
-- ============================================
CREATE TABLE IF NOT EXISTS call_sheets (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_id    UUID NOT NULL REFERENCES productions(id) ON DELETE CASCADE,
    shooting_day_id  UUID NOT NULL UNIQUE REFERENCES shooting_days(id) ON DELETE CASCADE,
    status           TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published')),
    weather          TEXT,
    sunrise_time     TIME,
    sunset_time      TIME,
    breakfast_time   TIME,
    lunch_time       TIME,
    nearest_hospital TEXT,
    parking_notes    TEXT,
    safety_notes     TEXT,
    general_notes    TEXT,
    created_by       UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_call_sheets_production ON call_sheets(production_id);

CREATE TRIGGER trg_call_sheets_updated
    BEFORE UPDATE ON call_sheets
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

-- ============================================
-- 2. call_sheet_locations
-- ============================================
CREATE TABLE IF NOT EXISTS call_sheet_locations (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_sheet_id UUID NOT NULL REFERENCES call_sheets(id) ON DELETE CASCADE,
    location_id   UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    is_primary    BOOLEAN NOT NULL DEFAULT false,
    sort_order    INT NOT NULL DEFAULT 0,
    UNIQUE (call_sheet_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_call_sheet_locations_sheet ON call_sheet_locations(call_sheet_id);

-- ============================================
-- 3. call_sheet_crew
-- ============================================
CREATE TABLE IF NOT EXISTS call_sheet_crew (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_sheet_id UUID NOT NULL REFERENCES call_sheets(id) ON DELETE CASCADE,
    crew_id       UUID NOT NULL REFERENCES production_crew(id) ON DELETE CASCADE,
    call_time     TIME,
    notes         TEXT,
    UNIQUE (call_sheet_id, crew_id)
);

CREATE INDEX IF NOT EXISTS idx_call_sheet_crew_sheet ON call_sheet_crew(call_sheet_id);

-- ============================================
-- 4. call_sheet_cast
-- ============================================
CREATE TABLE IF NOT EXISTS call_sheet_cast (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_sheet_id UUID NOT NULL REFERENCES call_sheets(id) ON DELETE CASCADE,
    casting_id    UUID NOT NULL REFERENCES casting(id) ON DELETE CASCADE,
    call_time     TIME,
    status_code   TEXT,
    notes         TEXT,
    UNIQUE (call_sheet_id, casting_id)
);

CREATE INDEX IF NOT EXISTS idx_call_sheet_cast_sheet ON call_sheet_cast(call_sheet_id);

-- ============================================
-- 5. RLS -- owner-only, direct-client backstop only
-- ============================================
ALTER TABLE call_sheets ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_sheet_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_sheet_crew ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_sheet_cast ENABLE ROW LEVEL SECURITY;

CREATE POLICY "owner manages call sheets"
    ON call_sheets FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = call_sheets.production_id
                  AND p.owner_id = auth.uid())
    );

CREATE POLICY "owner manages call sheet locations"
    ON call_sheet_locations FOR ALL USING (
        EXISTS (SELECT 1 FROM call_sheets cs
                JOIN productions p ON p.id = cs.production_id
                WHERE cs.id = call_sheet_locations.call_sheet_id
                  AND p.owner_id = auth.uid())
    );

CREATE POLICY "owner manages call sheet crew"
    ON call_sheet_crew FOR ALL USING (
        EXISTS (SELECT 1 FROM call_sheets cs
                JOIN productions p ON p.id = cs.production_id
                WHERE cs.id = call_sheet_crew.call_sheet_id
                  AND p.owner_id = auth.uid())
    );

CREATE POLICY "owner manages call sheet cast"
    ON call_sheet_cast FOR ALL USING (
        EXISTS (SELECT 1 FROM call_sheets cs
                JOIN productions p ON p.id = cs.production_id
                WHERE cs.id = call_sheet_cast.call_sheet_id
                  AND p.owner_id = auth.uid())
    );
```

- [ ] **Step 2: Validate against the spec's data-model tables**

Re-read the spec's "Data model" section (`call_sheets`, `call_sheet_locations`,
`call_sheet_crew`, `call_sheet_cast` tables) and confirm every column, type,
constraint, and index in the file above matches. There is no automated
migration test in this repo (confirmed: `grep -rl "054\|053_locations" tests/`
returns nothing) — this is a manual read-through, not a pytest step.

- [ ] **Step 3: Commit**

```bash
git add backend/db/migrations/054_call_sheets.sql
git commit -m "feat(db): add call_sheets schema (migration 054)"
```

---

### Task 2: `production_authz.py` — capability + resolvers

**Files:**
- Modify: `backend/middleware/production_authz.py`
- Test: `backend/tests/test_production_authz.py`

**Interfaces:**
- Consumes: `_lookup_production_id(table, id_value, id_col='id')` (existing helper in this file, `production_authz.py:78`).
- Produces: `CAPABILITIES` now includes `'can_edit_call_sheets'`; `from_call_sheet_id(kwargs)` and `from_shooting_day_id(kwargs)` — both take the Flask route's `kwargs` dict and return a `production_id` string or `None`. Task 11 imports both.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_production_authz.py` (uses the file's existing
`MockTable`/`MockSupabase`/`store` fixtures already in that file — read the
top of the file first for the exact fixture shape before adding below the
last test):

```python
def test_can_edit_call_sheets_in_capabilities():
    assert 'can_edit_call_sheets' in pa.CAPABILITIES


def test_from_call_sheet_id_resolves_production(monkeypatch):
    store = {'call_sheets': [{'id': 'cs1', 'production_id': 'p1'}]}
    monkeypatch.setattr(pa, 'get_supabase_admin', lambda: MockSupabase(store))
    assert pa.from_call_sheet_id({'call_sheet_id': 'cs1'}) == 'p1'


def test_from_call_sheet_id_missing_returns_none(monkeypatch):
    monkeypatch.setattr(pa, 'get_supabase_admin', lambda: MockSupabase({'call_sheets': []}))
    assert pa.from_call_sheet_id({'call_sheet_id': 'nope'}) is None


def test_from_shooting_day_id_resolves_through_chain(monkeypatch):
    store = {
        'shooting_days': [{'id': 'd1', 'schedule_id': 'sch1'}],
        'shooting_schedules': [{'id': 'sch1', 'script_id': 's1'}],
        'scripts': [{'id': 's1', 'production_id': 'p1'}],
    }
    monkeypatch.setattr(pa, 'get_supabase_admin', lambda: MockSupabase(store))
    assert pa.from_shooting_day_id({'day_id': 'd1'}) == 'p1'


def test_from_shooting_day_id_unassociated_script_returns_none(monkeypatch):
    store = {
        'shooting_days': [{'id': 'd1', 'schedule_id': 'sch1'}],
        'shooting_schedules': [{'id': 'sch1', 'script_id': 's1'}],
        'scripts': [{'id': 's1', 'production_id': None}],
    }
    monkeypatch.setattr(pa, 'get_supabase_admin', lambda: MockSupabase(store))
    assert pa.from_shooting_day_id({'day_id': 'd1'}) is None


def test_from_shooting_day_id_missing_day_returns_none(monkeypatch):
    monkeypatch.setattr(pa, 'get_supabase_admin', lambda: MockSupabase({'shooting_days': []}))
    assert pa.from_shooting_day_id({'day_id': 'missing'}) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_production_authz.py -k "call_sheet or shooting_day" -v`
Expected: FAIL — `AttributeError: module 'middleware.production_authz' has no attribute 'from_call_sheet_id'` (and `'can_edit_call_sheets' in pa.CAPABILITIES` is `False`).

- [ ] **Step 3: Implement**

In `backend/middleware/production_authz.py`, change line 21-23:

```python
CAPABILITIES = (
    'can_view_sensitive', 'can_edit_crew', 'can_manage_members', 'can_edit_production',
    'can_edit_call_sheets',
)
```

Add after `from_production_location_id` (after line 103):

```python
def from_call_sheet_id(kwargs):
    return _lookup_production_id('call_sheets', kwargs.get('call_sheet_id'))


def from_shooting_day_id(kwargs):
    """Resolve production_id via shooting_day -> shooting_schedule -> script
    -> scripts.production_id. Returns None (-> 404) if the day doesn't exist
    OR if the script has never been associated with a production -- these
    two cases are deliberately indistinguishable to the caller (see spec's
    corrected error-shape note)."""
    day_id = kwargs.get('day_id')
    if not day_id:
        return None
    admin = get_supabase_admin()
    day_res = (admin.table('shooting_days').select('schedule_id')
               .eq('id', day_id).limit(1).execute())
    if not day_res.data:
        return None
    schedule_id = day_res.data[0].get('schedule_id')
    sched_res = (admin.table('shooting_schedules').select('script_id')
                 .eq('id', schedule_id).limit(1).execute())
    if not sched_res.data:
        return None
    script_id = sched_res.data[0].get('script_id')
    script_res = (admin.table('scripts').select('production_id')
                  .eq('id', script_id).limit(1).execute())
    if not script_res.data:
        return None
    return script_res.data[0].get('production_id')
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_production_authz.py -v`
Expected: PASS (all tests, including the pre-existing ones).

- [ ] **Step 5: Commit**

```bash
git add backend/middleware/production_authz.py backend/tests/test_production_authz.py
git commit -m "feat(authz): add can_edit_call_sheets capability and call-sheet resolvers"
```

---

### Task 3: `production_member_service.py` — coordinator preset + regression test

**Files:**
- Modify: `backend/services/production_member_service.py`
- Test: `backend/tests/test_production_member_routes.py`

**Interfaces:**
- Consumes: `CAPABILITIES` from `middleware.production_authz` (now includes `can_edit_call_sheets`, from Task 2).
- Produces: `ROLE_PRESETS['coordinator']` now includes `can_edit_call_sheets: True`. Task 4+ services don't depend on this directly, but any coordinator-role test fixture across the suite should now get the key when calling `apply_role_preset`.

- [ ] **Step 1: Update the two exact-equality tests (would otherwise fail once CAPABILITIES grows)**

In `backend/tests/test_production_member_routes.py`, replace:

```python
def test_apply_role_preset_admin():
    assert pms.apply_role_preset("admin", None) == {
        "can_view_sensitive": True, "can_edit_crew": True,
        "can_manage_members": True, "can_edit_production": True}


def test_apply_role_preset_coordinator():
    assert pms.apply_role_preset("coordinator", None) == {
        "can_view_sensitive": False, "can_edit_crew": True,
        "can_manage_members": False, "can_edit_production": False}
```

with:

```python
def test_apply_role_preset_admin():
    assert pms.apply_role_preset("admin", None) == {
        "can_view_sensitive": True, "can_edit_crew": True,
        "can_manage_members": True, "can_edit_production": True,
        "can_edit_call_sheets": True}


def test_apply_role_preset_coordinator():
    assert pms.apply_role_preset("coordinator", None) == {
        "can_view_sensitive": False, "can_edit_crew": True,
        "can_manage_members": False, "can_edit_production": False,
        "can_edit_call_sheets": True}


def test_coordinator_preset_contains_call_sheets_key():
    # Regression: 'coordinator' is a hardcoded literal dict in ROLE_PRESETS
    # (unlike 'admin'/'viewer', which are dict-comprehensions over
    # CAPABILITIES). A missing key here is NOT caught by the NOT NULL
    # DEFAULT false column on insert -- it silently becomes False. Assert
    # the key is actually PRESENT with the intended value, not just that
    # inserts don't error.
    assert 'can_edit_call_sheets' in pms.ROLE_PRESETS['coordinator']
    assert pms.ROLE_PRESETS['coordinator']['can_edit_call_sheets'] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_production_member_routes.py -k "apply_role_preset or coordinator_preset" -v`
Expected: FAIL — dict mismatch (missing `can_edit_call_sheets` key) on all three.

- [ ] **Step 3: Implement**

In `backend/services/production_member_service.py`, change:

```python
ROLE_PRESETS = {
    'admin':       {c: True for c in CAPABILITIES},
    'coordinator': {'can_view_sensitive': False, 'can_edit_crew': True,
                    'can_manage_members': False, 'can_edit_production': False},
    'viewer':      {c: False for c in CAPABILITIES},
}
```

to:

```python
ROLE_PRESETS = {
    'admin':       {c: True for c in CAPABILITIES},
    'coordinator': {'can_view_sensitive': False, 'can_edit_crew': True,
                    'can_manage_members': False, 'can_edit_production': False,
                    'can_edit_call_sheets': True},
    'viewer':      {c: False for c in CAPABILITIES},
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_production_member_routes.py -v`
Expected: PASS (full file, not just the three new/changed tests — confirms no other test asserted the old 4-key shape).

- [ ] **Step 5: Commit**

```bash
git add backend/services/production_member_service.py backend/tests/test_production_member_routes.py
git commit -m "feat(members): add can_edit_call_sheets to coordinator role preset"
```

---

### Task 4: `call_sheet_service.py` — get-or-create + fetch with roster/locations/scenes

**Files:**
- Create: `backend/services/call_sheet_service.py`
- Test: `backend/tests/test_call_sheet_service.py`

**Interfaces:**
- Consumes: `db.supabase_client.get_supabase_admin()`. No dependency on Tasks 2/3 code (service layer doesn't call authz directly — routes do).
- Produces: `NOT_FOUND` sentinel; `get_or_create(shooting_day_id, user_id)` → dict call-sheet row (or a `'no_production'` string sentinel — routes map this to 404, matching the corrected error-shape note); `get_call_sheet(call_sheet_id)` → `{**call_sheet_row, 'crew': [...], 'cast': [...], 'locations': [...], 'scenes': [...]}` or `NOT_FOUND`. Tasks 5-8 add more functions to this same module; Task 9 (routes) imports `NOT_FOUND`, `get_or_create`, `get_call_sheet`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_call_sheet_service.py`:

```python
"""Service-layer tests for call_sheet_service.py.

MockTable/MockSupabase copied from tests/test_production_crew_routes.py —
this repo's standard chainable in-memory supabase-py stand-in.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_service as svc
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
    assert len(result["crew"]) == 1 and result["crew"][0]["contact"]["name"] == "Gary"
    assert len(result["cast"]) == 1 and result["cast"][0]["casting"]["character_name"] == "HERO"
    assert len(result["locations"]) == 1 and result["locations"][0]["location"]["name"] == "Warehouse"
    assert len(result["scenes"]) == 1 and result["scenes"][0]["scene_number"] == "1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_call_sheet_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.call_sheet_service'`.

- [ ] **Step 3: Implement**

Create `backend/services/call_sheet_service.py`:

```python
"""Call sheet CRUD, roster/location assembly, and PDF rendering
(build-sequence step 4).

Gated at the route layer by middleware.production_authz.require_production_role
-- this module trusts its caller already passed that check. See
docs/superpowers/specs/2026-09-18-call-sheets-design.md for the full design,
including the "permission-system fork" note on why this is production-authz
scoped despite being anchored to a shooting_day (script-role world).
"""
from db.supabase_client import get_supabase_admin

NOT_FOUND = object()

DAY_INFO_FIELDS = (
    "weather", "sunrise_time", "sunset_time", "breakfast_time", "lunch_time",
    "nearest_hospital", "parking_notes", "safety_notes", "general_notes",
)


def _resolve_production_id(supabase, shooting_day_id):
    """shooting_day -> shooting_schedule -> script -> scripts.production_id.
    None if the day doesn't exist OR the script has no production."""
    day_res = (supabase.table("shooting_days").select("schedule_id")
               .eq("id", shooting_day_id).limit(1).execute())
    if not day_res.data:
        return None
    sched_res = (supabase.table("shooting_schedules").select("script_id")
                 .eq("id", day_res.data[0].get("schedule_id")).limit(1).execute())
    if not sched_res.data:
        return None
    script_id = sched_res.data[0].get("script_id")
    script_res = (supabase.table("scripts").select("production_id")
                  .eq("id", script_id).limit(1).execute())
    if not script_res.data:
        return None
    return script_res.data[0].get("production_id"), script_id


def _script_id_for_day(supabase, shooting_day_id):
    """Just the script_id (used by add_cast's cross-script check)."""
    day_res = (supabase.table("shooting_days").select("schedule_id")
               .eq("id", shooting_day_id).limit(1).execute())
    if not day_res.data:
        return None
    sched_res = (supabase.table("shooting_schedules").select("script_id")
                 .eq("id", day_res.data[0].get("schedule_id")).limit(1).execute())
    return sched_res.data[0].get("script_id") if sched_res.data else None


def _get(supabase, call_sheet_id):
    res = (supabase.table("call_sheets").select("*")
           .eq("id", call_sheet_id).limit(1).execute())
    return res.data[0] if res.data else None


def get_or_create(shooting_day_id, user_id):
    """Idempotent: returns the existing call_sheets row for this day, or
    creates one. Returns the string 'no_production' if the day doesn't
    exist or its script has no production association -- callers map this
    to a 404 (indistinguishable from "day doesn't exist" per the spec's
    corrected error-shape note; the route's require_production_role
    decorator gives the same 404 for both cases before this function is
    even reached in the normal flow, but get_or_create is also exercised
    directly in these service tests)."""
    supabase = get_supabase_admin()
    existing = (supabase.table("call_sheets").select("*")
                .eq("shooting_day_id", shooting_day_id).limit(1).execute())
    if existing.data:
        return existing.data[0]
    resolved = _resolve_production_id(supabase, shooting_day_id)
    if not resolved or not resolved[0]:
        return "no_production"
    production_id, _script_id = resolved
    row = {"production_id": production_id, "shooting_day_id": shooting_day_id,
           "created_by": user_id}
    return supabase.table("call_sheets").insert(row).execute().data[0]


def _embed_crew(supabase, rows):
    if not rows:
        return rows
    crew_ids = {r["crew_id"] for r in rows}
    crew = (supabase.table("production_crew").select("*")
            .in_("id", list(crew_ids)).execute().data or [])
    crew_by_id = {c["id"]: c for c in crew}
    contact_ids = {c["contact_id"] for c in crew if c.get("contact_id")}
    contacts = (supabase.table("contacts").select("*")
                .in_("id", list(contact_ids)).execute().data or []) if contact_ids else []
    contacts_by_id = {c["id"]: c for c in contacts}
    for r in rows:
        crew_row = dict(crew_by_id.get(r["crew_id"]) or {})
        crew_row["contact"] = contacts_by_id.get(crew_row.get("contact_id"))
        r["crew"] = crew_row
    return rows


def _embed_cast(supabase, rows):
    if not rows:
        return rows
    casting_ids = {r["casting_id"] for r in rows}
    casting = (supabase.table("casting").select("*")
               .in_("id", list(casting_ids)).execute().data or [])
    casting_by_id = {c["id"]: c for c in casting}
    for r in rows:
        r["casting"] = casting_by_id.get(r["casting_id"])
    return rows


def _embed_locations(supabase, rows):
    if not rows:
        return rows
    location_ids = {r["location_id"] for r in rows}
    locations = (supabase.table("locations").select("*")
                 .in_("id", list(location_ids)).execute().data or [])
    locations_by_id = {l["id"]: l for l in locations}
    for r in rows:
        r["location"] = locations_by_id.get(r["location_id"])
    return rows


def get_day_scenes(supabase, shooting_day_id):
    """The day's live scene list -- NOT stored on the call sheet, read fresh
    from shooting_day_scenes + scenes every time. A scene reassigned to a
    different day stays in sync automatically while the sheet is draft."""
    ds_rows = (supabase.table("shooting_day_scenes").select("*")
               .eq("shooting_day_id", shooting_day_id)
               .order("sort_order", desc=False).execute().data or [])
    scene_ids = {r["scene_id"] for r in ds_rows}
    scenes = (supabase.table("scenes").select("*")
              .in_("id", list(scene_ids)).execute().data or []) if scene_ids else []
    scenes_by_id = {s["id"]: s for s in scenes}
    ordered = []
    for ds in ds_rows:
        s = scenes_by_id.get(ds["scene_id"])
        if s:
            ordered.append(s)
    return ordered


def get_call_sheet(call_sheet_id):
    supabase = get_supabase_admin()
    row = _get(supabase, call_sheet_id)
    if not row:
        return NOT_FOUND
    crew = (supabase.table("call_sheet_crew").select("*")
            .eq("call_sheet_id", call_sheet_id).execute().data or [])
    cast = (supabase.table("call_sheet_cast").select("*")
            .eq("call_sheet_id", call_sheet_id).execute().data or [])
    locations = (supabase.table("call_sheet_locations").select("*")
                 .eq("call_sheet_id", call_sheet_id)
                 .order("sort_order", desc=False).execute().data or [])
    return {
        **row,
        "crew": _embed_crew(supabase, crew),
        "cast": _embed_cast(supabase, cast),
        "locations": _embed_locations(supabase, locations),
        "scenes": get_day_scenes(supabase, row["shooting_day_id"]),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_call_sheet_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/call_sheet_service.py backend/tests/test_call_sheet_service.py
git commit -m "feat(call-sheets): add get-or-create and fetch-with-roster service logic"
```

---

### Task 5: `call_sheet_service.py` — day-info update + status transition

**Files:**
- Modify: `backend/services/call_sheet_service.py`
- Test: `backend/tests/test_call_sheet_service.py`

**Interfaces:**
- Consumes: `_get(supabase, call_sheet_id)`, `DAY_INFO_FIELDS`, `NOT_FOUND` (Task 4).
- Produces: `update_call_sheet(call_sheet_id, fields)` → updated row dict or `NOT_FOUND`. Task 9 (routes) calls this directly.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_call_sheet_service.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_call_sheet_service.py -k update_call_sheet -v`
Expected: FAIL — `AttributeError: module 'services.call_sheet_service' has no attribute 'update_call_sheet'`.

- [ ] **Step 3: Implement**

Append to `backend/services/call_sheet_service.py`:

```python
def update_call_sheet(call_sheet_id, fields):
    supabase = get_supabase_admin()
    if not _get(supabase, call_sheet_id):
        return NOT_FOUND
    patch = {f: fields[f] for f in DAY_INFO_FIELDS if f in fields}
    if "status" in fields and fields["status"] in ("draft", "published"):
        patch["status"] = fields["status"]
    if not patch:
        return _get(supabase, call_sheet_id)
    res = (supabase.table("call_sheets").update(patch)
           .eq("id", call_sheet_id).execute())
    return res.data[0] if res.data else NOT_FOUND
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_call_sheet_service.py -v`
Expected: PASS (full file).

- [ ] **Step 5: Commit**

```bash
git add backend/services/call_sheet_service.py backend/tests/test_call_sheet_service.py
git commit -m "feat(call-sheets): add day-info update and status transition"
```

---

### Task 6: `call_sheet_service.py` — crew roster add/remove

**Files:**
- Modify: `backend/services/call_sheet_service.py`
- Test: `backend/tests/test_call_sheet_service.py`

**Interfaces:**
- Consumes: `_get(supabase, call_sheet_id)` (Task 4).
- Produces: `add_crew(call_sheet_id, crew_id, call_time=None, notes=None)` → embedded row dict, or `'not_found'` (bad call_sheet_id) / `'cross_production'` (crew belongs to a different production); `remove_crew(call_sheet_id, crew_id)` → `None`. Task 9 (routes) calls both directly.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_call_sheet_service.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_call_sheet_service.py -k "add_crew or remove_crew" -v`
Expected: FAIL — `AttributeError: ... has no attribute 'add_crew'`.

- [ ] **Step 3: Implement**

Append to `backend/services/call_sheet_service.py`:

```python
def add_crew(call_sheet_id, crew_id, call_time=None, notes=None):
    supabase = get_supabase_admin()
    sheet = _get(supabase, call_sheet_id)
    if not sheet:
        return "not_found"
    crew_res = (supabase.table("production_crew").select("*")
                .eq("id", crew_id).limit(1).execute())
    if not crew_res.data or crew_res.data[0].get("production_id") != sheet["production_id"]:
        return "cross_production"
    row = {"call_sheet_id": call_sheet_id, "crew_id": crew_id,
           "call_time": call_time, "notes": notes}
    created = supabase.table("call_sheet_crew").insert(row).execute().data[0]
    return _embed_crew(supabase, [created])[0]


def remove_crew(call_sheet_id, crew_id):
    (get_supabase_admin().table("call_sheet_crew").delete()
     .eq("call_sheet_id", call_sheet_id).eq("crew_id", crew_id).execute())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_call_sheet_service.py -v`
Expected: PASS (full file).

- [ ] **Step 5: Commit**

```bash
git add backend/services/call_sheet_service.py backend/tests/test_call_sheet_service.py
git commit -m "feat(call-sheets): add crew roster add/remove with cross-production guard"
```

---

### Task 7: `call_sheet_service.py` — cast roster add/remove (cross-script guard)

**Files:**
- Modify: `backend/services/call_sheet_service.py`
- Test: `backend/tests/test_call_sheet_service.py`

**Interfaces:**
- Consumes: `_get`, `_script_id_for_day` (Task 4).
- Produces: `add_cast(call_sheet_id, casting_id, call_time=None, status_code=None, notes=None)` → embedded row dict, or `'not_found'` / `'cross_script'`; `remove_cast(call_sheet_id, casting_id)` → `None`. Task 9 (routes) calls both directly.

**This is the test the spec calls out explicitly** — a `casting_id` from a
*different script that shares the same production* must be rejected, not
just a casting_id from a different production (the `casting` table has no
`production_id` column at all — only `script_id` — so "same production" is
never even the check being performed; it must be "same script as this
shooting day's script").

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_call_sheet_service.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_call_sheet_service.py -k "add_cast or remove_cast" -v`
Expected: FAIL — `AttributeError: ... has no attribute 'add_cast'`.

- [ ] **Step 3: Implement**

Append to `backend/services/call_sheet_service.py`:

```python
def add_cast(call_sheet_id, casting_id, call_time=None, status_code=None, notes=None):
    supabase = get_supabase_admin()
    sheet = _get(supabase, call_sheet_id)
    if not sheet:
        return "not_found"
    script_id = _script_id_for_day(supabase, sheet["shooting_day_id"])
    casting_res = (supabase.table("casting").select("*")
                   .eq("id", casting_id).limit(1).execute())
    if not casting_res.data or casting_res.data[0].get("script_id") != script_id:
        return "cross_script"
    row = {"call_sheet_id": call_sheet_id, "casting_id": casting_id,
           "call_time": call_time, "status_code": status_code, "notes": notes}
    created = supabase.table("call_sheet_cast").insert(row).execute().data[0]
    return _embed_cast(supabase, [created])[0]


def remove_cast(call_sheet_id, casting_id):
    (get_supabase_admin().table("call_sheet_cast").delete()
     .eq("call_sheet_id", call_sheet_id).eq("casting_id", casting_id).execute())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_call_sheet_service.py -v`
Expected: PASS (full file).

- [ ] **Step 5: Commit**

```bash
git add backend/services/call_sheet_service.py backend/tests/test_call_sheet_service.py
git commit -m "feat(call-sheets): add cast roster add/remove with cross-script guard"
```

---

### Task 8: `call_sheet_service.py` — locations add/remove with primary demotion

**Files:**
- Modify: `backend/services/call_sheet_service.py`
- Test: `backend/tests/test_call_sheet_service.py`

**Interfaces:**
- Consumes: `_get` (Task 4).
- Produces: `add_location(call_sheet_id, location_id, is_primary=False)` → embedded row dict or `'not_found'`; `remove_location(call_sheet_id, location_id)` → `None`. Task 9 (routes) calls both directly.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_call_sheet_service.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_call_sheet_service.py -k "add_location or remove_location" -v`
Expected: FAIL — `AttributeError: ... has no attribute 'add_location'`.

- [ ] **Step 3: Implement**

Append to `backend/services/call_sheet_service.py`:

```python
def add_location(call_sheet_id, location_id, is_primary=False):
    supabase = get_supabase_admin()
    if not _get(supabase, call_sheet_id):
        return "not_found"
    if is_primary:
        (supabase.table("call_sheet_locations").update({"is_primary": False})
         .eq("call_sheet_id", call_sheet_id).execute())
    row = {"call_sheet_id": call_sheet_id, "location_id": location_id, "is_primary": bool(is_primary)}
    created = supabase.table("call_sheet_locations").insert(row).execute().data[0]
    return _embed_locations(supabase, [created])[0]


def remove_location(call_sheet_id, location_id):
    (get_supabase_admin().table("call_sheet_locations").delete()
     .eq("call_sheet_id", call_sheet_id).eq("location_id", location_id).execute())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_call_sheet_service.py -v`
Expected: PASS (full file).

- [ ] **Step 5: Commit**

```bash
git add backend/services/call_sheet_service.py backend/tests/test_call_sheet_service.py
git commit -m "feat(call-sheets): add location add/remove with primary demotion"
```

---

### Task 9: `call_sheet_service.py` — redaction helper + PDF rendering

**Files:**
- Modify: `backend/services/call_sheet_service.py`
- Test: `backend/tests/test_call_sheet_service.py`

**Interfaces:**
- Consumes: `get_call_sheet` (Task 4); `report_service.report_service._get_report_css()` (existing, `backend/services/report_service.py:2074` and `:2947`); `services.department_service.get_departments_list()` (existing).
- Produces: `redact_roster(call_sheet_data, can_view_sensitive)` — mutates and returns the dict from `get_call_sheet`, stripping `job_rate`/`standard_rate`; `render_call_sheet_pdf(call_sheet_id)` → `bytes`. Task 10 (routes) calls both.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_call_sheet_service.py`:

```python
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
```

Add the missing import at the top of the test file (next to the existing
imports):

```python
import services.department_service as ds
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_call_sheet_service.py -k "redact_roster or render_call_sheet_pdf" -v`
Expected: FAIL — `AttributeError: ... has no attribute 'redact_roster'`.

- [ ] **Step 3: Implement**

Append to `backend/services/call_sheet_service.py`. First add the two new
top-of-file imports (WeasyPrint, matching `report_service.py`'s
try/except-guarded import pattern, plus `report_service` and
`department_service`):

```python
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from services.report_service import report_service
from services import department_service
```

Then append the redaction + rendering functions:

```python
# Call-sheet-specific redaction. NOT production_crew_service._redact(): that
# function bundles job_rate (crew) with phone AND standard_rate (contact) as
# one all-or-nothing unit, so it can't isolate "hide rate, keep phone." A
# call sheet's entire purpose is day-of contact info, so phone/email are
# always shown to anyone who can view the sheet -- only rate fields are
# gated by can_view_sensitive.
_SENSITIVE_CREW = ("job_rate",)
_SENSITIVE_CONTACT = ("standard_rate",)


def redact_roster(call_sheet_data, can_view_sensitive):
    if can_view_sensitive:
        return call_sheet_data
    for row in call_sheet_data.get("crew", []):
        crew = row.get("crew")
        if isinstance(crew, dict):
            for k in _SENSITIVE_CREW:
                crew.pop(k, None)
            contact = crew.get("contact")
            if isinstance(contact, dict):
                for k in _SENSITIVE_CONTACT:
                    contact.pop(k, None)
    return call_sheet_data


def _esc(value):
    import html as _html
    return _html.escape(str(value)) if value is not None else ""


def _render_pdf_html(data, day):
    status = data.get("status", "draft")
    draft_banner = '<div class="cs-draft-banner">DRAFT</div>' if status == "draft" else ""

    day_info = (
        f'<div class="cs-day-info">'
        f'<span>Weather: {_esc(data.get("weather") or "-")}</span>'
        f'<span>Sunrise: {_esc(data.get("sunrise_time") or "-")}</span>'
        f'<span>Sunset: {_esc(data.get("sunset_time") or "-")}</span>'
        f'<span>Breakfast: {_esc(data.get("breakfast_time") or "-")}</span>'
        f'<span>Lunch: {_esc(data.get("lunch_time") or "-")}</span>'
        f'</div>'
    )

    locs = sorted(data.get("locations", []), key=lambda r: (not r.get("is_primary"), r.get("sort_order", 0)))
    loc_html = "".join(
        f'<div class="cs-location"><strong>{_esc((l.get("location") or {}).get("name"))}</strong>'
        f'{" (Primary)" if l.get("is_primary") else ""}<br>'
        f'{_esc((l.get("location") or {}).get("address") or "")}<br>'
        f'Parking: {_esc((l.get("location") or {}).get("parking_notes") or "-")}</div>'
        for l in locs
    )

    scene_rows = "".join(
        f'<tr><td>{_esc(s.get("scene_number"))}</td><td>{_esc(s.get("int_ext"))}</td>'
        f'<td>{_esc(s.get("setting") or s.get("location_canonical"))}</td>'
        f'<td>{_esc(s.get("time_of_day"))}</td><td>{s.get("page_length_eighths", 8)}/8</td></tr>'
        for s in data.get("scenes", [])
    )

    cast_rows = "".join(
        f'<tr><td>{_esc((c.get("casting") or {}).get("character_name"))}</td>'
        f'<td>{_esc((c.get("casting") or {}).get("actor_name"))}</td>'
        f'<td>{_esc(c.get("status_code") or "")}</td><td>{_esc(c.get("call_time") or "")}</td></tr>'
        for c in data.get("cast", [])
    )

    dept_order = [d["code"] for d in department_service.get_departments_list()]
    crew_rows = data.get("crew", [])
    crew_by_dept = {}
    for row in crew_rows:
        code = (row.get("crew") or {}).get("department_code")
        crew_by_dept.setdefault(code, []).append(row)
    crew_sections = []
    for code in dept_order + [c for c in crew_by_dept if c not in dept_order]:
        rows = crew_by_dept.get(code)
        if not rows:
            continue
        label = department_service.get_department_name(code) if code else "Other"
        rows_html = "".join(
            f'<tr><td>{_esc((r.get("crew") or {}).get("contact", {}).get("name"))}</td>'
            f'<td>{_esc((r.get("crew") or {}).get("role") or "")}</td>'
            f'<td>{_esc(r.get("call_time") or "")}</td></tr>'
            for r in rows
        )
        crew_sections.append(f'<h4>{_esc(label)}</h4><table class="report-table">{rows_html}</table>')

    return f"""
    <html><body>
    {draft_banner}
    <div class="cs-header"><h1>Day {day.get("day_number")} &middot; {_esc(day.get("shoot_date") or "")}</h1></div>
    {day_info}
    <h3>Locations</h3>{loc_html}
    <h3>Scene Schedule</h3><table class="report-table">
      <thead><tr><th>Sc</th><th>I/E</th><th>Set</th><th>D/N</th><th>Pgs</th></tr></thead>
      <tbody>{scene_rows}</tbody></table>
    <h3>Cast Call List</h3><table class="report-table">
      <thead><tr><th>Character</th><th>Actor</th><th>Status</th><th>Call Time</th></tr></thead>
      <tbody>{cast_rows}</tbody></table>
    <h3>Crew Call List</h3>{''.join(crew_sections)}
    <div class="cs-footer">
      <p>Nearest Hospital: {_esc(data.get("nearest_hospital") or "-")}</p>
      <p>Safety/COVID: {_esc(data.get("safety_notes") or "-")}</p>
      <p>{_esc(data.get("general_notes") or "")}</p>
    </div>
    </body></html>
    """


def render_call_sheet_pdf(call_sheet_id):
    if not WEASYPRINT_AVAILABLE:
        raise ImportError("weasyprint is not installed")
    supabase = get_supabase_admin()
    data = get_call_sheet(call_sheet_id)
    if data is NOT_FOUND:
        return NOT_FOUND
    day_res = (supabase.table("shooting_days").select("*")
               .eq("id", data["shooting_day_id"]).limit(1).execute())
    day = day_res.data[0] if day_res.data else {}
    html_content = _render_pdf_html(data, day)
    css = report_service._get_report_css()
    from weasyprint import CSS
    return HTML(string=html_content).write_pdf(stylesheets=[CSS(string=css)])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_call_sheet_service.py -v`
Expected: PASS (full file). If WeasyPrint's system dependencies (Pango/Cairo)
aren't available in the execution environment, `test_render_call_sheet_pdf_returns_pdf_bytes`
will fail with an `OSError` from `weasyprint` itself, not from this code —
confirm `python -c "import weasyprint"` succeeds standalone first; report_service.py's
existing PDF path already depends on this working in this environment.

- [ ] **Step 5: Commit**

```bash
git add backend/services/call_sheet_service.py backend/tests/test_call_sheet_service.py
git commit -m "feat(call-sheets): add roster redaction and PDF rendering"
```

---

### Task 10: `routes/call_sheet_routes.py` + `app.py` registration

**Files:**
- Create: `backend/routes/call_sheet_routes.py`
- Modify: `backend/app.py`
- Test: `backend/tests/test_call_sheet_routes.py`

**Interfaces:**
- Consumes: `middleware.production_authz.{require_production_role, from_call_sheet_id, from_shooting_day_id}` (Task 2); `services.call_sheet_service.*` (Tasks 4-9).
- Produces: `call_sheet_bp` registered at root (`/api/shooting-days/<day_id>/call-sheet`, `/api/call-sheets/<call_sheet_id>...`). Nothing downstream in this plan consumes this blueprint directly, but Task 11 (route-enforcement test) inspects its view functions' `_authz_min_role`/`_authz_capability` markers.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_call_sheet_routes.py`. This reuses the
`MockTable`/`MockSupabase` pattern from `test_production_crew_routes.py`
(copy it verbatim — see that file's `MockTable`/`MockSupabase` classes,
lines 36-147) plus the `_member_store` role-matrix helper pattern from the
same file (lines 401-417).

```python
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
        "production_members": [],
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_call_sheet_routes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'routes.call_sheet_routes'`.

- [ ] **Step 3: Implement**

Create `backend/routes/call_sheet_routes.py`:

```python
"""Call sheet HTTP routes. Logic in services/call_sheet_service.py.
Gated by middleware.production_authz.require_production_role -- see
docs/superpowers/specs/2026-09-18-call-sheets-design.md's
"permission-system fork" section for why (production-role, not
script-role, despite the shooting_day anchor)."""
from flask import Blueprint, request, jsonify, g, Response

from middleware.auth import require_auth, get_user_id
from middleware.production_authz import (
    require_production_role, from_call_sheet_id, from_shooting_day_id,
)
from services import call_sheet_service as svc

call_sheet_bp = Blueprint("call_sheet", __name__)


@call_sheet_bp.route("/api/shooting-days/<day_id>/call-sheet", methods=["POST"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_shooting_day_id)
def get_or_create_call_sheet(day_id):
    result = svc.get_or_create(day_id, get_user_id())
    if result == "no_production":
        return jsonify({"error": "Not found"}), 404
    return jsonify({"call_sheet": result})


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>", methods=["GET"])
@require_auth
@require_production_role(min_role="viewer", resolver=from_call_sheet_id)
def get_call_sheet(call_sheet_id):
    result = svc.get_call_sheet(call_sheet_id)
    if result is svc.NOT_FOUND:
        return jsonify({"error": "Call sheet not found"}), 404
    result = svc.redact_roster(result, g.production_access["can_view_sensitive"])
    return jsonify({"call_sheet": result})


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>", methods=["PATCH"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def update_call_sheet(call_sheet_id):
    data = request.get_json(silent=True) or {}
    result = svc.update_call_sheet(call_sheet_id, data)
    if result is svc.NOT_FOUND:
        return jsonify({"error": "Call sheet not found"}), 404
    return jsonify({"call_sheet": result})


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/crew", methods=["POST"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def add_call_sheet_crew(call_sheet_id):
    data = request.get_json(silent=True) or {}
    crew_id = data.get("crew_id")
    if not crew_id:
        return jsonify({"error": "crew_id is required"}), 400
    result = svc.add_crew(call_sheet_id, crew_id, data.get("call_time"), data.get("notes"))
    if result == "not_found":
        return jsonify({"error": "Call sheet not found"}), 404
    if result == "cross_production":
        return jsonify({"error": "That crew member is not part of this production"}), 400
    return jsonify({"crew": result}), 201


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/crew/<crew_id>", methods=["DELETE"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def remove_call_sheet_crew(call_sheet_id, crew_id):
    svc.remove_crew(call_sheet_id, crew_id)
    return jsonify({"success": True})


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/cast", methods=["POST"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def add_call_sheet_cast(call_sheet_id):
    data = request.get_json(silent=True) or {}
    casting_id = data.get("casting_id")
    if not casting_id:
        return jsonify({"error": "casting_id is required"}), 400
    result = svc.add_cast(call_sheet_id, casting_id, data.get("call_time"),
                          data.get("status_code"), data.get("notes"))
    if result == "not_found":
        return jsonify({"error": "Call sheet not found"}), 404
    if result == "cross_script":
        return jsonify({"error": "That cast member is not part of this shooting day's script"}), 400
    return jsonify({"cast": result}), 201


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/cast/<casting_id>", methods=["DELETE"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def remove_call_sheet_cast(call_sheet_id, casting_id):
    svc.remove_cast(call_sheet_id, casting_id)
    return jsonify({"success": True})


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/locations", methods=["POST"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def add_call_sheet_location(call_sheet_id):
    data = request.get_json(silent=True) or {}
    location_id = data.get("location_id")
    if not location_id:
        return jsonify({"error": "location_id is required"}), 400
    result = svc.add_location(call_sheet_id, location_id, bool(data.get("is_primary")))
    if result == "not_found":
        return jsonify({"error": "Call sheet not found"}), 404
    return jsonify({"location": result}), 201


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/locations/<location_id>", methods=["DELETE"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def remove_call_sheet_location(call_sheet_id, location_id):
    svc.remove_location(call_sheet_id, location_id)
    return jsonify({"success": True})


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/pdf", methods=["GET"])
@require_auth
@require_production_role(min_role="viewer", resolver=from_call_sheet_id)
def download_call_sheet_pdf(call_sheet_id):
    pdf_bytes = svc.render_call_sheet_pdf(call_sheet_id)
    if pdf_bytes is svc.NOT_FOUND:
        return jsonify({"error": "Call sheet not found"}), 404
    return Response(pdf_bytes, mimetype="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=call_sheet.pdf"})
```

In `backend/app.py`, add the import next to the other route imports (after
`from routes.location_routes import locations_bp`):

```python
from routes.call_sheet_routes import call_sheet_bp
```

And the registration next to `production_bp` (after
`app.register_blueprint(locations_bp)`):

```python
app.register_blueprint(call_sheet_bp)  # Call sheet routes at /api/shooting-days/:id/call-sheet, /api/call-sheets/*
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_call_sheet_routes.py -v`
Expected: PASS. Note `test_get_pdf_viewer_ok_edit_forbidden` exercises real
WeasyPrint rendering through the full HTTP stack (same caveat as Task 9
Step 4 about system Pango/Cairo dependencies).

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && pytest tests/ -v`
Expected: PASS — confirms Task 3's `ROLE_PRESETS` change and Task 2's
`CAPABILITIES` growth didn't break any other test in the suite.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/call_sheet_routes.py backend/tests/test_call_sheet_routes.py backend/app.py
git commit -m "feat(call-sheets): add call_sheet_bp routes gated by production_authz"
```

---

### Task 11: `test_route_enforcement.py` — extend for `call_sheet_bp`

**Files:**
- Modify: `backend/tests/test_route_enforcement.py`

**Interfaces:**
- Consumes: `routes.call_sheet_routes.call_sheet_bp` (Task 10).
- Produces: a new test function guarding against a future call-sheet route being added without the `require_production_role` decorator.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_route_enforcement.py`:

```python
def test_call_sheet_routes_carry_authz_marker():
    """Every call_sheet_bp route must carry require_production_role -- i.e.
    expose an _authz_min_role or _authz_capability marker on its view
    function. Mirrors test_production_scoped_routes_carry_authz_marker
    above, for the separate call_sheet_bp blueprint."""
    from routes.call_sheet_routes import call_sheet_bp
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(call_sheet_bp)

    SCOPED_ARGS = {"day_id", "call_sheet_id", "crew_id", "casting_id", "location_id"}

    for rule in app.url_map.iter_rules():
        if not rule.endpoint.startswith("call_sheet."):
            continue
        if not (set(rule.arguments) & SCOPED_ARGS):
            continue
        view = app.view_functions[rule.endpoint]
        assert hasattr(view, "_authz_min_role") or hasattr(view, "_authz_capability"), \
            f"{rule.endpoint} is call-sheet-scoped but has no require_production_role marker"
```

- [ ] **Step 2: Run test to verify it fails first, without Task 10's markers, then passes**

This test can only meaningfully fail if Task 10's routes lack markers, which
they don't (every route in Task 10 carries `require_production_role`).
Run: `cd backend && pytest tests/test_route_enforcement.py -v`
Expected: PASS immediately (this is a regression guard, not new
functionality — confirm it passes, and confirm it would fail by
temporarily commenting out one `@require_production_role(...)` line in
`call_sheet_routes.py`, running the test again to see it fail, then
restoring the line).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_route_enforcement.py
git commit -m "test(call-sheets): extend route-enforcement guard to call_sheet_bp"
```

---

### Task 12: Frontend `apiService.js` — call sheet functions

**Files:**
- Modify: `frontend/src/services/apiService.js`

**Interfaces:**
- Consumes: the shared `api` axios instance already configured at the top of `apiService.js` (attaches the cached Supabase JWT to every request — confirmed existing pattern, do not create a new instance).
- Produces: `getOrCreateCallSheet(dayId)`, `getCallSheet(callSheetId)`, `updateCallSheet(callSheetId, payload)`, `addCallSheetCrew(callSheetId, payload)`, `removeCallSheetCrew(callSheetId, crewId)`, `addCallSheetCast(callSheetId, payload)`, `removeCallSheetCast(callSheetId, castingId)`, `addCallSheetLocation(callSheetId, payload)`, `removeCallSheetLocation(callSheetId, locationId)`, `downloadCallSheetPdf(callSheetId, dayNumber)`. Task 13's `CallSheetEditor.jsx` imports all of these.

There is no automated test harness for `apiService.js` in this repo (it's a
thin axios wrapper, verified by grepping `frontend/src` for existing
`*.test.js` files targeting `apiService.js` — none exist for other function
blocks either). Verification for this task is `npm run build` succeeding
(catches syntax errors) plus Task 13's manual browser check exercising
these functions end-to-end.

- [ ] **Step 1: Add the new functions block**

Add to `frontend/src/services/apiService.js`, after the
`importProductionCrew` function (around line 2623, right before the
`// Locations directory...` section comment) — placed here rather than
after the locations block since the file has no existing "call sheets"
section and this keeps it adjacent to the other production-scoped
functions:

```javascript
// ============================================
// Call sheets (build-sequence step 4)
// ============================================

export const getOrCreateCallSheet = async (dayId) => {
    try {
        const response = await api.post(`/api/shooting-days/${dayId}/call-sheet`);
        return response.data;
    } catch (error) {
        console.error('Error creating call sheet:', error);
        throw error;
    }
};

export const getCallSheet = async (callSheetId) => {
    try {
        const response = await api.get(`/api/call-sheets/${callSheetId}`);
        return response.data;
    } catch (error) {
        console.error('Error getting call sheet:', error);
        throw error;
    }
};

export const updateCallSheet = async (callSheetId, payload) => {
    try {
        const response = await api.patch(`/api/call-sheets/${callSheetId}`, payload);
        return response.data;
    } catch (error) {
        console.error('Error updating call sheet:', error);
        throw error;
    }
};

export const addCallSheetCrew = async (callSheetId, payload) => {
    try {
        const response = await api.post(`/api/call-sheets/${callSheetId}/crew`, payload);
        return response.data;
    } catch (error) {
        console.error('Error adding call sheet crew:', error);
        throw error;
    }
};

export const removeCallSheetCrew = async (callSheetId, crewId) => {
    try {
        const response = await api.delete(`/api/call-sheets/${callSheetId}/crew/${crewId}`);
        return response.data;
    } catch (error) {
        console.error('Error removing call sheet crew:', error);
        throw error;
    }
};

export const addCallSheetCast = async (callSheetId, payload) => {
    try {
        const response = await api.post(`/api/call-sheets/${callSheetId}/cast`, payload);
        return response.data;
    } catch (error) {
        console.error('Error adding call sheet cast:', error);
        throw error;
    }
};

export const removeCallSheetCast = async (callSheetId, castingId) => {
    try {
        const response = await api.delete(`/api/call-sheets/${callSheetId}/cast/${castingId}`);
        return response.data;
    } catch (error) {
        console.error('Error removing call sheet cast:', error);
        throw error;
    }
};

export const addCallSheetLocation = async (callSheetId, payload) => {
    try {
        const response = await api.post(`/api/call-sheets/${callSheetId}/locations`, payload);
        return response.data;
    } catch (error) {
        console.error('Error adding call sheet location:', error);
        throw error;
    }
};

export const removeCallSheetLocation = async (callSheetId, locationId) => {
    try {
        const response = await api.delete(`/api/call-sheets/${callSheetId}/locations/${locationId}`);
        return response.data;
    } catch (error) {
        console.error('Error removing call sheet location:', error);
        throw error;
    }
};

/**
 * Download a call sheet as PDF
 * @param {string} callSheetId
 * @param {number} dayNumber - used for the downloaded filename
 * @returns {Promise<void>} Downloads the PDF file
 */
export const downloadCallSheetPdf = async (callSheetId, dayNumber) => {
    try {
        const response = await api.get(`/api/call-sheets/${callSheetId}/pdf`, {
            responseType: 'blob'
        });
        const blob = new Blob([response.data], { type: 'application/pdf' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `Call_Sheet_Day_${dayNumber || ''}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Error downloading call sheet PDF:', error);
        throw error;
    }
};
```

- [ ] **Step 2: Verify the file still builds**

Run: `cd frontend && npm run build`
Expected: build succeeds with no new errors (confirms no syntax mistakes in the added block).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/apiService.js
git commit -m "feat(call-sheets): add call sheet API client functions"
```

---

### Task 13: Frontend `CallSheetEditor.jsx` + wiring into the schedule UI

**Files:**
- Create: `frontend/src/components/schedule/CallSheetEditor.jsx`
- Create: `frontend/src/components/schedule/CallSheetEditor.css`
- Modify: `frontend/src/components/schedule/DayColumn.jsx`
- Modify: `frontend/src/components/schedule/ShootingSchedulePage.jsx`

**Interfaces:**
- Consumes: all functions from Task 12; `useToast` (`frontend/src/context/ToastContext.js`, existing, already imported in `DayColumn.jsx`); the existing `listProductionCrew(productionId)`, `listProductionLocations(productionId)`, and `getCasting(scriptId)` functions in `apiService.js` (`getCasting` confirmed at `frontend/src/services/apiService.js:2831`, returns `{casting: [...], characters: [...]}` — the `casting` array is what the cast picker lists; it's gated by the older `require_script_role('viewer')`, which the caller already holds simply by being on this script's schedule page).
- Produces: a "Call Sheet" button per shoot-day column that opens a modal to create/edit the day's call sheet, with roster pickers for crew, cast, and locations.

- [ ] **Step 1: Create the editor component**

Create `frontend/src/components/schedule/CallSheetEditor.jsx`:

```jsx
import { useState, useEffect, useCallback } from 'react';
import { X, Download } from 'lucide-react';
import {
    getOrCreateCallSheet, getCallSheet, updateCallSheet,
    addCallSheetCrew, removeCallSheetCrew,
    addCallSheetCast, removeCallSheetCast,
    addCallSheetLocation, removeCallSheetLocation,
    downloadCallSheetPdf,
    listProductionCrew, listProductionLocations, getCasting,
} from '../../services/apiService';
import { Spinner } from '../ui';
import { useToast } from '../../context/ToastContext';
import './CallSheetEditor.css';

const DAY_INFO_FIELDS = [
    ['weather', 'Weather', 'text'],
    ['sunrise_time', 'Sunrise', 'time'],
    ['sunset_time', 'Sunset', 'time'],
    ['breakfast_time', 'Breakfast', 'time'],
    ['lunch_time', 'Lunch', 'time'],
    ['nearest_hospital', 'Nearest Hospital', 'text'],
    ['parking_notes', 'Parking Notes', 'text'],
    ['safety_notes', 'Safety / COVID Officer', 'text'],
    ['general_notes', 'General Notes', 'textarea'],
];

const CallSheetEditor = ({ dayId, dayNumber, productionId, scriptId, onClose }) => {
    const toast = useToast();
    const [callSheet, setCallSheet] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [crewOptions, setCrewOptions] = useState([]);
    const [locationOptions, setLocationOptions] = useState([]);
    const [castOptions, setCastOptions] = useState([]);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const created = await getOrCreateCallSheet(dayId);
            const full = await getCallSheet(created.call_sheet.id);
            setCallSheet(full.call_sheet);
            if (productionId) {
                const [crewRes, locRes] = await Promise.all([
                    listProductionCrew(productionId),
                    listProductionLocations(productionId),
                ]);
                setCrewOptions(crewRes.crew || []);
                setLocationOptions((locRes.locations || []).map((l) => l.location || l));
            }
            if (scriptId) {
                const castRes = await getCasting(scriptId);
                setCastOptions(castRes.casting || []);
            }
        } catch (err) {
            console.error('Failed to load call sheet:', err);
            toast.error('Error', 'Could not load the call sheet for this day.');
        } finally {
            setLoading(false);
        }
    }, [dayId, productionId, scriptId, toast]);

    useEffect(() => { load(); }, [load]);

    const patchField = async (field, value) => {
        setSaving(true);
        try {
            const res = await updateCallSheet(callSheet.id, { [field]: value });
            setCallSheet((prev) => ({ ...prev, ...res.call_sheet }));
        } catch (err) {
            console.error('Failed to update call sheet:', err);
            toast.error('Update Failed', 'Could not save that change.');
        } finally {
            setSaving(false);
        }
    };

    const publish = () => patchField('status', 'published');
    const unpublish = () => patchField('status', 'draft');

    const addCrewRow = async (crewId) => {
        if (!crewId) return;
        try {
            await addCallSheetCrew(callSheet.id, { crew_id: crewId });
            await load();
        } catch (err) {
            toast.error('Error', err.response?.data?.error || 'Could not add crew member.');
        }
    };

    const removeCrewRow = async (crewId) => {
        await removeCallSheetCrew(callSheet.id, crewId);
        await load();
    };

    const addLocationRow = async (locationId) => {
        if (!locationId) return;
        try {
            await addCallSheetLocation(callSheet.id, { location_id: locationId });
            await load();
        } catch (err) {
            toast.error('Error', err.response?.data?.error || 'Could not add location.');
        }
    };

    const removeLocationRow = async (locationId) => {
        await removeCallSheetLocation(callSheet.id, locationId);
        await load();
    };

    const addCastRow = async (castingId) => {
        if (!castingId) return;
        try {
            await addCallSheetCast(callSheet.id, { casting_id: castingId });
            await load();
        } catch (err) {
            toast.error('Error', err.response?.data?.error || 'Could not add cast member.');
        }
    };

    const removeCastRow = async (castingId) => {
        await removeCallSheetCast(callSheet.id, castingId);
        await load();
    };

    if (loading || !callSheet) {
        return (
            <div className="cs-modal-backdrop" onClick={onClose}>
                <div className="cs-modal" onClick={(e) => e.stopPropagation()}><Spinner /></div>
            </div>
        );
    }

    return (
        <div className="cs-modal-backdrop" onClick={onClose}>
            <div className="cs-modal" onClick={(e) => e.stopPropagation()}>
                <div className="cs-modal-header">
                    <h3>Call Sheet &middot; Day {dayNumber}</h3>
                    <span className={`cs-status-chip cs-status-${callSheet.status}`}>{callSheet.status}</span>
                    <button className="cs-modal-close" onClick={onClose}><X size={18} /></button>
                </div>

                <div className="cs-modal-body">
                    <section className="cs-section">
                        <h4>Day Info</h4>
                        {DAY_INFO_FIELDS.map(([field, label, type]) => (
                            <label key={field} className="cs-field">
                                <span>{label}</span>
                                {type === 'textarea' ? (
                                    <textarea
                                        defaultValue={callSheet[field] || ''}
                                        onBlur={(e) => patchField(field, e.target.value)}
                                    />
                                ) : (
                                    <input
                                        type={type}
                                        defaultValue={callSheet[field] || ''}
                                        onBlur={(e) => patchField(field, e.target.value)}
                                    />
                                )}
                            </label>
                        ))}
                    </section>

                    <section className="cs-section">
                        <h4>Locations</h4>
                        <select defaultValue="" onChange={(e) => addLocationRow(e.target.value)}>
                            <option value="" disabled>Add a location…</option>
                            {locationOptions.map((l) => (
                                <option key={l.id} value={l.id}>{l.name}</option>
                            ))}
                        </select>
                        <ul className="cs-roster-list">
                            {(callSheet.locations || []).map((row) => (
                                <li key={row.id}>
                                    {row.location?.name} {row.is_primary && '(Primary)'}
                                    <button onClick={() => removeLocationRow(row.location_id)}>Remove</button>
                                </li>
                            ))}
                        </ul>
                    </section>

                    <section className="cs-section">
                        <h4>Crew</h4>
                        <select defaultValue="" onChange={(e) => addCrewRow(e.target.value)}>
                            <option value="" disabled>Add a crew member…</option>
                            {crewOptions.map((c) => (
                                <option key={c.id} value={c.id}>{c.contact?.name} — {c.role}</option>
                            ))}
                        </select>
                        <ul className="cs-roster-list">
                            {(callSheet.crew || []).map((row) => (
                                <li key={row.id}>
                                    {row.crew?.contact?.name}
                                    <input
                                        type="time"
                                        defaultValue={row.call_time || ''}
                                        onBlur={(e) => addCallSheetCrew(callSheet.id, { crew_id: row.crew_id, call_time: e.target.value }).then(load)}
                                    />
                                    <button onClick={() => removeCrewRow(row.crew_id)}>Remove</button>
                                </li>
                            ))}
                        </ul>
                    </section>

                    <section className="cs-section">
                        <h4>Cast</h4>
                        <select defaultValue="" onChange={(e) => addCastRow(e.target.value)}>
                            <option value="" disabled>Add a cast member…</option>
                            {castOptions.map((c) => (
                                <option key={c.id} value={c.id}>{c.character_name} — {c.actor_name || 'unbooked'}</option>
                            ))}
                        </select>
                        <ul className="cs-roster-list">
                            {(callSheet.cast || []).map((row) => (
                                <li key={row.id}>
                                    {row.casting?.character_name} ({row.casting?.actor_name || 'unbooked'})
                                    <input
                                        type="time"
                                        defaultValue={row.call_time || ''}
                                        onBlur={(e) => addCallSheetCast(callSheet.id, { casting_id: row.casting_id, call_time: e.target.value }).then(load)}
                                    />
                                    <button onClick={() => removeCastRow(row.casting_id)}>Remove</button>
                                </li>
                            ))}
                        </ul>
                    </section>

                    <section className="cs-section">
                        <h4>Scene Schedule</h4>
                        <table className="cs-scene-table">
                            <thead><tr><th>Sc</th><th>I/E</th><th>Set</th><th>D/N</th></tr></thead>
                            <tbody>
                                {(callSheet.scenes || []).map((s) => (
                                    <tr key={s.id}>
                                        <td>{s.scene_number}</td><td>{s.int_ext}</td>
                                        <td>{s.setting || s.location_canonical}</td><td>{s.time_of_day}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </section>
                </div>

                <div className="cs-modal-footer">
                    <button
                        className="cs-download-btn"
                        onClick={() => downloadCallSheetPdf(callSheet.id, dayNumber)}
                    >
                        <Download size={14} /> Download PDF
                    </button>
                    {callSheet.status === 'draft' ? (
                        <button className="cs-publish-btn" disabled={saving} onClick={publish}>Publish</button>
                    ) : (
                        <button className="cs-unpublish-btn" disabled={saving} onClick={unpublish}>Move back to draft</button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default CallSheetEditor;
```

- [ ] **Step 2: Create the stylesheet**

Create `frontend/src/components/schedule/CallSheetEditor.css` — reuse the
existing modal visual language already established by
`.production-modal-backdrop` / `.production-modal` in
`frontend/src/components/productions/` (grep for that class's rules first
and mirror its box-shadow/border-radius/max-width values so this modal
doesn't look inconsistent):

```css
.cs-modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.cs-modal {
    background: var(--surface, #fff);
    border-radius: 8px;
    max-width: 640px;
    width: 92vw;
    max-height: 88vh;
    overflow-y: auto;
    padding: 1.5rem;
}

.cs-modal-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
}

.cs-modal-header h3 {
    flex: 1;
    margin: 0;
}

.cs-modal-close {
    background: none;
    border: none;
    cursor: pointer;
}

.cs-status-chip {
    font-size: 0.75rem;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    text-transform: uppercase;
}

.cs-status-draft { background: #fef3c7; color: #92400e; }
.cs-status-published { background: #d1fae5; color: #065f46; }

.cs-section {
    margin-bottom: 1.25rem;
}

.cs-field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    margin-bottom: 0.5rem;
}

.cs-roster-list {
    list-style: none;
    padding: 0;
    margin: 0.5rem 0 0;
}

.cs-roster-list li {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0;
}

.cs-scene-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
}

.cs-scene-table th, .cs-scene-table td {
    text-align: left;
    padding: 0.25rem 0.5rem;
    border-bottom: 1px solid #eee;
}

.cs-modal-footer {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    margin-top: 1rem;
}
```

- [ ] **Step 3: Wire a "Call Sheet" action into `DayColumn.jsx`**

Modify `frontend/src/components/schedule/DayColumn.jsx`. Add the icon
import (extend the existing `lucide-react` import line):

```javascript
import { Trash2, FileText, Users, MapPin, CalendarDays, ClipboardList } from 'lucide-react';
```

Add a prop for the click handler and render a button in `kanban-col-actions`:

```javascript
const DayColumn = ({ day, hasConflict, conflictScenes, acknowledgedScenes, onResolve, refreshDays, selectedSceneIds, onToggleSelect, onOpenCallSheet }) => {
```

In the JSX, inside `<div className="kanban-col-actions">`, before the delete
button:

```jsx
<button
    className="kanban-call-sheet-btn"
    onClick={() => onOpenCallSheet?.(day)}
    title="Call sheet for this day"
>
    <ClipboardList size={13} />
</button>
```

- [ ] **Step 4: Own the modal state in `ShootingSchedulePage.jsx`**

Modify `frontend/src/components/schedule/ShootingSchedulePage.jsx`. Add the
import:

```javascript
import CallSheetEditor from './CallSheetEditor';
```

Add state near the other `useState` calls:

```javascript
const [callSheetDay, setCallSheetDay] = useState(null);
```

Pass `onOpenCallSheet={setCallSheetDay}` down to `ScheduleKanban` (which
must forward it to each `DayColumn` — check `ScheduleKanban.jsx`'s existing
prop-drilling for `refreshDays`/`onResolve` at the `<DayColumn ...>` call
site around line 262 and add `onOpenCallSheet={onOpenCallSheet}` there the
same way, plus accept `onOpenCallSheet` as a prop on `ScheduleKanban`
itself).

Render the modal conditionally, near the end of the component's JSX
(alongside `ConflictPanel`):

```jsx
{callSheetDay && (
    <CallSheetEditor
        dayId={callSheetDay.id}
        dayNumber={callSheetDay.day_number}
        productionId={metadata?.production_id}
        scriptId={scriptId}
        onClose={() => setCallSheetDay(null)}
    />
)}
```

`scriptId` is already in scope in this component (`const { scriptId } = useParams();`
at the top of the file) — pass it straight through.

`metadata` is already loaded in this component via `getScriptMetadata`
(see the existing `useEffect` at the top of the file) — confirm it carries
`production_id` by checking `getScriptMetadata`'s response shape
(`grep -n "production_id" backend/routes/*.py` for the script-metadata
route, or inspect the network response in the browser once running); if it
doesn't, pass `null` for `productionId` and note this in a follow-up rather
than guessing a wrong field name — `CallSheetEditor` already guards with
`if (productionId)` before fetching crew/location options, so a missing
`production_id` degrades to an empty picker rather than crashing.

- [ ] **Step 5: Manual verification in the browser**

Run: `cd frontend && npm run dev` (and `cd backend && python app.py` in a
second terminal, with `FLASK_ENV=development` for the auth bypass).

In the browser: open a script's shooting schedule, click the new call-sheet
icon on a day column, confirm the modal opens, shows day-info fields,
allows adding a location/crew member, shows the live scene list, and that
"Download PDF" triggers a file download. This is the UI verification this
plan can't automate — per the project's own guidance, type-checking/build
passing is not the same as the feature working; actually click through it.

- [ ] **Step 6: Verify the build**

Run: `cd frontend && npm run build`
Expected: succeeds with no new errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/schedule/CallSheetEditor.jsx frontend/src/components/schedule/CallSheetEditor.css frontend/src/components/schedule/DayColumn.jsx frontend/src/components/schedule/ShootingSchedulePage.jsx
git commit -m "feat(call-sheets): add CallSheetEditor and wire it into the schedule UI"
```

---

### Task 14: `ProductionMembersTab.jsx` — `can_edit_call_sheets` checkbox

**Files:**
- Modify: `frontend/src/components/productions/ProductionMembersTab.jsx`

**Interfaces:**
- Consumes: `CAP_LABELS`, `PRESETS` (existing objects in this file, lines 13-39).
- Produces: an owner now has UI to grant/revoke `can_edit_call_sheets` on an individual member, matching the backend capability added in Task 2/3.

- [ ] **Step 1: Add the label and preset entries**

In `frontend/src/components/productions/ProductionMembersTab.jsx`, change:

```javascript
const CAP_LABELS = {
    can_view_sensitive: 'See rates & phone',
    can_edit_crew: 'Edit crew',
    can_manage_members: 'Manage members',
    can_edit_production: 'Edit production',
};

const PRESETS = {
    admin: {
        can_view_sensitive: true,
        can_edit_crew: true,
        can_manage_members: true,
        can_edit_production: true,
    },
    coordinator: {
        can_view_sensitive: false,
        can_edit_crew: true,
        can_manage_members: false,
        can_edit_production: false,
    },
    viewer: {
        can_view_sensitive: false,
        can_edit_crew: false,
        can_manage_members: false,
        can_edit_production: false,
    },
};
```

to:

```javascript
const CAP_LABELS = {
    can_view_sensitive: 'See rates & phone',
    can_edit_crew: 'Edit crew',
    can_manage_members: 'Manage members',
    can_edit_production: 'Edit production',
    can_edit_call_sheets: 'Edit call sheets',
};

const PRESETS = {
    admin: {
        can_view_sensitive: true,
        can_edit_crew: true,
        can_manage_members: true,
        can_edit_production: true,
        can_edit_call_sheets: true,
    },
    coordinator: {
        can_view_sensitive: false,
        can_edit_crew: true,
        can_manage_members: false,
        can_edit_production: false,
        can_edit_call_sheets: true,
    },
    viewer: {
        can_view_sensitive: false,
        can_edit_crew: false,
        can_manage_members: false,
        can_edit_production: false,
        can_edit_call_sheets: false,
    },
};
```

No other changes are needed — the member table (line 141, 164) and the
add-member modal (line 292) both iterate `Object.keys(CAP_LABELS)` /
`Object.values(CAP_LABELS)`, so the new checkbox column appears
automatically in both places.

- [ ] **Step 2: Verify the build**

Run: `cd frontend && npm run build`
Expected: succeeds with no new errors.

- [ ] **Step 3: Manual verification in the browser**

With the dev server running (from Task 13 Step 6), open a production's
Members tab and confirm a new "Edit call sheets" column/checkbox appears
in both the members table and the "Add member" modal's advanced
permissions section, and that toggling it persists (calls
`updateProductionMember` under the hood — check the network tab for a
`PATCH .../members/:id` request with `can_edit_call_sheets` in the body).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/productions/ProductionMembersTab.jsx
git commit -m "feat(call-sheets): add can_edit_call_sheets toggle to Members tab"
```

---

### Task 15: Full-suite verification

**Files:** none (verification only).

- [ ] **Step 1: Full backend suite**

Run: `cd backend && pytest tests/ -v`
Expected: all tests pass, including every pre-existing test file (confirms
the `CAPABILITIES` tuple growth and `ROLE_PRESETS` change didn't silently
break any test elsewhere in the suite that constructs a `production_access`
or `production_members` row by hand without every key).

- [ ] **Step 2: Full frontend build**

Run: `cd frontend && npm run build`
Expected: succeeds with no errors. (Do not run `npm run lint` —
project memory confirms it's broken repo-wide.)

- [ ] **Step 3: Re-confirm the manual browser walkthroughs from Tasks 13 and 14**

If either was skipped or the dev servers were stopped, redo them now,
back-to-back, in one session: create a call sheet, add a location/crew/cast
row, download the PDF, publish it, then check the Members tab checkbox.

- [ ] **Step 4: No commit for this task** — it's a verification checkpoint. If
Step 1 or 2 surfaces a failure, fix it as part of whichever earlier task
introduced it and re-commit there (or as a small fixup commit referencing
this plan), rather than creating a new "fix tests" task here.

---

## Deferred (explicitly out of scope — see spec)

Sides, multi-unit shoots, distribution (email/share-link), per-person
default call times, auto-suggesting roster from scenes, and report-style
version history are all named non-goals in the spec and have no task here.
Do not add them speculatively.
