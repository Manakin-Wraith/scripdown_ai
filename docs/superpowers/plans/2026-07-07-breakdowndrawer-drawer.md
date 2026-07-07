# BreakdownDrawer → `<Drawer>` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate BreakdownDrawer's bespoke drawer shell to the shared `<Drawer>` primitive (adding a reusable `subHeader` slot) and its two `bd-confirm-*` dialogs to `useConfirmDialog`, preserving the fixed-header + fixed-tabs + scrolling-content layout.

**Architecture:** Three sequential tasks. T1 adds an additive `subHeader` slot to `<Drawer>`. T2 replaces BreakdownDrawer's backdrop/panel/header/tabs shell with `<Drawer subHeader={tabs}>`, reconciling the content scroll region. T3 consolidates the two hand-rolled confirm dialogs onto `useConfirmDialog`, matching the TeamDrawer B5 pattern.

**Tech Stack:** React 18 + Vite, plain JSX, plain CSS with design tokens. No TypeScript, no test runner.

## Global Constraints

- **No test runner exists.** Verification per task = `npm run build` from `frontend/` succeeds + the grep invariants in that task. Live-drive is login-gated and unavailable.
- **Staging discipline (CRITICAL):** stage ONLY the named files with an explicit `git add <path> …`. NEVER `git add .`, `git add -A`, or `git commit -a` — an untracked `.claude/` directory must never be committed.
- **Commit trailers (MUST append to every commit):**
  ```
  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN
  ```
- **`<Drawer>` primitive:** `components/ui/Drawer.jsx` renders a portal'd backdrop + panel with `ui-drawer-header` (title/subtitle/close via `useOverlay` — Escape + scroll-lock + focus-restore) then a single scrolling `ui-drawer-body`. Props today: `isOpen, onClose, title, subtitle, side, width, footer, showClose, children`.
- **`useConfirmDialog`:** `const { confirm } = useConfirmDialog();` → `await confirm({ title, message, variant:'danger'|'warning'|'info', confirmText? })` returns `Promise<boolean>`; `message` is a single string. Import path from `components/breakdown/BreakdownDrawer.jsx`: `'../../context/ConfirmDialogContext'`.
- **Import survival (verified):** in `BreakdownDrawer.jsx`, `X` is used at lines 444 (header close — removed in T2), 472 (`.bd-error` close — KEPT), 559 (KEPT) → **keep the `X` import**. `Trash2` is used at 622 (item row) and 790 (note row) plus the confirm modals (removed in T3) → **keep the `Trash2` import**.
- **`fadeIn` keyframe** (`BreakdownDrawer.css` lines 15–18) is referenced by `.drawer-backdrop` (line 12, removed in T2) and `.bd-confirm-overlay` (line 1085, removed in T3). Keep it through T2; remove it in T3 once orphaned.
- **No behavior changes** beyond the shell/confirm swaps: content logic, data fetching, item/note rendering, and the `.bd-error` banner feedback are unchanged. No new toasts.

---

### Task 1: Add `subHeader` slot to `<Drawer>`

**Files:**
- Modify: `frontend/src/components/ui/Drawer.jsx`
- Modify: `frontend/src/components/ui/Drawer.css`

**Interfaces:**
- Produces: `<Drawer subHeader={node}>` renders `node` in a fixed `.ui-drawer-subheader` region between the header and the scrolling body. Consumed by Task 2.

- [ ] **Step 1: Add the prop to JSDoc + destructure** — in `Drawer.jsx`, change the JSDoc line
```jsx
 *  subtitle?: React.ReactNode, side?: 'right'|'left', width?: string,
 *  footer?: React.ReactNode, showClose?: boolean, children?: React.ReactNode
```
to
```jsx
 *  subtitle?: React.ReactNode, side?: 'right'|'left', width?: string,
 *  subHeader?: React.ReactNode, footer?: React.ReactNode, showClose?: boolean, children?: React.ReactNode
```
and change the destructure
```jsx
  isOpen, onClose, title, subtitle, side = 'right', width = '480px',
  footer, showClose = true, children,
```
to
```jsx
  isOpen, onClose, title, subtitle, side = 'right', width = '480px',
  subHeader, footer, showClose = true, children,
```

