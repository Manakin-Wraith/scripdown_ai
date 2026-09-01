# Production Members (Step 2b) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the `production_members` permission layer so a production can be shared with a line producer / coordinator / viewer who can read or edit the crew roster (per role + per-member toggles) without gaining any script access.

**Architecture:** A new `production_members` table + `production_invites` table (migration 052). A new `middleware/production_authz.py` mirrors `middleware/authorization.py` but for the production axis: `get_production_role`, `get_production_access` (role + four capability booleans, owner short-circuits all-true), and a `require_production_role(min_role, capability, resolver)` decorator. The 2a owner-only crew routes are re-gated to the decorator; the crew payload is redacted server-side for members without `can_view_sensitive`. `_fetch_seats_used` unions production members + pending production invites into the existing person-dedup. Member/invite lifecycle routes live on the existing `production_bp`. Frontend adds a Members tab, un-hides the Crew tab for members, and a public invite-accept page.

**Tech Stack:** Flask (Python 3.13), supabase-py with the service-role key, pytest with an in-memory `MockSupabase`; React 18 + Vite (plain JSX), axios via the single `apiService.js`.

**Spec:** `docs/superpowers/specs/2026-09-01-production-members-design.md`

## Global Constraints

- **Migrations are applied manually** to the Supabase project (`run_migration.py` is dead). A migration task's final step is "apply this SQL in the Supabase SQL editor", not running a script.
- **Backend enforcement is app-layer** — the backend uses the service-role key (bypasses RLS). RLS policies in the migration are a direct-client backstop only.
- **`ROLE_RANK = {'viewer': 1, 'coordinator': 2, 'admin': 3, 'owner': 4}`** for the production axis. `owner` is never a stored row — it is `productions.owner_id`.
- **Four capability flags, exact names:** `can_view_sensitive`, `can_edit_crew`, `can_manage_members`, `can_edit_production`. All `boolean not null default false`.
- **Role presets** (applied in the service layer on insert, never by the DB): `admin` → all four `true`; `coordinator` → `can_edit_crew` true, rest false; `viewer` → all false.
- **Sensitive fields redacted for non-`can_view_sensitive`:** `production_crew.job_rate`, `contacts.phone`, `contacts.standard_rate`. Keep `job_rate_unit` / `rate_unit`.
- **The entitlement gate on add/invite checks the PRODUCTION OWNER's entitlement**, not the acting caller's.
- **Axes stay independent:** never modify `middleware/authorization.py`, `get_script_role`, `script_members`, or any report/breakdown route.
- **Frontend gate is `npm run build`** (repo lint is broken — see project memory). No frontend unit-test framework; frontend tasks end with a build + a manual check.
- Backend gate: `cd backend && pytest tests/` stays green.
- Test user in backend tests is always `DEV_USER_ID` (`middleware.auth.DEV_USER_ID`), email `dev@example.com`, via `monkeypatch.setattr("middleware.auth.DEV_MODE", True)`. Simulate "caller is not the owner" by setting `owner_id` to `"other"` on the production and adding a `production_members` row for `DEV_USER_ID`.

---

## File Structure

**Backend — create:**
- `backend/db/migrations/052_production_members.sql` — the two tables, indexes, RLS, delete-user comment.
- `backend/middleware/production_authz.py` — `ROLE_RANK`, `PRODUCTION_NOT_FOUND`, `get_production_role`, `get_production_access`, `require_production_role`, resolvers.
- `backend/services/production_member_service.py` — presets, rank guardrail, list, add, update, remove, revoke, token lookup, accept.
- `backend/tests/test_production_authz.py`
- `backend/tests/test_production_member_routes.py`

**Backend — modify:**
- `backend/services/production_crew_service.py` — `list_crew` / `add_crew` / `update_crew` gain redaction.
- `backend/routes/production_routes.py` — re-gate 5 crew routes to the decorator; add 7 member/invite routes.
- `backend/services/entitlement_service.py` — `_fetch_seats_used` unions two new sources.
- `backend/services/production_service.py` — `get_production_for_viewer` adds `production_access`; `list_productions` unions member rows.
- `backend/services/email_service.py` — `send_production_invite`, `send_production_member_added`.
- `backend/routes/invite_routes.py` — `auto_accept_pending_invites` also applies pending production invites.
- `backend/tests/test_production_crew_routes.py`, `test_entitlement_service.py`, `test_route_enforcement.py`, `test_production_routes.py` — extend.

**Frontend — create:**
- `frontend/src/components/productions/ProductionMembersTab.jsx`
- `frontend/src/pages/ProductionInviteAccept.jsx`

**Frontend — modify:**
- `frontend/src/services/apiService.js` — 7 new functions.
- `frontend/src/pages/ProductionDetailPage.jsx` — `production_access` state, Members tab, un-hide Crew tab.
- `frontend/src/components/productions/ProductionCrewTab.jsx` — gate write controls, redaction placeholders.
- `frontend/src/pages/ProductionsListPage.jsx` — list member productions + role badge.
- `frontend/src/App.jsx` — `/production-invites/:token` route.
- `frontend/src/pages/ProductionPages.css` — member-table + badge styles.

---

## Task 1: Migration 052 — production_members + production_invites

**Files:**
- Create: `backend/db/migrations/052_production_members.sql`

**Interfaces:**
- Produces: tables `production_members(id, production_id, user_id, role, can_view_sensitive, can_edit_crew, can_manage_members, can_edit_production, invited_by, created_at, updated_at)` and `production_invites(id, production_id, email, role, <4 flags>, token, status, invited_by, expires_at, created_at)`.

- [ ] **Step 1: Write the migration SQL**

Create `backend/db/migrations/052_production_members.sql`:

```sql
-- Migration 052: production_members + production_invites (build-sequence step 2b)
--
-- Additive permission layer for the production axis. Governs production-level
-- surfaces only (crew now; locations / schedule / call sheets / DPR later,
-- each adding its own capability column here). Does NOT touch script_members
-- or any script-scoped access.
--
-- Apply manually in the Supabase SQL editor (run_migration.py is dead).
--
-- DELETE-USER ORDERING (load-bearing, see 013_delete_user_safely.sql):
--   * A deleted OWNER: productions.owner_id ON DELETE CASCADE removes their
--     productions, which cascades production_members / production_invites /
--     production_crew via production_id ON DELETE CASCADE.
--   * A deleted MEMBER of someone else's production: production_members.user_id
--     ON DELETE CASCADE clears their membership rows; invited_by ON DELETE SET
--     NULL detaches invites they sent. No FK error in either direction.

CREATE TABLE IF NOT EXISTS production_members (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    production_id         uuid NOT NULL REFERENCES productions(id) ON DELETE CASCADE,
    user_id              uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role                 text NOT NULL CHECK (role IN ('admin','coordinator','viewer')),
    can_view_sensitive   boolean NOT NULL DEFAULT false,
    can_edit_crew        boolean NOT NULL DEFAULT false,
    can_manage_members   boolean NOT NULL DEFAULT false,
    can_edit_production  boolean NOT NULL DEFAULT false,
    invited_by           uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now(),
    UNIQUE (production_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_production_members_production ON production_members(production_id);
CREATE INDEX IF NOT EXISTS idx_production_members_user ON production_members(user_id);

CREATE TABLE IF NOT EXISTS production_invites (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    production_id         uuid NOT NULL REFERENCES productions(id) ON DELETE CASCADE,
    email                text NOT NULL,
    role                 text NOT NULL CHECK (role IN ('admin','coordinator','viewer')),
    can_view_sensitive   boolean NOT NULL DEFAULT false,
    can_edit_crew        boolean NOT NULL DEFAULT false,
    can_manage_members   boolean NOT NULL DEFAULT false,
    can_edit_production  boolean NOT NULL DEFAULT false,
    token                text NOT NULL UNIQUE,
    status               text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','accepted','revoked')),
    invited_by           uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    expires_at           timestamptz NOT NULL,
    created_at           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_production_invites_token ON production_invites(token);
CREATE INDEX IF NOT EXISTS idx_production_invites_production_status ON production_invites(production_id, status);
CREATE INDEX IF NOT EXISTS idx_production_invites_email ON production_invites(lower(email));
CREATE UNIQUE INDEX IF NOT EXISTS uq_production_invites_pending
    ON production_invites(production_id, lower(email)) WHERE status = 'pending';

-- updated_at trigger (reuses update_shooting_updated_at() from migration 030)
DROP TRIGGER IF EXISTS trg_production_members_updated_at ON production_members;
CREATE TRIGGER trg_production_members_updated_at
    BEFORE UPDATE ON production_members
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

-- RLS: direct-client backstop only. Real enforcement is Python + service key.
ALTER TABLE production_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE production_invites ENABLE ROW LEVEL SECURITY;

CREATE POLICY "owner manages production members"
    ON production_members FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = production_members.production_id
                  AND p.owner_id = auth.uid())
    );

CREATE POLICY "member reads own membership row"
    ON production_members FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "owner manages production invites"
    ON production_invites FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = production_invites.production_id
                  AND p.owner_id = auth.uid())
    );
```

- [ ] **Step 2: Verify the SQL parses (dry syntax check)**

Run: `python -c "import pathlib; s = pathlib.Path('backend/db/migrations/052_production_members.sql').read_text(); assert s.count('CREATE TABLE') == 2 and 'update_shooting_updated_at' in s and 'uq_production_invites_pending' in s; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/db/migrations/052_production_members.sql
git commit -m "feat(db): migration 052 — production_members + production_invites"
```

- [ ] **Step 4: Apply the migration in Supabase**

Paste the file contents into the Supabase SQL editor for project `twzfaizeyqwevmhjyicz` and run it. Confirm both tables appear under `public`. (This step is manual — note it in the PR description.)

---

## Task 2: production_authz.py — role & access resolution

**Files:**
- Create: `backend/middleware/production_authz.py`
- Test: `backend/tests/test_production_authz.py`

**Interfaces:**
- Consumes: `db.supabase_client.get_supabase_admin`.
- Produces:
  - `ROLE_RANK: dict[str, int]` — `{'viewer':1,'coordinator':2,'admin':3,'owner':4}`
  - `PRODUCTION_NOT_FOUND: object` — sentinel
  - `get_production_role(production_id, user_id) -> 'owner' | 'admin' | 'coordinator' | 'viewer' | None | PRODUCTION_NOT_FOUND`
  - `get_production_access(production_id, user_id) -> dict | None | PRODUCTION_NOT_FOUND` — dict has keys `role`, `can_view_sensitive`, `can_edit_crew`, `can_manage_members`, `can_edit_production`. Owner → `{'role':'owner', <all four>: True}`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_production_authz.py`:

```python
"""Tests for the production-axis authorization primitive.

MockSupabase is the same chainable in-memory stand-in used across the
production test suite (copied from test_production_crew_routes.py).
"""
import os, sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import middleware.production_authz as pa
from middleware.auth import DEV_USER_ID


class MockTable:
    def __init__(self, name, store):
        self.name, self.store = name, store
        self._filters, self._limit = {}, None

    def select(self, *_a, **_k): return self
    def eq(self, c, v): self._filters[c] = v; return self
    def limit(self, n): self._limit = n; return self

    def execute(self):
        rows = [r for r in self.store.get(self.name, [])
                if all(r.get(k) == v for k, v in self._filters.items())]
        if self._limit is not None:
            rows = rows[:self._limit]
        return SimpleNamespace(data=rows)


class MockSupabase:
    def __init__(self, store): self.store = store
    def table(self, name): return MockTable(name, self.store)


def _patch(monkeypatch, store):
    mock = MockSupabase(store)
    monkeypatch.setattr(pa, "get_supabase_admin", lambda: mock)
    return mock


def test_role_owner(monkeypatch):
    _patch(monkeypatch, {"productions": [{"id": "p1", "owner_id": DEV_USER_ID}],
                         "production_members": []})
    assert pa.get_production_role("p1", DEV_USER_ID) == "owner"


def test_role_member(monkeypatch):
    _patch(monkeypatch, {
        "productions": [{"id": "p1", "owner_id": "other"}],
        "production_members": [{"production_id": "p1", "user_id": DEV_USER_ID, "role": "coordinator"}],
    })
    assert pa.get_production_role("p1", DEV_USER_ID) == "coordinator"


def test_role_non_member_is_none(monkeypatch):
    _patch(monkeypatch, {"productions": [{"id": "p1", "owner_id": "other"}],
                         "production_members": []})
    assert pa.get_production_role("p1", DEV_USER_ID) is None


def test_role_missing_production(monkeypatch):
    _patch(monkeypatch, {"productions": [], "production_members": []})
    assert pa.get_production_role("nope", DEV_USER_ID) is pa.PRODUCTION_NOT_FOUND


def test_access_owner_is_all_true(monkeypatch):
    _patch(monkeypatch, {"productions": [{"id": "p1", "owner_id": DEV_USER_ID}],
                         "production_members": []})
    acc = pa.get_production_access("p1", DEV_USER_ID)
    assert acc == {"role": "owner", "can_view_sensitive": True, "can_edit_crew": True,
                   "can_manage_members": True, "can_edit_production": True}


def test_access_member_returns_stored_flags(monkeypatch):
    _patch(monkeypatch, {
        "productions": [{"id": "p1", "owner_id": "other"}],
        "production_members": [{"production_id": "p1", "user_id": DEV_USER_ID,
                               "role": "coordinator", "can_view_sensitive": True,
                               "can_edit_crew": True, "can_manage_members": False,
                               "can_edit_production": False}],
    })
    acc = pa.get_production_access("p1", DEV_USER_ID)
    assert acc["role"] == "coordinator" and acc["can_view_sensitive"] is True
    assert acc["can_manage_members"] is False


