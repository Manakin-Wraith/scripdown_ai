# Cast & Casting (v1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a production attach a real actor (contact, agent, headshot, booking status, blackout dates) to each character in a script, and flag availability conflicts against the shooting schedule.

**Architecture:** A per-script `casting` table (one row per character, bound to the canonical character name) plus a `casting_unavailability` child table. A new Flask blueprint `casting_bp` with a `casting_service` for persistence, serialization, and conflict computation. A new React route `scripts/:scriptId/cast` rendering a headshot-forward character list and an autosave detail drawer. Conflicts are computed server-side and surfaced read-only on the Cast page, the Schedule page, and Day Out of Days.

**Tech Stack:** Flask 3 / Python 3.13, `supabase-py` (service-role key), Postgres (Supabase). React 18 + Vite (plain JSX), axios via `frontend/src/services/apiService.js`, shared UI primitives in `frontend/src/components/ui/`. Backend tests: `pytest`. Frontend gate: `npm run build`.

**Spec:**
- `docs/superpowers/specs/2026-08-27-cast-casting-v1-design.md` (data model, API, architecture)
- `docs/superpowers/specs/2026-08-27-cast-casting-v1-ui-ux.md` (layout, states, interaction, copy)

## Global Constraints

- **Auth:** every route stacks `@require_auth` then `@require_script_role(<min_role>, resolver=<resolver>)`. `ROLE_RANK = {'viewer':1,'member':2,'admin':3,'owner':4}`; `require_script_role('admin')` also admits the owner. The decorator sets `g.script_role` and `g.resolved_script_id`.
- **DB access:** backend uses the Supabase **service-role key** via `from db.supabase_client import db` (`db.client` is the raw client) or `from db.supabase_client import get_supabase_admin`. RLS is defense-in-depth only.
- **Character names** are stored and compared **uppercased, stripped** (`name.strip().upper()`) — matches `merge_characters` and the alias map.
- **Status vocabulary:** exactly `wishlist | offer | booked | declined | released`. Default `wishlist`.
- **Contact fields** (`contact_phone`, `contact_email`, `agent_contact`) are omitted from any API payload unless `g.script_role in ('admin','owner')`.
- **Conflicts** are computed only for casting rows with `status in ('booked','offer')`, only for `shooting_days` with a non-null `shoot_date`. Informational only — never block.
- **Migrations** are applied manually against the Supabase project (`run_migration.py` is dead SQLite code). A migration task delivers the `.sql` file; applying it is a documented manual step.
- **Frontend copy:** sentence case except character names (uppercase) and the `Cast` nav label. Verbatim strings are in UI-UX spec §8.
- **Frontend lint is broken repo-wide** — gate frontend tasks on `npm run build`, never `npm run lint`.
- **Commits:** one per task minimum, conventional-commit style, ending with the two trailers used across this repo:
  ```
  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_015mHatrMUSyPmEAgh1tjTg6
  ```

---

## File Structure

**Backend — create**
- `backend/db/migrations/048_casting.sql` — `casting` + `casting_unavailability` tables, RLS, `updated_at` trigger.
- `backend/services/casting_service.py` — persistence, `breakdown_characters()`, `serialize()`, `compute_conflicts()`.
- `backend/routes/casting_routes.py` — blueprint `casting_bp`, all HTTP endpoints.
- `backend/tests/test_casting_service.py`
- `backend/tests/test_casting_routes.py`
- `backend/tests/test_casting_conflicts.py`
- `backend/tests/test_casting_merge_hook.py`

**Backend — modify**
- `backend/middleware/authorization.py` — add `from_casting` and `from_casting_unavailability` resolvers.
- `backend/app.py` — register `casting_bp`.
- `backend/routes/supabase_routes.py` — `merge_characters`: carry casting rows to the new canonical name.

**Frontend — create**
- `frontend/src/components/cast/CastPage.jsx` + `CastPage.css`
- `frontend/src/components/cast/CastRow.jsx`
- `frontend/src/components/cast/StatusBadge.jsx`
- `frontend/src/components/cast/CastingDetailPanel.jsx` + `CastingDetailPanel.css`
- `frontend/src/components/cast/UnavailabilityEditor.jsx`
- `frontend/src/components/schedule/ConflictPanel.jsx` + `ConflictPanel.css`

**Frontend — modify**
- `frontend/src/services/apiService.js` — 8 new calls.
- `frontend/src/components/layout/SectionNav.jsx` — `Cast` tab + `activeKey` regex.
- `frontend/src/App.jsx` — `scripts/:scriptId/cast` route.
- `frontend/src/components/schedule/ShootingSchedulePage.jsx` — mount `ConflictPanel`, day-header dots.
- Day Out of Days render path (`backend/services/report_service.py` `_render_day_out_of_days*`) — conflict ring + footnote (final, optional task).

---

## Task 1: Migration — `casting` and `casting_unavailability` tables

**Files:**
- Create: `backend/db/migrations/048_casting.sql`

**Interfaces:**
- Produces: tables `casting` (columns `id, script_id, character_name, actor_name, status, contact_phone, contact_email, agent_contact, headshot_path, notes, created_by, created_at, updated_at`) and `casting_unavailability` (`id, casting_id, start_date, end_date, reason, created_at`).

- [ ] **Step 1: Write the migration file**

```sql
-- Migration 048: Cast & Casting (v1)
-- Per-script casting record (one row per character) + blackout date ranges.
-- See docs/superpowers/specs/2026-08-27-cast-casting-v1-design.md §4.
-- Apply manually against the Supabase project (run_migration.py is dead).

-- ============================================
-- 1. casting — one row per character per script
-- ============================================
CREATE TABLE IF NOT EXISTS casting (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id      UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    character_name TEXT NOT NULL,
    actor_name     TEXT,
    status         TEXT NOT NULL DEFAULT 'wishlist'
                     CHECK (status IN ('wishlist','offer','booked','declined','released')),
    contact_phone  TEXT,
    contact_email  TEXT,
    agent_contact  TEXT,
    headshot_path  TEXT,
    notes          TEXT,
    created_by     UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (script_id, character_name)
);

CREATE INDEX IF NOT EXISTS idx_casting_script ON casting(script_id);

-- ============================================
-- 2. casting_unavailability — 0..n blackout ranges per casting row
-- ============================================
CREATE TABLE IF NOT EXISTS casting_unavailability (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    casting_id UUID NOT NULL REFERENCES casting(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date   DATE NOT NULL,
    reason     TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_casting_unavail_casting
    ON casting_unavailability(casting_id);

-- ============================================
-- 3. updated_at trigger (reuses the fn from migration 030)
-- ============================================
CREATE TRIGGER trg_casting_updated
    BEFORE UPDATE ON casting
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

-- ============================================
-- 4. RLS
-- ============================================
ALTER TABLE casting ENABLE ROW LEVEL SECURITY;
ALTER TABLE casting_unavailability ENABLE ROW LEVEL SECURITY;

CREATE POLICY "casting select for script members"
    ON casting FOR SELECT
    USING (
        script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
        OR script_id IN (SELECT script_id FROM script_members WHERE user_id = auth.uid())
    );

CREATE POLICY "casting write for owner or admin"
    ON casting FOR ALL
    USING (
        script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
        OR script_id IN (
            SELECT script_id FROM script_members
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "casting_unavailability select for script members"
    ON casting_unavailability FOR SELECT
    USING (
        casting_id IN (
            SELECT c.id FROM casting c
            WHERE c.script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
               OR c.script_id IN (SELECT script_id FROM script_members WHERE user_id = auth.uid())
        )
    );

CREATE POLICY "casting_unavailability write for owner or admin"
    ON casting_unavailability FOR ALL
    USING (
        casting_id IN (
            SELECT c.id FROM casting c
            WHERE c.script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
               OR c.script_id IN (
                   SELECT script_id FROM script_members
                   WHERE user_id = auth.uid() AND role = 'admin'
               )
        )
    );
```

- [ ] **Step 2: Verify the `update_shooting_updated_at` function exists to reuse**

Run: `grep -n "update_shooting_updated_at" backend/db/migrations/030_shooting_schedules.sql`
Expected: the `CREATE OR REPLACE FUNCTION update_shooting_updated_at()` definition is present. If for any reason it is missing in the live DB, add a copy of it to `048_casting.sql` above the trigger (same body: `NEW.updated_at = now(); RETURN NEW;`).

- [ ] **Step 3: Apply the migration to Supabase**

Apply `048_casting.sql` via the Supabase SQL editor (or the Supabase MCP `apply_migration`). Confirm with:
```sql
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('casting','casting_unavailability');
```
Expected: both rows returned.

- [ ] **Step 4: Commit**

```bash
git add backend/db/migrations/048_casting.sql
git commit -m "feat(casting): add casting + casting_unavailability tables (migration 048)"
```

---

## Task 2: `casting_service` — persistence, breakdown characters, serializer

**Files:**
- Create: `backend/services/casting_service.py`
- Test: `backend/tests/test_casting_service.py`

**Interfaces:**
- Consumes: `db.client` from `db.supabase_client`.
- Produces:
  - `norm_name(name: str) -> str` — `(name or '').strip().upper()`
  - `breakdown_characters(script_id: str) -> dict[str, int]` — canonical character name → scene count, resolved through `character_aliases`.
  - `list_casting(script_id: str) -> list[dict]` — raw casting rows (no serialization), each with a nested `unavailability: list[dict]`.
  - `get_casting(casting_id: str) -> dict | None`
  - `create_casting(script_id, character_name, user_id) -> dict` — inserts with defaults; raises `CastingConflict` on the unique violation.
  - `update_casting(casting_id, fields: dict) -> dict` — whitelist of updatable columns.
  - `delete_casting(casting_id) -> dict | None` — returns the deleted row (for headshot cleanup by the route).
  - `add_unavailability(casting_id, start_date, end_date, reason) -> dict` — raises `ValueError` if `end_date < start_date`.
  - `delete_unavailability(unavail_id) -> None`
  - `serialize(row: dict, *, include_contact: bool) -> dict` — drops contact fields unless `include_contact`; adds `orphaned: bool` when a `breakdown_names: set[str]` is threaded through (see below); adds `headshot_url` (signed) when `headshot_path` is set.
  - `class CastingConflict(Exception)` , `class CastingNotFound(Exception)`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_casting_service.py
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_casting_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.casting_service'`.

- [ ] **Step 3: Write the implementation**