- [ ] **Step 2: Render the subHeader** — in `Drawer.jsx`, change
```jsx
        <div className="ui-drawer-body">{children}</div>
```
to
```jsx
        {subHeader && <div className="ui-drawer-subheader">{subHeader}</div>}
        <div className="ui-drawer-body">{children}</div>
```

- [ ] **Step 3: Add the CSS** — in `Drawer.css`, immediately after the `.ui-drawer-close:hover { … }` line and before `.ui-drawer-body`, add:
```css
.ui-drawer-subheader { flex-shrink: 0; }
```

- [ ] **Step 4: Verify** — from `frontend/`:
```bash
grep -n "subHeader" src/components/ui/Drawer.jsx
```
Expected: the JSDoc line, the destructure, and the conditional render (3 hits).
```bash
grep -n "ui-drawer-subheader" src/components/ui/Drawer.css
```
Expected: the new rule.
```bash
npm run build
```
Expected: succeeds (pre-existing chunk-size + apiService dynamic-import warnings are unrelated and fine).

- [ ] **Step 5: Commit**
```bash
git add frontend/src/components/ui/Drawer.jsx frontend/src/components/ui/Drawer.css
git commit -m "feat(ui): add reusable subHeader slot to <Drawer>

Renders an optional node in a fixed (flex-shrink:0) region between the drawer
header and the scrolling body — for fixed sub-navs like tab bars. Additive;
existing callers pass no subHeader so their output is unchanged. Part of the
BreakdownDrawer conversion (Phase 3).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

### Task 2: Convert the BreakdownDrawer shell to `<Drawer>`

**Files:**
- Modify: `frontend/src/components/breakdown/BreakdownDrawer.jsx`
- Modify: `frontend/src/components/breakdown/BreakdownDrawer.css`

**Interfaces:**
- Consumes: `<Drawer>` with the `subHeader` prop from Task 1.

**Context the diff can't show:** the current shell (lines ~424–463) is a fragment `<>` containing `<div className="drawer-backdrop" onClick={onClose} />`, then `<div className="breakdown-drawer …">` containing in order `<div className="bd-header">` (title-group `<h3>{categoryTitle}</h3>` + `bd-subtitle` span + `bd-close-btn`), `<div className="bd-tabs">…</div>`, and `<div className="bd-content">…</div>`; the panel `</div>` closes near line 863, and the two `{deleteItemConfirm && (…)}` / `{deleteNoteConfirm && (…)}` blocks follow before the fragment closes. The `bd-tabs` and `bd-content` blocks are large — **move them verbatim**, do not rewrite their inner JSX.

- [ ] **Step 1: Import the primitive** — near the other imports in `BreakdownDrawer.jsx`, add:
```jsx
import { Drawer } from '../ui';
```
(Keep the `X` and `Trash2` lucide imports — both are still used elsewhere per Global Constraints.)

- [ ] **Step 2: Replace the backdrop + panel + header shell.** Replace this opening block (the backdrop, the `breakdown-drawer` opening div, and the entire `bd-header` div through its close), currently:
```jsx
    return (
        <>
            {/* Backdrop */}
            <div className="drawer-backdrop" onClick={onClose} />
            
            {/* Drawer */}
            <div className={`breakdown-drawer ${isOpen ? 'open' : ''}`}>
                {/* Header */}
                <div className="bd-header">
                    <div className="bd-title-group">
                        <h3>{categoryTitle}</h3>
                        {sceneNumber && (
                            <span className="bd-subtitle">
                                Scene {sceneNumber}
                                {sceneSetting && ` · ${sceneSetting}`}
                                {pageStart && ` · p.${pageStart}${pageEnd && pageEnd !== pageStart ? `-${pageEnd}` : ''}`}
                            </span>
                        )}
                    </div>
                    <button className="bd-close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                {/* Tabs */}
                <div className="bd-tabs">
```
with (note: the `bd-tabs` div is now the `subHeader` prop; it must be closed **before** `children`, so the existing `bd-tabs` closing `</div>` stays where it is and we open the `<Drawer>` + `subHeader={` before the tabs and insert `}` after the tabs' closing `</div>` in the next step):
```jsx
    return (
        <>
            <Drawer
                isOpen={isOpen}
                onClose={onClose}
                width="640px"
                title={categoryTitle}
                subtitle={sceneNumber && (
                    <>
                        Scene {sceneNumber}
                        {sceneSetting && ` · ${sceneSetting}`}
                        {pageStart && ` · p.${pageStart}${pageEnd && pageEnd !== pageStart ? `-${pageEnd}` : ''}`}
                    </>
                )}
                subHeader={
                    <div className="bd-tabs">
```

- [ ] **Step 3: Close the subHeader prop after the tabs block.** The `bd-tabs` div currently closes just before `{/* Content */}`:
```jsx
                    </button>
                </div>

                {/* Content */}
                <div className="bd-content">
```
Change it to close the `subHeader={…}` prop and open the Drawer children with the `bd-content` div unchanged:
```jsx
                    </button>
                </div>
                }
            >
                {/* Content */}
                <div className="bd-content">
```

- [ ] **Step 4: Close the `<Drawer>` where the panel div closed.** The `breakdown-drawer` panel `</div>` currently closes after `bd-content` (near line 863):
```jsx
                </div>
            </div>

            {/* Delete Item Confirmation */}
```
Change the panel-closing `</div>` to the Drawer close (leave the `bd-content` closing `</div>` as-is):
```jsx
                </div>
            </Drawer>

            {/* Delete Item Confirmation */}
```
(The two confirm blocks and the fragment stay for now; Task 3 removes them.)

- [ ] **Step 5: Remove the `if (!isOpen) return null;` early return** (currently line 419) so the primitive manages open/closed state. The pre-return computations (`totalItems`, `totalNotes`) operate on possibly-empty arrays and remain valid; the `<Drawer isOpen={isOpen}>` returns null internally when closed. If removing it causes a build/runtime problem (e.g. a computation dereferences a null prop only guarded by that return), instead KEEP the early return and leave `isOpen={isOpen}` — either is acceptable. Verify the data-fetch `useEffect` keyed on `isOpen` is unchanged.

- [ ] **Step 6: Reduce `.bd-content` and prune dead shell CSS** in `BreakdownDrawer.css`:
  - Change `.bd-content` (line ~142) from
    ```css
    .bd-content {
        flex: 1;
        overflow-y: auto;
        padding: 1rem 1.25rem;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }
    ```
    to
    ```css
    .bd-content {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }
    ```
  - Delete these now-dead rules entirely: `.drawer-backdrop` (7–13), `.breakdown-drawer` (21–35), `.breakdown-drawer.open` (37–39), `.bd-header` (45–53), `.bd-title-group h3` (55–60), `.bd-subtitle` (62–67), `.bd-close-btn` (69–77) and `.bd-close-btn:hover` (79–86).
  - **Keep** `@keyframes fadeIn` (15–18) — still used by `.bd-confirm-overlay` until Task 3.
  - **Keep** `.bd-tabs` and all `.bd-tab*` rules, `.bd-content` (reduced), and every inner content rule.

- [ ] **Step 7: Verify** — from `frontend/`:
```bash
grep -n "drawer-backdrop\|breakdown-drawer\|bd-header\|bd-close-btn\|bd-title-group\|bd-subtitle" src/components/breakdown/BreakdownDrawer.jsx
```
Expected: no output.
```bash
grep -n "<Drawer\|subHeader=\|bd-tabs\|bd-content" src/components/breakdown/BreakdownDrawer.jsx
```
Expected: `<Drawer`, `subHeader={`, the `bd-tabs` div (inside subHeader), and the `bd-content` div (as children).
```bash
grep -n "drawer-backdrop\|\.breakdown-drawer\|\.bd-header\|\.bd-close-btn\|\.bd-title-group\|\.bd-subtitle" src/components/breakdown/BreakdownDrawer.css
```
Expected: no output.
```bash
grep -n "overflow-y\|flex: 1" src/components/breakdown/BreakdownDrawer.css | grep -A0 "bd-content" ; grep -n -A4 "^.bd-content" src/components/breakdown/BreakdownDrawer.css
```
Expected: `.bd-content` no longer contains `overflow-y`/`flex: 1`/`padding`.
```bash
npm run build
```
Expected: succeeds.

- [ ] **Step 8: Commit**
```bash
git add frontend/src/components/breakdown/BreakdownDrawer.jsx frontend/src/components/breakdown/BreakdownDrawer.css
git commit -m "refactor(breakdown): convert BreakdownDrawer shell to <Drawer>

Replace the bespoke backdrop/panel/header with <Drawer width=640px> (title,
subtitle, tabs via the new subHeader slot); bd-content becomes the primitive's
scrolling body (scroll/padding reconciled). Gains Escape + scroll-lock + focus
via useOverlay; slide-in animation dropped to match the app's drawer standard.
Dead shell CSS pruned. Part of Phase 3 BreakdownDrawer conversion.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

### Task 3: Consolidate the two confirm dialogs onto `useConfirmDialog`

**Files:**
- Modify: `frontend/src/components/breakdown/BreakdownDrawer.jsx`
- Modify: `frontend/src/components/breakdown/BreakdownDrawer.css`

**Interfaces:**
- Consumes: `useConfirmDialog` from `'../../context/ConfirmDialogContext'` (existing, app-wide).

- [ ] **Step 1: Add the hook** — add the import near the other context imports:
```jsx
import { useConfirmDialog } from '../../context/ConfirmDialogContext';
```
and inside the component, add near the other hooks:
```jsx
    const { confirm } = useConfirmDialog();
```

- [ ] **Step 2: Delete the confirm state** — remove these two `useState` lines (currently 122 and 131):
```jsx
    const [deleteItemConfirm, setDeleteItemConfirm] = useState(null);
```
```jsx
    const [deleteNoteConfirm, setDeleteNoteConfirm] = useState(null);
```

- [ ] **Step 3: Clean `handleDeleteItem`** — remove the two `setDeleteItemConfirm(null);` lines (one in the try after `setRemovedItems`, one in the catch). Result:
```jsx
    const handleDeleteItem = async (itemId) => {
        try {
            await deleteSceneItem(itemId);
            // Move item from active to removed list (soft-delete)
            const removedItem = userItems.find(i => i.id === itemId);
            setUserItems(prev => prev.filter(i => i.id !== itemId));
            if (removedItem) {
                setRemovedItems(prev => [...prev, { ...removedItem, status: 'removed' }]);
            }
        } catch (err) {
            console.error('Error deleting item:', err);
            setError('Failed to delete item');
        }
    };
```

- [ ] **Step 4: Clean `handleDeleteNote`** — remove the two `setDeleteNoteConfirm(null);` lines. Result:
```jsx
    const handleDeleteNote = async (noteId) => {
        try {
            await deleteNote(noteId);
            setNotes(prev => prev.filter(n => n.id !== noteId));
        } catch (err) {
            console.error('Error deleting note:', err);
            setError('Failed to delete note');
        }
    };
```

- [ ] **Step 5: Add the two confirm-trigger handlers** — immediately after `handleDeleteNote`, add:
```jsx
    const handleDeleteItemClick = async (item) => {
        const ok = await confirm({
            title: 'Delete Item?',
            message: `"${item.item_name}" will be permanently removed. This action cannot be undone.`,
            variant: 'danger',
            confirmText: 'Delete'
        });
        if (!ok) return;
        await handleDeleteItem(item.id);
    };

    const handleDeleteNoteClick = async (note) => {
        const preview = note.content.substring(0, 50) + (note.content.length > 50 ? '...' : '');
        const ok = await confirm({
            title: 'Delete Note?',
            message: `"${preview}" will be permanently deleted. This action cannot be undone.`,
            variant: 'danger',
            confirmText: 'Delete'
        });
        if (!ok) return;
        await handleDeleteNote(note.id);
    };
```

- [ ] **Step 6: Rewire the trigger buttons.** Replace the delete-item trigger (line ~621):
```jsx
                                                                <button className="bd-action-btn delete" onClick={() => setDeleteItemConfirm({ id: item.id, name: item.item_name })} title="Delete">
```
with:
```jsx
                                                                <button className="bd-action-btn delete" onClick={() => handleDeleteItemClick(item)} title="Delete">
```
Replace the delete-note trigger (line ~789):
```jsx
                                                        <button className="bd-delete-btn" onClick={() => setDeleteNoteConfirm({ id: note.id, preview: note.content.substring(0, 50) + (note.content.length > 50 ? '...' : '') })}>
```
with:
```jsx
                                                        <button className="bd-delete-btn" onClick={() => handleDeleteNoteClick(note)}>
```

- [ ] **Step 7: Delete the two confirm JSX blocks** — remove the entire `{/* Delete Item Confirmation */} {deleteItemConfirm && (…)}` and `{/* Delete Note Confirmation */} {deleteNoteConfirm && (…)}` blocks (currently ~865–899). With them gone, the outer fragment now wraps only `<Drawer>…</Drawer>`; you may drop the `<>`/`</>` fragment wrapper and return the `<Drawer>` directly (optional — keeping the fragment is also valid).

- [ ] **Step 8: Prune the confirm CSS** — in `BreakdownDrawer.css`, delete the entire "Confirmation Modal" section: the comment header (line ~1074) through the end of `.bd-confirm-delete:hover` (line ~1162) — every `.bd-confirm-*` rule (`.bd-confirm-overlay`, `.bd-confirm-modal`, `.bd-confirm-icon`, `.bd-confirm-modal h4`, `.bd-confirm-name`, `.bd-confirm-warning`, `.bd-confirm-actions`, `.bd-confirm-cancel`(+hover), `.bd-confirm-delete`(+hover)). Then delete the now-orphaned `@keyframes fadeIn` (lines ~15–18) — after Task 2 removed `.drawer-backdrop`, this was its only other user. **Grep-confirm first** that `fadeIn` has no remaining reference:
```bash
grep -n "fadeIn" src/components/breakdown/BreakdownDrawer.css
```
Expected before deletion: only the `@keyframes fadeIn` definition line and (until you delete them) the `.bd-confirm-overlay` `animation: fadeIn …` line. After deleting both the confirm block and the keyframe: no output.

- [ ] **Step 9: Verify** — from `frontend/`:
```bash
grep -n "deleteItemConfirm\|deleteNoteConfirm\|bd-confirm" src/components/breakdown/BreakdownDrawer.jsx
```
Expected: no output.
```bash
grep -n "handleDeleteItemClick\|handleDeleteNoteClick\|useConfirmDialog" src/components/breakdown/BreakdownDrawer.jsx
```
Expected: the two handlers + the hook import/call present.
```bash
grep -n "bd-confirm\|fadeIn" src/components/breakdown/BreakdownDrawer.css
```
Expected: no output.
```bash
grep -n "Trash2\|<X " src/components/breakdown/BreakdownDrawer.jsx
```
Expected: `Trash2` still imported and used at the item/note rows; `<X` still at the `.bd-error` close (472) and line 559.
```bash
npm run build
```
Expected: succeeds.

- [ ] **Step 10: Commit**
```bash
git add frontend/src/components/breakdown/BreakdownDrawer.jsx frontend/src/components/breakdown/BreakdownDrawer.css
git commit -m "refactor(breakdown): consolidate confirm dialogs onto useConfirmDialog

Replace the two hand-rolled delete-item / delete-note confirm modals with the
shared useConfirmDialog context. Deletes the confirm state, the modal JSX, the
.bd-confirm-* CSS family, and the now-orphaned fadeIn keyframe. Handlers keep
their setError banner feedback. Completes the BreakdownDrawer conversion.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

## End-of-stream verification

After all 3 tasks, from `frontend/src`:
- `<Drawer>` gained `subHeader`; existing callers (TeamDrawer, StripDetailDrawer) render unchanged (no `subHeader` → `.ui-drawer-subheader` not emitted).
- BreakdownDrawer renders via `<Drawer subHeader={<div className="bd-tabs">…}>` at 640px; `grep -n "drawer-backdrop\|breakdown-drawer\|bd-confirm\|deleteItemConfirm\|deleteNoteConfirm" components/breakdown/BreakdownDrawer.jsx` returns nothing; `grep -n "\.drawer-backdrop\|\.breakdown-drawer\|\.bd-confirm\|fadeIn" components/breakdown/BreakdownDrawer.css` returns nothing.
- `npm run build` green.
- No test runner; live-drive login-gated. Correctness rests on build + per-task review + final whole-branch review + before/after that the drawer opens with a fixed header + fixed tab bar + scrolling content, tab switching works, tabs do NOT scroll with content, delete-item/delete-note still confirm and delete, Escape/backdrop close the drawer, and existing `<Drawer>` callers are visually unchanged.
