# Production Data Model — Direction & Data-Model Spec

**Date:** 2026-08-31
**Status:** Design approved — direction-setting only, no implementation plan yet
**Type:** Architectural / umbrella
**Supersedes:** the "Production data model — what a production needs, and how
it's uploaded/managed — brainstorm" backlog entry

## Purpose

Everything SlateOne holds today is derived from a script (AI extraction) or
generated from it (breakdown, schedule, reports), plus per-script cast
production data (`casting` / `casting_unavailability`). A real production runs
on a large body of *other* data with no home in the app: company/project
setup, crew by department with contacts and rates, real-world locations,
per-shoot-day operational detail, and multi-unit structure.

Four downstream features all need production-level scoping:

- Crew + call sheets / sides
- Department workspaces
- "Auto" AI scheduling
- Daily Production Reporting (DPR) — whose spec already assumes "per
  production" configuration and a Unit entity between shooting-day and report

This spec **sets direction and defines the data model** so those features
build against one schema instead of each reinventing a half-schema. It does
**not** design any individual feature — each slice gets its own brainstorm.

## Decision

**Introduce `production` as a new top-level entity.** It is a
*physical-shoot* container that holds one or more scripts and carries shoot
dates, units, crew roster, locations, call-sheet settings, and (later) DPR
configuration.

It is an **independent axis** from `series → seasons`:

- `series → seasons` is a **narrative** grouping (episodes of a show).
- `production` is a **physical shoot** grouping.
- A script may have a season, a production, both, or neither. Standalone
  features: production, no season. TV: usually both. A show's Season 1 and
  Season 2 are normally two separate productions; occasionally two seasons
  shoot back-to-back as one production. The independent-axes model is the
  only one that loses no information, and series/seasons is already shipped.

**Why not keep hanging everything off `script_id`:** the primary user is a
production company running many productions over time (a reusable address
book that outlives any one project), and productions frequently hold more
than one script (a TV block; a feature plus its reshoot script). Per-script
scoping cannot express either without duplication.

## Entity model

**"Account" in this spec means the owner user** — there is no `accounts` /
organization table in this codebase. Ownership is a `profiles` row
(`profiles.id` == the `auth.users` id), the same pattern `series.owner_id`
and `account_seats.owner_id` already use. "Account-level" below therefore
means **owner-scoped** (`owner_id → profiles(id)`); it does not imply a new
org entity.

```
account = the owner user (profiles row; NOT a new table)
 ├── productions              (new, 1:n)
 │    ├── production_members   (new — additive permission layer)
 │    ├── units               (new — 1st Unit / 2nd Unit / Splinter; unblocks DPR)
 │    ├── production_crew      (new — assignment rows: contact + role + dept
 │    │                          + this-job rate + call-time default)
 │    └── production_locations (new — links production ↔ location
 │                               + production-specific notes)
 ├── contacts                 (new — account-level reusable directory;
 │                               person or company)
 └── locations                (new — account-level reusable directory;
                                 real places)

scripts.production_id                (new, nullable — a script belongs to ≤1 production)
scripts.season_id                    (existing, unchanged — independent axis)

shooting_schedules.production_id     (new, nullable — TARGET model; see "Scheduling")
shooting_days.unit_id                (new, nullable — added with the schedule/DPR
                                       slice, not step 1; no reader/writer before then)
shooting_day_details                 (new — 1:1 with shooting_days; call-sheet
                                       fields; SHAPE NAMED ONLY in this spec)

casting / casting_unavailability     (existing — UNCHANGED; cast stays its own system)
script_members / departments         (existing — UNCHANGED; still the
                                       breakdown/scene/report access primitive)
```

### Table sketches (directional — columns finalized per slice)

**`productions`**
- `id`, `account_id` / `owner_id` (match existing ownership pattern)
- `title`, `format` (feature / tv / short / commercial / other)
- `status` (development / prep / shooting / wrapped / archived)
- `shoot_start_date`, `shoot_end_date` (nullable)
- `production_company`, `notes`
- `created_by`, `created_at`, `updated_at`

**`contacts`** (account-level directory)
- `id`, `account_id` / `owner_id`
- `kind` (person / company)
- `name`, `company_name` (nullable), `role_tags` (text[] — e.g. gaffer,
  1st AD, caterer)
- `phone`, `email`, `agent_contact` (nullable)
- `standard_rate` (nullable — sensitive), `rate_unit` (day / week / flat)
- `notes`, `created_by`, `created_at`, `updated_at`

**`production_crew`** (assignment; join of production ↔ contact)
- `id`, `production_id`, `contact_id`
- `role` (this job's title), `department_code` (references existing
  `departments`)
- `job_rate` (nullable — sensitive), `job_rate_unit`
- `default_call_offset` (nullable — e.g. "crew call minus 30m")
- `start_date`, `end_date` (nullable — for partial-schedule crew)
- `notes`, `created_at`, `updated_at`

