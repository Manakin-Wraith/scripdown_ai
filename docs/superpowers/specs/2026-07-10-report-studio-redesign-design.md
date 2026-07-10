# Report Studio — Report Page Redesign

**Date:** 2026-07-10
**Status:** Design approved, pending spec review
**Component:** `frontend/src/components/reports/ReportBuilder.jsx` (+ filter panel, backend report route)

## Problem

The current Report page (`ReportBuilder.jsx`) has four UX problems, all confirmed by the user:

1. **Fragmented flow** — the steps (pick type → filter → generate → find result) are scattered across a full-width type grid, a left filter panel, a thin right config bar, and a results list. The eye travels top → left → right → right-again.
2. **No preview** — you configure blind, generate, then must download/print a PDF to see whether the report is right.
3. **Filters overwhelming** — the filter panel is dense and always shows every filter regardless of context.
4. **Managing results** — the generated-reports list is a plain inline list, poor for finding/reusing earlier reports.

## Users & constraints

- **Primary workflow:** iterate on *one* report — pick a type, tweak filters, regenerate until right.
- **Primary device:** desktop (production office / laptop). Design responsively but optimize for wide screens.

## Solution: Report Studio

Replace the stacked layout with a single-screen **Report Studio**: a top toolbar, a left build-rail, and a right live-preview pane. Past reports move into a **Library** slide-over drawer.

The live preview shows the **real rendered report HTML** (the same template that becomes the PDF), refreshed **manually** via an "Update Preview" button. This is WYSIWYG — what you preview is exactly what downloads — and avoids re-rendering the backend on every keystroke.

### Chosen decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Layout | Report Studio (split view), Library as a built-in drawer |
| Preview refresh | Manual — "Update Preview" button (+ refresh on type change) |
| Preview fidelity | Real rendered report HTML, reusing `_render_report_html()` |
| Type picker | Compact icon list in the rail, always visible |
| Filters | Keep **all** filters, grouped into collapsible sections (no per-type hiding yet) |
| Library reopen | Clicking a past report restores its type + filters into the rail to edit & regenerate |

## Layout detail

### Top toolbar
- Left: "🎬 Report Studio · *{script title}*".
- Right actions:
  - **▤ Library** — toggles the Library drawer.
  - **⟳ Update Preview** — re-renders the preview pane from current rail config; no DB write.
  - **＋ Generate** — persists the report (existing `generateReport`), shows a success toast, and the new report appears in the Library.
  - **⭳ Download / ⎙ Print / ↗ Share** — icon buttons acting on the **active saved report** (the one just generated, or the one reopened from the Library). They are **disabled until a report has been generated/selected**, since all three use existing endpoints keyed on a `report_id`. The unsaved preview itself is not directly downloadable — the user clicks **Generate** first (which is cheap and also produces the downloadable/shareable artifact).

### Left build-rail
1. **Report type** — compact vertical icon list of all report types (from `getReportTypes`). Selecting a type sets `selectedType` and triggers a preview refresh.
2. **Presets** — load a saved filter preset / save current filters as a preset. Reuses existing `getFilterPresets` / `saveFilterPreset` / `deleteFilterPreset`.
3. **Filters** — every existing filter, reorganized into collapsible groups, each showing an active-count badge:
   - Location (locations, location_parents)
   - Character (characters)
   - INT/EXT · Time of day (int_ext, time_of_day)
   - Scene # / range · Story day (scene_numbers, scene_range, story_days, timeline_codes)
   - Grouping & categories (group_by, categories)

   Groups are collapsed by default; a group with active filters shows its count and may start expanded. Filter *inputs and state shape are unchanged* from the current `ReportFilterPanel` — this is a reorganization of the same controls.
4. **Title** — optional custom title input.

### Right preview pane
- Renders report HTML in an `<iframe>` (sandboxed, `srcdoc` or blob URL) so report CSS can't leak into the app.
- Status line above the doc: "*N of M scenes match*" (derived from the preview response / aggregated data).
- **Empty state** (before first render): "Configure on the left, then hit Update Preview."
- **Loading state**: spinner overlay while the preview request is in flight.
- **Error state**: inline message if preview rendering fails.

