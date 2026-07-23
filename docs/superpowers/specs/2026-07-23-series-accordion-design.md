# Series list/detail accordion merge — design

**Date:** 2026-07-23
**Status:** Approved, ready for planning

## Context

Backlog item "Series / multi-episode analysis" flagged the `/series` area's
3-level click-through (`/series` → series detail → season) as unchanged
since the My Scripts table grouping shipped as a parallel fast path
(2026-07-23). Brainstormed via `superpowers:brainstorming`.

Two pain points drove this:
1. Too many clicks/page loads to reach a specific season — two full page
   navigations even when the destination is known.
2. Redundant with My Scripts: `ScriptTable.jsx` already renders series →
   season → episode inline (collapsible, localStorage-persisted), so
   `SeriesDetailPage`'s season list duplicates structure the user has
   often already seen.

Investigation found `SeriesDetailPage.jsx` carries no unique data of its
own — it's purely a season-picker step. The only content with no home
elsewhere is `SeasonPage.jsx`'s combined cast table (and future
season-level metrics, tracked separately in the backlog). So the fix is
to remove the season-picker page as a separate navigation, not to add
new functionality.

**Explicitly out of scope** (deferred to other open backlog items):
`SeriesAssignmentModal` styling, the `.series-page` left-alignment bug
(`SeriesPages.css:6-8`), and season-level metrics content.

## Design

### Routing (`frontend/src/App.jsx`)

- `series` → `SeriesListPage` — unchanged path; page becomes an accordion
  (see below).
- `series/:seriesId` → no longer renders `SeriesDetailPage`. Replaced with
  a `<Navigate to={`/series?expand=${seriesId}`} replace />` redirect, so
  existing bookmarks/links to this URL still land somewhere useful.
- `series/:seriesId/seasons/:seasonId` → `SeasonPage` — unchanged, still
  the terminal destination for a season.
- `SeriesDetailPage.jsx` is deleted; its season-list rendering (row
  markup, empty state) moves into `SeriesListPage.jsx`'s expanded-row
  content.
- `frontend/src/components/scripts/ScriptTable.jsx`'s "View series"
  action (currently `navigate(`/series/${series.id}`)`, line ~323)
  changes to `navigate(`/series?expand=${series.id}`)`, landing directly
  on the pre-expanded accordion instead of round-tripping through the
  redirect.

### `SeriesListPage.jsx` (accordion)

- Each series row becomes a toggle (chevron rotates open/closed) instead
  of a `<Link>` to a detail page.
- Expand state and each series' fetched seasons are kept in local
  component state, keyed by series id (`Set` of expanded ids +
  `Map`/object of `seriesId -> seasons[]`), so collapsing and
  re-expanding a row does not refetch.
- On a series' *first* expand, fetch its seasons via the existing
  `listSeasons(seriesId)` API call (moved here from
  `SeriesDetailPage.jsx` — no new endpoint).
- Expanded content renders a nested `series-row-list` of season rows
  (same markup/classes `SeriesDetailPage` used: badge with season
  number, title fallback `Season N`, chevron), each a real `<Link>`
  straight to `/series/:seriesId/seasons/:seasonId`.
- Empty-seasons state per series reuses `SeriesDetailPage`'s empty-state
  copy ("This series doesn't have any seasons yet..."), rendered inline
  under the expanded row instead of as a full-page state.
- On mount, reads an `?expand=<seriesId>` query param (`useSearchParams`)
  and, once the series list has loaded and that id is present, expands
  it and kicks off its season fetch automatically — covering both the
  redirect path and the direct `ScriptTable.jsx` link.

### Data flow

No new API surface: `listSeries()` (page load, unchanged) and
`listSeasons(seriesId)` (moved from page-navigation-triggered to
expand-triggered, same call). `SeasonPage.jsx` and its
`listSeasons`/`listEpisodes`/`getSeasonCast` calls are unchanged.

### Error handling

- Page-level failure (`listSeries()` rejecting) keeps today's full-page
  error text (`series-page-error`).
- A single series' season-fetch failure (`listSeasons()` rejecting) shows
  inline under that row only (reuse `series-picker-error`-style inline
  text), so one bad row doesn't blow up the whole accordion or hide
  other series.

### Testing

No backend changes, so no backend test changes. Frontend has no existing
test coverage for `SeriesListPage`/`SeriesDetailPage` to update (verify
via `npm run build` per this repo's frontend-gate convention — `npm run
lint` is broken repo-wide). Manual verification: expand/collapse
multiple series, confirm no refetch on re-expand, confirm `?expand=`
deep link and the redirect from `/series/:seriesId` both land
pre-expanded, confirm a season link still reaches `SeasonPage`
correctly, confirm an empty-seasons series shows its inline empty state.

## References

- `frontend/src/App.jsx` — route definitions
- `frontend/src/pages/SeriesListPage.jsx` — becomes the accordion
- `frontend/src/pages/SeriesDetailPage.jsx` — deleted
- `frontend/src/pages/SeasonPage.jsx` — unchanged, terminal destination
- `frontend/src/pages/SeriesPages.css` — shared styles, extended for
  nested/expanded row states
- `frontend/src/components/scripts/ScriptTable.jsx` — "View series"
  action link target
- `frontend/src/services/apiService.js` — `listSeries`, `listSeasons`
  (both reused as-is)