```python
# backend/services/casting_service.py
"""Cast & Casting (v1) — persistence, breakdown-character aggregation,
serialization, and availability-conflict computation.

See docs/superpowers/specs/2026-08-27-cast-casting-v1-design.md.
"""
from datetime import date, datetime

from db.supabase_client import get_supabase_admin

UPDATABLE_FIELDS = {
    "character_name", "actor_name", "status", "contact_phone",
    "contact_email", "agent_contact", "headshot_path", "notes",
}
CONTACT_FIELDS = ("contact_phone", "contact_email", "agent_contact")
CONFLICT_STATUSES = ("booked", "offer")
VALID_STATUS = {"wishlist", "offer", "booked", "declined", "released"}
HEADSHOT_BUCKET = "scripts"
SIGNED_URL_TTL = 3600  # seconds


class CastingConflict(Exception):
    """A casting row already exists for this (script_id, character_name)."""


class CastingNotFound(Exception):
    """No casting row for the given id."""


def _client():
    return get_supabase_admin()


def norm_name(name):
    return (name or "").strip().upper()


def breakdown_characters(script_id):
    """canonical character name -> scene count, resolved through character_aliases."""
    c = _client()
    aliases = (c.table("character_aliases")
               .select("alias, canonical_name").eq("script_id", script_id).execute())
    alias_map = {norm_name(r["alias"]): norm_name(r["canonical_name"])
                 for r in (aliases.data or [])}
    scenes = (c.table("scenes").select("id, characters")
              .eq("script_id", script_id).execute())
    counts = {}
    for scene in (scenes.data or []):
        seen = set()
        for raw in (scene.get("characters") or []):
            canon = alias_map.get(norm_name(raw), norm_name(raw))
            if not canon or canon in seen:
                continue
            seen.add(canon)
            counts[canon] = counts.get(canon, 0) + 1
    return counts


def list_casting(script_id):
    c = _client()
    rows = (c.table("casting").select("*")
            .eq("script_id", script_id).order("character_name").execute()).data or []
    if not rows:
        return []
    ids = [r["id"] for r in rows]
    unavail = (c.table("casting_unavailability").select("*")
               .in_("casting_id", ids).order("start_date").execute()).data or []
    by_casting = {}
    for u in unavail:
        by_casting.setdefault(u["casting_id"], []).append(u)
    for r in rows:
        r["unavailability"] = by_casting.get(r["id"], [])
    return rows


def get_casting(casting_id):
    c = _client()
    res = (c.table("casting").select("*").eq("id", casting_id).limit(1).execute())
    if not res.data:
        return None
    row = res.data[0]
    unavail = (c.table("casting_unavailability").select("*")
               .eq("casting_id", casting_id).order("start_date").execute()).data or []
    row["unavailability"] = unavail
    return row


def create_casting(script_id, character_name, user_id):
    name = norm_name(character_name)
    if not name:
        raise ValueError("character_name is required")
    c = _client()
    existing = (c.table("casting").select("id")
                .eq("script_id", script_id).eq("character_name", name).limit(1).execute())
    if existing.data:
        raise CastingConflict(name)
    res = (c.table("casting").insert({
        "script_id": script_id, "character_name": name,
        "status": "wishlist", "created_by": user_id,
    }).execute())
    row = res.data[0]
    row["unavailability"] = []
    return row


def update_casting(casting_id, fields):
    payload = {k: v for k, v in fields.items() if k in UPDATABLE_FIELDS}
    if "character_name" in payload:
        payload["character_name"] = norm_name(payload["character_name"])
    if "status" in payload and payload["status"] not in VALID_STATUS:
        raise ValueError(f"invalid status: {payload['status']}")
    if not payload:
        return get_casting(casting_id)
    c = _client()
    res = (c.table("casting").update(payload).eq("id", casting_id).execute())
    if not res.data:
        raise CastingNotFound(casting_id)
    return get_casting(casting_id)


def delete_casting(casting_id):
    c = _client()
    res = (c.table("casting").delete().eq("id", casting_id).execute())
    return res.data[0] if res.data else None


def add_unavailability(casting_id, start_date, end_date, reason):
    s, e = str(start_date), str(end_date)
    if e < s:
        raise ValueError("end_date must be on or after start_date")
    c = _client()
    res = (c.table("casting_unavailability").insert({
        "casting_id": casting_id, "start_date": s, "end_date": e,
        "reason": (reason or None),
    }).execute())
    return res.data[0]


def delete_unavailability(unavail_id):
    _client().table("casting_unavailability").delete().eq("id", unavail_id).execute()


def _headshot_url(path):
    if not path:
        return None
    try:
        signed = (_client().storage.from_(HEADSHOT_BUCKET)
                  .create_signed_url(path, SIGNED_URL_TTL))
        return signed.get("signedURL") or signed.get("signed_url")
    except Exception:
        return None


def serialize(row, *, include_contact, breakdown_names=None):
    out = {
        "id": row["id"],
        "script_id": row["script_id"],
        "character_name": row["character_name"],
        "actor_name": row.get("actor_name"),
        "status": row.get("status") or "wishlist",
        "headshot_path": row.get("headshot_path"),
        "headshot_url": _headshot_url(row.get("headshot_path")),
        "notes": row.get("notes"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "unavailability": row.get("unavailability", []),
    }
    if include_contact:
        for f in CONTACT_FIELDS:
            out[f] = row.get(f)
    if breakdown_names is not None:
        out["orphaned"] = row["character_name"] not in breakdown_names
    return out
```

Note: `.in_(...)` is a `supabase-py` query method; the `FakeTable` in the test does not implement it, so `list_casting` is exercised through the route tests (Task 3) against a fuller fake, not here. Keep the service unit tests limited to what `FakeTable` covers.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_casting_service.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Run the full backend suite for regressions**

Run: `cd backend && python -m pytest -q`
Expected: no new failures vs. baseline.

- [ ] **Step 6: Commit**

```bash
git add backend/services/casting_service.py backend/tests/test_casting_service.py
git commit -m "feat(casting): casting_service — persistence, breakdown chars, serializer"
```

---

## Task 3: `casting_routes` — resolvers, blueprint, CRUD endpoints

**Files:**
- Modify: `backend/middleware/authorization.py` (add resolvers after `from_move_day`, ~line 100)
- Create: `backend/routes/casting_routes.py`
- Modify: `backend/app.py` (import + register, near line 64)
- Test: `backend/tests/test_casting_routes.py`

**Interfaces:**
- Consumes: `casting_service` (Task 2); `require_auth`, `require_script_role`, `from_script`.
- Produces HTTP:
  - `GET  /api/scripts/<script_id>/casting` → `{casting: [serialized...], characters: [{name, scene_count, casting_id|null}...]}`
  - `POST /api/scripts/<script_id>/casting` body `{character_name}` → `201 {casting: serialized}` | `409`
  - `PATCH  /api/casting/<casting_id>` body: any updatable field → `200 {casting: serialized}`
  - `DELETE /api/casting/<casting_id>` → `200 {success: true}`
- Produces resolver: `from_casting(kwargs)`, `from_casting_unavailability(kwargs)` in `middleware/authorization.py`.

- [ ] **Step 1: Add the resolvers**

In `backend/middleware/authorization.py`, immediately after `from_move_day`:

```python
def from_casting(kwargs):
    return _lookup_script_id('casting', kwargs.get('casting_id'))


def from_casting_unavailability(kwargs):
    """Two-hop: casting_unavailability.casting_id -> casting.script_id."""
    casting_id = _lookup_script_id('casting_unavailability', kwargs.get('unavail_id'),
                                   script_col='casting_id')
    if not casting_id:
        return None
    return _lookup_script_id('casting', casting_id)
```

- [ ] **Step 2: Write the failing route tests**

```python
# backend/tests/test_casting_routes.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
import routes.casting_routes as cr
import middleware.authorization as authz


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture(autouse=True)
def _bypass_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(cr, "get_user_id", lambda: "u1")


def _as_role(monkeypatch, role):
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: role)


def test_list_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    assert _client().get("/api/scripts/s1/casting").status_code == 401


def test_list_forbidden_for_non_member(monkeypatch):
    _as_role(monkeypatch, None)
    assert _client().get("/api/scripts/s1/casting").status_code == 403


def test_list_ok_for_viewer(monkeypatch):
    _as_role(monkeypatch, "viewer")
    monkeypatch.setattr(cr.casting_service, "list_casting", lambda sid: [])
    monkeypatch.setattr(cr.casting_service, "breakdown_characters", lambda sid: {"JOHN": 3})
    resp = _client().get("/api/scripts/s1/casting")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["characters"] == [{"name": "JOHN", "scene_count": 3, "casting_id": None}]
    assert body["casting"] == []


def test_list_omits_contact_for_viewer(monkeypatch):
    _as_role(monkeypatch, "viewer")
    monkeypatch.setattr(cr.casting_service, "list_casting", lambda sid: [
        {"id": "c1", "script_id": "s1", "character_name": "JOHN",
         "actor_name": "Jon", "status": "booked", "contact_phone": "0821",
         "headshot_path": None, "notes": None, "unavailability": []},
    ])
    monkeypatch.setattr(cr.casting_service, "breakdown_characters", lambda sid: {"JOHN": 3})
    monkeypatch.setattr(cr.casting_service, "_headshot_url", lambda p: None)
    body = _client().get("/api/scripts/s1/casting").get_json()
    assert "contact_phone" not in body["casting"][0]


def test_list_includes_contact_for_admin(monkeypatch):
    _as_role(monkeypatch, "admin")
    monkeypatch.setattr(cr.casting_service, "list_casting", lambda sid: [
        {"id": "c1", "script_id": "s1", "character_name": "JOHN",
         "actor_name": "Jon", "status": "booked", "contact_phone": "0821",
         "headshot_path": None, "notes": None, "unavailability": []},
    ])
    monkeypatch.setattr(cr.casting_service, "breakdown_characters", lambda sid: {"JOHN": 3})
    monkeypatch.setattr(cr.casting_service, "_headshot_url", lambda p: None)
    body = _client().get("/api/scripts/s1/casting").get_json()
    assert body["casting"][0]["contact_phone"] == "0821"


def test_create_forbidden_for_member(monkeypatch):
    _as_role(monkeypatch, "member")
    resp = _client().post("/api/scripts/s1/casting", json={"character_name": "JOHN"})
    assert resp.status_code == 403


def test_create_ok_for_admin(monkeypatch):
    _as_role(monkeypatch, "admin")
    monkeypatch.setattr(cr.casting_service, "create_casting",
                        lambda sid, name, uid: {"id": "c1", "script_id": sid,
                        "character_name": "JOHN", "status": "wishlist",
                        "actor_name": None, "headshot_path": None, "notes": None,
                        "unavailability": []})
    monkeypatch.setattr(cr.casting_service, "_headshot_url", lambda p: None)
    resp = _client().post("/api/scripts/s1/casting", json={"character_name": "john"})
    assert resp.status_code == 201
    assert resp.get_json()["casting"]["character_name"] == "JOHN"


def test_create_conflict_returns_409(monkeypatch):
    _as_role(monkeypatch, "admin")
    def _boom(sid, name, uid): raise cr.casting_service.CastingConflict(name)
    monkeypatch.setattr(cr.casting_service, "create_casting", _boom)
    resp = _client().post("/api/scripts/s1/casting", json={"character_name": "JOHN"})
    assert resp.status_code == 409


def test_patch_ok_for_admin(monkeypatch):
    _as_role(monkeypatch, "admin")
    monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")
    monkeypatch.setattr(cr.casting_service, "update_casting",
                        lambda cid, fields: {"id": cid, "script_id": "s1",
                        "character_name": "JOHN", "status": fields.get("status", "wishlist"),
                        "actor_name": fields.get("actor_name"), "headshot_path": None,
                        "notes": None, "unavailability": []})
    monkeypatch.setattr(cr.casting_service, "_headshot_url", lambda p: None)
    resp = _client().patch("/api/casting/c1", json={"status": "booked"})
    assert resp.status_code == 200
    assert resp.get_json()["casting"]["status"] == "booked"


def test_delete_ok_for_admin(monkeypatch):
    _as_role(monkeypatch, "admin")
    monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")
    monkeypatch.setattr(cr.casting_service, "delete_casting", lambda cid: {"id": cid, "headshot_path": None})
    resp = _client().delete("/api/casting/c1")
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_casting_routes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'routes.casting_routes'`.

