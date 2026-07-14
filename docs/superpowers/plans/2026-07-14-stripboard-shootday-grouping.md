# Stripboard Shoot-Day Grouping & Segmented Header — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a shooting schedule is active, reorder the Stripboard into shoot-day blocks (header + "End of Day N · X pgs" footer + trailing Unscheduled bin), and replace the flat stats strip with a segmented header card.

**Architecture:** Frontend only. A new pure helper `buildShootDayBlocks(days, scenesById)` groups full scene objects by shooting day; `Stripboard.jsx` stores the raw shooting-days payload, derives blocks in a memo (join + per-block page totals), and renders a grouped table body when a schedule is active — otherwise the existing flat scene-order + story-day-separator body is preserved verbatim. The per-row Shoot column is retired; the block structure carries scheduling status.

**Tech Stack:** React 18 (plain JSX), Vite, lucide-react. No test framework — pure helpers verified via `node scripts/verify-schedule-map.mjs` (node:assert); UI gated on `npm run build`.

## Global Constraints

- Frontend gate is `npm run build` (from `frontend/`). **Do NOT run `npm run lint`** — it is broken repo-wide.
- Pure helper gate: `node scripts/verify-schedule-map.mjs` (from `frontend/`) must print its OK lines.
- No backend or API changes. Reuse `getScenes`, `getSchedules`, `getShootingDays` exactly as they exist.
- Eighths math uses the existing `getSceneEighths(scene)` and `formatEighths(eighths)` from `src/utils/sceneUtils.js`. Do not reimplement. Note: `formatEighths(0)` returns `'1/8'` — guard zero totals explicitly.
- "Active scene" = `!scene.is_omitted`. Omitted scenes are excluded from page totals and the `· N scenes` count, but their row still renders inside its block.
- Scene id key is `scene.id || scene.scene_id` (used consistently across the file).
- Grouped mode is active exactly when `hasSchedules && !!activeScheduleId`. The no-schedule fallback path must remain byte-for-behaviour identical to today.

---

### Task 1: `buildShootDayBlocks` pure helper + node verification

**Files:**
- Modify: `frontend/src/utils/scheduleMap.mjs` (append new export; leave `buildScheduledMap` untouched)
- Test: `frontend/scripts/verify-schedule-map.mjs` (append cases + import)

**Interfaces:**
- Produces: `buildShootDayBlocks(days, scenesById) -> Array<{ dayNumber?: number, unscheduled?: true, scenes: object[] }>`
  - `days`: `getShootingDays().days` shape — `[{ id, day_number, scenes: [{ scene_id }] }]` (may be `undefined`/`[]`).
  - `scenesById`: `Map<sceneId, fullScene>` (insertion order = board natural order).
  - Returns one block per day in `day_number` input order (scenes resolved via `scenesById`, unresolved `scene_id`s skipped, day order preserved), followed by a single `{ unscheduled: true, scenes }` block of every scene in `scenesById` not assigned to any day — emitted only if non-empty.

- [ ] **Step 1: Write the failing test** — append to `frontend/scripts/verify-schedule-map.mjs`

