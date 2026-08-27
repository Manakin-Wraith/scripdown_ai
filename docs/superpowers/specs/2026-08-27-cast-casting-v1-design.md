# Cast & Casting (v1) — Design

**Date:** 2026-08-27
**Status:** Approved for planning
**Sub-project of:** "Production data model — what a production needs, and how
it's uploaded/managed" (`docs/BACKLOG.md`). This is sub-project **A** of
five (A Cast & casting, B Crew directory, C Locations as real places,
D Shoot-day production detail, E Call sheet + sides generation).

---

## 1. Goal

Let a production attach a real person to each character in a script — actor
name, contact details, agent, headshot, booking status, and
availability/blackout dates — and surface availability conflicts against the
shooting schedule.

This closes the single biggest gap between "breakdown tool" and "scheduling
tool": Day Out of Days already computes which days a character works, but
there is no way to know an actor is unavailable on one of those days.

## 2. Scope

### In scope (v1)

- A per-script casting record, one row per character.
- Fields: actor name, booking status, contact phone/email, agent contact
  (free text), headshot image, notes, and 0..n unavailable date ranges.
- A dedicated **Cast** tab in the script workspace (`scripts/:scriptId/cast`).
- Admin-only write; all script members can read; contact fields readable
  only by owner/admin.
- Informational availability-conflict display on the Shooting Schedule page
  and the Day Out of Days report (no blocking).
- The actor↔character link binds by canonical character name and is carried
  forward by the existing `merge_characters` flow.

### Out of scope (v1) — model stays additive

- Rates, deal memos, loan-out / union / tax data.
- CSV / bulk import (manual form entry only).
- Season- or account-level casting rollup. The model is shaped so a future
  `characters` table or `season_casting` table can be introduced and
  `casting.character_name` backfilled to a foreign key **without reworking
  casting**.
- Crew directory (sub-project B).
- Active conflict prevention (refusing an assignment/date change).
- Doubles / stunt / photo doubles / multiple actors per character.
- Fitting, rehearsal, travel, and accommodation data.

## 3. Decisions (from brainstorm)

| # | Decision |
|---|---|
| Q1 | Casting lives **per-script** for v1. Model kept additive for a later season/account rollup. |
| Q2 | Actor↔character link **binds by `(script_id, character_name)` string**. No new `characters` table. `merge_characters` is hooked to carry the casting row to the new canonical name. Re-analysis is safe because canonical names already resolve through `character_aliases`. A character dropped by re-analysis leaves a "soft orphan" casting row. |
| Q3 | **One row per character** (`UNIQUE(script_id, character_name)`). An actor doubling gets two rows. `status` vocabulary: `wishlist / offer / booked / declined / released`. |
| Q4 | Conflicts are **informational only**: a marker on the DOOD cell and a conflict list on the Schedule page. No soft or hard blocking. Days with no `shoot_date` are not checked. |
| Q5 | **Read** for all script members; **write** for owner + `script_members.role = 'admin'` only. Contact fields (`contact_phone`, `contact_email`, `agent_contact`) are omitted from the API payload for non-admin readers (all-or-nothing, no per-field UI redaction beyond hiding the section). |
| Q6 | **Manual form entry only** for v1. |
| UI | **Approach 1** — a dedicated Cast tab, not inline on the breakdown list and not nested under Schedule. |

## 4. Data model

New migration: `backend/db/migrations/048_casting.sql`.

### 4.1 `casting`

One row per character per script.

| column | type | notes |
|---|---|---|
| `id` | UUID PK DEFAULT `gen_random_uuid()` | |
| `script_id` | UUID NOT NULL REFERENCES `scripts(id)` ON DELETE CASCADE | |
| `character_name` | TEXT NOT NULL | canonical character name; the link (Q2) |
| `actor_name` | TEXT | |
| `status` | TEXT NOT NULL DEFAULT `'wishlist'` | `CHECK (status IN ('wishlist','offer','booked','declined','released'))` |
| `contact_phone` | TEXT | owner/admin read only |
| `contact_email` | TEXT | owner/admin read only |
| `agent_contact` | TEXT | free text (agency + name + phone); owner/admin read only |
| `headshot_path` | TEXT | object path within the `scripts` storage bucket |
| `notes` | TEXT | |
| `created_by` | UUID REFERENCES `auth.users(id)` ON DELETE SET NULL | |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT `now()` | |
| `updated_at` | TIMESTAMPTZ NOT NULL DEFAULT `now()` | maintained by trigger |

