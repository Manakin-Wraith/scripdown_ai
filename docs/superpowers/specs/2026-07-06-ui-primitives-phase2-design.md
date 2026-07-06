# Phase 2 — Shared UI Primitives — Design

**Date:** 2026-07-06
**Status:** Approved
**Parent:** `docs/audits/2026-07-06-ui-consistency-audit.md` (roadmap Phase 2)
**Goal:** Build a set of shared, token-driven UI primitives in `components/ui/`, and prove the APIs by adopting them in one real domain (the scenes modal cluster) plus consolidating ConfirmDialog.

## Decisions (locked)

- **Scope:** build all six primitives **and** adopt them in one domain as proof (not build-only).
- **Set:** all six — Button, Spinner, Modal, Drawer, EmptyState, Badge.
- **ConfirmDialog:** consolidate this phase — rebuild the canonical context dialog on Modal, delete the `common/` duplicate.
- **Language/convention:** plain JSX + JSDoc (no TypeScript), matching the codebase.
- **Location:** new `components/ui/` folder with a barrel `index.js`.
- **Tokens:** primitives consume only the Phase 1 token scales — zero hardcoded colors/spacing/radii/z-index in new CSS.

## Architecture

`components/ui/` contains one file pair per primitive (`Button.jsx` + `Button.css`, …), a shared hook `useOverlay.js`, and `index.js` (barrel export). Modal and Drawer both use `useOverlay`, which owns all cross-cutting overlay behavior so it is written once:

- Escape-to-close (document keydown, cleaned up on unmount)
- Focus trap: focus first focusable (or the close button) on open; restore focus to the previously-focused element on close
- Body scroll-lock while open
- Portal rendering into `document.body`

## Component APIs

### `<Button>`
```
variant: 'primary' | 'secondary' | 'danger' | 'ghost'  (default 'primary')
size: 'sm' | 'md'  (default 'md')
loading: boolean        // shows Spinner, disables, holds width
disabled: boolean
icon: LucideIcon        // optional leading/trailing icon component
iconPosition: 'left' | 'right'  (default 'left')
fullWidth: boolean
type, onClick, ...rest  // forwarded to <button>
```
Renders `<button class="ui-btn ui-btn--{variant} ui-btn--{size}">`. Classes only; no inline styles. Visual grounded in the existing common button (flex, gap `--space-2`, padding, `--radius-lg`, `--text-sm`, weight 500).

### `<Spinner>`
```
size: number  (default 16)
label: string  (default 'Loading')  // aria-label
className: string
```
Wraps lucide `Loader2` with a single `@keyframes ui-spin` in `Spinner.css`. `role="status"`. Becomes the canonical spinner; Phase 3 removes the 47 duplicated keyframes.

### `<Modal>`
```
isOpen: boolean
onClose: () => void
title: string | node
size: 'sm' | 'md' | 'lg'  (default 'md')
footer: node             // optional action row
showClose: boolean  (default true)
closeOnOverlay: boolean  (default true)
closeOnEscape: boolean  (default true)
children: node           // body
```
Portal + `.ui-modal-overlay` (z `--z-modal`) + `.ui-modal ui-modal--{size}`. Header (title + close X), body, optional footer. `role="dialog"`, `aria-modal`, `aria-labelledby`. Overlay click closes (container stops propagation). Uses `useOverlay`.

### `<Drawer>`
```
isOpen, onClose
title, subtitle: string | node
side: 'right' | 'left'  (default 'right')
width: string  (default '480px')
footer: node
showClose: boolean  (default true)
children: node
```
Portal + `.ui-drawer-backdrop` (z `--z-drawer`) + sliding `.ui-drawer ui-drawer--{side}`. Header markup mirrors the current `.drawer-header`/`.drawer-title-group` so Phase 3 migration of NoteDrawer/TeamDrawer/BreakdownDrawer is mechanical. Uses `useOverlay`.

### `<EmptyState>`
```
icon: LucideIcon
title: string
message: string | node
action: node        // usually a <Button>
size: 'sm' | 'md'  (default 'md')
```
Centered icon + title + message + optional action. Replaces ~25 ad-hoc empty states.

### `<Badge>`
```
variant: 'neutral' | 'primary' | 'success' | 'warning' | 'danger' | 'info'  (default 'neutral')
size: 'sm' | 'md'  (default 'sm')
dot: boolean        // leading status dot
icon: LucideIcon
children: node      // label
```
Pill; each variant maps to token pairs (e.g. success → `--success-bg` / `--success`). Replaces ~30 badge classes.

## ConfirmDialog consolidation

- Rewrite the inner `ConfirmDialog` component in `context/ConfirmDialogContext.jsx` to render on `<Modal>` with `<Button>` actions. The public `confirm({title, message, variant, confirmText, cancelText})` promise API stays **identical** — no consumer changes.
- Confirm actions use `--z-confirm` (1100), above Modal (1010), so a confirm raised from within another modal still stacks correctly.
- Delete `components/common/ConfirmDialog.{jsx,css}`. First verify its consumers (audit says admin-only) and repoint them to `useConfirmDialog()` or the new Modal.

## Proof-of-adoption (this phase only)

Convert the scenes modal cluster to the new primitives and delete their bespoke overlay/button CSS from `SceneModals.css`:

- `AddSceneModal`, `SceneSplitModal`, `SceneMergeModal`, `MultiMergeModal`, `SceneEditor` form modal → `<Modal>` + `<Button>`.
- Convert 1–2 scene-area empty states → `<EmptyState>` and 1–2 scene status pills → `<Badge>` to exercise those primitives.

Everything else (the other ~8 modals, all drawers, remaining badges/empties) stays on existing CSS until Phase 3. **Correction to the audit roadmap:** Phase 2 does not migrate all 13 modals — only the scenes cluster; the rest are Phase 3.

## Verification & testing

The frontend has **no test runner** (no vitest/jest; `tests/` is backend Python). This phase does not stand one up — a vitest + React Testing Library harness is noted as a recommended follow-up, explicitly out of scope here rather than silently skipped.

Verification this phase:
1. `npm run build` (vite) green.
2. Local `npm run dev`: drive the converted scenes flow — open Add Scene, Split, Merge; confirm submit shows Button `loading`; confirm Escape and overlay-click now close these modals (they previously did not); confirm the delete-scene ConfirmDialog still works. If local login blocks a live drive, fall back to build + component review and flag it.

## Success criteria

- `components/ui/` exports all six primitives + `useOverlay`, consuming only tokens.
- Scenes modal cluster renders and behaves via the new primitives with dismissal working; their bespoke overlay/button CSS is removed.
- One ConfirmDialog remains (context, on Modal); the `common/` duplicate is deleted; all its former consumers still work.
- Build is green.