```javascript
import { buildShootDayBlocks } from '../src/utils/scheduleMap.mjs';

// Full scene objects keyed by id (insertion order preserved by Map)
const sById = new Map([
  ['s1', { id: 's1', scene_number: '1' }],
  ['s2', { id: 's2', scene_number: '2' }],
  ['s3', { id: 's3', scene_number: '3' }],
  ['s4', { id: 's4', scene_number: '4' }], // never assigned → unscheduled
]);
const blkDays = [
  { id: 'd1', day_number: 1, scenes: [{ scene_id: 's2' }, { scene_id: 's1' }] }, // note order s2,s1
  { id: 'd2', day_number: 2, scenes: [{ scene_id: 's3' }, { scene_id: 's99' }] }, // s99 stale
];
const blocks = buildShootDayBlocks(blkDays, sById);
// two day blocks + one unscheduled block
assert.equal(blocks.length, 3);
assert.equal(blocks[0].dayNumber, 1);
assert.deepEqual(blocks[0].scenes.map((s) => s.id), ['s2', 's1']); // schedule order preserved
assert.equal(blocks[1].dayNumber, 2);
assert.deepEqual(blocks[1].scenes.map((s) => s.id), ['s3']); // stale s99 skipped
assert.equal(blocks[2].unscheduled, true);
assert.deepEqual(blocks[2].scenes.map((s) => s.id), ['s4']);

// no unscheduled scenes → no unscheduled block
const sAll = new Map([['s1', { id: 's1' }]]);
const blocksNoBin = buildShootDayBlocks(
  [{ day_number: 1, scenes: [{ scene_id: 's1' }] }],
  sAll,
);
assert.equal(blocksNoBin.length, 1);
assert.equal(blocksNoBin[0].unscheduled, undefined);

// empty/undefined days → single unscheduled block with all scenes
const blocksNoDays = buildShootDayBlocks(undefined, sAll);
assert.equal(blocksNoDays.length, 1);
assert.equal(blocksNoDays[0].unscheduled, true);
assert.deepEqual(blocksNoDays[0].scenes.map((s) => s.id), ['s1']);

// empty scenesById → no blocks at all
assert.equal(buildShootDayBlocks(blkDays, new Map()).length, 0);

console.log('OK: buildShootDayBlocks');
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && node scripts/verify-schedule-map.mjs`
Expected: FAIL — `SyntaxError` / `does not provide an export named 'buildShootDayBlocks'`.

- [ ] **Step 3: Implement the helper** — append to `frontend/src/utils/scheduleMap.mjs`

```javascript

// Group full scene objects into shoot-day blocks for one schedule.
// `days` is getShootingDays().days; `scenesById` is Map<sceneId, fullScene>.
// Returns day blocks in input order (scenes resolved + schedule-order-preserved,
// unresolved ids skipped) followed by a single trailing unscheduled bin of every
// scene not assigned to any day — emitted only when non-empty. Pure, no React.
export function buildShootDayBlocks(days, scenesById) {
  const blocks = [];
  const scheduledIds = new Set();
  (days || []).forEach((day) => {
    const scenes = [];
    (day?.scenes || []).forEach((ds) => {
      const sid = ds && ds.scene_id;
      if (sid == null) return;
      const full = scenesById.get(sid);
      if (!full) return; // stale assignment — scene no longer exists
      scenes.push(full);
      scheduledIds.add(sid);
    });
    blocks.push({ dayNumber: day.day_number, scenes });
  });
  const unscheduled = [];
  scenesById.forEach((scene, sid) => {
    if (!scheduledIds.has(sid)) unscheduled.push(scene);
  });
  if (unscheduled.length > 0) {
    blocks.push({ unscheduled: true, scenes: unscheduled });
  }
  return blocks;
}
```

- [ ] **Step 4: Run the verify script to confirm it passes**

Run: `cd frontend && node scripts/verify-schedule-map.mjs`
Expected: PASS — prints both `OK: buildScheduledMap` and `OK: buildShootDayBlocks`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/scheduleMap.mjs frontend/scripts/verify-schedule-map.mjs
git commit -m "feat(stripboard): add buildShootDayBlocks pure helper + node verify"
```

---

### Task 2: Grouped shoot-day rendering in Stripboard

**Files:**
- Modify: `frontend/src/components/reports/Stripboard.jsx`
- Modify: `frontend/src/components/reports/Stripboard.css`

**Interfaces:**
- Consumes: `buildShootDayBlocks` (Task 1); existing `getShootingDays`, `getSceneEighths`, `formatEighths`, `scheduledMap`.
- Produces: no exports; internal `grouped` flag, `scenesById` memo, `shootingDays` state, `shootDayBlocks` memo, and a `renderSceneRow(scene)` helper shared by both render paths.

This task retires the per-row Shoot column entirely (it only ever appeared when a schedule was active, which is now always the grouped path where the block header carries the day). `fullColSpan` becomes the constant `7`.

- [ ] **Step 1: Add `shootingDays` state**

In `Stripboard.jsx`, next to the other scheduling state (after line ~41 `const [filterScheduled, setFilterScheduled] = useState('all');`), add:

```javascript
    const [shootingDays, setShootingDays] = useState([]);
