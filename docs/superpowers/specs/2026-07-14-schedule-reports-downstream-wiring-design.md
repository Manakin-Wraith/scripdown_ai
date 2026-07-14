# Schedule → Reports Downstream Wiring

**Date:** 2026-07-14
**Status:** Design (approved for planning)
**Author:** brainstormed with LP/AD lens

## Problem

The Schedule (`ShootingSchedulePage` — the day-Kanban stripboard) is an island. It
produces genuinely new production data — which scenes are shot on which day, in what
order, on what date — and then dumps it into a **bespoke one-off PDF**
(`SchedulePrintView` + `window.print()`), bypassing the mature Report Studio pipeline
(saved library, share links, live preview, presets, WeasyPrint PDF, subscription
gating).

Meanwhile Report Studio already advertises the schedule's deliverables —
`day_out_of_days` ("Day Out of Days") and `one_liner` ("One-Liner / Stripboard") are
registered report types — but `generate_report()` → `aggregate_scene_data(script_id,
filters)` works **purely off scenes in script order, with no `schedule_id` and no
concept of a shooting day.** So today's DOOD and One-Liner are cosmetic: they group by
scene / story-day, never by the actual shooting days the user built.

**The isolation, precisely:** the report engine has the *names* of the schedule's
artifacts but no *wire* to the schedule's data.

## Goal

Run one wire that makes the report engine schedule-aware, so the Schedule flows into
the existing Report Studio infrastructure (library, share, PDF, live preview) and the
bespoke `SchedulePrintView` island can be retired.

Non-goals (deferred): call sheets, sides generation, the upstream wire (an
unscheduled-scenes bin fed by the shared filter engine — a separate future spec), and
any navigational/naming refactor of the Stripboard-table vs Board vs Schedule tabs.

## Design

### §1 — The data contract (one wire)

Thread an optional `schedule_id` through the report path:
`generate_report()`, `render_preview_html()`, and `aggregate_scene_data()`.

