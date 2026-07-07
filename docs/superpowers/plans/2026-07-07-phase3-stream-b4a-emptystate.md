# Phase 3 · Stream B4a — EmptyState Adoption — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the in-scope ad-hoc "no-data placeholder" blocks to the shared `<EmptyState>` primitive, keeping each placeholder's copy verbatim.

**Architecture:** Each bespoke placeholder (`<div className="…-empty"><Icon/><h3>…</h3><p>…</p></div>`) is replaced by `<EmptyState icon={Icon} title="…" message={…} action={…} size={…}/>` (`frontend/src/components/ui/EmptyState.jsx`, already proven in `SceneList.jsx`). The primitive centers an icon + title + optional message/action with unified spacing/typography. Bespoke block CSS is pruned once its class is unused.

**Tech Stack:** React 18 + Vite (plain JSX, no TypeScript), lucide-react icons, plain CSS with design tokens in `frontend/src/index.css`.

## Global Constraints

- No test runner exists and live-drive is login-gated. Verification per task = `npm run build` green (from `frontend/`) + the task's grep invariant. No unit tests.
- `<EmptyState>` API (from `frontend/src/components/ui/EmptyState.jsx`, do not change it): `EmptyState({ icon, title, message, action, size='md' })`. `icon` is a **component reference** (e.g. `Users`), NOT an element — the primitive renders `<Icon size={size==='sm'?28:40} />`. `title` is required (string). `message`/`action` are optional ReactNodes. `size='sm'` for compact hosts (drawer sections, dropdowns, sidebar lists), `'md'` for full-panel placeholders. Import from the `ui` barrel: `import { EmptyState } from '../ui';` (all target files are at `components/<domain>/*`).
- **Copy is verbatim:** every `title`/`message` string must exactly match the text it replaces — no rewording.
- **Icon reuse:** every icon needed is already imported in its file (it appears in the current block). Do not add lucide imports; only add `EmptyState`.
- CSS prune rule (cascade-safe): after converting a block, delete its **block-specific** class rule (e.g. `.dashboard-empty`, `.stripboard-empty`, `.bd-empty`) and any rule scoped under it. For **generic shared** classes (`.empty-icon`, `.empty-icon-small`, `.empty-content`, `.empty-text`), first `grep -rn` the class across `frontend/src`; delete it only if no remaining JSX (in-scope OR excluded) still uses it — otherwise leave it. Leaving an inert shared rule is acceptable; stripping a class an excluded file still uses is not.
- **Staging discipline:** stage only the files a task changed (`git add <paths>`); never `git add .`/`-A`/`commit -a` (untracked `.claude/` must never be committed).
- Out of scope: badges (B4b); excluded areas (admin, campaigns, auth, frozen WIP); inline hints and deferred emoji-icon blocks (see "Skipped by inspection" below).

### Skipped by inspection (do NOT convert — documented per the spec's per-instance rule)

- `components/reports/Stripboard.jsx` `breakdown-empty` — inline `<span>None</span>` category hint, not a placeholder block.
- `components/breakdown/BreakdownDrawer.jsx` `bd-empty-hint` — inline `<p>No team-added items yet</p>`.
- `components/board/SchedulePopover.jsx` `sp-empty`/`sp-empty-msg` — text-only inline hints (no icon/heading).
- `components/schedule/DayColumn.jsx` `kanban-col-empty` — "Drop scenes here" drop-zone affordance, not a no-data placeholder.
- `components/board/BoardCanvas.jsx` `board-empty-state` — real blocks but use emoji icons (📋/🔍); mapping to the primitive's lucide-component `icon` API is a visual change beyond B4a's structural-only remit. Deferred to a follow-up with an icon-mapping decision.

---

### Task 1: scenes domain — 6 placeholder blocks

Convert the empty-state blocks in the scenes cluster. Both `scene-detail-empty` users are in this batch, so `.scene-detail-empty`/`.empty-content` become unused together.

**Files:**
- Modify: `frontend/src/components/scenes/FilteredSceneList.jsx` (+ its CSS `FilteredSceneList.css`)
- Modify: `frontend/src/components/scenes/SceneDetail.jsx` (+ `SceneDetail.css`)
- Modify: `frontend/src/components/scenes/CharacterList.jsx`, `frontend/src/components/scenes/LocationList.jsx` (+ `SceneList.css`)
- Modify: `frontend/src/components/scenes/CharacterDashboard.jsx`, `frontend/src/components/scenes/LocationDashboard.jsx` (+ `Dashboard.css`)

