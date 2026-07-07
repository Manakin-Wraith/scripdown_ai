# Phase 3 · Stream B3b — Drawer Adoption — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `TeamDrawer` and `StripDetailDrawer` to the shared `<Drawer>` primitive and delete the dead `NoteDrawer`, keeping every leeched CSS class alive.

**Architecture:** Each drawer drops its hand-rolled backdrop + fixed side-panel + header chrome (markup + CSS) and delegates to `<Drawer>` (`frontend/src/components/ui/Drawer.jsx`), which supplies the portal, backdrop, `.ui-drawer` panel, header (`title`/`subtitle`/X), `.ui-drawer-body`, and — via `useOverlay` — Escape-to-close, scroll-lock, and focus-restore. Content moves into `children`; content-specific CSS is kept. Because `TeamDrawer` currently leeches `.drawer-loading`/`.drawer-error` from the soon-deleted `NoteDrawer.css`, those rules are relocated into `TeamDrawer.css` before deletion; and because `TeamDrawer`'s confirm dialogs are styled via a `.team-drawer ~ .confirm-overlay` sibling combinator that breaks once `.team-drawer` is gone, those rules are de-sibling-ed.

**Tech Stack:** React 18 + Vite (plain JSX, no TypeScript), lucide-react icons, plain CSS with design tokens in `frontend/src/index.css`.

## Global Constraints

- No test runner exists and live-drive is login-gated. Verification per task = `npm run build` green (run from `frontend/`) + the task's grep invariant. There are no unit tests to write.
- `<Drawer>` API (from `frontend/src/components/ui/Drawer.jsx`, do not change it): `Drawer({ isOpen, onClose, title, subtitle, side='right', width='480px', footer, showClose=true, children })`. `title`/`subtitle` are ReactNodes; `title` renders inside `<span className="ui-drawer-title">`, `subtitle` inside `<span className="ui-drawer-subtitle">`, both within `.ui-drawer-title-group` (flex column). The header renders when `title` OR `showClose` is truthy and provides its own padding + bottom border; `.ui-drawer-body` provides its own padding (`var(--space-6)`) + `overflow-y:auto` + `flex:1`; `.ui-drawer` provides the fixed-height panel, `--bg-card` background, side border, and shadow; the backdrop is click-to-close. Import from the barrel: `import { Drawer } from '../ui';` (both drawers live at `components/<domain>/*`, so `'../ui'` is correct).
- **Stream A guard (binding):** never modify any `timeline-*` CSS rule or the value inside any rule whose selector contains `timeline-`. `StripDetailDrawer` renders `.drawer-day-badge timeline-<code>` badges — their classes and values must stay verbatim; you may relocate the element in the DOM but must not touch the rules.
- Do NOT convert bespoke buttons inside these drawers to `<Button>`, and do NOT migrate `TeamDrawer`'s inline `.confirm-overlay` dialogs to `useConfirmDialog` — both are out of scope (later streams).
- `FeedbackDrawer` and `BreakdownDrawer` are out of scope — do not touch them.
- Minor padding deltas from unifying on `.ui-drawer-body`/`.ui-drawer-header` are accepted intended consequences, not regressions.

---

### Task 1: Convert TeamDrawer to `<Drawer>`

`TeamDrawer` (`components/team/TeamDrawer.jsx`) is a backdrop side-panel rendered by `ScriptHeader`. Its header maps cleanly onto the primitive's `title`/`subtitle`. This task also (a) relocates `.drawer-loading`/`.drawer-error` into `TeamDrawer.css` so they survive Task 3's `NoteDrawer.css` deletion, and (b) de-siblings the `.team-drawer ~ .confirm-overlay` rules so the two inline confirm dialogs stay styled after `.team-drawer` disappears.

**Files:**
- Modify: `frontend/src/components/team/TeamDrawer.jsx`
- Modify: `frontend/src/components/team/TeamDrawer.css`

