# Move Location Manager to the Board — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mount the Location Manager on the Board (`ZoomableStripboard` via `BoardToolbar`) and remove it from the Shooting Schedule page.

**Architecture:** Three-file frontend change. `BoardToolbar.jsx` gains a "Manage locations" button (new `onManageLocations` prop). `ZoomableStripboard.jsx` adds the modal state, passes the prop, and mounts `LocationManager` wired to its existing `state.scenes` + `refreshBoard`. `ShootingSchedulePage.jsx` reverts the mount added in commit `f61c8dd`. The `LocationManager` component and all backend endpoints are unchanged.

**Tech Stack:** React 18 (plain JSX), Vite, `lucide-react`, existing board reducer + `refreshBoard`.

## Global Constraints

- **Frontend only.** No change to `LocationManager.jsx`/`.css`, `apiService.js`, any backend route, or the DB.
- **Board only.** Location management lives on the Board after this change, not on the Schedule page.
- **Reuse the board's data:** mount `LocationManager` with `scenes={state.scenes}` and `onChanged={refreshBoard}` — do NOT add a separate scenes fetch to the board (it already loads scenes).
- **Gate on `npm run build`** from `frontend/` (repo lint known-broken).
- Button label wording: `Manage locations` (with `MapPin` icon).

---

### Task 1: Remove Location Manager from the Shooting Schedule page (`ShootingSchedulePage.jsx`)

Reverts commit `f61c8dd`. This is Task 1 so the manager is never mounted in two places at once during implementation.

**Files:**
- Modify: `frontend/src/components/schedule/ShootingSchedulePage.jsx`

**Interfaces:**
- Produces: `ShootingSchedulePage` no longer references `LocationManager`, `getScenes`, `MapPin`, `scenes`, `showLocationManager`, or `refreshLocationsAndBoard`. `refreshDays` and everything else remain.

- [ ] **Step 1: Revert the imports**

Line 3 — remove `, MapPin` from the `lucide-react` import:
```javascript
import { Plus, CalendarDays, Trash2, Pencil, Check, X, ZoomIn, ZoomOut, Maximize, RotateCcw, Printer } from 'lucide-react';
```

Lines 9–12 — remove `, getScenes` from the `apiService` import:
```javascript
import {
    getSchedules, createSchedule, getShootingDays,
    getScriptMetadata, deleteSchedule, updateSchedule,
} from '../../services/apiService';
```

Line 14 — delete the `LocationManager` import entirely:
```javascript
import LocationManager from '../scenes/LocationManager';
```

- [ ] **Step 2: Remove the state (lines 32–33)**

Delete:
```javascript
    const [scenes, setScenes] = useState([]);
    const [showLocationManager, setShowLocationManager] = useState(false);
```

- [ ] **Step 3: Restore the initial-load `Promise.all` (lines 47–55)**

Replace:
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
                setMetadata(metaData);
```
with:
```javascript
                const [schedData, metaData] = await Promise.all([
                    getSchedules(scriptId),
                    getScriptMetadata(scriptId),
                ]);
                setMetadata(metaData);
```

- [ ] **Step 4: Remove the `refreshLocationsAndBoard` callback (lines 98–107)**

Delete the whole block:
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
(Leave the preceding `}, [activeScheduleId]);` and following code intact.)

- [ ] **Step 5: Remove the toolbar button (lines 203–212)**

Delete the button so `schedule-header-right` opens directly with the Print block:
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
Result: `<div className="schedule-header-right">` is immediately followed by `{/* Print / Export button */}`.

- [ ] **Step 6: Remove the modal mount (lines 302–310)**

Delete:
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

- [ ] **Step 8: Verify removal is clean**

Run: `grep -nE "LocationManager|showLocationManager|Manage locations|refreshLocationsAndBoard|getScenes|MapPin" frontend/src/components/schedule/ShootingSchedulePage.jsx`
Expected: no output.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/schedule/ShootingSchedulePage.jsx
git commit -m "refactor(schedule): remove Location Manager from Shooting Schedule page"
```

---

### Task 2: Add Location Manager to the Board (`BoardToolbar.jsx` + `ZoomableStripboard.jsx`)