- [ ] **Step 4: Write the blueprint**

```python
# backend/routes/casting_routes.py
"""Cast & Casting (v1) HTTP endpoints. See
docs/superpowers/specs/2026-08-27-cast-casting-v1-design.md §5."""
from flask import Blueprint, request, jsonify, g

from middleware.auth import require_auth, get_user_id
from middleware.authorization import (
    require_script_role, from_script, from_casting, from_casting_unavailability,
)
import services.casting_service as casting_service

casting_bp = Blueprint("casting", __name__)


def _include_contact():
    return getattr(g, "script_role", None) in ("admin", "owner")


def _serialize_one(row):
    return casting_service.serialize(row, include_contact=_include_contact())


@casting_bp.route("/api/scripts/<script_id>/casting", methods=["GET"])
@require_auth
@require_script_role("viewer", resolver=from_script)
def list_casting(script_id):
    rows = casting_service.list_casting(script_id)
    counts = casting_service.breakdown_characters(script_id)
    names = set(counts) | {r["character_name"] for r in rows}
    inc = _include_contact()
    serialized = [
        casting_service.serialize(r, include_contact=inc, breakdown_names=set(counts))
        for r in rows
    ]
    casting_by_name = {r["character_name"]: r["id"] for r in rows}
    characters = [
        {"name": n, "scene_count": counts[n], "casting_id": casting_by_name.get(n)}
        for n in sorted(counts, key=lambda k: (-counts[k], k))
    ]
    return jsonify({"casting": serialized, "characters": characters}), 200


@casting_bp.route("/api/scripts/<script_id>/casting", methods=["POST"])
@require_auth
@require_script_role("admin", resolver=from_script)
def create_casting(script_id):
    data = request.get_json(silent=True) or {}
    try:
        row = casting_service.create_casting(script_id, data.get("character_name"), get_user_id())
    except casting_service.CastingConflict:
        return jsonify({"error": "Casting already exists for this character"}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"casting": _serialize_one(row)}), 201


@casting_bp.route("/api/casting/<casting_id>", methods=["PATCH"])
@require_auth
@require_script_role("admin", resolver=from_casting)
def update_casting(casting_id):
    data = request.get_json(silent=True) or {}
    try:
        row = casting_service.update_casting(casting_id, data)
    except casting_service.CastingNotFound:
        return jsonify({"error": "Not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"casting": _serialize_one(row)}), 200


@casting_bp.route("/api/casting/<casting_id>", methods=["DELETE"])
@require_auth
@require_script_role("admin", resolver=from_casting)
def delete_casting(casting_id):
    deleted = casting_service.delete_casting(casting_id)
    if deleted and deleted.get("headshot_path"):
        try:
            casting_service._client().storage.from_(
                casting_service.HEADSHOT_BUCKET
            ).remove([deleted["headshot_path"]])
        except Exception:
            pass
    return jsonify({"success": True}), 200
```

- [ ] **Step 5: Register the blueprint**

In `backend/app.py`, after the `series_bp` registration (~line 64):
```python
from routes.casting_routes import casting_bp
```
(with the other route imports at the top), and:
```python
app.register_blueprint(casting_bp)  # Cast & casting routes at /api/scripts/:id/casting, /api/casting/*
```

- [ ] **Step 6: Run the route tests**

Run: `cd backend && python -m pytest tests/test_casting_routes.py -v`
Expected: PASS (12 tests).

- [ ] **Step 7: Run the full suite + boot check**

Run: `cd backend && python -m pytest -q && python -c "import app"`
Expected: no new failures; `import app` exits 0.

- [ ] **Step 8: Commit**

```bash
git add backend/middleware/authorization.py backend/routes/casting_routes.py backend/app.py backend/tests/test_casting_routes.py
git commit -m "feat(casting): CRUD endpoints + from_casting resolvers + blueprint"
```

---

## Task 4: Unavailability endpoints

**Files:**
- Modify: `backend/routes/casting_routes.py`
- Test: `backend/tests/test_casting_routes.py` (append)

**Interfaces:**
- Consumes: `casting_service.add_unavailability`, `casting_service.delete_unavailability`; `from_casting`, `from_casting_unavailability`.
- Produces HTTP:
  - `POST   /api/casting/<casting_id>/unavailability` body `{start_date, end_date, reason?}` → `201 {unavailability: row}` | `400`
  - `DELETE /api/casting/unavailability/<unavail_id>` → `200 {success: true}`

- [ ] **Step 1: Append failing tests**

```python
# append to backend/tests/test_casting_routes.py

def test_add_unavailability_forbidden_for_viewer(monkeypatch):
    _as_role(monkeypatch, "viewer")
    monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")
    resp = _client().post("/api/casting/c1/unavailability",
                          json={"start_date": "2026-03-01", "end_date": "2026-03-05"})
    assert resp.status_code == 403


def test_add_unavailability_ok_for_admin(monkeypatch):
    _as_role(monkeypatch, "admin")
    monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")
    monkeypatch.setattr(cr.casting_service, "add_unavailability",
                        lambda cid, s, e, r: {"id": "u1", "casting_id": cid,
                        "start_date": s, "end_date": e, "reason": r})
    resp = _client().post("/api/casting/c1/unavailability",
                          json={"start_date": "2026-03-01", "end_date": "2026-03-05",
                                "reason": "Other shoot"})
    assert resp.status_code == 201
    assert resp.get_json()["unavailability"]["reason"] == "Other shoot"


def test_add_unavailability_bad_range_returns_400(monkeypatch):
    _as_role(monkeypatch, "admin")
    monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")
    def _boom(cid, s, e, r): raise ValueError("end_date must be on or after start_date")
    monkeypatch.setattr(cr.casting_service, "add_unavailability", _boom)
    resp = _client().post("/api/casting/c1/unavailability",
                          json={"start_date": "2026-03-10", "end_date": "2026-03-01"})
    assert resp.status_code == 400


def test_add_unavailability_missing_dates_returns_400(monkeypatch):
    _as_role(monkeypatch, "admin")
    monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")
    resp = _client().post("/api/casting/c1/unavailability", json={"reason": "x"})
    assert resp.status_code == 400


def test_delete_unavailability_ok_for_admin(monkeypatch):
    _as_role(monkeypatch, "admin")
    monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")
    monkeypatch.setattr(cr.casting_service, "delete_unavailability", lambda uid: None)
    resp = _client().delete("/api/casting/unavailability/u1")
    assert resp.status_code == 200
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_casting_routes.py -k unavailability -v`
Expected: FAIL — 404s (routes not defined).

- [ ] **Step 3: Add the endpoints**

Append to `backend/routes/casting_routes.py`:

```python
@casting_bp.route("/api/casting/<casting_id>/unavailability", methods=["POST"])
@require_auth
@require_script_role("admin", resolver=from_casting)
def add_unavailability(casting_id):
    data = request.get_json(silent=True) or {}
    start, end = data.get("start_date"), data.get("end_date")
    if not start or not end:
        return jsonify({"error": "start_date and end_date are required"}), 400
    try:
        row = casting_service.add_unavailability(casting_id, start, end, data.get("reason"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"unavailability": row}), 201


@casting_bp.route("/api/casting/unavailability/<unavail_id>", methods=["DELETE"])
@require_auth
@require_script_role("admin", resolver=from_casting_unavailability)
def delete_unavailability(unavail_id):
    casting_service.delete_unavailability(unavail_id)
    return jsonify({"success": True}), 200
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_casting_routes.py -v`
Expected: PASS (all, ~17 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/routes/casting_routes.py backend/tests/test_casting_routes.py
git commit -m "feat(casting): unavailability add/remove endpoints"
```

---

## Task 5: Headshot upload endpoint

**Files:**
- Modify: `backend/routes/casting_routes.py`
- Modify: `backend/services/casting_service.py` (add `store_headshot`)
- Test: `backend/tests/test_casting_routes.py` (append)

**Interfaces:**
- Consumes: `casting_service.get_casting`, `casting_service.update_casting`.
- Produces:
  - `casting_service.store_headshot(casting_id, script_id, file_bytes, content_type) -> str` — uploads to `scripts` bucket at `casting/<script_id>/<casting_id>.<ext>`, returns the path. Raises `ValueError` for unsupported type.
  - HTTP `POST /api/casting/<casting_id>/headshot` (multipart, field `file`) → `200 {casting: serialized}` | `400` (type) | `413` (size).

- [ ] **Step 1: Append failing tests**

```python
# append to backend/tests/test_casting_routes.py
import io

def test_headshot_rejects_wrong_type(monkeypatch):
    _as_role(monkeypatch, "admin")
    monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")
    data = {"file": (io.BytesIO(b"GIF89a"), "x.gif", "image/gif")}
    resp = _client().post("/api/casting/c1/headshot", data=data,
                          content_type="multipart/form-data")
    assert resp.status_code == 400


def test_headshot_rejects_oversize(monkeypatch):
    _as_role(monkeypatch, "admin")
    monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")
    big = io.BytesIO(b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024 + 10))
    data = {"file": (big, "x.jpg", "image/jpeg")}
    resp = _client().post("/api/casting/c1/headshot", data=data,
                          content_type="multipart/form-data")
    assert resp.status_code == 413


def test_headshot_ok(monkeypatch):
    _as_role(monkeypatch, "admin")
    monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")
    monkeypatch.setattr(cr.casting_service, "get_casting",
                        lambda cid: {"id": cid, "script_id": "s1", "character_name": "JOHN"})
    monkeypatch.setattr(cr.casting_service, "store_headshot",
                        lambda cid, sid, b, ct: "casting/s1/c1.jpg")
    monkeypatch.setattr(cr.casting_service, "update_casting",
                        lambda cid, fields: {"id": cid, "script_id": "s1",
                        "character_name": "JOHN", "status": "wishlist", "actor_name": None,
                        "headshot_path": fields["headshot_path"], "notes": None,
                        "unavailability": []})
    monkeypatch.setattr(cr.casting_service, "_headshot_url", lambda p: "https://signed/x.jpg")
    data = {"file": (io.BytesIO(b"\xff\xd8\xffdata"), "x.jpg", "image/jpeg")}
    resp = _client().post("/api/casting/c1/headshot", data=data,
                          content_type="multipart/form-data")
    assert resp.status_code == 200
    assert resp.get_json()["casting"]["headshot_url"] == "https://signed/x.jpg"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_casting_routes.py -k headshot -v`
Expected: FAIL (route 404).

- [ ] **Step 3: Add `store_headshot` to the service**

Append to `backend/services/casting_service.py`:

```python
_HEADSHOT_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_HEADSHOT_BYTES = 5 * 1024 * 1024


