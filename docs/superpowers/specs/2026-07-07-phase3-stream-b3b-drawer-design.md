# Phase 3 · Stream B3b — Drawer Adoption — Design

**Date:** 2026-07-07
**Status:** Approved (design)
**Parent:** `docs/audits/2026-07-06-ui-consistency-audit.md` (Phase 2/3 — shared primitives). Stream B by primitive: B1 Spinner (merged), B2 Button (merged), B3 Modal/Drawer — **B3a Modal merged**, **B3b Drawer (this)**; then B4 Badge/EmptyState, B5 interaction rules.
**Goal:** Adopt the shared `<Drawer>` primitive for the app's bespoke backdrop-side-drawer components, and delete the dead drawer discovered during scoping. This is the `<Drawer>` primitive's first real use.

## Context

B3 targets the two overlay primitives. B3a converted the modals; B3b converts the drawers. The `<Drawer>` primitive (`components/ui/Drawer.jsx`, backed by `components/ui/useOverlay.js`) is **currently unused** — B3b proves it, so scope is deliberately conservative: convert the drawers that genuinely fit the primitive's pattern (a full-height, backdrop-dimmed side panel with a header/body), delete dead code, and leave outliers alone.

### The 5 "drawers" and their disposition

| Component | Lines (jsx/css) | Renderer | Pattern | Disposition |
| --- | --- | --- | --- | --- |
| `components/team/TeamDrawer.jsx` | 495 / 526 | `ScriptHeader` | backdrop side-panel; title + subtitle header | **Convert** |
| `components/board/StripDetailDrawer.jsx` | 200 / 396 | `ZoomableStripboard` | backdrop side-panel; conditionally mounted (no `isOpen`); rich header w/ `timeline-*` badges | **Convert** |
| `components/notes/NoteDrawer.jsx` | 487 / 682 | *(none)* | — | **Delete (dead)** |
| `components/feedback/FeedbackDrawer.jsx` | 341 / 403 | `FeedbackButton` | **anchored popover** — `anchorRef` + click-outside, no backdrop | **Exclude (wrong pattern)** |
| `components/breakdown/BreakdownDrawer.jsx` | 912 / 1183 | `SceneDetail` | backdrop side-panel; 2 nested `.bd-confirm-overlay` dialogs | **Defer (heavy follow-up)** |

`NoteDrawer` is a superseded near-clone of `BreakdownDrawer` (same `CATEGORY_DEPARTMENTS`/`DEPARTMENT_ICONS` department-notes UI) with zero renderers — dead, like B3a's dead modals.

`FeedbackDrawer` is not a backdrop side-drawer: it positions off an `anchorRef` and dismisses on click-outside (a popover). Forcing it onto `<Drawer>` would change its UX; it is self-contained (`.feedback-drawer`, no shared classes), so excluding it costs nothing.

`BreakdownDrawer` fits the pattern but is by far the largest and carries two nested internal confirm-overlay dialogs; it defines its own `.drawer-backdrop` and uses a self-contained `bd-*` namespace, so it can be converted independently later without cascade impact.

## `<Drawer>` primitive API (target)

`Drawer({ isOpen, onClose, title, subtitle, side='right', width='480px', footer, showClose=true, children })` → `createPortal` to `document.body`; renders `.ui-drawer-backdrop` (click-to-close), a `.ui-drawer.ui-drawer--{side}` panel with inline `style={{ width }}`, an optional `.ui-drawer-header` (`.ui-drawer-title` + `.ui-drawer-subtitle` + X close), a `.ui-drawer-body` for `children`, and an optional `.ui-drawer-footer`. `useOverlay` supplies Escape-to-close, body scroll-lock, and focus-restore. `title`/`subtitle` accept ReactNodes.

## Scope

**In:**
- **Convert** `TeamDrawer` and `StripDetailDrawer` to `<Drawer>` (markup + CSS pruning).
- **Delete** dead `NoteDrawer` (`.jsx` + `.css`), with the cascade relocation described below.

**Out:**
- `FeedbackDrawer` (wrong pattern) and `BreakdownDrawer` (deferred) — untouched.
- The 2 inline `.confirm-overlay` dialogs inside TeamDrawer are **preserved** (kept working), not migrated to `useConfirmDialog` — that consolidation is Stream B5's job.
- Bespoke non-generic buttons inside these drawers — kept as children; not `<Button>` targets in this stream.
- Other primitives (B4, B5).

## Conversion approach

The primitive supplies backdrop, panel, header chrome (title/subtitle/X), Escape, scroll-lock, and focus-restore. Each drawer's content moves into `children`; its bespoke backdrop/panel/header-chrome CSS is pruned; content-specific CSS is kept.