**Files:**
- Modify: `frontend/src/components/board/BoardToolbar.jsx`
- Modify: `frontend/src/components/board/ZoomableStripboard.jsx`

**Interfaces:**
- `BoardToolbar` gains a new prop `onManageLocations: () => void`.
- `ZoomableStripboard` owns `showLocationManager` state and mounts `LocationManager` with `scenes={state.scenes}`, `onChanged={refreshBoard}`.

- [ ] **Step 1: `BoardToolbar` — import MapPin**

Line 2 — add `MapPin` to the `lucide-react` import:
```javascript
import { ZoomIn, ZoomOut, Maximize, RotateCcw, Filter, Layers, MousePointer2, Hand, Move, BoxSelect, CalendarPlus, X, MapPin } from 'lucide-react';
```

- [ ] **Step 2: `BoardToolbar` — accept the prop**

Line 7 — add `onManageLocations` to the destructured props:
```javascript
const BoardToolbar = ({ groupBy, filters, uniqueDays, uniqueCharacters, totalVisible, totalScenes, zoomApiRef, dispatch, toolMode, selectedCount, scriptId, selectedSceneIds, onScheduled, onManageLocations }) => {
```

- [ ] **Step 3: `BoardToolbar` — add the button in the Group By section**

In the center section, after the Group By `pill-group` `</div>` and before the closing `</div>` of `.toolbar-group-by` (i.e. right after the `.map(...)` block that renders the three group-by pills, currently ending near line 114), add the button as a sibling of `.pill-group` inside `.toolbar-group-by`:
```jsx
                    <button
                        className="pill-btn"
                        onClick={onManageLocations}
                        title="Group and rename locations"
                    >
                        <MapPin size={14} /> Manage locations
                    </button>
```
So `.toolbar-group-by` contains: the `Layers` icon, the `.pill-group`, then this button.

- [ ] **Step 4: `ZoomableStripboard` — imports**

Line 1 — add `useState`:
```javascript
import React, { useReducer, useEffect, useMemo, useRef, useCallback, useState } from 'react';
```

After the `BoardCanvas` import (line 11), add:
```javascript
import LocationManager from '../scenes/LocationManager';
```

- [ ] **Step 5: `ZoomableStripboard` — state**

Near the other hooks (after `const [state, dispatch] = useReducer(...)`, ~line 24), add:
```javascript
    const [showLocationManager, setShowLocationManager] = useState(false);
```

- [ ] **Step 6: `ZoomableStripboard` — pass the prop to `BoardToolbar`**

In the `<BoardToolbar … />` usage (ends ~line 195 with `onScheduled={handleScheduled}`), add a prop:
```jsx
                onScheduled={handleScheduled}
                onManageLocations={() => setShowLocationManager(true)}
```

- [ ] **Step 7: `ZoomableStripboard` — mount the modal**

After the `{state.activeStrip && (<StripDetailDrawer … />)}` block, add:
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
`state.scenes` and `refreshBoard` already exist in this component.

- [ ] **Step 8: Verify the build passes**

Run: `cd frontend && npm run build`
Expected: build completes with no errors.

- [ ] **Step 9: Verify wiring is present**

Run: `grep -nE "onManageLocations|Manage locations|LocationManager|MapPin" frontend/src/components/board/BoardToolbar.jsx frontend/src/components/board/ZoomableStripboard.jsx`
Expected: `BoardToolbar` shows `MapPin`, `onManageLocations` (prop + onClick), `Manage locations`; `ZoomableStripboard` shows the `LocationManager` import + mount and `onManageLocations={…}`.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/board/BoardToolbar.jsx frontend/src/components/board/ZoomableStripboard.jsx
git commit -m "feat(board): mount Location Manager on the Board toolbar"
```

---

## Manual E2E (post-merge, user)

1. On the **Board**, switch **Group By → Location**, click **Manage locations** → group `GARAGE / BACKROOM` + `MOODY BACKROOM` under `VILLA` → confirm the Location lanes reshape immediately.
2. Rename a location in the manager → confirm it sticks and the lanes/labels update.
3. On the **Shooting Schedule** page, confirm there is **no** "Manage locations" button.