def store_headshot(casting_id, script_id, file_bytes, content_type):
    ext = _HEADSHOT_TYPES.get(content_type)
    if not ext:
        raise ValueError("Use a JPG, PNG, or WebP image.")
    path = f"casting/{script_id}/{casting_id}.{ext}"
    _client().storage.from_(HEADSHOT_BUCKET).upload(
        path, file_bytes,
        {"content-type": content_type, "upsert": "true"},
    )
    return path
```

- [ ] **Step 4: Add the endpoint**

Append to `backend/routes/casting_routes.py`:

```python
@casting_bp.route("/api/casting/<casting_id>/headshot", methods=["POST"])
@require_auth
@require_script_role("admin", resolver=from_casting)
def upload_headshot(casting_id):
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400
    blob = file.read()
    if len(blob) > casting_service.MAX_HEADSHOT_BYTES:
        return jsonify({"error": "That image is over 5 MB. Use a smaller file."}), 413
    row = casting_service.get_casting(casting_id)
    if not row:
        return jsonify({"error": "Not found"}), 404
    try:
        path = casting_service.store_headshot(
            casting_id, row["script_id"], blob, file.mimetype
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    updated = casting_service.update_casting(casting_id, {"headshot_path": path})
    return jsonify({"casting": _serialize_one(updated)}), 200
```

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_casting_routes.py -v`
Expected: PASS (all, ~20 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/routes/casting_routes.py backend/services/casting_service.py backend/tests/test_casting_routes.py
git commit -m "feat(casting): headshot upload endpoint with type/size validation"
```

---

## Task 6: Conflict computation + endpoint

**Files:**
- Modify: `backend/services/casting_service.py` (add `compute_conflicts`, `active_schedule_id`)
- Modify: `backend/routes/casting_routes.py` (add conflicts endpoint)
- Test: `backend/tests/test_casting_conflicts.py`

**Interfaces:**
- Consumes: `db.client` tables `shooting_schedules`, `shooting_days`, `shooting_day_scenes`, `scenes`, `character_aliases`, `casting`, `casting_unavailability`.
- Produces:
  - `casting_service.active_schedule_id(script_id) -> str | None` — the `status='active'` schedule for the script; the most recently `updated_at` one if several; else `None`.
  - `casting_service.compute_conflicts(script_id, schedule_id) -> list[dict]` — each: `{shooting_day_id, day_number, shoot_date, character_name, actor_name, reason}`.
  - HTTP `GET /api/scripts/<script_id>/casting/conflicts?schedule_id=<id>` → `200 {conflicts: [...], schedule_id}` | `400` (missing schedule_id) | `404` (schedule not on this script). If `schedule_id` omitted, falls back to `active_schedule_id`; if that is also `None` → `200 {conflicts: [], schedule_id: null}`.

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_casting_conflicts.py -v`
Expected: FAIL — `AttributeError: module 'services.casting_service' has no attribute 'compute_conflicts'`.

- [ ] **Step 3: Implement**

Append to `backend/services/casting_service.py`:

```python
def active_schedule_id(script_id):
    rows = (_client().table("shooting_schedules").select("id, status, updated_at")
            .eq("script_id", script_id).eq("status", "active")
            .order("updated_at", desc=True).execute()).data or []
    return rows[0]["id"] if rows else None


def _alias_map(script_id):
    rows = (_client().table("character_aliases").select("alias, canonical_name")
            .eq("script_id", script_id).execute()).data or []
    return {norm_name(r["alias"]): norm_name(r["canonical_name"]) for r in rows}


def compute_conflicts(script_id, schedule_id):
    c = _client()
    days = [d for d in (c.table("shooting_days").select("id, day_number, shoot_date")
            .eq("schedule_id", schedule_id).order("day_number").execute()).data or []
            if d.get("shoot_date")]
    if not days:
        return []
    day_ids = [d["id"] for d in days]
    dps = (c.table("shooting_day_scenes").select("shooting_day_id, scene_id")
           .in_("shooting_day_id", day_ids).execute()).data or []
    scene_ids = list({p["scene_id"] for p in dps})
    if not scene_ids:
        return []
    scenes = (c.table("scenes").select("id, characters")
              .in_("id", scene_ids).execute()).data or []
    amap = _alias_map(script_id)
    scene_chars = {
        s["id"]: {amap.get(norm_name(x), norm_name(x)) for x in (s.get("characters") or [])}
        for s in scenes
    }
    # day -> set of canonical character names
    day_chars = {}
    for p in dps:
        day_chars.setdefault(p["shooting_day_id"], set()).update(
            scene_chars.get(p["scene_id"], set())
        )

    casting_rows = [r for r in (c.table("casting")
                    .select("id, character_name, actor_name, status")
                    .eq("script_id", script_id).execute()).data or []
                    if r.get("status") in CONFLICT_STATUSES]
    if not casting_rows:
        return []
    casting_by_name = {r["character_name"]: r for r in casting_rows}
    unavail = (c.table("casting_unavailability")
               .select("casting_id, start_date, end_date, reason")
               .in_("casting_id", [r["id"] for r in casting_rows]).execute()).data or []
    ranges_by_casting = {}
    for u in unavail:
        ranges_by_casting.setdefault(u["casting_id"], []).append(u)

    out = []
    for d in days:
        sd = str(d["shoot_date"])
        for cname in day_chars.get(d["id"], set()):
            row = casting_by_name.get(cname)
            if not row:
                continue
            for rng in ranges_by_casting.get(row["id"], []):
                if str(rng["start_date"]) <= sd <= str(rng["end_date"]):
                    out.append({
                        "shooting_day_id": d["id"],
                        "day_number": d["day_number"],
                        "shoot_date": sd,
                        "character_name": cname,
                        "actor_name": row.get("actor_name"),
                        "reason": rng.get("reason"),
                    })
                    break
    return out
```

- [ ] **Step 4: Add the endpoint**

Append to `backend/routes/casting_routes.py`:

```python
@casting_bp.route("/api/scripts/<script_id>/casting/conflicts", methods=["GET"])
@require_auth
@require_script_role("viewer", resolver=from_script)
def casting_conflicts(script_id):
    schedule_id = request.args.get("schedule_id") or casting_service.active_schedule_id(script_id)
    if not schedule_id:
        return jsonify({"conflicts": [], "schedule_id": None}), 200
    owner = casting_service._client().table("shooting_schedules").select("script_id") \
        .eq("id", schedule_id).limit(1).execute()
    if not owner.data or owner.data[0]["script_id"] != script_id:
        return jsonify({"error": "Schedule not found for this script"}), 404
    conflicts = casting_service.compute_conflicts(script_id, schedule_id)
    return jsonify({"conflicts": conflicts, "schedule_id": schedule_id}), 200
```

- [ ] **Step 5: Add a route test**

```python
# append to backend/tests/test_casting_routes.py

def test_conflicts_no_active_schedule_returns_empty(monkeypatch):
    _as_role(monkeypatch, "viewer")
    monkeypatch.setattr(cr.casting_service, "active_schedule_id", lambda sid: None)
    resp = _client().get("/api/scripts/s1/casting/conflicts")
    assert resp.status_code == 200
    assert resp.get_json() == {"conflicts": [], "schedule_id": None}
```

- [ ] **Step 6: Run all casting tests + full suite**

Run: `cd backend && python -m pytest tests/test_casting_conflicts.py tests/test_casting_routes.py -v && python -m pytest -q`
Expected: PASS; no new failures.

- [ ] **Step 7: Commit**

```bash
git add backend/services/casting_service.py backend/routes/casting_routes.py backend/tests/test_casting_conflicts.py backend/tests/test_casting_routes.py
git commit -m "feat(casting): availability-conflict computation + conflicts endpoint"
```

---

## Task 7: Merge hook — carry casting rows to the new canonical name

**Files:**
- Modify: `backend/routes/supabase_routes.py` — `merge_characters` (after the `character_aliases` upsert loop, ~line 4805, before `return jsonify(...)`)
- Test: `backend/tests/test_casting_merge_hook.py`

**Interfaces:**
- Consumes: `supabase` client already in scope in `merge_characters`; the local vars `canonical_name` (uppercased), `aliases` (list of uppercased strings), `script_id`.
- Produces: after a merge, every `casting` row for the script whose `character_name` is in `aliases` is renamed to `canonical_name`; if a row already exists for `canonical_name`, the alias row is deleted instead.

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_casting_merge_hook.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import routes.supabase_routes as sr


class Tbl:
    def __init__(self, store, name):
        self.store, self.name, self._f, self._op, self._payload = store, name, [], None, None
    def select(self, *a, **k): self._op = "select"; return self
    def update(self, p): self._op, self._payload = "update", p; return self
    def delete(self): self._op = "delete"; return self
    def insert(self, p): self._op, self._payload = "insert", p; return self
    def upsert(self, p, **k): self._op, self._payload = "insert", p; return self
    def eq(self, c, v): self._f.append((c, v)); return self
    def execute(self):
        rows = self.store.setdefault(self.name, [])
        m = lambda r: all(r.get(c) == v for c, v in self._f)
        if self._op == "select":
            return type("R", (), {"data": [r for r in rows if m(r)]})
        if self._op == "update":
            hit = [r for r in rows if m(r)]
            for r in hit: r.update(self._payload)
            return type("R", (), {"data": hit})
        if self._op == "delete":
            self.store[self.name] = [r for r in rows if not m(r)]
            return type("R", (), {"data": []})
        if self._op == "insert":
            rows.append(self._payload)
            return type("R", (), {"data": [self._payload]})


class Client:
    def __init__(self, store): self.store = store
    def table(self, name): return Tbl(self.store, name)


def _run_merge(monkeypatch, store, canonical, aliases):
    monkeypatch.setattr(sr, "supabase", Client(store))
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    from flask import Flask
    app = Flask(__name__)
    with app.test_request_context(json={"canonical_name": canonical, "aliases": aliases}):
        sr.merge_characters.__wrapped__("s1") if hasattr(sr.merge_characters, "__wrapped__") \
            else sr.merge_characters("s1")


def test_merge_renames_casting_row(monkeypatch):
    store = {
        "scenes": [{"id": "sc1", "script_id": "s1", "characters": ["JON"]}],
        "character_aliases": [],
        "casting": [{"id": "c1", "script_id": "s1", "character_name": "JON"}],
    }
    _run_merge(monkeypatch, store, "JOHN", ["JON"])
    assert store["casting"][0]["character_name"] == "JOHN"


def test_merge_collision_deletes_alias_casting_row(monkeypatch):
    store = {
        "scenes": [{"id": "sc1", "script_id": "s1", "characters": ["JON", "JOHN"]}],
        "character_aliases": [],
        "casting": [
            {"id": "c1", "script_id": "s1", "character_name": "JOHN"},
            {"id": "c2", "script_id": "s1", "character_name": "JON"},
        ],
    }
    _run_merge(monkeypatch, store, "JOHN", ["JON"])
    names = sorted(r["character_name"] for r in store["casting"])
    assert names == ["JOHN"]
```

Note: `merge_characters` is decorated with `@require_auth`. The helper calls the undecorated function via `__wrapped__` when available. If `@require_auth` does not set `__wrapped__`, add `from functools import wraps` usage is already present — verify `require_auth` uses `@wraps`; if not, the test calls `merge_characters("s1")` directly and relies on `DEV_MODE`. Set `monkeypatch.setattr("middleware.auth.DEV_MODE", True)` in `_run_merge` to be safe.

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_casting_merge_hook.py -v`
Expected: FAIL — casting row not renamed.

- [ ] **Step 3: Add the hook**

In `backend/routes/supabase_routes.py`, in `merge_characters`, after the
`for alias in aliases:` loop that upserts into `character_aliases` and
before `return jsonify({...'success': True...})`:

```python
        # 5. Carry any casting rows from an alias name to the canonical name.
        #    See docs/superpowers/specs/2026-08-27-cast-casting-v1-design.md §5.6.
        try:
            existing_canon = supabase.table('casting').select('id') \
                .eq('script_id', script_id).eq('character_name', canonical_name) \
                .execute()
            canon_taken = bool(existing_canon.data)
            for alias in aliases:
                alias_rows = supabase.table('casting').select('id') \
                    .eq('script_id', script_id).eq('character_name', alias).execute()
                if not alias_rows.data:
                    continue
                if canon_taken:
                    supabase.table('casting').delete() \
                        .eq('script_id', script_id).eq('character_name', alias).execute()
                else:
                    supabase.table('casting').update({'character_name': canonical_name}) \
                        .eq('script_id', script_id).eq('character_name', alias).execute()
                    canon_taken = True
        except Exception as casting_err:
            print(f"Warning: casting merge-carry failed: {casting_err}")
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_casting_merge_hook.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Full suite (merge_characters has existing tests)**

Run: `cd backend && python -m pytest -q`
Expected: no new failures; existing `test_character_merge_case.py` still green.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/supabase_routes.py backend/tests/test_casting_merge_hook.py
git commit -m "feat(casting): carry casting rows through character merge"
```

---

## Task 8: `apiService` — the 8 casting calls

**Files:**
- Modify: `frontend/src/services/apiService.js`

**Interfaces:**
- Consumes: the `api` axios instance already exported in the file.
- Produces (all return `response.data`):
  - `getCasting(scriptId)` → `{casting, characters}`
  - `createCasting(scriptId, characterName)` → `{casting}`
  - `updateCasting(castingId, fields)` → `{casting}`
  - `deleteCasting(castingId)` → `{success}`
  - `addUnavailability(castingId, {start_date, end_date, reason})` → `{unavailability}`
  - `removeUnavailability(unavailId)` → `{success}`
  - `uploadHeadshot(castingId, file)` → `{casting}`
  - `getCastingConflicts(scriptId, scheduleId?)` → `{conflicts, schedule_id}`

- [ ] **Step 1: Add the functions**

Append near the other resource groups in `frontend/src/services/apiService.js`
(follow the existing `export const` style; `uploadScript` at line ~116 is
the `FormData` reference):

```javascript
// ── Cast & casting ─────────────────────────────────────────────
export const getCasting = async (scriptId) => {
    const response = await api.get(`/api/scripts/${scriptId}/casting`);
    return response.data;
};

export const createCasting = async (scriptId, characterName) => {
    const response = await api.post(`/api/scripts/${scriptId}/casting`, {
        character_name: characterName,
    });
    return response.data;
};

export const updateCasting = async (castingId, fields) => {
    const response = await api.patch(`/api/casting/${castingId}`, fields);
    return response.data;
};

export const deleteCasting = async (castingId) => {
    const response = await api.delete(`/api/casting/${castingId}`);
    return response.data;
};

export const addUnavailability = async (castingId, range) => {
    const response = await api.post(`/api/casting/${castingId}/unavailability`, range);
    return response.data;
};

export const removeUnavailability = async (unavailId) => {
    const response = await api.delete(`/api/casting/unavailability/${unavailId}`);
    return response.data;
};

export const uploadHeadshot = async (castingId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post(`/api/casting/${castingId}/headshot`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

export const getCastingConflicts = async (scriptId, scheduleId) => {
    const params = scheduleId ? { schedule_id: scheduleId } : {};
    const response = await api.get(`/api/scripts/${scriptId}/casting/conflicts`, { params });
    return response.data;
};
```

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/apiService.js
git commit -m "feat(casting): apiService methods for casting endpoints"
```

---

## Task 9: Nav tab, route, and `CastPage` shell with states

**Files:**
- Modify: `frontend/src/components/layout/SectionNav.jsx`
- Modify: `frontend/src/App.jsx`
- Create: `frontend/src/components/cast/CastPage.jsx`, `frontend/src/components/cast/CastPage.css`

**Interfaces:**
- Consumes: `getCasting`, `getCastingConflicts` (Task 8); `SkeletonList`, `EmptyState`, `Spinner` from `components/ui`.
- Produces: default-exported `CastPage` component rendering at `scripts/:scriptId/cast`; a merged character list model `{ name, scene_count, casting, conflicts }[]` passed to `CastRow` (Task 10).

- [ ] **Step 1: Add the nav tab**

In `frontend/src/components/layout/SectionNav.jsx`:
- Import: add `Contact` to the `lucide-react` import (fall back to `Users` if `Contact` is not exported by the installed version — check `node_modules/lucide-react/dist/lucide-react.d.ts`).
- In `SECTIONS`, insert after the `scenes` entry:
  ```javascript
  { key: 'cast', label: 'Cast', icon: Contact, to: (id) => `/scripts/${id}/cast` },
  ```
- Extend the `activeKey` regex:
  ```javascript
  const m = pathname.match(/^\/scripts\/[^/]+\/(stripboard|board|reports|schedule|cast)/);
  ```

- [ ] **Step 2: Add the route**

In `frontend/src/App.jsx`: import `CastPage` alongside the other component
imports, and add inside the protected `<Route>` group (near the
`scripts/:scriptId/schedule` line):
```jsx
<Route path="scripts/:scriptId/cast" element={<CastPage />} />
```

- [ ] **Step 3: Write `CastPage.jsx`**

```jsx
// frontend/src/components/cast/CastPage.jsx
import { useEffect, useMemo, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Users } from 'lucide-react';
import { getCasting, getCastingConflicts } from '../../services/apiService';
import { SkeletonList, EmptyState } from '../ui';
import CastRow from './CastRow';
import CastingDetailPanel from './CastingDetailPanel';
import './CastPage.css';

const STATUS_FILTERS = ['all', 'wishlist', 'offer', 'booked', 'declined', 'released', 'uncast'];

export default function CastPage() {
    const { scriptId } = useParams();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [casting, setCasting] = useState([]);
    const [characters, setCharacters] = useState([]);
    const [conflicts, setConflicts] = useState([]);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [openId, setOpenId] = useState(null); // casting id OR `new:<CHARACTER>`

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getCasting(scriptId);
            setCasting(data.casting || []);
            setCharacters(data.characters || []);
            try {
                const conf = await getCastingConflicts(scriptId);
                setConflicts(conf.conflicts || []);
            } catch {
                setConflicts([]);
            }
        } catch (e) {
            setError('Couldn’t load casting. Check your connection and try again.');
        } finally {
            setLoading(false);
        }
    }, [scriptId]);

    useEffect(() => { load(); }, [load]);

    const castingByName = useMemo(
        () => Object.fromEntries(casting.map((c) => [c.character_name, c])),
        [casting],
    );
    const conflictsByName = useMemo(() => {
        const m = {};
        for (const c of conflicts) (m[c.character_name] ||= []).push(c);
        return m;
    }, [conflicts]);

    // Breakdown characters + orphaned casting rows (no matching breakdown char).
    const rows = useMemo(() => {
        const breakdownNames = new Set(characters.map((c) => c.name));
        const base = characters.map((c) => ({
            name: c.name,
            scene_count: c.scene_count,
            casting: castingByName[c.name] || null,
            conflicts: conflictsByName[c.name] || [],
            orphaned: false,
        }));
        const orphans = casting
            .filter((c) => !breakdownNames.has(c.character_name))
            .map((c) => ({
                name: c.character_name,
                scene_count: null,
                casting: c,
                conflicts: conflictsByName[c.character_name] || [],
                orphaned: true,
            }));
        return { base, orphans };
    }, [characters, casting, castingByName, conflictsByName]);

    const applyFilters = (list) => list.filter((r) => {
        const q = search.trim().toLowerCase();
        if (q && !r.name.toLowerCase().includes(q)
            && !(r.casting?.actor_name || '').toLowerCase().includes(q)) return false;
        if (statusFilter === 'all') return true;
        if (statusFilter === 'uncast') return !r.casting;
        return r.casting?.status === statusFilter;
    });

    const visibleBase = applyFilters(rows.base);
    const visibleOrphans = applyFilters(rows.orphans);

    const bookedCount = casting.filter((c) => c.status === 'booked').length;
    const conflictCharCount = new Set(conflicts.map((c) => c.character_name)).size;

    const openRow = (row) => setOpenId(row.casting ? row.casting.id : `new:${row.name}`);

    if (loading) {
        return (
            <div className="cast-page">
                <div className="cast-page-head"><h1>Cast</h1></div>
                <SkeletonList count={6} />
            </div>
        );
    }

    if (error) {
        return (
            <div className="cast-page">
                <div className="cast-page-head"><h1>Cast</h1></div>
                <div className="cast-error">
                    {error} <button onClick={load}>Retry</button>
                </div>
            </div>
        );
    }

    if (characters.length === 0 && casting.length === 0) {
        return (
            <div className="cast-page">
                <div className="cast-page-head"><h1>Cast</h1></div>
                <EmptyState
                    icon={Users}
                    title="No characters yet"
                    description="Run the breakdown on your scenes to detect characters — then cast them here."
                    action={{ label: 'Go to Scenes', onClick: () => navigate(`/scenes/${scriptId}`) }}
                />
            </div>
        );
    }

    return (
        <div className="cast-page">
            <div className="cast-page-head">
                <h1>Cast</h1>
                <p className="cast-summary">
                    {characters.length} characters &middot; {bookedCount} booked
                    {conflictCharCount > 0 && (
                        <span className="cast-summary-conflict">
                            {' '}&middot; {conflictCharCount} availability conflicts
                        </span>
                    )}
                </p>
            </div>

            <div className="cast-filterbar">
                <input
                    className="cast-search"
                    type="search"
                    placeholder="Search characters…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
                <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                    {STATUS_FILTERS.map((s) => (
                        <option key={s} value={s}>
                            {s === 'all' ? 'All statuses'
                                : s === 'uncast' ? 'Not cast'
                                : s[0].toUpperCase() + s.slice(1)}
                        </option>
                    ))}
                </select>
            </div>

            {visibleBase.length === 0 && visibleOrphans.length === 0 ? (
                <div className="cast-nomatch">
                    No characters match. <button onClick={() => { setSearch(''); setStatusFilter('all'); }}>Clear filters</button>
                </div>
            ) : (
                <div className="cast-list">
                    {visibleBase.map((row) => (
                        <CastRow key={row.name} row={row} onOpen={() => openRow(row)} />
                    ))}
                    {visibleOrphans.length > 0 && (
                        <>
                            <div className="cast-divider">Not in current breakdown</div>
                            {visibleOrphans.map((row) => (
                                <CastRow key={`orphan:${row.name}`} row={row} onOpen={() => openRow(row)} />
                            ))}
                        </>
                    )}
                </div>
            )}

            {openId && (
                <CastingDetailPanel
                    scriptId={scriptId}
                    openId={openId}
                    casting={openId.startsWith('new:') ? null
                        : casting.find((c) => c.id === openId) || null}
                    characterName={openId.startsWith('new:') ? openId.slice(4)
                        : (casting.find((c) => c.id === openId)?.character_name)}
                    conflicts={conflicts}
                    onClose={() => setOpenId(null)}
                    onChanged={load}
                />
            )}
        </div>
    );
}
```

- [ ] **Step 4: Write `CastPage.css`**

```css
/* frontend/src/components/cast/CastPage.css */
.cast-page { max-width: var(--container-max); margin: 0 auto; padding: var(--space-8) var(--edge-padding); }
.cast-page-head h1 { font-size: var(--text-2xl); color: var(--text-primary); margin: 0; }
.cast-summary { font-size: var(--text-sm); color: var(--text-secondary); margin: var(--space-2) 0 0; }
.cast-summary-conflict { color: var(--danger); }
.cast-filterbar {
    position: sticky; top: var(--header-height); z-index: var(--z-sticky);
    display: flex; gap: var(--space-3); padding: var(--space-4) 0;
    background: var(--bg-app);
}
.cast-search { flex: 1; max-width: 320px; padding: var(--space-2) var(--space-3);
    background: var(--bg-card); border: 1px solid var(--border-color);
    border-radius: var(--radius-md); color: var(--text-primary); }