### Library drawer (slide-over from the right)
- Header + search box (client-side filter over titles/types).
- Each item: report title, type icon, generated date, **Shared** badge when public.
- Per-item actions: **Download / Share / Delete** (existing handlers).
- **Clicking the row body** restores the report's `report_type` + `config` (filters, group_by, categories, title) back into the rail, closes the drawer, and refreshes the preview — enabling the "iterate on one report" loop against a past report.

## Backend changes

Minimal — one new endpoint; everything else is reused.

### New: `POST /api/reports/scripts/<script_id>/reports/preview-html`
- Body: `{ report_type, filters, group_by, categories, title }` (same shape as `generate`, minus persistence).
- Behavior: aggregate data with filters (existing `aggregate_scene_data`), build the in-memory report dict, and render it via the existing `_render_report_html()`. Return the HTML string (JSON `{ success, html, match_count, total_count }` or `text/html`).
- **No database write.** No new tables, no schema change.
- Reuses the exact render path used by `/reports/<id>/print` and PDF generation, guaranteeing preview == final output.

### Modified: `GET /api/reports/scripts/<script_id>/reports`
- Ensure each returned report includes `report_type` and `config` (the persisted config already contains `filters`, `group_by`, `categories`) so the Library can reopen a report into the rail. Verify current response already includes these; add if missing.

### Reused unchanged
`generate`, `/reports/<id>/pdf`, `/reports/<id>/print`, `/reports/<id>/share`, `filter-options`, `filter-presets`, `report-types`.

## Frontend component structure

Refactor `ReportBuilder.jsx` (currently one ~430-line component) into focused units under `frontend/src/components/reports/`:

- **`ReportStudio.jsx`** — page shell: toolbar, rail, preview pane, drawer; owns `selectedType`, `filters`, `customTitle`, `previewHtml`, `existingReports`, drawer open state. (Replaces `ReportBuilder` at the existing route `scripts/:scriptId/reports`.)
- **`ReportRail.jsx`** — type icon-list + presets + filter groups + title. Wraps/adapts the existing `ReportFilterPanel` controls into collapsible groups.
- **`ReportPreviewPane.jsx`** — iframe preview + status line + empty/loading/error states + "Update Preview" trigger.
- **`ReportLibraryDrawer.jsx`** — slide-over list with search, per-item actions, and reopen-to-edit.
- Keep `ShareModal.jsx` as-is. `ReportFilterPanel.jsx` is either adapted into `ReportRail` groups or its group internals are reused.

New API helper in `apiService.js`: `previewReportHtml(scriptId, reportType, filters, groupBy, categories, title)` calling the new endpoint.

## Data flow

1. Load: fetch report types, script metadata, existing reports (with `config`), filter options, presets (as today).
2. Build: user picks type + edits filter groups in the rail (state identical to current `filters` object).
3. Preview: user clicks **Update Preview** → `previewReportHtml(...)` → iframe `srcdoc` set to returned HTML; status line updated from `match_count`/`total_count`.
4. Generate: user clicks **Generate** → existing `generateReport(...)` → new report prepended to `existingReports` → toast.
5. Manage/reopen: **Library** drawer → click a report → restore `report_type` + `config` into rail state → refresh preview.

## Error handling

- Preview endpoint failure → inline error state in the pane; existing config preserved.
- Generate failure → toast error (as today).
- All existing failure paths (delete, share, preset save) unchanged.
- Iframe is sandboxed to contain report CSS/markup.

## Testing

- **Backend:** unit test for the new `preview-html` endpoint — returns HTML for a valid type, honors filters (match_count reflects filtering), 404 on unknown script, 400/handled on invalid type. Assert no `reports` row is created.
- **Frontend:** component tests — rail type switch triggers preview refresh; filter group active-count badges; Library reopen restores state; empty/loading/error states render.
- **Manual (desktop):** iterate loop — pick type, edit filters, Update Preview, Generate, reopen from Library, download.

## Out of scope (deferred)

- Strict per-type filter hiding (type→filters map).
- Auto/debounced preview refresh.
- Report thumbnails in the Library.
- Mobile-first / phone layout (responsive but desktop-optimized).
