# Stripboard Scheduling Status — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface each scene's shooting-day assignment (relative to one active schedule) on the Stripboard tab — with a schedule picker, a Shoot D{n}/Unscheduled pill column, a scheduled/unscheduled filter + stat, and a row flag — reflecting Board/Schedule changes via mount-refetch.

**Architecture:** Frontend-only change to `frontend/src/components/reports/Stripboard.jsx`. On mount it additionally fetches `getSchedules(scriptId)` (picker) and `getShootingDays(activeScheduleId)` (assignments), builds a pure `Map<sceneId,{dayNumber}>` via a new `buildScheduledMap` helper, and each scene row reads its scheduling state from that map. No backend changes; both APIs already exist.

**Tech Stack:** React 18 + Vite (plain JSX, no TypeScript), axios via `apiService.js`, lucide-react icons, Node 20+ for the one framework-free unit check.

## Global Constraints

- Frontend gate: `npm run build` must pass. Do NOT run `npm run lint` — it is broken repo-wide.
- All backend calls go through the single `frontend/src/services/apiService.js` — no new axios instances. (`getSchedules`, `getShootingDays` already exist there.)
- No new backend endpoints; this is frontend-only.
- "Scheduled" is always relative to ONE active schedule (the picker's selection), never "any schedule."
- Shooting day (production) must read distinctly from the existing story-day "Day" column (narrative) — different class, different label ("Shoot").
- Zero-schedule scripts: hide all scheduling surfaces (picker, Shoot column, scheduled filter, stat, row flag) and show a one-line hint linking to the Schedule tab.
- Omitted scenes are excluded from scheduled/unscheduled stat counts (consistent with existing `activeScenes` logic).

---

## Data shapes (verified against the codebase)

- `getSchedules(scriptId)` → `{ schedules: [{ id, name, ... }] }`.
- `getShootingDays(scheduleId)` → `{ days: [{ id, day_number, scenes: [{ scene_id, ... }, ...] }, ...] }`.
- A scene row from `getScenes` has `.id` (the Stripboard already uses `scene.id || scene.scene_id`). `shooting_day_scenes.scene_id` equals that `.id`.
- Board localStorage precedent: `board-state-<scriptId>`. This feature uses key `stripboard-schedule-<scriptId>` to persist the active schedule id.

## File Structure

- Create: `frontend/src/utils/scheduleMap.mjs` — pure `buildScheduledMap(days)`.
- Create: `frontend/scripts/verify-schedule-map.mjs` — framework-free node assertions for the helper.
- Modify: `frontend/src/components/reports/Stripboard.jsx` — state, effects, picker, pill column, filter, stat, row flag, edge cases.
- Modify: `frontend/src/components/reports/Stripboard.css` — pill, column, row-flag, hint styles.

---

## Task 1: `buildScheduledMap` pure helper

**Files:**
- Create: `frontend/src/utils/scheduleMap.mjs`
- Create: `frontend/scripts/verify-schedule-map.mjs`

**Interfaces:**
- Produces: `buildScheduledMap(days: Array) -> Map<sceneId, { dayNumber }>`. Iterates `days[].scenes[]`, mapping each `scene_id` to `{ dayNumber: day.day_number }`. Tolerates `null`/`undefined` `days` and `day.scenes` (returns empty / skips). A scene present under a day maps to that day's number.

- [ ] **Step 1: Write the failing verification script**

Create `frontend/scripts/verify-schedule-map.mjs`:

```javascript
import assert from 'node:assert/strict';
import { buildScheduledMap } from '../src/utils/scheduleMap.mjs';

// scenes assigned across two days
const days = [
  { id: 'd1', day_number: 1, scenes: [{ scene_id: 's1' }, { scene_id: 's2' }] },
  { id: 'd2', day_number: 2, scenes: [{ scene_id: 's3' }] },
];
const map = buildScheduledMap(days);
assert.equal(map.size, 3);
assert.deepEqual(map.get('s1'), { dayNumber: 1 });
assert.deepEqual(map.get('s3'), { dayNumber: 2 });
assert.equal(map.has('s4'), false);

// tolerates missing/empty input
assert.equal(buildScheduledMap(undefined).size, 0);
assert.equal(buildScheduledMap([]).size, 0);
assert.equal(buildScheduledMap([{ day_number: 5 }]).size, 0); // day with no scenes

// skips malformed scene rows
const map2 = buildScheduledMap([{ day_number: 1, scenes: [{ scene_id: 's1' }, {}, null] }]);
assert.equal(map2.size, 1);
assert.deepEqual(map2.get('s1'), { dayNumber: 1 });

console.log('OK: buildScheduledMap');
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && node scripts/verify-schedule-map.mjs`
Expected: FAIL — `Cannot find module .../src/utils/scheduleMap.mjs`.

- [ ] **Step 3: Implement the helper**

Create `frontend/src/utils/scheduleMap.mjs`:

```javascript
// Build a lookup from scene id → { dayNumber } for one schedule's shooting days.
// Pure and dependency-free so it can be verified without a test framework.
export function buildScheduledMap(days) {
  const map = new Map();
  (days || []).forEach((day) => {
    (day?.scenes || []).forEach((ds) => {
      if (ds && ds.scene_id != null) {
        map.set(ds.scene_id, { dayNumber: day.day_number });
      }
    });
  });
  return map;
}
```

- [ ] **Step 4: Run it to verify it passes**

Run: `cd frontend && node scripts/verify-schedule-map.mjs`
Expected: prints `OK: buildScheduledMap`, exit code 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/scheduleMap.mjs frontend/scripts/verify-schedule-map.mjs
git commit -m "feat(stripboard): buildScheduledMap helper (sceneId -> shooting day)"
```

---

## Task 2: Data wiring + schedule picker

**Files:**
- Modify: `frontend/src/components/reports/Stripboard.jsx`

**Interfaces:**
- Consumes: `buildScheduledMap` (Task 1); `getSchedules`, `getShootingDays` from apiService.
- Produces: component state `schedules` (array), `activeScheduleId` (string|null), `scheduledMap` (`Map<sceneId,{dayNumber}>`), `filterScheduled` (`'all'`), and `handleScheduleChange(id)`. Later tasks read `scheduledMap`, `activeScheduleId`, `schedules`. Convention for "does this script have scheduling UI": `schedules.length > 0`.

- [ ] **Step 1: Add imports**

In `Stripboard.jsx`, extend the apiService import and add the helper import:

```javascript
import { getScenes, getScriptMetadata, getScriptItems, getSchedules, getShootingDays } from '../../services/apiService';
import { buildScheduledMap } from '../../utils/scheduleMap';
```

- [ ] **Step 2: Add state**

Near the other `useState` calls (after `expandedRows`):

```javascript
    const [schedules, setSchedules] = useState([]);
    const [activeScheduleId, setActiveScheduleId] = useState(null);
    const [scheduledMap, setScheduledMap] = useState(() => new Map());
    const [filterScheduled, setFilterScheduled] = useState('all');
```

- [ ] **Step 3: Load schedules in the mount effect**

Inside the existing `fetchData` effect (the one that sets scenes/metadata), after metadata is fetched, add a schedules load that restores the persisted active id:

```javascript
                // Load schedules for the scheduling picker + restore persisted choice
                try {
                    const schedRes = await getSchedules(scriptId);
                    const list = schedRes.schedules || [];
                    setSchedules(list);
                    const saved = localStorage.getItem(`stripboard-schedule-${scriptId}`);
                    const initial = (saved && list.some((s) => s.id === saved))
                        ? saved
                        : (list[0]?.id || null);
                    setActiveScheduleId(initial);
                } catch (e) {
                    console.warn('Could not fetch schedules:', e);
                }
```

- [ ] **Step 4: Load shooting days when the active schedule changes**

Add a new effect after the `fetchData` effect:

```javascript
    // Build sceneId → { dayNumber } map for the active schedule
    useEffect(() => {
        if (!activeScheduleId) { setScheduledMap(new Map()); return; }
        let cancelled = false;
        getShootingDays(activeScheduleId)
            .then((data) => { if (!cancelled) setScheduledMap(buildScheduledMap(data.days || [])); })
            .catch((err) => {
                console.warn('Could not fetch shooting days:', err);
                if (!cancelled) setScheduledMap(new Map());
            });
        return () => { cancelled = true; };
    }, [activeScheduleId]);
```

- [ ] **Step 5: Add the change handler**

Add near the other handlers (e.g. after `toggleRowExpand`):

```javascript
    const handleScheduleChange = (id) => {
        const next = id || null;
        setActiveScheduleId(next);
        if (next) localStorage.setItem(`stripboard-schedule-${scriptId}`, next);
    };
```

- [ ] **Step 6: Render the picker in the filter row**

In the `stripboard-filters` div, as the FIRST `filter-group` (before the INT/EXT filter), add:

```javascript
                {schedules.length > 0 && (
                    <div className="filter-group">
                        <select
                            value={activeScheduleId || ''}
                            onChange={(e) => handleScheduleChange(e.target.value)}
                            title="Active shooting schedule"
                        >
                            {schedules.map((s) => (
                                <option key={s.id} value={s.id}>{s.name}</option>
                            ))}
                        </select>
                    </div>
                )}
```

- [ ] **Step 7: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds. (Picker renders for scripts with ≥1 schedule; no visual scheduling data yet — that is Task 3.)

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/reports/Stripboard.jsx
git commit -m "feat(stripboard): fetch schedules + active-schedule picker and scheduledMap"
```

---

## Task 3: Shoot pill column + row flag

**Files:**
- Modify: `frontend/src/components/reports/Stripboard.jsx`
- Modify: `frontend/src/components/reports/Stripboard.css`

**Interfaces:**
- Consumes: `scheduledMap`, `activeScheduleId`, `schedules` (Task 2).
- Produces: a `hasSchedules` boolean and a `fullColSpan` number used by all full-width rows; the Shoot column and `sb-unscheduled` row class relied on visually by later tasks.

- [ ] **Step 1: Derive hasSchedules + fullColSpan**

In `Stripboard.jsx`, just before the `return (` of the component body, add:

```javascript
    const hasSchedules = schedules.length > 0;
    // The table gains one column (Shoot) when scheduling is active.
    const fullColSpan = hasSchedules ? 8 : 7;
```

- [ ] **Step 2: Update all full-width colSpans**

The table currently has three `colSpan="7"` occurrences (story-day separator row, breakdown-row, print-cast-row). Change EACH from the literal `colSpan="7"` to `colSpan={fullColSpan}`:

```javascript
// story-day separator row
                                            <td colSpan={fullColSpan}>
// breakdown expanded row
                                            <td colSpan={fullColSpan}>
// print-only cast row
                                            <td colSpan={fullColSpan}>
```

- [ ] **Step 3: Add the Shoot column header**

In `<thead>`, immediately after the `col-day` header (`<th className="col-day">Day</th>`), add:

```javascript
                            {hasSchedules && <th className="col-shoot">Shoot</th>}
```

- [ ] **Step 4: Add the Shoot pill cell**

In the row body, immediately after the `col-day` `<td>` (the story-day badge cell), add:

```javascript
                                        {hasSchedules && (
                                            <td className="col-shoot">
                                                {activeScheduleId && scheduledMap.has(sceneId) ? (
                                                    <span className="sb-shoot-pill scheduled">
                                                        D{scheduledMap.get(sceneId).dayNumber}
                                                    </span>
                                                ) : (
                                                    <span className="sb-shoot-pill unscheduled">Unscheduled</span>
                                                )}
                                            </td>
                                        )}
```

- [ ] **Step 5: Flag unscheduled rows**

Extend the `<tr className=...>` for `stripboard-row` to append an unscheduled flag. Change the existing className expression to include:

```javascript
                                        className={`stripboard-row ${isInt ? 'int' : 'ext'} ${isDay ? 'day' : 'night'} ${isExpanded ? 'expanded' : ''} status-${analysisStatus} ${scene.is_omitted ? 'omitted' : ''} ${hasSchedules && activeScheduleId && !scene.is_omitted && !scheduledMap.has(sceneId) ? 'sb-unscheduled' : ''}`}
```

- [ ] **Step 6: Add styles**

Append to `frontend/src/components/reports/Stripboard.css`:

```css
/* Shooting-day scheduling status */
.stripboard-table .col-shoot { width: 96px; white-space: nowrap; }
.sb-shoot-pill {
    display: inline-block; padding: 1px 7px; border-radius: 10px;
    font-size: 11px; font-weight: 600; line-height: 1.5;
}
.sb-shoot-pill.scheduled { background: rgba(34, 197, 94, 0.15); color: #16a34a; }
.sb-shoot-pill.unscheduled { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }
.stripboard-row.sb-unscheduled { box-shadow: inset 3px 0 0 rgba(148, 163, 184, 0.55); opacity: 0.82; }
```

- [ ] **Step 7: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/reports/Stripboard.jsx frontend/src/components/reports/Stripboard.css
git commit -m "feat(stripboard): Shoot pill column + unscheduled row flag"
```

---

## Task 4: Scheduled/Unscheduled filter + stat

**Files:**
- Modify: `frontend/src/components/reports/Stripboard.jsx`

**Interfaces:**
- Consumes: `scheduledMap`, `filterScheduled`, `activeScheduleId`, `schedules`, `hasSchedules` (Tasks 2–3).
- Produces: filtered rows honor the scheduled filter; `stats` gains `scheduledCount` and `unscheduledCount`.

- [ ] **Step 1: Apply the scheduled filter**

In the `filteredScenes` `useMemo`, after the existing `filterStoryDay` block and before the sort, add:

```javascript
        if (filterScheduled !== 'all') {
            result = result.filter((s) => {
                const sid = s.id || s.scene_id;
                const isSched = scheduledMap.has(sid);
                return filterScheduled === 'scheduled' ? isSched : !isSched;
            });
        }
```

Add `filterScheduled` and `scheduledMap` to that `useMemo`'s dependency array (append them to the existing deps list).

- [ ] **Step 2: Compute scheduled counts in stats**

In the `stats` `useMemo`, before the `return`, add:

```javascript
        const scheduledCount = activeScenes.filter((s) => scheduledMap.has(s.id || s.scene_id)).length;
        const unscheduledCount = activeScenes.length - scheduledCount;
```

Add `scheduledCount` and `unscheduledCount` to the returned object, and add `scheduledMap` to the `stats` `useMemo` dependency array.

- [ ] **Step 3: Render the filter dropdown**

In the `stripboard-filters` div, after the analysis-status `filter-group`, add:

```javascript
                {hasSchedules && (
                    <div className="filter-group">
                        <select
                            value={filterScheduled}
                            onChange={(e) => setFilterScheduled(e.target.value)}
                            title="Scheduling status"
                        >
                            <option value="all">All Scheduling</option>
                            <option value="scheduled">Scheduled</option>
                            <option value="unscheduled">Unscheduled</option>
                        </select>
                    </div>
                )}
```

- [ ] **Step 4: Render the stat**

In the `stripboard-stats` div, after the Story Days `stat-group` (before the `stat-eighths` group), add:

```javascript
                {hasSchedules && activeScheduleId && (
                    <div className="stat-group">
                        <CalendarDays size={14} />
                        <span className="stat-value">
                            {stats.scheduledCount} scheduled · {stats.unscheduledCount} unscheduled
                        </span>
                    </div>
                )}
```

- [ ] **Step 5: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/reports/Stripboard.jsx
git commit -m "feat(stripboard): scheduled/unscheduled filter + stat"
```

---

## Task 5: Zero-schedule hint + verification

**Files:**
- Modify: `frontend/src/components/reports/Stripboard.jsx`
- Modify: `frontend/src/components/reports/Stripboard.css`

**Interfaces:**
- Consumes: `schedules` (Task 2). No new exports.

- [ ] **Step 1: Add the zero-schedule hint**

In the `stripboard-filters` div, after the sort `filter-group` (the last one), add:

```javascript
                {schedules.length === 0 && (
                    <div className="filter-group sb-no-schedule-hint">
                        <span>No schedule yet — build one on the Schedule tab.</span>
                    </div>
                )}
```

- [ ] **Step 2: Style the hint**

Append to `frontend/src/components/reports/Stripboard.css`:

```css
.sb-no-schedule-hint span {
    font-size: 12px; color: #94a3b8; font-style: italic; white-space: nowrap;
}
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Re-run the helper check (guard against regressions)**

Run: `cd frontend && node scripts/verify-schedule-map.mjs`
Expected: prints `OK: buildScheduledMap`.

- [ ] **Step 5: Manual verification (documented; run if a dev server is available)**

1. Open a script that has a schedule with some scenes assigned and some not. On the **Stripboard** tab: the picker shows the schedule; assigned rows show a green `D{n}` pill, others show a muted `Unscheduled` pill and a left-accent/dim.
2. The stats bar shows `X scheduled · Y unscheduled`; the counts exclude omitted scenes.
3. Set the scheduling filter to **Unscheduled** → only unscheduled rows remain; **Scheduled** → only assigned rows.
4. If the script has 2+ schedules, switch the picker → pills and counts update without a full page reload; reload the page → the picker keeps the chosen schedule (localStorage).
5. Assign a scene to a day on the **Board/Schedule**, then navigate to the **Stripboard** → that scene now reads Scheduled (change reflected).
6. Open a script with **zero schedules** → no picker/Shoot column/filter/stat; the hint "No schedule yet — build one on the Schedule tab." shows; the rest of the table is normal.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/reports/Stripboard.jsx frontend/src/components/reports/Stripboard.css
git commit -m "feat(stripboard): zero-schedule hint + verification"
```

---

## Self-Review Notes

- **Spec coverage:** §1 data & sync → Task 2 (fetch + map + localStorage; mount-refetch is inherent to the route remount, no code needed). §2 surfaces: picker → Task 2; Shoot pill column → Task 3; scheduled filter + stat → Task 4; row flag → Task 3. §3 edge cases: zero schedules → Tasks 2–4 guards + Task 5 hint; omitted excluded from counts → Task 4 (uses `activeScenes`); deleted day/removed assignment → naturally Unscheduled (map absence); persisted id no longer valid → Task 2 Step 3 `list.some(...)` fallback; fetch failure → Task 2 Step 4 catch → empty map. §Testing → Task 1 node check + Task 5 manual.
- **colSpan trap:** the table has exactly three `colSpan="7"` today; Task 3 Step 2 converts all three to `fullColSpan` so adding the Shoot column never misaligns full-width rows. This is the one easy-to-miss correctness detail.
- **Naming:** shooting-day pill uses `.sb-shoot-pill` / label "Shoot", kept distinct from the narrative story-day `.sb-day-badge` / "Day" column per the Global Constraints.
- **No test runner:** the repo has no vitest/jest; the pure helper is verified via `node scripts/verify-schedule-map.mjs`, UI via `npm run build` + manual — matching the established frontend convention.
