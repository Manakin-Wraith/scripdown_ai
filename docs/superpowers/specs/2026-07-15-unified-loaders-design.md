# Unified Loading System — Skeleton + Spinner Consistency

**Date:** 2026-07-15
**Status:** Approved design, pre-implementation
**Branch:** `feat/unified-loaders`

## Problem

The frontend has three inconsistent loader idioms and no skeleton loaders at all:

1. Canonical `<Spinner>` (`src/components/ui/Spinner.jsx`) — used in some places.
2. Ad-hoc lucide `<Loader className="spin">` — SceneManager, ProtectedRoute, AuthModal, DepartmentSelector, ForgotPasswordModal, DepartmentWorkspace.
3. Pure-CSS `className="spinner"` / `spinner-sm` divs — SceneViewer, AdminRoute, ScriptsChart, UserGrowthChart.

Separately, several async user actions show **no loading feedback at all** — they only disable buttons while a network write is in flight. The most visible gaps are around **story-day changes** and **segment operations**, which mutate silently and (for story days) trigger invisible cross-view refetches.

## Goals

1. **One spinner idiom** app-wide: standardize on `<Spinner>` for all action/inline/button loading.
2. **A skeleton primitive** for initial content (panel/list) loads.
3. **Close the loading-feedback gaps** on story-day and segment operations.

Non-goals: reworking toasts, changing the drag-reorder optimistic model on the board, adding skeletons to flows that already load fine.

## Design

### 1. Primitives (`src/components/ui/`)

**`<Spinner>`** — unchanged. Remains the canonical animated loader (`Loader2` + `ui-spin` keyframe, `role="status"`, `aria-label`).

**`<Skeleton>`** — new. Grey shimmer placeholder for initial content loads.

- New files: `Skeleton.jsx`, `Skeleton.css`.
- CSS: a shimmer keyframe (animated gradient sweep) that degrades to a static grey block under `@media (prefers-reduced-motion: reduce)`.
- Props: `width`, `height`, `radius`, `className`. Defaults sized for a text-line block.
- Colocated preset in the same file: **`SkeletonList`** — renders `count` stacked `Skeleton` rows with row spacing, for the segment list and scene list. Props: `count` (default 5), `rowHeight`. YAGNI on any other presets until a shape actually needs one.
- Both exported from `src/components/ui/index.js` (`Skeleton`, `SkeletonList`).
- `role="status"` / `aria-busy` on the skeleton container for accessibility.

### 2. Spinner unification sweep

Replace idioms (2) and (3) with `<Spinner>`:

- `<Loader className="spin">` → `<Spinner>` in: SceneManager, ProtectedRoute, AuthModal, DepartmentSelector, ForgotPasswordModal, DepartmentWorkspace.
- CSS-div `className="spinner"` → `<Spinner>` in: SceneViewer, AdminRoute, ScriptsChart, UserGrowthChart.
- Preserve existing sizes/labels where sensible; keep surrounding layout markup, only swap the spinner element.
- **Explicitly left alone:** `RefreshCw className="spin"` in LocationDashboard / CharacterDashboard — that is a *refresh affordance* (an icon that also happens to spin), not a load state. Approved to keep as-is.

Dead CSS (`.spinner`, `.spinner-sm`, `.spin` rules) is removed only where it becomes unused after the swap; leave anything still referenced.

### 3. Gap fixes

| # | Gap (file:line) | Treatment |
|---|-----------------|-----------|
| G1 | Cross-view story-day refetch: `SceneViewer.jsx:122-151` (`refreshScenes`), `ZoomableStripboard.jsx:117-143` (`refreshBoard`), `Stripboard.jsx:180` (listener) | Add a `refetching` state set around the refetch; render a subtle **panel-level overlay** with `<Spinner>` and `aria-busy` on the panel, so the silent mutation becomes visible. No full skeleton (data already on screen). |
| G2 | SegmentManager initial load: `SegmentManager.jsx:24-28` (`load`) | Add a `loading` state; render `<SkeletonList>` while the first fetch runs, before the list renders. |
| G3 | SegmentManager ops — rename/color/reorder/delete/create: `SegmentManager.jsx:52-100` | Refactor the single global `busy` flag into a per-item/per-action descriptor (e.g. `busy = { id, action }` or `null`). Render an inline `<Spinner>` on the specific control acted on: per-row for reorder/delete, on the save button for rename, on the add button for create, on the affected chip for color/type. All controls still disable during any op to prevent concurrent mutations. |
| G4 | StripDetailDrawer story-day edits: `StripDetailDrawer.jsx:24-35` (`sdSaving`) | Render `<Spinner>` on the button being saved, keyed off `sdSaving`. |
| G5 | SceneDetail story-day + segment assignment: `SceneDetail.jsx:99` (`storyDaySaving`), `:106` (`segmentSaving`) | Render `<Spinner>` on the acted control, keyed off the respective saving state. |

### 4. Architecture notes

- All changes are presentational/state-local; no API, context contract, or data-shape changes. `StoryDayContext`'s listener mechanism is unchanged — G1 only adds local `refetching` state inside each listener callback.
- The `busy` refactor in G3 is contained entirely within `SegmentManager.jsx`; its props and the segment service API are untouched.
- Overlay styling (G1) uses a shared, minimal CSS class (semi-transparent scrim + centered spinner) so the two/three panels look identical. Colocate it with the primitive or a small shared stylesheet rather than duplicating per panel.

## Testing / Verification

- No frontend component test framework is wired; `npm run lint` is broken repo-wide (known). **Gate on `npm run build` passing.**
- Then drive the real flows to confirm loaders appear and clear:
  - Switch a story day in one view with a second view open → overlay appears in the other view, then clears (G1).
  - Open SegmentManager cold → skeleton then list (G2).
  - Rename / recolor / reorder / delete / create a segment → spinner on the acted control only (G3).
  - Edit story day in StripDetailDrawer and SceneDetail; assign a scene to a segment → button/control spinner (G4, G5).
  - Spot-check swept spinners (auth, admin, charts) still render.
- Use the `/verify` skill or browser automation for the interactive checks.

## Risks

- The unification sweep touches ~10 files; risk is cosmetic (wrong size/placement), caught by build + visual spot-check.
- G3's `busy` refactor changes disable logic — must ensure concurrent segment ops remain blocked while only the acted control shows a spinner.
