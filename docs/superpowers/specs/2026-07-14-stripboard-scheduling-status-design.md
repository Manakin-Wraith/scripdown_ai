# Stripboard Scheduling Status

**Date:** 2026-07-14
**Status:** Design (approved for planning)
**Related:** [[2026-07-14-schedule-reports-downstream-wiring-design]] (built the Schedule→Reports wire; this surfaces schedule state on the Stripboard tab)

## Problem

The **Stripboard tab** (`frontend/src/components/reports/Stripboard.jsx`, branded "One-Liner / Stripboard") is a read-only breakdown table of every scene. It loads plain scene rows via `getScenes(scriptId)` and has **no concept of scheduling** — it can't show whether a scene is assigned to a shooting day.

Scheduling lives in the `shooting_day_scenes` join table, never on the scene row, so changes made on the Board/Schedule (assigning/unassigning scenes to days) are invisible on the Stripboard. An AD scanning the Stripboard cannot see "what's left to schedule."

(Story-day edits, reorders, and location changes already reflect on the Stripboard because it remounts and refetches scene data on navigation — and story-day even syncs live via `StoryDayContext`. The *only* missing dimension is scheduling status.)

## Goal

Surface, on the Stripboard, each scene's shooting-day assignment **relative to one active schedule**, and keep it current with Board/Schedule changes. Reuse existing APIs; no backend changes.

Non-goals: live cross-route sync between Schedule and Stripboard (impossible with route-based mounting; out of scope); changing the Report Studio `one_liner` report; multi-schedule simultaneous display.

## Design

### §1 — Data & sync

**Fetch** (on mount, and when the picker changes):
- `getSchedules(scriptId)` → `{ schedules: [{id, name}] }` — populates the schedule picker (same data the Report Studio rail uses).
- `getShootingDays(activeScheduleId)` → `{ days: [{ id, day_number, scenes: [{ scene_id, ... }] }] }` — from which the component builds a lookup `Map<sceneId, { dayNumber }>`.

Each scene row consults the map: present → **Scheduled (Shoot D`day_number`)**; absent → **Unscheduled**.

