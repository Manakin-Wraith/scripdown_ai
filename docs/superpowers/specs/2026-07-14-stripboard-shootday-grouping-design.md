# Stripboard Shoot-Day Grouping & Segmented Header

**Date:** 2026-07-14
**Status:** Design (approved for planning)
**Related:** [[2026-07-14-stripboard-scheduling-status-design]] (added the active-schedule picker, Shoot pill column, scheduled/unscheduled filter + stat that this builds on)

## Problem

The **Stripboard tab** (`frontend/src/components/reports/Stripboard.jsx`, branded "One-Liner / Stripboard") now knows each scene's shooting-day assignment relative to an active schedule, but it still presents scenes as one flat, scene-ordered list. Two gaps remain:

1. **No production-day structure.** An AD cannot see the shoot broken into its actual shooting days, and — critically — cannot see the **page count per shooting day**, the single number production planning lives by ("End of Day 1 — 3 3/8 pgs"). The only grouping today is the *story-day* separator (narrative day), which is a different axis.
2. **The summary header card is a cramped strip.** `stripboard-stats` is a single flex row of ~10 stats separated only by gaps; it wraps ungracefully and reads as undifferentiated noise.

## Goal

When a schedule is active, reorder the Stripboard into **shoot-day blocks** — each with a header and an "End of Day N · X pgs" footer — and restructure the summary header into a **segmented card**. Frontend only; reuse existing APIs (`getSchedules`, `getShootingDays`, `getScenes`); no backend changes.

Non-goals: editing the schedule from the Stripboard (still read-only); changing the Report Studio one-liner/shooting-schedule reports; multi-schedule simultaneous display; a user-facing story-day vs shoot-day toggle (shoot-day grouping is automatic whenever a schedule is active).

## Design

### §1 — Segmented header card

Replace the flat `stripboard-stats` strip with one card divided into labelled segments by `border-right` rules. Each segment is a flex column: a small uppercase caption over its stat(s).

| Segment | Contents | Notes |
|---|---|---|
| **Identity** | `{activeScenes.length}` over caption **SCENES** | large number |
| **Composition** | `{intCount} INT · {extCount} EXT · {dayCount} DAY · {nightCount} NIGHT` | icons retained, inline |
| **Coverage** | `{totalCharacters} Cast · {totalLocations} Locations · {totalStoryDays} Story Days` | Story Days omitted when 0 |
| **Scheduling** | `{scheduledCount} scheduled · {unscheduledCount} unscheduled` | rendered **only** when `hasSchedules && activeScheduleId` |
| **Length** | `{totalEighthsDisplay}` over caption **PAGES** | right-aligned, accent colour |

- Pure presentational restructure: consumes the **existing** `stats` memo unchanged — no new computed values.
- On narrow viewports the card wraps **segment-by-segment** (each segment is an atomic flex child), not stat-by-stat.
- The print-only header block (`print-header` / `print-stats`) is **untouched** — it already renders its own summary line for PDF/print.

### §2 — Shoot-day grouping (active schedule only)

**Data join.** A new pure helper builds an ordered block list from the shooting-days payload joined against the already-loaded full scene objects:

```
buildShootDayBlocks(days, scenesById) -> [
  { dayNumber: Number, scenes: [fullScene, ...] },   // one per shooting day, in day_number order
  ...,
  { unscheduled: true, scenes: [fullScene, ...] }    // trailing bin; omitted entirely if empty
]
```

- `days` is `getShootingDays(activeScheduleId).days` (`[{ day_number, scenes: [{ scene_id, ... }] }]`).
- `scenesById` is a `Map<sceneId, fullScene>` built from the component's `scenes` state (`scene.id || scene.scene_id` as key).
- Within a day, scenes appear in the **schedule's stored order** (the order `days[i].scenes` arrives in). A `scene_id` with no matching full scene (stale assignment) is skipped.
- The **unscheduled bin** = every active/full scene whose id is not present in any day, in the board's natural scene order. Built by the component (it holds the full scene list) and passed in, OR computed inside the helper from `scenesById` minus the scheduled ids — implementation picks one; the helper is the tested unit either way.

