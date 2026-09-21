# Call Sheet Customization — Per-Production Templates

**Date:** 2026-09-21 (revised after a spec-vs-code audit the same day)
**Status:** Design approved — pending spec review, then implementation plan
**Type:** Architectural
**Parent:** `docs/superpowers/specs/2026-09-18-call-sheets-design.md` (v1, shipped)
**Backlog:** "Call sheets: robustness + per-production customization pass"
(`docs/BACKLOG.md`)

## Purpose

Call sheets v1 is fixed-shape: the same day-info fields, roster columns and
PDF layout for every production. A real reference call sheet (a multi-page
TV-drama sheet with a header/key-crew block, department call times,
weather/police/hospital blocks, story-day/story-time scene columns, cast
tables with P/U, costume, M-UP&H and mic'ing columns, extras, per-meal
catering headcounts and an advanced schedule) shows how much a production's
needs vary.

This slice lets each production define **one call sheet template** that
controls what its daily sheets contain and how they look. Each day's sheet
inherits the template and can override values.

## Decisions (settled in brainstorming)

- **Model:** per-production template (not a fixed superset with toggles, not
  per-sheet free-form). **Storage:** JSONB config plus JSONB values, not
  normalized tables.
- **Template controls:** section show/hide/order/labels; custom day-info
  fields; custom cast, crew and scene table columns; department call times
  and notes blocks; a header section.
- **Header:** a template-level `header` section (static production identity
  fields, a key-crew list, plus a built-in general call time).
- **Catering:** manual per-meal grid, prefilled from roster counts.
- **Department calls:** independent, display-only; no inheritance into
  per-person crew call times.
- **Multi-script shoot days:** out of scope (see below).

## Out of scope (YAGNI)

- Drag-and-drop reordering (up/down arrows only).
- Multiple named templates per production; copying templates across
  productions.
- Sides, multi-unit, distribution — still deferred per the v1 spec.
- **Multi-script shoot days.** The reference sheet covers three episodes in
  one day. In this codebase schedules, scenes and casting are per script and
  `add_cast` enforces one script per day (`cross_script`). That limitation
  predates this work and stays; recorded as a follow-up in the backlog.
- Extras from `casting_groups` (anonymous headcount groups). The extras
  section uses background-tier cast rows only.

## Data model — migration `055_call_sheet_templates.sql`

