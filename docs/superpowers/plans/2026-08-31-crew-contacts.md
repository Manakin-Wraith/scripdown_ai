# Crew + Contacts (Step 2a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give a production a crew roster and give the account a reusable `contacts` address book, with CSV crew import — owner-only.

**Architecture:** New `contacts_bp` blueprint (directory CRUD, owner-scoped) + crew routes added to the existing `production_bp`, backed by `production_crew_service` and a pure `crew_import` parser. Frontend adds a `/contacts` page and a Crew tab on `ProductionDetailPage` (which is refactored into an Overview/Crew tab strip). The `production_members` permission layer is explicitly out of scope — deferred to slice 2b.

**Tech Stack:** Flask (Python 3.13), supabase-py with the service-role key, pytest with the in-repo `MockSupabase` fake; React 18 + Vite (plain JSX), single axios instance in `apiService.js`.

**Spec:** `docs/superpowers/specs/2026-08-31-crew-contacts-design.md`

## Global Constraints

- Supabase is the only database. Migrations are `.sql` files in `backend/db/migrations/`, **applied manually** to the Supabase project — `run_migration.py` is dead. The plan produces the SQL; a human applies it.
- Backend access uses the service-role key; **all authorization is enforced in Python**, not RLS. RLS policies are a direct-client backstop only.
- Backend tests use the `MockTable` / `MockSupabase` chainable fake from `backend/tests/test_production_routes.py` (copy it, do not import a shared one — that is the established pattern). Patch `middleware.auth.DEV_MODE = True` and both `services.<mod>.get_supabase_admin` and `middleware.authorization.get_supabase_admin` to the same mock so `get_script_role` sees the same store.
- Backend gate: `pytest tests/` green from `backend/`.
- Frontend gate: `npm run build` green from `frontend/` (`npm run lint` is broken repo-wide — do not rely on it).
- All frontend API calls go through the existing axios instance in `frontend/src/services/apiService.js`. No new axios instance.
- `department_code` is validated in Python against `get_departments_list()`, never a hard FK.
- Sensitive fields (`contacts.phone`, `contacts.standard_rate`, `production_crew.job_rate`) are stored and returned in full in 2a — the owner is the only viewer. No gating logic.
- End every commit message with the repo's trailer:
  ```
  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_011dzCtuqgTq5RnZPuULSQcP
  ```

---

## Task 1: Migration 051 — `contacts` + `production_crew` tables

**Files:**
- Create: `backend/db/migrations/051_contacts_crew.sql`

**Interfaces:**
- Consumes: existing `update_shooting_updated_at()` trigger fn (migration 030), `productions` (migration 050), `profiles`, `auth.users`.
- Produces: tables `contacts`, `production_crew` with the columns every later task reads/writes.

- [ ] **Step 1: Write the migration SQL**

Create `backend/db/migrations/051_contacts_crew.sql`:

```sql
-- Migration 051: Contacts directory + production crew (build-sequence step 2a)
-- See docs/superpowers/specs/2026-08-31-crew-contacts-design.md
-- Apply manually against the Supabase project (run_migration.py is dead).
--
-- Delete-user ordering note (013_delete_user_safely.sql deletes scripts then
-- profiles): profiles delete cascades to productions (050) which cascades to
-- production_crew via production_crew.production_id BEFORE the profiles ->
-- contacts cascade fires, so the ON DELETE RESTRICT on
-- production_crew.contact_id is never violated during user deletion. This
-- ordering is load-bearing; do not "soften" contact_id to CASCADE without
-- re-checking that script.

-- ============================================
-- 1. contacts -- account-level reusable directory
-- ============================================
CREATE TABLE IF NOT EXISTS contacts (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id       UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    kind           TEXT NOT NULL DEFAULT 'person'
                     CHECK (kind IN ('person','company')),
    name           TEXT NOT NULL,
    company_name   TEXT,
    role_tags      TEXT[] NOT NULL DEFAULT '{}'::TEXT[],
    phone          TEXT,
    email          TEXT,
    agent_contact  TEXT,
    standard_rate  NUMERIC,
    rate_unit      TEXT CHECK (rate_unit IS NULL OR rate_unit IN ('day','week','flat')),
    notes          TEXT,
    created_by     UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_contacts_owner ON contacts(owner_id);
CREATE INDEX IF NOT EXISTS idx_contacts_owner_email
    ON contacts(owner_id, lower(email)) WHERE email IS NOT NULL;

CREATE TRIGGER trg_contacts_updated
    BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

-- ============================================
-- 2. production_crew -- assignment (production <-> contact)
-- ============================================
CREATE TABLE IF NOT EXISTS production_crew (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_id   UUID NOT NULL REFERENCES productions(id) ON DELETE CASCADE,
    contact_id      UUID NOT NULL REFERENCES contacts(id) ON DELETE RESTRICT,
    role            TEXT,
    department_code TEXT,   -- soft ref to the departments list; validated in Python
    job_rate        NUMERIC,
    job_rate_unit   TEXT CHECK (job_rate_unit IS NULL OR job_rate_unit IN ('day','week','flat')),
    start_date      DATE,
    end_date        DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_production_crew_production ON production_crew(production_id);
CREATE INDEX IF NOT EXISTS idx_production_crew_contact ON production_crew(contact_id);

CREATE TRIGGER trg_production_crew_updated
    BEFORE UPDATE ON production_crew
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

-- ============================================
-- 3. RLS -- owner-only, direct-client backstop only
-- ============================================
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE production_crew ENABLE ROW LEVEL SECURITY;

CREATE POLICY "owner manages contacts"
    ON contacts FOR ALL USING (owner_id = auth.uid());

CREATE POLICY "owner manages production crew"
    ON production_crew FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = production_crew.production_id
                  AND p.owner_id = auth.uid())
    );
```

- [ ] **Step 2: Sanity-check the SQL locally**

Run: `python -c "import pathlib; s=pathlib.Path('backend/db/migrations/051_contacts_crew.sql').read_text(); assert s.count('(') == s.count(')'), 'paren mismatch'; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/db/migrations/051_contacts_crew.sql
git commit -m "feat(crew): migration 051 — contacts + production_crew tables"
```

- [ ] **Step 4: Flag for manual apply**

Note in the task hand-off (do NOT block on it): "Migration 051 must be applied manually to the Supabase project before the crew/contacts endpoints work against real data. Tests use the mock and do not need it."

---

## Task 2: Extract `get_departments_list()` into a shared module

**Files:**
- Create: `backend/services/department_service.py`
- Modify: `backend/routes/invite_routes.py` (remove the local `get_departments_list` / `get_department_name` / `_departments_cache`, import from the new module)
- Test: `backend/tests/test_department_service.py`

**Interfaces:**
- Produces:
  - `get_departments_list() -> list[dict]` — rows `{code, name, color}` ordered by `sort_order`, cached in a module global after first call. Returns `[]` if the table read fails.
  - `get_department_name(code: str) -> str` — the `name` for a code, or the code itself if unknown.
  - `valid_department_codes() -> set[str]` — `{row['code'] for row in get_departments_list()}`.
  - `_reset_departments_cache()` — test helper that clears the module global.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_department_service.py`:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.department_service as ds


class _Resp:
    def __init__(self, data): self.data = data


class _FakeTable:
    def __init__(self, rows): self._rows = rows
    def select(self, *_a, **_k): return self
    def order(self, *_a, **_k): return self
    def execute(self): return _Resp(self._rows)


class _FakeSupabase:
    def __init__(self, rows): self._rows = rows
    def table(self, _n): return _FakeTable(self._rows)


def test_list_and_helpers(monkeypatch):
    ds._reset_departments_cache()
    rows = [{"code": "camera", "name": "Camera", "color": "#111"},
            {"code": "grip", "name": "Grip", "color": "#222"}]
    monkeypatch.setattr(ds, "get_supabase_admin", lambda: _FakeSupabase(rows))

    assert [d["code"] for d in ds.get_departments_list()] == ["camera", "grip"]
    assert ds.get_department_name("grip") == "Grip"
    assert ds.get_department_name("nope") == "nope"
    assert ds.valid_department_codes() == {"camera", "grip"}


def test_read_failure_returns_empty(monkeypatch):
    ds._reset_departments_cache()
    def boom(): raise RuntimeError("db down")
    monkeypatch.setattr(ds, "get_supabase_admin", lambda: (_ for _ in ()).throw(RuntimeError("x")))
    assert ds.get_departments_list() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_department_service.py -v`
Expected: FAIL — `ModuleNotFoundError: services.department_service`

- [ ] **Step 3: Write the module**

Create `backend/services/department_service.py`:

```python
"""Shared access to the `departments` reference list.

Moved here from routes/invite_routes.py so route modules don't import each
other. Same cache behaviour as before: one read, memoised for the process.
"""
import logging
from db.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)

_cache = None


def _reset_departments_cache():
    """Test helper — clear the process-level cache."""
    global _cache
    _cache = None


def get_departments_list():
    """Return [{code, name, color}, ...] ordered by sort_order; [] on failure."""
    global _cache
    if _cache is None:
        try:
            res = (get_supabase_admin().table("departments")
                   .select("code, name, color").order("sort_order").execute())
            _cache = res.data or []
        except Exception as e:  # noqa: BLE001 — reference data, degrade gracefully
            logger.error("Failed to fetch departments: %s", e)
            _cache = []
    return _cache


def get_department_name(code):
    for d in get_departments_list():
        if d["code"] == code:
            return d["name"]
    return code


def valid_department_codes():
    return {d["code"] for d in get_departments_list()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_department_service.py -v`
