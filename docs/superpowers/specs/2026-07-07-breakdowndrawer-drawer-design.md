# BreakdownDrawer → `<Drawer>` — Design

**Date:** 2026-07-07
**Status:** Approved (design)
**Parent:** `docs/audits/2026-07-06-ui-consistency-audit.md` (Phase 2/3 — shared primitives; overlays via shared shells). Deferred from Stream B3b (Drawer adoption) because BreakdownDrawer is a 904-line component with a bespoke shell, a fixed sub-nav (tabs), and two hand-rolled confirm dialogs. This converts it.
**Goal:** Migrate BreakdownDrawer's bespoke drawer shell to the shared `<Drawer>` primitive and its two `bd-confirm-*` dialogs to `useConfirmDialog`, preserving the fixed header + fixed tab bar + scrolling content layout, with one small reusable primitive enhancement.

## Context

`components/breakdown/BreakdownDrawer.jsx` renders a bespoke drawer: `<div className="drawer-backdrop">` + `<div className="breakdown-drawer">` (640px, `position:fixed`, `flex-direction:column`, slide-in via `right:-640px→0`) containing a fixed `bd-header` (title `<h3>{categoryTitle}</h3>` + `bd-subtitle` composite), a fixed `bd-tabs` bar, and a scrolling `bd-content` (`flex:1; overflow-y:auto`). It registers no Escape listener (only backdrop/close `onClick`). Two bespoke confirm dialogs (`bd-confirm-*`: delete item, delete note) sit at the end of the fragment. The file imports neither `useToast` nor `useConfirmDialog`; delete failures surface via a shared `error` string rendered in an inline `.bd-error` banner.

The `<Drawer>` primitive (`components/ui/Drawer.jsx`) renders a portal'd backdrop + panel with a header (title/subtitle/close via `useOverlay`: Escape + scroll-lock + focus-restore) and a **single** scrolling `ui-drawer-body`. It has no slot between the header and the body — so BreakdownDrawer's **fixed tab bar** would scroll away if dropped into the body. The primitive needs a small `subHeader` slot.

## Task 1 — `<Drawer>` `subHeader` enhancement

Add an optional `subHeader` node rendered as a fixed (`flex-shrink:0`) region between the header and the scrolling body:
- `Drawer.jsx`: add `subHeader` to the JSDoc (`subHeader?: React.ReactNode`) and destructure it; render between the header block and `ui-drawer-body`:
  ```jsx
  {subHeader && <div className="ui-drawer-subheader">{subHeader}</div>}
  <div className="ui-drawer-body">{children}</div>
  ```
- `Drawer.css`: add `.ui-drawer-subheader { flex-shrink: 0; }` (no padding — subheader content is edge-to-edge and brings its own borders/layout).
- **Invariant:** additive only. Existing callers (TeamDrawer, StripDetailDrawer) pass no `subHeader`, so their rendered output is byte-identical (the conditional renders nothing).

## Task 2 — Convert the shell