**Interfaces:**
- Consumes: `Drawer` from `frontend/src/components/ui` (barrel).
- Produces: no prop-signature change — `TeamDrawer({ isOpen, onClose, scriptId, scriptTitle, currentUserId, isOwner })` unchanged; `ScriptHeader.jsx` untouched.

- [ ] **Step 1: Add the `Drawer` import**

In `TeamDrawer.jsx`, change the ui-barrel import (currently `import { Spinner } from '../ui';`) to:
```jsx
import { Spinner, Drawer } from '../ui';
```
Leave the lucide import as-is: `X` is still used by the two `.confirm-overlay` blocks? Check — the confirm blocks use `UserX`/`Trash2`, not `X`. `X` was only used by the removed `.close-btn`. So also remove `X` from the lucide import (drop just the `X,` token; keep `Crown, Shield, UserX, Clock, Users, AlertCircle, Mail, UserPlus, Link as LinkIcon, ChevronDown, ChevronUp, Trash2`).

- [ ] **Step 2: Replace the backdrop + panel + header wrapper with `<Drawer>`**

Keep the `if (!isOpen) return null;` guard (it preserves exact closed-state behavior for the sibling confirm-overlays). In the `return (…)`, replace this opening block:
```jsx
        <>
            {/* Backdrop */}
            <div className="drawer-backdrop" onClick={onClose} />
            
            {/* Drawer */}
            <div className={`team-drawer ${isOpen ? 'open' : ''}`}>
                {/* Header */}
                <div className="drawer-header">
                    <div className="drawer-title-group">
                        <h3>
                            <Users size={18} />
                            Team Members
                        </h3>
                        <span className="drawer-subtitle">{scriptTitle}</span>
                    </div>
                    <button className="close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="drawer-content">
```
with:
```jsx
        <>
            <Drawer
                isOpen={isOpen}
                onClose={onClose}
                side="right"
                width="420px"
                title={<span className="team-drawer-title"><Users size={18} /> Team Members</span>}
                subtitle={scriptTitle}
            >
                <div className="team-drawer-body">
```
Then find the matching close of the old `.drawer-content` div and the old `.team-drawer` div — the two consecutive `</div>` right before `{/* Remove Member Confirmation Modal */}`:
```jsx
                </div>
            </div>

            {/* Remove Member Confirmation Modal */}
```
and replace them with a single `</div>` + `</Drawer>`:
```jsx
                </div>
            </Drawer>

            {/* Remove Member Confirmation Modal */}
```
The `.drawer-loading`/`.drawer-error`/team-section body JSX between those boundaries is unchanged. The two `{removeConfirm && …}` / `{revokeConfirm && …}` `.confirm-overlay` blocks and the `<InviteModal … />` stay exactly as they are, as siblings of `<Drawer>` inside the fragment.

- [ ] **Step 3: Relocate `.drawer-loading`/`.drawer-error` and add the two new wrapper classes in TeamDrawer.css**

At the end of `TeamDrawer.css`, append:
```css
/* Header title node (icon + label), replaces .team-drawer .drawer-header h3 */
.team-drawer-title {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

/* Body vertical rhythm (was provided by .team-drawer .drawer-content) */
.team-drawer-body {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
}

/* Relocated from NoteDrawer.css (deleted in Task 3); TeamDrawer body still uses these */
.drawer-loading,
.drawer-error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 3rem 1rem;
    color: var(--gray-400);
}

.drawer-error {
    color: var(--danger);
}
```

- [ ] **Step 4: Prune dead chrome + de-sibling the confirm-overlay rules in TeamDrawer.css**

