# Call Sheet Customization — Per-Production Templates

**Date:** 2026-09-21
**Status:** Design approved — pending spec review, then implementation plan
**Type:** Architectural
**Parent:** `docs/superpowers/specs/2026-09-18-call-sheets-design.md` (v1, shipped)
**Backlog:** "Call sheets: robustness + per-production customization pass"
(`docs/BACKLOG.md`)

## Purpose

Call sheets v1 is fixed-shape: the same day-info fields, roster columns and
PDF layout for every production. A real reference call sheet (a multi-page
TV-drama sheet with department call times, weather/police/hospital blocks,
story-day/story-time scene columns, cast tables with P/U, costume, M-UP&H
and mic'ing columns, extras, catering headcounts and an advanced schedule)
shows how much a production's needs vary.

This slice lets each production define **one call sheet template** that
controls what its daily sheets contain and how they look. Each day's sheet
inherits the template and can override values.

## Decisions (settled in brainstorming)

- **Model:** per-production template (not a fixed superset with toggles, not
  per-sheet free-form).
- **Storage:** JSONB config plus JSONB values (approach A), not normalized
  tables.
- **Template controls, all four in scope:**
  1. Section show/hide, order and labels.
  2. Custom day-info fields.
  3. Custom cast and scene table columns.
  4. Department call times and notes blocks.

## Out of scope (YAGNI)

- Drag-and-drop reordering (up/down arrows only).
- Multiple named templates per production (one template per production).
- Copying a template across productions.
- Sides, multi-unit, distribution — still deferred per the v1 spec.

## Data model — migration `055_call_sheet_templates.sql`

Manual apply against Supabase (same pattern as 051–054). All changes are
additive with defaults; no backfill.

### `call_sheet_templates`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid pk | `gen_random_uuid()` |
| `production_id` | uuid not null unique | `REFERENCES productions(id) ON DELETE CASCADE` |
| `config` | jsonb not null | versioned, shape below |
| `updated_by` | uuid null | `REFERENCES auth.users(id) ON DELETE SET NULL` |
| `created_at` / `updated_at` | timestamptz | `updated_at` uses the `update_shooting_updated_at()` trigger |

Owner-only RLS backstop, as in 054.

### `config` shape (`"v": 1`)

```json
{
  "v": 1,
  "sections": [
    {"key": "day_info", "label": "Day info", "visible": true}
  ],
  "day_fields": [
    {"key": "wind", "label": "Wind", "type": "text",
     "default": "", "builtin": false}
  ],
  "cast_columns":  [{"key": "pickup", "label": "P/U at base",
                     "type": "time", "sensitive": false}],
  "scene_columns": [{"key": "story_day", "label": "Story day",
                     "type": "text", "sensitive": false}],
  "departments": [{"key": "wardrobe", "label": "Wardrobe",
                   "default_call": "06:00", "as_per": "Pippa"}],
  "blocks": [{"key": "safety", "label": "Special notes", "body": "..."}]
}
```

- Section keys: `day_info`, `locations`, `scenes`, `cast`, `extras`,
  `crew`, `dept_calls`, `catering`, `notes`, `advanced`.
- Field/column types: `text`, `time`, `link`, `number`.
- The nine v1 fixed columns (weather, sunrise_time, sunset_time,
  breakfast_time, lunch_time, nearest_hospital, parking_notes, safety_notes,
  general_notes) appear as `builtin: true` entries in `day_fields`. They may
  be hidden or relabelled but not deleted, and they keep reading/writing the
  existing columns on `call_sheets`.
- **No template row = the default config**, generated in code, mirroring v1
  exactly. Reads never create a row; only `PUT` does.

### Per-day and roster values (new JSONB columns, `NOT NULL DEFAULT '{}'`)

- `call_sheets.custom_values` — `{field_key: value}` for non-builtin day
  fields.
- `call_sheets.dept_overrides` — `{dept_key: {call, as_per}}`; blank values
  inherit the template default.
- `call_sheets.scene_extras` — `{scene_id: {column_key: value}}`.
- `call_sheet_cast.extra`, `call_sheet_crew.extra` — `{column_key: value}`.

### Permission columns

`can_edit_call_sheet_template boolean NOT NULL DEFAULT false` on
`production_members` and `production_invites`.

## Validation rules (service layer)

- Config save: unique keys within each list, allowed types only, section
  keys drawn from the fixed list, caps (40 day fields, 15 columns per
  table, 30 departments, 20 blocks), builtin fields cannot be removed,
  string length limits.
- Value writes: keys must exist in the template's current definitions
  (unknown keys rejected); values validated per type (`time` as HH:MM,
  `number` numeric, `link` an http/https URL).
- **Templates never destroy data.** Removing a field or column from the
  template leaves stored values in the JSONB, ignored at render time.
  Re-adding the same key restores them.

## Backend

### Permissions

- New capability `can_edit_call_sheet_template` in `CAPABILITIES`
  (`middleware/production_authz.py`).
- `ROLE_PRESETS`: `admin` picks it up automatically; `coordinator` is a
  hardcoded literal and must gain `True` explicitly; `viewer` stays `False`.
  A test asserts the coordinator key is present (the column default would
  otherwise mask a missing key, as noted in the v1 spec).
- Editing a day's sheet, including all new value fields, stays under the
  existing `can_edit_call_sheets`.
- Any production member may read the template.
- New `from_production_id` resolver for the template routes.

### Routes (in `call_sheet_bp`)

| Method + path | Access |
|---|---|
| `GET /api/productions/<pid>/call-sheet-template` | any member; stored config or the default, never creates a row |
| `PUT /api/productions/<pid>/call-sheet-template` | `can_edit_call_sheet_template`; validates, upserts |

Changed routes:

- `GET /api/call-sheets/<id>` also returns the effective template and the
  sheet's custom data.
- `PATCH /api/call-sheets/<id>` accepts `custom_values`, `dept_overrides`,
  `scene_extras`, validated against the template.
- Cast/crew add endpoints accept `extra`; the existing cast/crew update
  endpoints accept `extra` too.

### Redaction

Each column has `sensitive: bool`. Sensitive values are stripped for
viewers without `can_view_sensitive` in both the JSON response and the PDF,
extending `redact_roster` in `call_sheet_service.py`. Rates stay stripped
as today.

## Frontend

### Template editor — new "Call Sheet" tab on `ProductionDetailPage`

- New `ProductionCallSheetTab.jsx`, composed of small panels: Sections,
  Day-info fields, Cast/Scene columns (one reusable field-list component),
  Departments, Boilerplate blocks.
- Visible to members; editable only with `can_edit_call_sheet_template`,
  read-only otherwise.
- Local edit state, one Save button (single `PUT`), unsaved-changes
  indicator, "Reset to default", backend validation errors shown inline on
  the offending row. Reordering via up/down arrows. Builtin fields show a
  lock icon.
- Members tab gains one checkbox for the new capability.

### Per-day `CallSheetEditor.jsx`

- Hardcoded `DAY_INFO_FIELDS` is replaced by the template's `day_fields`;
  builtin and custom fields share one input component and prefill from the
  template default.
- Renders only visible sections, in template order, with template labels.
- Cast/crew rows gain inputs for the template's cast columns (`extra`).
- New **Department calls** panel (template defaults prefilled, edits stored
  as `dept_overrides`) and **Scene extras** panel (one input per scene per
  scene column). Scene rows stay read-only, pulled live from the schedule.
- Template blocks are shown read-only with an "Edit for this day only"
  toggle.
- **Advanced schedule** is a live next-day scene list from the next
  `shooting_day`; it has no data of its own.

## PDF rendering (`_render_pdf_html`)

- Config-driven: resolve the effective template, loop `sections` in order,
  skip hidden ones. A registry dict maps section keys to small renderer
  functions; unknown keys are a no-op.
- Custom fields render in a grid, skipping empty values; `link` values print
  as text and as a clickable anchor.
- Cast and scene tables build columns from the config; a production with no
  custom columns gets today's layout. Sensitive columns are dropped for
  viewers without `can_view_sensitive`.
- Department calls render as a compact table with override-then-default
  resolution.
- Catering headcounts are computed from roster counts (crew, cast, extras,
  total); nothing new to enter.
- Advanced schedule is a compact scene table for the next day.
- The v1 "single page" constraint is dropped: the PDF flows onto extra pages
  and repeats the header on each.
- All user-authored text (labels, blocks, values) is HTML-escaped before it
  reaches WeasyPrint.

## Testing

- Config validation (duplicate keys, bad types, caps, builtin removal).
- Default template renders identically to v1 (existing PDF smoke test).
- Unknown value keys rejected; remove-then-re-add a field restores values.
- Permissions: `can_edit_call_sheet_template` gate (viewer 403, coordinator
  allowed, `False` override blocks); coordinator preset key assertion;
  `test_route_enforcement.py` extended for the two new routes.
- Redaction: a sensitive custom column is hidden from a
  non-`can_view_sensitive` viewer in the JSON and the PDF.
- Rendering: hidden sections omitted, order respected, HTML in labels
  escaped.
- Gates: full `pytest tests/` green, `npm run build` green (frontend lint is
  broken repo-wide and is not a gate).

## Rollout

1. Apply `055_call_sheet_templates.sql` to Supabase before the backend
   deploys.
2. Deploy backend, then frontend. Existing sheets and productions are
   unaffected because a missing template resolves to the v1-equivalent
   default.
3. No env vars, no backfill.
4. Afterwards update the backlog entry and `SLATEONE_FEATURES.md`.

## Open items carried forward

- Drag-and-drop reordering, multiple named templates, cross-production
  template copy.
- Whether scene-table per-scene timings (the reference sheet's "TIMINGS"
  column) should become a first-class scheduled time later; for now it is a
  configurable `time`/`text` scene column.