```

- [ ] **Step 2: Store the raw days in the shooting-days effect**

Replace the effect that builds `scheduledMap` (currently lines ~139-149) with a version that also stores the raw `days`:

```javascript
    // Build sceneId → { dayNumber } map + retain raw days for shoot-day grouping
    useEffect(() => {
        if (!activeScheduleId) { setScheduledMap(new Map()); setShootingDays([]); return; }
        let cancelled = false;
        getShootingDays(activeScheduleId)
            .then((data) => {
                if (cancelled) return;
                const days = data.days || [];
                setScheduledMap(buildScheduledMap(days));
                setShootingDays(days);
            })
            .catch((err) => {
                console.warn('Could not fetch shooting days:', err);
                if (!cancelled) { setScheduledMap(new Map()); setShootingDays([]); }
            });
        return () => { cancelled = true; };
    }, [activeScheduleId]);
```

- [ ] **Step 3: Import the helper**

Update the import on line 16:

```javascript
import { buildScheduledMap, buildShootDayBlocks } from '../../utils/scheduleMap';
```

- [ ] **Step 4: Add `grouped` flag, `scenesById`, a shared filter predicate, and refactor `filteredScenes` to use it**

Add a `passesFilters` callback and a `scenesById` memo. Place `scenesById` right after the `activeScenes` memo (~line 255), and `passesFilters` above `filteredScenes` (~line 196). Then rewrite the filter block inside `filteredScenes` to call `passesFilters` (keeps the sort untouched):

```javascript
    // Shared per-scene filter predicate (used by flat list and grouped blocks)
    const passesFilters = useCallback((s) => {
        if (filterIntExt !== 'all' && s.int_ext !== filterIntExt) return false;
        if (filterTimeOfDay !== 'all' && s.time_of_day !== filterTimeOfDay) return false;
        if (filterAnalysisStatus !== 'all' && getSceneAnalysisStatus(s) !== filterAnalysisStatus) return false;
        if (filterStoryDay !== 'all' && s.story_day !== parseInt(filterStoryDay)) return false;
        if (filterScheduled !== 'all') {
            const isSched = scheduledMap.has(s.id || s.scene_id);
            if (filterScheduled === 'scheduled' ? !isSched : isSched) return false;
        }
        return true;
    }, [filterIntExt, filterTimeOfDay, filterAnalysisStatus, filterStoryDay, filterScheduled, scheduledMap]);
```

Rewrite `filteredScenes` (lines ~197-252) so its filtering delegates to `passesFilters` (sort logic unchanged):

```javascript
    const filteredScenes = useMemo(() => {
        let result = scenes.filter(passesFilters);
        result.sort((a, b) => {
            let aVal, bVal;
            switch (sortBy) {
                case 'scene_number':
                    aVal = parseInt(a.scene_number) || 0;
                    bVal = parseInt(b.scene_number) || 0;
                    break;
                case 'setting':
                    aVal = a.setting || '';
                    bVal = b.setting || '';
                    break;
                case 'characters':
                    aVal = (a.characters || []).length;
                    bVal = (b.characters || []).length;
                    break;
                default:
                    aVal = a.scene_order || 0;
                    bVal = b.scene_order || 0;
            }
            if (typeof aVal === 'string') {
                return sortDir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            }
            return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
        });
        return result;
    }, [scenes, passesFilters, sortBy, sortDir]);
```

Add `scenesById` after `activeScenes` (~line 255):

```javascript
    // sceneId → full scene (insertion order = board natural order)
    const scenesById = useMemo(() => {
        const m = new Map();
        scenes.forEach((s) => m.set(s.id || s.scene_id, s));
        return m;
    }, [scenes]);
```

- [ ] **Step 5: Add the `shootDayBlocks` memo**

After `scenesById`, add. Each block carries filtered visible scenes, a non-omitted count, and a page-total; blocks with no visible scenes are dropped:

```javascript
    // Shoot-day blocks (only meaningful when a schedule is active)
    const shootDayBlocks = useMemo(() => {
        return buildShootDayBlocks(shootingDays, scenesById)
            .map((b) => {
                const visible = b.scenes.filter(passesFilters);
                const active = visible.filter((s) => !s.is_omitted);
                const eighths = active.reduce((sum, s) => sum + getSceneEighths(s), 0);
                return { ...b, scenes: visible, sceneCount: active.length, eighths };
            })
            .filter((b) => b.scenes.length > 0);
    }, [shootingDays, scenesById, passesFilters]);
