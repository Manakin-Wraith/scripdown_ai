# Production Script Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Production membership grants access to every script attached to the production, controlled by a per-member `script_access` level (none / view / edit).

**Architecture:** `get_script_role` gains a third source: `scripts.production_id` → `production_members.script_access`, mapped to a script role and resolved at check time (no synced rows). Attaching a script with its own team prompts the owner to move those people into the production or drop them; detaching can keep chosen members on the script's own team. The per-script Team drawer shows a "managed by production" notice for production scripts.

**Tech Stack:** Flask + supabase-py (service-role key, app-layer authz), pytest with in-memory Supabase mocks; React 18 + Vite (plain JSX), axios via `services/apiService.js`.

**Spec:** `docs/superpowers/specs/2026-09-23-production-script-access-design.md`

## Global Constraints

- All data access via Supabase; never SQLite. Migrations are applied **manually** by the account owner to project `twzfaizeyqwevmhjyicz` — `run_migration.py` is dead.
- Backend gate: `cd backend && pytest tests/` must pass. Frontend gate: `cd frontend && npm run build` (`npm run lint` is broken repo-wide — do not use it as a gate).
- All frontend HTTP calls go through `frontend/src/services/apiService.js`; no new axios instances.
- `script_access` values are exactly `'none' | 'view' | 'edit'`. Mapping: `view → 'viewer'`, `edit → 'member'`, `none →` no access. Reverse (moving script members): `viewer → view`, `member → edit`, `admin → edit`.
- Role presets for `script_access`: `admin → edit`, `coordinator → edit`, `viewer → view`.
- Moving a script team into a production **bypasses** the seat and Team-tier gates (spec D3). It never goes through `production_member_service.add_member`.
- Moved members lose `department_code` (spec D2).
- Delete / lock / unlock script stay `owner`-only. Attach / detach stay production-owner-only.
- DB mocks in tests support only `select / insert / update / delete / eq / in_ / is_ / ilike / or_ / order / single / limit`. New backend code must **not** use `upsert`, `gt`, `neq` — filter in Python instead.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Scope split

Spec decision D1 (hide edit controls for viewers across all script pages) touches ~30 components whose correct gating depends on each backend route's `min_role`. This plan ships the **foundation** (`my_role` in script metadata, `canEditScript` helper, a "View only" badge on the script header) and records the per-component sweep as a follow-up plan in `docs/BACKLOG.md` (Task 11). Everything else in the spec is implemented here.

## File map

| File | Change |
|---|---|
| `backend/db/migrations/056_production_script_access.sql` | **Create.** `script_access` column on `production_members` + `production_invites`, backfill |
| `backend/middleware/production_authz.py` | Script-access constants; `get_production_access` returns `script_access`; docstring |
| `backend/middleware/authorization.py` | `production_derived_role`, `production_script_roles`, `_higher_role`; `get_script_role` third source |
| `backend/services/production_member_service.py` | `DEFAULT_SCRIPT_ACCESS`, `resolve_script_access`, `script_access_ok`; add/update/accept/views carry `script_access`; docstring |
| `backend/services/production_script_team_service.py` | **Create.** `load_script_team`, `describe_script_team`, `move_script_team_to_production`, `drop_script_team`, `keep_members_on_script` |
| `backend/services/production_service.py` | `get_owned_script`; `add_script` returns `'already_attached'` |
| `backend/routes/production_routes.py` | Attach `members_action`; detach `keep_user_ids`; new error code |
| `backend/routes/supabase_routes.py` | `GET /api/scripts`, health counts, `_user_can_access_script`, metadata route |
| `backend/routes/invite_routes.py` | `create_invite` 409 for production scripts; `my-membership` docstring |
| `backend/tests/test_production_script_access.py` | **Create.** authz + member-service + list/metadata tests |
| `backend/tests/test_production_script_team.py` | **Create.** attach/detach route tests |
| `backend/tests/test_team_gating.py` | Add managed-by-production test |
| `frontend/src/services/apiService.js` | `addScriptToProduction(id, scriptId, membersAction)`, `removeScriptFromProduction(id, scriptId, keepUserIds)` |
| `frontend/src/components/productions/ProductionMembersTab.jsx` | Script access column/select, presets, invites column, helper line |
| `frontend/src/components/productions/ProductionScriptPicker.jsx` | Move/drop prompt on 409, retry |
| `frontend/src/components/productions/DetachScriptModal.jsx` | **Create.** Keep-on-script checklist |
| `frontend/src/components/productions/ProductionOverviewTab.jsx` | `onRemove(script)`, empty-state copy |
| `frontend/src/pages/ProductionDetailPage.jsx` | `?tab=`, detach modal, delete copy, `scriptCount`, `NO_ACCESS.script_access` |
| `frontend/src/pages/ProductionPages.css` | Styles for prompt/modal |
| `frontend/src/components/team/TeamDrawer.jsx` | Managed-by-production notice |
| `frontend/src/components/team/TeamDrawer.css` | Notice style |
| `frontend/src/components/metadata/ScriptHeader.jsx` | Pass production props; View-only badge |
| `frontend/src/components/metadata/ScriptHeader.css` | Badge style |
| `frontend/src/utils/scriptRole.js` | **Create.** `SCRIPT_ROLE_RANK`, `canEditScript` |
| `frontend/src/components/scripts/ScriptTable.jsx` | "Shared via {production}" tooltip |
| `docs/BACKLOG.md` | D1 follow-up entry |

---

### Task 1: Migration + script-access constants in `production_authz`

**Files:**
- Create: `backend/db/migrations/056_production_script_access.sql`
- Modify: `backend/middleware/production_authz.py` (module docstring lines 1-11; constants after `ROLE_RANK`; `get_production_access` ~line 60-76)
- Test: `backend/tests/test_production_script_access.py` (create)

**Interfaces:**
- Produces (in `middleware.production_authz`):
  - `SCRIPT_ACCESS_LEVELS = ('none', 'view', 'edit')`
  - `SCRIPT_ACCESS_RANK = {'none': 0, 'view': 1, 'edit': 2}`
  - `SCRIPT_ACCESS_TO_ROLE = {'view': 'viewer', 'edit': 'member'}`
  - `SCRIPT_ROLE_TO_ACCESS = {'viewer': 'view', 'member': 'edit', 'admin': 'edit'}`
  - `get_production_access(...)` dict now includes `'script_access'` (`'edit'` for owner, row value or `'none'` for members).

- [ ] **Step 1: Write the migration**

`backend/db/migrations/056_production_script_access.sql`:

```sql
-- 056: production membership grants script access.
-- Spec: docs/superpowers/specs/2026-09-23-production-script-access-design.md
-- Manual apply (run_migration.py is dead).

ALTER TABLE production_members
  ADD COLUMN IF NOT EXISTS script_access text NOT NULL DEFAULT 'none'
  CHECK (script_access IN ('none','view','edit'));

ALTER TABLE production_invites
  ADD COLUMN IF NOT EXISTS script_access text NOT NULL DEFAULT 'none'
  CHECK (script_access IN ('none','view','edit'));

-- Backfill from role presets (admin/coordinator → edit, viewer → view).
UPDATE production_members SET script_access = 'edit'
  WHERE role IN ('admin','coordinator');
UPDATE production_members SET script_access = 'view'
  WHERE role = 'viewer';
UPDATE production_invites SET script_access = 'edit'
  WHERE role IN ('admin','coordinator') AND status = 'pending';
UPDATE production_invites SET script_access = 'view'
  WHERE role = 'viewer' AND status = 'pending';
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_production_script_access.py`:

```python
"""Production membership → script access (spec 2026-09-23)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import middleware.production_authz as pauthz
from middleware.production_authz import (
    SCRIPT_ACCESS_RANK, SCRIPT_ACCESS_TO_ROLE, SCRIPT_ROLE_TO_ACCESS,
    get_production_access,
)
from test_production_member_routes import MockSupabase


def _patch_pauthz(monkeypatch, store):
    mock = MockSupabase(store)
    monkeypatch.setattr(pauthz, "get_supabase_admin", lambda: mock)
    return mock


def test_script_access_constants():
    assert SCRIPT_ACCESS_RANK == {'none': 0, 'view': 1, 'edit': 2}
    assert SCRIPT_ACCESS_TO_ROLE == {'view': 'viewer', 'edit': 'member'}
    assert SCRIPT_ROLE_TO_ACCESS == {'viewer': 'view', 'member': 'edit', 'admin': 'edit'}


def test_production_access_owner_has_edit_script_access(monkeypatch):
    _patch_pauthz(monkeypatch, {"productions": [{"id": "p1", "owner_id": "o"}]})
    assert get_production_access("p1", "o")["script_access"] == "edit"


def test_production_access_member_script_access_from_row(monkeypatch):
    _patch_pauthz(monkeypatch, {
        "productions": [{"id": "p1", "owner_id": "o"}],
        "production_members": [{"production_id": "p1", "user_id": "u", "role": "viewer",
                                "script_access": "view"}],
    })
    assert get_production_access("p1", "u")["script_access"] == "view"


def test_production_access_member_missing_column_defaults_none(monkeypatch):
    _patch_pauthz(monkeypatch, {
        "productions": [{"id": "p1", "owner_id": "o"}],
        "production_members": [{"production_id": "p1", "user_id": "u", "role": "viewer"}],
    })
    assert get_production_access("p1", "u")["script_access"] == "none"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest tests/test_production_script_access.py -v`
Expected: FAIL — `ImportError: cannot import name 'SCRIPT_ACCESS_RANK'`

- [ ] **Step 4: Implement**

In `backend/middleware/production_authz.py`, replace the module docstring with:

```python
"""
Production-axis authorization for SlateOne.

Parallel to middleware/authorization.py (the script axis). A production
member's production-level capabilities live here; their access to the
production's SCRIPTS is the `script_access` level (none/view/edit), which
middleware/authorization.get_script_role reads via scripts.production_id.

Answers: may THIS user act on THIS production, at what role, with which
capability flags? Enforcement is app-layer (the backend uses the
service-role key).
"""
```

Directly below `ROLE_RANK = {...}` add:

```python
# Per-member access to the production's scripts. A level, not a boolean,
# so it is deliberately NOT part of CAPABILITIES.
SCRIPT_ACCESS_LEVELS = ('none', 'view', 'edit')
SCRIPT_ACCESS_RANK = {'none': 0, 'view': 1, 'edit': 2}
SCRIPT_ACCESS_TO_ROLE = {'view': 'viewer', 'edit': 'member'}   # none → no access
SCRIPT_ROLE_TO_ACCESS = {'viewer': 'view', 'member': 'edit', 'admin': 'edit'}
```

In `get_production_access`, change the two return lines:

```python
    if owner_id == user_id:
        return {'role': 'owner', 'script_access': 'edit',
                **{c: True for c in CAPABILITIES}}
    row = _get_member_row(production_id, user_id)
    if not row:
        return None
    return {'role': row['role'], 'script_access': row.get('script_access') or 'none',
            **{c: bool(row.get(c)) for c in CAPABILITIES}}
```