Constraints / indexes:

- `UNIQUE (script_id, character_name)`
- `INDEX idx_casting_script ON casting(script_id)`
- `BEFORE UPDATE` trigger setting `updated_at = now()` (reuse the existing
  `update_shooting_updated_at()` function from migration 030, or an
  identically-shaped `update_casting_updated_at()` if preferred for
  clarity).

### 4.2 `casting_unavailability`

0..n date ranges per casting row.

| column | type | notes |
|---|---|---|
| `id` | UUID PK DEFAULT `gen_random_uuid()` | |
| `casting_id` | UUID NOT NULL REFERENCES `casting(id)` ON DELETE CASCADE | |
| `start_date` | DATE NOT NULL | |
| `end_date` | DATE NOT NULL | |
| `reason` | TEXT | |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT `now()` | |

Constraints / indexes:

- `CHECK (end_date >= start_date)`
- `INDEX idx_casting_unavail_casting ON casting_unavailability(casting_id)`

### 4.3 RLS

Defense-in-depth. The backend uses the service-role key and enforces access
via route decorators (Section 5); these policies protect any future direct
frontend Supabase access.

`casting`:

- **SELECT** — `script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())`
  `OR script_id IN (SELECT script_id FROM script_members WHERE user_id = auth.uid())`
- **INSERT / UPDATE / DELETE** —
  `script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())`
  `OR script_id IN (SELECT script_id FROM script_members WHERE user_id = auth.uid() AND role = 'admin')`

`casting_unavailability`: same predicates, reached through a
`casting_id IN (SELECT id FROM casting WHERE …)` subquery.

RLS cannot express the owner/admin-only redaction of the three contact
columns — that is done in the backend serializer (Section 5.4).

## 5. Backend

### 5.1 New files

- `backend/routes/casting_routes.py` — blueprint `casting_bp`.
- `backend/services/casting_service.py` — persistence, serialization,
  conflict computation.
- Register `casting_bp` in `backend/app.py` (no ordering constraint).

### 5.2 New resolver

In `backend/middleware/authorization.py`:

```python
def from_casting(kwargs):
    return _lookup_script_id('casting', kwargs.get('casting_id'))
```

For `DELETE /api/casting/unavailability/<id>` a two-hop resolver is needed
(`casting_unavailability.casting_id` → `casting.script_id`), following the
`from_day` precedent.

### 5.3 Endpoints

All routes carry `@require_auth`. Role is enforced with
`@require_script_role(<min_role>, resolver=<resolver>)`. `ROLE_RANK` is
`{viewer:1, member:2, admin:3, owner:4}`, so `require_script_role('admin')`
also admits the owner.

| Method / path | Min role | Resolver | Purpose |
|---|---|---|---|
| `GET /api/scripts/<script_id>/casting` | viewer | `from_script` | List casting rows (+ nested unavailability). Merges in the current breakdown's character names so uncast characters also appear. Flags rows whose `character_name` matches no current breakdown character with `orphaned: true`. Contact fields present only for owner/admin callers. |
| `POST /api/scripts/<script_id>/casting` | admin | `from_script` | Create. `character_name` required. `UNIQUE` violation → HTTP 409. |
| `PATCH /api/casting/<casting_id>` | admin | `from_casting` | Partial update of any `casting` field. |
| `DELETE /api/casting/<casting_id>` | admin | `from_casting` | Delete row (cascades unavailability). Also deletes the headshot object from storage if `headshot_path` is set. |
| `POST /api/casting/<casting_id>/unavailability` | admin | `from_casting` | Body `{start_date, end_date, reason?}`. `end_date >= start_date` validated (400 otherwise). |
| `DELETE /api/casting/unavailability/<id>` | admin | two-hop | Remove one range. |
| `POST /api/casting/<casting_id>/headshot` | admin | `from_casting` | `multipart/form-data` image. Validates content type in {jpeg, png, webp} and size ≤ 5 MB. Uploads to the `scripts` bucket at `casting/<script_id>/<casting_id>.<ext>` (upsert). Sets `headshot_path`. Returns the updated row. |