def test_access_non_member_is_none(monkeypatch):
    _patch(monkeypatch, {"productions": [{"id": "p1", "owner_id": "other"}],
                         "production_members": []})
    assert pa.get_production_access("p1", DEV_USER_ID) is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_production_authz.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'middleware.production_authz'`

- [ ] **Step 3: Write the implementation**

Create `backend/middleware/production_authz.py`:

```python
"""
Production-axis authorization for SlateOne.

Parallel to middleware/authorization.py (the script axis) — deliberately a
separate module because the production axis is independent: a production
member gets zero script access and vice versa.

Answers: may THIS user act on THIS production, at what role, with which
capability flags? Enforcement is app-layer (the backend uses the
service-role key).
"""
import logging
from functools import wraps

from flask import g, jsonify

from db.supabase_client import get_supabase_admin
from middleware.auth import get_user_id

logger = logging.getLogger(__name__)

ROLE_RANK = {'viewer': 1, 'coordinator': 2, 'admin': 3, 'owner': 4}

CAPABILITIES = (
    'can_view_sensitive', 'can_edit_crew', 'can_manage_members', 'can_edit_production',
)

# Sentinel distinguishing "production does not exist" (404) from "no access" (403).
PRODUCTION_NOT_FOUND = object()


def _get_production_owner(production_id):
    if not production_id:
        return PRODUCTION_NOT_FOUND
    res = (get_supabase_admin().table('productions')
           .select('owner_id').eq('id', production_id).limit(1).execute())
    if not res.data:
        return PRODUCTION_NOT_FOUND
    return res.data[0].get('owner_id')


def _get_member_row(production_id, user_id):
    res = (get_supabase_admin().table('production_members')
           .select('*').eq('production_id', production_id)
           .eq('user_id', user_id).limit(1).execute())
    return res.data[0] if res.data else None


def get_production_role(production_id, user_id):
    """'owner' | 'admin' | 'coordinator' | 'viewer' | None | PRODUCTION_NOT_FOUND"""
    if not production_id or not user_id:
        return None
    owner_id = _get_production_owner(production_id)
    if owner_id is PRODUCTION_NOT_FOUND:
        return PRODUCTION_NOT_FOUND
    if owner_id == user_id:
        return 'owner'
    row = _get_member_row(production_id, user_id)
    return row['role'] if row else None


def get_production_access(production_id, user_id):
    """dict(role + 4 capability booleans) | None | PRODUCTION_NOT_FOUND.

    Owner short-circuits to all-true. A member returns its row's stored
    flags. A non-member returns None.
    """
    if not production_id or not user_id:
        return None
    owner_id = _get_production_owner(production_id)
    if owner_id is PRODUCTION_NOT_FOUND:
        return PRODUCTION_NOT_FOUND
    if owner_id == user_id:
        return {'role': 'owner', **{c: True for c in CAPABILITIES}}
    row = _get_member_row(production_id, user_id)
    if not row:
        return None
    return {'role': row['role'], **{c: bool(row.get(c)) for c in CAPABILITIES}}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_production_authz.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/middleware/production_authz.py backend/tests/test_production_authz.py
git commit -m "feat(authz): production_authz role + access resolution"
```

---

## Task 3: production_authz.py — decorator & resolvers

**Files:**
- Modify: `backend/middleware/production_authz.py`
- Test: `backend/tests/test_production_authz.py` (append)

**Interfaces:**
- Consumes: `get_production_access`, `PRODUCTION_NOT_FOUND`, `ROLE_RANK` (Task 2); `flask.g`, `flask.jsonify`; `middleware.auth.get_user_id`.
- Produces:
  - `require_production_role(min_role=None, capability=None, resolver=from_production_id)` — decorator. Sets `g.production_access` and `g.resolved_production_id`. Marks the wrapper with `_authz_min_role` and/or `_authz_capability`.
  - `from_production_id(kwargs) -> str | None` — `kwargs.get('production_id')`
  - `from_crew_id(kwargs) -> str | None` — `production_crew.production_id` for `kwargs['crew_id']`
  - `from_member_id(kwargs) -> str | None` — `production_members.production_id` for `kwargs['member_id']`
  - `from_production_invite_id(kwargs) -> str | None` — `production_invites.production_id` for `kwargs['invite_id']`

- [ ] **Step 1: Write the failing test (append to test_production_authz.py)**

```python
import pytest
from flask import Flask, g, jsonify


def _app_with_route(**decorator_kwargs):
    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/api/productions/<production_id>/thing")
    @pa.require_production_role(**decorator_kwargs)
    def thing(production_id):
        return jsonify({"role": g.production_access["role"]})

    return app.test_client()


def _patch_auth(monkeypatch, store):
    _patch(monkeypatch, store)
    monkeypatch.setattr(pa, "get_user_id", lambda: DEV_USER_ID)


def test_decorator_min_role_rejects_non_member(monkeypatch):
    _patch_auth(monkeypatch, {"productions": [{"id": "p1", "owner_id": "other"}],
                              "production_members": []})
    r = _app_with_route(min_role="viewer").get("/api/productions/p1/thing")
    assert r.status_code == 403


def test_decorator_min_role_accepts_viewer(monkeypatch):
    _patch_auth(monkeypatch, {
        "productions": [{"id": "p1", "owner_id": "other"}],
        "production_members": [{"production_id": "p1", "user_id": DEV_USER_ID, "role": "viewer"}],
    })
    r = _app_with_route(min_role="viewer").get("/api/productions/p1/thing")
    assert r.status_code == 200 and r.get_json()["role"] == "viewer"


def test_decorator_capability_rejects_without_flag(monkeypatch):
    _patch_auth(monkeypatch, {
        "productions": [{"id": "p1", "owner_id": "other"}],
        "production_members": [{"production_id": "p1", "user_id": DEV_USER_ID,
                               "role": "viewer", "can_edit_crew": False}],
    })
    r = _app_with_route(capability="can_edit_crew").get("/api/productions/p1/thing")
    assert r.status_code == 403


def test_decorator_capability_accepts_overridden_viewer(monkeypatch):
    _patch_auth(monkeypatch, {
        "productions": [{"id": "p1", "owner_id": "other"}],
        "production_members": [{"production_id": "p1", "user_id": DEV_USER_ID,
                               "role": "viewer", "can_edit_crew": True}],
    })
    r = _app_with_route(capability="can_edit_crew").get("/api/productions/p1/thing")
    assert r.status_code == 200


def test_decorator_404_for_missing_production(monkeypatch):
    _patch_auth(monkeypatch, {"productions": [], "production_members": []})
    r = _app_with_route(min_role="viewer").get("/api/productions/nope/thing")
    assert r.status_code == 404


def test_decorator_sets_introspection_markers():
    f = pa.require_production_role(capability="can_edit_crew")(lambda: None)
    assert f._authz_capability == "can_edit_crew"
    g2 = pa.require_production_role(min_role="admin")(lambda: None)
    assert g2._authz_min_role == "admin"


def test_from_crew_id_resolves_production(monkeypatch):
    _patch(monkeypatch, {"production_crew": [{"id": "cr1", "production_id": "p1"}]})
    assert pa.from_crew_id({"crew_id": "cr1"}) == "p1"
    assert pa.from_crew_id({"crew_id": "missing"}) is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_production_authz.py -v -k "decorator or from_crew"`
Expected: FAIL — `AttributeError: module 'middleware.production_authz' has no attribute 'require_production_role'`

- [ ] **Step 3: Append the implementation to production_authz.py**

```python
def _lookup_production_id(table, id_value, id_col='id'):
    if not id_value:
        return None
    res = (get_supabase_admin().table(table)
           .select('production_id').eq(id_col, id_value).limit(1).execute())
    return res.data[0].get('production_id') if res.data else None


def from_production_id(kwargs):
    return kwargs.get('production_id')


def from_crew_id(kwargs):
    return _lookup_production_id('production_crew', kwargs.get('crew_id'))


def from_member_id(kwargs):
    return _lookup_production_id('production_members', kwargs.get('member_id'))


def from_production_invite_id(kwargs):
    return _lookup_production_id('production_invites', kwargs.get('invite_id'))


def require_production_role(min_role=None, capability=None, resolver=from_production_id):
    """Require the caller to hold a production role (and/or a capability flag).

    Stack BELOW @require_auth. Resolves the production via resolver(kwargs).
    404 if the production/resource is absent; 403 if the role rank is below
    `min_role` or the named `capability` flag is not True. On success sets
    g.production_access (the full dict) and g.resolved_production_id.
    """
    if min_role is not None and min_role not in ROLE_RANK:
        raise ValueError(f"Unknown min_role: {min_role}")
    if capability is not None and capability not in CAPABILITIES:
        raise ValueError(f"Unknown capability: {capability}")

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_id = get_user_id()
            if not user_id:
                return jsonify({'error': 'Authentication required'}), 401

            production_id = resolver(kwargs)
            if not production_id:
                return jsonify({'error': 'Not found'}), 404

            access = get_production_access(production_id, user_id)
            if access is PRODUCTION_NOT_FOUND:
                return jsonify({'error': 'Not found'}), 404
            if access is None:
                return jsonify({'error': 'Insufficient permissions'}), 403
            if min_role is not None and ROLE_RANK[access['role']] < ROLE_RANK[min_role]:
                return jsonify({'error': 'Insufficient permissions'}), 403
            if capability is not None and not access.get(capability):
                return jsonify({'error': 'Insufficient permissions'}), 403

            g.production_access = access
            g.resolved_production_id = production_id
            return f(*args, **kwargs)

        if min_role is not None:
            wrapper._authz_min_role = min_role
        if capability is not None:
            wrapper._authz_capability = capability
        return wrapper
    return decorator
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_production_authz.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add backend/middleware/production_authz.py backend/tests/test_production_authz.py
git commit -m "feat(authz): require_production_role decorator + resolvers"
```

---

## Task 4: Re-gate crew routes + server-side redaction

**Files:**
- Modify: `backend/services/production_crew_service.py`
- Modify: `backend/routes/production_routes.py:150-230` (the crew routes + `_require_production_owner`)
- Test: `backend/tests/test_production_crew_routes.py` (extend)

**Interfaces:**
- Consumes: `require_production_role`, `from_crew_id` (Task 3); `flask.g.production_access`.
- Produces:
  - `production_crew_service.list_crew(production_id, *, can_view_sensitive=False)` — strips `job_rate` / `contact.phone` / `contact.standard_rate` from each row when `can_view_sensitive` is falsy.
  - `add_crew` / `update_crew` gain a `can_view_sensitive` kwarg; when falsy, `job_rate` is dropped from the incoming `fields` before the write.

- [ ] **Step 1: Write the failing tests (append to test_production_crew_routes.py)**

Add to the file. Note `_patch` there already patches `middleware.authorization.get_supabase_admin`; add a line patching `middleware.production_authz` too.

First, update the shared `_patch` helper in that file:

```python
def _patch(monkeypatch, store):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    mock = MockSupabase(store)
    for mod in (ps, pcs):
        monkeypatch.setattr(mod, "get_supabase_admin", lambda: mock)
    monkeypatch.setattr("middleware.authorization.get_supabase_admin", lambda: mock)
    monkeypatch.setattr("middleware.production_authz.get_supabase_admin", lambda: mock)
    monkeypatch.setattr("middleware.production_authz.get_user_id", lambda: DEV_USER_ID)
    monkeypatch.setattr(ds, "get_departments_list", lambda: [{"code": "camera", "name": "Camera", "color": "#1"}])
```

Then new tests:

```python
def _member_store(role, **flags):
    """A production owned by someone else, with DEV_USER_ID as a member."""
    row = {"production_id": "p1", "user_id": DEV_USER_ID, "role": role,
           "can_view_sensitive": False, "can_edit_crew": False,
           "can_manage_members": False, "can_edit_production": False}
    row.update(flags)
    return _store(
        productions=[{"id": "p1", "owner_id": "other", "title": "Farm Feature"}],
        production_members=[row],
        contacts=[{"id": "c1", "owner_id": "other", "name": "Gary", "kind": "person",
                   "phone": "0821112222", "standard_rate": 4500}],
        production_crew=[{"id": "cr1", "production_id": "p1", "contact_id": "c1",
                         "role": "Gaffer", "department_code": "camera",
                         "job_rate": 4000, "job_rate_unit": "day"}],
    )


def test_viewer_can_read_crew(monkeypatch):
    _patch(monkeypatch, _member_store("viewer"))
    r = _client().get("/api/productions/p1/crew")
    assert r.status_code == 200


def test_viewer_cannot_edit_crew(monkeypatch):
    _patch(monkeypatch, _member_store("viewer"))
    r = _client().post("/api/productions/p1/crew", json={"contact_id": "c1"})
    assert r.status_code == 403


def test_coordinator_can_edit_crew(monkeypatch):
    store = _member_store("coordinator", can_edit_crew=True)
    store["contacts"].append({"id": "c2", "owner_id": "other", "name": "Sam", "kind": "person"})
    _patch(monkeypatch, store)
    # contact must be owned by the production owner, not the caller — but add_crew
    # checks contacts.owner_id == user_id (caller). See Step 3 note.
    r = _client().post("/api/productions/p1/crew", json={"contact_id": "c2"})
    assert r.status_code in (201, 400)  # 400 only if contact-ownership rule bites; see Step 3


def test_redaction_hides_rates_for_plain_viewer(monkeypatch):
    _patch(monkeypatch, _member_store("viewer"))
    row = _client().get("/api/productions/p1/crew").get_json()["crew"][0]
    assert "job_rate" not in row
    assert row.get("job_rate_unit") == "day"
    assert "phone" not in row["contact"]
    assert "standard_rate" not in row["contact"]


def test_no_redaction_for_sensitive_viewer(monkeypatch):
    _patch(monkeypatch, _member_store("viewer", can_view_sensitive=True))
    row = _client().get("/api/productions/p1/crew").get_json()["crew"][0]
    assert row["job_rate"] == 4000
    assert row["contact"]["phone"] == "0821112222"