Also update its docstring first line to `dict(role + script_access + capability booleans) | None | PRODUCTION_NOT_FOUND.`

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/test_production_script_access.py tests/test_production_authz.py -v`
Expected: PASS (if an existing `test_production_authz.py` test asserts the exact dict for owner/member, add `'script_access'` to its expected dict — `'edit'` for owner, the row value or `'none'` for members).

- [ ] **Step 6: Commit**

```bash
git add backend/db/migrations/056_production_script_access.sql backend/middleware/production_authz.py backend/tests/test_production_script_access.py backend/tests/test_production_authz.py
git commit -m "feat(productions): script_access column + constants on production axis

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `get_script_role` resolves production-derived access

**Files:**
- Modify: `backend/middleware/authorization.py` (imports; `get_script_role` lines ~19-45; new helpers after it)
- Test: `backend/tests/test_production_script_access.py`

**Interfaces:**
- Consumes: `SCRIPT_ACCESS_TO_ROLE` (Task 1).
- Produces (in `middleware.authorization`):
  - `production_derived_role(client, production_id, user_id) -> 'viewer' | 'member' | None`
  - `production_script_roles(client, user_id) -> dict[script_id, 'viewer' | 'member']` — scripts reachable via production membership with access ≠ none, excluding scripts the user owns.
  - `get_script_role` returns the higher of direct `script_members.role` and production-derived role.

- [ ] **Step 1: Write the failing tests** (append to `backend/tests/test_production_script_access.py`)

```python
import middleware.authorization as authz
from middleware.authorization import (
    get_script_role, SCRIPT_NOT_FOUND, production_derived_role, production_script_roles,
)


def _patch_authz(monkeypatch, store):
    mock = MockSupabase(store)
    monkeypatch.setattr(authz, "get_supabase_admin", lambda: mock)
    return mock


def _prod_store(access, script_production="p1", direct=None):
    store = {
        "scripts": [{"id": "s1", "user_id": "owner", "production_id": script_production}],
        "production_members": [{"production_id": "p1", "user_id": "u", "role": "viewer",
                                "script_access": access}],
        "script_members": [],
    }
    if direct:
        store["script_members"].append({"script_id": "s1", "user_id": "u", "role": direct})
    return store


def test_production_edit_maps_to_member(monkeypatch):
    _patch_authz(monkeypatch, _prod_store("edit"))
    assert get_script_role("s1", "u") == "member"


def test_production_view_maps_to_viewer(monkeypatch):
    _patch_authz(monkeypatch, _prod_store("view"))
    assert get_script_role("s1", "u") == "viewer"


def test_production_none_gives_no_access(monkeypatch):
    _patch_authz(monkeypatch, _prod_store("none"))
    assert get_script_role("s1", "u") is None


def test_standalone_script_ignores_production_rows(monkeypatch):
    _patch_authz(monkeypatch, _prod_store("edit", script_production=None))
    assert get_script_role("s1", "u") is None


def test_direct_and_production_higher_wins(monkeypatch):
    _patch_authz(monkeypatch, _prod_store("view", direct="member"))
    assert get_script_role("s1", "u") == "member"
    _patch_authz(monkeypatch, _prod_store("edit", direct="viewer"))
    assert get_script_role("s1", "u") == "member"


def test_direct_admin_beats_production_edit(monkeypatch):
    _patch_authz(monkeypatch, _prod_store("edit", direct="admin"))
    assert get_script_role("s1", "u") == "admin"


def test_removed_member_loses_access(monkeypatch):
    store = _prod_store("edit")
    store["production_members"] = []
    _patch_authz(monkeypatch, store)
    assert get_script_role("s1", "u") is None


def test_owner_still_owner_and_missing_still_sentinel(monkeypatch):
    _patch_authz(monkeypatch, _prod_store("edit"))
    assert get_script_role("s1", "owner") == "owner"
    assert get_script_role("nope", "u") is SCRIPT_NOT_FOUND


def test_production_derived_role_helper(monkeypatch):
    mock = _patch_authz(monkeypatch, _prod_store("view"))
    assert production_derived_role(mock, "p1", "u") == "viewer"
    assert production_derived_role(mock, None, "u") is None
    assert production_derived_role(mock, "p1", "stranger") is None


def test_production_script_roles_lists_reachable_scripts(monkeypatch):
    mock = _patch_authz(monkeypatch, {
        "production_members": [
            {"production_id": "p1", "user_id": "u", "script_access": "edit"},
            {"production_id": "p2", "user_id": "u", "script_access": "none"},
        ],
        "scripts": [
            {"id": "s1", "user_id": "owner", "production_id": "p1"},
            {"id": "s2", "user_id": "owner", "production_id": "p2"},
            {"id": "s3", "user_id": "u", "production_id": "p1"},   # own script — excluded
        ],
    })
    assert production_script_roles(mock, "u") == {"s1": "member"}


def test_production_script_roles_empty_when_no_memberships(monkeypatch):
    mock = _patch_authz(monkeypatch, {"production_members": [], "scripts": []})
    assert production_script_roles(mock, "u") == {}
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && pytest tests/test_production_script_access.py -v`
Expected: FAIL — `ImportError: cannot import name 'production_derived_role'`

- [ ] **Step 3: Implement**

In `backend/middleware/authorization.py`, add below the existing imports:

```python
from middleware.production_authz import SCRIPT_ACCESS_TO_ROLE
```

Replace `get_script_role` with:

```python
def get_script_role(script_id, user_id):
    """Return the caller's effective role on a script.

    Sources, highest role wins:
      - scripts.user_id == user_id                      → 'owner'
      - a script_members row                            → its role
      - scripts.production_id → production_members.script_access
                                                        → 'member' (edit) / 'viewer' (view)

    Returns a role string, None (exists, no access), or SCRIPT_NOT_FOUND.
    """
    if not script_id or not user_id:
        return None

    supabase = get_supabase_admin()
    script = (supabase.table('scripts')
              .select('user_id, production_id').eq('id', script_id).limit(1).execute())
    if not script.data:
        return SCRIPT_NOT_FOUND

    row = script.data[0]
    if row.get('user_id') == user_id:
        return 'owner'

    member = (supabase.table('script_members')
              .select('role').eq('script_id', script_id)
              .eq('user_id', user_id).limit(1).execute())
    direct = member.data[0].get('role') if member.data else None
    derived = production_derived_role(supabase, row.get('production_id'), user_id)
    return _higher_role(direct, derived)


def _higher_role(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return a if ROLE_RANK.get(a, 0) >= ROLE_RANK.get(b, 0) else b


def production_derived_role(client, production_id, user_id):
    """Script role granted by production membership, or None."""
    if not production_id or not user_id:
        return None
    rows = (client.table('production_members').select('script_access')
            .eq('production_id', production_id).eq('user_id', user_id)
            .limit(1).execute().data or [])
    if not rows:
        return None
    return SCRIPT_ACCESS_TO_ROLE.get(rows[0].get('script_access'))


def production_script_roles(client, user_id):
    """{script_id: role} for scripts the user reaches only through production
    membership (script_access view/edit). Excludes scripts they own.

    `client` is passed in so route modules with their own module-level
    Supabase client (supabase_routes.supabase) can reuse it.
    """
    if not user_id:
        return {}
    rows = (client.table('production_members').select('production_id, script_access')
            .eq('user_id', user_id).execute().data or [])
    access_by_prod = {r['production_id']: r.get('script_access') for r in rows
                      if SCRIPT_ACCESS_TO_ROLE.get(r.get('script_access'))}
    if not access_by_prod:
        return {}
    scripts = (client.table('scripts').select('id, user_id, production_id')
               .in_('production_id', list(access_by_prod)).execute().data or [])
    return {s['id']: SCRIPT_ACCESS_TO_ROLE[access_by_prod[s['production_id']]]
            for s in scripts if s.get('user_id') != user_id}
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/test_production_script_access.py tests/test_authorization.py tests/test_production_routes.py tests/test_series_routes.py -v`
Expected: PASS. (Existing `conftest.FakeTable` ignores select columns, and a missing `production_members` table returns `[]`, so old tests are unaffected.)

- [ ] **Step 5: Commit**

```bash
git add backend/middleware/authorization.py backend/tests/test_production_script_access.py
git commit -m "feat(authz): get_script_role resolves production-derived script access

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Member lifecycle carries `script_access`

**Files:**
- Modify: `backend/services/production_member_service.py` (docstring; imports; after `rank_ok`; `_member_view`; `_invite_view`; `add_member`; `update_member`; `accept_invite`)
- Modify: `backend/routes/production_routes.py:23-25` (`_MEMBER_ERR_WITH_CODE`)
- Test: `backend/tests/test_production_script_access.py`

**Interfaces:**
- Consumes: `SCRIPT_ACCESS_RANK` (Task 1).
- Produces (in `services.production_member_service`):
  - `DEFAULT_SCRIPT_ACCESS = {'admin': 'edit', 'coordinator': 'edit', 'viewer': 'view'}`
  - `resolve_script_access(role, fields, current=None) -> str | None` — explicit valid value wins; else `current`; else role default; `None` if an explicit value is invalid.
  - `script_access_ok(actor_access, level) -> bool` — owner always; else `level` rank ≤ actor's `script_access` rank.
  - Member/invite views include `'script_access'`.
  - New error code `'bad_script_access'` (400).

- [ ] **Step 1: Write the failing tests** (append)

```python
import services.production_member_service as pms
from middleware.auth import DEV_USER_ID


def test_resolve_script_access_defaults_and_overrides():
    assert pms.resolve_script_access("admin", {}) == "edit"
    assert pms.resolve_script_access("coordinator", None) == "edit"
    assert pms.resolve_script_access("viewer", {}) == "view"
    assert pms.resolve_script_access("viewer", {"script_access": "none"}) == "none"
    assert pms.resolve_script_access("viewer", {"script_access": "bogus"}) is None
    assert pms.resolve_script_access("admin", {}, current="view") == "view"


def test_script_access_ok():
    assert pms.script_access_ok({"role": "owner"}, "edit") is True
    assert pms.script_access_ok({"role": "admin", "script_access": "view"}, "edit") is False
    assert pms.script_access_ok({"role": "admin", "script_access": "edit"}, "edit") is True
    assert pms.script_access_ok({"role": "admin"}, "view") is False   # missing → none


def _svc_patch(monkeypatch, store):
    mock = MockSupabase(store)
    monkeypatch.setattr(pms, "get_supabase_admin", lambda: mock)
    monkeypatch.setattr(pms, "get_entitlement", lambda uid: {
        "can_use_teams": True, "seats_used": 0, "seats_paid": 10})
    monkeypatch.setattr("services.email_service.is_configured", lambda: False)
    return mock


def _base_store(**ov):
    base = {"productions": [{"id": "p1", "owner_id": DEV_USER_ID, "title": "Farm"}],
            "production_members": [], "production_invites": [], "notifications": [],
            "profiles": [{"id": DEV_USER_ID, "email": "dev@example.com"},
                         {"id": "u2", "email": "jane@x.com", "full_name": "Jane"}]}
    base.update(ov)
    return base


OWNER = {"role": "owner"}


def test_add_member_uses_role_default_script_access(monkeypatch):
    store = _base_store()
    _svc_patch(monkeypatch, store)
    out = pms.add_member("p1", DEV_USER_ID, OWNER, {"email": "jane@x.com", "role": "viewer"})
    assert out["member"]["script_access"] == "view"
    assert store["production_members"][0]["script_access"] == "view"


