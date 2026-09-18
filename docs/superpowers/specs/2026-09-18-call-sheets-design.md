# Call Sheets — Build-Sequence Step 4 Design

**Date:** 2026-09-18
**Status:** Design approved — ready for implementation plan
**Type:** Architectural
**Parent:** `docs/superpowers/specs/2026-08-31-production-data-model-design.md`
(umbrella direction spec — build-sequence step 4)
**Siblings:** `2026-08-31-crew-contacts-design.md` (step 2a),
`2026-09-01-production-members-design.md` (step 2b, shipped `8477e82`),
`2026-09-02-locations-directory-design.md` (step 3, shipped)

## Purpose

Give a production the ability to generate a single-page-per-day call sheet
PDF for a specific `shooting_day`: who's needed, when, where, and the
day's key operational info (weather, hospital, parking, notices). This is
the first concrete "produce a physical document from the production data
model" feature — it consumes crew (2a), the permission layer (2b), and
locations (step 3) directly, and reads the existing shoot-day/scene
schedule (migration 030) rather than building new scheduling.

**Sides** (excerpted script pages for the day's scenes) are explicitly
**out of scope** for this slice — a deliberate fast-follow, not forgotten.

## Scope

**In:**

- Migration `054_call_sheets.sql`: `call_sheets`, `call_sheet_locations`,
  `call_sheet_crew`, `call_sheet_cast` tables.
- New blueprint `call_sheet_bp` (`routes/call_sheet_routes.py` +
  `services/call_sheet_service.py`) — CRUD for a day's call sheet, roster,
  and locations.
- PDF rendering (`call_sheet_service.render_call_sheet_pdf`), reusing
  `report_service.py`'s WeasyPrint pipeline and `_get_pdf_css()` helper.
- New `can_edit_call_sheets` capability in `production_authz.py`, plus a
  `from_call_sheet_id` resolver.
- Frontend: a call sheet entry point on the existing shoot-day view inside
  the schedule/stripboard UI, an edit form (day-info fields, location
  picker, cast/crew roster pickers with call times), and PDF
  download/status display.

**Out (named, deferred):**

- **Sides** (scene page excerpts) — its own slice, once call sheets ship.
- **Multi-unit shoots.** A `units` table already exists
  (`backend/db/migrations/050_productions.sql`, auto-created "Main Unit"
  per production) but nothing else in the codebase references it yet. This
  slice does **not** add a `unit_id` to call sheets and enforces at most
  one call sheet per `shooting_day` (`UNIQUE` constraint). When multi-unit
  scheduling is eventually built, `units` is the natural anchor and the
  call sheet's uniqueness constraint would need to move from
  `shooting_day_id` alone to `(shooting_day_id, unit_id)`.
- **Distribution** (email send, public share link). This slice is
  in-app view + PDF download only, matching how existing reports work.
  Revisit if the account owner asks for it once call sheets are in daily
  use.
- **Per-person default call times** on crew/cast records. Times are
  entered per call sheet, not stored as a recurring default.
- **Auto-suggesting roster** from the day's scenes/crew assignments. Both
  cast and crew are picked manually onto each call sheet. (Cast *could*
  be inferred from `shooting_day_scenes` → scene characters, and this is
  a plausible fast-follow once real usage shows manual entry is tedious.)
- **Report-style versioning/history** of call sheets (see the separate,
  still-unstarted "Report version control and tracking" backlog item — a
  call sheet is mutable in place until published, no version history in
  this slice).
- Editing a **published** call sheet — publishing is a one-way status
  flip in this slice (no "un-publish" or edit-after-publish flow); if a
  correction is needed after publishing, the UI allows moving status back
  to `draft` before editing again (see Status lifecycle below), but there
  is no notification that a previously-downloaded PDF is now stale. A
  proper revision/addendum flow is future work.

## A note on the permission-system fork

Scheduling (`shooting_schedules`, `shooting_days`, `shooting_day_scenes` —
migration 030, `routes/schedule_routes.py`) predates the production data
model and is gated entirely by the **older** `require_script_role` /
`script_members` system (`middleware/authorization.py`), keyed to
`script_id`. Crew, locations, and members (steps 2a/2b/3) are gated by the
**newer** `require_production_role` / `production_members` system
(`middleware/production_authz.py`), keyed to `production_id`.

Call sheets sit across this fork: they're anchored to a `shooting_day`
(script-role world) but their content — crew, cast, locations — and their
natural home in the UI (an emerging production-management surface) belong
to the production-role world. **Decision: call sheet routes are gated by
`production_authz`, not `require_script_role`.** A call sheet's
`production_id` is resolved once at creation time (via
`shooting_day → shooting_schedule → script → scripts.production_id`) and
stored directly on the `call_sheets` row, so every subsequent permission
check is a single-column lookup, not a join chain, and does not depend on
the script ever changing its production link after the fact.

**Consequence:** a call sheet can only be created for a shooting day whose
script has `scripts.production_id` set (i.e., the script's production has
gone through step 1's association flow). Attempting to create one for an
unassociated script's shooting day returns
`400 {"error": "Script is not associated with a production"}`. This is a
real, named constraint, not an edge case to paper over — schedules
existed before productions did, so unassociated scripts with active
schedules are expected to exist in production data today.

## Data model

Migration `backend/db/migrations/054_call_sheets.sql`. Follows the
`053_locations.sql` conventions: `gen_random_uuid()` pks, manual apply
(`run_migration.py` is dead), `update_shooting_updated_at()` trigger reuse
(migration 030), owner-only RLS as a direct-client backstop only.

### `call_sheets`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid pk | `default gen_random_uuid()` |
| `production_id` | uuid not null | `REFERENCES productions(id) ON DELETE CASCADE`. Denormalized at creation (see above) for single-lookup authz. |
| `shooting_day_id` | uuid not null unique | `REFERENCES shooting_days(id) ON DELETE CASCADE`. `UNIQUE` enforces one call sheet per day (single-unit scope). |
| `status` | text not null | `CHECK (status IN ('draft','published'))`, `default 'draft'`. |
| `weather` | text null | freeform, e.g. "Partly cloudy, 22°C, 10% rain" |
| `sunrise_time` | time null | |
| `sunset_time` | time null | |
| `breakfast_time` | time null | |
| `lunch_time` | time null | |
| `nearest_hospital` | text null | freeform name + address |
| `parking_notes` | text null | |
| `safety_notes` | text null | safety/COVID officer name + contact, freeform |
| `general_notes` | text null | announcements block |
| `created_by` | uuid null | `REFERENCES auth.users(id) ON DELETE SET NULL` |
| `created_at` | timestamptz not null | `default now()` |
| `updated_at` | timestamptz not null | `default now()`; `BEFORE UPDATE` trigger |

Index: `idx_call_sheets_production ON call_sheets(production_id)`.

### `call_sheet_locations`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid pk | `default gen_random_uuid()` |
| `call_sheet_id` | uuid not null | `REFERENCES call_sheets(id) ON DELETE CASCADE` |
| `location_id` | uuid not null | `REFERENCES locations(id) ON DELETE CASCADE` |
| `is_primary` | boolean not null | `default false` |
| `sort_order` | int not null | `default 0` |

Constraint: `UNIQUE (call_sheet_id, location_id)` — a location appears at
most once per call sheet. App-layer enforces at most one `is_primary=true`
row per call sheet (setting a new primary demotes the previous one in the
same request — no DB-level partial-unique-index needed for this scale).

Index: `idx_call_sheet_locations_sheet ON call_sheet_locations(call_sheet_id)`.

### `call_sheet_crew`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid pk | `default gen_random_uuid()` |
| `call_sheet_id` | uuid not null | `REFERENCES call_sheets(id) ON DELETE CASCADE` |
| `crew_id` | uuid not null | `REFERENCES production_crew(id) ON DELETE CASCADE` |
| `call_time` | time null | nullable so a row can exist before a time is set |
| `notes` | text null | e.g. "bring rain gear" |

Constraint: `UNIQUE (call_sheet_id, crew_id)`.
Index: `idx_call_sheet_crew_sheet ON call_sheet_crew(call_sheet_id)`.

### `call_sheet_cast`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid pk | `default gen_random_uuid()` |
| `call_sheet_id` | uuid not null | `REFERENCES call_sheets(id) ON DELETE CASCADE` |
| `casting_id` | uuid not null | `REFERENCES casting(id) ON DELETE CASCADE` |
| `call_time` | time null | |
| `status_code` | text null | freeform industry shorthand (SW/W/H/WF/SWF) |
| `notes` | text null | |

Constraint: `UNIQUE (call_sheet_id, casting_id)`.
Index: `idx_call_sheet_cast_sheet ON call_sheet_cast(call_sheet_id)`.

### RLS backstop (all four tables)

Owner-only `SELECT`/`ALL` policies keyed via `production_id → productions.owner_id`
(directly on `call_sheets`, via `call_sheet_id → call_sheets.production_id`
on the three join tables). Direct-client safety net only; the app never
relies on it (service-role key).

### Scene list — not a table

The day's scene schedule (scene numbers, INT/EXT, set, D/N, page count) is
**not duplicated** into a call-sheet table. It's read live at
API-response/PDF-generation time from the existing `shooting_day_scenes` +
`scenes` join — the same source `report_service.py`'s `shooting_schedule`
report type already renders. A scene reassigned to a different day after
a call sheet is created stays in sync automatically while the sheet is
`draft`; publishing freezes nothing (see the "editing a published sheet"
non-goal above — this is a known, accepted gap for this slice).

## Delete rules

- Deleting a `shooting_day` cascades its `call_sheets` row (and that
  row's join-table rows). No app-layer guard — a shooting day is already
  the parent record schedule editing deletes freely today.
- Deleting a `production_crew` / `casting` / `locations` row that's
  referenced by a call sheet's roster/location cascades the join row.
  This means a published call sheet can silently lose a crew/cast/
  location entry if the underlying record is later deleted — acceptable
  for this slice (call sheets are day-of documents, not permanent
  records); flagged, not solved.

## Backend

### `services/call_sheet_service.py`

- `NOT_FOUND` sentinel, matching `location_service.py`'s shape.
- `get_or_create(shooting_day_id, user_id)` — looks up an existing
  `call_sheets` row for the day, or creates one: resolves
  `shooting_day → shooting_schedule → script → scripts.production_id`;
  400 if null (see permission-fork section); inserts with
  `created_by=user_id`. Idempotent — safe to call every time the UI opens
  a day's call sheet panel.
- `get_call_sheet(id)` — the row plus joined roster (`call_sheet_crew`
  joined to `production_crew`/`contacts`, `call_sheet_cast` joined to
  `casting`) and locations (joined to `locations`), plus the day's live
  scene list (via a shared helper, extracted from
  `report_service.py`'s existing shooting-schedule scene query if not
  already a standalone function — extracting it is in-scope if it isn't
  already reusable). Returns `NOT_FOUND` if missing.
- `update_call_sheet(id, fields)` — whitelist of the day-info fields plus
  `status`. `status` transition `draft → published` only (rejecting
  `published → draft` is a UI-level convenience, not enforced at the
  service layer, since a correction workflow may want it — see non-goals).
- `add_crew(call_sheet_id, crew_id, call_time, notes)` /
  `remove_crew(call_sheet_id, crew_id)` — verifies `crew_id` belongs to
  the same `production_id` as the call sheet before inserting (a crew
  member from a different production can't be added).
- `add_cast(call_sheet_id, casting_id, call_time, status_code, notes)` /
  `remove_cast(...)` — verifies `casting_id`'s script resolves to the same
  production.
- `add_location(call_sheet_id, location_id, is_primary)` /
  `remove_location(...)` — on `is_primary=true`, demotes any existing
  primary row for that call sheet in the same call.
- `render_call_sheet_pdf(call_sheet_id)` — builds the HTML per the layout
  below and calls `HTML(string=html).write_pdf(...)` via WeasyPrint,
  importing `report_service._get_pdf_css()` rather than duplicating CSS.

**Sensitive-field handling on the roster:** `production_crew`'s
`job_rate`/`standard_rate` stay redacted per the existing
`can_view_sensitive` capability (reuse `production_crew_service._redact`)
— a call sheet is not a payroll document. **Phone/email are always shown**
regardless of `can_view_sensitive`, since day-of contact info is the
entire point of a call sheet and every crew/cast member on it is, by
construction, already someone the viewer is working with that day. This
is a deliberate narrowing of the existing sensitive-field rule for this
one surface, not a bug.

### `middleware/production_authz.py` changes

- Add `can_edit_call_sheets` to the `CAPABILITIES` tuple. Owner: always
  `True`. Admin/coordinator: `True` by default (matches
  `can_edit_crew`/`can_edit_production`'s defaults). Viewer: `False` by
  default, toggleable per-member like the other override flags.
- Add `from_call_sheet_id(kwargs)` resolver — single lookup of
  `call_sheets.production_id` by `call_sheet_id`.
- Add `from_shooting_day_id(kwargs)` resolver — resolves `production_id`
  via `shooting_day → shooting_schedule → script → scripts.production_id`
  (returns `None`/404 if the script has no production). Used only by the
  `POST .../call-sheet` get-or-create route, since every other route
  operates on an already-created `call_sheets` row and uses
  `from_call_sheet_id` instead.

### Routes — `routes/call_sheet_routes.py` → `call_sheet_bp`

All routes `@require_auth` + `require_production_role(...)`.

| Method + path | Resolver | Min role / capability |
|---|---|---|
| `POST /api/shooting-days/<day_id>/call-sheet` | `from_shooting_day_id` (get-or-create) | `can_edit_call_sheets` |
| `GET /api/call-sheets/<call_sheet_id>` | `from_call_sheet_id` | `viewer` (any member) |
| `PATCH /api/call-sheets/<call_sheet_id>` | `from_call_sheet_id` | `can_edit_call_sheets` |
| `POST /api/call-sheets/<call_sheet_id>/crew` | `from_call_sheet_id` | `can_edit_call_sheets` |
| `DELETE /api/call-sheets/<call_sheet_id>/crew/<crew_id>` | `from_call_sheet_id` | `can_edit_call_sheets` |
| `POST /api/call-sheets/<call_sheet_id>/cast` | `from_call_sheet_id` | `can_edit_call_sheets` |
| `DELETE /api/call-sheets/<call_sheet_id>/cast/<casting_id>` | `from_call_sheet_id` | `can_edit_call_sheets` |
| `POST /api/call-sheets/<call_sheet_id>/locations` | `from_call_sheet_id` | `can_edit_call_sheets` |
| `DELETE /api/call-sheets/<call_sheet_id>/locations/<location_id>` | `from_call_sheet_id` | `can_edit_call_sheets` |
| `GET /api/call-sheets/<call_sheet_id>/pdf` | `from_call_sheet_id` | `viewer` (any member) |

Register `call_sheet_bp` in `app.py` next to the other production-scoped
blueprints. Route path chosen to match the existing
`/api/shooting-days/<day_id>/...` convention in `schedule_routes.py`
(not nested under `/schedules/<id>/days/<id>/`, which isn't how the real
routes are shaped).

## PDF layout

Single page per day, top-to-bottom:

1. **Header** — production title, shoot date, day number (e.g. "Day 4 of
   12", from `shooting_days.day_number`), a visible "DRAFT" watermark/
   banner when `status = 'draft'`.
2. **Day info strip** — weather, sunrise/sunset, breakfast/lunch times.
3. **Locations** — primary first, then secondary, each with address and
   `parking_notes` pulled from the linked `locations` row.
4. **Scene schedule** — scene numbers, INT/EXT, set, D/N, page count, read
   live from `shooting_day_scenes` + `scenes` (same fields as the
   `shooting_schedule` report).
5. **Cast call list** — name, character, `status_code`, call time.
6. **Crew call list** — grouped by department (`department_service`'s
   ordering, matching `list_crew()`'s grouping), name, role, call time.
7. **Footer** — nearest hospital, safety/COVID contact, general notes.

## Frontend

No new top-level nav item — a call sheet only makes meaning attached to a
specific shoot day, so it lives inside the existing schedule/stripboard UI
where `shooting_days` are already managed.

- On each shoot-day row/panel: a "Call Sheet" action — "Create Call
  Sheet" if none exists yet, else "Edit" / "Download PDF" / a draft-vs-
  published status chip.
- `CallSheetEditor.jsx` (new): day-info fields form, a location picker
  (multi-select from `/api/locations` via the production's linked
  locations, primary toggle), and two roster pickers — cast (from the
  script's `casting` list) and crew (from `/api/productions/<id>/crew`) —
  each added row getting a call-time input. "Publish" button flips
  `status`.
- `apiService.js` — new functions block: `getOrCreateCallSheet`,
  `getCallSheet`, `updateCallSheet`, `addCallSheetCrew`,
  `removeCallSheetCrew`, `addCallSheetCast`, `removeCallSheetCast`,
  `addCallSheetLocation`, `removeCallSheetLocation`,
  `downloadCallSheetPdf` (blob-download pattern, matching
  `downloadReportCsv`/`downloadStripboardPdf`).

## Permissions (settled)

| Surface | Rule |
|---|---|
| Create / edit call sheet, roster, locations | `require_production_role` + `can_edit_call_sheets` |
| View call sheet (JSON or PDF) | `require_production_role('viewer')` — any production member |
| Sensitive crew fields (rate) on the roster | Redacted per existing `can_view_sensitive`, reusing `production_crew_service._redact` |
| Crew/cast phone/email on the roster | Always visible to anyone who can view the sheet (deliberate narrowing — see Backend section) |
| Script not associated with a production | 400 on create — call sheets require step 1's production↔script association |

## Testing

- **`test_call_sheet_service.py`** — get-or-create idempotency; 400 on
  unassociated script; day-info update; roster add/remove with
  cross-production rejection (a crew/cast id from a different production
  can't be added); primary-location demotion on re-assign; PDF generation
  smoke test (mocks WeasyPrint or asserts bytes returned); sensitive-field
  redaction on the roster (rate hidden, phone shown, for a
  non-`can_view_sensitive` caller).
- **`test_call_sheet_routes.py`** — auth required (401 anon); non-member
  403; viewer can `GET`/PDF but not `PATCH`/roster writes (403); coordinator/
  admin/owner can edit; `can_edit_call_sheets=False` override on a
  coordinator blocks edits; 404 on a call sheet in a different production.
- **`test_route_enforcement.py`** — extend the production-scoped-routes
  assertion to cover the new `call_sheet_bp` routes.
- Full backend suite green; frontend `npm run build` green.

## Migration / deploy notes

1. Apply `054_call_sheets.sql` manually to the Supabase project before
   deploying backend changes (same pattern as 051/052/053).
2. No env vars needed — PDF rendering reuses the existing WeasyPrint
   dependency already required for reports.
3. No data backfill; no changes to existing tables (`shooting_days`,
   `production_crew`, `casting`, `locations` all untouched — this slice
   only reads them and adds new join tables).

## Open items carried forward (not blocking this slice)

- **Sides** — its own design, once call sheets are in use and real usage
  clarifies what "the pages for today" should actually contain (full
  scene text vs. condensed sides format, PDF page extraction from the
  source script vs. re-rendering from parsed scene data).
- **Multi-unit** — the existing `units` table is the natural anchor;
  revisit if/when second-unit shoots come up.
- **Distribution** (email/share-link) — fast-follow if manual
  download/print proves to be a real friction point.
- **Auto-suggesting cast from scenes** — a plausible ergonomics
  improvement once manual roster entry is validated as the bottleneck.
- **Monetization** — like the recent revision-reanalysis decision, call
  sheets are unmetered production-management depth, not a billable unit
  in the current two-tier pricing model. No action needed now; flagged
  for the same future pricing-review pass.
