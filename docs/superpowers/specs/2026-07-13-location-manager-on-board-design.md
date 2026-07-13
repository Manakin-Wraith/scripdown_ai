# Move Location Manager to the Board — Design

**Date:** 2026-07-13
**Status:** Approved (design), pending implementation plan
**Supersedes placement of:** `2026-07-13-location-manager-move-to-scheduling-design.md`
(shipped) — the Location Manager moves from the Shooting Schedule page to the
Board. The `LocationManager` component is reused verbatim.
**Areas (frontend only):** `frontend/src/components/board/ZoomableStripboard.jsx`,
`frontend/src/components/board/BoardToolbar.jsx`,
`frontend/src/components/schedule/ShootingSchedulePage.jsx`. No backend, API, DB,
or `LocationManager.jsx` change.

## Problem

The Location Manager currently lives on the Shooting Schedule page (downstream).
The **Board** (`ZoomableStripboard`, route `/scripts/:scriptId/board`) is the
upstream surface where scenes are arranged and can be **grouped by Location** — so
managing locations there is more contextual (you watch scenes fall into location
lanes as you group them) and it happens *before* scheduling. The Board also already
holds everything the manager needs — `scriptId`, the loaded `state.scenes`, and a
`refreshBoard` callback — so it is a cleaner mount than the Schedule page (which
needed its own scenes fetch).

## Goal

Relocate the Location Manager to the Board, single home:

- **Board gains it.** A "Manage locations" button in the `BoardToolbar` (beside the
  Group By selector, where Location grouping lives) opens the existing
  `LocationManager`, wired to `state.scenes` and `refreshBoard`.
- **Schedule loses it.** Revert the Schedule-page mount added in commit `f61c8dd`
  (button, modal, `scenes`/`showLocationManager` state, the `getScenes` fetch, and
  `refreshLocationsAndBoard`), returning `ShootingSchedulePage.jsx` to its
  pre-`f61c8dd` shape for those hunks.

## Non-Goals

- No change to `LocationManager.jsx`/`.css` — mounted, not modified.
- No backend, `apiService.js`, or DB change.
- No change to Board grouping/filtering/scheduling logic — only a button + modal
  mount are added.
- Not on both surfaces — Board only.

## Architecture

### Part A — Add to the Board

**`BoardToolbar.jsx`:**
- Add `onManageLocations` to the component's props.
- Import `MapPin` from `lucide-react` (add to the existing import on line 2).
- Render a "Manage locations" button in the **center section**, immediately after
  the Group By `pill-group` closes (inside `.toolbar-group-by` or as its sibling in
  the center `toolbar-section`), reusing the existing `pill-btn` class:
  ```jsx
  <button className="pill-btn" onClick={onManageLocations} title="Group and rename locations">
      <MapPin size={14} /> Manage locations
  </button>
  ```

**`ZoomableStripboard.jsx`:**
- Add `useState` to the React import (line 1 currently imports
  `useReducer, useEffect, useMemo, useRef, useCallback`).
- Import `LocationManager` from `../scenes/LocationManager`.
- Add state: `const [showLocationManager, setShowLocationManager] = useState(false);`.
- Pass `onManageLocations={() => setShowLocationManager(true)}` to `<BoardToolbar>`.
- Mount the modal (e.g. after the `<BoardCanvas>` / alongside the `StripDetailDrawer`
  block), reusing the board's existing scenes + refresh:
  ```jsx
  {showLocationManager && (
      <LocationManager
          scriptId={scriptId}
          scenes={state.scenes}
          onClose={() => setShowLocationManager(false)}
          onChanged={refreshBoard}
      />
  )}
  ```
  `state.scenes` is already populated (used by `buildBoardViewModel`), and
  `refreshBoard` (defined ~line 110) refetches scenes + items and re-renders the
  board — so a grouping/rename change reshapes the Location lanes immediately.

### Part B — Remove from the Schedule page

Revert the `f61c8dd` additions in `ShootingSchedulePage.jsx`:
- Remove `MapPin` from the `lucide-react` import and `getScenes` from the
  `apiService` import (both were added only for the manager — confirm no other use
  in the file before removing).
- Remove `import LocationManager from '../scenes/LocationManager';`.
- Remove the `scenes` and `showLocationManager` state.
- Restore the initial-load `Promise.all` to its two-element form
  (`[getSchedules, getScriptMetadata]`) and drop the `setScenes(...)` line.
- Remove the `refreshLocationsAndBoard` useCallback.
- Remove the "Manage locations" toolbar button and the `<LocationManager …>` mount.

The Schedule page's `refreshDays` and everything else remain unchanged.

## Data Flow

```
Board (Group By: Location) → "Manage locations" → LocationManager (rename + Add/Remove)
  user groups rooms under VILLA / renames a location
    -> nestLocation / unnestLocation / rename* (existing endpoints, unchanged)
    -> onChanged: refreshBoard() → refetch scenes+items → Location lanes reshape live
Schedule page → no location management (downstream consumer of the grouping)
```

## Error Handling / Edge Cases

- **`onManageLocations` not passed** (defensive): the button calls whatever prop is
  given; `ZoomableStripboard` always passes it, so no guard needed. If a future
  caller omits it, the `onClick` is `undefined` and the button is inert — no crash.
- **A grouping change fails:** `LocationManager`'s `run` helper toasts the error;
  applied changes persist (unchanged behavior).
- **Board still loading** (`state.loading`): the toolbar renders after load as
  today; the button appears with the rest of the toolbar. `state.scenes` is an
  array throughout, so an early open shows the current (possibly empty) tree.

## Testing / Verification

- **Frontend gated on `npm run build`** (repo lint known-broken).
- **No backend tests in scope** (no backend change).
- **Grep gates after implementation:**
  - `ShootingSchedulePage.jsx`: no `LocationManager`, `showLocationManager`, or
    `Manage locations`; `getScenes`/`MapPin` gone unless used elsewhere.
  - `BoardToolbar.jsx`: `onManageLocations` + `Manage locations` present.
  - `ZoomableStripboard.jsx`: `LocationManager` import + mount + `onManageLocations`
    present.
- **Manual E2E:** on the Board, switch Group By → Location, click "Manage
  locations", group `GARAGE / BACKROOM` + `MOODY BACKROOM` under `VILLA`; confirm
  the Location lanes reshape immediately. Confirm the Schedule page no longer shows
  a "Manage locations" button.

## Copy Reference

- Board toolbar button label: `Manage locations` (with `MapPin` icon).
- All `LocationManager` internal copy unchanged.