def test_owner_still_sees_everything(monkeypatch):
    store = _store(
        contacts=[{"id": "c1", "owner_id": DEV_USER_ID, "name": "Gary", "kind": "person",
                   "phone": "0821112222", "standard_rate": 4500}],
        production_crew=[{"id": "cr1", "production_id": "p1", "contact_id": "c1",
                         "role": "Gaffer", "job_rate": 4000, "job_rate_unit": "day"}],
    )
    _patch(monkeypatch, store)
    row = _client().get("/api/productions/p1/crew").get_json()["crew"][0]
    assert row["job_rate"] == 4000 and row["contact"]["phone"] == "0821112222"
```

> **Note for the implementer:** the 2a `add_crew` requires the contact to be owned by the *caller* (`contacts.owner_id == user_id`). For a non-owner coordinator this is a real limitation — a coordinator can only assign contacts they personally own. This plan does NOT change that rule (contacts stay owner-scoped per the spec's "assigned subset only" decision; a coordinator creating crew for the owner's address book is out of scope). `test_coordinator_can_edit_crew` asserts the *authorization* passes (not 403); the 400 vs 201 depends on contact ownership and is acceptable either way. Keep the test as written.

- [ ] **Step 2: Run to verify the new tests fail**

Run: `cd backend && python -m pytest tests/test_production_crew_routes.py -v -k "viewer or redaction or coordinator or sensitive or owner_still"`
Expected: FAIL — routes still use `_require_production_owner` (403 for members) and `list_crew` has no redaction.

- [ ] **Step 3: Add redaction to production_crew_service.py**

Replace `_embed` and `list_crew`, and adjust `add_crew` / `update_crew` signatures:

```python
_SENSITIVE_CREW = ("job_rate",)
_SENSITIVE_CONTACT = ("phone", "standard_rate")


def _redact(rows, can_view_sensitive):
    if can_view_sensitive:
        return rows
    for r in rows:
        for k in _SENSITIVE_CREW:
            r.pop(k, None)
        contact = r.get("contact")
        if isinstance(contact, dict):
            for k in _SENSITIVE_CONTACT:
                contact.pop(k, None)
    return rows


def list_crew(production_id, *, can_view_sensitive=False):
    supabase = get_supabase_admin()
    rows = (supabase.table("production_crew").select("*")
            .eq("production_id", production_id).execute().data or [])
    _embed(supabase, rows)
    rows.sort(key=lambda c: (
        c.get("department_code") is None,
        c.get("department_code") or "",
        (c.get("contact") or {}).get("name") or "",
    ))
    return _redact(rows, can_view_sensitive)
```

In `add_crew(production_id, user_id, fields, *, can_view_sensitive=True)` and
`update_crew(production_id, crew_id, fields, *, can_view_sensitive=True)`, add at
the top of each (after the signature):

```python
    if not can_view_sensitive:
        fields = {k: v for k, v in fields.items() if k != "job_rate"}
```

(Default `True` keeps the owner path and CSV import unchanged — only the route passes an explicit flag.)

- [ ] **Step 4: Re-gate the crew routes in production_routes.py**

At the top, add:

```python
from middleware.production_authz import require_production_role, from_crew_id
from flask import g
```

Delete `_require_production_owner`. Rewrite the five crew routes:

```python
@production_bp.route("/api/productions/<production_id>/crew", methods=["GET"])
@require_auth
@require_production_role(min_role="viewer")
def list_production_crew(production_id):
    return jsonify({"crew": crew_svc.list_crew(
        production_id, can_view_sensitive=g.production_access["can_view_sensitive"])})


@production_bp.route("/api/productions/<production_id>/crew", methods=["POST"])
@require_auth
@require_production_role(capability="can_edit_crew")
def add_production_crew(production_id):
    data = request.get_json(silent=True) or {}
    try:
        result = crew_svc.add_crew(
            production_id, get_user_id(), data,
            can_view_sensitive=g.production_access["can_view_sensitive"])
        if result == "bad_contact":
            return jsonify({"error": "contact_id must be one of your contacts"}), 400
        if result == "bad_department":
            return jsonify({"error": "Unknown department_code"}), 400
        if result == "bad_rate_unit":
            return jsonify({"error": "job_rate_unit must be one of: day, week, flat"}), 400
        if result == "bad_dates":
            return jsonify({"error": "end_date must be on or after start_date"}), 400
        return jsonify({"crew": result}), 201
    except Exception as e:
        print(f"Error adding production crew: {e}")
        return jsonify({"error": str(e)}), 500


@production_bp.route("/api/productions/<production_id>/crew/<crew_id>", methods=["PATCH"])
@require_auth
@require_production_role(capability="can_edit_crew", resolver=from_crew_id)
def update_production_crew(production_id, crew_id):
    data = request.get_json(silent=True) or {}
    try:
        result = crew_svc.update_crew(
            production_id, crew_id, data,
            can_view_sensitive=g.production_access["can_view_sensitive"])
        if result == "not_found":
            return jsonify({"error": "Crew assignment not found"}), 404
        if result == "bad_department":
            return jsonify({"error": "Unknown department_code"}), 400
        if result == "bad_rate_unit":
            return jsonify({"error": "job_rate_unit must be one of: day, week, flat"}), 400
        if result == "bad_dates":
            return jsonify({"error": "end_date must be on or after start_date"}), 400
        return jsonify({"crew": result})
    except Exception as e:
        print(f"Error updating production crew: {e}")
        return jsonify({"error": str(e)}), 500


@production_bp.route("/api/productions/<production_id>/crew/import", methods=["POST"])
@require_auth
@require_production_role(capability="can_edit_crew")
def import_production_crew(production_id):
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


@production_bp.route("/api/productions/<production_id>/crew/<crew_id>", methods=["DELETE"])
@require_auth
@require_production_role(capability="can_edit_crew", resolver=from_crew_id)
def remove_production_crew(production_id, crew_id):
    crew_svc.remove_crew(production_id, crew_id)
    return jsonify({"success": True})
```

> `from_crew_id` resolves the production from the crew row; when `crew_id` doesn't exist it returns `None` → the decorator answers 404, which matches the old `not_found` behavior for PATCH.

- [ ] **Step 5: Run the full crew test file**

Run: `cd backend && python -m pytest tests/test_production_crew_routes.py -v`
Expected: PASS. The pre-existing owner-path tests still pass (owner → `can_view_sensitive=True`, no redaction). If any 2a test asserted an exact response with `job_rate` present as owner, it still holds.

- [ ] **Step 6: Commit**

```bash
git add backend/services/production_crew_service.py backend/routes/production_routes.py backend/tests/test_production_crew_routes.py
git commit -m "feat(crew): re-gate crew routes to production roles + redact sensitive fields"
```

---

## Task 5: `_fetch_seats_used` — count production members + pending invites

**Files:**
- Modify: `backend/services/entitlement_service.py:78-125` (`_fetch_seats_used`)
- Test: `backend/tests/test_entitlement_service.py` (extend)

**Interfaces:**
- Consumes: `get_supabase_admin()` (already imported in the module).
- Produces: `_fetch_seats_used(owner_id)` now also adds, before the existing dedup: accepted `production_members.user_id` for the owner's productions, and pending unexpired `production_invites.email` for those productions.

- [ ] **Step 1: Write the failing tests (append to test_entitlement_service.py)**

Match the existing test style in that file (inspect it first for the MockSupabase / patch helper it already uses). Add:

```python
def test_seats_used_counts_production_member(monkeypatch):
    store = _seat_store(  # helper already in this file; see existing tests
        profiles=[{"id": "owner", "email": "o@x.com"}],
        account_seats=[{"owner_id": "owner", "seats_granted": 5, "term_expires_at": _future()}],
        script_members=[],
        script_invites=[],
        productions=[{"id": "p1", "owner_id": "owner"}],
        production_members=[{"production_id": "p1", "user_id": "u-lp", "role": "admin"}],
        production_invites=[],
    )
    _patch_seats(monkeypatch, store)
    assert es._fetch_seats_used("owner") == 1


def test_seats_used_dedupes_person_across_both_systems(monkeypatch):
    store = _seat_store(
        profiles=[{"id": "u-both", "email": "both@x.com"}],
        account_seats=[{"owner_id": "owner", "seats_granted": 5, "term_expires_at": _future()}],
        script_members=[{"user_id": "u-both", "invited_by": "owner"}],
        script_invites=[],
        productions=[{"id": "p1", "owner_id": "owner"}],
        production_members=[{"production_id": "p1", "user_id": "u-both", "role": "viewer"}],
        production_invites=[],
    )
    _patch_seats(monkeypatch, store)
    assert es._fetch_seats_used("owner") == 1


def test_seats_used_counts_pending_production_invite(monkeypatch):
    store = _seat_store(
        profiles=[],
        account_seats=[{"owner_id": "owner", "seats_granted": 5, "term_expires_at": _future()}],
        script_members=[],
        script_invites=[],
        productions=[{"id": "p1", "owner_id": "owner"}],
        production_members=[],
        production_invites=[{"production_id": "p1", "email": "new@x.com",
                            "status": "pending", "expires_at": _future()}],
    )
    _patch_seats(monkeypatch, store)
    assert es._fetch_seats_used("owner") == 1


def test_seats_used_ignores_other_owners_production_members(monkeypatch):
    store = _seat_store(
        profiles=[],
        account_seats=[{"owner_id": "owner", "seats_granted": 5, "term_expires_at": _future()}],
        script_members=[], script_invites=[],
        productions=[{"id": "p9", "owner_id": "someone-else"}],
        production_members=[{"production_id": "p9", "user_id": "u-x", "role": "admin"}],
        production_invites=[],
    )
    _patch_seats(monkeypatch, store)
    assert es._fetch_seats_used("owner") == 0
```

> **Implementer:** the exact names `_seat_store`, `_patch_seats`, `_future` above are placeholders for whatever helpers `test_entitlement_service.py` already defines for its seat tests. Read the file first and reuse its real helpers / MockSupabase; if it builds stores inline, follow that. The MockSupabase in that file must support `.in_()` (it is used by `_fetch_seats_used` already for `profiles`).

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_entitlement_service.py -v -k "production"`
Expected: FAIL — production members/invites not counted.

- [ ] **Step 3: Extend `_fetch_seats_used`**

Insert, after the `pending_emails` set is built from `script_invites` and before the `if not pending_emails:` early return:

```python
    # --- Production axis: fold members + pending invites into the same tally.
    prod_resp = admin.table('productions').select('id').eq('owner_id', owner_id).execute()
    prod_ids = [row['id'] for row in (prod_resp.data or [])]
    if prod_ids:
        pm_resp = admin.table('production_members').select('user_id').in_(
            'production_id', prod_ids
        ).execute()
        accepted_ids |= {row['user_id'] for row in (pm_resp.data or []) if row.get('user_id')}

        pi_resp = admin.table('production_invites').select('email, status, expires_at').in_(
            'production_id', prod_ids
        ).eq('status', 'pending').gt('expires_at', now).execute()
        pending_emails |= {
            row['email'].strip().lower()
            for row in (pi_resp.data or []) if row.get('email')
        }
```

Update the docstring's first paragraph to note the production axis is now included.

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_entitlement_service.py -v`
Expected: PASS (new + all existing seat tests).

- [ ] **Step 5: Commit**

```bash
git add backend/services/entitlement_service.py backend/tests/test_entitlement_service.py
git commit -m "feat(seats): count production members + pending invites in _fetch_seats_used"
```

---

## Task 6: production_member_service.py — presets, rank guardrail, list

**Files:**
- Create: `backend/services/production_member_service.py`
- Test: `backend/tests/test_production_member_routes.py` (create — unit portion)

**Interfaces:**
- Consumes: `db.supabase_client.get_supabase_admin`; `middleware.production_authz.ROLE_RANK`, `CAPABILITIES`.
- Produces:
  - `ROLE_PRESETS: dict[str, dict]` — `{'admin': {all True}, 'coordinator': {'can_edit_crew': True, ...False}, 'viewer': {all False}}`
  - `apply_role_preset(role, overrides: dict | None) -> dict` — the four flags, preset defaults overridden by any explicit key in `overrides`
  - `rank_ok(actor_access: dict, target_role: str, new_flags: dict) -> bool` — actor may set `target_role` only if `ROLE_RANK[target_role] < ROLE_RANK[actor_access['role']]` (owner unrestricted), and may only grant a flag the actor holds
  - `list_members_and_invites(production_id) -> {'members': [...], 'invites': [...]}` — members with `name`/`email` joined from `profiles`; invites only `status='pending'`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_production_member_routes.py` (start with the unit tests; route tests come in Tasks 7–8):