Replace the bespoke backdrop + panel + header with the primitive:
```jsx
<Drawer
    isOpen={isOpen}
    onClose={onClose}
    width="640px"
    title={categoryTitle}
    subtitle={sceneNumber && (
        <>Scene {sceneNumber}{sceneSetting && ` · ${sceneSetting}`}{pageStart && ` · p.${pageStart}${pageEnd && pageEnd !== pageStart ? `-${pageEnd}` : ''}`}</>
    )}
    subHeader={
        <div className="bd-tabs">
            {/* existing Items/Notes tab buttons verbatim */}
        </div>
    }
>
    <div className="bd-content">
        {/* existing content verbatim */}
    </div>
</Drawer>
```
Decisions:
- **Title as string:** pass `categoryTitle` as a plain string (not wrapped in `<h3>`) so the primitive's `.ui-drawer-title` styling applies without a nested-heading margin. Drop the bespoke `.bd-header h3` rule.
- **Subtitle:** pass the existing `sceneNumber && (…)` composite directly to `subtitle` (the primitive's `subtitle` accepts `React.ReactNode`); drop the bespoke `.bd-subtitle` span/rule.
- **`bd-content` scroll/padding (Path Y):** the primitive's `ui-drawer-body` is now the sole scroll region and supplies padding (`var(--space-6)` = 1.5rem). Reduce `.bd-content` to layout-only: `{ display:flex; flex-direction:column; gap:0.75rem; }` — remove its `flex:1`, `overflow-y:auto`, and `padding`. (Intended minor change: content padding 1rem/1.25rem → 1.5rem, matching other drawers.)
- **Open/close:** pass `isOpen={isOpen}`; the primitive returns null when closed and manages Escape/scroll-lock/focus. Remove BreakdownDrawer's own `if (!isOpen) return null;` early return **only if** the pre-return computations (`totalItems`, `totalNotes`, `categoryTitle`) remain valid when closed (they operate on possibly-empty arrays/props — safe); otherwise keep the guard and pass `isOpen={isOpen}`. Either is acceptable as long as the data-fetch `useEffect` keyed on `isOpen` is unchanged.
- **No slide-in animation:** the primitive appears/unmounts instantly, consistent with every other converted drawer (TeamDrawer, StripDetailDrawer) post-B3b. The bespoke `right:-640px→0` transition is dropped by design.
- **Remove** the now-unused `X` lucide import only if it is no longer used elsewhere in the file (the primitive supplies its own close button; verify `X` has no other use before removing).
- **Prune** now-dead shell CSS: `.drawer-backdrop`, `.breakdown-drawer`, `.breakdown-drawer.open`, `.bd-header`, `.bd-title-group`, `.bd-header h3`, `.bd-subtitle`, `.bd-close-btn` (+ `:hover`). **Keep** `.bd-tabs`, `.bd-content` (reduced), and all inner content rules (`.bd-tab`, `.bd-tab-count`, `.bd-item`, `.bd-note`, `.bd-error`, etc.). **Keep** the `fadeIn` keyframe for now — the `bd-confirm-overlay` still references it until Task 3.

## Task 3 — Consolidate the two confirm dialogs

Identical pattern to the TeamDrawer B5 consolidation:
- Add `import { useConfirmDialog } from '../../context/ConfirmDialogContext';` + `const { confirm } = useConfirmDialog();`.
- Delete the `deleteItemConfirm`/`deleteNoteConfirm` `useState` declarations.
- Rewire the two triggers:
  - delete-item button `onClick={() => setDeleteItemConfirm({ id, name })}` → `onClick={() => handleDeleteItemClick(item)}` where:
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
    ```
  - delete-note button `onClick={() => setDeleteNoteConfirm({ id, preview })}` → `onClick={() => handleDeleteNoteClick(note)}` where:
    ```jsx
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
- Strip the `setDeleteItemConfirm(null)` / `setDeleteNoteConfirm(null)` lines from `handleDeleteItem`/`handleDeleteNote` (both success and catch branches); keep the rest of each handler (API call, state updates, `console.error` + `setError('Failed to delete …')`). No new toasts — the `error` banner already surfaces failures.
- Delete the two `{deleteItemConfirm && (…)}` / `{deleteNoteConfirm && (…)}` JSX blocks.
- **Prune** the contiguous `.bd-confirm-*` CSS block (delete-item/note confirm family) **plus the `fadeIn` keyframe**, which — after Task 2 removed `.drawer-backdrop` — is now referenced only by the removed confirm overlay. Grep-confirm `fadeIn` has no remaining reference in `BreakdownDrawer.css` before deleting it.
- Remove the `Trash2` lucide import only if it is no longer used elsewhere in the file after the modal JSX is deleted (verify — item/note rows may still use `Trash2`; if so, keep it).

## Out of scope

- No copy changes beyond folding the confirm name/preview into the single `message` string.
- No new toast feedback (the `error` banner is retained).
- No changes to the breakdown content logic, data fetching, or the item/note rendering beyond the shell/confirm swaps.
- No changes to other drawers or `bd-confirm-*` families in other files (BreakdownDrawer's copy is self-contained).

## Verification

- Per task: `npm run build` from `frontend/` green.
- Task 1 invariant: existing `<Drawer>` usages render unchanged (no `subHeader` passed → `.ui-drawer-subheader` not emitted); `grep -n "subHeader" components/ui/Drawer.jsx` shows the prop + conditional.
- Task 2 invariants: `grep -n "drawer-backdrop\|breakdown-drawer\|bd-header\|bd-close-btn" components/breakdown/BreakdownDrawer.jsx` returns nothing; the file imports and renders `<Drawer`; `.bd-tabs` passed as `subHeader`; `.bd-content` reduced (no `overflow-y` / `flex: 1`); pruned shell CSS classes gone from `BreakdownDrawer.css`; `.bd-tabs`/`.bd-content`/inner rules retained.
- Task 3 invariants: `grep -n "deleteItemConfirm\|deleteNoteConfirm\|bd-confirm" components/breakdown/BreakdownDrawer.jsx` returns nothing; `confirm` from `useConfirmDialog` used by both trigger handlers; `grep -n "bd-confirm\|@keyframes fadeIn\|fadeIn" components/breakdown/BreakdownDrawer.css` returns nothing.
- No test runner; live-drive login-gated. Correctness rests on build + per-task review + final whole-branch review + before/after that: the drawer opens with a fixed header + fixed tab bar + scrolling content; tab switching still works; the tabs do NOT scroll with content; delete-item and delete-note still confirm and delete; Escape/backdrop close the drawer; and existing `<Drawer>` callers are visually unchanged.

## Execution

Full subagent-driven-development on branch `phase3-breakdowndrawer-drawer`. Three tasks (primitive enhancement → shell conversion → confirm consolidation), per-task spec+quality review, final whole-branch review, then merge (push on command).

## Success criteria

- `<Drawer>` gains a reusable `subHeader` slot; existing callers unchanged.
- BreakdownDrawer renders via `<Drawer subHeader={tabs}>` at 640px with the fixed-header + fixed-tabs + scrolling-content layout preserved; slide animation intentionally dropped to match the app standard.
- The two `bd-confirm-*` dialogs are replaced by `useConfirmDialog`; the bespoke shell + confirm CSS families and the orphaned `fadeIn` keyframe are removed; retained inner CSS is intact.
- Build green; work lands as three reviewed commits.
