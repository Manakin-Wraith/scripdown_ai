# Series/season grouping in My Scripts — design

**Status:** Approved, ready for planning
**Date:** 2026-07-23
**Related:** `docs/superpowers/specs/2026-07-22-series-multi-episode-phase1-design.md` (Phase 1 series/season feature this builds on), `docs/BACKLOG.md` — "Series / multi-episode analysis" entry (the open "UX/UI reassessment" item this partially resolves)

## Problem

Phase 1 shipped series/season assignment (`SeriesPicker`, `SeriesAssignmentModal`, `/api/series` routes, `045_series_seasons.sql`), but the My Scripts table (`ScriptTable.jsx`) still renders every script as a flat row with no visual indication of series/season membership beyond a tooltip on a small icon. A user managing a multi-episode series has no way to see their season's episodes grouped together in the list they look at every day — they either scroll through a flat list hunting for episodes, or navigate out to the separate `/series` pages to browse by season. This is friction Phase 1 didn't address: assigning an episode's series happens inline (already fixed, `SeriesPicker` is embedded in the upload flow), but *browsing* your library by series was never addressed.

## Goals

- My Scripts becomes the fast, glanceable way to see a script's series/season context and browse episodes grouped together, without leaving the page.
- Adding the next episode to an existing season should not require re-navigating through the full "pick existing series → pick season → enter episode number" flow every time.
- The dedicated `/series` pages (`SeriesListPage`, `SeriesDetailPage`, `SeasonPage`) are **not replaced** — they remain the place for series-level views that don't belong in a flat script list, primarily the combined cast-across-episodes view. My Scripts and `/series` serve different purposes: browsing/assigning vs. deeper series management.

## Non-goals

- No changes to Board/Scheduling/Reporting — those remain strictly per-script, out of scope for this design (a separate, larger question noted in `docs/BACKLOG.md`).
- No changes to `SeriesAssignmentModal`'s reassign/remove behavior for an individual episode — that stays as-is.
- No changes to the combined cast view or any other content of the `/series` pages themselves.

## Design

### 1. Backend: join series/season names into the script list

`GET /api/scripts` (`backend/routes/supabase_routes.py`) currently returns each script row with only `season_id` and `episode_number` — no series or season *names*, so the frontend cannot group/label without additional round-trips per script.

Extend the query backing this endpoint to join through `seasons` → `series` (both tables and their FKs already exist from migration `045_series_seasons.sql`; `scripts.season_id` is nullable, `ON DELETE SET NULL`, so the join must be a left join / equivalent so scripts with no season are unaffected) and include on each script object:
- `series_id` (nullable)
- `series_title` (nullable)
- `season_number` (nullable)
- `season_title` (nullable, may be blank/null if a season was never given a title)

This is one additional join on an existing endpoint, no new endpoint, no N+1 (avoids a per-script or per-series follow-up fetch). Scripts with `season_id = null` get `null` for all four new fields, matching today's behavior for unassigned scripts.

### 2. Frontend: grouped, collapsible rendering in `ScriptTable.jsx`

Replace the flat `sortedScripts.map(...)` body with a grouping pass:

1. Bucket `scripts` by `series_id`, then within each series bucket by `season_id`. Scripts with `series_id === null` go into a separate "ungrouped" bucket.
2. Render order: series groups first, ungrouped scripts flat below (as today, sortable by the existing column-sort controls — sorting continues to apply only to the ungrouped section, since grouped episodes have a more meaningful order below).
3. Within a series group: a **series header row** (title, chevron toggle), containing one or more **season sub-header rows** nested under it (season number/title, episode count, chevron toggle), each containing its episodes as normal table rows sorted by `episode_number` ascending — episode order within a season is not user-sortable, since episode number is the only order that makes sense for a season.
4. Series ordering among groups: alphabetical by `series_title` (simplest, predictable, no new "most recently active" computation needed).
5. Group and sub-group collapse state persists per-user via `localStorage`, keyed by `series_id` / `season_id`, **defaulting to collapsed** on first encounter. This keeps the table compact for users with several series once the library grows; expand state survives reloads.