**Rendering (grouped path).** When `hasSchedules && activeScheduleId`, the table body renders block-by-block instead of the flat map. Each block emits:

1. **Header row** (`sb-block-header`, `colSpan={fullColSpan}`): calendar icon + `SHOOT DAY {n}` (or `UNSCHEDULED`) + ` · {sceneCount} scenes`. Accent left bar. `sceneCount` counts the block's rendered (post-filter, non-omitted) scenes.
2. **Scene rows**: the existing `stripboard-row` markup and its expand/breakdown row, **unchanged except** the per-row Shoot pill column is not rendered in grouped mode (the header carries the day — see column note below).
3. **Footer row** (`sb-block-footer`, `colSpan={fullColSpan}`): `End of Day {n} · {formatEighths(sum)} pgs`, where `sum` = `Σ getSceneEighths(scene)` over the block's active (non-omitted) scenes. The unscheduled bin shows `Unscheduled · {formatEighths(sum)} pgs`.

**Filters inside blocks.** The existing filters (INT/EXT, time-of-day, analysis status, story-day) still apply to the scenes within each block. A block whose scenes all filter out renders nothing (no empty header/footer). The scheduled/unscheduled *filter* remains available but is largely redundant while grouped (the blocks already separate the two); it is left in place for consistency and still works.

**Shoot pill column.** In grouped mode the `col-shoot` header and cells are **not rendered**, so `fullColSpan` is `7` in grouped mode (same as the no-schedule layout). Only the flat/fallback path with a schedule active would have shown the column — but the fallback path is reached precisely when there is *no* active schedule, so the Shoot column is effectively retired by this change. (See §3 — this removes the column introduced by the prior feature; the scheduling status now lives in the block structure. `fullColSpan` becomes a constant `7`.)

**Sort control.** While grouped, ordering is the schedule's, so the free sort would be silently inert. Disable the sort `<select>` and direction button and set a tooltip: "Sorted by shooting schedule." In the fallback view the sort control is fully active as today.

### §3 — Fallback & edge cases

- **No schedule active** (no schedules, or picker resolves to none) → the **exact current behaviour**: single scene-ordered `filteredScenes` list with story-day separators (`sb-day-separator`), no block headers/footers, no Shoot column, sort active. This path is preserved verbatim.
- **Story-day separators** are suppressed inside shoot-day blocks (they belong to a different axis and would clutter). The story-day **badge** in the `col-day` column stays in both modes. Separators return in the fallback view.
- **Omitted scenes** (`is_omitted`) are excluded from block page totals and from the header `· N scenes` count (consistent with `activeScenes`); the row still renders inside its block if it is scheduled.
- **Scene on a deleted/removed shooting day** → not returned by `getShootingDays`, so it naturally falls into the `Unscheduled` bin.
- **`getShootingDays` fetch failure** → `scheduledMap` is already set empty by the existing catch; block-building sees no scheduled scenes, so every active scene lands in one `Unscheduled` bin. The table still renders (graceful degradation, matches existing behaviour).
- **Picker points at a deleted schedule** → existing logic falls back to the first schedule or the zero-schedule state; block-building follows whatever `activeScheduleId` resolves to.

### §4 — Architecture & affected code

Frontend only:

- `frontend/src/utils/scheduleMap.mjs` — add `buildShootDayBlocks(days, scenesById)` (and, if computed there, the unscheduled bin). Pure, null-tolerant, no React. Keeps `buildScheduledMap` as-is.
- `frontend/scripts/verify-schedule-map.mjs` — extend the framework-free node:assert harness with cases for `buildShootDayBlocks`.
- `frontend/src/components/reports/Stripboard.jsx`:
  - New `shootDayBlocks` memo (join + order + per-block active-scene page totals), gated on `hasSchedules && activeScheduleId`; deps include `scenes`, the shooting-days data (via `scheduledMap` or a new `shootingDays` state — see note), and the active filters.
  - Conditional table-body render: grouped block path vs. existing flat `filteredScenes` path.
  - Restructured stats markup into segmented card (`sb-stats-*`).
  - Drop the `col-shoot` header/cell; `fullColSpan` → constant `7`.
  - Disable sort control while grouped.