In `TeamDrawer.css`:
- Delete the stale comment `/* Drawer (reuses backdrop from NoteDrawer) */`.
- Delete the `.team-drawer` rule (the `position:fixed` panel), the `.team-drawer.open` rule, `.team-drawer .drawer-header`, `.team-drawer .drawer-header h3`, and `.team-drawer .drawer-content` (chrome now provided by the primitive; body rhythm now by `.team-drawer-body`).
- De-sibling these five rules — remove the `.team-drawer ~ ` prefix from each so they no longer depend on the now-absent `.team-drawer` element:
  - `.team-drawer ~ .confirm-overlay .confirm-icon.danger` → `.confirm-overlay .confirm-icon.danger`
  - `.team-drawer ~ .confirm-overlay .confirm-icon.warning` → `.confirm-overlay .confirm-icon.warning`
  - `.team-drawer ~ .confirm-overlay .confirm-name` → `.confirm-overlay .confirm-name`
  - `.team-drawer ~ .confirm-overlay .confirm-delete.warning` → `.confirm-overlay .confirm-delete.warning`
  - `.team-drawer ~ .confirm-overlay .confirm-delete.warning:hover` → `.confirm-overlay .confirm-delete.warning:hover`

Keep everything else (`.team-section`, `.section-header`, member/role/invite styles, the base `.confirm-overlay`/`.confirm-modal`/`.confirm-*` rules).

- [ ] **Step 5: Verify chrome is gone, relocations present, and build passes**

Run (from `frontend/`):
```bash
grep -n "team-drawer ~\|\.team-drawer\.open\|\.team-drawer \.drawer-header\|reuses backdrop from NoteDrawer" src/components/team/TeamDrawer.css
```
Expected: no output.
```bash
grep -n "drawer-loading\|drawer-error\|team-drawer-body\|team-drawer-title" src/components/team/TeamDrawer.css
```
Expected: shows the relocated `.drawer-loading`/`.drawer-error` and the two new wrapper rules.
```bash
grep -c "<Drawer" src/components/team/TeamDrawer.jsx
```
Expected: `1`.

Run: `npm run build`
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/team/TeamDrawer.jsx frontend/src/components/team/TeamDrawer.css
git commit -m "refactor(team): adopt <Drawer> primitive in TeamDrawer

Move TeamDrawer onto the shared <Drawer> (title/subtitle map directly). Drop
the bespoke backdrop/panel/header CSS. Relocate .drawer-loading/.drawer-error
(NoteDrawer-only classes the body still uses) into TeamDrawer.css, and
de-sibling the .team-drawer ~ .confirm-overlay rules so the confirm dialogs
keep their styling. Part of Phase 3 Stream B3b.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

Do NOT use `git add .`/`-A`/`commit -a` — there is untracked `.claude/` in the tree that must never be committed. Stage only the two named files.

---

### Task 2: Convert StripDetailDrawer to `<Drawer>`

