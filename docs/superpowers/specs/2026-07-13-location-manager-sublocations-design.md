# Location Manager with Sub-Locations & Propagating Renames — Design

**Date:** 2026-07-13
**Status:** Approved (design), pending implementation plan
**Areas:** `backend/routes/supabase_routes.py`, `backend/services/location_resolver.py`,
`frontend/src/components/scenes/` (new `LocationManager`), `frontend/src/utils/locationKey.js`,
`frontend/src/components/board/boardModel.js`, `frontend/src/services/apiService.js`

## Problem

A physical shooting location (e.g. **VILLA**) contains multiple sets / sub-locations
(**Bathroom**, **Swimming Pool**, **Driveway**). Production scheduling is done per
physical location — you shoot everything at the Villa in one block regardless of
which room each scene is set in. Today:

- The schedule board groups by **raw `setting`** (`boardModel.js:82`), so
  `INT. VILLA - BATHROOM`, `EXT. VILLA - POOL`, `EXT. VILLA - DRIVEWAY` become
  three separate lanes instead of one Villa block.
- After analysis, the user cannot **rename** a location (and have it propagate to
  all its sub-location scenes, the schedule, and reports), fix a mis-grouped
  scene, or merge duplicate parents from the UI.

## Goal

After analysis, provide a dedicated **Locations Manager** where the user can:

1. **Rename a parent location** — propagates to every scene under it (all
   sub-locations), the schedule, and reports.
2. **Rename a sub-location** — under a parent, across the scenes that use it.
3. **Reassign a scene's parent** — move one mis-grouped scene to another parent.
4. **Merge two parents** — combine AI-split duplicates into one.

And make the schedule group scenes by **physical parent location**, showing the
sub-location as a label.

## Non-Goals

- No location *entity* table. Propagation works by rewriting the existing scene
  fields (`setting`, `location_canonical`, `location_hierarchy`), which all
  downstream consumers already read. (One small alias table is added for
  sub-location stickiness — see below — mirroring `location_aliases`.)
- No changes to AI extraction of locations.

## Existing Foundations (reuse, don't rebuild)

- `scenes.setting` — raw, e.g. `"INT. VILLA - BATHROOM - DAY"`.
- `scenes.location_canonical` — normalized base/parent place, e.g. `"VILLA"`
  (the grouping/merge key). Derived by `derive_base_place()`.
- `scenes.location_hierarchy` — `["VILLA", "BATHROOM"]` (parent first).
- `location_aliases(script_id, alias_place, canonical_place, merged_by)` — sticky
  base-place remaps, applied by `_apply_location_alias()` on ingestion and edits.
- `_apply_location_alias()` already rewrites **only the base token** within a
  setting, preserving the sub-location and time-of-day — the key mechanic reused
  by every rename below. It is extended (see below) to also apply sub-location
  aliases, scoped to the parent.
- **New:** `sub_location_aliases(script_id, parent_place, alias_sub,
  canonical_sub, renamed_by)` — sticky sub-location remaps scoped to a parent,
  the direct analogue of `location_aliases` (which is base-place scoped).
- `POST /api/scripts/<id>/locations/merge` (`merge_locations`) exists but matches
  on exact full setting text and is not surfaced in the UI. It is the seed for
  the parent-merge operation, which instead keys on base place.

## Architecture

### Core primitive (backend)

`rewrite_base(scene, from_base, to_name)` — for a single scene:

1. Rewrite the parent token in `setting`: replace `from_base` → `to_name`
   (case-insensitive, base portion only), preserving sub-location + time.
2. Set `location_canonical = normalize_place(to_name)`.
3. Set `location_hierarchy[0] = to_name` (when a hierarchy exists).

All four operations are expressed in terms of this primitive plus, for parent-level
changes, a `location_aliases` upsert so re-analysis stays sticky. This mirrors the
existing `merge_locations` mechanics exactly.

### Backend operations & endpoints

All new endpoints sit beside `merge_locations`, each `@require_auth` and guarded by
`_user_can_access_script(script_id, user_id)`. They return `{ success, scenes_updated }`.

| Endpoint | Body | Behaviour |
|---|---|---|
| `POST …/locations/rename-parent` | `{ from_canonical, to_name }` | For every scene where `location_canonical == normalize(from_canonical)`: `rewrite_base`; update matching `department_items` (item_type `locations`); upsert alias `from → to`. |
| `POST …/locations/merge-parents` | `{ canonical_name, source_canonicals[] }` | Apply rename-parent for each source into `canonical_name`. |
| `POST …/locations/reassign-scene` | `{ scene_id, to_parent_name }` | Single-scene `rewrite_base`. No alias (scene-specific). |
| `POST …/locations/rename-sub` | `{ parent_canonical, from_sub, to_sub }` | For scenes under the parent whose sub-location == `from_sub`: rewrite only the sub token; `location_canonical` unchanged; upsert `sub_location_aliases(parent, from_sub → to_sub)`. |