**Active schedule selection:** default to the first schedule returned (most-recent/first per existing `getSchedules` ordering). Persist the chosen schedule id in `localStorage` keyed by script (mirroring the Board's `board-state-<scriptId>` pattern) so the picker choice survives navigation.

**Sync mechanism:** mount-refetch. The Stripboard, Board, and Schedule are distinct routes; navigating to the Stripboard remounts it, which refetches schedules + shooting days, so any Board/Schedule change is reflected on arrival. No event bus is added — two routes cannot be mounted simultaneously, so there is nothing to live-update. (The existing `useStoryDayListener` remains for story-day sync and is untouched.)

### §2 — Surfaces

1. **Schedule picker** — a `<select>` added to the existing `stripboard-filters` row. Lists the script's schedules by name; value is the active schedule id; on change, refetch shooting days and update the map. Reuses the select styling already in the filter row.
2. **"Shoot" pill column** — a new column between the existing "Day" (story day) and "Cast" columns (final column order is a build detail). Renders a green `D{n}` pill when the scene is scheduled in the active schedule, or a muted `Unscheduled` pill otherwise. Styled distinctly from the story-day `sb-day-badge` so shooting day (production) is never confused with story day (narrative).
3. **Scheduled/Unscheduled filter** — a `<select>` (`All / Scheduled / Unscheduled`) added to the filter row, mirroring the existing analysis-status filter. Filters `filteredScenes` by the scene's presence in the scheduled map.
4. **Stat** — add `{scheduled} scheduled · {unscheduled} unscheduled` to the `stripboard-stats` bar, computed over active (non-omitted) scenes for the active schedule.
5. **Row flag** — unscheduled rows get a subtle left-border accent + slight dim (a `sb-unscheduled` class) so gaps pop when scanning. Applied only when a schedule is active (see edge cases).

### §3 — Edge cases

- **Zero schedules:** hide the picker, the Shoot pill column, the scheduled/unscheduled filter, the stat, and the row flag. Show a one-line hint in the filter row: "No schedule yet — build one on the Schedule tab." (Nothing is meaningfully "scheduled" or "unscheduled" without a schedule.)
- **Omitted scenes:** excluded from the scheduled/unscheduled stat counts, consistent with the existing `activeScenes` stat logic. Their row still renders (with whatever pill applies) but they don't skew counts.
- **Scene on a deleted day / removed assignment:** naturally resolves to Unscheduled because it is no longer in `shooting_day_scenes` returned by `getShootingDays`.
- **Schedule picker points at a schedule that was deleted elsewhere:** if the persisted id is not in the fetched `schedules`, fall back to the first schedule (or the zero-schedules state if none remain).
- **Fetch failure for shooting days:** degrade gracefully — treat the map as empty (all scenes read as Unscheduled) and log a warning; do not block the scene table from rendering.

## Architecture & affected code

Frontend only:
- `frontend/src/services/apiService.js` — no change (`getSchedules`, `getShootingDays` already exist).
- `frontend/src/components/reports/Stripboard.jsx`:
  - New state: `schedules`, `activeScheduleId`, `scheduledMap` (`Map<sceneId,{dayNumber}>`), `filterScheduled` (`all|scheduled|unscheduled`).
  - New effects: load `schedules` on mount (with localStorage-restored active id); load shooting days whenever `activeScheduleId` changes → build `scheduledMap`.
  - Extend `filteredScenes` to apply the scheduled filter.
  - Extend `stats` to compute scheduled/unscheduled counts.
  - Render: picker + scheduled filter in the filter row; Shoot pill column header + cell; stat in stats bar; `sb-unscheduled` row class.
- `frontend/src/components/reports/Stripboard.css` — styles for `.sb-shoot-pill` (scheduled/unscheduled variants), the new column, and `.sb-unscheduled` row accent.

If `Stripboard.jsx` grows unwieldy with the added scheduling logic, extract a small pure helper (e.g. `buildScheduledMap(days)`) so it can be unit-tested independently; keep it in the same file unless it clearly warrants its own module.

## Data flow

```
Stripboard mount
  ├─ getScenes(scriptId)            (existing) → scene rows
  ├─ getScriptItems(scriptId)       (existing) → user items
  └─ getSchedules(scriptId)         → schedules; pick active (localStorage ?? first)
        └─ getShootingDays(activeScheduleId) → days → buildScheduledMap → Map<sceneId,{dayNumber}>

per row: scheduledMap.has(sceneId) ? "Shoot D{n}" : "Unscheduled"
picker change → getShootingDays(newId) → rebuild map (no full remount)
navigate away & back → full remount → everything refetched (reflects Board/Schedule edits)
```

## Testing

Frontend gate: `npm run build` (lint is broken repo-wide). No backend tests (frontend-only, existing endpoints).

- **`buildScheduledMap(days)` unit behavior** (if extracted): days with scenes → correct `sceneId → dayNumber`; empty/undefined days → empty map; a scene appearing under one day maps to that day number.
- **Manual/build verification:**
  - With a schedule that has assigned + unassigned scenes: assigned rows show `Shoot D{n}`, others `Unscheduled`; stat counts match; filter narrows correctly; unscheduled rows carry the accent.
  - Switch the picker to another schedule → pills/counts update without a full page reload.
  - Assign a scene on the Board, navigate to Stripboard → it now reads Scheduled (reflects the change).
  - Script with zero schedules → scheduling surfaces hidden, hint shown, table otherwise normal.
  - Omitted scene → not counted in the stat.

## Sequencing (for the plan)

1. Fetch schedules + active-id selection (localStorage) + shooting-days fetch + `buildScheduledMap`.
2. Shoot pill column (header + cell) with scheduled/unscheduled styling.
3. Scheduled/Unscheduled filter + stat.
4. Row flag + zero-schedule empty state + graceful-degradation on fetch failure.
5. Build verification pass.