- `frontend/src/components/reports/Stripboard.css`:
  - `.sb-stats-card`, `.sb-stats-segment`, `.sb-stats-caption`, `.sb-stats-primary` (segmented card with dividers, responsive wrap).
  - `.sb-block-header`, `.sb-block-footer` (accent bar, page-total emphasis).
  - Retain `.sb-day-separator*`, `.col-shoot` (still used if any code path renders it), `.sb-shoot-pill`, `.sb-unscheduled` — remove only if provably dead after the change.

**Note on shooting-days data.** Today the component keeps only `scheduledMap` (`Map<sceneId,{dayNumber}>`) from `getShootingDays`. Block-building needs per-day scene *ordering*, which the map does not preserve. The plan should either (a) store the raw `days` array in state alongside `scheduledMap`, or (b) have `buildShootDayBlocks` accept the raw `days`. Prefer storing the raw `days` in a `shootingDays` state set in the same effect that builds `scheduledMap`, so both derive from one fetch. The `scheduledMap` remains for the header stat and any row-level checks.

## Data flow

```
Stripboard mount / picker change
  ├─ getScenes(scriptId)                 → scenes state → scenesById Map
  └─ getShootingDays(activeScheduleId)    → days
        ├─ buildScheduledMap(days)        → scheduledMap  (header stat)
        └─ setShootingDays(days)          → raw days for grouping

grouped render (hasSchedules && activeScheduleId):
  shootDayBlocks = buildShootDayBlocks(shootingDays, scenesById)
    → [ {dayNumber, scenes[]}..., {unscheduled, scenes[]} ]
  per block: header (· N scenes) → scene rows → footer (End of Day N · Σeighths pgs)

fallback render (no active schedule):
  filteredScenes flat list + story-day separators   (unchanged)
```

## Testing

Frontend gate: `npm run build` (lint is broken repo-wide — do NOT run `npm run lint`). Plus the framework-free node harness for the pure helper: `node scripts/verify-schedule-map.mjs` must print OK.

`buildShootDayBlocks` unit cases:
- Two days with scenes → two blocks in `day_number` order; scenes in each block preserve the input order.
- A `scene_id` absent from `scenesById` (stale assignment) → skipped, no crash.
- Active scenes not in any day → collected into a trailing `unscheduled` block, in scene order.
- No unscheduled scenes → no `unscheduled` block emitted.
- `days` empty/undefined → all scenes land in one `unscheduled` block (graceful).
- Page-total helper (or block totals): eighths carry correctly (e.g. 5×`1/8` + 1×`3/8` → `1` whole page), and omitted scenes are excluded from the total.

Manual/build verification:
- Active schedule with assigned + unassigned scenes → shoot-day blocks render with correct headers, footers, and page totals; unscheduled bin at bottom.
- Footer page total per block matches the sum of its scene eighths.
- Switch the picker to another schedule → blocks and totals rebuild without a full reload.
- Filter (e.g. INT only) → blocks show only matching scenes; empty blocks disappear; footers recompute.
- Script with zero schedules → flat scene-order list + story-day separators (unchanged), sort active, no blocks, no Shoot column.
- Segmented header card renders four/five segments with dividers; Scheduling segment hidden with no schedule; wraps cleanly when narrowed.

## Sequencing (for the plan)

1. `buildShootDayBlocks` pure helper + node verify cases (RED→GREEN).
2. Store raw `shootingDays` in state; `shootDayBlocks` memo (join + ordering + per-block page totals).
3. Grouped table-body render path (header/footer rows, scene rows, unscheduled bin); drop Shoot column; disable sort while grouped.
4. Segmented header card markup + CSS.
5. Block header/footer CSS + accent styling; suppress story-day separators in grouped mode.
6. Build verification pass + node verify.