Component boundaries: `ScriptTable.jsx` gains the grouping/bucketing logic and renders new small presentational pieces (`SeriesGroupHeader`, `SeasonGroupHeader` — can be inline sub-components in the same file initially, given the file is not large; split out only if it grows unwieldy). No changes to `ScriptLibrary.jsx`'s data-fetching beyond receiving the four new fields already present on each script object from step 1 — no new API calls from the frontend.

### 3. Group header actions

- **Chevron**: toggles collapse state (persisted per above).
- **"View series" link**: navigates to `/series/:series_id` (series header) — the existing `SeriesDetailPage`. No equivalent link is needed on the season sub-header since `SeriesDetailPage` already lists seasons.
- **"+ Add episode" button** (season sub-header only): navigates to `/upload?seasonId=<season_id>`.

### 4. Upload deep-link: `?seasonId=` query param

`ScriptUpload.jsx` reads `seasonId` from the URL on mount (via `useSearchParams` or equivalent). When present:
- Pre-fill `pendingSeasonAssignment` with `{ seasonId, episodeNumber: <next sequential number> }`, computed as `max(existing episode_number in that season) + 1` (fetched via the existing `GET /api/seasons/:id/episodes` call, or included as part of a small lookup — reuses the existing series routes, no new backend endpoint).
- `SeriesPicker` still renders (not hidden/locked) but opens pre-set to "add to this season" with the season and suggested episode number already filled in — the user can still change or clear it before uploading, consistent with Phase 1's principle that assignment is always editable, never forced.

This removes the "pick existing series → pick season → type episode number" sequence for the common case (adding the next episode to a season you're actively working in), while keeping the picker fully overridable.

### 5. Per-episode row (inside a season group)

Unchanged from today: same "Series" icon action opens `SeriesAssignmentModal` to reassign or remove the episode from its series. No behavior change here — only its visual context (now nested under its season) changes.

### Error handling

- If the series/season join fails or returns unexpected nulls for a script that has a non-null `season_id` (orphaned reference, e.g. a season deleted out from under a script — though `season_id` has `ON DELETE SET NULL` so this shouldn't normally occur), the frontend treats it as ungrouped (falls back to the flat row) rather than crashing the table render.
- `?seasonId=` pointing at a season the user no longer has access to (or that no longer exists) fails the "next episode number" lookup silently — `ScriptUpload.jsx` already treats `pendingSeasonAssignment` failures as non-fatal (existing pattern, `catch` around `updateScriptSeason`), so the upload still proceeds and the user can assign manually afterward via `SeriesAssignmentModal`.

## Testing

- **Backend**: extend the existing script-list route test(s) to assert the four new joined fields appear correctly for a script with a season, and are `null` for a script with none. Verify the join doesn't break existing assertions about the endpoint's other fields.
- **Frontend**: no existing test suite covers `ScriptTable`/`ScriptLibrary` (grep confirms none) — this is consistent with the rest of the frontend, which is gated on `npm run build`, not a test suite (see project memory: frontend lint is broken repo-wide). Verify manually: `npm run build` passes, then live-check against real multi-episode series data (the existing "Die Testament" test data referenced in prior series work) — collapse/expand persists across reload, "+ Add episode" pre-fills correctly, ungrouped scripts still render and sort as before.

## References

- `backend/routes/supabase_routes.py` — script-list endpoint (join target)
- `backend/routes/series_routes.py` — existing `GET /api/seasons/:id/episodes` (reused for next-episode-number lookup)
- `frontend/src/components/scripts/ScriptTable.jsx`, `ScriptLibrary.jsx` — grouping/rendering changes
- `frontend/src/components/script/ScriptUpload.jsx` — `?seasonId=` deep-link handling
- `frontend/src/components/series/SeriesPicker.jsx`, `SeriesAssignmentModal.jsx` — unchanged, reused as-is
- `backend/db/migrations/045_series_seasons.sql` — existing schema this design joins against, no migration needed