**Interfaces:**
- Consumes: `EmptyState` from `frontend/src/components/ui`.
- Produces: no prop/signature changes; parents untouched.

- [ ] **Step 1: FilteredSceneList.jsx** — add `import { EmptyState } from '../ui';` (after the existing imports), then replace:
```jsx
            <div className="scene-detail-empty">
                <div className="empty-content">
                    {type === 'character' ? <Users size={64} /> : <MapPin size={64} />}
                    <h3>Select a {type}</h3>
                    <p>Choose from the sidebar to view their scenes</p>
                </div>
            </div>
```
with:
```jsx
            <EmptyState
                icon={type === 'character' ? Users : MapPin}
                title={`Select a ${type}`}
                message="Choose from the sidebar to view their scenes"
            />
```

- [ ] **Step 2: SceneDetail.jsx** — add `import { EmptyState } from '../ui';` (or extend an existing `../ui` import if present), then replace:
```jsx
            <div className="scene-detail-empty">
                <div className="empty-content">
                    <Clapperboard size={64} className="empty-icon" />
                    <h3>Select a scene</h3>
                    <p>Choose a scene from the list to view its full breakdown</p>
                </div>
            </div>
```
with:
```jsx
            <EmptyState
                icon={Clapperboard}
                title="Select a scene"
                message="Choose a scene from the list to view its full breakdown"
            />
```

- [ ] **Step 3: CharacterList.jsx** — add `import { EmptyState } from '../ui';`, then replace:
```jsx
            <div className="list-empty">
                <Users size={32} className="empty-icon-small" />
                <p>No characters found</p>
            </div>
```
with:
```jsx
            <EmptyState icon={Users} title="No characters found" size="sm" />
```

- [ ] **Step 4: LocationList.jsx** — add `import { EmptyState } from '../ui';`, then replace:
```jsx
            <div className="list-empty">
                <MapPin size={32} className="empty-icon-small" />
                <p>No locations found</p>
            </div>
```
with:
```jsx
            <EmptyState icon={MapPin} title="No locations found" size="sm" />
```

- [ ] **Step 5: CharacterDashboard.jsx** — add `import { EmptyState } from '../ui';`, then replace:
```jsx
            <div className="dashboard-empty">
                <Users size={48} className="empty-icon" />
                <h3>No Characters Found</h3>
                <p>Characters will appear here once the script is analyzed</p>
            </div>
```
with:
```jsx
            <EmptyState
                icon={Users}
                title="No Characters Found"
                message="Characters will appear here once the script is analyzed"
            />
```

- [ ] **Step 6: LocationDashboard.jsx** — add `import { EmptyState } from '../ui';`, then replace:
```jsx
            <div className="dashboard-empty">
                <MapPin size={48} className="empty-icon" />
                <h3>No Locations Found</h3>
                <p>Locations will appear here once the script is analyzed</p>
            </div>
```
with:
```jsx
            <EmptyState
                icon={MapPin}
                title="No Locations Found"
                message="Locations will appear here once the script is analyzed"
            />
```

- [ ] **Step 7: Prune now-dead CSS (cascade-safe per the Global Constraints rule)**

For each of these classes, `grep -rn "<class>" frontend/src --include="*.jsx"` first; delete the CSS rule only if no JSX still references it:
- `.scene-detail-empty` (+ scoped children) — both users converted above → delete from wherever it's defined (`FilteredSceneList.css` and/or `SceneDetail.css`).
- `.list-empty` (+ children) in `SceneList.css` — both users converted → delete.
- `.dashboard-empty` (+ children) in `Dashboard.css` — both users converted → delete.
- Generic `.empty-content`, `.empty-icon`, `.empty-icon-small`: grep first. If still used by any remaining JSX (in-scope or excluded), LEAVE the rule; otherwise delete.

- [ ] **Step 8: Verify + commit**

Run (from `frontend/`):
```bash
grep -rn "scene-detail-empty\|list-empty\|dashboard-empty" src/components/scenes --include="*.jsx"
```
Expected: no output (all six blocks converted).
```bash
grep -c "EmptyState" src/components/scenes/FilteredSceneList.jsx src/components/scenes/SceneDetail.jsx src/components/scenes/CharacterList.jsx src/components/scenes/LocationList.jsx src/components/scenes/CharacterDashboard.jsx src/components/scenes/LocationDashboard.jsx
```
Expected: each file ≥ 2 (import + usage).