**`locations`** (account-level directory)
- `id`, `account_id` / `owner_id`
- `name`, `address`, `lat`/`lng` (nullable)
- `primary_contact_id` (nullable → `contacts`)
- `permit_status`, `parking_notes`, `loadin_notes`, `restrictions`
- `photos` (follow the `casting_photos` pattern — separate
  `location_photos` table, Supabase `scripts` bucket or a new bucket)
- `notes`, `created_by`, `created_at`, `updated_at`

**`production_locations`** (link)
- `id`, `production_id`, `location_id`
- `production_notes` (nullable — e.g. "week 2 only, north field")
- `created_at`

**`units`**
- `id`, `production_id`, `name` (default "Main Unit"), `sort_order`
- `created_at`

**`shooting_day_details`** — **shape named only.** 1:1 with `shooting_days`.
Will carry: unit base / base camp, location address + parking + load-in,
nearest hospital, sunrise/sunset + weather, general crew call, meal times,
key-personnel call times. Field-by-field design belongs to the call-sheet
slice brainstorm.

## Directories — the reusable address book

- **`contacts`** is account-scoped and canonical. Editing a contact's phone
  number updates it everywhere it appears. This is the "address book that
  outlives projects."
- **`production_crew`** is a per-production assignment referencing a contact.
  Job-specific data (this job's rate, call-time offset, dates) lives on the
  assignment, never on the contact.
- **`locations`** is account-scoped and canonical, same reuse logic — a
  stage or a farm location is used across many of a company's productions.
  `production_locations` links them per-production with production-specific
  notes.
- **Deferred:** the scene-`setting` → real-`location` mapping (aliases,
  sub-locations, canonical names already exist for creative sets). That
  belongs to the "Separate Location (production element) from Sets
  (creative)" brainstorm. This spec only reserves that `locations` is where
  it will attach.
- **Open for the crew-slice brainstorm:** whether a non-owner production
  member can browse the *whole* owner `contacts` / `locations` directory
  (including people/places attached only to that owner's *other*
  productions) or only the subset assigned to productions they belong to.
  This is a privacy decision, not settled here.

## Permissions

A **new additive layer**, consistent with the app's app-layer, per-surface
authorization (the backend uses the service-role key; enforcement is in
Python via role helpers).

**None of this lands in step 1.** `production_members` and everything gated
by it ship with the **crew slice (build-sequence step 2)** — step 1
productions are owner-only (with the `series`-style read-through for team
members who hold a role on a script inside the production; see the spine
spec). Until step 2, a production consumes no seat and grants no access.

- **`production_members`** — `(production_id, user_id, role,
  can_view_sensitive)`. Role set: `admin` (line producer), `coordinator`,
  `viewer`. Governs **production-level surfaces only**: crew, locations,
  production schedule, call sheets, DPR.
- **`script_members` is unchanged** — still the sole primitive for
  breakdown / scene / report access.
- **Inheritance (deferred, revisit at the crew slice):** the intent is that
  a production `admin` is granted access to the production's scripts, and
  being a script member grants **no** production access. Step 1 keeps
  production and script access fully independent; the inheritance direction
  is decided for real when `production_members` is built.
- **`can_view_sensitive`** (default: `admin` only) gates `contacts.phone`,
  `contacts.standard_rate`, `production_crew.job_rate`. Coordinators and
  viewers see names, roles, departments, call times — not money or personal
  numbers — unless explicitly granted.
- **Seats:** once it exists, a production member consumes a Team License
  seat exactly as a script member does. No new billing concept.

## Scheduling — target model and migration path

`shooting_schedules` today is `script_id NOT NULL`; a shoot day holds scenes
from that one script.

- **Target model:** `shooting_schedules.production_id` (nullable). A
  production-level schedule's shoot day can hold scenes from **any script in
  the production** — a real block schedule, episodes interleaved on one
  stripboard.
- **First slice keeps per-script scheduling exactly as-is** and adds only a
  **read-only production-level rollup**: a combined calendar / list view
  across the production's scripts' existing schedules. Cheap, non-breaking.
- **Later slice** fills in `production_id`, relaxes `shooting_day_scenes` to
  span scripts, and updates the schedule routes + Kanban UI for a true
  cross-script board. The model must *support* this; the first slice need
  not *build* it.

## Reconciliation with existing systems

| System | Change |
|---|---|
| `series` / `seasons` | None. Independent axis. `scripts.season_id` and `scripts.production_id` are both nullable and unrelated. |
| `casting` / `casting_unavailability` | None. Cast stays its own per-script system. Folding actors into `contacts` is a later migration with little near-term payoff and real cost (it is shipped and verified). |
| `script_members` / `departments` / `department_notes` / `department_items` | None. Still governs breakdown/scene/report access. `production_crew.department_code` references the existing `departments` list. |
| `shooting_schedules` | Gains nullable `production_id` in the target model; first slice does not touch it. |
| Team License seats | A production member consumes a seat like a script member. No new billing logic. |

## Ingestion

- **Manual entry forms** are the v1 baseline for every slice.
- **CSV / XLSX import is a fast-follow for `contacts` and `production_crew`
  specifically** — crew and cast lists circulate on set as spreadsheets;
  this is the highest-value import.
- **AI-parse an uploaded call sheet / production book PDF is deferred** —
  needs real sample documents to build against; silent wrong-parsing risk
  (same reasoning as FDX Tagger ingestion).

## App placement

- New top-level route **`/productions`** — a list of the account's
  productions.
- Each production opens a **workspace with tabs**: Overview, Crew,
  Locations, Schedule, Call Sheets (DPR later). Tabs appear as their slices
  ship.
- Productions are **created explicitly** (never auto-created from a script).
- **Script ↔ production association** is available in two places: at script
  upload (a picker beside the existing Series/Season picker) and from the
  production page ("Add script").

## Recommended build sequence

Each step is its own brainstorm → spec → plan → implementation cycle.

1. **The spine** — `productions` entity + `units` table, `/productions`
   list, per-production detail (Overview), script↔production association.
   Owner-only + `series`-style read-through. **No `production_members`
   yet.** Full design: `docs/superpowers/specs/2026-08-31-production-spine-design.md`.
   Nothing downstream can start without this. Fast-follows: upload-flow
   association picker; My Scripts production grouping; "add a whole
   season's episodes to this production" bulk action.
2. **Crew** — `contacts` directory + `production_crew` assignments + CSV
   import, **plus `production_members` + `can_view_sensitive`** (the first
   surface worth gating) and the non-owner directory-scope decision above.
   First real payoff; the highest-demand missing data.
3. **Locations** — `locations` directory + `production_locations`. Defer the
   scene-`setting` mapping.
4. **Call sheets** — `shooting_day_details` (field design happens here) +
   generation via the WeasyPrint pipeline. Depends on 2 and 3.
5. **Production-level schedule** — fill in `shooting_schedules.production_id`,
   cross-script board, route + Kanban changes.
6. **DPR** — `units` already exist from step 1; follow the existing DPR spec.
7. **Department workspaces** — re-scoped to production-level, building on
   `production_crew` + `departments`.

## Explicitly out of scope for this spec

- Field-by-field call-sheet and sides layout
- Scene-`setting` → real-`location` mapping mechanism
- DPR internals (covered by `docs/SPEC_Daily_Production_Reporting.md`)
- Auto-scheduling heuristics / engine choice
- Cast ↔ `contacts` unification
- The production-level cross-script stripboard implementation
- CSV import column formats (decided per slice)

## Known future reconciliation debt

- **Cast vs. crew as people.** `casting` stays separate from `contacts` /
  `production_crew`. A real person can be both a day-player actor and a
  crew member (e.g. a stunt coordinator who also appears on camera), and
  the same agent/contact detail will exist in both systems. Accepted for
  now; unifying is a later migration, tracked here so it isn't a surprise.
- **`shooting_days.unit_id`** is named in the entity model but added only
  with the schedule/DPR slice — the `units` rows created in step 1 have no
  consumer until then.

## Open questions resolved in the brainstorm

- **Production entity vs. keep slicing?** → Introduce the entity.
- **Relationship to series/seasons?** → Independent axes, both nullable on
  `scripts`.
- **Address book scope?** → Account-level `contacts`; per-production
  assignments carry job-specific data.
- **Cast in or out?** → Out. Stays its own system.
- **Schedule reconciliation?** → Model supports production-level (nullable
  `production_id`); first slice ships per-script rollup only.
- **Units now or later?** → Now (cheap; unblocks DPR without designing DPR).
- **Shoot-day detail?** → Shape named (`shooting_day_details`), fields
  deferred to the call-sheet slice.
- **Real locations?** → Account-level `locations` directory defined here;
  `setting` mapping deferred.
- **Permissions?** → Additive `production_members` layer; `script_members`
  untouched; `can_view_sensitive` gate; seat per member.
- **Ingestion?** → Manual forms baseline; CSV fast-follow for crew/contacts;
  AI-parse deferred.
- **App placement?** → `/productions` list + per-production tabbed
  workspace; explicit creation; association at upload and from the
  production page.

## References

- Backlog: "Production data model", "Add CREW and production detail for
  scheduling + call sheets / sides", "Department Workspaces", "Auto AI
  scheduling (first pass)", "Separate Location (production element) from
  Sets (creative)", "Series / multi-episode analysis" (Board/Schedule
  integration sub-item)
- `docs/SPEC_Daily_Production_Reporting.md` — Unit entity, per-production
  configuration
- `backend/db/migrations/030_shooting_schedules.sql` — schedule schema to
  extend
- `backend/db/migrations/045_series_seasons.sql` — the parallel independent
  axis and its nullable-FK pattern
- `backend/db/migrations/048_casting.sql`, `049_cast_tab_v2.sql` — the
  directory + photos + per-script-link pattern crew/locations should follow
- `backend/middleware/authorization.py` — `get_script_role`, resolver
  pattern the production-membership layer mirrors
- `frontend/src/components/series/SeriesPicker.jsx` — the upload-time
  association picker pattern
