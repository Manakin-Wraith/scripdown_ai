# Production Spine — Build-Sequence Step 1 Design

**Date:** 2026-08-31
**Status:** Design approved — ready for implementation plan
**Type:** Architectural
**Parent:** `docs/superpowers/specs/2026-08-31-production-data-model-design.md`
(umbrella direction spec — build-sequence step 1: "the spine")

## Purpose

Stand up the `production` entity and its minimal surface so the downstream
slices (crew, locations, call sheets, production-level schedule, DPR,
department workspaces) have something to attach to. This step deliberately
builds the thinnest useful vertical slice plus the `units` table (nearly
free, keeps the DPR promise). Everything else named in the umbrella spec is
deferred to the slice that needs it.

## Scope

**In:**

- `productions` table + `units` table + `scripts.production_id` column
  (migration `050_productions.sql`, applied manually to the Supabase
  project — `run_migration.py` is dead, per the casting migration notes)
- Backend blueprint `production_bp` (`routes/production_routes.py` +
  `services/production_service.py`) — CRUD + script association
- Frontend: `/productions` list, `/productions/:productionId` detail
  (editable Overview + associated-scripts list with add/remove), nav link
- One "Main Unit" auto-created per production; no unit UI

**Out (named, deferred to the slice that needs it):**

- `production_members`, member-management UI, `can_view_sensitive`
  → crew slice (build-sequence step 2)
- `contacts` / `locations` / `production_crew` directories → steps 2–3
- Upload-flow production picker (beside `SeriesPicker` in
  `ScriptUpload.jsx`) → fast-follow
- My Scripts (`ScriptTable`) production grouping / badges → fast-follow
- "Add all of a season's episodes to this production" bulk action → fast-follow
  (step 1 adds scripts one at a time; with driver D — many episodes — this
  will be wanted quickly)
- `shooting_days.unit_id` column → added with the schedule/DPR slice; no
  reader/writer exists in step 1
- Unit management (rename, add, reorder, delete) → DPR slice or when a
  consumer appears
- Cross-script / production-level scheduling
  (`shooting_schedules.production_id`) → step 5
- Permission inheritance (production admin → access to the production's
  scripts) → deferred; production and script access stay independent for
  now

## Data model

Migration `backend/db/migrations/050_productions.sql`.

### `productions`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid pk | `default gen_random_uuid()` |
| `owner_id` | uuid not null | → `profiles(id) on delete cascade`. `profiles.id` equals the `auth.users` id, i.e. the value `get_user_id()` returns and `scripts.user_id` / `get_script_role` compare against. (`account_seats.owner_id` references `profiles(id)` the same way; `series.owner_id` references `auth.users(id)` — same value, pick `profiles(id)` here to match the billing tables.) |
| `title` | text not null | |
| `status` | text not null | `default 'development'`, `CHECK (status IN ('development','prep','shooting','wrapped','archived'))` |
| `shoot_start_date` | date null | |
| `shoot_end_date` | date null | |
| `notes` | text null | |
| `created_by` | uuid null | → `auth.users(id) on delete set null`. Kept (not YAGNI-dropped like `format`) purely so an audit/"created by X" line is possible later; always equals `owner_id` until ownership transfer exists. Drop it if the plan reviewer prefers. |