Run: `npm run build` — expected: succeeds.

```bash
git add frontend/src/components/scenes/FilteredSceneList.jsx frontend/src/components/scenes/FilteredSceneList.css frontend/src/components/scenes/SceneDetail.jsx frontend/src/components/scenes/SceneDetail.css frontend/src/components/scenes/CharacterList.jsx frontend/src/components/scenes/LocationList.jsx frontend/src/components/scenes/SceneList.css frontend/src/components/scenes/CharacterDashboard.jsx frontend/src/components/scenes/LocationDashboard.jsx frontend/src/components/scenes/Dashboard.css
git commit -m "refactor(scenes): adopt <EmptyState> primitive for placeholders

Convert scene-detail/list/dashboard empty states to <EmptyState> (copy
verbatim); prune the now-unused bespoke empty-state CSS. Part of Phase 3
Stream B4a.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```
(Only stage the files you actually changed — drop any CSS path you did not edit.)

---

### Task 2: reports + breakdown — Stripboard + BreakdownDrawer

**Files:**
- Modify: `frontend/src/components/reports/Stripboard.jsx` (+ `Stripboard.css`)
- Modify: `frontend/src/components/breakdown/BreakdownDrawer.jsx` (+ `BreakdownDrawer.css`)

**Interfaces:**
- Consumes: `EmptyState` from `frontend/src/components/ui`.

- [ ] **Step 1: Stripboard.jsx** — add `import { EmptyState } from '../ui';`. Convert ONLY the `stripboard-empty` block (leave every `<span className="breakdown-empty">None</span>` untouched — inline hint). Replace:
```jsx
                <div className="stripboard-empty">
                    <List size={32} />
                    <p>No scenes match the current filters</p>
                </div>
```
with:
```jsx
                <EmptyState icon={List} title="No scenes match the current filters" />
```

- [ ] **Step 2: BreakdownDrawer.jsx** — add `import { EmptyState } from '../ui';`. Convert the TWO `.bd-empty` DIV blocks (leave the `<p className="bd-empty-hint">…` inline hint untouched). Replace the items-empty block:
```jsx
                                        <div className="bd-empty">
                                            <Plus size={32} />
                                            <p>No items yet</p>
                                            <span>Add breakdown items for this category</span>
                                        </div>
```
with:
```jsx
                                        <EmptyState icon={Plus} title="No items yet" message="Add breakdown items for this category" size="sm" />
```
and the notes-empty block:
```jsx
                                        <div className="bd-empty">
                                            <MessageSquare size={32} />
                                            <p>No notes yet</p>
                                            <span>Add a note to start collaborating</span>
                                        </div>
```
with:
```jsx
                                        <EmptyState icon={MessageSquare} title="No notes yet" message="Add a note to start collaborating" size="sm" />
```

- [ ] **Step 3: Prune CSS** — per the cascade-safe rule: delete `.stripboard-empty` (+ children) from `Stripboard.css` (grep-confirm no other JSX uses it), and `.bd-empty` (+ children) from `BreakdownDrawer.css`. Leave `.breakdown-empty` and `.bd-empty-hint` (still used by the un-converted inline hints).

- [ ] **Step 4: Verify + commit**

Run (from `frontend/`):
```bash
grep -rn "className=\"stripboard-empty\"\|className=\"bd-empty\"" src/components/reports/Stripboard.jsx src/components/breakdown/BreakdownDrawer.jsx
```
Expected: no output. (`breakdown-empty` and `bd-empty-hint` may still appear — that is correct.)

Run: `npm run build` — expected: succeeds.

