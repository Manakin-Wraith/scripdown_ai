# Upload page: known-series picker + visual polish — design

**Status:** Approved, ready for planning
**Date:** 2026-07-23
**Related:** `docs/superpowers/specs/2026-07-23-series-nested-script-table-design.md` (shipped the `?seriesId=&seasonId=` deep link this design consumes), `docs/BACKLOG.md` — "Series / multi-episode analysis" entry (SeriesPicker/SeriesAssignmentModal noted as still-unstyled)

## Problem

`SeriesPicker.jsx` has no CSS at all — it renders as raw browser-default buttons/selects/inputs floating on the app's dark page background (confirmed live, screenshot). Separately, when arriving at `/upload` via a season's "Add episode" deep link, the picker shows the exact same 3-tab "pick a series from scratch" UI as a cold upload, just with values pre-filled — the fact that the series is already known isn't reflected in the UI at all, and a user has to notice the dropdowns aren't empty. The account owner also flagged a functional gap: episodes are sometimes uploaded out of sequence (e.g. episode 5 before episode 3), and the UI needs to make that just as easy as accepting the suggested next number, not something that feels like fighting the form.

## Goals

- Give `SeriesPicker.jsx` real visual styling matching the app's dark navy/amber design language, for both the cold-upload (classic 3-tab) and known-series cases.
- When arriving via `/upload?seriesId=..&seasonId=..`, show the series as known context (not a re-pickable dropdown), while season and episode number remain live, editable controls — explicitly supporting out-of-sequence episode numbers, not just the suggested next one.
- Keep a clear escape hatch ("Not this series?") for the case where someone followed the wrong link or wants to override entirely.

## Non-goals

- `SeriesAssignmentModal.jsx` (the post-upload reassignment surface) is unchanged — stays on the classic unstyled 3-tab picker. Styling it is a separate, already-tracked backlog item.
- No change to the cold-upload (`/upload`, no query params) *behavior* — same 3 modes (none/existing/new), just visually styled.
- No backend changes. Reuses `listSeries()`, `listSeasons()`, `listEpisodes()` — all already exist.

## Design

### 1. `SeriesPicker.jsx`: new "known series" render path

Add a derived boolean, `isKnownSeries = !!(initialSeriesId && initialSeasonId)` (both required — a `seasonId`-only deep link, which shouldn't occur given `ScriptTable.jsx` always sends both, falls back to the classic picker rather than a half-known state).

New state: `overridden` (boolean, default `false`) — when `true`, renders the classic 3-tab picker instead, even if `isKnownSeries` is true.

When `isKnownSeries && !overridden`, render the new compact layout instead of the tabs:
- A series badge + name. Name comes from `listSeries()` (already fetched when needed — call it unconditionally on mount when `isKnownSeries`, not gated behind `mode === 'existing'` as today, since there's no tab click to gate it), filtered to `initialSeriesId`. No new backend endpoint needed.
- A season `<select>`, populated via `listSeasons(initialSeriesId)` (reuses the existing effect/fetch, just no longer gated on `mode`), defaulting to `initialSeasonId`.
- An episode-number `<input>`, always editable, pre-filled with a suggested next number (see below) but never disabled or read-only.
- A "Not this series?" button that sets `overridden = true`, revealing the classic tabs starting from a clean `'none'` state (not re-pre-filled with the same series — the user just said it's wrong).

Both the season select and the episode-number input fire `onAssign(selectedSeasonId, Number(episodeNumber))` directly on every `onChange` — no separate "Assign" button in this view, since the values displayed *are* the current assignment (unlike the classic 'existing' mode's explicit-confirm model, which still applies when `overridden` is true).

### 2. Episode-number suggestion moves into `SeriesPicker`

Today `ScriptUpload.jsx` computes the initial suggested episode number once (via `listEpisodes(seasonId)`, `max(episode_number) + 1`) and passes it in as `initialEpisodeNumber`. Since the season is now a live dropdown *inside* the picker, the suggestion needs to recompute whenever the selected season changes (numbering is per-season) — so this logic moves into `SeriesPicker.jsx` itself:

- New effect: whenever `selectedSeasonId` changes (in the known-series view), call `listEpisodes(selectedSeasonId)`, compute `nextNumber = max(episodes.map(e => e.episode_number || 0), 0) + 1`, and set the episode-number field to that value — overwriting any manual edit, since switching seasons changes what "next" means anyway. This also fires `onAssign` with the new season + suggested number, so `pendingSeasonAssignment` in `ScriptUpload.jsx` stays in sync without the user touching anything.
- The `initialEpisodeNumber` prop becomes unused for the known-series path (kept as a prop for now since it's harmless and `SeriesAssignmentModal`'s potential future use isn't precluded) — `ScriptUpload.jsx` no longer needs to precompute it itself.

### 3. `ScriptUpload.jsx` simplifies

The existing `useEffect` that reads `seasonId`/`seriesId` from the URL and calls `listEpisodes` to precompute `seriesPrefill` is replaced with a much smaller one: just read `seriesId`/`seasonId` from `searchParams` and pass them straight through as `initialSeriesId`/`initialSeasonId` props. `listEpisodes` and the episode-number math move to `SeriesPicker.jsx` (§2). `seriesPrefill` state's shape simplifies to `{seriesId, seasonId} | null` (episodeNumber no longer computed here).

### 4. `SeriesPicker.css` (new file)

First stylesheet for this component. Styles both render paths:
- Classic tabs (`.series-picker-modes` buttons — active/inactive states), the `.series-picker-existing`/`.series-picker-new` panels (selects, number input, buttons) — dark card background, amber active-tab state, matching `ScriptTable.css`'s existing token usage (`var(--gray-800)`, `var(--gray-700)`, `var(--primary-500)`, `var(--primary-alpha-*)`, `var(--border-color)`, `var(--text-primary)`, `var(--text-secondary)`).
- New known-series layout — series badge (amber-tinted pill), season/episode-number field row with uppercase micro-labels (matching the mockup approved during brainstorming), and an active-state hint under the episode-number field ("Suggested next — change to upload out of sequence").

### Error handling

- `listSeries()`/`listSeasons()`/`listEpisodes()` failures in the known-series view set the existing `error` state (same pattern as the classic picker) and are non-fatal — the upload itself is never blocked by a failed prefill/suggestion lookup, matching the existing principle established in Task 4 of the prior design.
- If `initialSeriesId` doesn't match any series returned by `listSeries()` (e.g. deleted between click and load), the badge falls back to showing the raw id or a generic "Series" label rather than crashing — exact copy decided during implementation, not load-bearing.

## Testing

- No frontend test runner exists in this repo (confirmed, unchanged) — verification is `npm run build` succeeding, plus a manual/live check against real series data (the account owner has stated they'll verify in production after this ships, consistent with the prior session).
- No backend changes, so no backend test changes.

## References

- `frontend/src/components/series/SeriesPicker.jsx` — main change, new known-series render path + moved episode-number logic
- `frontend/src/components/series/SeriesPicker.css` — new file
- `frontend/src/components/script/ScriptUpload.jsx` — simplified prefill effect
- `frontend/src/services/apiService.js` — `listSeries`, `listSeasons`, `listEpisodes` (all reused, unchanged)
- `frontend/src/components/scripts/ScriptTable.css` — token/pattern reference for the new stylesheet
- Explicitly unchanged: `frontend/src/components/series/SeriesAssignmentModal.jsx`
