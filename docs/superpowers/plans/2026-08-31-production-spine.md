# Production Spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a top-level `production` entity — a `/productions` area where an account owner creates a production, edits its Overview, and attaches/detaches script(s) — so downstream slices (crew, call sheets, DPR) have something to hang off.

**Architecture:** A new Flask blueprint `production_bp` (thin `routes/production_routes.py` over `services/production_service.py`) mirroring `series_routes.py` exactly: owner-scoped list, `series`-style read-through for team members, owner-gated writes. New tables `productions` + `units` + a nullable `scripts.production_id` FK (migration `050`). New React pages `/productions` and `/productions/:productionId` mirroring the Series pages. No new permission system — `production_members` is deferred to the crew slice.

**Tech Stack:** Flask 3 / Python 3.13, `supabase-py` (service-role key), pytest with an in-memory `MockSupabase`; React 18 + Vite (plain JSX), react-router, axios via the single `apiService.js` instance; Supabase Postgres (migrations applied manually).

**Spec:** `docs/superpowers/specs/2026-08-31-production-spine-design.md` (and its parent `docs/superpowers/specs/2026-08-31-production-data-model-design.md`)

## Global Constraints

- **Migrations are applied manually** to the Supabase project (`run_migration.py` is dead). The migration file is the deliverable; applying it is a documented manual step.
- **Backend gate:** `pytest tests/` from `backend/` must stay green (553 passing as of Cast tab v2).
- **Frontend gate:** `npm run build` from `frontend/` (repo-wide `npm run lint` is broken — do not use it).
- **No new axios instance** — all frontend API calls go through `frontend/src/services/apiService.js`'s `api`.
- **Ownership value:** `owner_id` / `user_id` everywhere is the `auth.users` id returned by `get_user_id()` (== `profiles.id`). Tests use `middleware.auth.DEV_USER_ID` with `DEV_MODE = True`.
- **`units` default name is the literal string `'Main Unit'`** — the DPR spec depends on it verbatim.
- **`production_members`, `contacts`, `locations`, `shooting_days.unit_id`, upload-flow picker, My Scripts grouping — all OUT of scope.** Do not add them.

---

## File Structure

**Backend**
- Create `backend/db/migrations/050_productions.sql` — `productions`, `units`, `scripts.production_id`, RLS, trigger, CHECK.
- Create `backend/services/production_service.py` — all production/unit/association data logic + local access helpers.
- Create `backend/routes/production_routes.py` — `production_bp`, HTTP concerns only.
- Modify `backend/app.py` — import + `register_blueprint(production_bp)` after `casting_bp`.
- Modify `backend/routes/supabase_routes.py` — add `production_id` + `production_title` to the `GET /api/scripts` response (new `_attach_production_info` helper, called next to `_attach_series_info`).
- Create `backend/tests/test_production_routes.py` — Flask-client + `MockSupabase` route tests.
- Create `backend/tests/test_get_scripts_production_info.py` — the `GET /api/scripts` enrichment regression.

**Frontend**
- Modify `frontend/src/services/apiService.js` — 7 production functions (new section).
- Create `frontend/src/pages/ProductionsListPage.jsx` — the list.
- Create `frontend/src/pages/ProductionDetailPage.jsx` — Overview + associated scripts.
- Create `frontend/src/components/productions/ProductionScriptPicker.jsx` — add-script modal.
- Create `frontend/src/pages/ProductionPages.css` — styles (reuse `SeriesPages.css` tokens).
- Modify `frontend/src/App.jsx` — two routes under the protected layout.
- Modify `frontend/src/components/layout/TopBar.jsx` — "Productions" nav link.

**Docs**
- Modify `docs/SLATEONE_FEATURES.md` — new "Productions" subsection.
- Modify `docs/BACKLOG.md` — mark spine step done.

---

## Task 1: Migration `050_productions.sql`

**Files:**
- Create: `backend/db/migrations/050_productions.sql`

**Interfaces:**
- Consumes: nothing.
- Produces: tables `productions(id, owner_id, title, status, shoot_start_date, shoot_end_date, notes, created_by, created_at, updated_at)`, `units(id, production_id, name, sort_order, created_at)`, column `scripts.production_id uuid null`.

- [ ] **Step 1: Write the migration file**

```sql
-- Migration 050: Productions (build-sequence step 1 -- "the spine")
-- A production is a physical-shoot container that holds one or more
-- scripts. Independent axis from series/seasons. See
-- docs/superpowers/specs/2026-08-31-production-spine-design.md
-- Apply manually against the Supabase project (run_migration.py is dead).

-- ============================================
-- 1. productions
-- ============================================
CREATE TABLE IF NOT EXISTS productions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- ON DELETE CASCADE is load-bearing: 013_delete_user_safely.sql deletes
    -- the profile and relies on this cascade to clean up productions+units.
    -- Do NOT soften this to SET NULL.
    owner_id          UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title             TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'development'
                        CHECK (status IN ('development','prep','shooting','wrapped','archived')),
    shoot_start_date  DATE,
    shoot_end_date    DATE,
    notes             TEXT,
    created_by        UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (shoot_end_date IS NULL OR shoot_start_date IS NULL
           OR shoot_end_date >= shoot_start_date)
);

CREATE INDEX IF NOT EXISTS idx_productions_owner ON productions(owner_id);

-- reuse the updated_at trigger fn from migration 030
CREATE TRIGGER trg_productions_updated
    BEFORE UPDATE ON productions
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

-- ============================================
-- 2. units -- one "Main Unit" auto-created per production by the service layer
-- ============================================
CREATE TABLE IF NOT EXISTS units (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_id UUID NOT NULL REFERENCES productions(id) ON DELETE CASCADE,
    name          TEXT NOT NULL DEFAULT 'Main Unit',
    sort_order    INT NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_units_production ON units(production_id);

-- ============================================
-- 3. scripts.production_id -- a script belongs to <=1 production
-- ============================================
ALTER TABLE scripts
    ADD COLUMN IF NOT EXISTS production_id UUID REFERENCES productions(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_scripts_production ON scripts(production_id);

-- ============================================
-- 4. RLS -- owner-only backstop (backend uses service-role key; real
--    access control is app-layer in production_service.py). Intentionally
--    narrower than the app: GET /api/productions/:id also serves team
--    members with a script role, same as series.
-- ============================================
ALTER TABLE productions ENABLE ROW LEVEL SECURITY;
ALTER TABLE units ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage their own productions"
    ON productions FOR ALL USING (owner_id = auth.uid());

CREATE POLICY "Users view units of their productions"
    ON units FOR SELECT USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = units.production_id AND p.owner_id = auth.uid())
    );
CREATE POLICY "Users manage units of their productions"
    ON units FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = units.production_id AND p.owner_id = auth.uid())
    );
```

- [ ] **Step 2: Sanity-check the SQL**

Read the file once more against these points:
- `update_shooting_updated_at()` exists (defined in `030_shooting_schedules.sql:131`) — no need to redefine.
- `profiles` table exists (referenced by `account_seats`, `email_logs`).
- No `DROP` statements; every `CREATE` is `IF NOT EXISTS` / idempotent except the trigger and policies (acceptable — migrations run once).

- [ ] **Step 3: Commit**

```bash
git add backend/db/migrations/050_productions.sql
git commit -m "feat(production): migration 050 — productions, units, scripts.production_id"
```