.cast-filterbar select { padding: var(--space-2) var(--space-3); background: var(--bg-card);
    border: 1px solid var(--border-color); border-radius: var(--radius-md); color: var(--text-primary); }
.cast-list { border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); overflow: hidden; }
.cast-divider { padding: var(--space-3) var(--space-4); font-size: var(--text-xs);
    text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted);
    background: var(--bg-app); border-top: 1px solid var(--border-subtle); }
.cast-error, .cast-nomatch { padding: var(--space-6); color: var(--text-secondary); }
.cast-error button, .cast-nomatch button {
    margin-left: var(--space-2); color: var(--primary-400); background: none; border: none; cursor: pointer; }

@media (max-width: 720px) {
    .cast-page { padding: var(--space-5) var(--space-4); }
    .cast-search { max-width: none; }
}
```

- [ ] **Step 5: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds (CastRow / CastingDetailPanel are stubbed in Tasks 10–11; to build now, create minimal placeholder files exporting `() => null` for `CastRow.jsx` and `CastingDetailPanel.jsx`, to be replaced next).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/layout/SectionNav.jsx frontend/src/App.jsx frontend/src/components/cast/
git commit -m "feat(casting): Cast nav tab, route, and CastPage shell with states"
```

---

## Task 10: `CastRow` and `StatusBadge`

