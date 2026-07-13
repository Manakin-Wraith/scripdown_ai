# Location Manager — Nesting & Clarity — Design

**Date:** 2026-07-13
**Status:** Approved (design), pending implementation plan
**Builds on:** `2026-07-13-location-manager-sublocations-design.md` (v1, shipped)
**Areas:** `backend/routes/supabase_routes.py`, `backend/services/location_resolver.py`,
`backend/db/migrations/`, `frontend/src/components/scenes/LocationManager.jsx` (+ css),
`frontend/src/services/apiService.js`

## Problem

The shipped Location Manager (v1) has two real weaknesses, seen on a production
script:

1. **Grouping quality.** Rooms that logistically belong to one building appear as
   separate top-level locations instead of nested — e.g. `VILLA` (44 scenes) sits
   beside `GARAGE / BACKROOM`, `MOODY BACKROOM`, `SPARE ROOM`, `TAM'S ROOM`,
   `DOM & GERRIE BEDROOM`, which are all rooms *at the villa*. The script text
   gives no signal they're related (a scene reads `INT. GARAGE / BACKROOM - DAY`,
   never `INT. VILLA - GARAGE`), so no automatic derivation can nest them. The
   user must be able to nest them manually.
2. **Clarity / UX.** The panel uses raw browser `window.prompt` dialogs, shows a
   jargon `(main)` row, and never states what the tool is for.

## Goal

Keep v1's model and tree (parent › sub, rename / rename-sub / reassign / merge),
and add:

1. A manual **nest** action — file a top-level location under another so it
   becomes a **sub that keeps its own name**, and an **un-nest** to reverse it.
   Nested scenes then group and schedule with the parent. Sticky across
   re-analysis.
2. A clearer UI — inline rename (no browser prompts), no `(main)` jargon, a
   one-line purpose header.

## Non-Goals

- No "shooting location / sets" vocabulary or new paradigm — this stays V1.
- No AI-inferred or AI-suggested grouping (nesting is a manual user action).
- No changes to rename / rename-sub / reassign / merge behavior.
- Nesting is **two-level only**: a location is either top-level or a sub of one
  top-level parent. Nesting a location that already has subs under another is out
  of scope (the UI disallows it — see UX).

## Why a new operation (not merge or reassign)

- **Merge** rewrites the source's base token to the target and *discards* the
  source name — `GARAGE / BACKROOM` merged into `VILLA` becomes `VILLA`, losing
  the room. Nesting must **keep** `GARAGE / BACKROOM` as the sub.
- **Reassign-scene** rewrites the base token in place, also dropping the room, and
  acts on a single scene.
- So **nest** is genuinely new: it *prepends* the parent and keeps the original
  name as the sub, for every scene under the source location.

## Architecture

### Core operation — `nest`

`nest(script_id, source_canonical, parent_name)`:

For every scene whose `location_canonical == normalize_place(source_canonical)`:

- `set_name` = the source's display name (default = `source_canonical`; if it
  already begins with `parent_name`, strip that prefix — e.g. `VILLA, KITCHEN`
  under `VILLA` → `KITCHEN`).
- Rewrite `setting` → `{int_ext}. {parent_name} - {set_name} - {time_of_day}`
  built from the scene's existing `int_ext` / `time_of_day`, preserving the
  original tokens (do not re-derive from the old setting beyond int_ext/time).
- Set `location_canonical = normalize_place(parent_name)` (the **base**, so the
  scene nests under the parent — NOT `normalize_place("PARENT - SET")`, which was
  the v1 bug that produced `VILLA - BACKROOM` as its own node).
- Set `location_hierarchy = [parent_name, set_name]`.

Return the count of scenes updated.

**Stickiness.** Add a nullable `set_name` column to the existing `location_aliases`
table. `nest` upserts a row `{alias_place: normalize(source), canonical_place:
normalize(parent), set_name}`. `resolve_location` is extended: when a base maps to
a canonical via `location_aliases` AND that row carries a `set_name`, it also
rewrites the sub to `set_name` (prepend parent + set), so a re-analyzed scene
re-nests. This reuses the parent-alias path already in `resolve_location`.

### Reverse operation — `unnest`

`unnest(script_id, parent_canonical, set_name)`:

For every scene under `parent_canonical` whose sub-location (`derive_sub_place`)
== `normalize_place(set_name)`:

- Rewrite `setting` → `{int_ext}. {set_name} - {time_of_day}` (promote the set to
  its own place).
- Set `location_canonical = normalize_place(set_name)`.
- Set `location_hierarchy = [set_name]`.

Delete the matching `location_aliases` row(s) — those where
`canonical_place == normalize_place(parent_canonical)` AND
`set_name == set_name` (case-insensitive) — so the set does not re-nest on
re-analysis. Return the count of scenes updated.

### Endpoints

Beside the v1 location endpoints, `@require_auth` + `_user_can_access_script` → 403,
body validation → 400:

- `POST /api/scripts/<script_id>/locations/nest` — body `{ source_canonical, parent_name }`.
- `POST /api/scripts/<script_id>/locations/unnest` — body `{ parent_canonical, set_name }`.

### Migration

`backend/db/migrations/039_location_aliases_set_name.sql`:
`ALTER TABLE location_aliases ADD COLUMN IF NOT EXISTS set_name TEXT;` (nullable;
existing rows keep NULL and behave exactly as today).

## Frontend — LocationManager rework

Same file (`LocationManager.jsx`), same tree shape. Changes:

1. **Inline rename (no `window.prompt`).** Clicking a location or sub name turns
   it into a text input (Enter = save via `renameParentLocation` /
   `renameSubLocation`, Esc = cancel). Remove all four `window.prompt` calls; the
   reassign and merge prompts become inline pickers (see 3).
2. **Drop `(main)`.** A location whose scenes sit directly on it (no sub) shows
   only its count on the parent row — no phantom `(main)` child. Subs render only
   when a real sub-location exists.
3. **`Move under…` / `Move out`.**
   - Each **top-level** location row gets a `Move under… ▾` control listing the
     other top-level locations plus `Keep separate`. Selecting one calls the new
     `nestLocation(scriptId, source, parent)`. A location that already has subs is
     not offered as a *source* (two-level constraint) but can be a *target*.
   - Each **sub** row gets `Move out`, calling `unnestLocation(scriptId, parent,
     setName)`.
   - Merge stays available on top-level rows via an inline picker (existing
     `mergeParentLocations`), replacing its `window.prompt`.
4. **Purpose header:** one line under the title — *"Group your locations the way
   you'll shoot them — nest rooms and areas under the building or place they
   belong to."*
5. After any successful action, call `onChanged()` to refetch scenes (as today),
   so the tree, schedule, and reports reflect the change.

### apiService additions

- `nestLocation(scriptId, sourceCanonical, parentName)` → POST `/locations/nest`
  body `{ source_canonical, parent_name }`.
- `unnestLocation(scriptId, parentCanonical, setName)` → POST `/locations/unnest`
  body `{ parent_canonical, set_name }`.

## Data Flow

```
User picks "Move under… → VILLA" on GARAGE / BACKROOM
  -> POST /locations/nest { source_canonical: "GARAGE / BACKROOM", parent_name: "VILLA" }
     -> for each scene under GARAGE / BACKROOM:
          setting  = "INT. VILLA - GARAGE / BACKROOM - DAY"
          canonical = "VILLA"
          hierarchy = ["VILLA", "GARAGE / BACKROOM"]
     -> location_aliases upsert { alias: "GARAGE / BACKROOM", canonical: "VILLA", set_name: "GARAGE / BACKROOM" }
  -> refetch scenes
     -> tree shows GARAGE / BACKROOM under VILLA; schedule groups it in the VILLA lane
     -> re-analysis -> resolve_location applies the alias+set_name -> stays nested
```

## Error Handling / Edge Cases

- **Nest target is itself a sub** (already nested): disallow in the UI (only
  top-level locations are valid targets); backend treats an unknown/again-nested
  target as a normal parent name (no crash).
- **Nest a location that has subs:** not offered as a source in the UI (two-level
  constraint). If called directly, only its directly-attached scenes move; its
  subs are unaffected — documented, not a crash.
- **Set-name collision** (a set with that name already exists under the parent):
  the scenes simply join that set — acceptable (same physical set).
- **Unnest a set that never existed / 0 matches:** returns `scenes_updated: 0`,
  no error.
- **Alias lookup / write failures** remain non-fatal (degrade to derived base),
  matching v1.
- **`resolve_location` with a `set_name` alias** must apply parent remap first,
  then set the sub — reuse the existing ordering; a NULL `set_name` behaves
  exactly as a v1 parent alias (no regression for existing rows).

## Testing / Verification

- Backend `pytest`:
  - `resolve_location`: a `location_aliases` entry carrying `set_name` rewrites
    base → `PARENT` and sub → `set_name`; a NULL `set_name` entry behaves as today
    (regression).
  - `nest` endpoint: auth/access → 403, validation → 400, and (recording-stub, as
    in v1) that `_nest` sets `location_canonical` to the **parent base** (not the
    combined string), writes `hierarchy=[parent,set]`, and upserts the alias with
    `set_name`.
  - `unnest` endpoint: auth/validation, and that `_unnest` promotes the set and
    deletes the alias row.
- Frontend gated on `npm run build`.
- Manual: on the production script, `Move under… → VILLA` on `GARAGE / BACKROOM`;
  confirm it nests under VILLA, the schedule groups it in the VILLA lane, then
  re-analyze one of its scenes and confirm it stays nested. Inline-rename a
  location and a sub (no browser prompt appears). Confirm no `(main)` row renders.