Case-only renames preserve the user's chosen spelling verbatim (do not
`normalize_place` the target), consistent with `merge_locations`.

### Sticky sub-location renames (`_apply_location_alias` extension)

`_apply_location_alias()` is extended so sub-location renames survive
re-analysis, exactly as parent renames do:

1. Resolve the parent as today (base place + `location_aliases`).
2. Derive the scene's sub-location (`derive_sub_place`, below).
3. Look up `sub_location_aliases` for `(resolved_parent, sub)`; if found, rewrite
   the sub token in `setting` and the corresponding `location_hierarchy` element.

Ordering: parent alias is applied first (so the sub lookup is keyed on the final
parent). The lookup is best-effort and non-fatal on failure, matching the parent
path.

### Sub-location parsing (shared)

A single definition of "what is the sub-location of a scene", used by both the
manager tree and the schedule:

- **Frontend** `locationKey.js`: existing `locationKey(scene)` returns
  `location_canonical || setting`; add `subLocationLabel(scene)` — prefer
  `location_hierarchy[1..].join(' - ')`; else parse `setting` (strip INT/EXT
  prefix via the same rules as `location_resolver`, strip the base token, strip
  time-of-day words); else `''`.
- **Backend** `location_resolver.py`: a matching `derive_sub_place(setting,
  int_ext, time_of_day, location_hierarchy)` used by `rename-sub` to match scenes.

### Frontend — Locations Manager

New `LocationManager` component (dedicated view/tab). The tree is built
**client-side** from the already-loaded scenes list — no new GET endpoint:

- Group scenes by `locationKey(scene)` → parent rows (name, total scene count).
- Within each parent, group by `subLocationLabel(scene)` → sub rows (count).
- Row actions call new `apiService.js` functions (`renameParentLocation`,
  `renameSubLocation`, `reassignSceneLocation`, `mergeParentLocations`), then
  refresh scenes so the tree, schedule, and reports reflect the change.

### Scheduling propagation

`boardModel.groupScenes('location')` changes from grouping on raw `setting` to
grouping on `locationKey(scene)` (= `location_canonical`), with
`subLocationLabel(scene)` shown as the strip's secondary label. `LocationDashboard`
and `SchedulePrintView` (already imports `locationKey`) get the same grouping key.
Because renames rewrite `location_canonical`, lanes regroup automatically and
existing per-scene schedule assignments are untouched.

## Data Flow

```
User renames parent in LocationManager
  -> POST /locations/rename-parent { from_canonical, to_name }
     -> for each scene with canonical == from: rewrite_base (setting, canonical, hierarchy[0])
     -> update department_items; upsert location_aliases(from -> to)
  -> frontend refreshes scenes
     -> boardModel groups by location_canonical  => schedule regroups under new name
     -> reports read setting/location_canonical   => reflect new name
     -> re-analysis applies location_aliases       => rename stays sticky
```

## Error Handling / Edge Cases

- **Rename collides with an existing parent** → effectively a merge (both group
  under the same canonical). The manager warns before applying.
- **Both parent and sub renames are sticky across re-analysis.** Parents persist
  via `location_aliases` (base-place keyed); sub-locations via
  `sub_location_aliases` (parent+sub keyed). `_apply_location_alias` applies the
  parent remap first, then the sub remap scoped to the resolved parent, so a
  re-analyzed scene keeps both. A sub alias is scoped to its parent, so renaming
  `POOL → SWIMMING POOL` under `VILLA` never touches a `POOL` under another parent.
- **Case-only rename** preserves the chosen spelling verbatim.
- **Concurrency** — last-write-wins per scene; acceptable for this workflow.
- **Alias lookup failure** is non-fatal (degrades to derived base place), matching
  existing `_apply_location_alias` behaviour.

## Testing / Verification

- Backend `pytest` per operation: base-token rewrite preserves sub + time;
  rename-parent updates all sub-location scenes and upserts the alias; rename-sub
  leaves `location_canonical` unchanged and upserts a parent-scoped sub alias;
  `_apply_location_alias` re-applies both parent and sub aliases (and a sub alias
  scoped to one parent does not affect the same sub name under another parent);
  reassign-scene touches one scene; merge folds sources into target; auth/access
  enforced (403 for non-members).
- Frontend gated on `npm run build` (`npm run lint` is known broken).
- Manual: rename a parent with multiple sub-locations, confirm the schedule board
  regroups those scenes into one lane and a production report shows the new name.