- [ ] **Step 4: Apply manually (documented step, done by the account owner)**

Run the file's contents in the Supabase SQL editor for project `twzfaizeyqwevmhjyicz`. Verify: `SELECT * FROM productions LIMIT 1;` and `SELECT production_id FROM scripts LIMIT 1;` both succeed (empty is fine).

---

## Task 2: `production_service.py` + create/list/get routes + blueprint

**Files:**
- Create: `backend/services/production_service.py`
- Create: `backend/routes/production_routes.py`
- Modify: `backend/app.py` (imports near line 23; `register_blueprint` near line 66)
- Test: `backend/tests/test_production_routes.py`

**Interfaces:**
- Consumes: `db.supabase_client.get_supabase_admin`, `middleware.auth.require_auth` / `get_user_id`, `middleware.authorization.get_script_role` / `SCRIPT_NOT_FOUND`.
- Produces:
  - `production_service.create_production(user_id: str, fields: dict) -> dict` — returns `{"production": {...}, "unit": {...}}`
  - `production_service.list_productions(user_id: str) -> list[dict]`
  - `production_service.get_production_for_viewer(production_id: str, user_id: str) -> dict | None | object` — returns `{"production": {...}, "scripts": [...]}`, or `None` (no access), or the `NOT_FOUND` sentinel (also exported as `production_service.NOT_FOUND`)
  - `production_service._user_owns_production(production_id: str, user_id: str) -> bool`
  - Blueprint `production_bp` with `POST /api/productions`, `GET /api/productions`, `GET /api/productions/<production_id>`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_production_routes.py
"""
Production CRUD + association route tests.

Mirrors the MockTable/MockSupabase pattern from test_series_routes.py:
a chainable supabase-py stand-in over a shared in-memory store, so route
code and get_script_role() see the same rows.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.production_service as ps
import routes.production_routes as pr
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
    base = {"productions": [], "units": [], "scripts": [], "script_members": []}
    base.update(overrides)
    return base


def _patch(monkeypatch, store):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    mock = MockSupabase(store)
    monkeypatch.setattr(ps, "get_supabase_admin", lambda: mock)
    # get_script_role() in middleware.authorization has its own get_supabase_admin
    monkeypatch.setattr("middleware.authorization.get_supabase_admin", lambda: mock)


def test_create_production_makes_production_and_main_unit(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)

    resp = _client().post("/api/productions", json={"title": "Farm Feature"})

    assert resp.status_code == 201
    body = resp.get_json()
    assert body["production"]["title"] == "Farm Feature"
    assert body["production"]["owner_id"] == DEV_USER_ID
    assert body["production"]["status"] == "development"
    assert body["unit"]["name"] == "Main Unit"
    assert body["unit"]["production_id"] == body["production"]["id"]
    assert len(store["units"]) == 1


def test_create_production_requires_title(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _client().post("/api/productions", json={})
    assert resp.status_code == 400


def test_list_productions_returns_only_callers_own(monkeypatch):
    store = _store(productions=[
        {"id": "p1", "owner_id": DEV_USER_ID, "title": "Mine"},
        {"id": "p2", "owner_id": "other", "title": "Not mine"},
    ])
    _patch(monkeypatch, store)
    resp = _client().get("/api/productions")
    assert resp.status_code == 200
    assert [p["title"] for p in resp.get_json()["productions"]] == ["Mine"]


def test_get_production_owner_sees_all_associated_scripts(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID, "title": "Mine"}],
        scripts=[
            {"id": "s1", "user_id": DEV_USER_ID, "production_id": "p1", "title": "Ep 1"},
            {"id": "s2", "user_id": DEV_USER_ID, "production_id": "p1", "title": "Ep 2"},
        ],
    )
    _patch(monkeypatch, store)
    resp = _client().get("/api/productions/p1")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["production"]["id"] == "p1"
    assert {s["id"] for s in body["scripts"]} == {"s1", "s2"}


def test_get_production_unrelated_user_forbidden(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": "other", "title": "Theirs"}],
        scripts=[{"id": "s1", "user_id": "other", "production_id": "p1", "title": "Ep 1"}],
    )
    _patch(monkeypatch, store)
    resp = _client().get("/api/productions/p1")
    assert resp.status_code == 403


def test_get_production_team_member_sees_only_their_script(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": "other", "title": "Theirs"}],
        scripts=[
            {"id": "s1", "user_id": "other", "production_id": "p1", "title": "Ep 1"},
            {"id": "s2", "user_id": "other", "production_id": "p1", "title": "Ep 2"},
        ],
        script_members=[{"script_id": "s1", "user_id": DEV_USER_ID, "role": "viewer"}],
    )
    _patch(monkeypatch, store)
    resp = _client().get("/api/productions/p1")
    assert resp.status_code == 200
    assert {s["id"] for s in resp.get_json()["scripts"]} == {"s1"}


def test_get_production_missing_is_404(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _client().get("/api/productions/nope")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_production_routes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.production_service'`

- [ ] **Step 3: Write `production_service.py`**

```python
# backend/services/production_service.py
"""
Production data logic (build-sequence step 1 -- "the spine").