```python
"""Production member + invite tests.

MockTable / MockSupabase are the chainable in-memory stand-in shared across
the production suite (copied from test_production_crew_routes.py).
"""
import os, sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.production_member_service as pms
from middleware.auth import DEV_USER_ID

# --- paste MockTable / MockSupabase / _ilike_match / _or_match verbatim from
#     tests/test_production_crew_routes.py ---


def _patch(monkeypatch, store):
    mock = MockSupabase(store)
    monkeypatch.setattr(pms, "get_supabase_admin", lambda: mock)
    return mock


def test_apply_role_preset_admin():
    assert pms.apply_role_preset("admin", None) == {
        "can_view_sensitive": True, "can_edit_crew": True,
        "can_manage_members": True, "can_edit_production": True}


def test_apply_role_preset_coordinator():
    assert pms.apply_role_preset("coordinator", None) == {
        "can_view_sensitive": False, "can_edit_crew": True,
        "can_manage_members": False, "can_edit_production": False}


def test_apply_role_preset_with_override():
    out = pms.apply_role_preset("coordinator", {"can_view_sensitive": True})
    assert out["can_view_sensitive"] is True and out["can_edit_crew"] is True


def test_rank_ok_owner_can_anything():
    owner = {"role": "owner", "can_manage_members": True, "can_edit_crew": True,
             "can_view_sensitive": True, "can_edit_production": True}
    assert pms.rank_ok(owner, "admin", pms.apply_role_preset("admin", None)) is True


def test_rank_ok_admin_cannot_create_admin():
    admin = {"role": "admin", "can_manage_members": True, "can_edit_crew": True,
             "can_view_sensitive": True, "can_edit_production": True}
    assert pms.rank_ok(admin, "admin", pms.apply_role_preset("admin", None)) is False


def test_rank_ok_admin_can_create_coordinator():
    admin = {"role": "admin", "can_manage_members": True, "can_edit_crew": True,
             "can_view_sensitive": True, "can_edit_production": True}
    assert pms.rank_ok(admin, "coordinator", pms.apply_role_preset("coordinator", None)) is True


def test_rank_ok_actor_cannot_grant_flag_they_lack():
    admin_no_manage = {"role": "admin", "can_manage_members": False, "can_edit_crew": True,
                       "can_view_sensitive": True, "can_edit_production": True}
    flags = pms.apply_role_preset("coordinator", {"can_manage_members": True})
    assert pms.rank_ok(admin_no_manage, "coordinator", flags) is False


def test_list_members_joins_profile_name(monkeypatch):
    _patch(monkeypatch, {
        "production_members": [{"id": "m1", "production_id": "p1", "user_id": "u1",
                               "role": "coordinator", "can_view_sensitive": False,
                               "can_edit_crew": True, "can_manage_members": False,
                               "can_edit_production": False}],
        "profiles": [{"id": "u1", "full_name": "Lee Producer", "email": "lee@x.com"}],
        "production_invites": [{"id": "i1", "production_id": "p1", "email": "new@x.com",
                              "role": "viewer", "status": "pending", "expires_at": "2099-01-01"}],
    })
    out = pms.list_members_and_invites("p1")
    assert out["members"][0]["name"] == "Lee Producer"
    assert out["members"][0]["email"] == "lee@x.com"
    assert len(out["invites"]) == 1 and out["invites"][0]["email"] == "new@x.com"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_production_member_routes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.production_member_service'`

- [ ] **Step 3: Write the implementation**

Create `backend/services/production_member_service.py`:

```python
"""
Production membership + invite lifecycle (build-sequence step 2b).

A production_members row grants production-level access only (crew now;
locations / schedule / call sheets / DPR later). It grants ZERO script
access. Enforcement is app-layer via middleware/production_authz.py; this
module is the data logic the routes call.
"""
from datetime import datetime, timedelta, timezone

from db.supabase_client import get_supabase_admin
from middleware.production_authz import ROLE_RANK, CAPABILITIES

ROLE_PRESETS = {
    'admin':       {c: True for c in CAPABILITIES},
    'coordinator': {'can_view_sensitive': False, 'can_edit_crew': True,
                    'can_manage_members': False, 'can_edit_production': False},
    'viewer':      {c: False for c in CAPABILITIES},
}


def apply_role_preset(role, overrides):
    flags = dict(ROLE_PRESETS[role])
    for c in CAPABILITIES:
        if overrides and c in overrides and overrides[c] is not None:
            flags[c] = bool(overrides[c])
    return flags


def rank_ok(actor_access, target_role, new_flags):
    """The actor may assign `target_role` + `new_flags` only if:
    - actor is owner (unrestricted), OR
    - target_role ranks strictly below the actor's role, AND
    - every flag being granted is one the actor themselves holds.
    """
    if actor_access['role'] == 'owner':
        return True
    if ROLE_RANK[target_role] >= ROLE_RANK[actor_access['role']]:
        return False
    for c in CAPABILITIES:
        if new_flags.get(c) and not actor_access.get(c):
            return False
    return True


def _profiles_by_id(supabase, ids):
    if not ids:
        return {}
    rows = (supabase.table('profiles').select('id, full_name, email')
            .in_('id', list(ids)).execute().data or [])
    return {r['id']: r for r in rows}


def _member_view(row, profile):
    profile = profile or {}
    return {
        'id': row['id'],
        'user_id': row['user_id'],
        'name': profile.get('full_name') or profile.get('email') or 'Unknown',
        'email': profile.get('email'),
        'role': row['role'],
        **{c: bool(row.get(c)) for c in CAPABILITIES},
        'created_at': row.get('created_at'),
    }


def _invite_view(row):
    return {
        'id': row['id'],
        'email': row['email'],
        'role': row['role'],
        **{c: bool(row.get(c)) for c in CAPABILITIES},
        'expires_at': row.get('expires_at'),
        'created_at': row.get('created_at'),
    }


def list_members_and_invites(production_id):
    supabase = get_supabase_admin()
    members = (supabase.table('production_members').select('*')
               .eq('production_id', production_id).execute().data or [])
    profiles = _profiles_by_id(supabase, {m['user_id'] for m in members})
    invites = (supabase.table('production_invites').select('*')
               .eq('production_id', production_id).eq('status', 'pending')
               .execute().data or [])
    return {
        'members': [_member_view(m, profiles.get(m['user_id'])) for m in members],
        'invites': [_invite_view(i) for i in invites],
    }
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_production_member_routes.py -v`
Expected: PASS (unit tests).

- [ ] **Step 5: Commit**

```bash
git add backend/services/production_member_service.py backend/tests/test_production_member_routes.py
git commit -m "feat(members): production_member_service presets + rank guardrail + list"
```

---

## Task 7: Member routes — GET / POST / PATCH / DELETE members

**Files:**
- Modify: `backend/services/production_member_service.py` (add `add_member`, `update_member`, `remove_member`)
- Modify: `backend/routes/production_routes.py` (add 4 routes)
- Modify: `backend/services/email_service.py` (add `send_production_member_added`)
- Test: `backend/tests/test_production_member_routes.py` (extend)

**Interfaces:**
- Consumes: `require_production_role`, `from_member_id` (Task 3); `apply_role_preset`, `rank_ok`, `list_members_and_invites` (Task 6); `entitlement_service.get_entitlement`.
- Produces:
  - `add_member(production_id, actor_access, fields) -> {'member': dict} | {'invite': dict} | ('error', code, http_status)` — `code` ∈ `{'tier_2_required','no_seats_available','bad_role','rank_denied','duplicate_member','duplicate_invite'}`
  - `update_member(production_id, member_id, actor_access, fields) -> {'member': dict} | ('error', code, status)` — codes `{'not_found','bad_role','rank_denied'}`
  - `remove_member(production_id, member_id, actor_access) -> 'ok' | ('error', code, status)` — codes `{'rank_denied'}`; missing row → `'ok'` (no-op)
  - `email_service.send_production_member_added(to_email, inviter_name, production_title, role, production_url) -> dict`

- [ ] **Step 1: Write the failing tests (append)**

```python
import routes.production_routes as pr  # noqa


def _client():
    from flask import Flask
    from routes.production_routes import production_bp
    app = Flask(__name__); app.config["TESTING"] = True
    app.register_blueprint(production_bp)
    return app.test_client()


def _rt_patch(monkeypatch, store):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    mock = MockSupabase(store)
    monkeypatch.setattr(pms, "get_supabase_admin", lambda: mock)
    monkeypatch.setattr("middleware.production_authz.get_supabase_admin", lambda: mock)
    monkeypatch.setattr("middleware.production_authz.get_user_id", lambda: DEV_USER_ID)
    monkeypatch.setattr("services.production_service.get_supabase_admin", lambda: mock)
    # owner is Tier-2 active with spare seats unless a test overrides
    monkeypatch.setattr(pms, "get_entitlement", lambda uid: {
        "can_use_teams": True, "seats_used": 0, "seats_paid": 10})
    monkeypatch.setattr("services.email_service.is_configured", lambda: False)


def _owned_store(**ov):
    base = {"productions": [{"id": "p1", "owner_id": DEV_USER_ID, "title": "Farm Feature"}],
            "production_members": [], "production_invites": [],
            "profiles": [{"id": DEV_USER_ID, "full_name": "Owner", "email": "dev@example.com"}],
            "notifications": []}
    base.update(ov)
    return base


def test_get_members_requires_membership(monkeypatch):
    _rt_patch(monkeypatch, {"productions": [{"id": "p1", "owner_id": "other"}],
                            "production_members": [], "production_invites": [], "profiles": []})
    assert _client().get("/api/productions/p1/members").status_code == 403


def test_get_members_owner_ok(monkeypatch):
    _rt_patch(monkeypatch, _owned_store())
    r = _client().get("/api/productions/p1/members")
    assert r.status_code == 200 and r.get_json() == {"members": [], "invites": []}


def test_add_member_existing_account_is_immediate(monkeypatch):
    store = _owned_store(profiles=[
        {"id": DEV_USER_ID, "full_name": "Owner", "email": "dev@example.com"},
        {"id": "u-lee", "full_name": "Lee", "email": "lee@x.com"}])
    _rt_patch(monkeypatch, store)
    r = _client().post("/api/productions/p1/members",
                       json={"email": "lee@x.com", "role": "coordinator"})
    assert r.status_code == 201
    assert r.get_json()["member"]["role"] == "coordinator"
    assert store["production_members"][0]["user_id"] == "u-lee"
    assert store["production_members"][0]["can_edit_crew"] is True
    assert store["production_invites"] == []


def test_add_member_unknown_email_creates_pending_invite(monkeypatch):
    store = _owned_store()
    _rt_patch(monkeypatch, store)
    r = _client().post("/api/productions/p1/members",
                       json={"email": "stranger@x.com", "role": "viewer"})
    assert r.status_code == 201
    assert r.get_json()["invite"]["email"] == "stranger@x.com"
    assert store["production_invites"][0]["status"] == "pending"
    assert store["production_invites"][0]["token"]


def test_add_member_duplicate_is_409(monkeypatch):
    store = _owned_store(
        profiles=[{"id": DEV_USER_ID, "email": "dev@example.com"},
                  {"id": "u-lee", "email": "lee@x.com"}],
        production_members=[{"id": "m1", "production_id": "p1", "user_id": "u-lee", "role": "viewer"}])
    _rt_patch(monkeypatch, store)
    r = _client().post("/api/productions/p1/members", json={"email": "lee@x.com", "role": "viewer"})
    assert r.status_code == 409


def test_add_member_override_persists(monkeypatch):
    store = _owned_store(profiles=[{"id": DEV_USER_ID, "email": "dev@example.com"},
                                   {"id": "u-lee", "email": "lee@x.com"}])
    _rt_patch(monkeypatch, store)
    _client().post("/api/productions/p1/members",
                   json={"email": "lee@x.com", "role": "coordinator", "can_view_sensitive": True})
    assert store["production_members"][0]["can_view_sensitive"] is True


def test_add_member_owner_not_tier2_is_403(monkeypatch):
    store = _owned_store(profiles=[{"id": DEV_USER_ID, "email": "dev@example.com"},
                                   {"id": "u-lee", "email": "lee@x.com"}])
    _rt_patch(monkeypatch, store)
    monkeypatch.setattr(pms, "get_entitlement", lambda uid: {
        "can_use_teams": False, "seats_used": 0, "seats_paid": 10})
    r = _client().post("/api/productions/p1/members", json={"email": "lee@x.com", "role": "viewer"})
    assert r.status_code == 403 and r.get_json()["code"] == "tier_2_required"


def test_add_member_no_seats_is_402(monkeypatch):
    store = _owned_store(profiles=[{"id": DEV_USER_ID, "email": "dev@example.com"},
                                   {"id": "u-lee", "email": "lee@x.com"}])
    _rt_patch(monkeypatch, store)
    monkeypatch.setattr(pms, "get_entitlement", lambda uid: {
        "can_use_teams": True, "seats_used": 10, "seats_paid": 10})
    r = _client().post("/api/productions/p1/members", json={"email": "lee@x.com", "role": "viewer"})
    assert r.status_code == 402 and r.get_json()["code"] == "no_seats_available"


def test_admin_member_cannot_create_admin(monkeypatch):
    store = {"productions": [{"id": "p1", "owner_id": "other", "title": "T"}],
             "production_members": [{"id": "m1", "production_id": "p1", "user_id": DEV_USER_ID,
                                     "role": "admin", "can_manage_members": True, "can_edit_crew": True,
                                     "can_view_sensitive": True, "can_edit_production": True}],
             "production_invites": [],
             "profiles": [{"id": DEV_USER_ID, "email": "dev@example.com"},
                          {"id": "u-x", "email": "x@x.com"}],
             "notifications": []}
    _rt_patch(monkeypatch, store)
    r = _client().post("/api/productions/p1/members", json={"email": "x@x.com", "role": "admin"})
    assert r.status_code == 403 and r.get_json()["code"] == "rank_denied"


def test_patch_member_role(monkeypatch):
    store = _owned_store(production_members=[
        {"id": "m1", "production_id": "p1", "user_id": "u-lee", "role": "viewer",
         "can_view_sensitive": False, "can_edit_crew": False,
         "can_manage_members": False, "can_edit_production": False}],
        profiles=[{"id": DEV_USER_ID, "email": "dev@example.com"},
                  {"id": "u-lee", "email": "lee@x.com"}])
    _rt_patch(monkeypatch, store)
    r = _client().patch("/api/productions/p1/members/m1",
                        json={"role": "coordinator", "can_edit_crew": True})
    assert r.status_code == 200
    assert store["production_members"][0]["role"] == "coordinator"
    assert store["production_members"][0]["can_edit_crew"] is True


def test_delete_member(monkeypatch):
    store = _owned_store(production_members=[
        {"id": "m1", "production_id": "p1", "user_id": "u-lee", "role": "viewer"}],
        profiles=[{"id": DEV_USER_ID, "email": "dev@example.com"}])
    _rt_patch(monkeypatch, store)
    assert _client().delete("/api/productions/p1/members/m1").status_code == 200
    assert store["production_members"] == []


def test_delete_missing_member_is_noop_200(monkeypatch):
    _rt_patch(monkeypatch, _owned_store())
    assert _client().delete("/api/productions/p1/members/nope").status_code == 200
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_production_member_routes.py -v -k "member"`
Expected: FAIL — routes/service functions don't exist.