`StripDetailDrawer` (`components/board/StripDetailDrawer.jsx`) is a backdrop side-panel rendered by `ZoomableStripboard` and **conditionally mounted with no `isOpen` prop**. It has its own Escape handler (replaced by the primitive's) and a rich three-row header (scene identity + location + editable story-day controls, including `timeline-*` badges). All its content CSS classes are bare (not scoped under `.strip-detail-drawer`/`.drawer-header`), so reparenting the header rows is safe.

**Files:**
- Modify: `frontend/src/components/board/StripDetailDrawer.jsx`
- Modify: `frontend/src/components/board/StripDetailDrawer.css`

**Interfaces:**
- Consumes: `Drawer` from `frontend/src/components/ui`.
- Produces: no prop change — `StripDetailDrawer({ stripId, scenes, userItemsByScene, onClose, scriptId, onStoryDayChanged })` unchanged; `ZoomableStripboard.jsx` untouched.

- [ ] **Step 1: Add the `Drawer` import**

In `StripDetailDrawer.jsx`, add to the ui imports. There is currently no `../ui` import; add one after the existing imports (keep the lucide import unchanged — `X` is still used by the story-day edit/cancel buttons):
```jsx
import { Drawer } from '../ui';
```

- [ ] **Step 2: Remove the bespoke Escape handler**

Delete this `useEffect` (the primitive's `useOverlay` provides Escape-to-close):
```jsx
    // Close on Escape
    useEffect(() => {
        const handleKey = (e) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', handleKey);
        return () => window.removeEventListener('keydown', handleKey);
    }, [onClose]);
```
`useEffect` is still imported and used elsewhere? Check — after removal, if no other `useEffect` remains, drop it from the React import (`import React, { useState } from 'react';`). (There is no other `useEffect` in this file, so remove it.)

- [ ] **Step 3: Replace the backdrop + panel wrapper with `<Drawer>`; move the header rows into `title`; drop the bespoke close button**

Replace the entire `return (…)` block. The three header rows (title-row **without** its `.drawer-close-btn`, the setting row, and the meta-row) become the `title` node wrapped in `.sdd-header-content`; the primitive supplies the X close. The `.drawer-body` block is unchanged and becomes `children`:
```jsx
    return (
        <Drawer
            isOpen
            onClose={onClose}
            side="right"
            width="400px"
            title={
                <div className="sdd-header-content">
                    <div className="drawer-title-row">
                        <span className="drawer-scene-number">Scene {scene.scene_number}</span>
                        <span className={`drawer-ie-badge ${scene.int_ext === 'INT' ? 'int' : 'ext'}`}>
                            {scene.int_ext}
                        </span>
                        <span className="drawer-time">{scene.time_of_day}</span>
                    </div>

                    <div className="drawer-setting">
                        <MapPin size={14} />
                        <span>{scene.setting || 'Unknown Location'}</span>
                    </div>

                    <div className="drawer-meta-row">
                        {/* Story Day Editing Controls */}
                        <div className="drawer-sd-controls">
                            {scene.story_day && !sdEditing && (
                                <button
                                    className={`drawer-day-badge timeline-${(scene.timeline_code || 'PRESENT').toLowerCase()} editable-drawer-badge`}
                                    onClick={() => { setSdDraft(scene.story_day.toString()); setSdEditing(true); }}
                                    title="Click to edit story day"
                                >
                                    <CalendarDays size={12} />
                                    {scene.story_day_label || `Day ${scene.story_day}`}
                                    <Pencil size={9} className="drawer-edit-hint" />
                                </button>
                            )}
                            {!scene.story_day && !sdEditing && (
                                <button
                                    className="drawer-day-badge unassigned editable-drawer-badge"
                                    onClick={() => { setSdDraft('1'); setSdEditing(true); }}
                                    title="Assign story day"
                                >
                                    <CalendarDays size={12} />
                                    No Day
                                    <Pencil size={9} className="drawer-edit-hint" />
                                </button>
                            )}
                            {sdEditing && (
                                <div className="drawer-sd-edit">
                                    <span className="drawer-sd-label">Day</span>
                                    <input
                                        className="drawer-sd-input"
                                        type="number"
                                        min="1"
                                        value={sdDraft}
                                        onChange={e => setSdDraft(e.target.value)}
                                        onKeyDown={e => {
                                            if (e.key === 'Enter') {
                                                const val = parseInt(sdDraft, 10);
                                                if (val >= 1) handleStoryDayAction(() => setStoryDay(scriptId, sceneId, val)).then(() => setSdEditing(false));
                                            }
                                            if (e.key === 'Escape') setSdEditing(false);
                                        }}
                                        disabled={sdSaving}
                                        autoFocus
                                    />
                                    <button className="drawer-sd-btn confirm" disabled={sdSaving} onClick={() => {
                                        const val = parseInt(sdDraft, 10);
                                        if (val >= 1) handleStoryDayAction(() => setStoryDay(scriptId, sceneId, val)).then(() => setSdEditing(false));
                                    }}><Check size={14} /></button>
                                    <button className="drawer-sd-btn cancel" disabled={sdSaving} onClick={() => setSdEditing(false)}><X size={14} /></button>
                                </div>
                            )}
                            {scene.story_day && !sdEditing && scriptId && (
                                <>
                                    <button
                                        className={`drawer-sd-action ${scene.is_new_story_day ? 'active' : ''}`}
                                        onClick={() => handleStoryDayAction(() => toggleNewDay(scriptId, sceneId))}
                                        disabled={sdSaving}
                                        title={scene.is_new_story_day ? 'Starts new day (toggle)' : 'Mark as new day'}
                                    >
                                        <Sun size={11} />
                                    </button>
                                    <select
                                        className="drawer-sd-timeline"
                                        value={scene.timeline_code || 'PRESENT'}
                                        onChange={(e) => handleStoryDayAction(() => setTimelineCode(scriptId, sceneId, e.target.value))}
                                        disabled={sdSaving}
                                        title="Timeline code"
                                    >
                                        {TIMELINE_CODE_OPTIONS.map(opt => (
                                            <option key={opt} value={opt}>{opt.charAt(0) + opt.slice(1).toLowerCase().replace('_', ' ')}</option>
                                        ))}
                                    </select>
                                </>
                            )}
                        </div>
                        {scene.page_length_eighths > 0 && (
                            <span className="drawer-pages">{formatEighths(scene.page_length_eighths)} pages</span>
                        )}
                        {scene.shot_type && (
                            <span className="drawer-shot-type">{scene.shot_type}</span>
                        )}
                    </div>
                </div>
            }
        >
            <div className="drawer-body">
                {breakdownSections.map(section => (
                    <div key={section.label} className="drawer-section">
                        <div className="drawer-section-header" style={{ '--section-color': section.color }}>
                            <section.icon size={14} />
                            <span>{section.label}</span>
                            <span className="drawer-section-count">{section.items.length}</span>
                        </div>
                        {section.items.length > 0 ? (
                            <ul className="drawer-item-list">
                                {section.items.map((item, i) => (
                                    <li key={i}>{item}</li>
                                ))}
                            </ul>
                        ) : (
                            <span className="drawer-empty">None</span>
                        )}
                    </div>
                ))}

                {atmosphere && (
                    <div className="drawer-section">
                        <div className="drawer-section-header" style={{ '--section-color': '#94a3b8' }}>
                            <Cloud size={14} />
                            <span>Atmosphere</span>
                        </div>
                        <p className="drawer-atmosphere-text">{atmosphere}</p>
                    </div>
                )}
            </div>
        </Drawer>
    );
```
Note the `.drawer-close-btn` button from the old `.drawer-title-row` is intentionally dropped (the primitive supplies the X close).

- [ ] **Step 4: Prune dead chrome + neutralize doubled padding in StripDetailDrawer.css; add `.sdd-header-content`**

In `StripDetailDrawer.css`:
- Delete `.drawer-backdrop`, `.strip-detail-drawer`, `@keyframes slideIn`, `@keyframes fadeIn` (panel/backdrop chrome now from the primitive).
- Delete `.drawer-header` (its padding + border are now provided by `.ui-drawer-header`).
- Delete `.drawer-close-btn` and `.drawer-close-btn:hover` (button removed).
- Edit `.drawer-body`: remove the `flex: 1;`, `overflow-y: auto;`, and `padding: 1rem 1.25rem;` declarations (the primitive's `.ui-drawer-body` provides those), keeping only `display: flex; flex-direction: column; gap: 1rem;`. Leave the `.drawer-body::-webkit-scrollbar*` rules as-is (harmless).
- Add:
```css
/* Header rows container, passed as the <Drawer> title node */
.sdd-header-content {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
```
Keep everything else, and **do not touch any `timeline-*` rule** (`.drawer-day-badge.timeline-flashback`, `-dream`, `-fantasy`, `-montage`, etc.) or the `.drawer-day-badge`/`.drawer-sd-*`/`.drawer-section*`/`.drawer-item-list`/`.drawer-empty`/`.drawer-atmosphere-text` content rules.

- [ ] **Step 5: Verify chrome is gone, timeline rules untouched, and build passes**

Run (from `frontend/`):
```bash
grep -n "\.strip-detail-drawer\|\.drawer-backdrop\|@keyframes slideIn\|@keyframes fadeIn\|\.drawer-close-btn" src/components/board/StripDetailDrawer.css
```
Expected: no output.
```bash
grep -c "timeline-" src/components/board/StripDetailDrawer.css
```
Expected: `4` (the four `.drawer-day-badge.timeline-*` rules, unchanged).
```bash
grep -c "<Drawer" src/components/board/StripDetailDrawer.jsx
```
Expected: `1`.

Run: `npm run build`
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/board/StripDetailDrawer.jsx frontend/src/components/board/StripDetailDrawer.css
git commit -m "refactor(board): adopt <Drawer> primitive in StripDetailDrawer

Move StripDetailDrawer onto the shared <Drawer>. Pass the rich three-row header
via the title slot; drop the bespoke backdrop/panel CSS and Escape handler
(the primitive owns Escape). timeline-* badges preserved verbatim. Part of B3b.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

Stage only the two named files (never `git add .`/`-A`/`-a`).

---

### Task 3: Delete dead NoteDrawer

`NoteDrawer` (`components/notes/NoteDrawer.jsx` / `.css`) has zero renderers (verified) — a superseded near-clone of `BreakdownDrawer`. Its only live consumer of shared classes was `TeamDrawer`, which Task 1 moved off them (and relocated `.drawer-loading`/`.drawer-error`). `DepartmentNotesSection` (also in `components/notes/`) is unrelated and stays.

**Files:**
- Delete: `frontend/src/components/notes/NoteDrawer.jsx`, `frontend/src/components/notes/NoteDrawer.css`

- [ ] **Step 1: Delete the files**

```bash
cd frontend
git rm src/components/notes/NoteDrawer.jsx src/components/notes/NoteDrawer.css
```

- [ ] **Step 2: Verify no references remain**

Run:
```bash
grep -rn "NoteDrawer" src --include="*.jsx" --include="*.js" --include="*.css"
```
Expected: no output. (The stale `TeamDrawer.css` comment was removed in Task 1.)
```bash
grep -rn 'drawer-content"\|drawer-title-group"\|"drawer-subtitle"' src --include="*.jsx"
```
Expected: no output (no live JSX still relies on the NoteDrawer-only wrapper classes; the primitive's `ui-drawer-*` classes are a different prefix and won't match these quoted forms).

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: build succeeds (no unresolved-import errors).

- [ ] **Step 4: Commit**

```bash
git rm src/components/notes/NoteDrawer.jsx src/components/notes/NoteDrawer.css  # if not already staged
git commit -m "refactor(notes): delete dead NoteDrawer component

Remove NoteDrawer.jsx + .css — zero renderers, a superseded near-clone of
BreakdownDrawer. Its only shared-class consumer (TeamDrawer) was migrated in
Task 1. Part of Phase 3 Stream B3b.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

## End-of-stream verification

After all 3 tasks, from `frontend/src`:

- Both drawers use the primitive:
  ```bash
  grep -l "import { .*Drawer.* } from '../ui'" components/team/TeamDrawer.jsx components/board/StripDetailDrawer.jsx
  ```
  Returns both files.
- No bespoke drawer chrome remains in the two converted files:
  ```bash
  grep -rn "drawer-backdrop\|\.team-drawer\b\|\.strip-detail-drawer\b" components/team/TeamDrawer.jsx components/board/StripDetailDrawer.jsx components/team/TeamDrawer.css components/board/StripDetailDrawer.css
  ```
  Returns nothing (the `.ui-drawer-*` classes the primitive uses are a different prefix).
- Dead NoteDrawer gone: `grep -rn "NoteDrawer" . --include="*.jsx" --include="*.js" --include="*.css"` returns nothing.
- `.confirm-overlay` styling in `TeamDrawer.css` no longer contains `.team-drawer ~`.
- `.drawer-loading`/`.drawer-error` are defined in `TeamDrawer.css`.
- `npm run build` green.
- No test runner; live-drive login-gated. Correctness rests on build + per-task review + these invariants + before/after of each drawer's open/close wiring and the TeamDrawer confirm-dialog styling. Intended new behavior: Escape-to-close, scroll-lock, and focus-restore now apply to both drawers. `FeedbackDrawer` and `BreakdownDrawer` untouched.