A production is a physical-shoot container holding >=0 scripts. Access:
owner-only for list/write; GET-one also serves a team member who holds a
role on a script inside the production (mirrors series_routes.py). No
production_members table yet -- that ships with the crew slice.
"""
from db.supabase_client import get_supabase_admin
from middleware.authorization import get_script_role, SCRIPT_NOT_FOUND

NOT_FOUND = object()  # distinguishes 404 from 403 to the route layer

_EDITABLE_FIELDS = ("title", "status", "shoot_start_date", "shoot_end_date", "notes")


def _get_production(supabase, production_id):
    res = (supabase.table("productions").select("*")
           .eq("id", production_id).limit(1).execute())
    return res.data[0] if res.data else None


def _user_owns_production(production_id, user_id):
    prod = _get_production(get_supabase_admin(), production_id)
    return bool(prod and prod.get("owner_id") == user_id)


def create_production(user_id, fields):
    supabase = get_supabase_admin()
    row = {"owner_id": user_id, "created_by": user_id,
           "title": fields["title"]}
    for f in ("status", "shoot_start_date", "shoot_end_date", "notes"):
        if fields.get(f) is not None:
            row[f] = fields[f]
    prod = supabase.table("productions").insert(row).execute().data[0]
    unit = supabase.table("units").insert({
        "production_id": prod["id"], "name": "Main Unit", "sort_order": 0,
    }).execute().data[0]
    return {"production": prod, "unit": unit}


def list_productions(user_id):
    supabase = get_supabase_admin()
    res = (supabase.table("productions").select("*")
           .eq("owner_id", user_id).order("created_at", desc=True).execute())
    return res.data or []


def _accessible_scripts(supabase, production_id, user_id, is_owner):
    res = (supabase.table("scripts").select("*")
           .eq("production_id", production_id).execute())
    scripts = res.data or []
    if is_owner:
        return scripts
    visible = []
    for s in scripts:
        role = get_script_role(s["id"], user_id)
        if role not in (None, SCRIPT_NOT_FOUND):
            visible.append(s)
    return visible


def get_production_for_viewer(production_id, user_id):
    supabase = get_supabase_admin()
    prod = _get_production(supabase, production_id)
    if not prod:
        return NOT_FOUND
    is_owner = prod.get("owner_id") == user_id
    scripts = _accessible_scripts(supabase, production_id, user_id, is_owner)
    if not is_owner and not scripts:
        return None  # exists, but caller has no way in
    return {"production": prod, "scripts": scripts}


def update_production(production_id, fields):
    supabase = get_supabase_admin()
    patch = {f: fields[f] for f in _EDITABLE_FIELDS if f in fields}
    if not patch:
        return _get_production(supabase, production_id)
    res = (supabase.table("productions").update(patch)
           .eq("id", production_id).execute())
    return res.data[0] if res.data else None


def delete_production(production_id):
    get_supabase_admin().table("productions").delete().eq("id", production_id).execute()


def add_script(production_id, script_id, user_id):
    """Single conditional UPDATE -- no read-then-write race.

    Returns 'ok' | 'not_owned' | 'conflict'.
    """
    supabase = get_supabase_admin()
    owned = (supabase.table("scripts").select("id")
             .eq("id", script_id).eq("user_id", user_id).limit(1).execute())
    if not owned.data:
        return "not_owned"
    res = (supabase.table("scripts")
           .update({"production_id": production_id})
           .eq("id", script_id).eq("user_id", user_id)
           .is_("production_id", "null")
           .execute())
    return "ok" if res.data else "conflict"


def remove_script(production_id, script_id):
    (get_supabase_admin().table("scripts")
     .update({"production_id": None})
     .eq("id", script_id).eq("production_id", production_id)
     .execute())
```

- [ ] **Step 4: Write `production_routes.py`**

```python
# backend/routes/production_routes.py
"""
Production HTTP routes. Logic lives in services/production_service.py.
Owner-scoped list/write; GET-one also serves team members with a script
role inside the production (see production_service.get_production_for_viewer).
"""
from flask import Blueprint, request, jsonify

from middleware.auth import require_auth, get_user_id
from services import production_service as svc

production_bp = Blueprint("production", __name__)


@production_bp.route("/api/productions", methods=["POST"])
@require_auth
def create_production():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    data["title"] = title
    try:
        result = svc.create_production(get_user_id(), data)
        return jsonify(result), 201
    except Exception as e:
        print(f"Error creating production: {e}")
        return jsonify({"error": str(e)}), 500


@production_bp.route("/api/productions", methods=["GET"])
@require_auth
def list_productions():
    try:
        return jsonify({"productions": svc.list_productions(get_user_id())})
    except Exception as e:
        print(f"Error listing productions: {e}")
        return jsonify({"error": str(e)}), 500


@production_bp.route("/api/productions/<production_id>", methods=["GET"])
@require_auth
def get_production(production_id):
    try:
        result = svc.get_production_for_viewer(production_id, get_user_id())
        if result is svc.NOT_FOUND:
            return jsonify({"error": "Production not found"}), 404
        if result is None:
            return jsonify({"error": "Insufficient permissions"}), 403
        return jsonify(result)
    except Exception as e:
        print(f"Error getting production: {e}")
        return jsonify({"error": str(e)}), 500
```

- [ ] **Step 5: Register the blueprint in `app.py`**

Add with the other route imports (after `from routes.casting_routes import casting_bp`):
```python
from routes.production_routes import production_bp
```
Add after `app.register_blueprint(casting_bp)`:
```python
app.register_blueprint(production_bp)  # Production entity routes at /api/productions/*
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_production_routes.py -v`
Expected: PASS (7 tests)

- [ ] **Step 7: Run the full backend suite**

Run: `cd backend && python -m pytest tests/ -q`
Expected: all green (no regressions from the `app.py` / blueprint addition)

- [ ] **Step 8: Commit**

```bash
git add backend/services/production_service.py backend/routes/production_routes.py backend/app.py backend/tests/test_production_routes.py
git commit -m "feat(production): productions service + create/list/get routes"
```

---

## Task 3: update + delete routes

**Files:**
- Modify: `backend/routes/production_routes.py`
- Test: `backend/tests/test_production_routes.py`

**Interfaces:**
- Consumes: `production_service.update_production`, `delete_production`, `_user_owns_production` (from Task 2).
- Produces: `PATCH /api/productions/<production_id>`, `DELETE /api/productions/<production_id>`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_production_routes.py`:
```python
def test_patch_production_updates_only_given_fields(monkeypatch):
    store = _store(productions=[
        {"id": "p1", "owner_id": DEV_USER_ID, "title": "Old", "status": "development",
         "notes": "keep me"},
    ])
    _patch(monkeypatch, store)
    resp = _client().patch("/api/productions/p1", json={"title": "New", "status": "prep"})
    assert resp.status_code == 200
    row = store["productions"][0]
    assert row["title"] == "New"
    assert row["status"] == "prep"
    assert row["notes"] == "keep me"


def test_patch_production_non_owner_forbidden(monkeypatch):
    store = _store(productions=[{"id": "p1", "owner_id": "other", "title": "Theirs"}])
    _patch(monkeypatch, store)
    resp = _client().patch("/api/productions/p1", json={"title": "Hijack"})
    assert resp.status_code == 403
    assert store["productions"][0]["title"] == "Theirs"


def test_patch_production_missing_is_404(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _client().patch("/api/productions/nope", json={"title": "x"})
    assert resp.status_code == 404


def test_delete_production_nulls_associated_scripts(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID, "title": "Mine"}],
        scripts=[{"id": "s1", "user_id": DEV_USER_ID, "production_id": "p1", "title": "Ep 1"}],
    )
    _patch(monkeypatch, store)
    resp = _client().delete("/api/productions/p1")
    assert resp.status_code == 200
    assert store["productions"] == []
    # ON DELETE SET NULL is a DB behavior; the route mirrors it explicitly
    assert store["scripts"][0]["production_id"] is None


def test_delete_production_non_owner_forbidden(monkeypatch):
    store = _store(productions=[{"id": "p1", "owner_id": "other", "title": "Theirs"}])
    _patch(monkeypatch, store)
    resp = _client().delete("/api/productions/p1")
    assert resp.status_code == 403
    assert len(store["productions"]) == 1
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && python -m pytest tests/test_production_routes.py -k "patch or delete" -v`
Expected: FAIL — 405 Method Not Allowed / 404 (routes not defined)

- [ ] **Step 3: Add the routes**

Append to `backend/routes/production_routes.py`:
```python
@production_bp.route("/api/productions/<production_id>", methods=["PATCH"])
@require_auth
def update_production(production_id):
    user_id = get_user_id()
    try:
        if not svc._get_production(svc.get_supabase_admin(), production_id):
            return jsonify({"error": "Production not found"}), 404
        if not svc._user_owns_production(production_id, user_id):
            return jsonify({"error": "Insufficient permissions"}), 403
        data = request.get_json(silent=True) or {}
        if "title" in data:
            data["title"] = (data.get("title") or "").strip()
            if not data["title"]:
                return jsonify({"error": "title cannot be empty"}), 400
        return jsonify({"production": svc.update_production(production_id, data)})
    except Exception as e:
        print(f"Error updating production: {e}")
        return jsonify({"error": str(e)}), 500


@production_bp.route("/api/productions/<production_id>", methods=["DELETE"])
@require_auth
def delete_production(production_id):
    user_id = get_user_id()
    try:
        if not svc._get_production(svc.get_supabase_admin(), production_id):
            return jsonify({"error": "Production not found"}), 404
        if not svc._user_owns_production(production_id, user_id):
            return jsonify({"error": "Insufficient permissions"}), 403
        # Explicitly null associated scripts (DB does this via ON DELETE SET
        # NULL too; doing it here keeps behavior identical under the mock).
        svc.get_supabase_admin().table("scripts").update(
            {"production_id": None}).eq("production_id", production_id).execute()
        svc.delete_production(production_id)
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error deleting production: {e}")
        return jsonify({"error": str(e)}), 500
```

Add `get_supabase_admin` to the service import surface — at the top of `production_service.py` it is already imported from `db.supabase_client`; expose it by adding this line just below that import so `svc.get_supabase_admin` resolves:
```python
# (already imported above) get_supabase_admin is used by routes via svc.get_supabase_admin
```
(no code change needed — `from db.supabase_client import get_supabase_admin` at module top already makes `svc.get_supabase_admin` valid.)

- [ ] **Step 4: Run to verify they pass**

Run: `cd backend && python -m pytest tests/test_production_routes.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/routes/production_routes.py backend/tests/test_production_routes.py
git commit -m "feat(production): update + delete production routes"
```

---

## Task 4: script association (add/remove) + `GET /api/scripts` enrichment

**Files:**
- Modify: `backend/routes/production_routes.py`
- Modify: `backend/routes/supabase_routes.py` (add `_attach_production_info`, call it near the existing `_attach_series_info(scripts)` at line ~233)
- Test: `backend/tests/test_production_routes.py`, `backend/tests/test_get_scripts_production_info.py`

**Interfaces:**
- Consumes: `production_service.add_script` (returns `"ok" | "not_owned" | "conflict"`), `remove_script`, `_user_owns_production`.
- Produces:
  - `POST /api/productions/<production_id>/scripts` (body `{"script_id": "..."}`)
  - `DELETE /api/productions/<production_id>/scripts/<script_id>`
  - `GET /api/scripts` response items gain `production_id` (str|null) and `production_title` (str|null)

- [ ] **Step 1: Write the failing association tests**

Append to `backend/tests/test_production_routes.py`:
```python
def test_add_script_associates_owned_unassigned_script(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID, "title": "Mine"}],
        scripts=[{"id": "s1", "user_id": DEV_USER_ID, "production_id": None, "title": "Ep 1"}],
    )
    _patch(monkeypatch, store)
    resp = _client().post("/api/productions/p1/scripts", json={"script_id": "s1"})
    assert resp.status_code == 200
    assert store["scripts"][0]["production_id"] == "p1"


def test_add_script_already_in_a_production_conflicts(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID, "title": "Mine"},
                     {"id": "p2", "owner_id": DEV_USER_ID, "title": "Other"}],
        scripts=[{"id": "s1", "user_id": DEV_USER_ID, "production_id": "p2", "title": "Ep 1"}],
    )
    _patch(monkeypatch, store)
    resp = _client().post("/api/productions/p1/scripts", json={"script_id": "s1"})
    assert resp.status_code == 409
    assert store["scripts"][0]["production_id"] == "p2"


def test_add_script_not_owned_forbidden(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID, "title": "Mine"}],
        scripts=[{"id": "s1", "user_id": "other", "production_id": None, "title": "Ep 1"}],
    )
    _patch(monkeypatch, store)
    resp = _client().post("/api/productions/p1/scripts", json={"script_id": "s1"})
    assert resp.status_code == 403


def test_add_script_non_owner_of_production_forbidden(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": "other", "title": "Theirs"}],
        scripts=[{"id": "s1", "user_id": DEV_USER_ID, "production_id": None, "title": "Ep 1"}],
    )
    _patch(monkeypatch, store)
    resp = _client().post("/api/productions/p1/scripts", json={"script_id": "s1"})
    assert resp.status_code == 403


def test_remove_script_clears_pointer_and_second_call_is_noop(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID, "title": "Mine"}],
        scripts=[{"id": "s1", "user_id": DEV_USER_ID, "production_id": "p1", "title": "Ep 1"}],
    )
    _patch(monkeypatch, store)
    c = _client()
    r1 = c.delete("/api/productions/p1/scripts/s1")
    assert r1.status_code == 200
    assert store["scripts"][0]["production_id"] is None
    r2 = c.delete("/api/productions/p1/scripts/s1")
    assert r2.status_code == 200  # idempotent no-op
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && python -m pytest tests/test_production_routes.py -k "add_script or remove_script" -v`
Expected: FAIL — 405 / 404 (routes not defined)

- [ ] **Step 3: Add the association routes**

Append to `backend/routes/production_routes.py`:
```python
@production_bp.route("/api/productions/<production_id>/scripts", methods=["POST"])
@require_auth
def add_script_to_production(production_id):
    user_id = get_user_id()
    try:
        if not svc._get_production(svc.get_supabase_admin(), production_id):
            return jsonify({"error": "Production not found"}), 404
        if not svc._user_owns_production(production_id, user_id):
            return jsonify({"error": "Insufficient permissions"}), 403
        script_id = (request.get_json(silent=True) or {}).get("script_id")
        if not script_id:
            return jsonify({"error": "script_id is required"}), 400
        outcome = svc.add_script(production_id, script_id, user_id)
        if outcome == "not_owned":
            return jsonify({"error": "You do not own that script"}), 403
        if outcome == "conflict":
            return jsonify({"error": "Script already belongs to a production"}), 409
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error adding script to production: {e}")
        return jsonify({"error": str(e)}), 500


@production_bp.route("/api/productions/<production_id>/scripts/<script_id>", methods=["DELETE"])
@require_auth
def remove_script_from_production(production_id, script_id):
    user_id = get_user_id()
    try:
        if not svc._get_production(svc.get_supabase_admin(), production_id):
            return jsonify({"error": "Production not found"}), 404
        if not svc._user_owns_production(production_id, user_id):
            return jsonify({"error": "Insufficient permissions"}), 403
        svc.remove_script(production_id, script_id)
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error removing script from production: {e}")
        return jsonify({"error": str(e)}), 500
```

- [ ] **Step 4: Run to verify association tests pass**

Run: `cd backend && python -m pytest tests/test_production_routes.py -v`
Expected: PASS (17 tests)

- [ ] **Step 5: Write the failing `GET /api/scripts` enrichment test**

```python
# backend/tests/test_get_scripts_production_info.py
"""GET /api/scripts: production_id / production_title enrichment."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.supabase_routes as sr