### TeamDrawer (`components/team/TeamDrawer.jsx` / `.css`) — cleanest fit
- Already `({ isOpen, onClose, scriptId, isOwner, scriptTitle, … })` returning `null` when `!isOpen`. Its header — `<h3><Users size={18}/> Team Members</h3>` + `<span className="drawer-subtitle">{scriptTitle}</span>` — maps directly to the primitive: `<Drawer isOpen={isOpen} onClose={onClose} side="right" width="420px" title={<><Users size={18}/> Team Members</>} subtitle={scriptTitle}>`. Drop the manual `if (!isOpen) return null` (the primitive handles it) — but retain it if other early logic depends on it; otherwise remove.
- The `.drawer-content` body markup (loading/error/team-sections) moves into `children`; `.drawer-content` wrapper is dropped (the primitive's `.ui-drawer-body` provides padding/scroll).
- **Confirm-overlay wrinkle:** TeamDrawer renders two inline `.confirm-overlay` blocks and the nested `<InviteModal>` as siblings after the drawer, inside the return fragment. Keep them as siblings of `<Drawer>` in the fragment. Their variant CSS uses the sibling combinator `.team-drawer ~ .confirm-overlay …` (e.g. `.confirm-icon.danger`, `.confirm-name`, `.confirm-delete.warning`) — because `.team-drawer` no longer exists after conversion, **rewrite those selectors to plain `.confirm-overlay …`** so the confirm dialogs keep their styling. The base `.confirm-overlay` rule (TeamDrawer.css) stays.
- **Cascade relocation:** TeamDrawer's body uses `.drawer-loading` and `.drawer-error`, whose rules are defined **only** in `NoteDrawer.css` (about to be deleted). Copy those two rule blocks into `TeamDrawer.css` so they survive. (`.drawer-content`/`.drawer-title-group`/`.drawer-subtitle` are also NoteDrawer-only, but TeamDrawer stops using them after conversion — the primitive supplies `.ui-drawer-body`/`.ui-drawer-title`/`.ui-drawer-subtitle`.)
- Prune from `TeamDrawer.css`: `.team-drawer` (panel), `.drawer-header`, `.close-btn`, and the stale `/* reuses backdrop from NoteDrawer */` comment. Keep the team-section/member/role content styles and the (de-sibling-ed) confirm-overlay styles.

### StripDetailDrawer (`components/board/StripDetailDrawer.jsx` / `.css`) — medium
- Conditionally mounted by `ZoomableStripboard` (rendered only when a strip is selected) with **no `isOpen` prop** — pass `isOpen` (always true while mounted) to `<Drawer>`; `ZoomableStripboard` is otherwise unchanged.
- **Remove its bespoke Escape `useEffect`** (lines ~14-21) — the primitive's `useOverlay` provides Escape-to-close.
- Its header is rich and interactive (scene number, INT/EXT badge, time-of-day, and the editable story-day controls). Pass the existing header markup through the primitive's `title` slot as a ReactNode, and drop the bespoke `.drawer-close-btn` in favor of the primitive's X (`showClose` default). **The story-day controls contain `timeline-*` badge classes (`.drawer-day-badge timeline-<code>`) — preserve those classes and their values verbatim; never modify any `timeline-` rule (Stream A guard).**
- `width="400px"`; body sections (`.drawer-section`, `.drawer-setting`, atmosphere, etc.) move into `children`.
- Prune from `StripDetailDrawer.css`: `.drawer-backdrop`, `.strip-detail-drawer` (panel), and the `.drawer-header` chrome now supplied by the primitive. Keep all content/section/badge styles, especially every `timeline-*` rule.

### Delete NoteDrawer
- Delete `components/notes/NoteDrawer.jsx` and `components/notes/NoteDrawer.css`. Safe because its exported classes (`.drawer-content`, `.drawer-title-group`, `.drawer-subtitle`, `.drawer-loading`, `.drawer-error`, plus a `.drawer-header`/`.drawer-backdrop` def) have exactly one live consumer — TeamDrawer — which is converted first and has `.drawer-loading`/`.drawer-error` relocated into its own CSS. `DepartmentNotesSection` (the other file in `components/notes/`) is unrelated and stays.

## Execution

Three independently reviewable tasks, in this order (so no class is stripped while still in use):

1. **Convert TeamDrawer** → `<Drawer>`; de-sibling the `.confirm-overlay` rules; relocate `.drawer-loading`/`.drawer-error` into `TeamDrawer.css`.
2. **Convert StripDetailDrawer** → `<Drawer>`; remove bespoke Escape; preserve `timeline-*` badges.
3. **Delete NoteDrawer** (`.jsx`+`.css`); remove the stale NoteDrawer comment in `TeamDrawer.css`.

Each task is one commit.

## Verification

- Per task: `npm run build` green.
- Conversion invariants (from `frontend/src`):
  - `TeamDrawer.jsx` and `StripDetailDrawer.jsx` each import `Drawer` from `../ui` and render `<Drawer`.
  - No `.team-drawer`/`.strip-detail-drawer` panel classes or `.drawer-backdrop` remain in those two JSX files.
  - `.confirm-overlay` styling in `TeamDrawer.css` no longer depends on the `.team-drawer ~` sibling combinator.
  - `.drawer-loading` and `.drawer-error` are defined in `TeamDrawer.css` (relocated).
- Deletion invariant: `grep -rn "NoteDrawer" frontend/src --include="*.jsx" --include="*.js"` returns nothing; `.drawer-content`/`.drawer-title-group`/`.drawer-subtitle` are no longer referenced by any live JSX.
- No test runner; live-drive login-gated (as in prior streams). Correctness rests on build + per-task review + these invariants + careful before/after of each drawer's open/close wiring. Intended new behavior: Escape-to-close, scroll-lock, and focus-restore now apply to both drawers (they lacked scroll-lock/focus-restore before; StripDetailDrawer had a bespoke Escape now replaced by the primitive's).

## Success criteria

- `TeamDrawer` and `StripDetailDrawer` render via `<Drawer>`; backdrop, header, X close, Escape, scroll-lock, and focus-restore are unified across them.
- Dead `NoteDrawer` is removed; the deletion invariant passes and no leeched class is left unstyled.
- TeamDrawer's two inline confirm dialogs and its nested `<InviteModal>` still render and are styled correctly.
- StripDetailDrawer's `timeline-*` badges are visually unchanged.
- Build green; work lands as three reviewed commits.
- `<Drawer>` primitive is proven; `FeedbackDrawer` (popover) and `BreakdownDrawer` (deferred) remain cleanly separable follow-ups.