- [ ] **Step 3: Add `send_production_member_added` to email_service.py**

Follow `send_team_invite`'s structure (HTML-escape inputs, `APP_URL` prefix check on `production_url`, header-injection strip on subject). Minimal:

```python
def send_production_member_added(
    to_email: str,
    inviter_name: str,
    production_title: str,
    role: str,
    production_url: str,
) -> Dict[str, Any]:
    """Notify an existing account that they were added to a production."""
    import html as _html
    safe_name = _html.escape(inviter_name or 'A teammate')
    safe_title = _html.escape(production_title or 'Untitled')
    safe_role = _html.escape(role or '')
    if not production_url or not production_url.startswith(APP_URL):
        return {'error': 'Invalid production URL'}
    safe_url = _html.escape(production_url, quote=True)
    subject = f"🎬 {inviter_name} added you to {production_title}".replace('\r', ' ').replace('\n', ' ')
    html = f"""<!DOCTYPE html><html><body>
      <p>{safe_name} added you to <strong>{safe_title}</strong> as {safe_role}.</p>
      <p><a href="{safe_url}">Open the production</a></p>
    </body></html>"""
    return _send(to_email, subject, html)  # use whatever the module's internal send helper is named
```

> **Implementer:** inspect `email_service.py` for the actual internal send primitive (`_send` / `send_email` / a Resend call) and the `APP_URL` constant name; match `send_team_invite` exactly. Also add `send_production_invite` here now (used in Task 8) with the same shape but pointing at `{FRONTEND}/production-invites/{token}` and subject "invited you to collaborate on".

- [ ] **Step 4: Add the service functions to production_member_service.py**

```python
import secrets

from services.production_service import _get_production
from services.entitlement_service import get_entitlement


def _generate_token():
    return secrets.token_urlsafe(32)


def _owner_id(supabase, production_id):
    prod = _get_production(supabase, production_id)
    return prod.get('owner_id') if prod else None


def add_member(production_id, actor_access, fields):
    supabase = get_supabase_admin()
    email = (fields.get('email') or '').strip().lower()
    role = fields.get('role')
    if not email:
        return ('error', 'bad_email', 400)
    if role not in ROLE_PRESETS:
        return ('error', 'bad_role', 400)

    flags = apply_role_preset(role, fields)
    if not rank_ok(actor_access, role, flags):
        return ('error', 'rank_denied', 403)

    # Entitlement gate — keyed to the PRODUCTION OWNER, not the caller.
    owner_id = _owner_id(supabase, production_id)
    ent = get_entitlement(owner_id)
    if not ent.get('can_use_teams'):
        return ('error', 'tier_2_required', 403)
    if ent.get('seats_used', 0) >= ent.get('seats_paid', 0):
        return ('error', 'no_seats_available', 402)

    actor_uid = _dev_actor_uid()  # see note

    # Existing account?
    prof = (supabase.table('profiles').select('id, email')
            .ilike('email', email).limit(1).execute().data or [])
    if prof:
        target_uid = prof[0]['id']
        dupe = (supabase.table('production_members').select('id')
                .eq('production_id', production_id).eq('user_id', target_uid)
                .limit(1).execute().data or [])
        if dupe:
            return ('error', 'duplicate_member', 409)
        row = supabase.table('production_members').insert({
            'production_id': production_id, 'user_id': target_uid, 'role': role,
            'invited_by': actor_uid, **flags,
        }).execute().data[0]
        _notify_member_added(supabase, production_id, target_uid, role)
        profiles = _profiles_by_id(supabase, {target_uid})
        return {'member': _member_view(row, profiles.get(target_uid))}

    # Unknown email → pending invite
    pending = (supabase.table('production_invites').select('id')
               .eq('production_id', production_id).eq('status', 'pending')
               .ilike('email', email).limit(1).execute().data or [])
    if pending:
        return ('error', 'duplicate_invite', 409)
    expires = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    inv = supabase.table('production_invites').insert({
        'production_id': production_id, 'email': email, 'role': role,
        'token': _generate_token(), 'status': 'pending', 'invited_by': actor_uid,
        'expires_at': expires, **flags,
    }).execute().data[0]
    _send_invite_email(supabase, production_id, inv)
    return {'invite': _invite_view(inv)}


def update_member(production_id, member_id, actor_access, fields):
    supabase = get_supabase_admin()
    row = (supabase.table('production_members').select('*')
           .eq('id', member_id).eq('production_id', production_id)
           .limit(1).execute().data or [])
    if not row:
        return ('error', 'not_found', 404)
    current = row[0]
    new_role = fields.get('role', current['role'])
    if new_role not in ROLE_PRESETS:
        return ('error', 'bad_role', 400)
    # Start from the member's current flags, apply any explicit overrides.
    merged = {c: bool(fields[c]) if c in fields and fields[c] is not None
              else bool(current.get(c)) for c in CAPABILITIES}
    # Guard against the current role AND the new role, and the resulting flags.
    if not rank_ok(actor_access, current['role'], {}) or not rank_ok(actor_access, new_role, merged):
        return ('error', 'rank_denied', 403)
    supabase.table('production_members').update(
        {'role': new_role, **merged}).eq('id', member_id).execute()
    updated = (supabase.table('production_members').select('*')
               .eq('id', member_id).limit(1).execute().data[0])
    profiles = _profiles_by_id(supabase, {updated['user_id']})
    return {'member': _member_view(updated, profiles.get(updated['user_id']))}


def remove_member(production_id, member_id, actor_access):
    supabase = get_supabase_admin()
    row = (supabase.table('production_members').select('*')
           .eq('id', member_id).eq('production_id', production_id)
           .limit(1).execute().data or [])
    if not row:
        return 'ok'  # no-op, mirrors remove_script
    if not rank_ok(actor_access, row[0]['role'], {}):
        return ('error', 'rank_denied', 403)
    supabase.table('production_members').delete().eq('id', member_id).execute()
    return 'ok'
```

Helpers (also in this module):

```python
import os
from flask import g


def _dev_actor_uid():
    """The acting user id — g may not be populated in unit calls, fall back to DEV."""
    try:
        return g.current_user.get('sub')
    except Exception:
        return os.getenv('DEV_USER_ID', '00000000-0000-0000-0000-000000000001')


def _notify_member_added(supabase, production_id, target_uid, role):
    prod = _get_production(supabase, production_id)
    title = (prod or {}).get('title', 'a production')
    try:
        supabase.table('notifications').insert({
            'user_id': target_uid,
            'type': 'production_member_added',
            'title': 'Added to a production',
            'message': f'You were added to "{title}" as {role}',
            'data': {'production_id': production_id, 'role': role},
        }).execute()
    except Exception as e:
        print(f"Warning: production member-added notification failed: {e}")
    _maybe_email_member_added(supabase, production_id, target_uid, role, title)


def _maybe_email_member_added(supabase, production_id, target_uid, role, title):
    from services import email_service
    if not email_service.is_configured():
        return
    prof = (supabase.table('profiles').select('email')
            .eq('id', target_uid).limit(1).execute().data or [])
    if not prof or not prof[0].get('email'):
        return
    frontend = os.getenv('FRONTEND_URL', 'http://localhost:5173')
    try:
        email_service.send_production_member_added(
            to_email=prof[0]['email'], inviter_name='A teammate',
            production_title=title, role=role,
            production_url=f"{frontend}/productions/{production_id}")
    except Exception as e:
        print(f"Warning: production member-added email failed: {e}")


def _send_invite_email(supabase, production_id, inv):
    from services import email_service
    if not email_service.is_configured():
        return
    prod = _get_production(supabase, production_id)
    title = (prod or {}).get('title', 'a production')
    frontend = os.getenv('FRONTEND_URL', 'http://localhost:5173')
    try:
        email_service.send_production_invite(
            to_email=inv['email'], inviter_name='A teammate',
            production_title=title, role=inv['role'],
            invite_url=f"{frontend}/production-invites/{inv['token']}")
    except Exception as e:
        print(f"Warning: production invite email failed: {e}")
```

> **Implementer:** `email_service.is_configured` is imported in `invite_routes.py` as `is_configured as email_configured` — confirm the real export name. `_dev_actor_uid` is a pragmatic shim; if the routes already have `get_user_id()` handy, prefer passing `actor_uid` into `add_member` explicitly instead. Keep it simple — pass `get_user_id()` from the route.

**Simplification:** change the service signatures to take `actor_uid` explicitly:
`add_member(production_id, actor_uid, actor_access, fields)` etc. Drop `_dev_actor_uid`. The route passes `get_user_id()`.

- [ ] **Step 5: Add the routes to production_routes.py**

```python
from middleware.production_authz import (
    require_production_role, from_crew_id, from_member_id, from_production_invite_id,
)
from services import production_member_service as member_svc

_ERR_STATUS = {'bad_email': 400, 'bad_role': 400, 'rank_denied': 403,
               'tier_2_required': 403, 'no_seats_available': 402,
               'duplicate_member': 409, 'duplicate_invite': 409, 'not_found': 404}
_ERR_CODE = {'rank_denied': 'rank_denied', 'tier_2_required': 'tier_2_required',
             'no_seats_available': 'no_seats_available'}


def _member_error(result):
    _, code, status = result
    body = {'error': code}
    if code in _ERR_CODE:
        body['code'] = _ERR_CODE[code]
    return jsonify(body), status


@production_bp.route("/api/productions/<production_id>/members", methods=["GET"])
@require_auth
@require_production_role(min_role="viewer")
def list_production_members(production_id):
    return jsonify(member_svc.list_members_and_invites(production_id))


@production_bp.route("/api/productions/<production_id>/members", methods=["POST"])
@require_auth
@require_production_role(capability="can_manage_members")
def add_production_member(production_id):
    data = request.get_json(silent=True) or {}
    result = member_svc.add_member(production_id, get_user_id(), g.production_access, data)
    if isinstance(result, tuple):
        return _member_error(result)
    return jsonify(result), 201


@production_bp.route("/api/productions/<production_id>/members/<member_id>", methods=["PATCH"])
@require_auth
@require_production_role(capability="can_manage_members", resolver=from_member_id)
def update_production_member(production_id, member_id):
    data = request.get_json(silent=True) or {}
    result = member_svc.update_member(production_id, member_id, g.production_access, data)
    if isinstance(result, tuple):
        return _member_error(result)
    return jsonify(result)


@production_bp.route("/api/productions/<production_id>/members/<member_id>", methods=["DELETE"])
@require_auth
@require_production_role(capability="can_manage_members", resolver=from_member_id)
def remove_production_member(production_id, member_id):
    result = member_svc.remove_member(production_id, member_id, g.production_access)
    if isinstance(result, tuple):
        return _member_error(result)
    return jsonify({"success": True})
```

> `from_member_id` resolves the production from the member row, so a `member_id` on the wrong production → `None` → 404 (matches `not_found`). Update `add_member`/`update_member`/`remove_member` signatures to `(production_id, actor_uid, actor_access, fields)` per the Step 4 simplification.

- [ ] **Step 6: Run the tests**

Run: `cd backend && python -m pytest tests/test_production_member_routes.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/services/production_member_service.py backend/routes/production_routes.py backend/services/email_service.py backend/tests/test_production_member_routes.py
git commit -m "feat(members): add/update/remove member routes + immediate-vs-invite flow"
```

---

## Task 8: Invite routes — revoke, token lookup, accept

**Files:**
- Modify: `backend/services/production_member_service.py` (add `revoke_invite`, `get_invite_by_token`, `accept_invite`)
- Modify: `backend/routes/production_routes.py` (add 3 routes)
- Test: `backend/tests/test_production_member_routes.py` (extend)

**Interfaces:**
- Produces:
  - `revoke_invite(invite_id) -> 'ok'`
  - `get_invite_by_token(token) -> dict | None` — `{production_title, inviter_name, role, email, status, expired: bool}`
  - `accept_invite(token, user_id, user_email) -> {'production_id', 'already_member': bool} | ('error', code, status)` — codes `{'not_found','invite_expired','invite_revoked','email_mismatch'}`

- [ ] **Step 1: Write the failing tests (append)**

```python
def test_revoke_invite(monkeypatch):
    store = _owned_store(production_invites=[
        {"id": "i1", "production_id": "p1", "email": "x@x.com", "role": "viewer",
         "status": "pending", "expires_at": "2099-01-01"}])
    _rt_patch(monkeypatch, store)
    assert _client().delete("/api/production-invites/i1").status_code == 200
    assert store["production_invites"][0]["status"] == "revoked"


def test_get_invite_by_token_public(monkeypatch):
    store = _owned_store(production_invites=[
        {"id": "i1", "production_id": "p1", "email": "x@x.com", "role": "coordinator",
         "token": "tok1", "status": "pending", "expires_at": "2099-01-01"}])
    _rt_patch(monkeypatch, store)
    r = _client().get("/api/production-invites/token/tok1")
    assert r.status_code == 200
    assert r.get_json()["role"] == "coordinator"
    assert r.get_json()["production_title"] == "Farm Feature"


def test_accept_invite_email_mismatch(monkeypatch):
    store = _owned_store(production_invites=[
        {"id": "i1", "production_id": "p1", "email": "someone-else@x.com", "role": "viewer",
         "token": "tok1", "status": "pending", "expires_at": "2099-01-01"}])
    _rt_patch(monkeypatch, store)
    # DEV_MODE user email is dev@example.com
    r = _client().post("/api/production-invites/token/tok1/accept")
    assert r.status_code == 403 and r.get_json()["code"] == "email_mismatch"


def test_accept_invite_success(monkeypatch):
    store = _owned_store(production_invites=[
        {"id": "i1", "production_id": "p1", "email": "dev@example.com", "role": "coordinator",
         "can_view_sensitive": False, "can_edit_crew": True, "can_manage_members": False,
         "can_edit_production": False, "token": "tok1", "status": "pending",
         "expires_at": "2099-01-01", "invited_by": "owner"}])
    _rt_patch(monkeypatch, store)
    r = _client().post("/api/production-invites/token/tok1/accept")
    assert r.status_code == 200
    assert r.get_json()["production_id"] == "p1"
    assert store["production_members"][0]["user_id"] == DEV_USER_ID
    assert store["production_members"][0]["role"] == "coordinator"
    assert store["production_members"][0]["can_edit_crew"] is True
    assert store["production_invites"][0]["status"] == "accepted"


def test_accept_invite_already_member(monkeypatch):
    store = _owned_store(
        production_members=[{"id": "m1", "production_id": "p1", "user_id": DEV_USER_ID, "role": "viewer"}],
        production_invites=[{"id": "i1", "production_id": "p1", "email": "dev@example.com",
                            "role": "viewer", "token": "tok1", "status": "pending",
                            "expires_at": "2099-01-01"}])
    _rt_patch(monkeypatch, store)
    r = _client().post("/api/production-invites/token/tok1/accept")
    assert r.status_code == 200 and r.get_json()["already_member"] is True
    assert store["production_invites"][0]["status"] == "accepted"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_production_member_routes.py -v -k "invite"`