class FakeQuery:
    def __init__(self, rows):
        self._rows = list(rows)
        self._single = False

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._rows = [r for r in self._rows if r.get(col) == val]
        return self

    def in_(self, col, values):
        values = set(values)
        self._rows = [r for r in self._rows if r.get(col) in values]
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        if self._single:
            return SimpleNamespace(data=self._rows[0] if self._rows else None)
        return SimpleNamespace(data=self._rows)


class FakeSupabase:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return FakeQuery(self.tables.get(name, []))


def test_attach_production_info_sets_id_and_title():
    supa = FakeSupabase({
        "productions": [{"id": "p1", "title": "Farm Feature"}],
    })
    sr.supabase = supa
    scripts = [
        {"id": "s1", "production_id": "p1"},
        {"id": "s2", "production_id": None},
    ]
    out = sr._attach_production_info(scripts)
    assert out[0]["production_id"] == "p1"
    assert out[0]["production_title"] == "Farm Feature"
    assert out[1]["production_id"] is None
    assert out[1]["production_title"] is None
```

- [ ] **Step 6: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_get_scripts_production_info.py -v`
Expected: FAIL — `AttributeError: module 'routes.supabase_routes' has no attribute '_attach_production_info'`

- [ ] **Step 7: Add `_attach_production_info` and call it**