Headshot delivery: the list and single-row payloads include a
short-lived signed URL (`headshot_url`) derived from `headshot_path`
(`scripts` bucket is private), generated at serialization time. No separate
GET endpoint.

### 5.4 Serializer

`casting_service.serialize(row, *, include_contact: bool)` is the single
place that includes or drops `contact_phone`, `contact_email`,
`agent_contact`. `include_contact` is `role in ('admin', 'owner')`, computed
once per request from the value `require_script_role` already resolved
(exposed via `g` or re-resolved with `get_script_role`).

### 5.5 Conflict computation

`casting_service.compute_conflicts(script_id, schedule_id) -> list[dict]`:

1. Load the schedule's `shooting_days` that have a non-null `shoot_date`.
2. For each such day, compute the set of characters working that day: the
   scenes assigned to the day (`shooting_day_scenes` → `scenes`), union of
   each scene's `characters`, each resolved to its canonical name via
   `character_aliases`.
3. Load `casting` + `casting_unavailability` for the script.
4. For each (day, character) pair where a `casting` row exists for that
   character **and** an unavailable range covers `shoot_date`
   (`start_date <= shoot_date <= end_date`), emit:
   `{shooting_day_id, day_number, shoot_date, character_name, actor_name,
   unavailability_reason}`.

Step 2's day→characters logic is extracted from `report_service`'s DOOD
path into a shared helper if it is not already independently callable.
`report_service` keeps its own call site.

Endpoint: `GET /api/scripts/<script_id>/casting/conflicts?schedule_id=<id>`
(min role viewer, resolver `from_script`). Missing/invalid `schedule_id` →
400. Schedule not belonging to the script → 404.

### 5.6 Merge hook

In `backend/routes/supabase_routes.py::merge_characters`, after the
`character_aliases` row is inserted and scene arrays are rewritten:

```
UPDATE casting
   SET character_name = <canonical_name>
 WHERE script_id = <script_id>
   AND character_name = <alias_name>
```

If a `casting` row already exists for `<canonical_name>` (would violate
`UNIQUE(script_id, character_name)`): the canonical row wins; the alias's
`casting` row is deleted. This is logged. It is a rare case (two casting
rows for characters later discovered to be the same person).

`merge_locations` is not touched.

## 6. Frontend

### 6.1 Route & navigation

- `App.jsx`: `<Route path="scripts/:scriptId/cast" element={<CastPage />} />`.
- Add a "Cast" link to the script workspace navigation, alongside the
  existing Breakdown / Board / Schedule / Reports links (locate the shared
  workspace header/nav component during implementation).

### 6.2 Components (`frontend/src/components/cast/`)

- **`CastPage.jsx`** — fetches `GET /casting` and the current breakdown
  character list. Renders a grid, one row per character: character name,
  actor name, `status` badge, headshot thumbnail, a conflict marker (⚠) if
  the character appears in `getCastingConflicts` for the script's active
  schedule (if one exists), and an `orphaned` tag for casting rows with no
  matching breakdown character. Uncast characters show an "Add casting"
  action. Owns its own fetch/state — no new React context (follows
  `ReportStudio` / `ShootingSchedulePage`).
  - Conflict marker source: `CastPage` calls `getCastingConflicts` for the
    script's schedule whose `status = 'active'`; if there is none, it skips
    the conflict markers entirely (the Schedule page is where per-schedule
    conflicts are always shown). If more than one schedule is `active`, use
    the most recently updated.
- **`CastingDetailPanel.jsx`** — slide-over drawer for one character:
  `actor_name`, `status` dropdown, `notes`, headshot upload/preview, and
  the unavailable-ranges editor (each range: start date, end date, reason;
  add / delete row). The contact section (`contact_phone`,
  `contact_email`, `agent_contact`) renders only when the current user is
  owner/admin.
