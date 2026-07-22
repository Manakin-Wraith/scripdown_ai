# Series / Multi-Episode Analysis — Phase 1 (Grouping & Reporting Layer)

**Date:** 2026-07-22
**Status:** Approved for planning
**Backlog item:** "Series / multi-episode analysis" (`docs/BACKLOG.md`)

## 1. Summary

SlateOne's data model is single-script-centric today: one upload, one set of
scenes, one breakdown. Productions working a TV season need to manage a set
of related episode scripts together and see combined views across them (a
season's full cast, at a glance).

This is Phase 1 of a two-phase idea captured in the backlog. Phase 1 is a
**grouping and reporting layer only** — it does not change how an individual
script is uploaded, parsed, or analyzed, and it does not attempt cross-episode
character/location identity resolution (that's Phase 2, deferred and out of
scope here — see §6).

## 2. Goals

- Let a user group related episode scripts into a **Series → Season →
  Episode** hierarchy.
- Give each season a page listing its episodes in the right order.
- Give each season a **combined cast view** — one row per distinct character
  name across the season's visible episodes, grouped by exact (case-insensitive)
  name match.
- Zero changes to per-script upload, parsing, AI analysis, or entitlement/
  billing logic. Every episode is billed exactly as a standalone script is
  today; series/season membership is free.
- A script not assigned to a series behaves exactly as it does today —
  this is purely additive.

## 3. Data Model

### 3.1 New tables

```sql
CREATE TABLE series (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE seasons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    series_id UUID NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    season_number INT NOT NULL,
    title TEXT,                       -- optional override, e.g. "Season 2: The Return"
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (series_id, season_number)
);

ALTER TABLE scripts
    ADD COLUMN season_id UUID REFERENCES seasons(id) ON DELETE SET NULL,
    ADD COLUMN episode_number INT;
```

- `owner_id` on `series` is the creating user — used only to scope "my
  series" listings, not as an access-control gate (see §3.2).
- `scripts.season_id` / `scripts.episode_number` are both nullable. A
  standalone script (the common case, unchanged) has both `NULL`.
- `ON DELETE SET NULL` on `scripts.season_id`: deleting a season un-groups its
  episodes rather than cascading destructively into script data.
- No uniqueness constraint on `(season_id, episode_number)` — episode
  renumbering (e.g. inserting "4.5") shouldn't require a transaction to avoid
  transient collisions. A soft warning in the UI if a number is reused is
  enough for v1.

### 3.2 Access control

Series/seasons have **no independent permission model**. A user can see a
series/season/episode-list entry if and only if they already have
viewer-or-above access to at least one script inside it, via the existing
`require_script_role` / `get_script_role` machinery
(`backend/middleware/authorization.py`) applied per-episode. Concretely:

- Listing a user's series: return only series where at least one contained
  script passes their existing per-script access check.
- Viewing a season page: filter its episode list down to only the scripts the
  requesting user can access; episodes they can't see are simply absent, not
  shown-but-redacted.
- The combined cast view only aggregates data from episodes the requester can
  see.

This means two users on different teams could theoretically have scripts in
the same series (unlikely in practice, since assignment is a deliberate user
action) and each would only ever see their own accessible episodes.

### 3.3 Billing

No entitlement logic touches `series`/`seasons` at all. `entitlement_service.py`
is untouched by this feature. Each episode script consumes/costs exactly as a
standalone script does under Tier 1 or Tier 2 today.

## 4. Upload Flow

The existing script upload flow gains one optional step, presented after file
selection and before (or alongside) existing metadata fields:

**"Add to a series"** picker, three states:

1. **None** (default) — upload proceeds exactly as today. `season_id` and
   `episode_number` are omitted/`NULL` in the create request.
2. **Existing season** — pick a series (owned/accessible to the user) → pick
   a season within it, or "+ New season" inline (prompts for a season
   number) → enter an episode number for this script.
3. **New series** — enter a series title → season defaults to "Season 1"
   (number editable) → enter an episode number.

The upload request (`upload_script` in `backend/routes/supabase_routes.py`)
gains two optional form fields, `season_id` and `episode_number`, alongside
today's file/metadata fields. No changes to PDF parsing, scene detection, or
the analysis queue — this is purely metadata attached to the `scripts` row
already being created.

**Reassignment after the fact.** The same three-state picker is reachable
from a script's existing settings/edit surface, so a script can be moved
into, out of, or between seasons later — covering both "I forgot at upload
time" and "I'm backfilling older scripts into a newly-created series."

## 5. Series / Season Page & Combined Cast View

### 5.1 New routes (frontend)

- `/series` — list of series visible to the current user (at least one
  accessible episode).
- `/series/:seriesId` — a series' seasons, each showing its episode count.
- `/series/:seriesId/seasons/:seasonId` — the season page: ordered episode
  list (by `episode_number`) linking through to each episode's existing
  scene/breakdown view (unchanged), plus the combined cast view.

### 5.2 New backend endpoints

- `GET /api/series` — series visible to the user.
- `POST /api/series` — create a series (+ optional first season).
- `GET /api/series/<series_id>/seasons` — seasons in a series.
- `POST /api/series/<series_id>/seasons` — create a season.
- `GET /api/seasons/<season_id>/episodes` — episodes in a season, filtered to
  the requester's accessible scripts, ordered by `episode_number`.
- `PATCH /api/scripts/<script_id>/season` — assign/reassign/clear a script's
  `season_id` + `episode_number` (used by both the upload-time picker and the
  later-reassignment surface).
- `GET /api/seasons/<season_id>/cast` — the combined cast view.

All new routes require `@require_auth`; per-episode visibility is enforced by
calling `get_script_role(script_id, user_id)` (`middleware/authorization.py`
— the same lookup `require_script_role`'s decorator uses internally) for each
episode in a series/season and keeping only those where the caller holds at
least `viewer`, rather than inventing a parallel access-check mechanism. The
single-script `PATCH /api/scripts/<script_id>/season` endpoint uses
`@require_script_role('member')` directly, the same way other script-scoped
mutation routes in `supabase_routes.py` already do.

### 5.3 Combined cast view computation

Computed on request, not materialized — the same pattern
`report_service.py` already uses for per-script aggregation:

1. Fetch the season's visible episodes.
2. For each, fetch its character list (however scenes already expose cast
   today — `scenes.characters` / the existing character-analysis surface).
3. Group rows by `name.strip().upper()` (matching the exact-name-match
   decision — same normalization already used by
   `merge_characters`'s alias comparison in `supabase_routes.py`, for
   consistency with existing case-handling conventions in this codebase).
4. Return one row per distinct name with the list of episodes (title +
   episode number) it appears in.

A character appearing under two genuinely different spellings (e.g. "JOHN"
vs "Jon") is **not** merged — that's exactly the gap Phase 2 exists to close
later. This view is explicitly a convenience aggregation, not a claim of
identity.

## 6. Explicitly Out of Scope (future work)

- **Phase 2 — cross-episode entity continuity.** Fuzzy/AI-assisted matching
  so differently-spelled or independently-extracted mentions of the same
  character resolve to one identity across episodes. Would extend
  `entity_resolver.py`'s existing single-script duplicate-merging logic
  across scripts within a season. Separate brainstorm/spec when picked up.
- **Season-wide schedule/stripboard.** Merging `shooting_schedules` across a
  season's episodes. `shooting_schedules` is strictly `script_id`-scoped
  today; this needs its own design.
- **Cross-episode reports** beyond the combined cast view (e.g. a season-wide
  prop list, location list, or PDF/CSV report spanning multiple episodes).
- **Season/series-level billing** (discounted per-episode rate for season
  bulk uploads). Confirmed explicitly out of scope for Phase 1 — every
  episode is billed identically to a standalone script.

## 7. Testing Plan

- Backend: new tests for `series`/`seasons` CRUD routes, the
  `PATCH /api/scripts/<id>/season` reassignment endpoint, and the combined
  cast view's grouping logic (exact-match grouping, case-insensitivity,
  visibility filtering when the requester lacks access to some episodes).
- Access control: a route-enforcement test (mirroring
  `test_route_enforcement.py`'s pattern) confirming every new route requires
  auth and correctly filters to only the requester's accessible episodes —
  given this codebase's history with auth-gap incidents
  (`analysis_routes.py` had none at all; `list_members` was IDOR-shaped),
  this is the single highest-risk area of this feature and should not ship
  without an explicit test proving a user cannot see another user's
  inaccessible episodes via the season/series endpoints.
- Frontend: `npm run build` must pass; manual verification of the upload-time
  picker (all three states) and the season page's combined cast view against
  a real multi-episode season in a dev environment.

## 8. Migration

New migration file `backend/db/migrations/<next>_series_seasons.sql`
containing the DDL in §3.1. No backfill needed — existing scripts simply
have `season_id`/`episode_number` as `NULL`, which is their correct,
unchanged state.