Expected: PASS

- [ ] **Step 5: Update `invite_routes.py` to use the shared module**

In `backend/routes/invite_routes.py`: delete the local `_departments_cache`, `get_departments_list()`, and `get_department_name()` definitions (around lines 35–47 and wherever `get_department_name` is defined). Add near the other imports:

```python
from services.department_service import get_departments_list, get_department_name
```

Leave every call site (`get_departments_list()`, `get_department_name(...)`) unchanged.

- [ ] **Step 6: Run the invite tests + full suite**

Run: `cd backend && pytest tests/ -q`
Expected: PASS (no regression in invite-related tests)

- [ ] **Step 7: Commit**

```bash
git add backend/services/department_service.py backend/routes/invite_routes.py backend/tests/test_department_service.py
git commit -m "refactor(departments): extract get_departments_list into services/department_service"
```

---

## Task 3: `contact_service` + `contacts_bp` — directory CRUD

**Files:**
- Create: `backend/services/contact_service.py`
- Create: `backend/routes/contact_routes.py`
- Modify: `backend/app.py` (import + register `contacts_bp` after `production_bp`, ~line 25 and ~line 69)
- Test: `backend/tests/test_contact_routes.py`

**Interfaces:**
- Consumes: `middleware.auth.require_auth`, `get_user_id`; `MockSupabase` pattern.
- Produces (`contact_service`):
  - `FIELDS` — tuple of writable column names: `("kind","name","company_name","role_tags","phone","email","agent_contact","standard_rate","rate_unit","notes")`
  - `NOT_FOUND` — module sentinel `object()`
  - `list_contacts(user_id, q=None, kind=None) -> list[dict]`
  - `create_contact(user_id, fields) -> dict`
  - `get_contact_with_usage(user_id, contact_id) -> dict | NOT_FOUND` — `{contact, assignments:[{crew_id, production_id, production_title, role}]}`
  - `update_contact(user_id, contact_id, fields) -> dict | NOT_FOUND`
  - `delete_contact(user_id, contact_id) -> "ok" | "not_found" | "in_use"`
  - `contact_usage(user_id, contact_id) -> list[dict]` — the `used_in` payload `[{production_id, production_title}]`
  - `_user_owns_contact(user_id, contact_id) -> bool`
  - `_normalize_role_tags(value) -> list[str]` — accepts `list` or comma string → trimmed non-empty list

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_contact_routes.py`. Copy the `MockTable` / `MockSupabase` classes verbatim from `backend/tests/test_production_routes.py` (top of file through `class MockSupabase`). Then:

```python
import services.contact_service as cs
import routes.contact_routes as cr  # noqa: F401
from middleware.auth import DEV_USER_ID


def _client():
    from flask import Flask
    from routes.contact_routes import contacts_bp
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(contacts_bp)
    return app.test_client()


def _store(**overrides):
    base = {"contacts": [], "production_crew": [], "productions": []}
    base.update(overrides)
    return base


def _patch(monkeypatch, store):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    mock = MockSupabase(store)
    monkeypatch.setattr(cs, "get_supabase_admin", lambda: mock)


def test_anonymous_is_401(monkeypatch):
    _patch(monkeypatch, _store())
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    assert _client().get("/api/contacts").status_code == 401


def test_create_requires_name(monkeypatch):
    _patch(monkeypatch, _store())
    assert _client().post("/api/contacts", json={}).status_code == 400
    assert _client().post("/api/contacts", json={"name": "  "}).status_code == 400


def test_create_rejects_bad_kind_and_rate_unit(monkeypatch):
    _patch(monkeypatch, _store())
    assert _client().post("/api/contacts", json={"name": "A", "kind": "robot"}).status_code == 400
    assert _client().post("/api/contacts", json={"name": "A", "rate_unit": "hour"}).status_code == 400