Expected: FAIL.

- [ ] **Step 3: Add service functions**

```python
def revoke_invite(invite_id):
    get_supabase_admin().table('production_invites').update(
        {'status': 'revoked'}).eq('id', invite_id).execute()
    return 'ok'


def get_invite_by_token(token):
    supabase = get_supabase_admin()
    rows = (supabase.table('production_invites').select('*')
            .eq('token', token).limit(1).execute().data or [])
    if not rows:
        return None
    inv = rows[0]
    prod = _get_production(supabase, inv['production_id'])
    inviter = None
    if inv.get('invited_by'):
        p = (supabase.table('profiles').select('full_name, email')
             .eq('id', inv['invited_by']).limit(1).execute().data or [])
        if p:
            inviter = p[0].get('full_name') or p[0].get('email')
    expired = False
    if inv.get('expires_at'):
        try:
            exp = datetime.fromisoformat(inv['expires_at'].replace('Z', '+00:00'))
            expired = exp < datetime.now(exp.tzinfo)
        except ValueError:
            pass
    return {
        'production_id': inv['production_id'],
        'production_title': (prod or {}).get('title', 'a production'),
        'inviter_name': inviter or 'A teammate',
        'role': inv['role'], 'email': inv['email'],
        'status': inv['status'], 'expired': expired,
    }


def accept_invite(token, user_id, user_email):
    supabase = get_supabase_admin()
    rows = (supabase.table('production_invites').select('*')
            .eq('token', token).limit(1).execute().data or [])
    if not rows:
        return ('error', 'not_found', 404)
    inv = rows[0]
    if (inv['email'] or '').lower() != (user_email or '').lower():
        return ('error', 'email_mismatch', 403)
    if inv['status'] == 'revoked':
        return ('error', 'invite_revoked', 403)
    if inv.get('expires_at'):
        try:
            exp = datetime.fromisoformat(inv['expires_at'].replace('Z', '+00:00'))
            if exp < datetime.now(exp.tzinfo):
                return ('error', 'invite_expired', 403)
        except ValueError:
            pass

    existing = (supabase.table('production_members').select('id')
                .eq('production_id', inv['production_id']).eq('user_id', user_id)
                .limit(1).execute().data or [])
    if existing:
        supabase.table('production_invites').update(
            {'status': 'accepted'}).eq('id', inv['id']).execute()
        return {'production_id': inv['production_id'], 'already_member': True}

    supabase.table('production_members').insert({
        'production_id': inv['production_id'], 'user_id': user_id, 'role': inv['role'],
        'invited_by': inv.get('invited_by'),
        **{c: bool(inv.get(c)) for c in CAPABILITIES},
    }).execute()
    supabase.table('production_invites').update(
        {'status': 'accepted'}).eq('id', inv['id']).execute()
    _notify_invite_accepted(supabase, inv, user_id)
    return {'production_id': inv['production_id'], 'already_member': False}


def _notify_invite_accepted(supabase, inv, user_id):
    if not inv.get('invited_by'):
        return
    prod = _get_production(supabase, inv['production_id'])
    title = (prod or {}).get('title', 'a production')
    try:
        supabase.table('notifications').insert({
            'user_id': inv['invited_by'],
            'type': 'production_invite_accepted',
            'title': 'Invite accepted',
            'message': f'Someone joined "{title}" as {inv["role"]}',
            'data': {'production_id': inv['production_id']},
        }).execute()
    except Exception as e:
        print(f"Warning: production invite-accepted notification failed: {e}")
```

- [ ] **Step 4: Add routes to production_routes.py**

```python
@production_bp.route("/api/production-invites/<invite_id>", methods=["DELETE"])
@require_auth
@require_production_role(capability="can_manage_members", resolver=from_production_invite_id)
def revoke_production_invite(invite_id):
    member_svc.revoke_invite(invite_id)
    return jsonify({"success": True})


@production_bp.route("/api/production-invites/token/<token>", methods=["GET"])
def get_production_invite(token):
    info = member_svc.get_invite_by_token(token)
    if not info:
        return jsonify({"error": "Invite not found"}), 404
    return jsonify(info)


@production_bp.route("/api/production-invites/token/<token>/accept", methods=["POST"])
@require_auth
def accept_production_invite(token):
    from flask import g as _g
    user_email = (_g.current_user or {}).get('email', '')
    result = member_svc.accept_invite(token, get_user_id(), user_email)
    if isinstance(result, tuple):
        _, code, status = result
        return jsonify({"error": code, "code": code}), status
    return jsonify(result)
```

> **Route ordering:** `/api/production-invites/token/<token>` must be registered before `/api/production-invites/<invite_id>` is matched for a literal `token` segment — Flask matches static vs. dynamic correctly here since `token/<token>` has a static `token` prefix, but keep the token routes above the `<invite_id>` route in the file for clarity.

- [ ] **Step 5: Run the tests**

Run: `cd backend && python -m pytest tests/test_production_member_routes.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/services/production_member_service.py backend/routes/production_routes.py backend/tests/test_production_member_routes.py
git commit -m "feat(members): production invite revoke / token lookup / accept"
```

---

## Task 9: auto-accept — apply pending production invites on login

**Files:**
- Modify: `backend/routes/invite_routes.py` (`auto_accept_pending_invites`, ~line 473-615)
- Test: `backend/tests/test_production_member_routes.py` (extend) OR `backend/tests/test_accept_invite.py`

**Interfaces:**
- Consumes: `production_member_service.accept_invite` (Task 8).
- Produces: `POST /api/invites/auto-accept` response gains a `productions_accepted: [production_id, ...]` list alongside the existing `accepted`.

- [ ] **Step 1: Write the failing test**

Add to `test_production_member_routes.py`:

```python
import routes.invite_routes as ir


def test_auto_accept_applies_pending_production_invites(monkeypatch):
    store = {
        "productions": [{"id": "p1", "owner_id": "owner", "title": "T"}],
        "production_members": [], "notifications": [],
        "production_invites": [{"id": "i1", "production_id": "p1", "email": "dev@example.com",
                               "role": "viewer", "token": "tk", "status": "pending",
                               "expires_at": "2099-01-01",
                               "can_view_sensitive": False, "can_edit_crew": False,
                               "can_manage_members": False, "can_edit_production": False}],
        "script_invites": [], "script_members": [], "profiles": [],
    }
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    mock = MockSupabase(store)
    monkeypatch.setattr(ir, "supabase", mock)
    monkeypatch.setattr(pms, "get_supabase_admin", lambda: mock)
    monkeypatch.setattr("services.production_service.get_supabase_admin", lambda: mock)

    from flask import Flask
    app = Flask(__name__); app.config["TESTING"] = True
    app.register_blueprint(ir.invite_bp)
    r = app.test_client().post("/api/invites/auto-accept")
    assert r.status_code == 200
    assert "p1" in r.get_json().get("productions_accepted", [])
    assert store["production_members"][0]["user_id"] == DEV_USER_ID
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_production_member_routes.py -v -k auto_accept`
Expected: FAIL — `productions_accepted` not in response.

- [ ] **Step 3: Extend `auto_accept_pending_invites`**

Just before the final `return jsonify({...})` in that handler, add:

```python
        # --- Production invites (build-sequence step 2b) ---
        productions_accepted = []
        try:
            from services import production_member_service as _pms
            prod_invites = supabase.table('production_invites').select('token').eq(
                'email', user_email).eq('status', 'pending').execute()
            for pi in (prod_invites.data or []):
                res = _pms.accept_invite(pi['token'], user_id, user_email)
                if not isinstance(res, tuple):
                    productions_accepted.append(res['production_id'])
        except Exception as e:
            print(f"Warning: production invite auto-accept failed: {e}")
```

And add `'productions_accepted': productions_accepted` to the response dict. If the early-return path (`if not result.data: return jsonify({'accepted': [], ...})`) is hit first, also run the production block there — simplest is to restructure so the production block runs unconditionally before any return. Move the `return jsonify({'accepted': [], 'message': 'No pending invites found'})` to instead fall through: change it to set `accepted = []` and continue.

- [ ] **Step 4: Run the tests**

Run: `cd backend && python -m pytest tests/test_production_member_routes.py tests/test_accept_invite.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/invite_routes.py backend/tests/test_production_member_routes.py
git commit -m "feat(members): auto-accept pending production invites on login"
```

---

## Task 10: production_service — production_access field + member-visible list

**Files:**
- Modify: `backend/services/production_service.py` (`get_production_for_viewer`, `list_productions`)
- Test: `backend/tests/test_production_routes.py` (extend)

**Interfaces:**
- Consumes: `middleware.production_authz.get_production_access`.
- Produces:
  - `get_production_for_viewer` result dict gains `production_access` (the dict from `get_production_access`, or `{'role': None, <4 flags>: False}` for a script-only read-through viewer).
  - `list_productions(user_id)` returns owned productions **and** productions the user has a `production_members` row on; each row carries `is_owner: bool` and (for member rows) `member_role: str`.

- [ ] **Step 1: Write the failing tests (append to test_production_routes.py)**

```python
def test_get_production_includes_production_access_for_owner(monkeypatch):
    store = _store(productions=[{"id": "p1", "owner_id": DEV_USER_ID, "title": "Mine"}])
    _patch(monkeypatch, store)  # use this file's existing _patch
    # also patch production_authz
    monkeypatch.setattr("middleware.production_authz.get_supabase_admin",
                        lambda: MockSupabase(store))
    body = _client().get("/api/productions/p1").get_json()
    assert body["production_access"]["role"] == "owner"
    assert body["production_access"]["can_edit_crew"] is True


def test_get_production_access_for_member(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": "other", "title": "Theirs"}],
        production_members=[{"production_id": "p1", "user_id": DEV_USER_ID,
                            "role": "coordinator", "can_view_sensitive": False,
                            "can_edit_crew": True, "can_manage_members": False,
                            "can_edit_production": False}],
    )
    _patch(monkeypatch, store)
    monkeypatch.setattr("middleware.production_authz.get_supabase_admin",
                        lambda: MockSupabase(store))
    body = _client().get("/api/productions/p1").get_json()
    assert body["production_access"]["role"] == "coordinator"
    assert body["is_owner"] is False


def test_list_productions_includes_member_productions(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID, "title": "Mine"},
                     {"id": "p2", "owner_id": "other", "title": "Member of"}],
        production_members=[{"production_id": "p2", "user_id": DEV_USER_ID, "role": "viewer"}],
    )
    _patch(monkeypatch, store)
    ids = {p["id"] for p in _client().get("/api/productions").get_json()["productions"]}
    assert ids == {"p1", "p2"}
```

> **Implementer:** check `test_production_routes.py`'s existing `_patch` — it likely patches `ps.get_supabase_admin` and `middleware.authorization.get_supabase_admin`. Add `middleware.production_authz.get_supabase_admin` to it so all three point at the same store, then the per-test extra `setattr` above isn't needed. Prefer fixing `_patch` once.

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_production_routes.py -v -k "production_access or member_productions"`
Expected: FAIL.

- [ ] **Step 3: Update `get_production_for_viewer`**

```python
from middleware.production_authz import get_production_access, PRODUCTION_NOT_FOUND, CAPABILITIES


def get_production_for_viewer(production_id, user_id):
    supabase = get_supabase_admin()
    prod = _get_production(supabase, production_id)
    if not prod:
        return NOT_FOUND
    is_owner = prod.get("owner_id") == user_id
    scripts = _accessible_scripts(supabase, production_id, user_id, is_owner)

    access = get_production_access(production_id, user_id)
    if access in (None, PRODUCTION_NOT_FOUND):
        access = {"role": None, **{c: False for c in CAPABILITIES}}

    if not is_owner and access["role"] is None and not scripts:
        return None  # exists, but caller has no way in
    return {"production": prod, "scripts": scripts,
            "is_owner": is_owner, "production_access": access}
```

- [ ] **Step 4: Update `list_productions`**

```python
def list_productions(user_id):
    supabase = get_supabase_admin()
    owned = (supabase.table("productions").select("*")
             .eq("owner_id", user_id).order("created_at", desc=True).execute().data or [])
    for p in owned:
        p["is_owner"] = True

    member_rows = (supabase.table("production_members").select("production_id, role")
                   .eq("user_id", user_id).execute().data or [])
    role_by_id = {r["production_id"]: r["role"] for r in member_rows}
    owned_ids = {p["id"] for p in owned}
    extra_ids = [pid for pid in role_by_id if pid not in owned_ids]
    extra = []
    if extra_ids:
        extra = (supabase.table("productions").select("*")
                 .in_("id", extra_ids).execute().data or [])
        for p in extra:
            p["is_owner"] = False
            p["member_role"] = role_by_id.get(p["id"])
    return owned + extra
