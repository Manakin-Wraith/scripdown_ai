# Phase 3 · Stream B4a — EmptyState Adoption — Design

**Date:** 2026-07-07
**Status:** Approved (design)
**Parent:** `docs/audits/2026-07-06-ui-consistency-audit.md` (Phase 2/3 — shared primitives; C5 "Empty states — ~25 ad-hoc versions"). Stream B by primitive: B1 Spinner, B2 Button, B3a Modal, B3b Drawer (all merged); **B4 EmptyState/Badge** — split into **B4a EmptyState (this)** + B4b Badge (later). Then B5 interaction rules.
**Goal:** Adopt the shared `<EmptyState>` primitive for the app's ad-hoc "no-data placeholder" blocks, keeping each placeholder's existing copy verbatim.

## Context

The audit found ~25 ad-hoc empty-state implementations — `.empty-state` plus feature-prefixed reinventions (`.bd-empty`, `.board-empty-state`, `.stripboard-empty`, `.drawer-empty`, …) with divergent structure and mixed copy. The `<EmptyState>` primitive (`components/ui/EmptyState.jsx`) already exists and is **proven** in `components/scenes/SceneList.jsx` (`<EmptyState icon={FileText} title="No scenes found" />`). B4a converts the remaining in-scope placeholder blocks to it.

B4 is split by primitive because the two halves differ sharply in nature: empty states are a uniform "centered icon + heading + optional message/action" pattern that maps cleanly onto `<EmptyState>`, whereas badges (B4b) are a heterogeneous surface (status pills, dynamic-color department/role badges, the Stream-A-guarded `timeline-*` badges, numeric count chips) where only a subset maps to the primitive's fixed variants. B4a is the clean, low-risk half and runs first.

## `<EmptyState>` primitive API (target)

`EmptyState({ icon, title, message, action, size='md' })` → `.ui-empty.ui-empty--{size}` block containing an optional `.ui-empty-icon` (renders `<Icon size={size==='sm'?28:40} />`), a required `.ui-empty-title`, an optional `.ui-empty-message`, and an optional `.ui-empty-action`. `icon` is a component reference (e.g. `FileText`), not an element; `title` is a string; `message`/`action` are ReactNodes. Size `sm` for compact contexts (popovers, columns), `md` for full-panel placeholders.

## Scope

**In — convert genuine "no-data placeholder" blocks** (a centered icon + heading + optional message/action) to `<EmptyState>`, across these in-scope files:

| Domain | File(s) | Bespoke class |
| --- | --- | --- |
| scenes | `components/scenes/FilteredSceneList.jsx`, `components/scenes/SceneDetail.jsx` | `scene-detail-empty` |
| scenes | `components/scenes/CharacterList.jsx`, `components/scenes/LocationList.jsx` | `list-empty` |
| scenes | `components/scenes/CharacterDashboard.jsx`, `components/scenes/LocationDashboard.jsx` | `dashboard-empty` |
| reports | `components/reports/Stripboard.jsx` | `breakdown-empty`, `stripboard-empty` |
| board | `components/board/BoardCanvas.jsx` | `board-empty-state` |
| board | `components/board/SchedulePopover.jsx` | `sp-empty` |
| schedule | `components/schedule/ShootingSchedulePage.jsx` | `schedule-empty` |
| schedule | `components/schedule/DayColumn.jsx` | `kanban-col-empty` |
| notifications | `components/notifications/NotificationBell.jsx` | `notification-empty` |
| breakdown | `components/breakdown/BreakdownDrawer.jsx` | `bd-empty` |

**Per-instance verification (binding):** each listed block must be confirmed a real placeholder (icon + heading, optionally message/action) before conversion. If an instance turns out to be an inline hint rather than a placeholder block, **skip it** and note the skip — do not force it into the primitive.

**Out:**
- **Excluded areas:** all `components/admin/*` and `pages/Admin/*` (charts, analytics, payments, user activity, email campaigns), `components/campaigns/*` (`tlp-empty`), and the frozen WIP components (`SceneManager`, `DepartmentWorkspace`, `ShootingScriptPreview`, `CharacterProfile`, `SettingsPage`, `ScriptEditorPage`).
- **Inline hints (not the primitive's pattern):** `components/reports/ReportFilterPanel.jsx` `dropdown-empty` (in-dropdown "no options"), `multi-select-placeholder`, and one-word `drawer-empty` ("None"/"—").
- **Copy unification:** existing title/message text is kept **verbatim**; no wording changes (a possible later pass).
- **Badges (B4b)** and other primitives.

## Conversion approach

Per placeholder block:
- Replace the bespoke markup (e.g. `<div className="board-empty-state"><Icon/><h3>…</h3><p>…</p></div>`) with `<EmptyState icon={Icon} title="…" message={…} action={…} size={…}/>`, moving the icon component into `icon`, the heading text into `title`, the secondary line into `message`, and any button/link into `action`. Choose `size="sm"` for compact hosts (popover, kanban column, notification dropdown), `size="md"` otherwise.
- Add `import { EmptyState } from '<rel>/ui';` (or extend an existing `../ui` import). Remove now-unused icon imports only if truly unused.
- Where the bespoke block sat inside a positioning wrapper (centering in a panel/canvas), keep that wrapper if the layout needs it; the primitive renders the inner content.
- Prune the block's now-dead CSS (`.board-empty-state`, `.board-empty-icon`, `.bd-empty`, `.stripboard-empty`, `.breakdown-empty`, `.scene-detail-empty`, `.list-empty`, `.dashboard-empty`, `.schedule-empty`, `.kanban-col-empty`, `.notification-empty`, `.sp-empty`/`.sp-empty-msg`, plus their icon/title/message descendants) once the block is converted. Keep any wrapper/positioning rule still used.

## Execution

Per-domain batches, each an independently reviewable commit:
1. **scenes** — FilteredSceneList, SceneDetail, CharacterList, LocationList, CharacterDashboard, LocationDashboard.
2. **reports + breakdown** — Stripboard, BreakdownDrawer.
3. **board** — BoardCanvas, SchedulePopover.
4. **schedule** — ShootingSchedulePage, DayColumn.
5. **notifications** — NotificationBell.

(Batches may be merged where small; each ends with a build-green, reviewable commit.)

## Verification

- Per batch: `npm run build` green.
- Invariants (from `frontend/src`):
  - Each converted file imports `EmptyState` from the `ui` barrel and renders `<EmptyState`.
  - The converted bespoke placeholder classes no longer appear in the converted JSX, and their CSS rule families are removed (or the class is documented as an intentionally-kept wrapper).
  - Excluded-area and inline-hint empty states are untouched.
- No test runner exists; live-drive is login-gated (as in prior streams). Correctness rests on build + per-batch review + the invariants + before/after of each placeholder's copy (must be verbatim) and layout. Intended change: unified empty-state chrome (icon size, spacing, typography) across the converted blocks — the point of the primitive.

## Success criteria

- The in-scope ad-hoc empty-state placeholders render via `<EmptyState>` with their original copy intact.
- The corresponding bespoke empty-state CSS families are removed; no orphaned rules or classes remain in the converted files.
- Inline hints, excluded areas, and WIP components are untouched.
- Build green; work lands as per-domain reviewed commits.
- `<EmptyState>` is broadly adopted; B4b Badge remains a cleanly separable follow-up.