```bash
git add frontend/src/components/reports/Stripboard.jsx frontend/src/components/reports/Stripboard.css frontend/src/components/breakdown/BreakdownDrawer.jsx frontend/src/components/breakdown/BreakdownDrawer.css
git commit -m "refactor(reports,breakdown): adopt <EmptyState> for list/section placeholders

Convert Stripboard filtered-empty and the two BreakdownDrawer section-empty
blocks to <EmptyState> (copy verbatim); leave inline 'None'/hint spans. Prune
the bespoke block CSS. Part of Phase 3 Stream B4a.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

### Task 3: schedule + notifications — ShootingSchedulePage + NotificationBell

**Files:**
- Modify: `frontend/src/components/schedule/ShootingSchedulePage.jsx` (+ its CSS)
- Modify: `frontend/src/components/notifications/NotificationBell.jsx` (+ its CSS)

**Interfaces:**
- Consumes: `EmptyState` from `frontend/src/components/ui`.

- [ ] **Step 1: ShootingSchedulePage.jsx** — add `import { EmptyState } from '../ui';` (or extend an existing `../ui` import). This block has an action button — keep it verbatim in the `action` slot. Replace:
```jsx
                <div className="schedule-empty">
                    <CalendarDays size={48} />
                    <h2>No schedules yet</h2>
                    <p>Go to the Board, select scenes, and click "Schedule" to start building your shooting days.</p>
                    <button className="schedule-create-btn" onClick={handleCreateSchedule}>
                        <Plus size={16} /> Create Schedule
                    </button>
                </div>
```
with:
```jsx
                <EmptyState
                    icon={CalendarDays}
                    title="No schedules yet"
                    message='Go to the Board, select scenes, and click "Schedule" to start building your shooting days.'
                    action={
                        <button className="schedule-create-btn" onClick={handleCreateSchedule}>
                            <Plus size={16} /> Create Schedule
                        </button>
                    }
                />
```
(Note the `message` uses single-quotes because the copy contains double-quotes around "Schedule".)

- [ ] **Step 2: NotificationBell.jsx** — add `import { EmptyState } from '../ui';`. This lives in a dropdown → `size="sm"`. Replace:
```jsx
                            <div className="notification-empty">
                                <Bell size={32} />
                                <p>No notifications yet</p>
                            </div>
```
with:
```jsx
                            <EmptyState icon={Bell} title="No notifications yet" size="sm" />
```

- [ ] **Step 3: Prune CSS** — per the cascade-safe rule: delete `.schedule-empty` (+ children) from ShootingSchedulePage's CSS and `.notification-empty` (+ children) from NotificationBell's CSS (grep-confirm unused first). Keep `.schedule-create-btn` (still used inside the action slot) and any other still-referenced class.

- [ ] **Step 4: Verify + commit**

Run (from `frontend/`):
```bash
grep -rn "schedule-empty\|notification-empty" src/components/schedule/ShootingSchedulePage.jsx src/components/notifications/NotificationBell.jsx
```
Expected: no output.

Run: `npm run build` — expected: succeeds.

```bash
git add frontend/src/components/schedule/ShootingSchedulePage.jsx frontend/src/components/notifications/NotificationBell.jsx
# plus the two CSS files you edited
git commit -m "refactor(schedule,notifications): adopt <EmptyState> for placeholders

Convert the schedule-page and notification-dropdown empty states to
<EmptyState> (copy verbatim; schedule keeps its create-button in the action
slot). Prune bespoke block CSS. Part of Phase 3 Stream B4a.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```
(Include the two CSS files you edited in the `git add`.)

---

## End-of-stream verification

After all 3 tasks, from `frontend/src`:

- All converted blocks gone from JSX:
  ```bash
  grep -rn "className=\"scene-detail-empty\"\|className=\"list-empty\"\|className=\"dashboard-empty\"\|className=\"stripboard-empty\"\|className=\"bd-empty\"\|className=\"schedule-empty\"\|className=\"notification-empty\"" . --include="*.jsx"
  ```
  Returns nothing.
- Each converted file imports and uses `EmptyState`:
  ```bash
  grep -rln "EmptyState" components/scenes/FilteredSceneList.jsx components/scenes/SceneDetail.jsx components/scenes/CharacterList.jsx components/scenes/LocationList.jsx components/scenes/CharacterDashboard.jsx components/scenes/LocationDashboard.jsx components/reports/Stripboard.jsx components/breakdown/BreakdownDrawer.jsx components/schedule/ShootingSchedulePage.jsx components/notifications/NotificationBell.jsx
  ```
  Returns all ten.
- Skipped-by-inspection items untouched: `breakdown-empty`, `bd-empty-hint`, `sp-empty`, `kanban-col-empty`, `board-empty-state` still present in their files.
- `npm run build` green.
- No test runner; live-drive login-gated. Correctness rests on build + per-batch review + these invariants + before/after that every `title`/`message` string is verbatim and each host's layout still reads correctly. Intended change: unified empty-state chrome (icon size, spacing, typography) across the converted blocks.