In `backend/routes/supabase_routes.py`, directly after the `_attach_series_info` function (ends ~line 127):
```python
def _attach_production_info(scripts):
    """Enrich each script dict with production_id/production_title by joining
    scripts.production_id -> productions. Scripts with no production_id (the
    common case) get both keys set to None, matching the series-info pattern."""
    prod_ids = {s['production_id'] for s in scripts if s.get('production_id')}
    prod_map = {}
    if prod_ids and supabase:
        res = supabase.table('productions').select('id, title').in_('id', list(prod_ids)).execute()
        for prod in res.data or []:
            prod_map[prod['id']] = prod

    for script in scripts:
        prod = prod_map.get(script.get('production_id'))
        script['production_id'] = script.get('production_id') or None
        script['production_title'] = prod.get('title') if prod else None

    return scripts
```

Then, in `get_scripts()` where the code currently reads `scripts = _attach_series_info(scripts)` (~line 233), add the line right after:
```python
        scripts = _attach_series_info(scripts)
        scripts = _attach_production_info(scripts)
```

Note: the `get_scripts` builder appends dicts that do not yet carry `production_id`. Ensure each appended script dict includes `'production_id': script.get('production_id')` alongside the existing `'season_id'` / `'episode_number'` keys (there are two append sites — the owner branch and the member branch; add it to both, mirroring how `season_id` is already set in each).

- [ ] **Step 8: Run both test files + full suite**

Run: `cd backend && python -m pytest tests/test_get_scripts_production_info.py tests/test_get_scripts_series_info.py tests/test_production_routes.py -v`
Expected: PASS
Run: `cd backend && python -m pytest tests/ -q`
Expected: all green

- [ ] **Step 9: Commit**

```bash
git add backend/routes/production_routes.py backend/routes/supabase_routes.py backend/tests/test_production_routes.py backend/tests/test_get_scripts_production_info.py
git commit -m "feat(production): script association routes + GET /api/scripts production_id"
```

---

## Task 5: `apiService.js` production functions

**Files:**
- Modify: `frontend/src/services/apiService.js` (new section, place after the "Series / Season / Episode Management" block ~line 2290)

**Interfaces:**
- Consumes: the module-level `api` axios instance.
- Produces: `listProductions()`, `createProduction(payload)`, `getProduction(id)`, `updateProduction(id, payload)`, `deleteProduction(id)`, `addScriptToProduction(id, scriptId)`, `removeScriptFromProduction(id, scriptId)` — each returns `response.data` and rethrows on error, matching `listSeries` / `createSeries`.

- [ ] **Step 1: Add the functions**

```javascript
// ============================================
// Productions (build-sequence step 1 — the spine)
// ============================================

/**
 * List productions the current user owns.
 * @returns {Promise<{productions: object[]}>}
 */
export const listProductions = async () => {
    try {
        const response = await api.get('/api/productions');
        return response.data;
    } catch (error) {
        console.error('Error listing productions:', error);
        throw error;
    }
};

/**
 * Create a production (auto-creates its "Main Unit").
 * @param {{title: string, status?: string, shoot_start_date?: string, shoot_end_date?: string, notes?: string}} payload
 * @returns {Promise<{production: object, unit: object}>}
 */
export const createProduction = async (payload) => {
    try {
        const response = await api.post('/api/productions', payload);
        return response.data;
    } catch (error) {
        console.error('Error creating production:', error);
        throw error;
    }
};

/**
 * Get a production plus its associated scripts (filtered to the caller's access).
 * @param {string} id
 * @returns {Promise<{production: object, scripts: object[]}>}
 */
export const getProduction = async (id) => {
    try {
        const response = await api.get(`/api/productions/${id}`);
        return response.data;
    } catch (error) {
        console.error('Error getting production:', error);
        throw error;
    }
};

/**
 * Update a production's Overview fields (owner only).
 * @param {string} id
 * @param {object} payload  any of title/status/shoot_start_date/shoot_end_date/notes
 * @returns {Promise<{production: object}>}
 */
export const updateProduction = async (id, payload) => {
    try {
        const response = await api.patch(`/api/productions/${id}`, payload);
        return response.data;
    } catch (error) {
        console.error('Error updating production:', error);
        throw error;
    }
};

/**
 * Delete a production (associated scripts survive, unlinked).
 * @param {string} id
 */
export const deleteProduction = async (id) => {
    try {
        const response = await api.delete(`/api/productions/${id}`);
        return response.data;
    } catch (error) {
        console.error('Error deleting production:', error);
        throw error;
    }
};

/**
 * Attach a script the caller owns to a production. 409 if the script is
 * already in a production.
 * @param {string} id  production id
 * @param {string} scriptId
 */
export const addScriptToProduction = async (id, scriptId) => {
    try {
        const response = await api.post(`/api/productions/${id}/scripts`, { script_id: scriptId });
        return response.data;
    } catch (error) {
        console.error('Error adding script to production:', error);
        throw error;
    }
};

/**
 * Detach a script from a production.
 * @param {string} id  production id
 * @param {string} scriptId
 */
export const removeScriptFromProduction = async (id, scriptId) => {
    try {
        const response = await api.delete(`/api/productions/${id}/scripts/${scriptId}`);
        return response.data;
    } catch (error) {
        console.error('Error removing script from production:', error);
        throw error;
    }
};
```

- [ ] **Step 2: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds (no unused-import or syntax errors)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/apiService.js
git commit -m "feat(production): apiService production functions"
```

---

## Task 6: `/productions` list page + route + nav link

**Files:**
- Create: `frontend/src/pages/ProductionsListPage.jsx`
- Create: `frontend/src/pages/ProductionPages.css`
- Modify: `frontend/src/App.jsx` (import + route)
- Modify: `frontend/src/components/layout/TopBar.jsx` (nav link)

**Interfaces:**
- Consumes: `listProductions`, `createProduction` from `apiService.js`; `PageHeader`, `Spinner` from the existing UI kit (see `SeriesListPage.jsx` imports).
- Produces: route `/productions`; a "Productions" `NavLink` in `.topbar-nav`.

- [ ] **Step 1: Write the list page**

```jsx
// frontend/src/pages/ProductionsListPage.jsx
import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Clapperboard, ChevronRight, Plus } from 'lucide-react';
import { listProductions, createProduction } from '../services/apiService';
import PageHeader from '../components/layout/PageHeader';
import { Spinner } from '../components/ui';
import './ProductionPages.css';

const STATUS_LABELS = {
    development: 'Development', prep: 'Prep', shooting: 'Shooting',
    wrapped: 'Wrapped', archived: 'Archived',
};