Table-level constraint:
`CHECK (shoot_end_date IS NULL OR shoot_start_date IS NULL OR shoot_end_date >= shoot_start_date)`
(mirrors `casting_unavailability`'s date-order check).
| `created_at` | timestamptz not null | `default now()` |
| `updated_at` | timestamptz not null | `default now()`; `BEFORE UPDATE` trigger reusing `update_shooting_updated_at()` from migration 030 |

Index: `idx_productions_owner ON productions(owner_id)`.

`format` and `production_company` are intentionally omitted — series/season
already signals TV, the account owner is effectively the company, and
nothing in the build sequence consumes either. Add when a consumer appears.

### `units`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid pk | `default gen_random_uuid()` |
| `production_id` | uuid not null | → `productions(id) on delete cascade` |
| `name` | text not null | `default 'Main Unit'` |
| `sort_order` | int not null | `default 0` |
| `created_at` | timestamptz not null | `default now()` |

Index: `idx_units_production ON units(production_id)`.

One row auto-inserted (`name = 'Main Unit'`, `sort_order = 0`) when a
production is created — in `production_service.create_production`, same
transaction-ish sequence as `create_series` inserting its first season.
The literal string `'Main Unit'` is what the DPR spec's velocity logic
expects to find as the default unit, so keep it verbatim.

**Not added in step 1:** `shooting_days.unit_id` (named in the umbrella
entity model). No reader or writer exists until the schedule/DPR slice, so
adding the column now would be speculative. The `units` rows created here
simply wait for that slice.

### `scripts.production_id`

```sql
ALTER TABLE scripts
    ADD COLUMN IF NOT EXISTS production_id UUID REFERENCES productions(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_scripts_production ON scripts(production_id);
```

Nullable. A script belongs to **at most one** production; a production holds
**many** scripts (a season's episodes, a feature + its reshoot). Independent
of `scripts.season_id` — a script may have either, both, or neither.

**User deletion:** `013_delete_user_safely.sql` (a manual admin script)
deletes `scripts` then `profiles`. Because `productions.owner_id` is
`ON DELETE CASCADE`, deleting the profile cascades to `productions` →
`units` with no FK error or orphan. Add a comment to migration 050 noting
the cascade is load-bearing for that script — do not "soften" `owner_id`
to `SET NULL`.

### RLS

Owner-only policies on `productions` and `units` as a defense-in-depth
backstop, matching the pattern in `045_series_seasons.sql` (the backend uses
the service-role key and enforces access in Python; RLS only guards any
direct client-side table access).

**RLS is intentionally narrower than the app.** `GET /api/productions/:id`
lets a team member with a script role read the production (see Backend
below); the owner-only RLS policy does not. This is not a bug — it is the
exact `series` arrangement, where RLS is only a direct-client backstop and
all real reads go through the service-role key with Python enforcement.

```sql
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

## Backend

New blueprint `production_bp`, registered in `app.py` after `casting_bp`.
Follows the casting pattern: thin `routes/production_routes.py` over
`services/production_service.py`. Access helpers live in the service
module, not `middleware/authorization.py` (that module is script-role
specific; `series_routes.py` likewise keeps its `_user_owns_series` local).

### Routes

| Method / path | Access | Behavior |
|---|---|---|
| `POST /api/productions` | `@require_auth`, any user | Body `{title, status?, shoot_start_date?, shoot_end_date?, notes?}`. Creates the production (`owner_id = caller`, `created_by = caller`) and auto-inserts one "Main Unit". Returns `{production, unit}`. 201. |
| `GET /api/productions` | `@require_auth` | Owner-scoped list: `productions WHERE owner_id = caller`. Mirrors `list_series` — intentionally not "every production I have script access in". |
| `GET /api/productions/<production_id>` | owner **or** viewer+ on any script in the production | Returns `{production, scripts: [...]}` where `scripts` is the associated scripts filtered to those the caller can access (owner sees all associated; a team member sees the ones they hold a role on). Mirrors `list_seasons` / `_visible_episode_scripts`. 404 if the production doesn't exist; 403 if no owner and no accessible script. |
| `PATCH /api/productions/<production_id>` | owner only | Body: any of `{title, status, shoot_start_date, shoot_end_date, notes}`. 403 if not owner, 404 if absent. |
| `DELETE /api/productions/<production_id>` | owner only | Deletes the production. `scripts.production_id` → NULL via `ON DELETE SET NULL`; units cascade. |
| `POST /api/productions/<production_id>/scripts` | owner only | Body `{script_id}`. 403 if the script isn't owned by the caller (`scripts.user_id == caller`). Association is a **single conditional UPDATE** — `UPDATE scripts SET production_id = :pid WHERE id = :sid AND user_id = :caller AND production_id IS NULL` — and a zero-row result → 409 `{error: 'Script already belongs to a production'}`. Read-then-write is **not** acceptable here (concurrent requests would both pass a prior `SELECT ... IS NULL` check — the same race class already logged against `casting` group-create). |
| `DELETE /api/productions/<production_id>/scripts/<script_id>` | owner only | Clears `scripts.production_id` (only if it currently points at this production). |

No unit routes in step 1 — nothing consumes them yet.

### `services/production_service.py`

- `create_production(user_id, fields) -> {production, unit}` — insert +
  Main Unit insert
- `list_productions(user_id) -> [production]`
- `get_production_for_viewer(production_id, user_id) -> {production, scripts} | None | NOT_FOUND`
  — resolves owner-or-script-member visibility, reusing
  `get_script_role` from `middleware/authorization.py` for the per-script
  filter (same as `_visible_episode_scripts`)
- `update_production(production_id, fields)`
- `delete_production(production_id)`
- `add_script(production_id, script_id, user_id)` — single conditional
  `UPDATE ... WHERE production_id IS NULL AND user_id = :user_id`; returns
  whether a row was affected (caller maps `False` → 409, and distinguishes
  "not owned" → 403 with a cheap ownership pre-check for the right status
  code)
- `remove_script(production_id, script_id)` — conditional
  `UPDATE scripts SET production_id = NULL WHERE id = :sid AND production_id = :pid`;
  a no-match is a 200 no-op
- `_user_owns_production(production_id, user_id) -> bool` — local helper,
  mirrors `_user_owns_series`

### `GET /api/scripts` — add `production_id`

The existing scripts listing (`supabase_routes.py`) does not return the new
column. The `ProductionScriptPicker` needs "my scripts where `production_id`
is null," and the deferred My Scripts view will need the association too.
Add `production_id` (and `production_title` via a batched join, the way
`_attach_series_info` already attaches `series_title` / `season_number`) to
the `GET /api/scripts` response. This is the one touch to an existing
endpoint in step 1.

## Frontend

### `services/apiService.js`

`listProductions()`, `createProduction(payload)`, `getProduction(id)`,
`updateProduction(id, payload)`, `deleteProduction(id)`,
`addScriptToProduction(id, scriptId)`,
`removeScriptFromProduction(id, scriptId)` — all through the single axios
instance, no new instance.

### Pages / components

- `pages/ProductionsListPage.jsx` — owner's productions as a styled row
  list (mirror `SeriesListPage.jsx`), "New production" action (inline form
  or small modal: title + optional dates), full-page loading/error/empty
  states matching the series pages.
- `pages/ProductionDetailPage.jsx` — editable Overview panel (title,
  status `<select>`, start/end dates, notes) with save; associated-scripts
  list, each row linking to `/scenes/:scriptId` with a "Remove" action;
  "Add script" opens the picker. Owner-only controls hidden/disabled for a
  non-owner viewer (parallels how the series pages degrade).
- `components/productions/ProductionScriptPicker.jsx` — modal listing the
  caller's scripts with `production_id == null`; single-select → calls
  `addScriptToProduction`.
- `pages/ProductionPages.css` — reuse the dark-navy/amber token system from
  `SeriesPages.css` / `ScriptTable.css`.

### Routing & nav

- `App.jsx`: `<Route path="productions" element={<ProductionsListPage />} />`
  and `<Route path="productions/:productionId" element={<ProductionDetailPage />} />`
  under the existing `ProtectedRoute` layout.
- `components/layout/TopBar.jsx`: a "Productions" `NavLink` in
  `.topbar-nav` immediately after the "Series" link. This makes three
  top-level items ("My Scripts", "Series", "Productions") — check
  `.topbar-nav` wrapping / overflow at narrow widths and tighten spacing
  if needed (no redesign; just don't let it break the bar).

## Testing

### Backend — `backend/tests/test_production_routes.py` (new)

- **Auth / visibility:**
  - anonymous → 401 on every route
  - `GET /api/productions` returns only the caller's productions
  - `GET /api/productions/:id` — owner 200; a `script_members` viewer on
    an associated script 200 with only their accessible scripts listed; an
    unrelated authed user 403; nonexistent id 404
  - `PATCH` / `DELETE` / script-association routes — non-owner 403
- **CRUD:**
  - `POST` creates the production and exactly one unit named "Main Unit"
  - `PATCH` updates only the provided fields
  - `DELETE` removes the production and leaves formerly-associated scripts
    with `production_id IS NULL`
- **Association guards:**
  - `POST .../scripts` with an already-assigned script → 409 (assert via
    the conditional-UPDATE zero-row path, not a pre-`SELECT`)
  - `POST .../scripts` with a script the caller doesn't own → 403
  - `DELETE .../scripts/:id` clears the pointer; a second delete is a
    no-op 200
  - `POST .../scripts` with a script already in *this same* production →
    409 (not a silent success)
- **`GET /api/scripts` regression:** response now includes `production_id`
  (null when unassigned, the id when assigned); existing scripts-list
  tests still pass.
- Full suite (`pytest tests/`) stays green.

### Frontend

- `npm run build` green (repo lint is broken — see project memory — so
  build is the gate).
- Manual: create a production, add two scripts, edit Overview, remove a
  script, delete the production; confirm the scripts survive in My Scripts.

## Reconciliation with existing systems

| System | Change |
|---|---|
| `series` / `seasons` | None. `scripts.production_id` and `scripts.season_id` are independent nullable FKs. |
| `casting`, `script_members`, `departments`, `shooting_schedules` | None. |
| `GET /api/scripts` (`supabase_routes.py`) | Adds `production_id` (+ `production_title`) to the response, mirroring `_attach_series_info`. The one existing-endpoint touch in step 1. |
| `middleware/authorization.py` | None — `get_script_role` is reused read-only by `production_service` for the per-script visibility filter. No new resolver added there. |
| `013_delete_user_safely.sql` | No edit needed — `productions.owner_id ON DELETE CASCADE` makes the existing `DELETE FROM profiles` cascade cleanly. Migration 050 carries a comment saying so. |
| `app.py` | One `register_blueprint(production_bp)` line. |
| Billing / seats | None. A production consumes nothing; `production_members` (which would consume seats) is deferred to the crew slice. |

## Open questions resolved

- **Thin spine or full skeleton?** → Thin + `units` table (umbrella spec
  option C).
- **Visibility without `production_members`?** → Mirror `series`: owner
  lists/edits; a team member with viewer+ on an associated script can open
  the detail page read-only.
- **Fields?** → `title`, `status`, shoot dates, `notes`. No `format` /
  `production_company`.
- **Delete semantics?** → Production delete: scripts survive,
  `production_id` → NULL, units cascade. Script delete: production
  unaffected.
- **Association?** → Owner-gated, on the production detail page; script
  must be owned and unassigned (≤1 production per script). Upload-flow
  picker deferred.
- **My Scripts / scenes view changes?** → Deferred to a fast-follow.

## References

- `docs/superpowers/specs/2026-08-31-production-data-model-design.md` —
  parent umbrella spec
- `backend/routes/series_routes.py` — the route/visibility pattern this
  mirrors (`create_series` + first-season insert; `list_seasons` /
  `_visible_episode_scripts` visibility; `_user_owns_series`)
- `backend/db/migrations/045_series_seasons.sql` — nullable-FK + RLS pattern
- `backend/db/migrations/048_casting.sql` — service-layer + manual-migration
  pattern; `update_shooting_updated_at()` trigger reuse
- `backend/middleware/authorization.py` — `get_script_role`, `ROLE_RANK`,
  `SCRIPT_NOT_FOUND`
- `frontend/src/pages/SeriesListPage.jsx`, `SeasonPage.jsx`,
  `SeriesPages.css` — page patterns and token system
- `frontend/src/components/layout/TopBar.jsx` — top nav
- `frontend/src/App.jsx` — route registration