**Files:**
- Create: `frontend/src/components/cast/StatusBadge.jsx`
- Create/replace: `frontend/src/components/cast/CastRow.jsx`
- Modify: `frontend/src/components/cast/CastPage.css` (row styles)

**Interfaces:**
- Consumes: `row` shape from `CastPage` — `{ name, scene_count, casting, conflicts, orphaned }`; `Badge` from `components/ui`.
- Produces: `StatusBadge({ status })`; `CastRow({ row, onOpen })` — a `<button>` row.

- [ ] **Step 1: Write `StatusBadge.jsx`**

```jsx
// frontend/src/components/cast/StatusBadge.jsx
import { Badge } from '../ui';

const MAP = {
    wishlist: { variant: 'neutral', label: 'Wishlist' },
    offer:    { variant: 'warning', label: 'Offer' },
    booked:   { variant: 'success', label: 'Booked' },
    declined: { variant: 'danger',  label: 'Declined' },
    released: { variant: 'neutral', label: 'Released', className: 'status-badge--released' },
};

export default function StatusBadge({ status }) {
    const cfg = MAP[status] || MAP.wishlist;
    return <Badge variant={cfg.variant} dot className={cfg.className}>{cfg.label}</Badge>;
}
```

Add to `CastPage.css`:
```css
.status-badge--released { background: transparent; border: 1px dashed var(--gray-600); color: var(--text-muted); }
```

- [ ] **Step 2: Write `CastRow.jsx`**

```jsx
// frontend/src/components/cast/CastRow.jsx
import { ChevronRight, TriangleAlert } from 'lucide-react';
import StatusBadge from './StatusBadge';

function Avatar({ row }) {
    const url = row.casting?.headshot_url;
    if (url) return <img className="cast-row-avatar" src={url} alt="" />;
    if (!row.casting) return <span className="cast-row-avatar cast-row-avatar--empty" aria-hidden />;
    const initials = row.name.split(/\s+/).slice(0, 2).map((w) => w[0]).join('');
    return <span className="cast-row-avatar cast-row-avatar--mono" aria-hidden>{initials}</span>;
}

export default function CastRow({ row, onOpen }) {
    const actor = row.casting?.actor_name;
    const conflictCount = row.conflicts.length;
    const label = `${row.name} — ${actor || 'not cast'}${row.casting ? `, ${row.casting.status}` : ''}`;
    return (
        <button className="cast-row" onClick={onOpen} aria-label={label}>
            <Avatar row={row} />
            <span className="cast-row-main">
                <span className="cast-row-name">{row.name}</span>
                {row.scene_count != null && (
                    <span className="cast-row-sub">{row.scene_count} scenes</span>
                )}
            </span>
            <span className="cast-row-actor">
                {actor || <span className="cast-row-addcta">Add casting &rarr;</span>}
            </span>
            {row.casting && <StatusBadge status={row.casting.status} />}
            {conflictCount > 0 && (
                <span className="cast-row-conflict" aria-label={`${conflictCount} availability conflicts`}>
                    <TriangleAlert size={13} aria-hidden /> {conflictCount} conflicts
                </span>
            )}
            {row.orphaned && <span className="cast-row-tag">Not in breakdown</span>}
            <ChevronRight size={16} className="cast-row-chev" aria-hidden />
        </button>
    );
}
```

- [ ] **Step 3: Row CSS**

Append to `CastPage.css`:
```css
.cast-row { display: flex; align-items: center; gap: var(--space-3); width: 100%;
    padding: var(--space-3) var(--space-4); background: var(--bg-card);
    border: none; border-bottom: 1px solid var(--border-subtle); cursor: pointer;
    text-align: left; color: var(--text-primary); }
.cast-row:last-child { border-bottom: none; }
.cast-row:hover { background: var(--bg-elevated); }
.cast-row:focus-visible { outline: 2px solid var(--primary-500); outline-offset: -2px; }
.cast-row-avatar { width: 40px; height: 40px; border-radius: var(--radius-md);
    object-fit: cover; flex-shrink: 0; display: grid; place-items: center;
    background: var(--gray-700); font-size: var(--text-xs); color: var(--text-secondary); }
.cast-row-avatar--empty { border: 1px solid var(--gray-600); background: transparent; border-radius: var(--radius-full); }
.cast-row-main { display: flex; flex-direction: column; min-width: 160px; }
.cast-row-name { font-size: var(--text-sm); font-weight: 600; text-transform: uppercase; letter-spacing: 0.02em; }
.cast-row-sub { font-size: var(--text-xs); color: var(--text-secondary); }
.cast-row-actor { flex: 1; font-size: var(--text-sm); }
.cast-row-addcta { color: var(--primary-400); }
.cast-row-conflict { display: inline-flex; align-items: center; gap: 4px;
    font-size: var(--text-xs); color: var(--danger); white-space: nowrap; }
.cast-row-tag { font-size: var(--text-2xs); color: var(--text-muted);
    border: 1px solid var(--gray-600); border-radius: var(--radius-full); padding: 1px 8px; }
.cast-row-chev { color: var(--text-muted); flex-shrink: 0; }

@media (max-width: 720px) {
    .cast-row { flex-wrap: wrap; }
    .cast-row-sub, .cast-row-chev { display: none; }
    .cast-row-actor { flex-basis: 100%; padding-left: 52px; }
}
```

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/cast/
git commit -m "feat(casting): CastRow + StatusBadge, headshot-forward list"
```

---

## Task 11: `CastingDetailPanel` + `UnavailabilityEditor` (autosave)

**Files:**
- Create/replace: `frontend/src/components/cast/CastingDetailPanel.jsx`, `CastingDetailPanel.css`
- Create: `frontend/src/components/cast/UnavailabilityEditor.jsx`

**Interfaces:**
- Consumes: `createCasting`, `updateCasting`, `deleteCasting`, `addUnavailability`, `removeUnavailability`, `uploadHeadshot` (Task 8); `Drawer` from `components/ui`; `useConfirm`/toast context if the app has one (check `frontend/src/context/`).
- Produces: `CastingDetailPanel({ scriptId, openId, casting, characterName, conflicts, onClose, onChanged })`. On any create it calls `onChanged()` so the parent reloads; edits also call `onChanged()` after save (debounced) so the list reflects new status/actor.
- `canEdit` is derived from whether contact fields are present OR the app's existing role hook; simplest v1: attempt the edit and, on `403`, flip to read-only + show the notice.

- [ ] **Step 1: Write `UnavailabilityEditor.jsx`**

```jsx
// frontend/src/components/cast/UnavailabilityEditor.jsx
import { useState } from 'react';
import { X, Plus } from 'lucide-react';
import { addUnavailability, removeUnavailability } from '../../services/apiService';

const fmt = (d) => new Date(d + 'T00:00:00').toLocaleDateString(undefined,
    { day: '2-digit', month: 'short' });

export default function UnavailabilityEditor({ castingId, ranges, canEdit, onChanged }) {
    const [adding, setAdding] = useState(false);
    const [start, setStart] = useState('');
    const [end, setEnd] = useState('');
    const [reason, setReason] = useState('');
    const [err, setErr] = useState(null);

    const submit = async () => {
        setErr(null);
        if (!start || !end) { setErr('Pick both dates.'); return; }
        if (end < start) { setErr('End date is before the start date.'); return; }
        try {
            await addUnavailability(castingId, { start_date: start, end_date: end, reason });
            setAdding(false); setStart(''); setEnd(''); setReason('');
            onChanged();
        } catch {
            setErr('Couldn’t save — retry.');
        }
    };

    const remove = async (id) => {
        try { await removeUnavailability(id); onChanged(); } catch { /* toast */ }
    };

    return (
        <div className="cd-unavail">
            <p className="cd-label">Unavailable dates</p>
            {ranges.length === 0 && <p className="cd-muted">None set.</p>}
            {ranges.map((r) => (
                <div className="cd-range" key={r.id}>
                    <span>{fmt(r.start_date)} – {fmt(r.end_date)}</span>
                    <span className="cd-range-reason">{r.reason || '—'}</span>
                    {canEdit && (
                        <button aria-label="Remove range" onClick={() => remove(r.id)}>
                            <X size={14} />
                        </button>
                    )}
                </div>
            ))}
            {canEdit && !adding && (
                <button className="cd-add" onClick={() => setAdding(true)}>
                    <Plus size={14} /> Add unavailable dates
                </button>
            )}
            {adding && (
                <div className="cd-range-form">
                    <input type="date" value={start} onChange={(e) => setStart(e.target.value)} aria-label="Start date" />
                    <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} aria-label="End date" />
                    <input type="text" placeholder="Reason (optional)" value={reason}
                        onChange={(e) => setReason(e.target.value)} />
                    <div className="cd-range-actions">
                        <button onClick={submit}>Add</button>
                        <button onClick={() => setAdding(false)}>Cancel</button>
                    </div>
                    {err && <p className="cd-err">{err}</p>}
                </div>
            )}
        </div>
    );
}
```

- [ ] **Step 2: Write `CastingDetailPanel.jsx`**

```jsx
// frontend/src/components/cast/CastingDetailPanel.jsx
import { useEffect, useRef, useState } from 'react';
import { Drawer } from '../ui';
import {
    createCasting, updateCasting, deleteCasting, uploadHeadshot,
} from '../../services/apiService';
import UnavailabilityEditor from './UnavailabilityEditor';
import './CastingDetailPanel.css';