- **`schedule_id` absent** (today's behavior, unchanged): aggregate scenes in script
  order, grouped by whatever `group_by` says. `scene_breakdown`, `location`, `props`,
  `wardrobe`, etc. are unaffected.
- **`schedule_id` present**: aggregation joins `shooting_day_scenes` → `scenes`, and
  the unit of grouping becomes the **shooting day** — ordered by `day_number`, and by
  `sort_order` within each day. Each day carries `day_number`, `shoot_date`, `status`,
  and its ordered strips. Scenes on no day are bucketed as **"Unscheduled"** (a config
  flag `include_unscheduled`, default `true`) or excluded.

Report types split into two families:

- **Scene-based** (ignore `schedule_id`): `scene_breakdown`, `location`, `props`,
  `wardrobe`, `full_breakdown`, and the department reports.
- **Schedule-backed** (require `schedule_id`): `one_liner`, `day_out_of_days`, and the
  new `shooting_schedule`. When one of these is selected with no schedule, the report
  renders an **empty state** linking to the Schedule tab — never fake data.

**Persistence semantics:** a generated schedule-backed report snapshots the schedule
state into `data_snapshot` at generation time — a point-in-time **published**
deliverable (how ADs treat a "published" schedule). `config.schedule_id` is stored so
the report can be re-generated against the latest schedule state.

### §2 — Report types that take the wire

Only three. Everything else stays scene-based.

| Type | Change |
|---|---|
| `one_liner` ("One-Liner / Stripboard") | Strips in **shoot order**, grouped under **day-break banners** (Day N · date), with per-day totals: eighths, scene count, cast count, locations. |
| `day_out_of_days` | **True DOOD**: cast (rows) × shooting days (columns) matrix with **S / W / H / F** (Start · Work · Hold · Finish), plus per-cast totals (work days, hold days, total span). |
| `shooting_schedule` *(new)* | Full day-by-day schedule: each day a section with header (date, day #), its ordered strips, and day totals. Ports `SchedulePrintView`'s layout server-side. |

**Deferred:** `call_sheet` — needs per-day data not yet modeled (crew calls, call/wrap
times, weather, hospital). Follow-on spec.

**Wrinkles handled:**

- **Old saved reports** of `one_liner` / `day_out_of_days` render from their stored
  `data_snapshot` — snapshot-based rendering means no breakage. Only *new* generation
  of these types requires a schedule.
- **`full_breakdown`** currently embeds a DOOD section via `_render_day_out_of_days`.
  It stays scene-based, but **upgrades** when a `schedule_id` is supplied: with a
  schedule it renders the real DOOD; without, it falls back to the scene-based
  "appearances by story day" variant.

#### DOOD computation (S/W/H/F)

Given the ordered shooting days and each day's scenes' `characters`:

- For each cast member, find the first day they appear (**Start** = `S`) and the last
  day they appear (**Finish** = `F`).
- Every day between Start and Finish where they appear = **Work** (`W`).
- Every day between Start and Finish where they do **not** appear = **Hold** (`H`).
- Days before Start / after Finish = blank.
- Per-cast totals: work-day count, hold-day count, total span (F − S + 1 in shoot
  days). Cast ordering: by Start day, then alphabetically (cast ID numbers are a
  future enhancement, not required here).

### §3 — Entry points (both push + rail)

Two synchronized triggers, mirroring existing Studio patterns:

1. **Push from Schedule.** `ShootingSchedulePage`'s existing `Print / Export` button is
   **rewired** into a `Generate ▾` menu (One-Liner / DOOD / Shooting Schedule). Each
   item deep-links into Report Studio pre-loaded with `?schedule=<id>&type=<type>`,
   landing on the live preview so the user can tweak filters then Generate / Share.
2. **Rail selector in Report Studio.** When a schedule-backed type is selected, the
   rail reveals a **`Source: [Schedule ▾]`** dropdown listing the script's schedules
   (default: the schedule from the deep-link, else the first/most-recent). Selecting a
   schedule triggers a preview refresh. This keeps the Studio self-sufficient — a user
   can produce these reports without ever visiting the Schedule tab.

Deep-link contract: Report Studio reads `schedule` and `type` query params on mount,
sets `selectedType` and the new `scheduleId` state, and fires the existing
`triggerPreview()` path.

### §4 — Retire the bespoke print

- **Rewire, don't delete the affordance.** The `Print / Export` button becomes the
  `Generate ▾` button from §3 — same location, same muscle memory, now flowing through
  the report pipeline.
- **Port the markup.** `SchedulePrintView`'s layout/CSS becomes the server-side
  `_render_shooting_schedule` template so the new report looks as good or better and
  gains library / share / versioning.
- **Full retirement.** Remove the print-preview modal, `SchedulePrintView.jsx`,
  `SchedulePrintView.css`, and the `printing-schedule` print path from
  `ShootingSchedulePage`. One export path, no drift. (A future "inline generate"
  shortcut — §3 option C — can restore instant PDF without resurrecting the island.)

## Architecture & affected code

### Backend

- `backend/services/report_service.py`
  - `aggregate_scene_data(script_id, filters, schedule_id=None)` — when `schedule_id`
    set, build day-grouped structure from `shooting_day_scenes` + `shooting_days`;
    add an `unscheduled` bucket per `include_unscheduled`.
  - `generate_report(...)` and `render_preview_html(...)` — accept and pass through
    `schedule_id` (from `config.schedule_id` on generate).
  - New `_render_shooting_schedule(data)`, rewritten `_render_one_liner(data)` and
    `_render_day_out_of_days(data)` to consume day-grouped data; DOOD helper computes
    S/W/H/F.
  - `REPORT_TYPES` / `VALID_REPORT_TYPES` — add `shooting_schedule`; tag which types
    are schedule-backed (a `requires_schedule` flag surfaced in `get_report_types`).
- `backend/routes/report_routes.py` — thread `schedule_id` from request body/query
  into generate + preview; return `requires_schedule` in the types payload.

### Frontend

- `frontend/src/services/apiService.js` — `generateReport` / `previewReportHtml` gain
  a `scheduleId` argument; add `getSchedules` reuse for the rail dropdown.
- `frontend/src/components/reports/ReportStudio.jsx` — `scheduleId` state; read `type`
  + `schedule` query params on mount; pass `scheduleId` into preview/generate; empty
  state for schedule-backed types with no schedule.
- `frontend/src/components/reports/ReportRail.jsx` — `Source: [Schedule ▾]` selector,
  shown only for `requires_schedule` types.
- `frontend/src/components/schedule/ShootingSchedulePage.jsx` — replace Print/Export
  button + modal with `Generate ▾` menu deep-linking to `/scripts/:id/reports?...`.
- **Delete:** `SchedulePrintView.jsx`, `SchedulePrintView.css`, and the print-modal
  code path.

## Data flow

```
Schedule (Generate ▾)
   └─ deep-link → /scripts/:id/reports?type=day_out_of_days&schedule=<sid>
        └─ ReportStudio reads params → scheduleId + selectedType
             └─ previewReportHtml(scriptId, type, filters, ..., scheduleId)
                  └─ report_service.render_preview_html(..., schedule_id)
                       └─ aggregate_scene_data(script_id, filters, schedule_id)
                            └─ join shooting_day_scenes → day-grouped data
                       └─ _render_{one_liner|day_out_of_days|shooting_schedule}
             └─ Generate → generateReport(..., scheduleId)
                  └─ snapshot day-grouped data → reports table → library/share/PDF
```

## Error handling

- Schedule-backed type + no `schedule_id` → structured empty state (not an error),
  copy links to the Schedule tab.
- `schedule_id` referencing a deleted/foreign schedule → validate ownership via
  existing script-scoped access; treat as "no schedule" empty state.
- A schedule with zero days or zero assigned scenes → render headers + an
  "empty schedule" note; DOOD renders the cast list with all-blank rows.
- Deep-link with an unknown `type` → fall back to `scene_breakdown` (existing default).

## Testing

- **Backend (pytest):**
  - `aggregate_scene_data` with `schedule_id`: correct day grouping, sort order,
    unscheduled bucket on/off.
  - DOOD S/W/H/F computation: single-day actor (S=F=W), gap actor (H between), full-run
    actor, actor absent entirely.
  - `one_liner` / `shooting_schedule` render day-break banners and per-day totals.
  - Scene-based types ignore `schedule_id` (regression: output identical with/without).
  - `full_breakdown` DOOD section: scene-based fallback vs schedule-upgraded.
  - Old saved snapshot renders unchanged.
- **Frontend (build + manual):**
  - Deep-link params select type + schedule and preview renders.
  - Rail source dropdown switches schedules and refreshes preview.
  - Empty state for schedule-backed type with no schedule.
  - Schedule `Generate ▾` navigates correctly; old print path fully gone.

## Sequencing (for the plan)

1. Backend contract: `schedule_id` through aggregate/generate/preview + day-grouped
   aggregation + unscheduled bucket. (Ships behind existing types, no UI yet.)
2. Rewrite `_render_one_liner` / `_render_day_out_of_days` (+ DOOD math) and add
   `_render_shooting_schedule`; port `SchedulePrintView` markup.
3. `REPORT_TYPES` metadata (`requires_schedule`, new type) + route plumbing.
4. Report Studio: scheduleId state, query-param deep-link, preview/generate wiring,
   empty state.
5. Report Rail: source selector.
6. Schedule page: `Generate ▾`, delete `SchedulePrintView` + modal.
7. Tests + regression pass.