def test_create_normalizes_role_tags_from_string(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _client().post("/api/contacts", json={"name": "Gaffer Gary", "role_tags": "gaffer, best boy , "})
    assert resp.status_code == 201
    assert resp.get_json()["contact"]["role_tags"] == ["gaffer", "best boy"]
    assert resp.get_json()["contact"]["owner_id"] == DEV_USER_ID


def test_list_returns_only_callers_contacts(monkeypatch):
    store = _store(contacts=[
        {"id": "c1", "owner_id": DEV_USER_ID, "name": "Mine", "kind": "person"},
        {"id": "c2", "owner_id": "other", "name": "Theirs", "kind": "person"},
    ])
    _patch(monkeypatch, store)
    body = _client().get("/api/contacts").get_json()
    assert [c["name"] for c in body["contacts"]] == ["Mine"]


def test_get_patch_delete_other_users_contact_is_404(monkeypatch):
    store = _store(contacts=[{"id": "c2", "owner_id": "other", "name": "Theirs", "kind": "person"}])
    _patch(monkeypatch, store)
    assert _client().get("/api/contacts/c2").status_code == 404
    assert _client().patch("/api/contacts/c2", json={"name": "x"}).status_code == 404
    assert _client().delete("/api/contacts/c2").status_code == 404


def test_patch_updates_only_given_fields(monkeypatch):
    store = _store(contacts=[
        {"id": "c1", "owner_id": DEV_USER_ID, "name": "Old", "phone": "111", "kind": "person"},
    ])
    _patch(monkeypatch, store)
    resp = _client().patch("/api/contacts/c1", json={"phone": "222"})
    assert resp.status_code == 200
    assert store["contacts"][0]["name"] == "Old"
    assert store["contacts"][0]["phone"] == "222"


def test_delete_blocked_when_assigned(monkeypatch):
    store = _store(
        contacts=[{"id": "c1", "owner_id": DEV_USER_ID, "name": "Gary", "kind": "person"}],
        productions=[{"id": "p1", "owner_id": DEV_USER_ID, "title": "Farm Feature"}],
        production_crew=[{"id": "cw1", "production_id": "p1", "contact_id": "c1", "role": "Gaffer"}],
    )
    _patch(monkeypatch, store)
    resp = _client().delete("/api/contacts/c1")
    assert resp.status_code == 409
    assert resp.get_json()["used_in"] == [{"production_id": "p1", "production_title": "Farm Feature"}]
    assert len(store["contacts"]) == 1


def test_delete_unassigned_then_second_delete_404(monkeypatch):
    store = _store(contacts=[{"id": "c1", "owner_id": DEV_USER_ID, "name": "Gary", "kind": "person"}])
    _patch(monkeypatch, store)
    assert _client().delete("/api/contacts/c1").status_code == 200
    assert _client().delete("/api/contacts/c1").status_code == 404


def test_get_contact_lists_assignments(monkeypatch):
    store = _store(
        contacts=[{"id": "c1", "owner_id": DEV_USER_ID, "name": "Gary", "kind": "person"}],
        productions=[{"id": "p1", "owner_id": DEV_USER_ID, "title": "Farm Feature"}],
        production_crew=[{"id": "cw1", "production_id": "p1", "contact_id": "c1", "role": "Gaffer"}],
    )
    _patch(monkeypatch, store)
    body = _client().get("/api/contacts/c1").get_json()
    assert body["assignments"] == [
        {"crew_id": "cw1", "production_id": "p1", "production_title": "Farm Feature", "role": "Gaffer"}
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_contact_routes.py -v`
Expected: FAIL — `ModuleNotFoundError: services.contact_service` / `routes.contact_routes`

- [ ] **Step 3: Write `contact_service.py`**

```python
"""Account-level contacts directory (build-sequence step 2a).

Owner-scoped: every query filters owner_id == caller. Contacts have no
script axis, so get_script_role is not involved.
"""
from db.supabase_client import get_supabase_admin

NOT_FOUND = object()

FIELDS = ("kind", "name", "company_name", "role_tags", "phone", "email",
          "agent_contact", "standard_rate", "rate_unit", "notes")

VALID_KINDS = frozenset(("person", "company"))
VALID_RATE_UNITS = frozenset(("day", "week", "flat"))


def _normalize_role_tags(value):
    if value is None:
        return []
    parts = value.split(",") if isinstance(value, str) else list(value)
    return [str(p).strip() for p in parts if str(p).strip()]


def _get(supabase, user_id, contact_id):
    res = (supabase.table("contacts").select("*")
           .eq("id", contact_id).eq("owner_id", user_id).limit(1).execute())
    return res.data[0] if res.data else None


def _user_owns_contact(user_id, contact_id):
    return _get(get_supabase_admin(), user_id, contact_id) is not None


def list_contacts(user_id, q=None, kind=None):
    supabase = get_supabase_admin()
    query = supabase.table("contacts").select("*").eq("owner_id", user_id)
    if kind:
        query = query.eq("kind", kind)
    rows = query.order("name").execute().data or []
    if q:
        needle = q.strip().lower()
        rows = [r for r in rows if needle in " ".join(
            str(r.get(f) or "") for f in ("name", "company_name", "email")).lower()]
    return rows


def create_contact(user_id, fields):
    supabase = get_supabase_admin()
    row = {"owner_id": user_id, "created_by": user_id,
           "name": fields["name"].strip(),
           "kind": fields.get("kind") or "person",
           "role_tags": _normalize_role_tags(fields.get("role_tags"))}
    for f in ("company_name", "phone", "email", "agent_contact",
              "standard_rate", "rate_unit", "notes"):
        if fields.get(f) is not None:
            row[f] = fields[f]
    return supabase.table("contacts").insert(row).execute().data[0]


def contact_usage(user_id, contact_id):
    supabase = get_supabase_admin()
    crew = (supabase.table("production_crew").select("production_id")
            .eq("contact_id", contact_id).execute().data or [])
    pids = {c["production_id"] for c in crew}
    if not pids:
        return []
    prods = (supabase.table("productions").select("id, title")
             .in_("id", list(pids)).execute().data or [])
    return [{"production_id": p["id"], "production_title": p.get("title")} for p in prods]


def get_contact_with_usage(user_id, contact_id):
    supabase = get_supabase_admin()
    contact = _get(supabase, user_id, contact_id)
    if not contact:
        return NOT_FOUND
    crew = (supabase.table("production_crew").select("*")
            .eq("contact_id", contact_id).execute().data or [])
    prods = {p["id"]: p for p in (supabase.table("productions").select("id, title")
             .in_("id", list({c["production_id"] for c in crew}) or ["__none__"]).execute().data or [])}
    assignments = [{
        "crew_id": c["id"], "production_id": c["production_id"],
        "production_title": prods.get(c["production_id"], {}).get("title"),
        "role": c.get("role"),
    } for c in crew]
    return {"contact": contact, "assignments": assignments}


def update_contact(user_id, contact_id, fields):
    supabase = get_supabase_admin()
    if not _get(supabase, user_id, contact_id):
        return NOT_FOUND
    patch = {}
    for f in FIELDS:
        if f in fields:
            patch[f] = _normalize_role_tags(fields[f]) if f == "role_tags" else fields[f]
    if "name" in patch:
        patch["name"] = (patch["name"] or "").strip()
    if not patch:
        return _get(supabase, user_id, contact_id)
    res = (supabase.table("contacts").update(patch)
           .eq("id", contact_id).eq("owner_id", user_id).execute())
    return res.data[0] if res.data else NOT_FOUND


def delete_contact(user_id, contact_id):
    supabase = get_supabase_admin()
    if not _get(supabase, user_id, contact_id):
        return "not_found"
    used = (supabase.table("production_crew").select("id")
            .eq("contact_id", contact_id).limit(1).execute().data or [])
    if used:
        return "in_use"
    supabase.table("contacts").delete().eq("id", contact_id).eq("owner_id", user_id).execute()
    return "ok"
```

- [ ] **Step 4: Write `contact_routes.py`**

```python
"""Contacts directory HTTP routes. Logic in services/contact_service.py.
Owner-scoped: every route acts only on the caller's own contacts.
"""
from flask import Blueprint, request, jsonify

from middleware.auth import require_auth, get_user_id
from services import contact_service as svc
from services.contact_service import VALID_KINDS, VALID_RATE_UNITS

contacts_bp = Blueprint("contacts", __name__)


def _field_error(data):
    if data.get("kind") not in (None, *VALID_KINDS):
        return "kind must be 'person' or 'company'"
    if data.get("rate_unit") not in (None, *VALID_RATE_UNITS):
        return "rate_unit must be one of: day, week, flat"
    return None


@contacts_bp.route("/api/contacts", methods=["GET"])
@require_auth
def list_contacts():
    rows = svc.list_contacts(get_user_id(), request.args.get("q"), request.args.get("kind"))
    return jsonify({"contacts": rows})


@contacts_bp.route("/api/contacts", methods=["POST"])
@require_auth
def create_contact():
    data = request.get_json(silent=True) or {}
    if not (data.get("name") or "").strip():
        return jsonify({"error": "name is required"}), 400
    err = _field_error(data)
    if err:
        return jsonify({"error": err}), 400
    return jsonify({"contact": svc.create_contact(get_user_id(), data)}), 201


@contacts_bp.route("/api/contacts/<contact_id>", methods=["GET"])
@require_auth
def get_contact(contact_id):
    result = svc.get_contact_with_usage(get_user_id(), contact_id)
    if result is svc.NOT_FOUND:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify(result)


@contacts_bp.route("/api/contacts/<contact_id>", methods=["PATCH"])
@require_auth
def update_contact(contact_id):
    data = request.get_json(silent=True) or {}
    if "name" in data and not (data.get("name") or "").strip():
        return jsonify({"error": "name cannot be empty"}), 400
    err = _field_error(data)
    if err:
        return jsonify({"error": err}), 400
    result = svc.update_contact(get_user_id(), contact_id, data)
    if result is svc.NOT_FOUND:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify({"contact": result})


@contacts_bp.route("/api/contacts/<contact_id>", methods=["DELETE"])
@require_auth
def delete_contact(contact_id):
    user_id = get_user_id()
    outcome = svc.delete_contact(user_id, contact_id)
    if outcome == "not_found":
        return jsonify({"error": "Contact not found"}), 404
    if outcome == "in_use":
        return jsonify({"error": "Contact is assigned to crew",
                        "used_in": svc.contact_usage(user_id, contact_id)}), 409
    return jsonify({"success": True})
```

- [ ] **Step 5: Register the blueprint in `app.py`**

Add with the other route imports (near line 24):
```python
from routes.contact_routes import contacts_bp
```
Add after the `production_bp` registration (line ~68):
```python
app.register_blueprint(contacts_bp)  # Account-level contacts directory at /api/contacts/*
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_contact_routes.py -v`
Expected: PASS (all)

- [ ] **Step 7: Run the full suite**

Run: `cd backend && pytest tests/ -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/services/contact_service.py backend/routes/contact_routes.py backend/app.py backend/tests/test_contact_routes.py
git commit -m "feat(contacts): account-level contacts directory CRUD (contacts_bp)"
```

---

## Task 4: `production_crew_service` + crew routes on `production_bp`

**Files:**
- Create: `backend/services/production_crew_service.py`
- Modify: `backend/routes/production_routes.py` (add 4 crew routes; import the new service + `department_service.valid_department_codes`)
- Test: `backend/tests/test_production_crew_routes.py`

**Interfaces:**
- Consumes: `production_service._user_owns_production`, `production_service._get_production`, `production_service.get_supabase_admin`; `contact_service._get` for contact-ownership check (or a local equivalent); `department_service.valid_department_codes`.
- Produces (`production_crew_service`):
  - `ASSIGN_FIELDS = ("role","department_code","job_rate","job_rate_unit","start_date","end_date","notes")`
  - `list_crew(production_id) -> list[dict]` — crew rows each with `contact` embedded, ordered by `department_code` (nulls last) then `contact.name`
  - `add_crew(production_id, user_id, fields) -> dict | "bad_contact" | "bad_department"` — returns the created row with `contact` embedded
  - `update_crew(production_id, crew_id, fields) -> dict | "not_found" | "bad_department"`
  - `remove_crew(production_id, crew_id) -> None`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_production_crew_routes.py`. Copy `MockTable` / `MockSupabase` verbatim from `test_production_routes.py`. Then:

```python
import services.production_service as ps
import services.production_crew_service as pcs
import services.department_service as ds
import routes.production_routes as pr  # noqa: F401
from middleware.auth import DEV_USER_ID


def _client():
    from flask import Flask
    from routes.production_routes import production_bp
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(production_bp)
    return app.test_client()


def _store(**overrides):
    base = {"productions": [{"id": "p1", "owner_id": DEV_USER_ID, "title": "Farm Feature"}],
            "contacts": [{"id": "c1", "owner_id": DEV_USER_ID, "name": "Gary", "kind": "person"}],
            "production_crew": [], "scripts": [], "script_members": []}
    base.update(overrides)
    return base


def _patch(monkeypatch, store):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    mock = MockSupabase(store)
    for mod in (ps, pcs):
        monkeypatch.setattr(mod, "get_supabase_admin", lambda: mock)
    monkeypatch.setattr("middleware.authorization.get_supabase_admin", lambda: mock)
    monkeypatch.setattr(ds, "get_departments_list", lambda: [{"code": "camera", "name": "Camera", "color": "#1"}])


def test_add_crew_happy_path(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _client().post("/api/productions/p1/crew",
                          json={"contact_id": "c1", "role": "Gaffer", "department_code": "camera"})
    assert resp.status_code == 201
    body = resp.get_json()["crew"]
    assert body["role"] == "Gaffer"
    assert body["contact"]["name"] == "Gary"
    assert len(store["production_crew"]) == 1


def test_add_crew_null_department_ok(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _client().post("/api/productions/p1/crew", json={"contact_id": "c1", "role": "Caterer"})
    assert resp.status_code == 201


def test_add_crew_unknown_department_is_400(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _client().post("/api/productions/p1/crew",
                          json={"contact_id": "c1", "department_code": "wizardry"})
    assert resp.status_code == 400
    assert store["production_crew"] == []


def test_add_crew_contact_not_owned_is_400(monkeypatch):
    store = _store(contacts=[{"id": "c9", "owner_id": "other", "name": "X", "kind": "person"}])
    _patch(monkeypatch, store)
    resp = _client().post("/api/productions/p1/crew", json={"contact_id": "c9"})
    assert resp.status_code == 400


def test_non_owner_forbidden_on_all_crew_routes(monkeypatch):
    store = _store(productions=[{"id": "p1", "owner_id": "other", "title": "Theirs"}],
                   scripts=[{"id": "s1", "user_id": "other", "production_id": "p1"}],
                   script_members=[{"script_id": "s1", "user_id": DEV_USER_ID, "role": "viewer"}])
    _patch(monkeypatch, store)
    assert _client().get("/api/productions/p1/crew").status_code == 403
    assert _client().post("/api/productions/p1/crew", json={"contact_id": "c1"}).status_code == 403
    assert _client().patch("/api/productions/p1/crew/cw1", json={"role": "x"}).status_code == 403
    assert _client().delete("/api/productions/p1/crew/cw1").status_code == 403


def test_missing_production_is_404(monkeypatch):
    _patch(monkeypatch, _store(productions=[]))
    assert _client().get("/api/productions/pX/crew").status_code == 404


def test_list_crew_orders_by_department_then_name(monkeypatch):
    store = _store(
        contacts=[
            {"id": "c1", "owner_id": DEV_USER_ID, "name": "Zed", "kind": "person"},
            {"id": "c2", "owner_id": DEV_USER_ID, "name": "Amy", "kind": "person"},
            {"id": "c3", "owner_id": DEV_USER_ID, "name": "Bob", "kind": "person"},
        ],
        production_crew=[
            {"id": "w1", "production_id": "p1", "contact_id": "c1", "department_code": "camera"},
            {"id": "w2", "production_id": "p1", "contact_id": "c2", "department_code": "camera"},
            {"id": "w3", "production_id": "p1", "contact_id": "c3", "department_code": None},
        ],
    )
    _patch(monkeypatch, store)
    names = [c["contact"]["name"] for c in _client().get("/api/productions/p1/crew").get_json()["crew"]]
    assert names == ["Amy", "Zed", "Bob"]  # camera (Amy,Zed) then null-dept (Bob)


def test_patch_ignores_contact_id(monkeypatch):
    store = _store(production_crew=[
        {"id": "w1", "production_id": "p1", "contact_id": "c1", "role": "Gaffer"}])
    _patch(monkeypatch, store)
    resp = _client().patch("/api/productions/p1/crew/w1",
                           json={"role": "Best Boy", "contact_id": "cHACK"})
    assert resp.status_code == 200
    assert store["production_crew"][0]["contact_id"] == "c1"
    assert store["production_crew"][0]["role"] == "Best Boy"


def test_delete_then_redelete_is_noop_200(monkeypatch):
    store = _store(production_crew=[{"id": "w1", "production_id": "p1", "contact_id": "c1"}])
    _patch(monkeypatch, store)
    assert _client().delete("/api/productions/p1/crew/w1").status_code == 200
    assert _client().delete("/api/productions/p1/crew/w1").status_code == 200


def test_same_contact_two_roles_both_persist(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    _client().post("/api/productions/p1/crew", json={"contact_id": "c1", "role": "Gaffer"})
    _client().post("/api/productions/p1/crew", json={"contact_id": "c1", "role": "Best Boy"})
    assert len(store["production_crew"]) == 2


def test_delete_production_cascade_is_simulated_by_route(monkeypatch):
    # The DB cascades production_crew on production delete; the delete route
    # already nulls scripts explicitly. Assert crew rows are cleared too.
    store = _store(production_crew=[{"id": "w1", "production_id": "p1", "contact_id": "c1"}])
    _patch(monkeypatch, store)
    assert _client().delete("/api/productions/p1").status_code == 200
    assert store["production_crew"] == []
    assert len(store["contacts"]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_production_crew_routes.py -v`
Expected: FAIL — `ModuleNotFoundError: services.production_crew_service`

- [ ] **Step 3: Write `production_crew_service.py`**

```python
"""Crew assignments for a production (build-sequence step 2a).

A production_crew row joins a production to a contact with job-specific
detail. Owner-only — the route layer enforces via
production_service._user_owns_production.
"""
from services.production_service import get_supabase_admin
from services.department_service import valid_department_codes

ASSIGN_FIELDS = ("role", "department_code", "job_rate", "job_rate_unit",
                 "start_date", "end_date", "notes")


def _contacts_by_id(supabase, ids):
    if not ids:
        return {}
    rows = (supabase.table("contacts").select("*")
            .in_("id", list(ids)).execute().data or [])
    return {r["id"]: r for r in rows}


def _embed(supabase, crew_rows):
    contacts = _contacts_by_id(supabase, {c["contact_id"] for c in crew_rows})
    for c in crew_rows:
        c["contact"] = contacts.get(c["contact_id"])
    return crew_rows


def list_crew(production_id):
    supabase = get_supabase_admin()
    rows = (supabase.table("production_crew").select("*")
            .eq("production_id", production_id).execute().data or [])
    _embed(supabase, rows)
    rows.sort(key=lambda c: (
        c.get("department_code") is None,
        c.get("department_code") or "",
        (c.get("contact") or {}).get("name") or "",
    ))
    return rows


def _contact_owned_by(supabase, contact_id, user_id):
    res = (supabase.table("contacts").select("id")
           .eq("id", contact_id).eq("owner_id", user_id).limit(1).execute())
    return bool(res.data)


def add_crew(production_id, user_id, fields):
    supabase = get_supabase_admin()
    contact_id = fields.get("contact_id")
    if not contact_id or not _contact_owned_by(supabase, contact_id, user_id):
        return "bad_contact"
    dept = fields.get("department_code")
    if dept and dept not in valid_department_codes():
        return "bad_department"
    row = {"production_id": production_id, "contact_id": contact_id}
    for f in ASSIGN_FIELDS:
        if fields.get(f) is not None:
            row[f] = fields[f]
    created = supabase.table("production_crew").insert(row).execute().data[0]
    return _embed(supabase, [created])[0]


def _get_crew(supabase, production_id, crew_id):
    res = (supabase.table("production_crew").select("*")
           .eq("id", crew_id).eq("production_id", production_id).limit(1).execute())
    return res.data[0] if res.data else None


def update_crew(production_id, crew_id, fields):
    supabase = get_supabase_admin()
    if not _get_crew(supabase, production_id, crew_id):
        return "not_found"
    dept = fields.get("department_code")
    if dept and dept not in valid_department_codes():
        return "bad_department"
    patch = {f: fields[f] for f in ASSIGN_FIELDS if f in fields}
    if patch:
        supabase.table("production_crew").update(patch).eq("id", crew_id).execute()
    updated = _get_crew(supabase, production_id, crew_id)
    return _embed(supabase, [updated])[0]


def remove_crew(production_id, crew_id):
    (get_supabase_admin().table("production_crew").delete()
     .eq("id", crew_id).eq("production_id", production_id).execute())
```

- [ ] **Step 4: Add the crew routes to `production_routes.py`**

Add imports near the top:
```python
from services import production_crew_service as crew_svc
```

Add a shared guard helper and the four routes at the end of the file:
```python
def _require_production_owner(production_id):
    """Return (err_response, status) or (None, None) if the caller owns it."""
    user_id = get_user_id()
    if not svc._get_production(svc.get_supabase_admin(), production_id):
        return jsonify({"error": "Production not found"}), 404
    if not svc._user_owns_production(production_id, user_id):
        return jsonify({"error": "Insufficient permissions"}), 403
    return None, None


@production_bp.route("/api/productions/<production_id>/crew", methods=["GET"])
@require_auth
def list_production_crew(production_id):
    err, status = _require_production_owner(production_id)
    if err:
        return err, status
    return jsonify({"crew": crew_svc.list_crew(production_id)})


@production_bp.route("/api/productions/<production_id>/crew", methods=["POST"])
@require_auth
def add_production_crew(production_id):
    err, status = _require_production_owner(production_id)
    if err:
        return err, status
    data = request.get_json(silent=True) or {}
    result = crew_svc.add_crew(production_id, get_user_id(), data)
    if result == "bad_contact":
        return jsonify({"error": "contact_id must be one of your contacts"}), 400
    if result == "bad_department":
        return jsonify({"error": "Unknown department_code"}), 400
    return jsonify({"crew": result}), 201


@production_bp.route("/api/productions/<production_id>/crew/<crew_id>", methods=["PATCH"])
@require_auth
def update_production_crew(production_id, crew_id):
    err, status = _require_production_owner(production_id)
    if err:
        return err, status
    data = request.get_json(silent=True) or {}
    result = crew_svc.update_crew(production_id, crew_id, data)
    if result == "not_found":
        return jsonify({"error": "Crew assignment not found"}), 404
    if result == "bad_department":
        return jsonify({"error": "Unknown department_code"}), 400
    return jsonify({"crew": result})


@production_bp.route("/api/productions/<production_id>/crew/<crew_id>", methods=["DELETE"])
@require_auth
def remove_production_crew(production_id, crew_id):
    err, status = _require_production_owner(production_id)
    if err:
        return err, status
    crew_svc.remove_crew(production_id, crew_id)
    return jsonify({"success": True})
```

- [ ] **Step 5: Make the production-delete route clear crew rows**

In the existing `delete_production` route in `production_routes.py`, next to the line that nulls `scripts.production_id`, add:
```python
        svc.get_supabase_admin().table("production_crew").delete().eq(
            "production_id", production_id).execute()
```
(The real DB does this via `ON DELETE CASCADE`; doing it explicitly keeps behaviour identical under the mock, matching how the route already handles `scripts`.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_production_crew_routes.py -v`
Expected: PASS (all)

- [ ] **Step 7: Run the full suite**

Run: `cd backend && pytest tests/ -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/services/production_crew_service.py backend/routes/production_routes.py backend/tests/test_production_crew_routes.py
git commit -m "feat(crew): production_crew assignments + crew routes on production_bp"
```

---

## Task 5: `crew_import` — pure CSV parser

**Files:**
- Create: `backend/services/crew_import.py`
- Test: `backend/tests/test_crew_import.py`

**Interfaces:**
- Produces:
  - `RECOGNIZED_HEADERS = {"name","email","phone","company_name","role","department","rate","rate_unit","notes"}`
  - `parse_crew_csv(text, valid_codes, name_to_code) -> {"rows": [dict], "errors": [{"line": int, "reason": str}], "fatal": str | None}`
    - each `rows` dict: `{"name","email","phone","company_name","role","department_code","rate","rate_unit","notes"}` (missing keys → `None`); `line` is the 1-based source line (header = line 1, first data row = line 2)
    - `fatal` set (and `rows` empty) when there is no `name` column

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_crew_import.py`:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.crew_import import parse_crew_csv

CODES = {"camera", "grip"}
NAMES = {"camera": "Camera", "grip": "Grip"}


def _parse(text):
    return parse_crew_csv(text, CODES, NAMES)


def test_missing_name_column_is_fatal():
    out = _parse("email,role\na@b.com,Gaffer\n")
    assert out["fatal"] is not None
    assert out["rows"] == []


def test_header_normalization_and_extra_columns():
    out = _parse("  Name , Company Name ,Nonsense\nGary,Acme Lighting,ignore\n")
    assert out["fatal"] is None
    assert out["rows"][0]["name"] == "Gary"
    assert out["rows"][0]["company_name"] == "Acme Lighting"


def test_blank_name_row_skipped_with_line_number():
    out = _parse("name,role\n,Gaffer\nGary,Best Boy\n")
    assert [r["name"] for r in out["rows"]] == ["Gary"]
    assert out["errors"] == [{"line": 2, "reason": "missing name"}]


def test_non_numeric_rate_skips_row():
    out = _parse("name,rate\nGary,lots\n")
    assert out["rows"] == []
    assert out["errors"][0]["line"] == 2
    assert "rate" in out["errors"][0]["reason"].lower()


def test_bad_rate_unit_coerced_with_warning():
    out = _parse("name,rate_unit\nGary,hour\n")
    assert out["rows"][0]["rate_unit"] is None
    assert out["errors"][0]["reason"].lower().startswith("rate_unit")


def test_department_matched_by_code_or_name():
    out = _parse("name,department\nGary,camera\nAmy,Grip\n")
    assert [r["department_code"] for r in out["rows"]] == ["camera", "grip"]


def test_unknown_department_skips_row():
    out = _parse("name,department\nGary,wizardry\n")
    assert out["rows"] == []
    assert "department" in out["errors"][0]["reason"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_crew_import.py -v`
Expected: FAIL — `ModuleNotFoundError: services.crew_import`

- [ ] **Step 3: Write `crew_import.py`**

```python
"""Pure CSV parser for per-production crew import. No DB access."""
import csv
import io

RECOGNIZED_HEADERS = {"name", "email", "phone", "company_name", "role",
                      "department", "rate", "rate_unit", "notes"}
_VALID_RATE_UNITS = {"day", "week", "flat"}


def _norm_header(h):
    return (h or "").strip().lower().replace(" ", "_")


def parse_crew_csv(text, valid_codes, name_to_code):
    reader = csv.reader(io.StringIO(text))
    try:
        raw_header = next(reader)
    except StopIteration:
        return {"rows": [], "errors": [], "fatal": "empty file"}

    headers = [_norm_header(h) for h in raw_header]
    if "name" not in headers:
        return {"rows": [], "errors": [], "fatal": "CSV must have a 'name' column"}

    code_by_name = {v.lower(): k for k, v in (name_to_code or {}).items()}
    rows, errors = [], []

    for offset, raw in enumerate(reader):
        line = offset + 2  # header is line 1
        cell = {headers[i]: (raw[i].strip() if i < len(raw) else "")
                for i in range(len(headers))}

        name = cell.get("name", "").strip()
        if not name:
            errors.append({"line": line, "reason": "missing name"})
            continue

        dept_code = None
        dept_raw = cell.get("department", "").strip()
        if dept_raw:
            if dept_raw in valid_codes:
                dept_code = dept_raw
            elif dept_raw.lower() in code_by_name:
                dept_code = code_by_name[dept_raw.lower()]
            else:
                errors.append({"line": line, "reason": f"unknown department '{dept_raw}'"})
                continue

        rate = None
        rate_raw = cell.get("rate", "").strip()
        if rate_raw:
            try:
                rate = float(rate_raw)
            except ValueError:
                errors.append({"line": line, "reason": f"rate '{rate_raw}' is not a number"})
                continue

        rate_unit = cell.get("rate_unit", "").strip().lower() or None
        if rate_unit and rate_unit not in _VALID_RATE_UNITS:
            errors.append({"line": line, "reason": f"rate_unit '{rate_unit}' ignored (use day/week/flat)"})
            rate_unit = None

        rows.append({
            "name": name,
            "email": cell.get("email") or None,
            "phone": cell.get("phone") or None,
            "company_name": cell.get("company_name") or None,
            "role": cell.get("role") or None,
            "department_code": dept_code,
            "rate": rate,
            "rate_unit": rate_unit,
            "notes": cell.get("notes") or None,
        })

    return {"rows": rows, "errors": errors, "fatal": None}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_crew_import.py -v`
Expected: PASS (all)

- [ ] **Step 5: Commit**

```bash
git add backend/services/crew_import.py backend/tests/test_crew_import.py
git commit -m "feat(crew): pure CSV parser for crew import"
```

---

## Task 6: Crew import endpoint

**Files:**
- Modify: `backend/services/production_crew_service.py` (add `import_crew_csv`)
- Modify: `backend/routes/production_routes.py` (add the import route)
- Modify: `backend/tests/test_production_crew_routes.py` (add import tests)

**Interfaces:**
- Consumes: `crew_import.parse_crew_csv`, `department_service.get_departments_list`.
- Produces: `production_crew_service.import_crew_csv(production_id, user_id, csv_text) -> dict | "fatal"` where the dict is `{"created_contacts": int, "matched_contacts": int, "assignments_created": int, "skipped": [{"line": int, "reason": str}]}` and `"fatal"` (a tuple `("fatal", message)`) signals the no-`name`-column case.

- [ ] **Step 1: Write the failing tests** (append to `test_production_crew_routes.py`)

```python
import io


def _post_csv(client, pid, text):
    return client.post(f"/api/productions/{pid}/crew/import",
                       data={"file": (io.BytesIO(text.encode()), "crew.csv")},
                       content_type="multipart/form-data")


def test_import_happy_path_counts(monkeypatch):
    store = _store(contacts=[
        {"id": "c1", "owner_id": DEV_USER_ID, "name": "Existing", "email": "e@x.com", "kind": "person"}])
    _patch(monkeypatch, store)
    csv_text = (
        "name,email,role,department,rate,rate_unit\n"
        "New One,new@x.com,Gaffer,camera,800,day\n"
        "Existing,e@x.com,Best Boy,camera,,\n"
        ",,,,,\n"
    )
    resp = _post_csv(_client(), "p1", csv_text)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["created_contacts"] == 1
    assert body["matched_contacts"] == 1
    assert body["assignments_created"] == 2
    assert body["skipped"] == [{"line": 4, "reason": "missing name"}]
    assert len(store["production_crew"]) == 2


def test_import_is_idempotent_on_rerun(monkeypatch):
    store = _store(contacts=[])
    _patch(monkeypatch, store)
    csv_text = "name,role\nGary,Gaffer\n"
    _post_csv(_client(), "p1", csv_text)
    resp = _post_csv(_client(), "p1", csv_text)
    body = resp.get_json()
    assert body["assignments_created"] == 0
    assert body["skipped"] and "already on crew" in body["skipped"][0]["reason"]
    assert len(store["production_crew"]) == 1


def test_import_email_match_scoped_to_owner(monkeypatch):
    store = _store(contacts=[
        {"id": "cX", "owner_id": "other", "name": "Stranger", "email": "dup@x.com", "kind": "person"}])
    _patch(monkeypatch, store)
    _post_csv(_client(), "p1", "name,email\nMine,dup@x.com\n")
    # a new contact is created for the caller, the stranger's row is untouched
    mine = [c for c in store["contacts"] if c["owner_id"] == DEV_USER_ID]
    assert len(mine) == 1 and mine[0]["name"] == "Mine"


def test_import_no_name_column_is_400(monkeypatch):
    _patch(monkeypatch, _store())
    resp = _post_csv(_client(), "p1", "email,role\na@b.com,Gaffer\n")
    assert resp.status_code == 400


def test_import_non_owner_forbidden(monkeypatch):
    store = _store(productions=[{"id": "p1", "owner_id": "other", "title": "Theirs"}])
    _patch(monkeypatch, store)
    resp = _post_csv(_client(), "p1", "name\nGary\n")
    assert resp.status_code == 403
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && pytest tests/test_production_crew_routes.py -k import -v`
Expected: FAIL — route 404 / `AttributeError: import_crew_csv`

- [ ] **Step 3: Add `import_crew_csv` to `production_crew_service.py`**

```python
from services.crew_import import parse_crew_csv
from services.department_service import get_departments_list


def _find_contact_by_email(supabase, user_id, email):
    if not email:
        return None
    res = (supabase.table("contacts").select("*")
           .eq("owner_id", user_id).execute().data or [])
    for c in res:
        if (c.get("email") or "").strip().lower() == email.strip().lower():
            return c
    return None


def _has_same_role_assignment(supabase, production_id, contact_id, role):
    rows = (supabase.table("production_crew").select("role")
            .eq("production_id", production_id).eq("contact_id", contact_id)
            .execute().data or [])
    target = (role or "").strip().lower()
    return any((r.get("role") or "").strip().lower() == target for r in rows)


def import_crew_csv(production_id, user_id, csv_text):
    supabase = get_supabase_admin()
    depts = get_departments_list()
    valid_codes = {d["code"] for d in depts}
    name_to_code = {d["code"]: d["name"] for d in depts}

    parsed = parse_crew_csv(csv_text, valid_codes, name_to_code)
    if parsed["fatal"]:
        return ("fatal", parsed["fatal"])

    created = matched = assignments = 0
    skipped = list(parsed["errors"])

    for row in parsed["rows"]:
        line = None  # parsed rows don't carry line; dedup skips use role text
        contact = _find_contact_by_email(supabase, user_id, row["email"])
        if contact:
            matched += 1
        else:
            contact = supabase.table("contacts").insert({
                "owner_id": user_id, "created_by": user_id, "kind": "person",
                "name": row["name"], "email": row["email"], "phone": row["phone"],
                "company_name": row["company_name"], "role_tags": [],
                "standard_rate": row["rate"], "rate_unit": row["rate_unit"],
            }).execute().data[0]
            created += 1

        if _has_same_role_assignment(supabase, production_id, contact["id"], row["role"]):
            skipped.append({"line": 0, "reason": f"{row['name']} already on crew as {row['role'] or '(no role)'}"})
            continue

        supabase.table("production_crew").insert({
            "production_id": production_id, "contact_id": contact["id"],
            "role": row["role"], "department_code": row["department_code"],
            "job_rate": row["rate"], "job_rate_unit": row["rate_unit"],
            "notes": row["notes"],
        }).execute()
        assignments += 1

    return {"created_contacts": created, "matched_contacts": matched,
            "assignments_created": assignments, "skipped": skipped}
```

> Note: `parse_crew_csv` rows don't carry the source line; dedup-skip entries use `line: 0`. If line numbers on dedup skips matter to the reviewer, add a `line` key to each row dict in `crew_import.parse_crew_csv` (Task 5) and thread it through. Left out here to keep the parser's row shape minimal.

- [ ] **Step 4: Add the import route to `production_routes.py`**

```python
@production_bp.route("/api/productions/<production_id>/crew/import", methods=["POST"])
@require_auth
def import_production_crew(production_id):
    err, status = _require_production_owner(production_id)
    if err:
        return err, status
    upload = request.files.get("file")
    if not upload:
        return jsonify({"error": "file is required"}), 400
    raw = upload.read()
    if len(raw) > 1_000_000:
        return jsonify({"error": "File too large (max ~1 MB)"}), 400
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return jsonify({"error": "File must be UTF-8 CSV"}), 400
    result = crew_svc.import_crew_csv(production_id, get_user_id(), text)
    if isinstance(result, tuple) and result[0] == "fatal":
        return jsonify({"error": result[1]}), 400
    return jsonify(result)
```

- [ ] **Step 5: Run to verify they pass**

Run: `cd backend && pytest tests/test_production_crew_routes.py -v`
Expected: PASS (all, including the earlier crew tests)

- [ ] **Step 6: Full suite**

Run: `cd backend && pytest tests/ -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/services/production_crew_service.py backend/routes/production_routes.py backend/tests/test_production_crew_routes.py
git commit -m "feat(crew): CSV crew import endpoint with contact match + dedup guard"
```

---

## Task 7: `GET /api/productions/:id` returns `is_owner`

**Files:**
- Modify: `backend/services/production_service.py` (`get_production_for_viewer` — add `is_owner` to the returned dict)
- Modify: `backend/tests/test_production_routes.py` (assert the field)

**Interfaces:**
- Produces: `GET /api/productions/:id` response gains `"is_owner": bool` alongside `production` and `scripts`.

- [ ] **Step 1: Write the failing test** (append to `test_production_routes.py`)

```python
def test_get_production_includes_is_owner_flag(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID, "title": "Mine"}],
        scripts=[{"id": "s1", "user_id": DEV_USER_ID, "production_id": "p1", "title": "Ep 1"}],
    )
    _patch(monkeypatch, store)
    assert _client().get("/api/productions/p1").get_json()["is_owner"] is True


def test_get_production_is_owner_false_for_script_member(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": "other", "title": "Theirs"}],
        scripts=[{"id": "s1", "user_id": "other", "production_id": "p1", "title": "Ep 1"}],
        script_members=[{"script_id": "s1", "user_id": DEV_USER_ID, "role": "viewer"}],
    )
    _patch(monkeypatch, store)
    body = _client().get("/api/productions/p1").get_json()
    assert body["is_owner"] is False
    assert {s["id"] for s in body["scripts"]} == {"s1"}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/test_production_routes.py -k is_owner -v`
Expected: FAIL — `KeyError: 'is_owner'`

- [ ] **Step 3: Add the field**

In `production_service.get_production_for_viewer`, change the final return:
```python
    return {"production": prod, "scripts": scripts, "is_owner": is_owner}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/test_production_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/production_service.py backend/tests/test_production_routes.py
git commit -m "feat(production): GET /api/productions/:id returns is_owner"
```

---

## Task 8: `apiService.js` — contacts + crew functions

**Files:**
- Modify: `frontend/src/services/apiService.js` (add a new section after the Productions section, ~line 2510)

**Interfaces:**
- Produces (all `async`, return `response.data`, `console.error` + rethrow on failure — match the existing Productions helpers exactly):
  - `listContacts({ q, kind } = {}) -> {contacts: []}`
  - `createContact(payload) -> {contact}`
  - `getContact(id) -> {contact, assignments: []}`
  - `updateContact(id, payload) -> {contact}`
  - `deleteContact(id) -> {success: true}` (throws with `error.response.status === 409` and `error.response.data.used_in` on the blocked case)
  - `listProductionCrew(productionId) -> {crew: []}`
  - `addProductionCrew(productionId, payload) -> {crew}`
  - `updateProductionCrew(productionId, crewId, payload) -> {crew}`
  - `removeProductionCrew(productionId, crewId) -> {success: true}`
  - `importProductionCrew(productionId, file) -> {created_contacts, matched_contacts, assignments_created, skipped}`

- [ ] **Step 1: Add the functions**

```javascript
// ============================================
// Contacts directory + production crew (build-sequence step 2a)
// ============================================

/** List the current user's contacts. @param {{q?: string, kind?: string}} params */
export const listContacts = async (params = {}) => {
    try {
        const response = await api.get('/api/contacts', { params });
        return response.data;
    } catch (error) {
        console.error('Error listing contacts:', error);
        throw error;
    }
};

export const createContact = async (payload) => {
    try {
        const response = await api.post('/api/contacts', payload);
        return response.data;
    } catch (error) {
        console.error('Error creating contact:', error);
        throw error;
    }
};

export const getContact = async (id) => {
    try {
        const response = await api.get(`/api/contacts/${id}`);
        return response.data;
    } catch (error) {
        console.error('Error getting contact:', error);
        throw error;
    }
};

export const updateContact = async (id, payload) => {
    try {
        const response = await api.patch(`/api/contacts/${id}`, payload);
        return response.data;
    } catch (error) {
        console.error('Error updating contact:', error);
        throw error;
    }
};

/** Delete a contact. Throws with response.status 409 + data.used_in if still assigned. */
export const deleteContact = async (id) => {
    try {
        const response = await api.delete(`/api/contacts/${id}`);
        return response.data;
    } catch (error) {
        console.error('Error deleting contact:', error);
        throw error;
    }
};

export const listProductionCrew = async (productionId) => {
    try {
        const response = await api.get(`/api/productions/${productionId}/crew`);
        return response.data;
    } catch (error) {
        console.error('Error listing production crew:', error);
        throw error;
    }
};

export const addProductionCrew = async (productionId, payload) => {
    try {
        const response = await api.post(`/api/productions/${productionId}/crew`, payload);
        return response.data;
    } catch (error) {
        console.error('Error adding production crew:', error);
        throw error;
    }
};

export const updateProductionCrew = async (productionId, crewId, payload) => {
    try {
        const response = await api.patch(`/api/productions/${productionId}/crew/${crewId}`, payload);
        return response.data;
    } catch (error) {
        console.error('Error updating production crew:', error);
        throw error;
    }
};

export const removeProductionCrew = async (productionId, crewId) => {
    try {
        const response = await api.delete(`/api/productions/${productionId}/crew/${crewId}`);
        return response.data;
    } catch (error) {
        console.error('Error removing production crew:', error);
        throw error;
    }
};

export const importProductionCrew = async (productionId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    try {
        const response = await api.post(
            `/api/productions/${productionId}/crew/import`, formData,
            { headers: { 'Content-Type': 'multipart/form-data' } });
        return response.data;
    } catch (error) {
        console.error('Error importing production crew:', error);
        throw error;
    }
};
```

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/apiService.js
git commit -m "feat(crew): apiService functions for contacts + production crew"
```

---

## Task 9: `/contacts` directory page

**Files:**
- Create: `frontend/src/pages/ContactsListPage.jsx`
- Create: `frontend/src/components/contacts/ContactFormModal.jsx`
- Create: `frontend/src/components/contacts/ContactDetailDrawer.jsx`
- Modify: `frontend/src/App.jsx` (import + `<Route path="contacts" element={<ContactsListPage />} />` next to the `productions` routes)
- Modify: `frontend/src/components/layout/TopBar.jsx` (a `NavLink` to `/contacts` after the Productions one; import an icon — use `Contact` or `Users` from `lucide-react`)
- Reuse: `frontend/src/pages/ProductionPages.css` (import it; add a couple of contacts-specific classes at the bottom if needed)

**Interfaces:**
- Consumes: `listContacts`, `createContact`, `getContact`, `updateContact`, `deleteContact` from `apiService`; `Spinner` from `../components/ui`.
- Produces: default-exported `ContactsListPage` component; route `/contacts`.

- [ ] **Step 1: Build `ContactFormModal.jsx`**

A controlled modal (match the structure of `ProductionScriptPicker.jsx` — same overlay/panel classnames from `ProductionPages.css`). Props: `{ initial, onSubmit, onClose, saving }`. Fields:
- `name` (text, required — disable submit when blank)
- `kind` (select: person / company)
- `company_name` (text)
- `role_tags` (text input; on submit split on comma into an array — the backend also accepts the raw string, but send an array for clarity)
- `phone`, `email`, `agent_contact` (text)
- `standard_rate` (number), `rate_unit` (select: — / day / week / flat)
- `notes` (textarea)

`onSubmit(payload)` where `payload` omits empty strings (send `undefined`, not `""`, so validation is clean). Used for both create and edit (when `initial` is set, prefill and the title says "Edit contact").

- [ ] **Step 2: Build `ContactDetailDrawer.jsx`**

Props: `{ contactId, onClose, onChanged, onDeleted }`. On mount calls `getContact(contactId)` → shows the `ContactFormModal` fields inline (or reuse the modal in "drawer" mode — your call; keep it one form component if practical) plus:
- a **"Used on"** section listing `assignments` — each row: `production_title` + `role`, linking to `/productions/:production_id`
- a **Delete** button. On click → `deleteContact(id)`. On success → `onDeleted()`. On `error.response?.status === 401`? no — on `error.response?.status === 409` → show an inline error: `"Assigned to " + used_in.map(u => u.production_title).join(', ') + " — remove those crew assignments first."` (read `error.response.data.used_in`).
- a **Save** button → `updateContact(id, payload)` → `onChanged()`.

- [ ] **Step 3: Build `ContactsListPage.jsx`**

Structure mirrors `ProductionsListPage.jsx`:
- state: `contacts`, `loading`, `error`, `q` (search box, debounced ~300ms → refetch with `{ q }`), `kindFilter`, `creating` (bool), `openId` (contact id for the drawer)
- `load()` → `listContacts({ q, kind })` → set state; full-page `<Spinner>` while loading; error panel; empty state ("No contacts yet — add your address book of crew and vendors.")
- header row: title "Contacts", a search `<input>`, a kind `<select>` (all / person / company), a "New contact" button
- table: columns Name, Kind (badge), Company, Role tags (comma-joined), Phone, Email. Row `onClick` → `setOpenId(row.id)`
- `{creating && <ContactFormModal onSubmit={...} onClose={...} saving={saving} />}` → `createContact` → close + `load()`
- `{openId && <ContactDetailDrawer contactId={openId} onClose={() => setOpenId(null)} onChanged={load} onDeleted={() => { setOpenId(null); load(); }} />}`

- [ ] **Step 4: Wire the route + nav**

`App.jsx` — near the productions routes:
```jsx
import ContactsListPage from './pages/ContactsListPage';
// ...
<Route path="contacts" element={<ContactsListPage />} />
```

`TopBar.jsx` — after the Productions `NavLink`:
```jsx
<NavLink
  to="/contacts"
  className={({ isActive }) => `topbar-nav-item ${isActive ? 'active' : ''}`}
>
  <Contact size={18} />
  <span>Contacts</span>
</NavLink>
```
Add `Contact` to the existing `lucide-react` import in that file. Eyeball `.topbar-nav` at ~1024px width — if the four items wrap badly, reduce horizontal padding on `.topbar-nav-item` in the relevant CSS (no redesign).

- [ ] **Step 5: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds

- [ ] **Step 6: Manual check**

Start `npm run dev`; log in; visit `/contacts`; create a person and a company; edit one; search; open the drawer.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/ContactsListPage.jsx frontend/src/components/contacts/ frontend/src/App.jsx frontend/src/components/layout/TopBar.jsx
git commit -m "feat(contacts): /contacts directory page with form modal + detail drawer"
```

---

## Task 10: `ProductionDetailPage` tab refactor + `is_owner`

**Files:**
- Modify: `frontend/src/pages/ProductionDetailPage.jsx` (extract Overview into a sub-component; add a tab strip; use real `is_owner`)
- Create: `frontend/src/components/productions/ProductionOverviewTab.jsx`
- Modify: `frontend/src/pages/ProductionPages.css` (tab-strip styles)

**Interfaces:**
- Consumes: `data.is_owner` from `getProduction` (Task 7).
- Produces: `ProductionDetailPage` renders a `.production-tabs` strip with `Overview` always, `Crew` only when `isOwner`; `activeTab` state (`'overview' | 'crew'`); `ProductionOverviewTab` receives `{ production, scripts, form, setForm, isOwner, saving, onSave, onAddScript, onRemoveScript, picking, setPicking }`.

- [ ] **Step 1: Extract `ProductionOverviewTab.jsx`**

Move the current JSX that renders the Overview form + associated-scripts list + `ProductionScriptPicker` out of `ProductionDetailPage.jsx` into `ProductionOverviewTab.jsx`, taking the props listed above. No behaviour change — pure extraction.

- [ ] **Step 2: Replace the optimistic owner heuristic**

In `ProductionDetailPage.jsx` `load()`: replace `setIsOwner(true)` with `setIsOwner(!!data.is_owner)`. Remove the now-inaccurate comment block about the heuristic.

- [ ] **Step 3: Add the tab strip**

In `ProductionDetailPage.jsx`, after the header, before the body:
```jsx
const [activeTab, setActiveTab] = useState('overview');
const tabs = [{ id: 'overview', label: 'Overview' }];
if (isOwner) tabs.push({ id: 'crew', label: 'Crew' });
```
```jsx
<div className="production-tabs">
  {tabs.map((t) => (
    <button
      key={t.id}
      className={`production-tab ${activeTab === t.id ? 'active' : ''}`}
      onClick={() => setActiveTab(t.id)}
    >
      {t.label}
    </button>
  ))}
</div>
{activeTab === 'overview' && <ProductionOverviewTab {...overviewProps} />}
{activeTab === 'crew' && isOwner && <ProductionCrewTab productionId={productionId} />}
```
(Import `ProductionCrewTab` — built in Task 11. For this task, a placeholder `const ProductionCrewTab = () => null;` is acceptable **only if** Task 11 immediately follows; prefer to land Task 11 in the same branch. If splitting, stub with a `<div>Crew — coming next</div>` and note it.)

Guard against `activeTab === 'crew'` when `isOwner` flips false after load (e.g. reload as non-owner): in an effect, `if (!isOwner && activeTab === 'crew') setActiveTab('overview')`.

- [ ] **Step 4: CSS**

Add to `ProductionPages.css`:
```css
.production-tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--border, #2a3550); margin-bottom: 20px; }
.production-tab { background: none; border: none; padding: 10px 16px; color: var(--text-dim, #8a94ad); cursor: pointer; border-bottom: 2px solid transparent; font-size: 14px; }
.production-tab.active { color: var(--text, #e8ecf5); border-bottom-color: var(--accent, #f5a623); }
```
(Match the actual token names used elsewhere in the file — check `ProductionPages.css` and copy its convention.)

- [ ] **Step 5: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds

- [ ] **Step 6: Manual check**

Open a production you own → see Overview + Crew tabs, Overview works as before. (Crew tab content lands in Task 11.)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/ProductionDetailPage.jsx frontend/src/components/productions/ProductionOverviewTab.jsx frontend/src/pages/ProductionPages.css
git commit -m "refactor(production): tab strip on detail page + real is_owner"
```

---

## Task 11: Crew tab — roster, add/edit/remove, CSV import

**Files:**
- Create: `frontend/src/components/productions/ProductionCrewTab.jsx`
- Create: `frontend/src/components/productions/CrewAssignmentModal.jsx`
- Create: `frontend/src/components/productions/CrewImportModal.jsx`
- Create: `frontend/public/crew-import-template.csv`
- Modify: `frontend/src/pages/ProductionDetailPage.jsx` (swap the Task 10 stub for the real import)

**Interfaces:**
- Consumes: `listProductionCrew`, `addProductionCrew`, `updateProductionCrew`, `removeProductionCrew`, `importProductionCrew`, `listContacts`, `createContact`; the departments list — fetch via a new tiny helper `getDepartments()` in `apiService` **only if** one doesn't already exist. Check first: `grep -n "departments" frontend/src/services/apiService.js`. If absent, add:
  ```javascript
  export const getDepartments = async () => {
      try { const r = await api.get('/api/departments'); return r.data; }
      catch (e) { console.error('Error getting departments:', e); throw e; }
  };
  ```
  and confirm `GET /api/departments` exists in the backend (`grep -rn "api/departments" backend/routes/`). **If that endpoint does not exist**, add a 3-line read-only route to `invite_routes.py` or a small `misc_routes` returning `get_departments_list()` — a `department_code` `<select>` needs the list. Add a backend test asserting it returns `{departments: [...]}`.
- Produces: default-exported `ProductionCrewTab` taking `{ productionId }`.

- [ ] **Step 1: Confirm / add the departments endpoint**

Run: `grep -rn "api/departments\|departments" backend/routes/*.py | grep -i route`
If no GET endpoint returns the list, add to `backend/routes/invite_routes.py`:
```python
@invite_bp.route("/api/departments", methods=["GET"])
@require_auth
def list_departments():
    return jsonify({"departments": get_departments_list()})
```
and a test in `backend/tests/test_department_service.py` or a new `test_departments_route.py`:
```python
def test_departments_route_returns_list(monkeypatch):
    # patch get_departments_list to a fixed list; assert 200 + {"departments": [...]}
```
Commit this separately:
```bash
git add backend/routes/invite_routes.py backend/tests/
git commit -m "feat(departments): GET /api/departments read endpoint"
```

- [ ] **Step 2: `frontend/public/crew-import-template.csv`**

```csv
name,email,phone,company_name,role,department,rate,rate_unit,notes
Jane Gaffer,jane@example.com,+27 82 000 0000,,Gaffer,camera,900,day,Owns own kit
Acme Catering,info@acmecatering.com,+27 21 555 0000,Acme Catering,Caterer,,15000,flat,Vegan options
```

- [ ] **Step 3: `CrewAssignmentModal.jsx`**

Props: `{ productionId, initial, departments, onSaved, onClose }`.
- **Contact field** — a combobox:
  - text input; on type (debounced) → `listContacts({ q })` → dropdown of matches (name + company)
  - a "＋ Create new contact" row → expands inline fields (name required, plus phone/email/company) → on assignment submit, `createContact` first, then use the returned `contact.id`
  - when `initial` is set (edit mode), the contact is fixed and shown read-only (backend ignores `contact_id` on PATCH)
- **Assignment fields:** `role` (text), `department_code` (`<select>` from `departments`, with a "— Vendor / none —" option = `''`), `job_rate` (number), `job_rate_unit` (select), `start_date` / `end_date` (date inputs), `notes` (textarea)
- Submit: create mode → `addProductionCrew(productionId, { contact_id, ...fields })`; edit mode → `updateProductionCrew(productionId, initial.id, fields)`. Then `onSaved()`.

- [ ] **Step 4: `CrewImportModal.jsx`**

Props: `{ productionId, onDone, onClose }`.
- a `<a href="/crew-import-template.csv" download>` link ("Download template")
- a file `<input type="file" accept=".csv">`
- on upload → `importProductionCrew(productionId, file)` → show the summary:
  `${r.created_contacts} added, ${r.matched_contacts} matched existing, ${r.assignments_created} assigned` and, if `r.skipped.length`, a list of `line N: reason` (omit "line 0" — just show the reason for dedup skips)
- on `error.response?.status === 400` → show `error.response.data.error`
- a "Done" button → `onDone()` (parent refetches crew)

- [ ] **Step 5: `ProductionCrewTab.jsx`**

- state: `crew`, `loading`, `error`, `departments`, `editing` (crew row or `null`), `adding` (bool), `importing` (bool)
- on mount: `listProductionCrew(productionId)` + `getDepartments()`
- header: "Crew" + buttons "Add crew" / "Import CSV"
- body: group `crew` by `department_code`. Render a section per department (label from `departments`, fallback "Unassigned / Vendors" for null). Each row: `contact.name`, `role`, rate (`job_rate` + `job_rate_unit`), date range, Edit / Remove.
  - Remove → `window.confirm` then `removeProductionCrew(productionId, row.id)` → refetch
  - Edit → `setEditing(row)` → `CrewAssignmentModal` in edit mode
- empty state: "No crew yet. Add people or import a CSV."
- `{adding && <CrewAssignmentModal .../>}`, `{editing && <CrewAssignmentModal initial={editing} .../>}`, `{importing && <CrewImportModal .../>}` — each `onSaved`/`onDone` closes and refetches.

- [ ] **Step 6: Swap the stub in `ProductionDetailPage.jsx`**

Replace the Task 10 placeholder with `import ProductionCrewTab from '../components/productions/ProductionCrewTab';` and the real render.

- [ ] **Step 7: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds

- [ ] **Step 8: Manual check (full flow)**

`npm run dev`; open a production you own → Crew tab:
1. Add crew picking an existing contact
2. Add crew creating a new contact inline
3. Edit a rate; remove an assignment
4. Import `crew-import-template.csv` — confirm the summary, rows appear grouped
5. Re-import the same file — confirm 0 new assignments (dedup)
6. Go to `/contacts`, open one of the imported contacts, try to delete → see the 409 message
7. Delete the production → confirm the contacts survive in `/contacts`

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/productions/ProductionCrewTab.jsx frontend/src/components/productions/CrewAssignmentModal.jsx frontend/src/components/productions/CrewImportModal.jsx frontend/public/crew-import-template.csv frontend/src/pages/ProductionDetailPage.jsx frontend/src/services/apiService.js
git commit -m "feat(crew): production Crew tab — roster, add/edit/remove, CSV import"
```

---

## Task 12: Docs — SLATEONE_FEATURES + backlog

**Files:**
- Modify: `docs/SLATEONE_FEATURES.md` (add a "Productions → Crew & Contacts" subsection)
- Modify: `docs/BACKLOG.md` (mark step 2a shipped; note slice 2b — `production_members` — is the next production slice)

**Interfaces:** none.

- [ ] **Step 1: SLATEONE_FEATURES.md**

Find the Productions section added by the spine (grep `Productions`). Add a subsection:
```markdown
### Crew & Contacts

- **Contacts directory** (`/contacts`) — an account-level address book of
  people and companies (crew, vendors, agents). Canonical: editing a
  contact updates it everywhere it's used. Owner-only.
- **Production crew** — each production has a Crew tab: assign contacts to
  the production with a role, department, this-job rate, and date range.
  One person can hold multiple roles. Grouped by department, with an
  "Unassigned / Vendors" bucket.
- **CSV crew import** — upload a crew list onto a production; rows
  create-or-match contacts (by email) and create assignments in one pass.
  A downloadable template defines the columns. Re-importing is safe
  (duplicate role assignments are skipped).
- Deleting a contact that's still on a crew is blocked with a list of
  where it's used. Deleting a production removes its crew assignments; the
  contacts remain.

Not yet: sharing a production's crew/contacts with non-owner team members
(the `production_members` permission layer — next slice).
```

- [ ] **Step 2: BACKLOG.md**

In the "Production data model" standing note, append: "Step 2a (crew + contacts, owner-only) shipped `<date>` — `docs/superpowers/plans/2026-08-31-crew-contacts.md`. Next: slice 2b — `production_members` permission layer (`can_view_sensitive`, seat consumption, non-owner directory scope, permission inheritance)." Update item 1 in the "Do next" list to point at 2b.

- [ ] **Step 3: Commit**

```bash
git add docs/SLATEONE_FEATURES.md docs/BACKLOG.md
git commit -m "docs(crew): document contacts directory + production crew; backlog step 2a shipped"
```

---

## Self-Review

**1. Spec coverage:**

| Spec section | Task |
|---|---|
| `contacts` table | Task 1 |
| `production_crew` table | Task 1 |
| RLS owner-only backstop | Task 1 |
| delete-user cascade comment | Task 1 (comment); Task 4 test simulates cascade |
| `get_departments_list` shared module | Task 2 |
| `contacts_bp` CRUD + delete guard (409 + used_in) | Task 3 |
| `GET /api/contacts/:id` assignments list | Task 3 |
| crew routes on `production_bp`, owner-only | Task 4 |
| department_code Python validation, nullable | Task 4 (+ Task 5 for import) |
| no unique constraint / multi-role | Task 1 (schema) + Task 4 test |
| production delete cascades crew | Task 4 Step 5 + test |
| `crew_import.py` pure parser + all row/error rules | Task 5 |
| import route: email match (owner-scoped), always-create, dedup guard, summary, non-transactional | Task 6 |
| `GET /api/productions/:id` gains `is_owner` | Task 7 |
| `apiService` functions | Task 8 |
| `/contacts` page + nav + route + drawer + form modal | Task 9 |
| Crew tab hidden for non-owners | Task 10 (tab gated on `isOwner`) |
| `ProductionDetailPage` tab refactor | Task 10 |
| Crew tab: grouped roster, add (pick/create contact), edit, remove | Task 11 |
| CSV import modal + template file | Task 11 |
| departments `<select>` needs a list endpoint | Task 11 Step 1 |
| docs | Task 12 |
| **Out of scope** — `production_members`, `can_view_sensitive`, seats, non-owner access, `default_call_offset`, locations, contact photos | not implemented (correct) |

No gaps.

**2. Placeholder scan:** Task 10 Step 3 mentions a temporary `ProductionCrewTab` stub — explicitly resolved in Task 11 Step 6, and the guidance says to land them on the same branch. Task 11 Step 1 is conditional (endpoint may exist) with both branches spelled out. No bare TODOs, no "add error handling", every code step has real code.

**3. Type consistency:**
- `production_crew_service` returns embedded `contact` key — used consistently in Task 4 tests, Task 11 UI.
- `delete_contact` → `"ok" | "not_found" | "in_use"` — matched in Task 3 route + tests.
- `add_crew` → `dict | "bad_contact" | "bad_department"` — matched in Task 4 route + tests.
- `import_crew_csv` → `dict | ("fatal", msg)` — Task 6 route checks `isinstance(result, tuple)`.
- `parse_crew_csv` → `{rows, errors, fatal}` — Task 5 tests + Task 6 consumer agree.
- `is_owner` key — Task 7 produces, Task 10 consumes.
- `used_in` shape `[{production_id, production_title}]` — Task 3 (`contact_usage`) + Task 9 drawer agree.

Consistent.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-08-31-crew-contacts.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review.

**Which approach?**