export default function ProductionsListPage() {
    const navigate = useNavigate();
    const [productions, setProductions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [creating, setCreating] = useState(false);
    const [newTitle, setNewTitle] = useState('');
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        listProductions()
            .then((data) => setProductions(data.productions || []))
            .catch((err) => setError(err.message || 'Failed to load productions'))
            .finally(() => setLoading(false));
    }, []);

    const handleCreate = async (e) => {
        e.preventDefault();
        const title = newTitle.trim();
        if (!title || submitting) return;
        setSubmitting(true);
        try {
            const { production } = await createProduction({ title });
            navigate(`/productions/${production.id}`);
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Failed to create production');
            setSubmitting(false);
        }
    };

    if (loading) {
        return <div className="production-page-loading"><Spinner size={32} /></div>;
    }
    if (error && !productions.length) {
        return <p className="production-page-error">{error}</p>;
    }

    return (
        <div className="production-page">
            <PageHeader
                title="Productions"
                subtitle="A production groups the scripts you shoot together, with its own crew and schedule"
                action={
                    <button className="production-new-btn" onClick={() => setCreating((v) => !v)}>
                        <Plus size={16} /> New production
                    </button>
                }
            />

            {creating && (
                <form className="production-create-form" onSubmit={handleCreate}>
                    <input
                        autoFocus
                        type="text"
                        placeholder="Production title"
                        value={newTitle}
                        onChange={(e) => setNewTitle(e.target.value)}
                    />
                    <button type="submit" disabled={submitting || !newTitle.trim()}>
                        {submitting ? 'Creating…' : 'Create'}
                    </button>
                </form>
            )}

            {error && productions.length > 0 && <p className="production-page-error">{error}</p>}

            {productions.length === 0 ? (
                <div className="production-empty-state">
                    <div className="production-empty-icon-wrapper">
                        <Clapperboard size={28} className="production-empty-icon" />
                    </div>
                    <h2>No productions yet</h2>
                    <p>Create a production, then attach the scripts you'll shoot under it.</p>
                </div>
            ) : (
                <ul className="production-list">
                    {productions.map((p) => (
                        <li key={p.id}>
                            <Link to={`/productions/${p.id}`} className="production-row">
                                <span className="production-row-title">{p.title}</span>
                                <span className={`production-row-status status-${p.status}`}>
                                    {STATUS_LABELS[p.status] || p.status}
                                </span>
                                <ChevronRight size={18} className="production-row-chevron" />
                            </Link>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
```

- [ ] **Step 2: Write `ProductionPages.css`**

Reuse the dark-navy/amber token values from `frontend/src/pages/SeriesPages.css`. Copy that file's `.series-page*` rules as `.production-page*` equivalents, plus:
```css
.production-page { max-width: 900px; margin: 0 auto; padding: 24px; }
.production-page-loading { display: flex; justify-content: center; padding: 80px 0; }
.production-page-error { color: #ef4444; padding: 12px 0; }

.production-new-btn,
.production-create-form button {
    display: inline-flex; align-items: center; gap: 6px;
    background: #f5b301; color: #1a2332; border: none; border-radius: 6px;
    padding: 8px 14px; font-weight: 600; cursor: pointer;
}
.production-create-form { display: flex; gap: 8px; margin: 12px 0 20px; }
.production-create-form input {
    flex: 1; padding: 8px 12px; border-radius: 6px;
    border: 1px solid #33415a; background: #131c2e; color: #e6ecf5;
}

.production-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
.production-row {
    display: flex; align-items: center; gap: 12px;
    padding: 14px 16px; border-radius: 8px;
    background: #131c2e; border: 1px solid #26324a;
    text-decoration: none; color: #e6ecf5;
}
.production-row:hover { border-color: #f5b301; }
.production-row-title { flex: 1; font-weight: 600; }
.production-row-status {
    font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em;
    padding: 2px 8px; border-radius: 999px; background: #26324a; color: #9fb0c9;
}
.production-row-status.status-shooting { background: #1e3a2e; color: #6ee7a8; }
.production-row-status.status-wrapped { background: #2e2a1e; color: #f5b301; }
.production-row-chevron { color: #6b7a94; }

.production-empty-state { text-align: center; padding: 64px 24px; color: #9fb0c9; }
.production-empty-icon-wrapper {
    display: inline-flex; padding: 16px; border-radius: 999px;
    background: #131c2e; border: 1px solid #26324a; margin-bottom: 12px;
}
.production-empty-icon { color: #f5b301; }
```
If `PageHeader` does not accept an `action` prop, check `frontend/src/components/layout/PageHeader.jsx` and either add a right-slot prop (mirror how other pages pass actions) or render the "New production" button directly under the header instead.

- [ ] **Step 3: Add the routes in `App.jsx`**

Import near the other page imports:
```jsx
import ProductionsListPage from './pages/ProductionsListPage';
import ProductionDetailPage from './pages/ProductionDetailPage';
```
Add inside the protected layout `<Route>` block, next to the `series` routes:
```jsx
                    <Route path="productions" element={<ProductionsListPage />} />
                    <Route path="productions/:productionId" element={<ProductionDetailPage />} />
```
(`ProductionDetailPage` is created in Task 7 — add a temporary stub file now so the build passes:
```jsx
// frontend/src/pages/ProductionDetailPage.jsx  — replaced in full by Task 7
export default function ProductionDetailPage() { return null; }
```)

- [ ] **Step 4: Add the nav link in `TopBar.jsx`**

After the `/series` `NavLink` block (~line 82):
```jsx
          <NavLink
            to="/productions"
            className={({ isActive }) => `topbar-nav-item ${isActive ? 'active' : ''}`}
          >
            <span>Productions</span>
          </NavLink>
```
Then check `.topbar-nav` in the TopBar CSS at a ~375px viewport width — if three items overflow the bar, reduce `.topbar-nav-item` horizontal padding or `gap`; do not restructure the bar.

- [ ] **Step 5: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 6: Manual check**

`npm run dev`, log in, click "Productions" in the top nav → empty state renders → "New production", enter a title, Create → navigates to `/productions/:id` (blank for now).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/ProductionsListPage.jsx frontend/src/pages/ProductionPages.css frontend/src/pages/ProductionDetailPage.jsx frontend/src/App.jsx frontend/src/components/layout/TopBar.jsx
git commit -m "feat(production): /productions list page, route, nav link"
```

---

## Task 7: `/productions/:productionId` detail page + script picker

**Files:**
- Replace: `frontend/src/pages/ProductionDetailPage.jsx` (full file, overwriting the Task 6 stub)
- Create: `frontend/src/components/productions/ProductionScriptPicker.jsx`
- Modify: `frontend/src/pages/ProductionPages.css` (append detail-page styles)

**Interfaces:**
- Consumes: `getProduction`, `updateProduction`, `deleteProduction`, `addScriptToProduction`, `removeScriptFromProduction`, and `getScripts` (existing — returns `{scripts: [...]}` each with `production_id`) from `apiService.js`; `useParams` / `useNavigate`; `Spinner`, `PageHeader`.
- Produces: the `/productions/:productionId` screen. No exports consumed by other tasks.

- [ ] **Step 1: Write the script picker**

```jsx
// frontend/src/components/productions/ProductionScriptPicker.jsx
import { useState, useEffect } from 'react';
import { getScripts } from '../../services/apiService';
import { Spinner } from '../ui';

export default function ProductionScriptPicker({ onPick, onClose }) {
    const [scripts, setScripts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [busyId, setBusyId] = useState(null);

    useEffect(() => {
        getScripts()
            .then((data) => setScripts((data.scripts || []).filter(
                (s) => !s.production_id && (s.is_owner ?? true))))
            .catch((err) => setError(err.message || 'Failed to load scripts'))
            .finally(() => setLoading(false));
    }, []);

    const pick = async (scriptId) => {
        setBusyId(scriptId);
        try {
            await onPick(scriptId);
        } catch (err) {
            setError(err.response?.data?.error || 'Could not add that script');
            setBusyId(null);
        }
    };

    return (
        <div className="production-modal-backdrop" onClick={onClose}>
            <div className="production-modal" onClick={(e) => e.stopPropagation()}>
                <h3>Add a script</h3>
                {loading ? (
                    <Spinner size={24} />
                ) : error ? (
                    <p className="production-page-error">{error}</p>
                ) : scripts.length === 0 ? (
                    <p>Every script you own is already in a production.</p>
                ) : (
                    <ul className="production-picker-list">
                        {scripts.map((s) => (
                            <li key={s.id}>
                                <button disabled={busyId === s.id} onClick={() => pick(s.id)}>
                                    {s.title || 'Untitled script'}
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
                <button className="production-modal-close" onClick={onClose}>Close</button>
            </div>
        </div>
    );
}
```

- [ ] **Step 2: Write the detail page**

```jsx
// frontend/src/pages/ProductionDetailPage.jsx
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Trash2, Plus, X } from 'lucide-react';
import {
    getProduction, updateProduction, deleteProduction,
    addScriptToProduction, removeScriptFromProduction,
} from '../services/apiService';
import { Spinner } from '../components/ui';
import ProductionScriptPicker from '../components/productions/ProductionScriptPicker';
import './ProductionPages.css';

const STATUSES = ['development', 'prep', 'shooting', 'wrapped', 'archived'];

export default function ProductionDetailPage() {
    const { productionId } = useParams();
    const navigate = useNavigate();

    const [production, setProduction] = useState(null);
    const [scripts, setScripts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [form, setForm] = useState(null);
    const [saving, setSaving] = useState(false);
    const [picking, setPicking] = useState(false);
    const [isOwner, setIsOwner] = useState(false);

    const load = useCallback(() => {
        getProduction(productionId)
            .then((data) => {
                setProduction(data.production);
                setScripts(data.scripts || []);
                setForm({
                    title: data.production.title || '',
                    status: data.production.status || 'development',
                    shoot_start_date: data.production.shoot_start_date || '',
                    shoot_end_date: data.production.shoot_end_date || '',
                    notes: data.production.notes || '',
                });
                // Heuristic: PATCH is owner-only; probe cheaply by allowing edit
                // and letting the server 403. Simpler: treat as owner if the
                // list endpoint returned this production. Here we optimistically
                // enable and surface a 403 on save.
                setIsOwner(true);
            })
            .catch((err) => {
                if (err.response?.status === 403) setError('You can view this production but not edit it.');
                else setError(err.response?.data?.error || err.message || 'Failed to load production');
            })
            .finally(() => setLoading(false));
    }, [productionId]);

    useEffect(load, [load]);

    const save = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            const payload = {
                ...form,
                shoot_start_date: form.shoot_start_date || null,
                shoot_end_date: form.shoot_end_date || null,
            };
            const { production: updated } = await updateProduction(productionId, payload);
            setProduction(updated);
            setError(null);
        } catch (err) {
            if (err.response?.status === 403) { setIsOwner(false); setError('Only the production owner can edit this.'); }
            else setError(err.response?.data?.error || 'Save failed');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!window.confirm('Delete this production? Its scripts are kept and just unlinked.')) return;
        try {
            await deleteProduction(productionId);
            navigate('/productions');
        } catch (err) {
            setError(err.response?.data?.error || 'Delete failed');
        }
    };

    const handlePick = async (scriptId) => {
        await addScriptToProduction(productionId, scriptId);
        setPicking(false);
        load();
    };

    const handleRemove = async (scriptId) => {
        await removeScriptFromProduction(productionId, scriptId);
        setScripts((prev) => prev.filter((s) => s.id !== scriptId));
    };

    if (loading) return <div className="production-page-loading"><Spinner size={32} /></div>;
    if (!production) return <p className="production-page-error">{error || 'Not found'}</p>;

    return (
        <div className="production-page">
            <Link to="/productions" className="production-back"><ArrowLeft size={16} /> Productions</Link>

            {error && <p className="production-page-error">{error}</p>}

            <form className="production-overview" onSubmit={save}>
                <label>
                    Title
                    <input value={form.title} disabled={!isOwner}
                        onChange={(e) => setForm({ ...form, title: e.target.value })} />
                </label>
                <label>
                    Status
                    <select value={form.status} disabled={!isOwner}
                        onChange={(e) => setForm({ ...form, status: e.target.value })}>
                        {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                </label>
                <div className="production-date-row">
                    <label>
                        Shoot start
                        <input type="date" value={form.shoot_start_date} disabled={!isOwner}
                            onChange={(e) => setForm({ ...form, shoot_start_date: e.target.value })} />
                    </label>
                    <label>
                        Shoot end
                        <input type="date" value={form.shoot_end_date} disabled={!isOwner}
                            onChange={(e) => setForm({ ...form, shoot_end_date: e.target.value })} />
                    </label>
                </div>
                <label>
                    Notes
                    <textarea value={form.notes} disabled={!isOwner} rows={3}
                        onChange={(e) => setForm({ ...form, notes: e.target.value })} />
                </label>
                {isOwner && (
                    <div className="production-overview-actions">
                        <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
                        <button type="button" className="production-delete-btn" onClick={handleDelete}>
                            <Trash2 size={14} /> Delete production
                        </button>
                    </div>
                )}
            </form>

            <section className="production-scripts">
                <div className="production-scripts-head">
                    <h3>Scripts</h3>
                    {isOwner && (
                        <button onClick={() => setPicking(true)}><Plus size={14} /> Add script</button>
                    )}
                </div>
                {scripts.length === 0 ? (
                    <p className="production-scripts-empty">No scripts attached yet.</p>
                ) : (
                    <ul className="production-scripts-list">
                        {scripts.map((s) => (
                            <li key={s.id}>
                                <Link to={`/scenes/${s.id}`}>{s.title || 'Untitled script'}</Link>
                                {isOwner && (
                                    <button className="production-script-remove"
                                        onClick={() => handleRemove(s.id)} aria-label="Remove script">
                                        <X size={14} />
                                    </button>
                                )}
                            </li>
                        ))}
                    </ul>
                )}
            </section>

            {picking && (
                <ProductionScriptPicker onPick={handlePick} onClose={() => setPicking(false)} />
            )}
        </div>
    );
}
```

- [ ] **Step 3: Append detail + modal styles to `ProductionPages.css`**

```css
.production-back {
    display: inline-flex; align-items: center; gap: 6px;
    color: #9fb0c9; text-decoration: none; font-size: 14px; margin-bottom: 16px;
}
.production-overview { display: flex; flex-direction: column; gap: 14px; margin-bottom: 32px; }
.production-overview label { display: flex; flex-direction: column; gap: 4px; font-size: 13px; color: #9fb0c9; }
.production-overview input,
.production-overview select,
.production-overview textarea {
    padding: 8px 12px; border-radius: 6px; border: 1px solid #33415a;
    background: #131c2e; color: #e6ecf5; font: inherit;
}
.production-overview input:disabled,
.production-overview select:disabled,
.production-overview textarea:disabled { opacity: 0.6; }
.production-date-row { display: flex; gap: 12px; }
.production-date-row label { flex: 1; }
.production-overview-actions { display: flex; justify-content: space-between; align-items: center; }
.production-overview-actions > button[type="submit"] {
    background: #f5b301; color: #1a2332; border: none; border-radius: 6px;
    padding: 8px 18px; font-weight: 600; cursor: pointer;
}
.production-delete-btn {
    display: inline-flex; align-items: center; gap: 6px;
    background: none; border: none; color: #ef4444; cursor: pointer; font-size: 13px;
}

.production-scripts-head { display: flex; align-items: center; justify-content: space-between; }
.production-scripts-head button {
    display: inline-flex; align-items: center; gap: 4px;
    background: #26324a; color: #e6ecf5; border: none; border-radius: 6px;
    padding: 6px 12px; cursor: pointer;
}
.production-scripts-list { list-style: none; padding: 0; margin: 12px 0 0; display: flex; flex-direction: column; gap: 6px; }
.production-scripts-list li {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 14px; background: #131c2e; border: 1px solid #26324a; border-radius: 6px;
}
.production-scripts-list a { color: #e6ecf5; text-decoration: none; }
.production-scripts-list a:hover { color: #f5b301; }
.production-script-remove { background: none; border: none; color: #6b7a94; cursor: pointer; }
.production-scripts-empty { color: #6b7a94; margin-top: 12px; }

.production-modal-backdrop {
    position: fixed; inset: 0; background: rgba(6, 10, 20, 0.7);
    display: flex; align-items: center; justify-content: center; z-index: 50;
}
.production-modal {
    background: #1a2332; border: 1px solid #33415a; border-radius: 10px;
    padding: 20px; width: min(420px, 92vw); max-height: 80vh; overflow: auto;
}
.production-picker-list { list-style: none; padding: 0; margin: 12px 0; display: flex; flex-direction: column; gap: 6px; }
.production-picker-list button {
    width: 100%; text-align: left; padding: 10px 12px; border-radius: 6px;
    background: #131c2e; border: 1px solid #26324a; color: #e6ecf5; cursor: pointer;
}
.production-picker-list button:hover:not(:disabled) { border-color: #f5b301; }
.production-modal-close {
    margin-top: 8px; background: #26324a; color: #e6ecf5; border: none;
    border-radius: 6px; padding: 8px 16px; cursor: pointer;
}
```

- [ ] **Step 4: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Manual check**

`npm run dev`: open a production → edit title/status/dates/notes, Save → reload, values persist. "Add script" → pick a script → it appears in the list and disappears from the picker on reopen. Remove it → gone. Attach a script, then try to attach the same script to a second production → the picker no longer offers it (it has a `production_id`). Delete the production → back to `/productions`, and the script still shows in My Scripts.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/ProductionDetailPage.jsx frontend/src/components/productions/ProductionScriptPicker.jsx frontend/src/pages/ProductionPages.css
git commit -m "feat(production): production detail page + script picker"
```

---

## Task 8: docs + backlog

**Files:**
- Modify: `docs/SLATEONE_FEATURES.md`
- Modify: `docs/BACKLOG.md`

**Interfaces:** none.

- [ ] **Step 1: Add a "Productions" subsection to `SLATEONE_FEATURES.md`**

Under "## 🚀 Currently Available Features", after the "### 7. Cast & Casting" block, add a new numbered section (renumber "Exporting & Reporting" from 8 to 9):
```markdown
### 8. Productions
- **Production Entity:** Group the scripts you shoot together (a TV block, a feature and its reshoot) under a single Production with its own status and shoot dates — an axis independent of Series/Season.
- **Script Association:** Attach and detach scripts from a production; each script belongs to at most one production, kept in sync with My Scripts.
- **Units:** Every production starts with a "Main Unit"; multi-unit support underpins later Daily Production Reporting.
```

- [ ] **Step 2: Mark the spine done in `BACKLOG.md`**

In the "Production data model — DIRECTION DECIDED" entry, under "**Next:**", change the step 1 line to note it shipped, referencing `docs/superpowers/plans/2026-08-31-production-spine.md`. In the priority snapshot item 1, update "Next:" to point at build-sequence step 2 (crew).

- [ ] **Step 3: Commit**

```bash
git add docs/SLATEONE_FEATURES.md docs/BACKLOG.md
git commit -m "docs(production): document Productions; mark spine shipped in backlog"
```

---

## Self-Review

**1. Spec coverage:**
- `productions` / `units` / `scripts.production_id` schema → Task 1 ✓
- RLS owner-only + narrower-than-app note → Task 1 ✓
- `delete_user_safely` cascade comment → Task 1 (migration comment) ✓
- Blueprint + service pattern, create/list/get with `series`-style visibility → Task 2 ✓
- `'Main Unit'` auto-create → Task 2 (test asserts it) ✓
- update + delete, owner-gated, scripts survive → Task 3 ✓
- Association via single conditional UPDATE (no race), ≤1-production 409, not-owned 403, idempotent remove → Task 4 ✓
- `GET /api/scripts` gains `production_id` (+ `production_title`) via `_attach_production_info` → Task 4 ✓
- `apiService.js` 7 functions → Task 5 ✓
- `/productions` list + route + nav link + nav-crowding check → Task 6 ✓
- `/productions/:id` Overview (editable, owner-gated) + associated scripts add/remove + picker excludes assigned scripts → Task 7 ✓
- Frontend gate `npm run build`; backend gate `pytest tests/` → every task ✓
- Docs debt (SLATEONE_FEATURES) → Task 8 ✓
- Out-of-scope items (`production_members`, contacts/locations, `shooting_days.unit_id`, upload picker, My Scripts grouping) → none introduced ✓

**2. Placeholder scan:** No "TBD"/"handle edge cases"/"similar to Task N". The one stub (`ProductionDetailPage` in Task 6 Step 3) is explicitly a throwaway replaced in full by Task 7, with its full contents given there.

**3. Type consistency:**
- `add_script` returns `"ok" | "not_owned" | "conflict"` — defined in Task 2's service code, consumed in Task 4's route with exactly those three string checks. ✓
- `get_production_for_viewer` returns `{"production", "scripts"} | None | NOT_FOUND` — Task 2 defines, Task 2's route + Task 7's page consume `data.production` / `data.scripts`. ✓
- `NOT_FOUND` exported as `svc.NOT_FOUND` — Task 2 defines at module level, route checks `result is svc.NOT_FOUND`. ✓
- `_attach_production_info(scripts) -> scripts` (mutates in place, returns same list) — matches `_attach_series_info` signature. Task 4 defines + calls. ✓
- apiService: `getProduction` returns `{production, scripts}`; `createProduction` returns `{production, unit}` — Task 5 defines, Tasks 6/7 consume the right keys. ✓
- `getScripts()` returning items with `.production_id` and `.is_owner` — `production_id` added in Task 4, `is_owner` already exists in the current `get_scripts` response. Picker filter in Task 7 uses both. ✓