const STATUSES = ['wishlist', 'offer', 'booked', 'declined', 'released'];
const LABEL = { wishlist: 'Wishlist', offer: 'Offer', booked: 'Booked', declined: 'Declined', released: 'Released' };

export default function CastingDetailPanel({
    scriptId, casting, characterName, conflicts, onClose, onChanged,
}) {
    const [row, setRow] = useState(casting);
    const [saveState, setSaveState] = useState('idle'); // idle | saving | error
    const [canEdit, setCanEdit] = useState(true);
    const rowIdRef = useRef(casting?.id || null);

    useEffect(() => { setRow(casting); rowIdRef.current = casting?.id || null; }, [casting]);

    const myConflicts = conflicts.filter((c) => c.character_name === (row?.character_name || characterName));

    // Ensure a casting row exists, then apply `fields`. Returns updated row.
    const persist = async (fields) => {
        setSaveState('saving');
        try {
            let id = rowIdRef.current;
            if (!id) {
                const created = await createCasting(scriptId, characterName);
                id = created.casting.id;
                rowIdRef.current = id;
                setRow(created.casting);
            }
            const res = await updateCasting(id, fields);
            setRow(res.casting);
            setSaveState('idle');
            onChanged();
            return res.casting;
        } catch (e) {
            if (e?.response?.status === 403) { setCanEdit(false); setSaveState('idle'); return null; }
            setSaveState('error');
            return null;
        }
    };

    const field = (name) => ({
        defaultValue: row?.[name] ?? '',
        onBlur: (e) => { if (e.target.value !== (row?.[name] ?? '')) persist({ [name]: e.target.value }); },
        disabled: !canEdit,
    });

    const onHeadshot = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        if (file.size > 5 * 1024 * 1024) { setSaveState('error'); return; }
        setSaveState('saving');
        try {
            let id = rowIdRef.current;
            if (!id) { const c = await createCasting(scriptId, characterName); id = c.casting.id; rowIdRef.current = id; }
            const res = await uploadHeadshot(id, file);
            setRow(res.casting); setSaveState('idle'); onChanged();
        } catch { setSaveState('error'); }
    };

    const onDelete = async () => {
        if (!rowIdRef.current) { onClose(); return; }
        if (!window.confirm(`Delete casting for ${row.character_name}? This removes the actor, contacts, headshot, and availability for this character. It doesn’t affect the breakdown.`)) return;
        await deleteCasting(rowIdRef.current);
        onChanged();
        onClose();
    };

    const subtitle = row?.orphaned
        ? 'Not in the latest breakdown — details are kept.'
        : (row ? null : 'Not cast yet.');

    return (
        <Drawer
            isOpen
            onClose={onClose}
            width="440px"
            title={row?.character_name || characterName}
            subtitle={subtitle}
            subHeader={
                <span className="cd-savestate">
                    {saveState === 'saving' && 'Saving…'}
                    {saveState === 'idle' && '✓ All changes saved'}
                    {saveState === 'error' && '⚠ Couldn’t save — change a field to retry'}
                </span>
            }
            footer={canEdit && rowIdRef.current
                ? <button className="cd-delete" onClick={onDelete}>Delete casting</button>
                : null}
        >
            {!canEdit && <p className="cd-muted">Only the owner and admins can edit casting.</p>}

            {myConflicts.length > 0 && (
                <div className="cd-conflict-callout">
                    <strong>Conflicts with {myConflicts.length} shoot {myConflicts.length === 1 ? 'day' : 'days'}</strong>
                    <span>{myConflicts.map((c) => `Day ${c.day_number} (${c.shoot_date})`).join(' · ')}</span>
                </div>
            )}

            <label className="cd-label">Actor</label>
            <input type="text" {...field('actor_name')} placeholder="Actor name" />

            <label className="cd-label">Status</label>
            <div className="cd-status" role="radiogroup" aria-label="Status">
                {STATUSES.map((s) => (
                    <button
                        key={s}
                        role="radio"
                        aria-checked={(row?.status || 'wishlist') === s}
                        className={(row?.status || 'wishlist') === s ? 'active' : ''}
                        disabled={!canEdit}
                        onClick={() => persist({ status: s })}
                    >{LABEL[s]}</button>
                ))}
            </div>

            <label className="cd-label">Headshot</label>
            <div className="cd-headshot">
                {row?.headshot_url
                    ? <img src={row.headshot_url} alt={`${row.character_name} headshot`} />
                    : <span className="cd-headshot-empty">No photo</span>}
                {canEdit && (
                    <label className="cd-headshot-btn">
                        {row?.headshot_url ? 'Replace' : 'Upload'}
                        <input type="file" accept="image/jpeg,image/png,image/webp" onChange={onHeadshot} hidden />
                    </label>
                )}
            </div>

            {'contact_phone' in (row || {}) || canEdit ? (
                <>
                    <p className="cd-section">Contact</p>
                    <label className="cd-label">Phone</label>
                    <input type="tel" {...field('contact_phone')} />
                    <label className="cd-label">Email</label>
                    <input type="email" {...field('contact_email')} />
                    <label className="cd-label">Agent</label>
                    <textarea rows={2} {...field('agent_contact')} placeholder="Agency, agent name, phone" />
                </>
            ) : null}

            <p className="cd-section">Availability</p>
            {rowIdRef.current
                ? <UnavailabilityEditor
                    castingId={rowIdRef.current}
                    ranges={row?.unavailability || []}
                    canEdit={canEdit}
                    onChanged={onChanged}
                  />
                : <p className="cd-muted">Add an actor or status first to record unavailable dates.</p>}

            <label className="cd-label">Notes</label>
            <textarea rows={3} {...field('notes')} />
        </Drawer>
    );
}
```

Note: `UnavailabilityEditor` calls `onChanged` (the page reload) after add/remove; the panel receives fresh `casting`/`conflicts` via props on the parent's re-render. To keep the open drawer in sync after `onChanged`, `CastPage` must pass the refreshed `casting.find(...)` — which it already does because `openId` is stable across reloads.

- [ ] **Step 3: Write `CastingDetailPanel.css`**

```css
/* frontend/src/components/cast/CastingDetailPanel.css */
.cd-savestate { font-size: var(--text-2xs); color: var(--text-muted); }
.cd-label { display: block; font-size: var(--text-2xs); text-transform: uppercase;
    letter-spacing: 0.06em; color: var(--text-muted); margin: var(--space-4) 0 var(--space-1); }
.cd-section { font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--text-secondary); margin: var(--space-6) 0 0; border-top: 1px solid var(--border-subtle);
    padding-top: var(--space-4); }
.ui-drawer-body input[type=text], .ui-drawer-body input[type=tel],
.ui-drawer-body input[type=email], .ui-drawer-body input[type=date],
.ui-drawer-body textarea {
    width: 100%; padding: var(--space-2) var(--space-3); background: var(--bg-app);
    border: 1px solid var(--border-color); border-radius: var(--radius-md);
    color: var(--text-primary); font: inherit; }
.cd-status { display: flex; flex-wrap: wrap; gap: var(--space-1); }
.cd-status button { padding: var(--space-1) var(--space-2); font-size: var(--text-xs);
    background: var(--bg-app); border: 1px solid var(--border-color);
    border-radius: var(--radius-sm); color: var(--text-secondary); cursor: pointer; }
.cd-status button.active { background: var(--primary-alpha-15); border-color: var(--primary-500); color: var(--primary-300); }
.cd-headshot { display: flex; align-items: center; gap: var(--space-3); }
.cd-headshot img { width: 88px; height: 88px; object-fit: cover; border-radius: var(--radius-md); }
.cd-headshot-empty { width: 88px; height: 88px; display: grid; place-items: center;
    border: 1px dashed var(--gray-600); border-radius: var(--radius-md);
    font-size: var(--text-2xs); color: var(--text-muted); }
.cd-headshot-btn { font-size: var(--text-sm); color: var(--primary-400); cursor: pointer; }
.cd-conflict-callout { display: flex; flex-direction: column; gap: 2px;
    padding: var(--space-3); margin-top: var(--space-4);
    background: var(--danger-bg); border-left: 3px solid var(--danger); border-radius: var(--radius-sm);
    font-size: var(--text-xs); color: var(--text-primary); }
.cd-muted { font-size: var(--text-xs); color: var(--text-muted); }
.cd-err { color: var(--danger); font-size: var(--text-xs); }
.cd-delete { color: var(--danger); background: none; border: none; cursor: pointer; font-size: var(--text-sm); }
.cd-range { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-xs);
    padding: var(--space-1) 0; }
.cd-range-reason { color: var(--text-secondary); flex: 1; }
.cd-range button, .cd-add, .cd-range-actions button {
    background: none; border: none; color: var(--primary-400); cursor: pointer; }
.cd-add { display: inline-flex; align-items: center; gap: 4px; font-size: var(--text-xs); margin-top: var(--space-2); }
.cd-range-form { display: flex; flex-direction: column; gap: var(--space-2); margin-top: var(--space-2); }
```

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Manual verification (dev server)**

Run backend (`cd backend && python app.py`) and frontend (`cd frontend && npm run dev`), open a script with an analyzed breakdown, go to the Cast tab:
- List shows every breakdown character as "Not cast".
- Click a character → drawer opens; set status to Booked, type an actor name, blur → "Saving…" → "All changes saved"; the row now shows the actor + Booked badge.
- Add an unavailable range → it appears; remove it → it's gone.
- Upload a JPG headshot → thumbnail appears in drawer and row.
- Reload the page → all data persists.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/cast/
git commit -m "feat(casting): CastingDetailPanel + UnavailabilityEditor with autosave"
```

---

## Task 12: Conflict panel + day dots on the Schedule page

**Files:**
- Create: `frontend/src/components/schedule/ConflictPanel.jsx`, `ConflictPanel.css`
- Modify: `frontend/src/components/schedule/ShootingSchedulePage.jsx`

**Interfaces:**
- Consumes: `getCastingConflicts(scriptId, scheduleId)` (Task 8). `ShootingSchedulePage` already has `scriptId` and an active schedule id (`activeScheduleId` per line ~197).
- Produces: `ConflictPanel({ scriptId, scheduleId })` — self-fetches, renders nothing when there are no conflicts; a `conflictDayIds: Set` the page can use to mark day headers.