Manual apply against Supabase (same pattern as 051–054). Additive with
defaults; no backfill.

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
  "sections": [{"key": "day_info", "label": "Day info", "visible": true}],
  "day_fields": [
    {"key": "wind", "label": "Wind", "type": "text", "section": "day_info",
     "default": "", "sensitive": false, "builtin": false}
  ],
  "cast_columns":  [{"key": "pickup", "label": "P/U at base",
                     "type": "time", "sensitive": false}],
  "crew_columns":  [],
  "scene_columns": [{"key": "story_day", "label": "Story day",
                     "type": "text", "sensitive": false}],
  "departments": [{"key": "wardrobe", "label": "Wardrobe",
                   "default_call": "06:00", "as_per": "Pippa"}],
  "blocks": [{"key": "safety", "label": "Special notes", "body": "..."}],
  "key_crew": [{"key": "director", "label": "Director", "value": "..."}]
}
```

- **Section keys** (fixed list): `header`, `day_info`, `locations`, `scenes`,
  `cast`, `extras`, `crew`, `dept_calls`, `catering`, `notes`, `advanced`.
- **Field/column types:** `text`, `textarea`, `time`, `link`, `number`.
- **Keys:** proposed by the client as a slug of the label, validated by the
  server against `^[a-z][a-z0-9_]{0,39}$`, and **immutable** once saved.
  Renaming changes only `label`, so stored values are never orphaned by a
  rename.
- **Built-in fields.** The nine v1 columns on `call_sheets` (`weather`,
  `sunrise_time`, `sunset_time`, `breakfast_time`, `lunch_time`,
  `nearest_hospital`, `parking_notes`, `safety_notes`, `general_notes`) plus
  a new built-in `general_call` (time; see Migration) appear as
  `builtin: true`. They may be hidden, relabelled, re-sectioned or given a
  default, but not deleted, and their **type is locked** (the time columns
  are Postgres `TIME`; the three notes fields are `textarea`).
- **Field placement.** Each day field has a `section` (`header`, `day_info`
  or `notes`); the renderer draws a field only in its section.
- **The default config mirrors v1's actual PDF, not the v1 field list.**
  v1 renders weather/sunrise/sunset/breakfast/lunch in the day-info strip;
  hospital, safety notes and general notes in the footer; and never prints
  `call_sheets.parking_notes` (it prints each location's own parking notes).
  So the default has weather, sunrise, sunset, breakfast, lunch in
  `day_info`; hospital, safety, general notes in `notes`; `parking_notes`
  `visible`-hidden by default; and `general_call` hidden by default.
- **No template row = the default config**, generated in code. Reads never
  create a row; only `PUT` does.

### Per-day and roster values (new JSONB columns, `NOT NULL DEFAULT '{}'`)

- `call_sheets.custom_values` — `{field_key: value}` for non-builtin day
  fields.
- `call_sheets.dept_overrides` — `{dept_key: {call, as_per}}`; blank values
  inherit the template default.
- `call_sheets.scene_extras` — `{scene_id: {column_key: value}}`.
- `call_sheets.catering` — `{meal: {group: count}}` with meals `craft`,
  `breakfast`, `lunch`, `dinner` and groups `crew`, `cast`, `add_crew`,
  `extras`. Absent entries are prefilled at render/edit time from roster
  counts (crew, non-background cast, none, background cast).
- `call_sheets.header_values` — `{key: value}` per-day overrides of the
  template's header fields and `key_crew` entries.
- `call_sheet_cast.extra`, `call_sheet_crew.extra` — `{column_key: value}`.
- `call_sheets.general_call` — new nullable `TIME` column (the built-in).

### Permission columns

`can_edit_call_sheet_template boolean NOT NULL DEFAULT false` on
`production_members` and `production_invites`.

## Validation rules (service layer)

- **Config save:** unique keys within each list, allowed types and section
  keys only, key format above, builtin fields present and type-locked,
  caps (40 day fields, 15 columns per table, 30 departments, 20 blocks,
  20 key-crew entries), string length limits.
- **Value writes:** values validated per type (`time` HH:MM, normalized —
  Postgres returns `HH:MM:SS` for `TIME` columns and the API trims it to
  `HH:MM`; `number` numeric; `link` an http/https URL); per-value length
  cap (2,000 chars, 10,000 for `textarea`).
- **Merge semantics.** Every JSONB value payload is merged **per key**, not
  replaced: `PATCH {"custom_values": {"wind": "SSW 15"}}` touches only
  `wind`; sending `null` for a key clears it. This is what makes "templates
  never destroy data" hold when an editor only sends fields it can see.
- **Unknown keys** (not in the current template) are ignored, not stored,
  and echoed back in an `ignored_keys` array so the UI can prompt a reload.
  This covers a stale editor whose template changed under it.
- **Templates never destroy data.** Removing a field or column leaves stored
  values in the JSONB, ignored at render time; re-adding the same key
  brings them back.
- **Template `PUT` concurrency:** the request carries `expected_updated_at`;
  a mismatch returns 409 so two admins don't silently overwrite each other.

## Backend

### Permissions

- New capability `can_edit_call_sheet_template` in `CAPABILITIES`
  (`middleware/production_authz.py`).
- `ROLE_PRESETS` in `production_member_service.py`: `admin` picks it up
  automatically; `coordinator` is a hardcoded literal and must gain `True`
  explicitly; `viewer` stays `False`. A test asserts the coordinator key is
  present.
- **`ProductionMembersTab.jsx` hardcodes the same presets** (the per-role
  capability objects and label map, ~lines 18–41) and must be updated in
  step with the backend, plus one new checkbox.
- Verify the invite-accept path copies the new capability column from
  `production_invites` to `production_members` (implementation-plan task).
- Editing a day's sheet, including all new value fields, stays under the
  existing `can_edit_call_sheets`. Any production member may read the
  template.
- The existing `from_production_id` resolver (the decorator default, reads
  `kwargs['production_id']`) is reused; no new resolver is needed.

### Routes (in `call_sheet_bp`)

| Method + path | Access |
|---|---|
| `GET /api/productions/<production_id>/call-sheet-template` | any member; stored config or the default, never creates a row |
| `PUT /api/productions/<production_id>/call-sheet-template` | `can_edit_call_sheet_template`; validates, upserts, 409 on stale `expected_updated_at` |

Changed:

- `GET /api/call-sheets/<id>` (and the by-day GET) also returns the
  effective template and the sheet's custom data.
- `PATCH /api/call-sheets/<id>` accepts `custom_values`, `dept_overrides`,
  `scene_extras`, `catering`, `header_values`, `general_call`, with the merge
  and unknown-key rules above.
- The existing cast/crew add and PATCH endpoints accept `extra`; the
  service whitelists (`_CREW_CALL_FIELDS`, `_CAST_CALL_FIELDS`) and
  `add_crew`/`add_cast` signatures gain it.

### Redaction (broader than v1)

v1's `redact_roster` strips only crew `job_rate` and contact
`standard_rate`, is never applied to cast rows or cast routes, and is never
applied to the PDF. This slice:

- Extends redaction to cast rows and to the cast add/PATCH responses.
- Strips values of any `sensitive` column/field (`cast_columns`,
  `crew_columns`, `scene_columns`, `day_fields`) for viewers without
  `can_view_sensitive`, in the JSON responses **and** the PDF. The PDF
  route passes `can_view_sensitive` into `render_call_sheet_pdf`.
- The template is an input to redaction (it defines which keys are
  sensitive).
- The editor hides inputs for sensitive columns from users without
  `can_view_sensitive`, so they can't blindly overwrite values they can't
  see.

## Frontend

### Template editor — new "Call Sheet" tab on `ProductionDetailPage`

- New `ProductionCallSheetTab.jsx`, composed of small panels: Sections,
  Header (static fields + key crew), Day-info fields, Cast/Crew/Scene
  columns (one reusable field-list component), Departments, Boilerplate
  blocks.
- Visible to members; editable only with `can_edit_call_sheet_template`,
  read-only otherwise.
- Local edit state, one Save (single `PUT`, sends `expected_updated_at`),
  unsaved-changes indicator, "Reset to default", backend validation errors
  inline on the offending row, and a reload prompt on 409. Reordering via
  up/down arrows. Builtin fields show a lock icon and a locked type.

### Per-day `CallSheetEditor.jsx`

- Hardcoded `DAY_INFO_FIELDS` is replaced by the template's `day_fields`;
  builtin and custom fields share one input component and prefill from the
  template default. If a response includes `ignored_keys`, the editor
  prompts a reload.
- Renders only visible sections, in template order, with template labels.
- Cast, crew and scene rows gain inputs for the corresponding template
  columns; sensitive columns are hidden per the redaction rule.
- New **Header**, **Department calls** (template defaults prefilled, edits
  stored as `dept_overrides`) and **Catering** (per-meal grid prefilled from
  roster counts) panels.
- Template blocks show read-only with an "Edit for this day only" toggle.
- **Extras** is the roster's background-tier cast rows shown as their own
  table (they are added via the existing cast picker); no new data.
- **Advanced schedule** is the next shooting day's scenes: the day in the
  same schedule with the next-higher `day_number`. It is omitted when there
  is no next day or it has no scenes.

## PDF rendering (`_render_pdf_html`)

- Config-driven: resolve the effective template, loop `sections` in order,
  skip hidden ones. A registry dict maps section keys to small renderer
  functions; unknown keys are a no-op.
- Day fields draw only in their own `section`; empty values are skipped;
  `link` values print as text and as a clickable anchor.
- Cast, crew and scene tables build columns from the config; a production
  with no custom columns gets today's layout.
- The header renders company/address/reference fields, the key-crew list,
  "Day X of Y" (Y = count of days in the schedule) and the general call time.
- Department calls render as a compact table with override-then-default
  resolution.
- Catering renders the per-meal grid with totals.
- The v1 "single page" constraint is dropped: the PDF flows onto extra pages
  and repeats the header on each.
- All user-authored text (labels, blocks, values) is HTML-escaped before it
  reaches WeasyPrint.

## Testing

- Config validation: duplicate keys, bad key format, bad types, caps,
  builtin removal and builtin type change rejected.
- **Default-config parity:** with no template row, the rendered HTML has the
  same fields in the same sections as v1 (parking_notes and general_call
  absent), extending the existing PDF smoke tests.
- Merge semantics (untouched keys survive, `null` clears); unknown keys land
  in `ignored_keys`; remove-then-re-add a field restores its value; stale
  `expected_updated_at` returns 409.
- Permissions: `can_edit_call_sheet_template` gate (viewer 403, coordinator
  allowed, `False` override blocks); coordinator preset key assertion;
  invite-accept copies the capability; `test_route_enforcement.py` extended
  for the two new routes.
- Redaction: sensitive cast/crew/scene/day values hidden from a
  non-`can_view_sensitive` viewer in JSON, in cast route responses, and in
  the PDF.
- Rendering: hidden sections omitted, order respected, HTML in labels and
  values escaped, advanced schedule omitted on the last day.
- Time normalization (`HH:MM:SS` → `HH:MM`).
- Gates: full `pytest tests/` green, `npm run build` green (frontend lint
  is broken repo-wide and is not a gate).

## Rollout

1. Apply `055_call_sheet_templates.sql` to Supabase before the backend
   deploys (new table, new JSONB columns, `general_call`, capability
   columns).
2. Deploy backend, then frontend. Existing sheets and productions are
   unaffected: a missing template resolves to the v1-equivalent default.
3. No env vars, no backfill.
4. Afterwards update the backlog entry (including the multi-script
   follow-up) and `SLATEONE_FEATURES.md`.

## Open items carried forward

- Drag-and-drop reordering, multiple named templates, cross-production
  template copy.
- Multi-script shoot days; extras from `casting_groups`.
- Whether scene "TIMINGS" should become a first-class scheduled time; for
  now it is a configurable `time`/`text` scene column.
- Config `v` migration story if a `v2` shape is ever needed.
