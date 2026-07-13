# Move Location Manager to Scheduling — Design

**Date:** 2026-07-13
**Status:** Approved (design), pending implementation plan
**Builds on:** `2026-07-13-location-manager-add-remove-design.md` (shipped) — the
`LocationManager` component is reused verbatim, only its mount point moves.
**Areas (frontend only):** `frontend/src/components/scenes/SceneViewer.jsx`,
`frontend/src/components/schedule/ShootingSchedulePage.jsx`. No backend, API, DB,
or `LocationManager.jsx` change.

## Problem

Two location-editing surfaces sit side by side on the Script Summary screen and
read as redundant/confusing:

1. **Merge duplicates** — inline checkboxes in the Script Summary `LOCATIONS`
   list (symmetric with character merge), for collapsing two names that are the
   *same place* (`VILLA` + `THE VILLA` → one). This is breakdown **accuracy**.
2. **Manage Locations modal** — a button next to that list opening `LocationManager`,
   which does **rename** (creative naming) and **Add/Remove grouping** (declaring
   that rooms shoot together). Grouping is a **scheduling/logistics** concern.

Three distinct jobs — dedup, rename, group — with dedup and (rename+group) crammed
onto the same screen. The adjacency is the confusion.

## Goal

Separate the jobs by where their payoff lives, removing the redundancy:

- **Script Summary keeps dedup only.** Remove the "Manage locations" button (and
  the modal mount) from the summary/`SceneViewer`. Merge stays exactly as is.
- **Scheduling gains the Location Manager.** Mount the existing `LocationManager`
  (rename + Add/Remove grouping, unchanged) on the Shooting Schedule page, where
  grouping locations into shooting units is the natural task. After a change, the
  schedule board refreshes so regrouping is reflected immediately.

## Non-Goals

- No change to `LocationManager.jsx` / `.css` — it is mounted, not modified.
- No backend, `apiService.js`, or DB change (grouping/rename endpoints unchanged).
- No change to the merge/dedup flow in `ScriptSummary.jsx`.
- No new "rename" surface in the Summary — rename lives with grouping in the
  Location Manager (avoids re-introducing two editors).

## Architecture

### Part A — Remove from Script Summary (`SceneViewer.jsx`)

Currently (`SceneViewer.jsx` ~lines 42, 606–620): a `showLocationManager` state, a
`Manage locations` pill button, and a conditional `<LocationManager …>` mount live
above `<ScriptSummary>`. Remove all three, plus the now-unused
`import LocationManager from './LocationManager'` (line 8) and the
`const [showLocationManager, setShowLocationManager] = useState(false)` (line 42).

`ScriptSummary` (merge/dedup) and the rest of `SceneViewer` are untouched. The
`refreshScenes` callback stays (still used elsewhere in the file).

### Part B — Add to Shooting Schedule (`ShootingSchedulePage.jsx`)

`LocationManager` needs `scenes` (to build its tree) and an `onChanged` refetch.
`ShootingSchedulePage` does not currently load scenes, so add:

1. **Import:** `LocationManager` from `../scenes/LocationManager`, `getScenes` from
   `../../services/apiService`, and a suitable icon (`MapPin`) from `lucide-react`.
2. **State:** `const [scenes, setScenes] = useState([]);` and
   `const [showLocationManager, setShowLocationManager] = useState(false);`.
3. **Fetch scenes:** in the existing initial `load` effect (which already runs
   `Promise.all([getSchedules, getScriptMetadata])`), add `getScenes(scriptId)`
   and `setScenes(sceneData.scenes ?? sceneData ?? [])` — matching the shape
   `getScenes` returns (see note below). Failure to load scenes is non-fatal: log
   and leave `scenes` empty (the manager then shows "No locations yet.").
4. **Toolbar button:** a "Manage locations" button in the schedule page header/
   toolbar (near the Print control) that sets `showLocationManager(true)`.
5. **Mount:**
   ```jsx
   {showLocationManager && (
       <LocationManager
           scriptId={scriptId}
           scenes={scenes}
           onClose={() => setShowLocationManager(false)}
           onChanged={refreshLocationsAndBoard}
       />
   )}
   ```
6. **onChanged refresh** — after a grouping/rename change, both the scene list
   (for the manager's own tree) and the board must refresh:
   ```javascript
   const refreshLocationsAndBoard = useCallback(async () => {
       try {
           const sceneData = await getScenes(scriptId);
           setScenes(sceneData.scenes ?? sceneData ?? []);
       } catch (err) {
           console.error('Failed to refresh scenes:', err);
       }
       await refreshDays(); // existing callback — reloads shooting days/board
   }, [scriptId, refreshDays]);
   ```

### `getScenes` return shape

`getScenes` is already used by `SceneViewer`. The plan's implementer MUST read
`apiService.js:136` (`getScenes`) and `SceneViewer.jsx:56–60` to confirm whether it
returns an array or `{ scenes: [...] }`, and unwrap identically (`SceneViewer`
stores the result via `setScenes(fetchedScenes)` from a `Promise.all` — match that
exact unwrapping). Do not guess the shape.

## Data Flow

```
Shooting Schedule page → "Manage locations" → LocationManager (rename + Add/Remove)
  user groups rooms under VILLA / renames a location
    -> nestLocation / unnestLocation / rename* (existing endpoints, unchanged)
    -> onChanged: getScenes() refetch + refreshDays()
       -> board reflects the regrouping; manager tree updates
Script Summary → merge checkboxes only (dedup) — unchanged
```

## Error Handling / Edge Cases

- **Scenes fail to load on the schedule page:** non-fatal; manager opens with an
  empty tree ("No locations yet."). Board is unaffected.
- **A grouping change fails:** `LocationManager`'s existing `run` helper toasts the
  error; already-applied changes persist (unchanged behavior).
- **User never opens the manager:** the extra `getScenes` call is one small fetch
  on page load; acceptable. (Optional: lazy-fetch scenes on first open — the plan
  may choose the simpler eager fetch to match `SceneViewer`.)

## Testing / Verification

- **Frontend gated on `npm run build`** (repo lint known-broken).
- **No backend tests in scope** (no backend change; existing 54 location tests and
  the grouping/rename endpoints already cover the data behavior).
- **Grep gates** after implementation:
  - `SceneViewer.jsx`: no `LocationManager`, `showLocationManager`, or
    `Manage locations` remain.
  - `ShootingSchedulePage.jsx`: `LocationManager`, `getScenes`, and
    `Manage locations` are present.
- **Manual E2E:** on the schedule page of the real script, open "Manage locations",
  group `GARAGE / BACKROOM` + `MOODY BACKROOM` under VILLA, confirm the board
  updates; confirm the Script Summary screen no longer shows a "Manage locations"
  button and still merges duplicates.

## Copy Reference

- Schedule toolbar button label: `Manage locations` (same wording as before, new
  home).
- All `LocationManager` internal copy unchanged (Add / Remove / rename / purpose
  header).