- **`useCastRole` (or reuse existing role hook)** — resolves the current
  user's role on the script to gate edit controls and the contact section.
  Backend enforces regardless; this is UX only.

### 6.3 `apiService.js`

Add, through the existing axios instance:
`getCasting(scriptId)`, `createCasting(scriptId, body)`,
`updateCasting(castingId, body)`, `deleteCasting(castingId)`,
`addUnavailability(castingId, body)`, `removeUnavailability(id)`,
`uploadHeadshot(castingId, file)`,
`getCastingConflicts(scriptId, scheduleId)`.

## 7. Conflict surfacing on consumers

Both are read-only consumers of the conflicts endpoint; no writes.

- **`ShootingSchedulePage.jsx`** — on load, fetch conflicts for the open
  schedule. Show a red badge on any day with a conflict and a dismissible
  "Availability conflicts" panel listing each
  (`Day 4 (12 Mar) — Jane Doe (JOHN) unavailable — <reason>`).
  Informational only.
- **Day Out of Days** — in the DOOD report aggregation
  (`report_service`, `day_out_of_days` report type only), pass
  casting + unavailability in, and mark any work-day cell that falls inside
  an unavailable range (warning glyph / red text) in both the preview and
  the WeasyPrint PDF. A scoped change to that one report type, not a
  general `report_service` change.
- Days with no `shoot_date` are never checked or marked.

## 8. Storage

Headshots go in the existing private `scripts` bucket at
`casting/<script_id>/<casting_id>.<ext>`. Upload endpoint validates type
(`image/jpeg`, `image/png`, `image/webp`) and size (≤ 5 MB), upserts, and
records `headshot_path`. Serialized rows carry a short-lived signed
`headshot_url`. Deleting a casting row deletes its headshot object.

## 9. Testing

- **`backend/tests/test_casting_routes.py`** — authz matrix (viewer read
  200 / viewer write 403 / non-member 403 / admin write 200 / owner write
  200); CRUD happy paths; `UNIQUE(script_id, character_name)` → 409;
  unavailability add (valid + `end_date < start_date` → 400) and remove;
  contact-field redaction (non-admin list payload excludes
  `contact_phone` / `contact_email` / `agent_contact`); headshot upload
  rejects wrong type and oversize.
- **`backend/tests/test_casting_merge_hook.py`** — `merge_characters`
  renames the casting row to the canonical name; collision case deletes the
  alias row and keeps the canonical.
- **`backend/tests/test_casting_conflicts.py`** — character unavailable on
  a dated shoot day → conflict; same character available → none; undated
  day → none; uncast character working that day → none; alias-named
  character in a scene still resolves to its casting row.
- Frontend: gate on `npm run build` (repo-wide `npm run lint` is broken).
- Full backend suite must remain green.

## 10. Additive-for-later notes

- A future `characters` table: add it, backfill from breakdown + existing
  `casting.character_name`, then migrate `casting.character_name` → a
  `character_id` FK. The casting record's own fields and endpoints are
  unaffected.
- Season/account rollup: a `season_casting` (or account-level talent pool)
  table can reference the same casting shape; per-script `casting` rows
  become overrides/links. No v1 column needs to change.
- Crew (sub-project B) will reuse the `departments` table and
  `script_members.department_code` that already exist; it does not depend
  on casting.

## 11. References

- `docs/BACKLOG.md` — "Production data model" (umbrella), "Add CREW, CAST
  and production detail…", "Real production data for scheduling…"
- `backend/db/migrations/030_shooting_schedules.sql` — schedule/day schema
- `backend/db/migrations/031_character_aliases.sql` — canonical-name model
- `backend/middleware/authorization.py` — `require_script_role`,
  `ROLE_RANK`, resolver pattern (`from_report`, `from_day`)
- `backend/routes/supabase_routes.py` — `merge_characters` (hook site)
- `backend/services/report_service.py` — DOOD day→characters logic to share
- `frontend/src/App.jsx` — flat `scripts/:scriptId/*` routing
- `frontend/src/components/reports/ReportStudio.jsx`,
  `frontend/src/components/schedule/ShootingSchedulePage.jsx` — precedent
  for a self-contained script-scoped workspace page