```

- [ ] **Step 6: Define `grouped` and fix `fullColSpan`**

Replace the `hasSchedules` / `fullColSpan` lines (~344-346) with:

```javascript
    const hasSchedules = schedules.length > 0;
    const grouped = hasSchedules && !!activeScheduleId;
    // Shoot column retired — block headers carry the shooting day. Constant 7.
    const fullColSpan = 7;
```

- [ ] **Step 7: Extract `renderSceneRow(scene)` from the existing row markup**

Inside the component body (before the `return`), add a `renderSceneRow` arrow that returns the `React.Fragment` currently produced inside `filteredScenes.map` — **minus** the story-day separator and **minus** the `col-shoot` `<td>`, and with the row-level `sb-unscheduled` class removed (the Unscheduled bin now carries that meaning). Copy the existing body verbatim except those three removals. The key changes vs. today's inline block:

- signature: `const renderSceneRow = (scene) => { ... }` (no `index`; no separator).
- the row `className` drops the `${hasSchedules && activeScheduleId && !scene.is_omitted && !scheduledMap.has(sceneId) ? 'sb-unscheduled' : ''}` segment.
- delete the entire `{hasSchedules && (<td className="col-shoot">...</td>)}` cell.
- keep the expanded breakdown row and the print-cast row exactly as-is.

```javascript
    const renderSceneRow = (scene) => {
        const sceneId = scene.id || scene.scene_id;
        const sceneUserItems = userItemsByScene[sceneId] || {};
        const chars = [...(scene.characters || []), ...(sceneUserItems.characters || [])];
        const charDisplay = chars.slice(0, 3).join(', ');
        const moreChars = chars.length > 3 ? ` +${chars.length - 3}` : '';
        const eighthsDisplay = getSceneEighthsDisplay(scene);
        const isInt = scene.int_ext === 'INT';
        const isDay = scene.time_of_day === 'DAY';
        const isExpanded = expandedRows.has(sceneId);
        const fullCast = chars.join(', ');
        const props = [...(scene.props || []), ...(sceneUserItems.props || [])];
        const wardrobe = [...(scene.wardrobe || []), ...(sceneUserItems.wardrobe || [])];
        const vehicles = [...(scene.vehicles || []), ...(sceneUserItems.vehicles || [])];
        const specialFx = [...(scene.special_fx || []), ...(sceneUserItems.special_fx || [])];
        const sound = [...(scene.sound || []), ...(sceneUserItems.sound || [])];
        const atmosphere = scene.atmosphere || '';
        const analysisStatus = getSceneAnalysisStatus(scene);
        const notes = getSceneNotes(scene);
        const notesByDept = getNotesByDepartment(notes);
        const timelineClass = (scene.timeline_code || 'PRESENT').toLowerCase();

        return (
            <React.Fragment key={sceneId}>
                <tr
                    className={`stripboard-row ${isInt ? 'int' : 'ext'} ${isDay ? 'day' : 'night'} ${isExpanded ? 'expanded' : ''} status-${analysisStatus} ${scene.is_omitted ? 'omitted' : ''}`}
                    onClick={() => toggleRowExpand(sceneId)}
                    style={{ cursor: 'pointer' }}
                >
                    <td className="col-scene" style={{ display: 'table-cell' }}>
                        <span className="scene-num">{scene.scene_number}</span>
                        <span className={`status-icon status-${analysisStatus}`} title={
                            analysisStatus === 'analyzed' ? 'Analyzed' :
                            analysisStatus === 'incomplete' ? 'Incomplete - needs more breakdown' :
                            'Pending analysis'
                        }>
                            {analysisStatus === 'analyzed' && <CheckCircle size={12} />}
                            {analysisStatus === 'incomplete' && <AlertCircle size={12} />}
                            {analysisStatus === 'pending' && <Clock size={12} />}
                        </span>
                    </td>
                    <td className="col-ie">
                        <span className={`ie-badge ${isInt ? 'int' : 'ext'}`}>{scene.int_ext}</span>
                    </td>
                    <td className="col-setting">
                        <span className="setting-text">{scene.setting}</span>
                    </td>
                    <td className="col-time">
                        <span className={`time-badge ${isDay ? 'day' : 'night'}`}>{scene.time_of_day}</span>
                    </td>
                    <td className="col-day">
                        {scene.story_day && (
                            <span className={`sb-day-badge timeline-${timelineClass}`}>D{scene.story_day}</span>
                        )}
                    </td>
                    <td className="col-cast">
                        <span className="cast-text">{charDisplay}{moreChars}</span>
                        {chars.length > 0 && <span className="cast-count">({chars.length})</span>}
                    </td>
                    <td className="col-pages">
                        <span className="eighths-num">{eighthsDisplay}</span>
                    </td>
                </tr>
                {isExpanded && (
                    <tr className="breakdown-row">
                        <td colSpan={fullColSpan}>
                            <div className="breakdown-content">
                                <div className="breakdown-grid">
                                    {[
                                        { icon: <Users size={14} />, label: 'Cast', items: chars, dept: 'cast' },
                                        { icon: <Package size={14} />, label: 'Props', items: props, dept: 'props' },
                                        { icon: <Shirt size={14} />, label: 'Wardrobe', items: wardrobe, dept: 'wardrobe' },
                                        { icon: <Car size={14} />, label: 'Vehicles', items: vehicles, dept: 'vehicles' },
                                        { icon: <Sparkles size={14} />, label: 'Special FX', items: specialFx, dept: 'special_fx' },
                                        { icon: <Volume2 size={14} />, label: 'Sound', items: sound, dept: 'sound' },
                                    ].map((card) => (
                                        <div className="breakdown-card" key={card.label}>
                                            <div className="breakdown-card-header">
                                                {card.icon}
                                                <span>{card.label} ({card.items.length})</span>
                                                {notesByDept[card.dept] > 0 && (
                                                    <span className="note-indicator">
                                                        <MessageSquare size={10} />
                                                        {notesByDept[card.dept]}
                                                    </span>
                                                )}
                                            </div>
                                            <div className="breakdown-card-body">
                                                {card.items.length > 0 ? (
                                                    <ul className="breakdown-list">
                                                        {card.items.map((it, i) => <li key={i}>{it}</li>)}
                                                    </ul>
                                                ) : (
                                                    <span className="breakdown-empty">None</span>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                {atmosphere && (
                                    <div className="breakdown-atmosphere">
                                        <Cloud size={14} />
                                        <span className="atmosphere-label">Atmosphere:</span>
                                        <span className="atmosphere-text">{atmosphere}</span>
                                    </div>
                                )}
                            </div>
                        </td>
                    </tr>
                )}
                {chars.length > 0 && (
                    <tr className="print-cast-row">
                        <td colSpan={fullColSpan}>
                            <span className="print-cast-label">Cast: </span>
                            <span className="print-cast-list">{fullCast}</span>
                        </td>
                    </tr>
                )}
            </React.Fragment>
        );
    };
```

Note: this collapses the six repeated breakdown-card blocks into a small array `.map` (DRY) — behaviour identical to the current six hand-written cards. Verify the six categories and their note-department keys match the originals (`cast`, `props`, `wardrobe`, `vehicles`, `special_fx`, `sound`).

- [ ] **Step 8: Replace the `<thead>` and `<tbody>` with mode-aware rendering**

Remove the `col-shoot` `<th>` (line ~577). Guard the sortable header `onClick`s so they are inert while grouped (add `!grouped &&`). Then split the body: grouped → blocks; else → existing flat map calling `renderSceneRow`.

Header — replace the three sortable `<th>` onClicks and drop col-shoot:

```jsx
                        <tr>
                            <th className={`col-scene${grouped ? ' sort-disabled' : ''}`} onClick={() => !grouped && toggleSort('scene_number')}>
                                #
                                {!grouped && sortBy === 'scene_number' && (
                                    sortDir === 'asc' ? <SortAsc size={12} /> : <SortDesc size={12} />
                                )}
                            </th>
                            <th className="col-ie">I/E</th>
                            <th className={`col-setting${grouped ? ' sort-disabled' : ''}`} onClick={() => !grouped && toggleSort('setting')}>
                                Setting
                                {!grouped && sortBy === 'setting' && (
                                    sortDir === 'asc' ? <SortAsc size={12} /> : <SortDesc size={12} />
                                )}
                            </th>
                            <th className="col-time">D/N</th>
                            <th className="col-day">Day</th>
                            <th className={`col-cast${grouped ? ' sort-disabled' : ''}`} onClick={() => !grouped && toggleSort('characters')}>
                                Cast
                                {!grouped && sortBy === 'characters' && (
                                    sortDir === 'asc' ? <SortAsc size={12} /> : <SortDesc size={12} />
                                )}
                            </th>
                            <th className="col-pages">pg</th>
                        </tr>
```

Body — replace the entire `<tbody>{filteredScenes.map(...)}</tbody>` (lines ~587-884) with:

```jsx
                    <tbody>
                        {grouped
                            ? shootDayBlocks.map((block) => {
                                const key = block.unscheduled ? 'unscheduled' : `day-${block.dayNumber}`;
                                const title = block.unscheduled ? 'Unscheduled' : `Shoot Day ${block.dayNumber}`;
                                const totalLabel = block.eighths > 0 ? formatEighths(block.eighths) : '0';
                                const footLabel = block.unscheduled ? 'Unscheduled' : `End of Day ${block.dayNumber}`;
                                return (
                                    <React.Fragment key={key}>
                                        <tr className={`sb-block-header-row${block.unscheduled ? ' unscheduled' : ''}`}>
                                            <td colSpan={fullColSpan}>
                                                <div className="sb-block-header">
                                                    <CalendarDays size={13} />
                                                    <span className="sb-block-title">{title}</span>
                                                    <span className="sb-block-count">· {block.sceneCount} scene{block.sceneCount === 1 ? '' : 's'}</span>
                                                </div>
                                            </td>
                                        </tr>
                                        {block.scenes.map((scene) => renderSceneRow(scene))}
                                        <tr className={`sb-block-footer-row${block.unscheduled ? ' unscheduled' : ''}`}>
                                            <td colSpan={fullColSpan}>
                                                <div className="sb-block-footer">
                                                    <span className="sb-block-foot-label">{footLabel}</span>
                                                    <span className="sb-block-foot-pages">· {totalLabel} pgs</span>
                                                </div>
                                            </td>
                                        </tr>
                                    </React.Fragment>
                                );
                            })
                            : filteredScenes.map((scene, index) => {
                                const prevScene = index > 0 ? filteredScenes[index - 1] : null;
                                const showDaySeparator = scene.story_day && (
                                    !prevScene || prevScene.story_day !== scene.story_day
                                );
                                const timelineClass = (scene.timeline_code || 'PRESENT').toLowerCase();
                                return (
                                    <React.Fragment key={scene.id || scene.scene_id}>
                                        {showDaySeparator && (
                                            <tr className="sb-day-separator-row">
                                                <td colSpan={fullColSpan}>
                                                    <div className={`sb-day-separator timeline-${timelineClass}`}>
                                                        <div className="sb-day-separator-line"></div>
                                                        <span className={`sb-day-separator-label timeline-${timelineClass}`}>
                                                            <CalendarDays size={11} />
                                                            {scene.story_day_label || `Day ${scene.story_day}`}
                                                        </span>
                                                        <div className="sb-day-separator-line"></div>
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                        {renderSceneRow(scene)}
                                    </React.Fragment>
                                );
                            })}
                    </tbody>
```

Note the flat path wraps `renderSceneRow` in an outer `React.Fragment` keyed for the separator; `renderSceneRow` already returns a keyed fragment, so the outer wrapper needs its own `key` (used here). React tolerates the nested keyed fragment.

- [ ] **Step 9: Disable the sort control while grouped**

In the sort `filter-group` (~lines 533-549), disable the `<select>` and direction button when grouped, and add a tooltip:

```jsx
                <div className="filter-group" title={grouped ? 'Sorted by shooting schedule' : undefined}>
                    <select
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value)}
                        disabled={grouped}
                    >
                        <option value="scene_order">Scene Order</option>
                        <option value="scene_number">Scene Number</option>
                        <option value="setting">Location</option>
                        <option value="characters">Cast Size</option>
                    </select>
                    <button
                        className="sort-dir-btn"
                        onClick={() => setSortDir(sortDir === 'asc' ? 'desc' : 'asc')}
                        disabled={grouped}
                    >
                        {sortDir === 'asc' ? <SortAsc size={14} /> : <SortDesc size={14} />}
                    </button>
                </div>
```

- [ ] **Step 10: Block header/footer CSS + remove dead `.sb-unscheduled` row rule**

In `Stripboard.css`, append the block styles and delete the now-unused `.stripboard-row.sb-unscheduled` rule (the row-level flag is gone; the `.col-shoot`/`.sb-shoot-pill` rules may remain harmlessly but delete them too if present since the column is retired):

```css
/* Shoot-day block header / footer */
.sb-block-header-row td,
.sb-block-footer-row td {
    padding: 0;
}
.sb-block-header {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.5rem 0.75rem;
    margin-top: 0.75rem;
    background: var(--bg-elevated, rgba(255, 255, 255, 0.03));
    border-left: 3px solid var(--accent, #10b981);
    border-radius: 6px 6px 0 0;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    color: var(--text-primary);
}
.sb-block-header .sb-block-count {
    font-weight: 500;
    text-transform: none;
    letter-spacing: 0;
    color: var(--text-secondary);
}
.sb-block-footer {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 0.4rem;
    padding: 0.45rem 0.75rem;
    margin-bottom: 0.35rem;
    border-left: 3px solid var(--accent, #10b981);
    border-top: 1px dashed var(--border-color);
    border-radius: 0 0 6px 6px;
    font-size: 0.8rem;
    color: var(--text-secondary);
}
.sb-block-footer .sb-block-foot-pages {
    font-weight: 700;
    color: var(--text-primary);
}
/* Unscheduled bin uses a muted accent to read as "not yet placed" */
.sb-block-header-row.unscheduled .sb-block-header,
.sb-block-footer-row.unscheduled .sb-block-footer {
    border-left-color: var(--text-tertiary, #6b7280);
}
.stripboard-table th.sort-disabled {
    cursor: default;
}
```

- [ ] **Step 11: Build**

Run: `cd frontend && npm run build`
Expected: `✓ built in …` with no errors.

- [ ] **Step 12: Verify pure helper still green**

Run: `cd frontend && node scripts/verify-schedule-map.mjs`
Expected: PASS (both OK lines).

- [ ] **Step 13: Commit**

```bash
git add frontend/src/components/reports/Stripboard.jsx frontend/src/components/reports/Stripboard.css
git commit -m "feat(stripboard): group scenes into shoot-day blocks with page totals"
```

---

### Task 3: Segmented header card

**Files:**
- Modify: `frontend/src/components/reports/Stripboard.jsx` (the `stripboard-stats` block only, lines ~408-455)
- Modify: `frontend/src/components/reports/Stripboard.css`

**Interfaces:**
- Consumes: the existing `stats` memo and `activeScenes` — no new computed values. Pure presentational restructure.

- [ ] **Step 1: Replace the stats markup**

Replace the entire `<div className="stripboard-stats">…</div>` block with a segmented card. The Scheduling segment renders only when `hasSchedules && activeScheduleId`; the Story Days line only when `> 0`:

```jsx
            {/* Summary header card — segmented */}
            <div className="stripboard-stats sb-stats-card">
                <div className="sb-stats-segment sb-stats-identity">
                    <span className="sb-stats-primary">{activeScenes.length}</span>
                    <span className="sb-stats-caption">Scenes</span>
                </div>
                <div className="sb-stats-segment">
                    <span className="sb-stats-caption">Composition</span>
                    <div className="sb-stats-row">
                        <span className="stat-value"><Home size={13} /> {stats.intCount} INT</span>
                        <span className="stat-value"><Building2 size={13} /> {stats.extCount} EXT</span>
                        <span className="stat-value"><Sun size={13} /> {stats.dayCount} DAY</span>
                        <span className="stat-value"><Moon size={13} /> {stats.nightCount} NIGHT</span>
                    </div>
                </div>
                <div className="sb-stats-segment">
                    <span className="sb-stats-caption">Coverage</span>
                    <div className="sb-stats-row">
                        <span className="stat-value"><Users size={13} /> {stats.totalCharacters} Cast</span>
                        <span className="stat-value"><MapPin size={13} /> {stats.totalLocations} Locations</span>
                        {stats.totalStoryDays > 0 && (
                            <span className="stat-value"><CalendarDays size={13} /> {stats.totalStoryDays} Story Days</span>
                        )}
                    </div>
                </div>
                {hasSchedules && activeScheduleId && (
                    <div className="sb-stats-segment">
                        <span className="sb-stats-caption">Scheduling</span>
                        <div className="sb-stats-row">
                            <span className="stat-value">{stats.scheduledCount} scheduled</span>
                            <span className="stat-value sb-stats-muted">{stats.unscheduledCount} unscheduled</span>
                        </div>
                    </div>
                )}
                <div className="sb-stats-segment sb-stats-length">
                    <span className="sb-stats-primary sb-stats-accent">{stats.totalEighthsDisplay}</span>
                    <span className="sb-stats-caption">Pages</span>
                </div>
            </div>
```

- [ ] **Step 2: Add the segmented-card CSS**

Append to `Stripboard.css`. Keep the base `.stripboard-stats` rule (padding/background/border) and layer the segment structure on top:

```css
/* Segmented summary header card */
.sb-stats-card {
    gap: 0;
    flex-wrap: wrap;
    align-items: stretch;
}
.sb-stats-segment {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 0.3rem;
    padding: 0.25rem 1.1rem;
    border-right: 1px solid var(--border-color);
}
.sb-stats-segment:last-child {
    border-right: none;
}
.sb-stats-caption {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-secondary);
    font-weight: 600;
}
.sb-stats-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem;
}
.sb-stats-row .stat-value {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
}
.sb-stats-row .stat-value svg {
    color: var(--text-secondary);
}
.sb-stats-identity,
.sb-stats-length {
    align-items: center;
    text-align: center;
}
.sb-stats-primary {
    font-size: 1.5rem;
    font-weight: 700;
    line-height: 1;
    color: var(--text-primary);
}
.sb-stats-accent {
    color: var(--accent, #10b981);
}
.sb-stats-muted {
    color: var(--text-secondary);
}
@media (max-width: 900px) {
    .sb-stats-segment {
        border-right: none;
        border-bottom: 1px solid var(--border-color);
        padding: 0.5rem 0;
        width: 100%;
    }
    .sb-stats-segment:last-child {
        border-bottom: none;
    }
}
```

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`
Expected: `✓ built in …` with no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/reports/Stripboard.jsx frontend/src/components/reports/Stripboard.css
git commit -m "feat(stripboard): segmented summary header card"
```

---

## Self-Review

**Spec coverage:**
- §1 segmented header → Task 3 (four/five segments, dividers, Scheduling gated, responsive wrap). ✓
- §2 shoot-day grouping (blocks, header, footer page totals, unscheduled bin, schedule order, Shoot column retired, sort disabled) → Task 2 + helper Task 1. ✓
- §3 fallback & edge cases: no-schedule flat path preserved (Task 2 Step 8 `else` branch verbatim incl. story-day separators); omitted excluded from totals/count (Step 5 `active`); stale assignment → skipped (Task 1); fetch failure → empty `shootingDays` → single unscheduled bin (Step 2 catch + helper). ✓
- §4 affected code matches Tasks 1-3. ✓

**Placeholder scan:** none — all steps carry full code.

**Type/name consistency:** `buildShootDayBlocks(days, scenesById)` signature identical across Task 1 (def), Task 2 Step 5 (call). Block shape `{ dayNumber?, unscheduled?, scenes, sceneCount, eighths }` produced in Step 5, consumed in Step 8. `grouped`, `fullColSpan=7`, `scenesById`, `passesFilters` all defined before use. `formatEighths(0)` guard applied (Step 8 `totalLabel`). Scene-id key `scene.id || scene.scene_id` consistent.

**Note for the implementer (DRY refactor risk):** Task 2 Step 7 collapses the six breakdown cards into an array `.map`. Confirm the rendered output equals the current six hand-written cards (same icons, labels, note-dept keys `cast/props/wardrobe/vehicles/special_fx/sound`). If in doubt, keep the six explicit cards — behaviour parity outranks brevity.