def test_add_member_explicit_script_access(monkeypatch):
    store = _base_store()
    _svc_patch(monkeypatch, store)
    pms.add_member("p1", DEV_USER_ID, OWNER,
                   {"email": "jane@x.com", "role": "admin", "script_access": "none"})
    assert store["production_members"][0]["script_access"] == "none"


def test_add_member_bad_script_access(monkeypatch):
    _svc_patch(monkeypatch, _base_store())
    out = pms.add_member("p1", DEV_USER_ID, OWNER,
                         {"email": "jane@x.com", "role": "viewer", "script_access": "all"})
    assert out == ("error", "bad_script_access", 400)


def test_add_member_rank_denied_above_own_script_access(monkeypatch):
    _svc_patch(monkeypatch, _base_store())
    actor = {"role": "admin", "script_access": "view", "can_manage_members": True}
    out = pms.add_member("p1", "actor", actor,
                         {"email": "jane@x.com", "role": "viewer", "script_access": "edit"})
    assert out == ("error", "rank_denied", 403)


def test_invite_carries_script_access(monkeypatch):
    store = _base_store()
    _svc_patch(monkeypatch, store)
    out = pms.add_member("p1", DEV_USER_ID, OWNER, {"email": "new@x.com", "role": "coordinator"})
    assert out["invite"]["script_access"] == "edit"
    assert store["production_invites"][0]["script_access"] == "edit"


def test_update_member_role_change_keeps_script_access(monkeypatch):
    store = _base_store(production_members=[{
        "id": "m1", "production_id": "p1", "user_id": "u2", "role": "viewer",
        "script_access": "none"}])
    _svc_patch(monkeypatch, store)
    out = pms.update_member("p1", "m1", DEV_USER_ID, OWNER, {"role": "coordinator"})
    assert out["member"]["script_access"] == "none"


def test_update_member_sets_script_access(monkeypatch):
    store = _base_store(production_members=[{
        "id": "m1", "production_id": "p1", "user_id": "u2", "role": "viewer",
        "script_access": "view"}])
    _svc_patch(monkeypatch, store)
    out = pms.update_member("p1", "m1", DEV_USER_ID, OWNER, {"script_access": "edit"})
    assert out["member"]["script_access"] == "edit"


def test_update_member_unchanged_script_access_not_rank_checked(monkeypatch):
    # Actor holds only 'view' but is not changing the member's 'edit'.
    store = _base_store(production_members=[{
        "id": "m1", "production_id": "p1", "user_id": "u2", "role": "viewer",
        "script_access": "edit"}])
    _svc_patch(monkeypatch, store)
    actor = {"role": "admin", "script_access": "view", "can_manage_members": True}
    out = pms.update_member("p1", "m1", "actor", actor, {"role": "viewer"})
    assert not isinstance(out, tuple)


def test_accept_invite_copies_script_access(monkeypatch):
    store = _base_store(production_invites=[{
        "id": "i1", "production_id": "p1", "email": "jane@x.com", "role": "viewer",
        "token": "t", "status": "pending", "expires_at": "2099-01-01T00:00:00+00:00",
        "script_access": "edit"}])
    _svc_patch(monkeypatch, store)
    pms.accept_invite("t", "u2", "jane@x.com")
    assert store["production_members"][0]["script_access"] == "edit"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && pytest tests/test_production_script_access.py -v`
Expected: FAIL — `AttributeError: module 'services.production_member_service' has no attribute 'resolve_script_access'`

- [ ] **Step 3: Implement**

In `backend/services/production_member_service.py`:

Replace the module docstring's second paragraph with:

```python
A production_members row grants production-level access (crew, locations,
call sheets, …) plus access to the production's scripts at the member's
`script_access` level (none/view/edit), which get_script_role resolves via
scripts.production_id. Enforcement is app-layer via
middleware/production_authz.py; this module is the data logic the routes call.
```

Change the import line to:

```python
from middleware.production_authz import ROLE_RANK, CAPABILITIES, SCRIPT_ACCESS_RANK
```

After `rank_ok` add:

```python
DEFAULT_SCRIPT_ACCESS = {'admin': 'edit', 'coordinator': 'edit', 'viewer': 'view'}


def resolve_script_access(role, fields, current=None):
    """Explicit valid value wins; else `current` (updates keep what they have);
    else the role's default. Returns None when an explicit value is invalid."""
    val = (fields or {}).get('script_access')
    if val is not None:
        return val if val in SCRIPT_ACCESS_RANK else None
    if current is not None:
        return current
    return DEFAULT_SCRIPT_ACCESS[role]


def script_access_ok(actor_access, level):
    """A non-owner may not grant script access above their own."""
    if actor_access.get('role') == 'owner':
        return True
    mine = SCRIPT_ACCESS_RANK.get(actor_access.get('script_access') or 'none', 0)
    return SCRIPT_ACCESS_RANK[level] <= mine
```

In `_member_view` and `_invite_view`, add after `'role': row['role'],`:

```python
        'script_access': row.get('script_access') or 'none',
```

In `add_member`, directly after the `rank_ok` check add:

```python
    script_access = resolve_script_access(role, fields)
    if script_access is None:
        return ('error', 'bad_script_access', 400)
    if not script_access_ok(actor_access, script_access):
        return ('error', 'rank_denied', 403)
```

and add `'script_access': script_access,` to **both** insert payloads (the `production_members` insert and the `production_invites` insert), next to `**flags`.

In `update_member`, after the `merged = {...}` block add:

```python
    script_access = resolve_script_access(
        new_role, fields, current.get('script_access') or 'none')
    if script_access is None:
        return ('error', 'bad_script_access', 400)
    if (script_access != (current.get('script_access') or 'none')
            and not script_access_ok(actor_access, script_access)):
        return ('error', 'rank_denied', 403)
```

and change the update payload to `{'role': new_role, 'script_access': script_access, **merged}`.

In `accept_invite`, add to the `production_members` insert payload:

```python
            'script_access': inv.get('script_access') or 'none',
```

In `backend/routes/production_routes.py`, add `'bad_script_access'` to `_MEMBER_ERR_WITH_CODE`.

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/test_production_script_access.py tests/test_production_member_routes.py tests/test_accept_invite.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/production_member_service.py backend/routes/production_routes.py backend/tests/test_production_script_access.py
git commit -m "feat(productions): script_access on member add/update/invite/accept

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Direct-query call sites + script metadata

**Files:**
- Modify: `backend/routes/supabase_routes.py` — imports (line 14, 22-25); `get_scripts` (~148-260); `get_script_metadata` (~345-362); `_user_can_access_script` (~4923-4957); `get_location_health_counts` (~5562-5585)
- Modify: `backend/routes/invite_routes.py` — `get_my_membership` docstring (~740)
- Test: `backend/tests/test_production_script_access.py`

**Interfaces:**
- Consumes: `production_derived_role`, `production_script_roles` (Task 2); `get_production_access` (Task 1).
- Produces:
  - `GET /api/scripts`: production-derived scripts appear with `is_owner: false`, `membership: {role, department_code: None, via_production: true}`. Every member entry's `membership` gains `via_production` (bool). `production_title` is already attached by `_attach_production_info`.
  - `GET /api/scripts/<id>/metadata` adds `production_id`, `production_title`, `my_role`, `can_manage_production_members`.

- [ ] **Step 1: Write the failing tests** (append)

```python
from types import SimpleNamespace
import routes.supabase_routes as sr


class _Q:
    """Chainable read-only query over a list of dict rows."""
    def __init__(self, rows):
        self._rows = list(rows); self._single = False

    def select(self, *_a, **_k): return self
    def eq(self, col, val):
        self._rows = [r for r in self._rows if r.get(col) == val]; return self
    def in_(self, col, values):
        values = set(values); self._rows = [r for r in self._rows if r.get(col) in values]; return self
    def is_(self, col, _v):
        self._rows = [r for r in self._rows if r.get(col) is None]; return self
    def limit(self, _n): return self
    def order(self, *_a, **_k): return self
    def single(self): self._single = True; return self
    def execute(self):
        if self._single:
            return SimpleNamespace(data=self._rows[0] if self._rows else None)
        return SimpleNamespace(data=self._rows)


class _DB:
    def __init__(self, tables): self.tables = tables
    def table(self, name): return _Q(self.tables.get(name, []))


def _app_client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


_SCRIPT = {"id": "s1", "user_id": "owner", "production_id": "p1", "title": "Ep 1",
           "created_at": "2026-09-01T00:00:00Z"}


def _list_db():
    return _DB({
        "scripts": [_SCRIPT],
        "production_members": [{"production_id": "p1", "user_id": "u", "role": "viewer",
                                "script_access": "view"}],
        "productions": [{"id": "p1", "title": "Farm", "owner_id": "owner"}],
        "script_members": [], "scenes": [],
    })


