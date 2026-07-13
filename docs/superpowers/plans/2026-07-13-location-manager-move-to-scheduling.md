# Move Location Manager to Scheduling — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the Location Manager from the Script Summary screen and mount it on the Shooting Schedule page, leaving the Summary with dedup-only.

**Architecture:** Two-file frontend change. `SceneViewer.jsx` loses the "Manage locations" button, modal mount, state, and import. `ShootingSchedulePage.jsx` gains a scenes fetch, a toolbar button, the `LocationManager` mount, and an onChanged refresh that refetches scenes and the board. The `LocationManager` component and all backend endpoints are reused unchanged.

**Tech Stack:** React 18 (plain JSX), Vite, existing `apiService.js` (`getScenes`), `lucide-react` icons.

## Global Constraints

- **Frontend only.** No change to `LocationManager.jsx`/`.css`, `apiService.js`, any backend route, or the DB.
- **No new rename surface in the Summary.** Rename stays inside `LocationManager` (now in Scheduling). `ScriptSummary.jsx` and its merge/dedup flow are untouched.
- **`getScenes` shape (verified):** `getScenes(scriptId)` returns `response.data`; unwrap scenes as `sceneData.scenes || []` (exactly as `SceneViewer.jsx:59` does).
- **Gate on `npm run build`** from `frontend/` (repo lint known-broken).
- Button label wording stays `Manage locations`.

---

### Task 1: Remove Location Manager from Script Summary (`SceneViewer.jsx`)

**Files:**
- Modify: `frontend/src/components/scenes/SceneViewer.jsx`

**Interfaces:**
- Consumes: nothing new.
- Produces: `SceneViewer` no longer references `LocationManager` or `showLocationManager`. `refreshScenes` remains (used elsewhere in the file).

- [ ] **Step 1: Remove the import**

Delete line 8:
```javascript
import LocationManager from './LocationManager';
```

- [ ] **Step 2: Remove the state**

Delete line 42:
```javascript
    const [showLocationManager, setShowLocationManager] = useState(false);
```

- [ ] **Step 3: Remove the button and modal mount**

Delete this block (currently lines ~606–620):
```javascript
                <button
                    className="pill-btn"
                    onClick={() => setShowLocationManager(true)}
                >
                    Manage locations
                </button>

                {showLocationManager && (
                    <LocationManager
                        scriptId={scriptId}
                        scenes={scenes}
                        onClose={() => setShowLocationManager(false)}
                        onChanged={refreshScenes}
                    />
                )}

```
Leave the surrounding `Script Summary` toggle button (above) and the `{showSummary && (<ScriptSummary …>)}` block (below) intact.

- [ ] **Step 4: Verify the build passes**

Run: `cd frontend && npm run build`
Expected: build completes with no errors; no error referencing `LocationManager` or `showLocationManager`.

- [ ] **Step 5: Verify removal is clean**

Run: `grep -nE "LocationManager|showLocationManager|Manage locations" frontend/src/components/scenes/SceneViewer.jsx`
Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/scenes/SceneViewer.jsx
git commit -m "refactor(locations): remove Manage Locations from Script Summary"
```

---

### Task 2: Mount Location Manager on the Shooting Schedule page (`ShootingSchedulePage.jsx`)

**Files:**
- Modify: `frontend/src/components/schedule/ShootingSchedulePage.jsx`

**Interfaces:**
- Consumes: `LocationManager` (`../scenes/LocationManager`), `getScenes` (`../../services/apiService`), existing `refreshDays` callback, existing `scriptId`.
- Produces: a "Manage locations" button + modal on the schedule page; grouping/rename changes refresh scenes and the board.

- [ ] **Step 1: Add imports**

Add `MapPin` to the existing `lucide-react` import (line 3), e.g. append `, MapPin` before the closing brace:
```javascript
import { Plus, CalendarDays, Trash2, Pencil, Check, X, ZoomIn, ZoomOut, Maximize, RotateCcw, Printer, MapPin } from 'lucide-react';
```

Add `getScenes` to the existing `apiService` import (the block at lines 9–12):
```javascript
import {
    getSchedules, createSchedule, getShootingDays,
    getScriptMetadata, deleteSchedule, updateSchedule, getScenes,
} from '../../services/apiService';
```

Add the `LocationManager` import after the `ScheduleKanban` import (line 12):
```javascript
import LocationManager from '../scenes/LocationManager';
```

- [ ] **Step 2: Add state**

After `const [showPrintPreview, setShowPrintPreview] = useState(false);` (line 30), add:
```javascript
    const [scenes, setScenes] = useState([]);
    const [showLocationManager, setShowLocationManager] = useState(false);