```

- [ ] **Step 5: Run the tests**

Run: `cd backend && python -m pytest tests/test_production_routes.py tests/test_get_scripts_production_info.py -v`
Expected: PASS. (Existing `test_get_production_is_owner_false_for_script_member` still passes — `production_access.role` is `None` there, and the script read-through still returns the production.)

- [ ] **Step 6: Commit**

```bash
git add backend/services/production_service.py backend/tests/test_production_routes.py
git commit -m "feat(productions): production_access in GET-one + member-visible list"
```

---

## Task 11: route-enforcement regression test

**Files:**
- Modify: `backend/tests/test_route_enforcement.py`

**Interfaces:**
- Consumes: the `_authz_min_role` / `_authz_capability` markers set by `require_production_role` (Task 3).

- [ ] **Step 1: Write the failing test**

Add a new test function to `test_route_enforcement.py`:

```python
def test_production_scoped_routes_carry_authz_marker():
    """Every production_bp route keyed to a production (directly or via a
    child resource) must carry require_production_role — i.e. expose an
    _authz_min_role or _authz_capability marker on its view function."""
    from routes.production_routes import production_bp
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(production_bp)

    # Routes intentionally NOT production-role scoped:
    #  - create/list (no production yet / filters itself)
    #  - the public invite-token lookup + accept (token IS the credential)
    WHITELIST = {
        "production.create_production",
        "production.list_productions",
        "production.get_production_invite",
        "production.accept_production_invite",
    }
    # Owner-only spine routes still use the inline _user_owns_production guard,
    # not the decorator — track them explicitly so this test documents them.
    INLINE_OWNER_GUARD = {
        "production.get_production",
        "production.update_production",
        "production.delete_production",
        "production.add_script_to_production",
        "production.remove_script_from_production",
    }

    SCOPED_ARGS = {"production_id", "crew_id", "member_id", "invite_id"}

    for rule in app.url_map.iter_rules():
        if not rule.endpoint.startswith("production."):
            continue
        if rule.endpoint in WHITELIST or rule.endpoint in INLINE_OWNER_GUARD:
            continue
        if not (set(rule.arguments) & SCOPED_ARGS):
            continue
        view = app.view_functions[rule.endpoint]
        assert hasattr(view, "_authz_min_role") or hasattr(view, "_authz_capability"), \
            f"{rule.endpoint} is production-scoped but has no require_production_role marker"
```

- [ ] **Step 2: Run it**

Run: `cd backend && python -m pytest tests/test_route_enforcement.py -v`
Expected: PASS (if every route from Tasks 4/7/8 is decorated). If it FAILS, it named a route missing the decorator — fix that route, not the test.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_route_enforcement.py
git commit -m "test: production-scoped routes must carry require_production_role"
```

- [ ] **Step 4: Full backend suite**

Run: `cd backend && python -m pytest tests/ -q`
Expected: PASS, no regressions.

---

## Task 12: apiService.js — member + invite functions

**Files:**
- Modify: `frontend/src/services/apiService.js` (after the step-2a crew functions, ~line 2620)

**Interfaces:**
- Produces (all `async`, all via the shared `api` axios instance):
  - `listProductionMembers(productionId) -> {members, invites}`
  - `addProductionMember(productionId, payload) -> {member} | {invite}` (payload: `{email, role, can_view_sensitive?, can_edit_crew?, can_manage_members?, can_edit_production?}`)
  - `updateProductionMember(productionId, memberId, payload) -> {member}`
  - `removeProductionMember(productionId, memberId) -> {success}`
  - `revokeProductionInvite(inviteId) -> {success}`
  - `getProductionInvite(token) -> {production_id, production_title, inviter_name, role, email, status, expired}`
  - `acceptProductionInvite(token) -> {production_id, already_member}`

- [ ] **Step 1: Add the functions**

```javascript
// Production members + invites (build-sequence step 2b)

export const listProductionMembers = async (productionId) => {
    try {
        const response = await api.get(`/api/productions/${productionId}/members`);
        return response.data;
    } catch (error) {
        console.error('Error listing production members:', error);
        throw error;
    }
};

export const addProductionMember = async (productionId, payload) => {
    try {
        const response = await api.post(`/api/productions/${productionId}/members`, payload);
        return response.data;
    } catch (error) {
        console.error('Error adding production member:', error);
        throw error;
    }
};

export const updateProductionMember = async (productionId, memberId, payload) => {
    try {
        const response = await api.patch(
            `/api/productions/${productionId}/members/${memberId}`, payload);
        return response.data;
    } catch (error) {
        console.error('Error updating production member:', error);
        throw error;
    }
};

export const removeProductionMember = async (productionId, memberId) => {
    try {
        const response = await api.delete(
            `/api/productions/${productionId}/members/${memberId}`);
        return response.data;
    } catch (error) {
        console.error('Error removing production member:', error);
        throw error;
    }
};

export const revokeProductionInvite = async (inviteId) => {
    try {
        const response = await api.delete(`/api/production-invites/${inviteId}`);
        return response.data;
    } catch (error) {
        console.error('Error revoking production invite:', error);
        throw error;
    }
};

export const getProductionInvite = async (token) => {
    try {
        const response = await api.get(`/api/production-invites/token/${token}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching production invite:', error);
        throw error;
    }
};

export const acceptProductionInvite = async (token) => {
    try {
        const response = await api.post(`/api/production-invites/token/${token}/accept`);
        return response.data;
    } catch (error) {
        console.error('Error accepting production invite:', error);
        throw error;
    }
};
```

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/apiService.js
git commit -m "feat(api): production member + invite client functions"
```

---

## Task 13: ProductionDetailPage — production_access wiring + Members tab

**Files:**
- Modify: `frontend/src/pages/ProductionDetailPage.jsx`

**Interfaces:**
- Consumes: `getProduction` now returns `production_access` (Task 10); `ProductionMembersTab` (Task 14 — create a stub first if executing strictly in order, or reorder 13↔14).
- Produces: page renders `production_access` into state; tab list is `Overview` + (`Crew` if member of any kind) + (`Members` if `can_manage_members || role === 'owner'`); Overview edit gated on `can_edit_production`.

- [ ] **Step 1: Rewrite the component**

```jsx
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import {
    getProduction, updateProduction, deleteProduction,
    addScriptToProduction, removeScriptFromProduction,
} from '../services/apiService';
import { Spinner } from '../components/ui';
import ProductionOverviewTab from '../components/productions/ProductionOverviewTab';
import ProductionCrewTab from '../components/productions/ProductionCrewTab';
import ProductionMembersTab from '../components/productions/ProductionMembersTab';
import './ProductionPages.css';

const NO_ACCESS = {
    role: null, can_view_sensitive: false, can_edit_crew: false,
    can_manage_members: false, can_edit_production: false,
};

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
    const [access, setAccess] = useState(NO_ACCESS);
    const [activeTab, setActiveTab] = useState('overview');

    const isOwner = access.role === 'owner';
    const canManageMembers = isOwner || access.can_manage_members;
    const isMember = isOwner || access.role !== null;

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
                setAccess(data.production_access || NO_ACCESS);
            })
            .catch((err) => {
                if (err.response?.status === 403) setError('You can view this production but not edit it.');
                else setError(err.response?.data?.error || err.message || 'Failed to load production');
            })
            .finally(() => setLoading(false));
    }, [productionId]);

    useEffect(load, [load]);

    useEffect(() => {
        if (activeTab === 'crew' && !isMember) setActiveTab('overview');
        if (activeTab === 'members' && !canManageMembers) setActiveTab('overview');
    }, [activeTab, isMember, canManageMembers]);

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
            if (err.response?.status === 403) setError('You do not have permission to edit this.');
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
        try {
            await removeScriptFromProduction(productionId, scriptId);
            setScripts((prev) => prev.filter((s) => s.id !== scriptId));
            setError(null);
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Failed to remove script');
        }
    };

    if (loading) return <div className="production-page-loading"><Spinner size={32} /></div>;
    if (!production) return <p className="production-page-error">{error || 'Not found'}</p>;

    const tabs = [{ id: 'overview', label: 'Overview' }];
    if (isMember) tabs.push({ id: 'crew', label: 'Crew' });
    if (canManageMembers) tabs.push({ id: 'members', label: 'Members' });

    return (
        <div className="production-page">
            <Link to="/productions" className="production-back"><ArrowLeft size={16} /> Productions</Link>
            {error && <p className="production-page-error">{error}</p>}

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

            {activeTab === 'overview' && (
                <ProductionOverviewTab
                    production={production}
                    scripts={scripts}
                    form={form}
                    setForm={setForm}
                    isOwner={access.can_edit_production}
                    saving={saving}
                    onSave={save}
                    onDelete={handleDelete}
                    onPick={handlePick}
                    onRemove={handleRemove}
                    picking={picking}
                    setPicking={setPicking}
                />
            )}
            {activeTab === 'crew' && isMember && (
                <ProductionCrewTab productionId={productionId} access={access} />
            )}
            {activeTab === 'members' && canManageMembers && (
                <ProductionMembersTab productionId={productionId} access={access} />
            )}
        </div>
    );
}
```

> **Note:** `ProductionOverviewTab` receives `isOwner={access.can_edit_production}` — its prop name stays `isOwner` (no change to that component) but now means "can edit". The delete button inside Overview is only shown to a true owner; if `ProductionOverviewTab` shows delete whenever `isOwner`, pass an extra `canDelete={isOwner}` prop and gate the delete button on it. Check `ProductionOverviewTab.jsx` and adjust: delete → `canDelete`, everything else → `isOwner` (= can_edit_production).

- [ ] **Step 2: Adjust ProductionOverviewTab delete gating**

Open `frontend/src/components/productions/ProductionOverviewTab.jsx`. If it renders a delete button gated on `isOwner`, add a `canDelete` prop (default `false`) and gate the delete button on `canDelete` instead. In `ProductionDetailPage.jsx` pass `canDelete={isOwner}`.

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`
Expected: PASS (needs `ProductionMembersTab` to exist — do Task 14 first or create an empty default-export stub).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ProductionDetailPage.jsx frontend/src/components/productions/ProductionOverviewTab.jsx
git commit -m "feat(productions): wire production_access into detail page + Members tab"
```

---

## Task 14: ProductionMembersTab component

**Files:**
- Create: `frontend/src/components/productions/ProductionMembersTab.jsx`
- Modify: `frontend/src/pages/ProductionPages.css` (member table + badge styles)

**Interfaces:**
- Consumes: `listProductionMembers`, `addProductionMember`, `updateProductionMember`, `removeProductionMember`, `revokeProductionInvite` (Task 12); props `{ productionId, access }`.

- [ ] **Step 1: Write the component**

```jsx
import { useState, useEffect, useCallback } from 'react';
import {
    listProductionMembers, addProductionMember, updateProductionMember,
    removeProductionMember, revokeProductionInvite,
} from '../../services/apiService';
import { Spinner } from '../ui';

const ROLES = ['viewer', 'coordinator', 'admin'];
const CAP_LABELS = {
    can_view_sensitive: 'See rates & phone',
    can_edit_crew: 'Edit crew',
    can_manage_members: 'Manage members',
    can_edit_production: 'Edit production',
};
const PRESETS = {
    admin: { can_view_sensitive: true, can_edit_crew: true, can_manage_members: true, can_edit_production: true },
    coordinator: { can_view_sensitive: false, can_edit_crew: true, can_manage_members: false, can_edit_production: false },
    viewer: { can_view_sensitive: false, can_edit_crew: false, can_manage_members: false, can_edit_production: false },
};
const RANK = { viewer: 1, coordinator: 2, admin: 3, owner: 4 };

export default function ProductionMembersTab({ productionId, access }) {
    const [members, setMembers] = useState([]);
    const [invites, setInvites] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [adding, setAdding] = useState(false);

    const myRank = RANK[access.role] || 0;

    const load = useCallback(() => {
        setLoading(true);
        listProductionMembers(productionId)
            .then((d) => { setMembers(d.members || []); setInvites(d.invites || []); setError(null); })
            .catch((e) => setError(e.response?.data?.error || 'Failed to load members'))
            .finally(() => setLoading(false));
    }, [productionId]);

    useEffect(load, [load]);

    const patchMember = async (m, patch) => {
        try {
            const { member } = await updateProductionMember(productionId, m.id, patch);
            setMembers((prev) => prev.map((x) => (x.id === member.id ? member : x)));
            setError(null);
        } catch (e) {
            setError(e.response?.data?.error || 'Update failed');
        }
    };

    const remove = async (m) => {
        if (!window.confirm(`Remove ${m.name}?`)) return;
        try {
            await removeProductionMember(productionId, m.id);
            setMembers((prev) => prev.filter((x) => x.id !== m.id));
        } catch (e) {
            setError(e.response?.data?.error || 'Remove failed');
        }
    };

    const revoke = async (inv) => {
        try {
            await revokeProductionInvite(inv.id);
            setInvites((prev) => prev.filter((x) => x.id !== inv.id));
        } catch (e) {
            setError(e.response?.data?.error || 'Revoke failed');
        }
    };

    if (loading) return <div className="production-page-loading"><Spinner size={28} /></div>;

    return (
        <div className="production-members-tab">
            {error && <p className="production-page-error">{error}</p>}

            <div className="members-header">
                <h3>Members</h3>
                <button className="btn-primary" onClick={() => setAdding(true)}>Add member</button>
            </div>

            <table className="members-table">
                <thead>
                    <tr><th>Name</th><th>Email</th><th>Role</th>
                        {Object.values(CAP_LABELS).map((l) => <th key={l}>{l}</th>)}
                        <th /></tr>
                </thead>
                <tbody>
                    {members.map((m) => {
                        const locked = (RANK[m.role] || 0) >= myRank && access.role !== 'owner';
                        return (
                            <tr key={m.id}>
                                <td>{m.name}</td>
                                <td>{m.email}</td>
                                <td>
                                    <select value={m.role} disabled={locked}
                                        onChange={(e) => patchMember(m, { role: e.target.value, ...PRESETS[e.target.value] })}>
                                        {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                                    </select>
                                </td>
                                {Object.keys(CAP_LABELS).map((c) => (
                                    <td key={c} style={{ textAlign: 'center' }}>
                                        <input type="checkbox" checked={!!m[c]} disabled={locked}
                                            onChange={(e) => patchMember(m, { [c]: e.target.checked })} />
                                    </td>
                                ))}
                                <td>{!locked && <button className="btn-link-danger" onClick={() => remove(m)}>Remove</button>}</td>
                            </tr>
                        );
                    })}
                    {members.length === 0 && <tr><td colSpan={8} className="members-empty">No members yet.</td></tr>}
                </tbody>
            </table>

            {invites.length > 0 && (
                <>
                    <h3>Pending invites</h3>
                    <table className="members-table">
                        <thead><tr><th>Email</th><th>Role</th><th>Sent</th><th /></tr></thead>
                        <tbody>
                            {invites.map((inv) => (
                                <tr key={inv.id}>
                                    <td>{inv.email}</td>
                                    <td>{inv.role}</td>
                                    <td>{(inv.created_at || '').slice(0, 10)}</td>
                                    <td><button className="btn-link-danger" onClick={() => revoke(inv)}>Revoke</button></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </>
            )}

            {adding && (
                <AddMemberModal
                    myRank={myRank}
                    isOwner={access.role === 'owner'}
                    onClose={() => setAdding(false)}
                    onDone={() => { setAdding(false); load(); }}
                    productionId={productionId}
                    setError={setError}
                />
            )}
        </div>
    );
}

function AddMemberModal({ productionId, myRank, isOwner, onClose, onDone, setError }) {
    const [email, setEmail] = useState('');
    const [role, setRole] = useState('viewer');
    const [flags, setFlags] = useState(PRESETS.viewer);
    const [touched, setTouched] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    const changeRole = (r) => {
        setRole(r);
        if (!touched) setFlags(PRESETS[r]);
    };

    const roleAllowed = (r) => isOwner || RANK[r] < myRank;

    const submit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            await addProductionMember(productionId, { email: email.trim(), role, ...flags });
            onDone();
        } catch (err) {
            const code = err.response?.data?.code;
            if (code === 'no_seats_available') setError('All paid seats are in use. Purchase more seats to add members.');
            else if (code === 'tier_2_required') setError('Team features require an active Team License.');
            else setError(err.response?.data?.error || 'Failed to add member');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
                <h3>Add member</h3>
                <form onSubmit={submit}>
                    <label>Email
                        <input type="email" required value={email}
                            onChange={(e) => setEmail(e.target.value)} />
                    </label>
                    <label>Role
                        <select value={role} onChange={(e) => changeRole(e.target.value)}>
                            {ROLES.filter(roleAllowed).map((r) => <option key={r} value={r}>{r}</option>)}
                        </select>
                    </label>
                    <details>
                        <summary>Advanced permissions</summary>
                        {Object.keys(CAP_LABELS).map((c) => (
                            <label key={c} className="cap-check">
                                <input type="checkbox" checked={!!flags[c]}
                                    onChange={(e) => { setTouched(true); setFlags((f) => ({ ...f, [c]: e.target.checked })); }} />
                                {CAP_LABELS[c]}
                            </label>
                        ))}
                    </details>
                    <div className="modal-actions">
                        <button type="button" onClick={onClose}>Cancel</button>
                        <button type="submit" className="btn-primary" disabled={submitting}>
                            {submitting ? 'Adding…' : 'Add'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
```