def test_get_scripts_includes_production_derived(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u")
    monkeypatch.setattr(sr, "supabase", _list_db())
    body = _app_client().get("/api/scripts").get_json()
    [s] = [x for x in body["scripts"] if x["id"] == "s1"]
    assert s["is_owner"] is False
    assert s["membership"] == {"role": "viewer", "department_code": None, "via_production": True}
    assert s["production_title"] == "Farm"


def test_user_can_access_script_via_production(monkeypatch):
    monkeypatch.setattr(sr, "supabase", _list_db())
    assert sr._user_can_access_script("s1", "u") is True
    assert sr._user_can_access_script("s1", "stranger") is False


def test_script_metadata_returns_role_and_production(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u")
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: "viewer")
    db = _list_db()
    monkeypatch.setattr(sr, "supabase", db)
    monkeypatch.setattr("middleware.production_authz.get_supabase_admin", lambda: db)
    body = _app_client().get("/api/scripts/s1/metadata").get_json()
    assert body["my_role"] == "viewer"
    assert body["production_id"] == "p1"
    assert body["production_title"] == "Farm"
    assert body["can_manage_production_members"] is False
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && pytest tests/test_production_script_access.py -k "get_scripts or can_access or metadata" -v`
Expected: FAIL (`s1` missing from list / `KeyError: 'my_role'`)

- [ ] **Step 3: Implement**

`backend/routes/supabase_routes.py` imports — change line 14 and the authorization import:

```python
from flask import Blueprint, request, jsonify, g
```

```python
from middleware.authorization import (
    require_script_role, from_scene, from_note, from_item,
    get_script_role, ROLE_RANK, SCRIPT_NOT_FOUND,
    production_derived_role, production_script_roles,
)
from middleware.production_authz import get_production_access
```

In `get_scripts`, inside `if user_id:` directly after the `if member_script_ids:` block (before the legacy block), add:

```python
            # Scripts reached through production membership (script_access view/edit)
            for script_id, prod_role in production_script_roles(supabase, user_id).items():
                if script_id in script_ids:
                    continue
                script_result = supabase.table('scripts').select('*').eq('id', script_id).single().execute()
                if script_result.data:
                    script_ids.add(script_id)
                    member_scripts[script_id] = {
                        'script': script_result.data,
                        'membership': {'role': prod_role, 'department_code': None,
                                       'via_production': True},
                    }
```

and in the member-scripts output change the `'membership'` dict to:

```python
                'membership': {
                    'department_code': membership['department_code'] if membership else None,
                    'role': membership['role'] if membership else None,
                    'via_production': bool(membership.get('via_production')) if membership else False,
                }
```

Replace the body of `get_script_metadata`'s `try:` with:

```python
    try:
        result = supabase.table('scripts').select(
            'id, user_id, title, writer_name, draft_version, genre, logline, total_pages, '
            'created_at, analysis_status, production_id'
        ).eq('id', script_id).single().execute()

        data = dict(result.data or {})
        data['my_role'] = g.script_role
        data['production_title'] = None
        data['can_manage_production_members'] = False
        if data.get('production_id'):
            prod = (supabase.table('productions').select('title')
                    .eq('id', data['production_id']).limit(1).execute())
            data['production_title'] = prod.data[0].get('title') if prod.data else None
            access = get_production_access(data['production_id'], get_user_id())
            data['can_manage_production_members'] = bool(
                isinstance(access, dict) and access.get('can_manage_members'))
        return jsonify(data), 200
```

(keep the existing `except` block).

In `_user_can_access_script`, change the scripts select to `.select('user_id, production_id')` and add after the team-member check (before the superuser check):

```python
        # Production member with script_access view/edit.
        if production_derived_role(supabase, script.data[0].get('production_id'), user_id):
            return True
```

Update its docstring's first sentence to: `Mirrors the access model of the scripts-list endpoint: the script owner, a team member, a production member with script access, a superuser, or any authenticated user for a legacy no-owner script.`

In `get_location_health_counts`, after the `member_result` loop add:

```python
        script_ids.update(production_script_roles(supabase, user_id))
```

In `backend/routes/invite_routes.py`, `get_my_membership` docstring becomes:

```python
    """Get the current user's DIRECT script_members membership for a script.

    Does not report production-derived access (get_script_role does). No
    frontend caller today; use GET /api/scripts/<id>/metadata `my_role`.
    """
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/test_production_script_access.py tests/test_location_health_counts_route.py tests/test_get_scripts_production_info.py tests/test_get_scripts_series_info.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routes/supabase_routes.py backend/routes/invite_routes.py backend/tests/test_production_script_access.py
git commit -m "feat(scripts): production-derived scripts in lists, access check, metadata my_role

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Script invites refuse production scripts

**Files:**
- Modify: `backend/routes/invite_routes.py` — `create_invite` (~52-190)
- Test: `backend/tests/test_team_gating.py`

**Interfaces:**
- Produces: `POST /api/scripts/<id>/invites` → 409 `{error, code: 'managed_by_production', production_id}` when `scripts.production_id` is set.

- [ ] **Step 1: Write the failing test** (append to `backend/tests/test_team_gating.py`)

```python
def test_invite_refused_for_production_script(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr("services.entitlement_service.get_user_id", lambda: 'owner')
    monkeypatch.setattr("services.entitlement_service.get_entitlement",
                        lambda uid: {'can_use_teams': True})
    monkeypatch.setattr(ir, "get_entitlement",
                        lambda uid: {'can_use_teams': True, 'seats_paid': 5, 'seats_used': 0})
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: 'owner')

    class _Q:
        def __init__(self, name): self.name = name
        def select(self, *a, **k): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def execute(self):
            if self.name == 'scripts':
                return SimpleNamespace(data=[{'production_id': 'p1'}])
            raise AssertionError(f"unexpected table {self.name}")
    monkeypatch.setattr(ir, "supabase", type("S", (), {"table": lambda self, n: _Q(n)})())

    resp = _client().post("/api/scripts/s1/invites",
                          json={'email': 'a@b.com', 'department_code': 'camera'})
    assert resp.status_code == 409
    body = resp.get_json()
    assert body['code'] == 'managed_by_production'
    assert body['production_id'] == 'p1'
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && pytest tests/test_team_gating.py::test_invite_refused_for_production_script -v`
Expected: FAIL (status is not 409)

- [ ] **Step 3: Implement**

In `create_invite`, immediately **after** the seat-limit block (the `if not ent.get('is_superuser') and ent['seats_used'] >= ent['seats_paid']:` return) and before any body parsing, add:

```python
    # Scripts in a production are shared via the production's Members tab.
    prod_row = (supabase.table('scripts').select('production_id')
                .eq('id', script_id).limit(1).execute())
    production_id = prod_row.data[0].get('production_id') if prod_row.data else None
    if production_id:
        return jsonify({
            'error': 'Access to this script is managed by its production',
            'code': 'managed_by_production',
            'production_id': production_id,
        }), 409
```

(Placing it after the seat gate keeps `test_invite_blocked_when_seats_exhausted` from touching the DB.)

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/test_team_gating.py tests/test_role_management.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routes/invite_routes.py backend/tests/test_team_gating.py
git commit -m "feat(invites): refuse script invites for scripts managed by a production

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Script-team move/drop/keep service

**Files:**
- Create: `backend/services/production_script_team_service.py`
- Test: `backend/tests/test_production_script_team.py` (create)

**Interfaces:**
- Consumes: `SCRIPT_ACCESS_RANK`, `SCRIPT_ACCESS_TO_ROLE`, `SCRIPT_ROLE_TO_ACCESS` (Task 1); `pms.apply_role_preset`, `pms._profiles_by_id`, `pms._owner_id`, `pms._notify_member_added`, `pms._send_invite_email`, `pms._generate_token` (existing).
- Produces (module `services.production_script_team_service`):
  - `load_script_team(script_id) -> (members: list, live_invites: list, expired_invites: list)`
  - `describe_script_team(members, invites) -> {'members': [{user_id, name, email, role}], 'invites': [{email, role}]}`
  - `move_script_team_to_production(production_id, script_id, actor_uid) -> {'moved_members': int, 'moved_invites': int}`
  - `drop_script_team(script_id, actor_uid) -> {'moved_members': 0, 'moved_invites': 0}`
  - `keep_members_on_script(production_id, script_id, user_ids, actor_uid) -> int` (number kept)

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_production_script_team.py`:

```python
"""Attach/detach: moving a script's own team into a production (spec 2026-09-23)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.production_script_team_service as team
import services.production_member_service as pms
from middleware.auth import DEV_USER_ID
from test_production_member_routes import MockSupabase

FUTURE = "2099-01-01T00:00:00+00:00"
PAST = "2000-01-01T00:00:00+00:00"


def _patch(monkeypatch, store, sent=None):
    mock = MockSupabase(store)
    for target in ("services.production_script_team_service",
                   "services.production_member_service",
                   "services.production_service",
                   "middleware.authorization",
                   "middleware.production_authz"):
        monkeypatch.setattr(f"{target}.get_supabase_admin", lambda: mock)
    monkeypatch.setattr("services.email_service.is_configured", lambda: sent is not None)
    if sent is not None:
        monkeypatch.setattr("services.email_service.send_production_invite",
                            lambda **k: sent.append(("prod_invite", k["to_email"])))
        monkeypatch.setattr("services.email_service.send_production_member_added",
                            lambda **k: sent.append(("member_added", k["to_email"])))
        monkeypatch.setattr("services.email_service.send_invite_revoked",
                            lambda **k: sent.append(("revoked", k["to_email"])))
    return mock


def _store(**ov):
    base = {
        "productions": [{"id": "p1", "owner_id": DEV_USER_ID, "title": "Farm"}],
        "scripts": [{"id": "s1", "user_id": DEV_USER_ID, "production_id": None, "title": "Ep 1"}],
        "script_members": [
            {"id": "sm1", "script_id": "s1", "user_id": "jane", "role": "member",
             "department_code": "camera"},
            {"id": "sm2", "script_id": "s1", "user_id": "tom", "role": "viewer",
             "department_code": "props"},
        ],
        "script_invites": [
            {"id": "si1", "script_id": "s1", "email": "new@x.com", "role": "admin",
             "status": "pending", "expires_at": FUTURE},
            {"id": "si2", "script_id": "s1", "email": "old@x.com", "role": "member",
             "status": "pending", "expires_at": PAST},
        ],
        "production_members": [], "production_invites": [], "notifications": [],
        "profiles": [{"id": DEV_USER_ID, "email": "dev@example.com", "full_name": "Owner"},
                     {"id": "jane", "email": "jane@x.com", "full_name": "Jane"},
                     {"id": "tom", "email": "tom@x.com", "full_name": "Tom"}],
    }
    base.update(ov)
    return base


def test_load_script_team_splits_live_and_expired(monkeypatch):
    _patch(monkeypatch, _store())
    members, live, expired = team.load_script_team("s1")
    assert {m["user_id"] for m in members} == {"jane", "tom"}
    assert [i["id"] for i in live] == ["si1"]
    assert [i["id"] for i in expired] == ["si2"]


def test_describe_script_team_names_people(monkeypatch):
    _patch(monkeypatch, _store())
    members, live, _ = team.load_script_team("s1")
    out = team.describe_script_team(members, live)
    assert {m["name"] for m in out["members"]} == {"Jane", "Tom"}
    assert out["invites"] == [{"email": "new@x.com", "role": "admin"}]


def test_move_creates_viewer_members_with_mapped_access(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    out = team.move_script_team_to_production("p1", "s1", DEV_USER_ID)
    pm = {r["user_id"]: r for r in store["production_members"]}
    assert pm["jane"]["role"] == "viewer" and pm["jane"]["script_access"] == "edit"
    assert pm["tom"]["script_access"] == "view"
    assert pm["jane"]["can_edit_crew"] is False
    assert store["script_members"] == []
    assert out == {"moved_members": 2, "moved_invites": 1}


def test_move_raises_but_never_lowers_existing_member(monkeypatch):
    store = _store(production_members=[
        {"id": "pm1", "production_id": "p1", "user_id": "jane", "role": "coordinator",
         "script_access": "view"},
        {"id": "pm2", "production_id": "p1", "user_id": "tom", "role": "admin",
         "script_access": "edit"},
    ])
    _patch(monkeypatch, store)
    team.move_script_team_to_production("p1", "s1", DEV_USER_ID)
    pm = {r["user_id"]: r for r in store["production_members"]}
    assert pm["jane"]["script_access"] == "edit" and pm["jane"]["role"] == "coordinator"
    assert pm["tom"]["script_access"] == "edit" and pm["tom"]["role"] == "admin"


def test_move_converts_live_invites_silently_revokes_script_invite(monkeypatch):
    store = _store()
    sent = []
    _patch(monkeypatch, store, sent)
    team.move_script_team_to_production("p1", "s1", DEV_USER_ID)
    [pi] = store["production_invites"]
    assert pi["email"] == "new@x.com" and pi["role"] == "viewer"
    assert pi["script_access"] == "edit" and pi["status"] == "pending"
    status = {i["id"]: i["status"] for i in store["script_invites"]}
    assert status == {"si1": "revoked", "si2": "revoked"}
    assert ("prod_invite", "new@x.com") in sent
    assert not any(kind == "revoked" for kind, _ in sent)


def test_move_raises_existing_pending_production_invite(monkeypatch):
    store = _store(production_invites=[
        {"id": "pi1", "production_id": "p1", "email": "NEW@x.com", "role": "viewer",
         "status": "pending", "script_access": "view", "expires_at": FUTURE}])
    _patch(monkeypatch, store)
    team.move_script_team_to_production("p1", "s1", DEV_USER_ID)
    assert len(store["production_invites"]) == 1
    assert store["production_invites"][0]["script_access"] == "edit"


def test_move_is_idempotent(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    team.move_script_team_to_production("p1", "s1", DEV_USER_ID)
    team.move_script_team_to_production("p1", "s1", DEV_USER_ID)
    assert len(store["production_members"]) == 2
    assert len(store["production_invites"]) == 1


def test_move_ignores_seat_and_tier_gates(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    def _boom(uid):
        raise AssertionError("move must not consult entitlements")
    monkeypatch.setattr(pms, "get_entitlement", _boom)
    team.move_script_team_to_production("p1", "s1", DEV_USER_ID)
    assert len(store["production_members"]) == 2


def test_drop_deletes_members_and_revokes_with_email(monkeypatch):
    store = _store()
    sent = []
    _patch(monkeypatch, store, sent)
    team.drop_script_team("s1", DEV_USER_ID)
    assert store["script_members"] == []
    assert store["production_members"] == []
    assert {i["status"] for i in store["script_invites"]} == {"revoked"}
    assert ("revoked", "new@x.com") in sent
    assert ("revoked", "old@x.com") not in sent   # expired: silent


def test_keep_members_on_script_maps_roles(monkeypatch):
    store = _store(script_members=[], production_members=[
        {"id": "pm1", "production_id": "p1", "user_id": "jane", "role": "viewer",
         "script_access": "edit"},
        {"id": "pm2", "production_id": "p1", "user_id": "tom", "role": "viewer",
         "script_access": "none"},
    ])
    _patch(monkeypatch, store)
    kept = team.keep_members_on_script("p1", "s1", ["jane", "tom", "ghost"], DEV_USER_ID)
    assert kept == 1
    [row] = store["script_members"]
    assert row["user_id"] == "jane" and row["role"] == "member"
    assert row["invited_by"] == DEV_USER_ID
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && pytest tests/test_production_script_team.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.production_script_team_service'`

- [ ] **Step 3: Implement**

Create `backend/services/production_script_team_service.py`:

```python
"""
Moving a script's own team (script_members / script_invites) into a
production when the script is attached, and back out on detach.

Spec: docs/superpowers/specs/2026-09-23-production-script-access-design.md

Every write is idempotent (select-then-insert, raise-only updates,
pending-only revokes) and script_members rows are deleted LAST, so a retry
after a partial failure converges. A leftover direct row is harmless:
get_script_role takes the higher of direct and production-derived roles.

Moving deliberately bypasses the seat and Team-tier gates in
production_member_service.add_member: it relocates people who are already
counted (spec decision D3).
"""
from datetime import datetime, timedelta, timezone

from db.supabase_client import get_supabase_admin
from middleware.production_authz import (
    SCRIPT_ACCESS_RANK, SCRIPT_ACCESS_TO_ROLE, SCRIPT_ROLE_TO_ACCESS,
)
import services.production_member_service as pms

# script_members.department_code for members kept on detach; production
# members carry no department (spec decision D2).
KEPT_DEPARTMENT_CODE = 'production'


def _is_live(invite):
    exp = invite.get('expires_at')
    if not exp:
        return True
    try:
        return datetime.fromisoformat(exp.replace('Z', '+00:00')) > datetime.now(timezone.utc)
    except ValueError:
        return True


def _raise_access(current, mapped):
    current = current or 'none'
    return mapped if SCRIPT_ACCESS_RANK[mapped] > SCRIPT_ACCESS_RANK.get(current, 0) else current


def load_script_team(script_id):
    supabase = get_supabase_admin()
    members = (supabase.table('script_members').select('*')
               .eq('script_id', script_id).execute().data or [])
    pending = (supabase.table('script_invites').select('*')
               .eq('script_id', script_id).eq('status', 'pending').execute().data or [])
    live = [i for i in pending if _is_live(i)]
    expired = [i for i in pending if not _is_live(i)]
    return members, live, expired


def describe_script_team(members, invites):
    profiles = pms._profiles_by_id(get_supabase_admin(), {m['user_id'] for m in members})
    out_members = []
    for m in members:
        p = profiles.get(m['user_id']) or {}
        out_members.append({
            'user_id': m['user_id'],
            'name': p.get('full_name') or p.get('email') or 'Unknown',
            'email': p.get('email'),
            'role': m.get('role'),
        })
    return {
        'members': out_members,
        'invites': [{'email': i.get('email'), 'role': i.get('role')} for i in invites],
    }


def _revoke_script_invite(supabase, invite_id):
    (supabase.table('script_invites').update({'status': 'revoked'})
     .eq('id', invite_id).eq('status', 'pending').execute())


def move_script_team_to_production(production_id, script_id, actor_uid):
    supabase = get_supabase_admin()
    members, live, expired = load_script_team(script_id)
    owner_id = pms._owner_id(supabase, production_id)
    viewer_flags = pms.apply_role_preset('viewer', None)

    moved_members = 0
    for m in members:
        uid = m['user_id']
        if uid == owner_id:
            continue
        mapped = SCRIPT_ROLE_TO_ACCESS.get(m.get('role'), 'view')
        existing = (supabase.table('production_members').select('*')
                    .eq('production_id', production_id).eq('user_id', uid)
                    .limit(1).execute().data or [])
        if existing:
            row = existing[0]
            new = _raise_access(row.get('script_access'), mapped)
            if new != (row.get('script_access') or 'none'):
                (supabase.table('production_members').update({'script_access': new})
                 .eq('id', row['id']).execute())
        else:
            try:
                supabase.table('production_members').insert({
                    'production_id': production_id, 'user_id': uid, 'role': 'viewer',
                    'invited_by': actor_uid, 'script_access': mapped, **viewer_flags,
                }).execute()
            except Exception:
                # Concurrent insert raced the UNIQUE (production_id, user_id).
                again = (supabase.table('production_members').select('id')
                         .eq('production_id', production_id).eq('user_id', uid)
                         .limit(1).execute().data or [])
                if not again:
                    raise
            else:
                pms._notify_member_added(supabase, production_id, uid, 'viewer')
        moved_members += 1

    prod_pending = (supabase.table('production_invites').select('*')
                    .eq('production_id', production_id).eq('status', 'pending')
                    .execute().data or [])
    by_email = {(p.get('email') or '').strip().lower(): p for p in prod_pending}
    expires = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()

    moved_invites = 0
    for inv in live:
        email = (inv.get('email') or '').strip().lower()
        mapped = SCRIPT_ROLE_TO_ACCESS.get(inv.get('role'), 'view')
        if email in by_email:
            p = by_email[email]
            new = _raise_access(p.get('script_access'), mapped)
            if new != (p.get('script_access') or 'none'):
                (supabase.table('production_invites').update({'script_access': new})
                 .eq('id', p['id']).execute())
                p['script_access'] = new
        else:
            new_inv = supabase.table('production_invites').insert({
                'production_id': production_id, 'email': email, 'role': 'viewer',
                'token': pms._generate_token(), 'status': 'pending',
                'invited_by': actor_uid, 'expires_at': expires,
                'script_access': mapped, **viewer_flags,
            }).execute().data[0]
            by_email[email] = new_inv
            pms._send_invite_email(supabase, production_id, new_inv)
        # Silent revoke: the person just got a production invite instead.
        _revoke_script_invite(supabase, inv['id'])
        moved_invites += 1

    for inv in expired:
        _revoke_script_invite(supabase, inv['id'])

    supabase.table('script_members').delete().eq('script_id', script_id).execute()
    return {'moved_members': moved_members, 'moved_invites': moved_invites}


def _email_invite_withdrawn(supabase, invite, actor_uid):
    from services import email_service
    if not email_service.is_configured() or not invite.get('email'):
        return
    try:
        script = (supabase.table('scripts').select('title')
                  .eq('id', invite['script_id']).limit(1).execute().data or [])
        prof = (supabase.table('profiles').select('full_name, email')
                .eq('id', actor_uid).limit(1).execute().data or [])
        name = 'The script owner'
        if prof:
            name = (prof[0].get('full_name')
                    or (prof[0].get('email') or '').split('@')[0]
                    or name)
        email_service.send_invite_revoked(
            to_email=invite['email'],
            script_title=(script[0].get('title') if script else None) or 'Unknown Script',
            inviter_name=name)
    except Exception as e:
        print(f"Warning: invite-withdrawn email failed: {e}")


def drop_script_team(script_id, actor_uid):
    supabase = get_supabase_admin()
    _members, live, expired = load_script_team(script_id)
    for inv in live:
        _revoke_script_invite(supabase, inv['id'])
        _email_invite_withdrawn(supabase, inv, actor_uid)
    for inv in expired:
        _revoke_script_invite(supabase, inv['id'])
    supabase.table('script_members').delete().eq('script_id', script_id).execute()
    return {'moved_members': 0, 'moved_invites': 0}


def keep_members_on_script(production_id, script_id, user_ids, actor_uid):
    """On detach: give chosen production members a direct script_members row.

    Only members with script_access view/edit qualify. `invited_by` is the
    owner (actor) so entitlement_service keeps counting them as one seat.
    """
    supabase = get_supabase_admin()
    kept = 0
    for uid in dict.fromkeys(user_ids or []):
        rows = (supabase.table('production_members').select('script_access')
                .eq('production_id', production_id).eq('user_id', uid)
                .limit(1).execute().data or [])
        role = SCRIPT_ACCESS_TO_ROLE.get(rows[0].get('script_access')) if rows else None
        if not role:
            continue
        existing = (supabase.table('script_members').select('id')
                    .eq('script_id', script_id).eq('user_id', uid)
                    .limit(1).execute().data or [])
        if existing:
            continue
        supabase.table('script_members').insert({
            'script_id': script_id, 'user_id': uid, 'role': role,
            'department_code': KEPT_DEPARTMENT_CODE, 'invited_by': actor_uid,
        }).execute()
        kept += 1
    return kept
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/test_production_script_team.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/production_script_team_service.py backend/tests/test_production_script_team.py
git commit -m "feat(productions): move/drop/keep script team on attach and detach

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Attach and detach routes

**Files:**
- Modify: `backend/services/production_service.py` — `add_script` (~131-146); add `get_owned_script`
- Modify: `backend/routes/production_routes.py` — imports; `add_script_to_production` (~129-149); `remove_script_from_production` (~152-164)
- Test: `backend/tests/test_production_script_team.py`

**Interfaces:**
- Consumes: Task 6 service functions.
- Produces:
  - `svc.get_owned_script(script_id, user_id) -> dict | None` (row with `id, production_id`)
  - `svc.add_script(...)` returns `'ok' | 'not_owned' | 'conflict' | 'already_attached'`
  - `POST /api/productions/<pid>/scripts` body `{script_id, members_action?}` → 200 `{success, moved_members, moved_invites}` | 400 bad action | 403 not owned | 409 `script_has_members` | 409 conflict.
  - `DELETE /api/productions/<pid>/scripts/<sid>` body `{keep_user_ids?}` → 200 `{success, kept}`.

- [ ] **Step 1: Write the failing tests** (append to `backend/tests/test_production_script_team.py`)

```python
def _client():
    from flask import Flask
    from routes.production_routes import production_bp
    app = Flask(__name__); app.config["TESTING"] = True
    app.register_blueprint(production_bp)
    return app.test_client()


def _rt(monkeypatch, store, sent=None):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr("middleware.production_authz.get_user_id", lambda: DEV_USER_ID)
    return _patch(monkeypatch, store, sent)


def test_attach_with_team_and_no_action_is_409_and_writes_nothing(monkeypatch):
    store = _store()
    _rt(monkeypatch, store)
    resp = _client().post("/api/productions/p1/scripts", json={"script_id": "s1"})
    assert resp.status_code == 409
    body = resp.get_json()
    assert body["code"] == "script_has_members"
    assert len(body["members"]) == 2 and len(body["invites"]) == 1
    assert store["scripts"][0]["production_id"] is None
    assert len(store["script_members"]) == 2


def test_attach_expired_invites_only_does_not_prompt(monkeypatch):
    store = _store(script_members=[], script_invites=[
        {"id": "si2", "script_id": "s1", "email": "old@x.com", "role": "member",
         "status": "pending", "expires_at": PAST}])
    _rt(monkeypatch, store)
    resp = _client().post("/api/productions/p1/scripts", json={"script_id": "s1"})
    assert resp.status_code == 200
    assert store["scripts"][0]["production_id"] == "p1"


def test_attach_move(monkeypatch):
    store = _store()
    _rt(monkeypatch, store)
    resp = _client().post("/api/productions/p1/scripts",
                          json={"script_id": "s1", "members_action": "move"})
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "moved_members": 2, "moved_invites": 1}
    assert store["scripts"][0]["production_id"] == "p1"
    assert store["script_members"] == []


def test_attach_drop(monkeypatch):
    store = _store()
    _rt(monkeypatch, store)
    resp = _client().post("/api/productions/p1/scripts",
                          json={"script_id": "s1", "members_action": "drop"})
    assert resp.status_code == 200
    assert store["script_members"] == [] and store["production_members"] == []


def test_attach_bad_action_is_400(monkeypatch):
    _rt(monkeypatch, _store())
    resp = _client().post("/api/productions/p1/scripts",
                          json={"script_id": "s1", "members_action": "merge"})
    assert resp.status_code == 400


def test_attach_script_in_other_production_conflicts_before_members(monkeypatch):
    store = _store(
        productions=[{"id": "p1", "owner_id": DEV_USER_ID, "title": "Farm"},
                     {"id": "p2", "owner_id": DEV_USER_ID, "title": "Other"}],
        scripts=[{"id": "s1", "user_id": DEV_USER_ID, "production_id": "p2", "title": "Ep 1"}])
    _rt(monkeypatch, store)
    resp = _client().post("/api/productions/p1/scripts",
                          json={"script_id": "s1", "members_action": "move"})
    assert resp.status_code == 409
    assert resp.get_json().get("code") != "script_has_members"
    assert len(store["script_members"]) == 2
    assert store["production_members"] == []


def test_attach_not_owned_does_not_leak_team(monkeypatch):
    store = _store(scripts=[{"id": "s1", "user_id": "someone", "production_id": None}])
    _rt(monkeypatch, store)
    resp = _client().post("/api/productions/p1/scripts", json={"script_id": "s1"})
    assert resp.status_code == 403
    assert "members" not in resp.get_json()


def test_attach_retry_when_already_attached_here_succeeds(monkeypatch):
    store = _store(scripts=[{"id": "s1", "user_id": DEV_USER_ID, "production_id": "p1"}])
    _rt(monkeypatch, store)
    resp = _client().post("/api/productions/p1/scripts",
                          json={"script_id": "s1", "members_action": "move"})
    assert resp.status_code == 200
    assert store["script_members"] == []


def test_detach_without_keep(monkeypatch):
    store = _store(script_members=[], script_invites=[],
                   scripts=[{"id": "s1", "user_id": DEV_USER_ID, "production_id": "p1"}],
                   production_members=[{"id": "pm1", "production_id": "p1", "user_id": "jane",
                                        "role": "viewer", "script_access": "edit"}])
    _rt(monkeypatch, store)
    resp = _client().delete("/api/productions/p1/scripts/s1")
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "kept": 0}
    assert store["scripts"][0]["production_id"] is None
    assert store["script_members"] == []


def test_detach_with_keep(monkeypatch):
    store = _store(script_members=[], script_invites=[],
                   scripts=[{"id": "s1", "user_id": DEV_USER_ID, "production_id": "p1"}],
                   production_members=[{"id": "pm1", "production_id": "p1", "user_id": "jane",
                                        "role": "viewer", "script_access": "view"}])
    _rt(monkeypatch, store)
    resp = _client().delete("/api/productions/p1/scripts/s1",
                            json={"keep_user_ids": ["jane"]})
    assert resp.get_json() == {"success": True, "kept": 1}
    assert store["script_members"][0]["role"] == "viewer"


def test_detach_keep_ignored_for_script_not_in_this_production(monkeypatch):
    store = _store(script_members=[], script_invites=[],
                   scripts=[{"id": "s1", "user_id": "someone", "production_id": "p2"}],
                   production_members=[{"id": "pm1", "production_id": "p1", "user_id": "jane",
                                        "role": "viewer", "script_access": "edit"}])
    _rt(monkeypatch, store)
    resp = _client().delete("/api/productions/p1/scripts/s1",
                            json={"keep_user_ids": ["jane"]})
    assert resp.get_json()["kept"] == 0
    assert store["script_members"] == []
    assert store["scripts"][0]["production_id"] == "p2"


def test_detach_keep_must_be_list(monkeypatch):
    store = _store(scripts=[{"id": "s1", "user_id": DEV_USER_ID, "production_id": "p1"}])
    _rt(monkeypatch, store)
    resp = _client().delete("/api/productions/p1/scripts/s1", json={"keep_user_ids": "jane"})
    assert resp.status_code == 400
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && pytest tests/test_production_script_team.py -v`
Expected: FAIL (the 409 test gets 200, keep tests fail on response shape)

- [ ] **Step 3: Implement the service changes**

In `backend/services/production_service.py`, add above `add_script`:

```python
def get_owned_script(script_id, user_id):
    """The script row (id, production_id) if the caller owns it, else None."""
    rows = (get_supabase_admin().table("scripts").select("id, production_id")
            .eq("id", script_id).eq("user_id", user_id).limit(1).execute().data or [])
    return rows[0] if rows else None
```

Replace `add_script`'s docstring and final return with:

```python
    """Single conditional UPDATE -- no read-then-write race.

    Returns 'ok' | 'not_owned' | 'conflict' | 'already_attached'.
    'already_attached' (the script already points at THIS production) lets a
    retried attach continue to its member-move step.
    """
```

```python
    if res.data:
        return "ok"
    again = (supabase.table("scripts").select("production_id")
             .eq("id", script_id).limit(1).execute().data or [])
    if again and again[0].get("production_id") == production_id:
        return "already_attached"
    return "conflict"
```

- [ ] **Step 4: Implement the routes**

In `backend/routes/production_routes.py`, add to the service imports:

```python
from services import production_script_team_service as team_svc
```

Replace `add_script_to_production`'s `try:` body with:

```python
    try:
        if not svc._get_production(svc.get_supabase_admin(), production_id):
            return jsonify({"error": "Production not found"}), 404
        if not svc._user_owns_production(production_id, user_id):
            return jsonify({"error": "Insufficient permissions"}), 403
        body = request.get_json(silent=True) or {}
        script_id = body.get("script_id")
        members_action = body.get("members_action")
        if not script_id:
            return jsonify({"error": "script_id is required"}), 400
        if members_action not in (None, "move", "drop"):
            return jsonify({"error": "members_action must be 'move' or 'drop'"}), 400

        # Ownership + "already elsewhere" first, so a stranger's script team is
        # never disclosed and a conflict never reaches the members prompt.
        script = svc.get_owned_script(script_id, user_id)
        if not script:
            return jsonify({"error": "You do not own that script"}), 403
        if script.get("production_id") not in (None, production_id):
            return jsonify({"error": "Script already belongs to a production"}), 409

        members, live, _expired = team_svc.load_script_team(script_id)
        if (members or live) and members_action is None:
            return jsonify({"error": "This script has its own team",
                            "code": "script_has_members",
                            **team_svc.describe_script_team(members, live)}), 409

        outcome = svc.add_script(production_id, script_id, user_id)
        if outcome == "not_owned":
            return jsonify({"error": "You do not own that script"}), 403
        if outcome == "conflict":
            return jsonify({"error": "Script already belongs to a production"}), 409

        # Re-read inside move/drop (load_script_team is called again there), so
        # an invite created between the check above and the attach is handled.
        result = {"moved_members": 0, "moved_invites": 0}
        if members_action == "move":
            result = team_svc.move_script_team_to_production(production_id, script_id, user_id)
        elif members_action == "drop":
            result = team_svc.drop_script_team(script_id, user_id)
        return jsonify({"success": True, **result})
    except Exception as e:
        print(f"Error adding script to production: {e}")
        return jsonify({"error": str(e)}), 500
```

Replace `remove_script_from_production`'s `try:` body with:

```python
    try:
        if not svc._get_production(svc.get_supabase_admin(), production_id):
            return jsonify({"error": "Production not found"}), 404
        if not svc._user_owns_production(production_id, user_id):
            return jsonify({"error": "Insufficient permissions"}), 403
        keep = (request.get_json(silent=True) or {}).get("keep_user_ids") or []
        if not isinstance(keep, list):
            return jsonify({"error": "keep_user_ids must be a list"}), 400
        # Keep only applies to a script that really is in THIS production —
        # otherwise the owner could add members to any script by id.
        in_this = (svc.get_supabase_admin().table("scripts").select("id")
                   .eq("id", script_id).eq("production_id", production_id)
                   .limit(1).execute().data or [])
        svc.remove_script(production_id, script_id)
        kept = 0
        if in_this and keep:
            kept = team_svc.keep_members_on_script(production_id, script_id, keep, user_id)
        return jsonify({"success": True, "kept": kept})
    except Exception as e:
        print(f"Error removing script from production: {e}")
        return jsonify({"error": str(e)}), 500
```

- [ ] **Step 5: Keep existing route tests off the real client**

The attach route now calls `team_svc.load_script_team`, which has its own `get_supabase_admin`. In `backend/tests/test_production_routes.py`, add to `_patch` (after the `middleware.production_authz` line):

```python
    # attach now reads the script's own team via this service
    monkeypatch.setattr("services.production_script_team_service.get_supabase_admin", lambda: mock)
```

Also check `backend/tests/test_production_member_routes.py::_rt_patch` and `backend/tests/test_production_crew_routes.py` — if either exercises `POST /api/productions/<id>/scripts`, add the same line there.

- [ ] **Step 6: Run tests**

Run: `cd backend && pytest tests/test_production_script_team.py tests/test_production_routes.py -v`
Expected: PASS. `test_remove_script_clears_pointer_and_second_call_is_noop` asserts only the status code, so the new `kept` key is fine. If any existing test asserts `resp.get_json() == {"success": True}` for attach/detach, update it to the new shape.

- [ ] **Step 7: Full backend suite**

Run: `cd backend && pytest tests/ -q`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add backend/services/production_service.py backend/routes/production_routes.py backend/tests/test_production_script_team.py backend/tests/test_production_routes.py
git commit -m "feat(productions): attach prompts to move/drop script team; detach can keep members

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Frontend — API service + Members tab script access

**Files:**
- Modify: `frontend/src/services/apiService.js` (~2515-2545)
- Modify: `frontend/src/components/productions/ProductionMembersTab.jsx`
- Modify: `frontend/src/pages/ProductionDetailPage.jsx` (`NO_ACCESS`; Members tab render)

**Interfaces:**
- Produces:
  - `addScriptToProduction(id, scriptId, membersAction = null)` — sends `members_action` only when set.
  - `removeScriptFromProduction(id, scriptId, keepUserIds = [])` — sends `{keep_user_ids}` as the DELETE body.
  - `ProductionMembersTab` prop `scriptCount: number`.

- [ ] **Step 1: Update apiService**

Replace `addScriptToProduction` and `removeScriptFromProduction` with:

```js
/**
 * Attach a script the caller owns to a production. 409 if the script is
 * already in a production, or 409 {code: 'script_has_members', members,
 * invites} when the script has its own team and no membersAction was given.
 * @param {string} id  production id
 * @param {string} scriptId
 * @param {'move'|'drop'|null} membersAction
 */
export const addScriptToProduction = async (id, scriptId, membersAction = null) => {
    try {
        const body = { script_id: scriptId };
        if (membersAction) body.members_action = membersAction;
        const response = await api.post(`/api/productions/${id}/scripts`, body);
        return response.data;
    } catch (error) {
        console.error('Error adding script to production:', error);
        throw error;
    }
};

/**
 * Detach a script from a production. Production members lose access unless
 * listed in keepUserIds (they get a direct script-team row).
 * @param {string} id  production id
 * @param {string} scriptId
 * @param {string[]} keepUserIds
 */
export const removeScriptFromProduction = async (id, scriptId, keepUserIds = []) => {
    try {
        const response = await api.delete(`/api/productions/${id}/scripts/${scriptId}`, {
            data: { keep_user_ids: keepUserIds },
        });
        return response.data;
    } catch (error) {
        console.error('Error removing script from production:', error);
        throw error;
    }
};
```

- [ ] **Step 2: Members tab constants**

In `ProductionMembersTab.jsx`, add `script_access` to each preset (`admin: 'edit'`, `coordinator: 'edit'`, `viewer: 'view'`) — e.g. in `admin` add `script_access: 'edit',` as the last key. Below `RANK` add:

```js
const SCRIPT_ACCESS_OPTIONS = [
    { value: 'none', label: 'None' },
    { value: 'view', label: 'View' },
    { value: 'edit', label: 'Edit' },
];
const ACCESS_RANK = { none: 0, view: 1, edit: 2 };
```

Add to `CODE_MESSAGES`:

```js
    bad_script_access: 'Script access must be None, View or Edit.',
```

- [ ] **Step 3: Members tab component**

Change the signature to `export default function ProductionMembersTab({ productionId, access, scriptCount = 0 })` and below `const isOwner = ...` add:

```js
    const myAccessRank = isOwner ? ACCESS_RANK.edit : (ACCESS_RANK[access?.script_access] ?? 0);
    const accessAllowed = (v) => isOwner || ACCESS_RANK[v] <= myAccessRank;
```

Under the `production-scripts-head` div add:

```jsx
            <p className="members-script-hint">
                Script access applies to all scripts in this production ({scriptCount}).
            </p>
```

In the members table header, after `<th>Role</th>` add `<th>Script access</th>`. In each row, after the role `<td>` add:

```jsx
                                    <td>
                                        <select
                                            value={m.script_access || 'none'}
                                            disabled={locked}
                                            onChange={(e) => patchMember(m, { script_access: e.target.value })}
                                        >
                                            {SCRIPT_ACCESS_OPTIONS.map((o) => (
                                                <option key={o.value} value={o.value}
                                                    disabled={!accessAllowed(o.value) && o.value !== m.script_access}>
                                                    {o.label}
                                                </option>
                                            ))}
                                        </select>
                                    </td>
```

Change the empty-row `colSpan` to `{4 + Object.keys(CAP_LABELS).length + 1}`.

In the invites table add `<th>Script access</th>` after `<th>Role</th>` and `<td>{inv.script_access || 'none'}</td>` after `<td>{inv.role}</td>`.

Pass `myAccessRank`/`accessAllowed` into the modal: `<AddMemberModal ... accessAllowed={accessAllowed} />`.

- [ ] **Step 4: Add-member modal**

Change the signature to `function AddMemberModal({ productionId, myRank, isOwner, accessAllowed, onClose, onDone, setError })`. The `flags` state already starts from `PRESETS.viewer` (now including `script_access`) and is sent with `...flags`. After the Role `<label>` add:

```jsx
                    <label className="contact-field">
                        <span>Script access</span>
                        <select
                            value={flags.script_access}
                            onChange={(e) => {
                                setTouched(true);
                                setFlags((f) => ({ ...f, script_access: e.target.value }));
                            }}
                        >
                            {SCRIPT_ACCESS_OPTIONS.filter((o) => accessAllowed(o.value)).map((o) => (
                                <option key={o.value} value={o.value}>{o.label}</option>
                            ))}
                        </select>
                    </label>
```

- [ ] **Step 5: Detail page wiring**

In `ProductionDetailPage.jsx`, add `script_access: 'none',` to `NO_ACCESS`, and pass `scriptCount={scripts.length}` to `<ProductionMembersTab>`.

Add to `frontend/src/pages/ProductionPages.css`:

```css
.members-script-hint { color: #6b7a94; margin: 4px 0 12px; font-size: 13px; }
```

- [ ] **Step 6: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/services/apiService.js frontend/src/components/productions/ProductionMembersTab.jsx frontend/src/pages/ProductionDetailPage.jsx frontend/src/pages/ProductionPages.css
git commit -m "feat(productions-ui): script access setting on members and invites

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Frontend — attach prompt, detach modal, delete copy, `?tab=`

**Files:**
- Modify: `frontend/src/components/productions/ProductionScriptPicker.jsx`
- Create: `frontend/src/components/productions/DetachScriptModal.jsx`
- Modify: `frontend/src/components/productions/ProductionOverviewTab.jsx`
- Modify: `frontend/src/pages/ProductionDetailPage.jsx`
- Modify: `frontend/src/pages/ProductionPages.css`

**Interfaces:**
- Consumes: `addScriptToProduction(id, scriptId, membersAction)`, `removeScriptFromProduction(id, scriptId, keepUserIds)`, `listProductionMembers(id)` (existing, returns `{members, invites}` with `script_access`).
- Produces: `ProductionScriptPicker` `onPick(scriptId, membersAction)`; `ProductionOverviewTab` `onRemove(script)`; `DetachScriptModal({ productionId, script, onConfirm(keepIds), onClose })`.

- [ ] **Step 1: Picker with move/drop prompt**

Replace `ProductionScriptPicker.jsx` with:

```jsx
import { useState, useEffect } from 'react';
import { getScripts } from '../../services/apiService';
import { Spinner } from '../ui';

export default function ProductionScriptPicker({ onPick, onClose }) {
    const [scripts, setScripts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [busyId, setBusyId] = useState(null);
    // Set when the server answers 409 script_has_members: {scriptId, members, invites}
    const [team, setTeam] = useState(null);

    useEffect(() => {
        getScripts()
            .then((data) => setScripts((data.scripts || []).filter(
                (s) => !s.production_id && (s.is_owner ?? true))))
            .catch((err) => setError(err.message || 'Failed to load scripts'))
            .finally(() => setLoading(false));
    }, []);

    const pick = async (scriptId, membersAction = null) => {
        setBusyId(scriptId);
        setError(null);
        try {
            await onPick(scriptId, membersAction);
        } catch (err) {
            const status = err.response?.status;
            const data = err.response?.data || {};
            if (status === 409 && data.code === 'script_has_members') {
                setTeam({ scriptId, members: data.members || [], invites: data.invites || [] });
            } else if (membersAction) {
                // The script may already be attached; re-sending the same choice
                // is safe (the server treats "already here" as success).
                setError(`${data.error || 'Moving the team failed'}. Try again.`);
            } else {
                setError(data.error || 'Could not add that script');
            }
            setBusyId(null);
        }
    };

    const teamCount = team ? team.members.length : 0;
    const inviteCount = team ? team.invites.length : 0;

    return (
        <div className="production-modal-backdrop" onClick={onClose}>
            <div className="production-modal" onClick={(e) => e.stopPropagation()}>
                <h3>{team ? 'This script has its own team' : 'Add a script'}</h3>
                {error && <p className="production-page-error">{error}</p>}
                {team ? (
                    <div className="production-attach-team">
                        <p>
                            {teamCount} team member{teamCount === 1 ? '' : 's'}
                            {inviteCount > 0 && ` and ${inviteCount} pending invite${inviteCount === 1 ? '' : 's'}`}
                            {' '}can open this script. Once it is in the production, access is
                            managed from the production&apos;s Members tab.
                        </p>
                        <ul className="production-attach-list">
                            {team.members.map((m) => (
                                <li key={m.user_id}>{m.name} <span>({m.role})</span></li>
                            ))}
                            {team.invites.map((i) => (
                                <li key={i.email}>{i.email} <span>(invite pending)</span></li>
                            ))}
                        </ul>
                        <p className="production-attach-note">
                            Moved people join the production as viewers — they will also see its
                            crew, locations and call sheets — with their script access carried over.
                        </p>
                        <div className="production-overview-actions">
                            <button disabled={!!busyId} onClick={() => pick(team.scriptId, 'move')}>
                                Move to production
                            </button>
                            <button className="production-delete-btn" disabled={!!busyId}
                                onClick={() => pick(team.scriptId, 'drop')}>
                                Remove their access
                            </button>
                            <button className="production-modal-close" disabled={!!busyId}
                                onClick={() => { setTeam(null); setError(null); }}>
                                Back
                            </button>
                        </div>
                    </div>
                ) : loading ? (
                    <Spinner size={24} />
                ) : !error && scripts.length === 0 ? (
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
                {!team && <button className="production-modal-close" onClick={onClose}>Close</button>}
            </div>
        </div>
    );
}
```

- [ ] **Step 2: Detach modal**

Create `frontend/src/components/productions/DetachScriptModal.jsx`:

```jsx
import { useState, useEffect } from 'react';
import { listProductionMembers } from '../../services/apiService';
import { Spinner } from '../ui';

export default function DetachScriptModal({ productionId, script, onConfirm, onClose }) {
    const [members, setMembers] = useState([]);
    const [keep, setKeep] = useState(() => new Set());
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        listProductionMembers(productionId)
            .then((d) => setMembers((d.members || []).filter(
                (m) => m.script_access && m.script_access !== 'none')))
            .catch((e) => setError(e.response?.data?.error || 'Failed to load members'))
            .finally(() => setLoading(false));
    }, [productionId]);

    const toggle = (userId) => setKeep((prev) => {
        const next = new Set(prev);
        if (next.has(userId)) next.delete(userId); else next.add(userId);
        return next;
    });

    const confirm = async () => {
        setBusy(true);
        setError(null);
        try {
            await onConfirm([...keep]);
        } catch (e) {
            setError(e.response?.data?.error || 'Failed to remove script');
            setBusy(false);
        }
    };

    return (
        <div className="production-modal-backdrop" onClick={onClose}>
            <div className="production-modal" onClick={(e) => e.stopPropagation()}>
                <h3>Remove “{script.title || 'Untitled script'}” from this production?</h3>
                {error && <p className="production-page-error">{error}</p>}
                {loading ? (
                    <Spinner size={24} />
                ) : members.length === 0 ? (
                    <p>No production members currently have access to this script.</p>
                ) : (
                    <>
                        <p>
                            These members will lose access to the script. Tick anyone who should
                            keep it on the script&apos;s own team.
                        </p>
                        <ul className="production-attach-list">
                            {members.map((m) => (
                                <li key={m.user_id}>
                                    <label>
                                        <input type="checkbox" checked={keep.has(m.user_id)}
                                            onChange={() => toggle(m.user_id)} />
                                        {' '}{m.name} <span>({m.script_access})</span> — keep on script
                                    </label>
                                </li>
                            ))}
                        </ul>
                    </>
                )}
                <div className="production-overview-actions">
                    <button className="production-delete-btn" disabled={busy || loading} onClick={confirm}>
                        {busy ? 'Removing…' : 'Remove script'}
                    </button>
                    <button className="production-modal-close" disabled={busy} onClick={onClose}>
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
}
```

- [ ] **Step 3: Overview tab**

In `ProductionOverviewTab.jsx`:
- change `onClick={() => onRemove(s.id)}` to `onClick={() => onRemove(s)}`;
- replace the empty-state paragraph with:

```jsx
                    <p className="production-scripts-empty">
                        {canDelete ? 'No scripts attached yet.' : 'No scripts shared with you in this production.'}
                    </p>
```

- [ ] **Step 4: Detail page**

In `ProductionDetailPage.jsx`:

Imports: change the router import to `import { useParams, useNavigate, Link, useSearchParams } from 'react-router-dom';`, add `listProductionMembers` to the apiService import, and add `import DetachScriptModal from '../components/productions/DetachScriptModal';`.

Above the component add:

```js
const TAB_IDS = ['overview', 'crew', 'locations', 'callsheet', 'members'];
```

Replace `const [activeTab, setActiveTab] = useState('overview');` with:

```js
    const [searchParams] = useSearchParams();
    const [activeTab, setActiveTab] = useState(() => {
        const t = searchParams.get('tab');
        return TAB_IDS.includes(t) ? t : 'overview';
    });
    const [detaching, setDetaching] = useState(null);
```

In the tab-guard `useEffect`, add `if (loading) return;` as the first line and add `loading` to its dependency array (otherwise `?tab=members` is reset before access loads).

Replace `handleDelete`, `handlePick`, `handleRemove` with:

```js
    const handleDelete = async () => {
        let memberCount = 0;
        try {
            const d = await listProductionMembers(productionId);
            memberCount = (d.members || []).length;
        } catch {
            // Count is only for the warning copy; proceed without it.
        }
        const warn = memberCount > 0
            ? ` ${memberCount} member${memberCount === 1 ? '' : 's'} will lose access to its ${scripts.length} script${scripts.length === 1 ? '' : 's'}.`
            : '';
        if (!window.confirm(`Delete this production? Its scripts are kept and just unlinked.${warn}`)) return;
        try {
            await deleteProduction(productionId);
            navigate('/productions');
        } catch (err) {
            setError(err.response?.data?.error || 'Delete failed');
        }
    };

    const handlePick = async (scriptId, membersAction = null) => {
        await addScriptToProduction(productionId, scriptId, membersAction);
        setPicking(false);
        load();
    };

    const handleRemove = (script) => setDetaching(script);

    const confirmDetach = async (keepUserIds) => {
        await removeScriptFromProduction(productionId, detaching.id, keepUserIds);
        setScripts((prev) => prev.filter((s) => s.id !== detaching.id));
        setDetaching(null);
        setError(null);
    };
```

Before the final closing `</div>` of the page add:

```jsx
            {detaching && (
                <DetachScriptModal
                    productionId={productionId}
                    script={detaching}
                    onConfirm={confirmDetach}
                    onClose={() => setDetaching(null)}
                />
            )}
```

- [ ] **Step 5: Styles**

Append to `frontend/src/pages/ProductionPages.css`:

```css
.production-attach-list { list-style: none; padding: 0; margin: 8px 0 12px; }
.production-attach-list li { padding: 4px 0; }
.production-attach-list span { color: #6b7a94; }
.production-attach-note { color: #6b7a94; font-size: 13px; }
```

- [ ] **Step 6: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/productions/ProductionScriptPicker.jsx frontend/src/components/productions/DetachScriptModal.jsx frontend/src/components/productions/ProductionOverviewTab.jsx frontend/src/pages/ProductionDetailPage.jsx frontend/src/pages/ProductionPages.css
git commit -m "feat(productions-ui): move/drop prompt on attach, keep-on-script detach, ?tab= deep link

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Frontend — Team drawer notice, View-only badge, shared tooltip

**Files:**
- Create: `frontend/src/utils/scriptRole.js`
- Modify: `frontend/src/components/team/TeamDrawer.jsx`, `frontend/src/components/team/TeamDrawer.css`
- Modify: `frontend/src/components/metadata/ScriptHeader.jsx`, `frontend/src/components/metadata/ScriptHeader.css`
- Modify: `frontend/src/components/scripts/ScriptTable.jsx:198-204`

**Interfaces:**
- Consumes: metadata fields `my_role`, `production_id`, `production_title`, `can_manage_production_members` (Task 4); list `membership.via_production` + `production_title` (Task 4).
- Produces: `SCRIPT_ROLE_RANK`, `canEditScript(role) -> boolean` in `utils/scriptRole.js` (used now by the badge, later by the D1 sweep); `TeamDrawer` props `productionId`, `productionTitle`, `canManageProductionMembers`.

- [ ] **Step 1: Role helper**

Create `frontend/src/utils/scriptRole.js`:

```js
// Script-axis roles, mirroring backend middleware/authorization.ROLE_RANK.
// UX only — the backend's require_script_role is the real enforcement.
export const SCRIPT_ROLE_RANK = { viewer: 1, member: 2, admin: 3, owner: 4 };

/** True when the role may edit script content (member and above). */
export const canEditScript = (role) =>
    (SCRIPT_ROLE_RANK[role] || 0) >= SCRIPT_ROLE_RANK.member;
```

- [ ] **Step 2: TeamDrawer notice**

In `TeamDrawer.jsx`:
- add `productionId`, `productionTitle`, `canManageProductionMembers` to the destructured props;
- in the seat-draft resume effect, change the guard to `if (!isOpen || !scriptId || productionId) return;` and add `productionId` to its deps;
- in the fetch effect, change the guard to `if (!isOpen || !scriptId || !hasTeamAccess || productionId) return;` and add `productionId` to its deps;
- replace `{!hasTeamAccess ? (` inside `team-drawer-body` with:

```jsx
                    {productionId ? (
                        <div className="team-drawer-managed">
                            <p>
                                Access for this script is managed in{' '}
                                {canManageProductionMembers ? (
                                    <Link to={`/productions/${productionId}?tab=members`} onClick={onClose}>
                                        <strong>{productionTitle || 'its production'} → Members</strong>
                                    </Link>
                                ) : (
                                    <strong>{productionTitle || 'its production'} → Members</strong>
                                )}
                                .
                            </p>
                            <p className="team-drawer-managed-hint">
                                Everyone in the production can open this script at the script
                                access level set there.
                            </p>
                        </div>
                    ) : !hasTeamAccess ? (
```

Append to `TeamDrawer.css`:

```css
.team-drawer-managed { padding: 16px 4px; line-height: 1.5; }
.team-drawer-managed a { color: inherit; }
.team-drawer-managed-hint { color: #6b7a94; font-size: 13px; margin-top: 8px; }
```

- [ ] **Step 3: ScriptHeader**

In `ScriptHeader.jsx` add `import { canEditScript } from '../../utils/scriptRole';`. After `<span className="scene-count-badge">…</span>` add:

```jsx
            {metadata?.my_role && !canEditScript(metadata.my_role) && (
                <span className="script-view-only-badge" title="You have view-only access to this script">
                    View only
                </span>
            )}
```

Pass the production props to `<TeamDrawer>`:

```jsx
                productionId={metadata?.production_id || null}
                productionTitle={metadata?.production_title || null}
                canManageProductionMembers={isOwner || !!metadata?.can_manage_production_members}
```

Append to `ScriptHeader.css`:

```css
.script-view-only-badge {
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 999px;
    background: #eef1f6;
    color: #4a5670;
}
```

- [ ] **Step 4: ScriptTable tooltip**

In `ScriptTable.jsx`, replace the `title={...}` of the `shared-badge` span with:

```jsx
                                title={script.membership?.via_production
                                    ? `Shared via ${script.production_title || 'a production'}${script.membership?.role ? ` — role: ${script.membership.role}` : ''}`
                                    : (script.membership?.role ? `Shared with you — role: ${script.membership.role}` : 'Shared with you')}
```

- [ ] **Step 5: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/utils/scriptRole.js frontend/src/components/team/TeamDrawer.jsx frontend/src/components/team/TeamDrawer.css frontend/src/components/metadata/ScriptHeader.jsx frontend/src/components/metadata/ScriptHeader.css frontend/src/components/scripts/ScriptTable.jsx
git commit -m "feat(scripts-ui): production-managed Team drawer notice, View only badge, shared-via tooltip

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Verification, backlog, hand-off

**Files:**
- Modify: `docs/BACKLOG.md`

- [ ] **Step 1: Full gates**

Run: `cd backend && pytest tests/ -q` — expected: all pass.
Run: `cd frontend && npm run build` — expected: succeeds.

- [ ] **Step 2: Backlog entry for the D1 sweep**

Add a section to `docs/BACKLOG.md`:

```markdown
## Role-aware edit controls on script pages (production script access D1 follow-up)

**Status:** Not started — needs its own plan.

**Context.** Production script access (spec
`docs/superpowers/specs/2026-09-23-production-script-access-design.md`) puts
many members at script `viewer`. The foundation shipped: script metadata
returns `my_role`, `frontend/src/utils/scriptRole.js` exports
`canEditScript`, and `ScriptHeader` shows a "View only" badge. Viewers still
see write controls that 403.

**Work.** For each script page (`SceneViewer`, `SceneManager`, `Stripboard`,
`ZoomableStripboard`, `ShootingSchedulePage`, `ReportStudio`, `CastPage`)
and its children, hide/disable write controls when `!canEditScript(my_role)`
— but first audit each write call's backend `require_script_role(min_role)`
so controls viewers ARE allowed (e.g. anything gated at `viewer`) stay
visible. Add a `useScriptRole(scriptId)` hook reading `my_role` from
`getScriptMetadata`.
```

- [ ] **Step 3: Commit**

```bash
git add docs/BACKLOG.md
git commit -m "docs(backlog): D1 role-aware script controls follow-up

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 4: Hand-off note to the user**

Tell the user: migration `backend/db/migrations/056_production_script_access.sql` must be applied manually in Supabase (project `twzfaizeyqwevmhjyicz`) **before** the backend deploys — `get_script_role` and the member routes read `script_access`. Then run the manual scenario from the spec's Testing section.