```

- [ ] **Step 3: Fetch scenes in the initial load effect**

In the `load` async function (the effect at line 41), extend the existing `Promise.all` to also fetch scenes, and store them. Change:
```javascript
                const [schedData, metaData] = await Promise.all([
                    getSchedules(scriptId),
                    getScriptMetadata(scriptId),
                ]);
```
to:
```javascript
                const [schedData, metaData, sceneData] = await Promise.all([
                    getSchedules(scriptId),
                    getScriptMetadata(scriptId),
                    getScenes(scriptId).catch((err) => {
                        console.error('Failed to load scenes for location manager:', err);
                        return { scenes: [] };
                    }),
                ]);
                setScenes(sceneData.scenes || []);
```
(Place `setScenes(sceneData.scenes || []);` immediately after the destructuring, before the existing `setMetadata(metaData);` line.)

- [ ] **Step 4: Add the onChanged refresh callback**

After the existing `refreshDays` callback (ends ~line 89), add:
```javascript
    const refreshLocationsAndBoard = useCallback(async () => {
        try {
            const sceneData = await getScenes(scriptId);
            setScenes(sceneData.scenes || []);
        } catch (err) {
            console.error('Failed to refresh scenes:', err);
        }
        await refreshDays();
    }, [scriptId, refreshDays]);
```
(If `refreshDays` is defined after this point, place this callback immediately below its definition so the reference resolves.)

- [ ] **Step 5: Add the toolbar button**

In `schedule-header-right` (line 184), as the FIRST child (before the Print button block at line 186), add:
```javascript
                    <button
                        className="schedule-print-btn"
                        onClick={() => setShowLocationManager(true)}
                        title="Group and rename locations"
                    >
                        <MapPin size={14} />
                        Manage locations
                    </button>

```
(Reuses the existing `schedule-print-btn` header-button style — no CSS change. This button is always visible, not gated on `activeScheduleId`/`days`.)

- [ ] **Step 6: Mount the modal**

Immediately before the `{/* Print Preview Modal */}` block (line 275), add:
```javascript
            {showLocationManager && (
                <LocationManager
                    scriptId={scriptId}
                    scenes={scenes}
                    onClose={() => setShowLocationManager(false)}
                    onChanged={refreshLocationsAndBoard}
                />
            )}

```

- [ ] **Step 7: Verify the build passes**

Run: `cd frontend && npm run build`
Expected: build completes with no errors.

- [ ] **Step 8: Verify wiring is present**

Run: `grep -nE "LocationManager|getScenes|Manage locations|refreshLocationsAndBoard" frontend/src/components/schedule/ShootingSchedulePage.jsx`
Expected: matches for the import + mount, `getScenes` in import and both fetch sites, the button label, and the callback (defined + passed).

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/schedule/ShootingSchedulePage.jsx
git commit -m "feat(schedule): mount Location Manager on the Shooting Schedule page"
```

---

## Manual E2E (post-merge, user)

1. On the **Shooting Schedule** page of the real script, click **Manage locations** → group `GARAGE / BACKROOM` + `MOODY BACKROOM` under `VILLA` → confirm the board reflects the regrouping without a manual reload.
2. Rename a location in the manager → confirm it sticks and the board label updates.
3. On the **Script Summary** screen, confirm there is **no** "Manage locations" button and that merging duplicate locations still works.