- [ ] **Step 2: Add styles to ProductionPages.css**

```css
.production-members-tab .members-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.members-table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; font-size: 0.9rem; }
.members-table th, .members-table td { padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border, #2a2a3a); text-align: left; }
.members-table th { font-weight: 600; color: var(--text-muted, #9aa); }
.members-empty { text-align: center; color: var(--text-muted, #9aa); padding: 1.5rem; }
.btn-link-danger { background: none; border: none; color: #e5484d; cursor: pointer; padding: 0; }
.cap-check { display: block; margin: 0.35rem 0; }
```

> Match the existing token names in `ProductionPages.css` — inspect it and reuse its actual CSS variables / class conventions rather than the fallbacks above.

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/productions/ProductionMembersTab.jsx frontend/src/pages/ProductionPages.css
git commit -m "feat(productions): Members tab — roster, role/capability edits, invites, add-member modal"
```

---

## Task 15: ProductionCrewTab — gate write controls + redaction placeholders

**Files:**
- Modify: `frontend/src/components/productions/ProductionCrewTab.jsx`

**Interfaces:**
- Consumes: new prop `access` (from Task 13). `access.can_edit_crew`, `access.can_view_sensitive`.

- [ ] **Step 1: Read the current component**

Run: `cat frontend/src/components/productions/ProductionCrewTab.jsx`

- [ ] **Step 2: Gate the write controls**

- Accept `access` as a prop: `export default function ProductionCrewTab({ productionId, access }) {`
- `const canEdit = access?.can_edit_crew;`
- Render "Add crew" / "Import CSV" buttons only when `canEdit`.
- Render per-row Edit / Remove actions only when `canEdit`.
- For rate / phone cells: the API omits the field entirely for a redacted viewer. Where a rate would render, show `{row.job_rate != null ? formatRate(row) : <span className="muted">— hidden</span>}` so an omitted value reads as intentionally hidden, not missing. Same for `contact.phone`.

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/productions/ProductionCrewTab.jsx
git commit -m "feat(crew): gate crew-tab write controls on can_edit_crew, mark hidden rates"
```

---

## Task 16: ProductionInviteAccept page + route

**Files:**
- Create: `frontend/src/pages/ProductionInviteAccept.jsx`
- Modify: `frontend/src/App.jsx` (add public route)

**Interfaces:**
- Consumes: `getProductionInvite`, `acceptProductionInvite` (Task 12). Mirrors `frontend/src/pages/InvitePage.jsx` for the auth-gating pattern.

- [ ] **Step 1: Read InvitePage.jsx for the pattern**

Run: `cat frontend/src/pages/InvitePage.jsx`

- [ ] **Step 2: Write the component**

Follow `InvitePage.jsx`'s structure (it handles: not-logged-in → store token + redirect to login; logged-in → show summary card → accept → redirect). Adapt:

```jsx
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getProductionInvite, acceptProductionInvite } from '../services/apiService';
import { useAuth } from '../context/AuthContext';
import { Spinner } from '../components/ui';
import './InvitePage.css';

export default function ProductionInviteAccept() {
    const { token } = useParams();
    const navigate = useNavigate();
    const { user } = useAuth();
    const [invite, setInvite] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);
    const [accepting, setAccepting] = useState(false);

    useEffect(() => {
        getProductionInvite(token)
            .then(setInvite)
            .catch((e) => setError(e.response?.data?.error || 'Invite not found'))
            .finally(() => setLoading(false));
    }, [token]);

    useEffect(() => {
        if (!loading && !user) {
            sessionStorage.setItem('pendingProductionInvite', token);
            navigate(`/login?redirect=/production-invites/${token}`);
        }
    }, [loading, user, token, navigate]);

    const accept = async () => {
        setAccepting(true);
        try {
            const res = await acceptProductionInvite(token);
            navigate(`/productions/${res.production_id}`);
        } catch (e) {
            setError(e.response?.data?.error || 'Could not accept invite');
            setAccepting(false);
        }
    };

    if (loading) return <div className="invite-page"><Spinner size={32} /></div>;
    if (error) return <div className="invite-page"><p className="invite-error">{error}</p></div>;
    if (invite?.status !== 'pending' || invite?.expired) {
        return <div className="invite-page"><p className="invite-error">
            This invitation is {invite?.expired ? 'expired' : invite?.status}.</p></div>;
    }

    return (
        <div className="invite-page">
            <div className="invite-card">
                <h1>Join {invite.production_title}</h1>
                <p>{invite.inviter_name} invited you as <strong>{invite.role}</strong>.</p>
                <button className="btn-primary" onClick={accept} disabled={accepting}>
                    {accepting ? 'Joining…' : 'Accept invitation'}
                </button>
            </div>
        </div>
    );
}
```

> **Implementer:** match `InvitePage.jsx`'s actual auth hook (`useAuth` vs `useContext(AuthContext)`), its CSS classes, and its login-redirect convention exactly. If `InvitePage` uses a shared `<InviteLayout>` or similar, reuse it.

- [ ] **Step 3: Add the route to App.jsx**

Next to `<Route path="invite/:token" element={<InvitePage />} />` (line ~145):

```jsx
<Route path="production-invites/:token" element={<ProductionInviteAccept />} />
```

And the import near line 42:

```jsx
import ProductionInviteAccept from './pages/ProductionInviteAccept';
```

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ProductionInviteAccept.jsx frontend/src/App.jsx
git commit -m "feat(productions): public production-invite accept page"
```

---

## Task 17: ProductionsListPage — show member productions + role badge

**Files:**
- Modify: `frontend/src/pages/ProductionsListPage.jsx`

**Interfaces:**
- Consumes: `listProductions()` now returns rows with `is_owner` and optional `member_role` (Task 10).

- [ ] **Step 1: Read the current page**

Run: `cat frontend/src/pages/ProductionsListPage.jsx`

- [ ] **Step 2: Add a role badge**

Wherever a production row/card renders its title, append a small badge when `!production.is_owner`:

```jsx
{!p.is_owner && <span className="production-role-badge">{p.member_role}</span>}
```

The list already renders whatever `listProductions` returns, so member productions appear automatically once Task 10 ships — this task only adds the visual badge so an owned vs. joined production is distinguishable.

- [ ] **Step 3: Add the badge style to ProductionPages.css**

```css
.production-role-badge {
    display: inline-block; margin-left: 0.5rem; padding: 0.1rem 0.5rem;
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.04em;
    border-radius: 999px; background: var(--surface-2, #2a2a3a); color: var(--text-muted, #9aa);
}
```

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ProductionsListPage.jsx frontend/src/pages/ProductionPages.css
git commit -m "feat(productions): show joined productions with a role badge in the list"
```

---

## Task 18: Full-stack verification pass

**Files:** none (verification only).

- [ ] **Step 1: Backend suite**

Run: `cd backend && python -m pytest tests/ -q`
Expected: all pass, no regressions.

- [ ] **Step 2: Frontend build**

Run: `cd frontend && npm run build`
Expected: pass.

- [ ] **Step 3: Manual smoke (dev servers running, migration 052 applied)**

1. As owner, open a production → **Members** tab → "Add member" with a teammate's existing-account email, role `coordinator` → appears immediately in the roster.
2. "Add member" with an email that has no account, role `viewer` → shows under **Pending invites**.
3. In a second browser/session as that invited user, visit the invite link → accept → land on the production; the pending invite clears from the owner's view.
4. As the coordinator, open the production → **Crew** tab is visible, "Add crew" is available, **rate and phone columns show "— hidden"**.
5. As owner, tick the coordinator's **See rates & phone** checkbox → the coordinator now sees rates on reload.
6. As a plain `viewer`, the Crew tab is read-only (no Add / Edit / Remove).
7. As an `admin` member, try to change someone's role to `admin` → the option isn't offered / the request is rejected; as owner it works.
8. Remove a member → `/billing` seat count drops by one.
9. Delete the production → members and invites vanish; `/contacts` and other productions are intact.

- [ ] **Step 4: Commit any fixups, then finish the branch**

Follow `superpowers:finishing-a-development-branch`.

---

## Self-Review

**Spec coverage:**
- `production_members` / `production_invites` tables → Task 1 ✓
- `production_authz.py` (`get_production_role`, `get_production_access`, `require_production_role`, resolvers) → Tasks 2–3 ✓
- Crew routes re-gated + redaction → Task 4 ✓
- `_fetch_seats_used` four-source union → Task 5 ✓
- Role presets + rank guardrail → Task 6 ✓
- Member routes (GET/POST/PATCH/DELETE), immediate-vs-invite, owner-keyed entitlement gate → Task 7 ✓
- Invite revoke / token GET / accept, email templates → Task 8 ✓
- Auto-accept extension → Task 9 ✓
- `production_access` in GET-one, member-visible `list_productions` / `get_production_for_viewer` → Task 10 ✓
- Route-enforcement regression → Task 11 ✓
- apiService functions → Task 12 ✓
- ProductionDetailPage tabs + access wiring → Task 13 ✓
- Members tab UI → Task 14 ✓
- Crew tab gating + redaction placeholders → Task 15 ✓
- Invite accept page + route → Task 16 ✓
- Productions list — joined productions + badge → Task 17 ✓
- Verification → Task 18 ✓
- Out of scope (untouched): `script_members`, `get_script_role`, reports, `/contacts` for non-owners — no task touches these ✓

**Placeholder scan:** the two "read the file first" notes (Task 5 helper names, Task 8 `email_service` internals, Task 14/16 CSS + hook names) are explicit "match the existing pattern" instructions with concrete fallbacks, not deferred work. Every code step has real code.

**Type consistency:**
- `get_production_access` returns `{role, can_view_sensitive, can_edit_crew, can_manage_members, can_edit_production}` — used identically in Tasks 3, 4, 7, 10, 13.
- `CAPABILITIES` tuple defined in Task 2, imported in Tasks 6, 8, 10.
- Service error shape `('error', code, http_status)` — consistent across `add_member` / `update_member` / `accept_invite` and unwrapped by `_member_error` in the routes (Task 7).
- `add_member(production_id, actor_uid, actor_access, fields)` — the Step 4 simplification note in Task 7 fixes the signature; Task 7 Step 5 routes call it with `get_user_id(), g.production_access, data` in that order. **Fix applied inline:** signature is `(production_id, actor_uid, actor_access, fields)`, route passes `(production_id, get_user_id(), g.production_access, data)`.
- `ROLE_RANK` identical in `production_authz.py` (Task 2) and the frontend `RANK` (Tasks 14) — both `{viewer:1, coordinator:2, admin:3, owner:4}`.