- [ ] **Step 1: Write `ConflictPanel.jsx`**

```jsx
// frontend/src/components/schedule/ConflictPanel.jsx
import { useEffect, useState } from 'react';
import { TriangleAlert, ChevronDown, ChevronRight } from 'lucide-react';
import { getCastingConflicts } from '../../services/apiService';
import './ConflictPanel.css';

export default function ConflictPanel({ scriptId, scheduleId, onConflictDays }) {
    const [conflicts, setConflicts] = useState([]);
    const [open, setOpen] = useState(true);

    useEffect(() => {
        let cancelled = false;
        if (!scheduleId) { setConflicts([]); onConflictDays?.(new Set()); return; }
        getCastingConflicts(scriptId, scheduleId)
            .then((data) => {
                if (cancelled) return;
                setConflicts(data.conflicts || []);
                onConflictDays?.(new Set((data.conflicts || []).map((c) => c.shooting_day_id)));
            })
            .catch(() => { if (!cancelled) { setConflicts([]); onConflictDays?.(new Set()); } });
        return () => { cancelled = true; };
    }, [scriptId, scheduleId, onConflictDays]);

    if (conflicts.length === 0) return null;

    return (
        <div className="conflict-panel">
            <button className="conflict-panel-head" onClick={() => setOpen((o) => !o)}>
                {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                <TriangleAlert size={14} />
                Availability conflicts ({conflicts.length})
            </button>
            {open && (
                <ul className="conflict-panel-list">
                    {conflicts.map((c, i) => (
                        <li key={i}>
                            Day {c.day_number} &middot; {c.shoot_date} &mdash;{' '}
                            {c.actor_name || 'Actor'} ({c.character_name}) unavailable
                            {c.reason ? ` · ${c.reason}` : ''}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
```

- [ ] **Step 2: `ConflictPanel.css`**

```css
/* frontend/src/components/schedule/ConflictPanel.css */
.conflict-panel { margin: var(--space-3) 0; border: 1px solid var(--danger);
    border-left-width: 3px; border-radius: var(--radius-md); background: var(--danger-bg); }
.conflict-panel-head { display: flex; align-items: center; gap: var(--space-2);
    width: 100%; padding: var(--space-2) var(--space-3); background: none; border: none;
    color: var(--text-primary); font-size: var(--text-sm); font-weight: 600; cursor: pointer; }
.conflict-panel-list { margin: 0; padding: 0 var(--space-4) var(--space-3) var(--space-8);
    font-size: var(--text-xs); color: var(--text-secondary); }
.conflict-panel-list li { padding: 2px 0; }
```

- [ ] **Step 3: Mount it in `ShootingSchedulePage.jsx`**

- Import `ConflictPanel` and `useState`/`useCallback` if not already imported.
- Add state: `const [conflictDayIds, setConflictDayIds] = useState(new Set());`
- Render `<ConflictPanel scriptId={scriptId} scheduleId={activeScheduleId} onConflictDays={setConflictDayIds} />` just below the schedule toolbar (above the day grid).
- Where day headers render, add a marker when `conflictDayIds.has(day.id)`:
  ```jsx
  {conflictDayIds.has(day.id) && <span className="day-conflict-dot" aria-label="Has an availability conflict" />}
  ```
  and in the schedule CSS:
  ```css
  .day-conflict-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
      background: var(--danger); margin-left: 6px; }
  ```
  (Use the actual day-header element/class present in the file.)

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Manual verification**

With a script that has: an `active` schedule, dated shoot days, a `booked` casting row, and an unavailable range covering one of those dates — open the Schedule page: the "Availability conflicts (N)" panel appears and the affected day header shows a red dot. Remove the unavailable range → panel disappears on reload.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/schedule/
git commit -m "feat(casting): availability conflict panel + day markers on schedule"
```

---

## Task 13 (final, optional): Day Out of Days conflict overlay

Deferrable — the Schedule panel (Task 12) is the primary surface. Ship this only if Task 12 review is clean and there's appetite for touching the DOOD renderer.

**Files:**
- Modify: `backend/services/report_service.py` — `_render_day_out_of_days` / `_render_day_out_of_days_from_scenes` (~lines 1691–1760) and `aggregate_scene_data` (to thread conflict data into `data`).
- Modify: the DOOD preview React component (find via `grep -rn "day_out_of_days" frontend/src`).
- Test: `backend/tests/test_report_csv.py` is CSV-only; add `backend/tests/test_dood_conflict_overlay.py`.

**Interfaces:**
- Consumes: `casting_service.active_schedule_id`, `casting_service.compute_conflicts`.
- Produces: DOOD HTML (preview + PDF) renders a `--danger` ring on the work-mark cell for any `(character, day)` in the conflict set, plus a footnote when ≥1 conflict exists.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_dood_conflict_overlay.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.report_service import report_service


def test_dood_html_marks_conflict_cell(monkeypatch):
    # Minimal DOOD `data` with one character working one day, and that
    # (character, day) present in the conflict set.
    data = {
        "report_type": "day_out_of_days",
        "days": [{"day_number": 1, "shoot_date": "2026-03-12", "characters": ["JOHN"]}],
        "characters": ["JOHN"],
        "dood_conflicts": {("JOHN", 1)},
    }
    html = report_service._render_day_out_of_days(data)
    assert "dood-conflict" in html
    assert "Cast member unavailable" in html
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_dood_conflict_overlay.py -v`
Expected: FAIL (`dood-conflict` class absent).

- [ ] **Step 3: Implement**

In `report_service.py`:
- In `generate_report` / wherever DOOD `data` is assembled for the
  `day_out_of_days` type, after the schedule days are loaded, compute:
  ```python
  if report_type == 'day_out_of_days':
      try:
          import services.casting_service as casting_service
          sched_id = casting_service.active_schedule_id(script_id)
          conflicts = casting_service.compute_conflicts(script_id, sched_id) if sched_id else []
          data['dood_conflicts'] = {(c['character_name'], c['day_number']) for c in conflicts}
      except Exception:
          data['dood_conflicts'] = set()
  ```
- In `_render_day_out_of_days` (and the `_from_scenes` variant), where each
  work-mark `<td>` is emitted for `(character, day_number)`, add the class
  when `(character, day_number) in data.get('dood_conflicts', set())`:
  ```python
  cls = 'dood-conflict' if (char, day_num) in data.get('dood_conflicts', set()) else ''
  # ... f'<td class="{cls}">{mark}</td>'
  ```
- Append a footnote after the grid when `data.get('dood_conflicts')`:
  ```python
  '<p class="dood-footnote">▨ Cast member unavailable on this day.</p>'
  ```
- Add CSS to the DOOD stylesheet block:
  ```css
  td.dood-conflict { box-shadow: inset 0 0 0 2px #ef4444; }
  .dood-footnote { font-size: 9pt; color: #ef4444; margin-top: 6px; }
  ```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_dood_conflict_overlay.py tests/test_report_csv.py -v`
Expected: PASS; no CSV regressions.

- [ ] **Step 5: Full suite + frontend build**

Run: `cd backend && python -m pytest -q` then `cd ../frontend && npm run build`
Expected: green.

- [ ] **Step 6: Commit**

```bash
git add backend/services/report_service.py backend/tests/test_dood_conflict_overlay.py frontend/src
git commit -m "feat(casting): availability-conflict overlay on Day Out of Days"
```

---

## Self-Review

**1. Spec coverage**

| Design spec section | Task |
|---|---|
| §4.1 `casting` table | 1 |
| §4.2 `casting_unavailability` | 1 |
| §4.3 RLS | 1 |
| §5.1 blueprint + service + register | 2, 3 |
| §5.2 `from_casting` resolver | 3 |
| §5.3 list/create/patch/delete endpoints | 3 |
| §5.3 unavailability endpoints | 4 |
| §5.3 headshot endpoint | 5 |
| §5.4 serializer / contact redaction | 2 (impl), 3 (wiring + tests) |
| §5.5 `compute_conflicts` + endpoint | 6 |
| §5.6 merge hook | 7 |
| §6.1 route & nav | 9 |
| §6.2 `CastPage`, `CastingDetailPanel`, `useCastRole` | 9, 10, 11 |
| §6.3 apiService | 8 |
| §7 Schedule conflict panel + day dots | 12 |
| §7 DOOD overlay | 13 |
| §8 headshot storage path + signed URL | 2 (`_headshot_url`), 5 (`store_headshot`) |
| §9 tests | every backend task; 11–12 manual + build |

| UI/UX spec section | Task |
|---|---|
| §1 design tokens | CSS in 9–12 |
| §2 nav placement + icon + activeKey | 9 |
| §3 page layout, summary, filter bar, ordering, states | 9 |
| §3.4 row anatomy (cast/uncast/orphan, mobile) | 10 |
| §4 drawer, autosave, not-cast/orphan/read-only variants | 11 |
| §5 status badge (5 states, `released` outline) | 10 |
| §6 conflict surfacing (CastPage pills, Schedule panel, DOOD) | 9 (pills), 12 (schedule), 13 (DOOD) |
| §6 conflicts only for booked/offer | 6 |
| §7 page states table | 9 |
| §8 copy | 9–12 (strings inlined) |
| §9 a11y (row button label, radiogroup, aria-label on pill, focus ring) | 10, 11 |

Gaps closed: none outstanding. The `useCastRole` hook from UI-UX §11 is replaced by the simpler "attempt-then-403 → read-only" approach in Task 11 (noted in that task's Interfaces block) — functionally equivalent for v1, less code.

**2. Placeholder scan** — no "TBD"/"handle edge cases"/"similar to Task N". Every code step has literal code. Task 13 is explicitly marked optional/deferrable, not a placeholder. The one "find via grep" (Task 13, DOOD preview component) is a genuine locate-in-codebase step with the exact grep given.

**3. Type consistency**
- `casting_service` function names used in route tasks (`list_casting`, `breakdown_characters`, `create_casting`, `update_casting`, `delete_casting`, `add_unavailability`, `delete_unavailability`, `serialize`, `compute_conflicts`, `active_schedule_id`, `store_headshot`, `_headshot_url`, `_client`, `CastingConflict`, `CastingNotFound`, `HEADSHOT_BUCKET`, `MAX_HEADSHOT_BYTES`, `CONFLICT_STATUSES`) all match their definitions in Tasks 2, 5, 6.
- Endpoint payload keys (`casting`, `characters`, `unavailability`, `conflicts`, `schedule_id`, `success`) consistent between route tasks and the apiService/frontend tasks.
- Conflict dict keys (`shooting_day_id`, `day_number`, `shoot_date`, `character_name`, `actor_name`, `reason`) identical in Task 6 service, Task 6 tests, Task 12 `ConflictPanel`, Task 13.
- `row` shape in `CastPage` (`name`, `scene_count`, `casting`, `conflicts`, `orphaned`) matches `CastRow` consumption in Task 10.
- URL param name `unavail_id` matches between the route (`/api/casting/unavailability/<unavail_id>`), `from_casting_unavailability` resolver (`kwargs.get('unavail_id')`), and Task 4.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-08-27-cast-casting-v1.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
