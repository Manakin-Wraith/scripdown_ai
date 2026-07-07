# Swallowed-Error Toasts — Scheduling Cluster — Design

**Date:** 2026-07-07
**Status:** Approved (design)
**Parent:** `docs/audits/2026-07-06-ui-consistency-audit.md` (Lens 3 — Interaction patterns; I1 "kill … swallowed errors"). Deferred from Stream B5, which consolidated confirms/alerts but left silent action-failure feedback for a later pass.
**Goal:** Give the scheduling/board mutation handlers that currently fail silently (`console.error` only, no user-visible feedback) an explanatory `toast.error`, so a failed schedule action tells the user why instead of appearing to do nothing.

## Context

A survey of in-scope components (excluding `admin/`, `campaigns/`, auth pages, and frozen WIP) found `console.error`-only catch blocks across many files, but most are background fetch-on-mount or polling failures where a toast would be noise, or already surface an inline error banner / `result` state. The genuine silent-failures-of-user-mutations cluster in the scheduling/board domain: `DayColumn`, `ScheduleKanban`, `SchedulePopover` (add-to-schedule), and `StripDetailDrawer` (story-day action). Notably, `SchedulePopover.handleQuickAdd` sets `setResult({ error })` on failure but that error branch is **never rendered** (only the success view exists), so it is effectively silent. `DepartmentNotesSection` (the other B5 deferral) already shows an inline `setError` banner on delete failure and is therefore **not** in scope.

The transient-feedback channel already exists and is proven app-wide: `useToast` (`context/ToastContext.jsx`), `toast.error(title, message)`.

## Scope

**In — 4 files. Each gains `import { useToast } from '../../context/ToastContext';` + `const toast = useToast();`, and each silent catch keeps its existing `console.error` and adds a `toast.error(...)`. No other behavior (rollbacks, reverts, `setResult`) changes.**

### `frontend/src/components/schedule/DayColumn.jsx`
| Handler | Catch adds |
| --- | --- |
| `handleRemoveScene` | `toast.error('Remove Failed', 'Could not remove the scene from this day.');` |
| `handleDeleteDay` | `toast.error('Delete Failed', 'Could not delete the day.');` |
| `handleSaveDate` (already reverts `localDate`) | `toast.error('Update Failed', 'Could not update the shoot date.');` |

### `frontend/src/components/schedule/ScheduleKanban.jsx`
| Handler | Catch adds |
| --- | --- |
| reorder-within-day (already rolls back via `refreshDays`) | `toast.error('Reorder Failed', 'Your change was reverted.');` |
| move-between-days (already rolls back) | `toast.error('Move Failed', 'Your change was reverted.');` |
| `handleAddDay` | `toast.error('Add Day Failed', 'Could not create a new day.');` |
| `handleBulkMove` — **restructure** the per-scene inline `.catch` to avoid N toasts | see below |

**Bulk-move restructure:** the current per-scene mapping is
```js
.map(sceneId =>
    moveSceneToDay(sceneMap[sceneId].dayId, sceneId, targetDayId, null)
        .catch(err => console.error(`Failed to move scene ${sceneId}:`, err))
);
await Promise.all(moves);
await refreshDays();
```
Change each move to report success/failure, then emit a single summary toast after settling:
```js
.map(sceneId =>
    moveSceneToDay(sceneMap[sceneId].dayId, sceneId, targetDayId, null)
        .then(() => true)
        .catch(err => { console.error(`Failed to move scene ${sceneId}:`, err); return false; })
);
const results = await Promise.all(moves);
await refreshDays();
if (results.some(r => r === false)) {
    toast.error('Some Moves Failed', 'Not all scenes could be moved.');
}
```

### `frontend/src/components/board/SchedulePopover.jsx`
| Handler | Catch adds |
| --- | --- |
| `handleQuickAdd` (keep the existing `setResult({ error })` line) | `toast.error('Add Failed', err.message || 'Could not add to the schedule.');` |

The two fetch-on-mount catches (`Failed to fetch schedules`, `Failed to fetch days`) stay `console.error`-only — out of scope.

### `frontend/src/components/board/StripDetailDrawer.jsx`
| Handler | Catch adds |
| --- | --- |
| `handleStoryDayAction` (wraps `toggleNewDay` / `setTimelineCode` / `setStoryDay`) | `toast.error('Update Failed', 'Your story day change could not be saved.');` |

This adds a toast to a JS data-mutation catch. **No `timeline-*` CSS rule is touched**, so the Stream A guard is unaffected.

**Out:**
- Background fetch/poll catches (SchedulePopover fetches, dashboards, NotificationBell poll, SceneDetail data fetch) — silent-by-design; a toast on every failed background load is noise.
- Files that already surface errors (`DepartmentNotesSection` banner; SceneViewer/TeamDrawer/ShootingSchedulePage/ScriptLibrary/reports already toast).
- SceneDetail story-day inline handlers, ScriptHeader clipboard-copy, NotificationBell management — considered and deferred (chosen scope is the scheduling cluster only).
- No copy changes elsewhere, no confirm/alert changes (those shipped in B5).

## Verification

- `npm run build` from `frontend/` succeeds.
- Invariants (from `frontend/src`): each of the 4 files imports `useToast` and calls `const toast = useToast();`; `grep -c "toast.error" <file>` ≥ the count in its table (DayColumn 3, ScheduleKanban 4, SchedulePopover 1, StripDetailDrawer 1); every existing `console.error` in those catches is retained (no catch had its logging removed); `handleBulkMove` no longer maps a bare `.catch(err => console.error(...))` and instead emits one summary toast.
- No test runner; live-drive login-gated. Correctness rests on build + review + before/after that each targeted action now toasts on failure, rollbacks/reverts still occur, and background fetches remain untouched.

## Execution

Lightweight — in-session, two commits by domain (`schedule/` = DayColumn + ScheduleKanban; `board/` = SchedulePopover + StripDetailDrawer), one review subagent, merge. No multi-task SDD.

## Success criteria

- The 4 scheduling/board mutation handlers surface a `toast.error` on failure; the bulk-move emits exactly one summary toast regardless of how many scenes failed.
- Existing `console.error` logging and rollback/revert behavior are preserved.
- Background fetch/poll failures and already-surfaced errors are untouched; no `timeline-*` CSS changed.
- Build green; work lands as two reviewed commits.
