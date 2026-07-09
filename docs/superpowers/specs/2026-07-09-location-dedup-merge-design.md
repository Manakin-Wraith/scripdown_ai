# Location Deduplication & Merge — Design Spec

**Date:** 2026-07-09
**Status:** Approved for planning
**Author:** Brainstorming session

## Problem

Locations accumulate as duplicates. A location is stored only as the free-text
`scenes.setting` string (e.g. `INT. COFFEE SHOP - DAY`), produced by three
different ingest paths (ScreenPy grammar parser, regex fallback, AI enhancement).
Every aggregation across the app — the `process_locations_job` worker, `SELECT
DISTINCT setting` in the overview job, `report_service.py`, and the frontend
location/schedule components — keys on the **exact raw string**. There is zero
canonicalization or fuzzy merging anywhere.

Consequently `COFFEE SHOP`, `THE COFFEE SHOP`, and `COFEE SHOP` (typo) are three
distinct locations in every count, list, report, and stripboard. `AddSceneModal`
is a free-text input with no lookup, so typos actively spawn new locations.

The **character** system already solves the equivalent problem via a
manual-merge + persistent-alias design (`character_aliases` table, migration
031; `POST /api/scripts/<id>/characters/merge`; a prevention hook on scene
writes). This spec ports that design to locations **and adds automatic
merge suggestions**, which characters do not have.

## Goals

1. Let a user merge duplicate locations, with the merge sticking permanently
   (re-analysis must not resurrect a merged-away duplicate).
2. **Automatically suggest** likely-duplicate locations (articles/spacing/case
   differences + true typos), surfaced in the UI. The merge itself stays
   **user-confirmed** — nothing auto-merges silently.
3. Deduplicate on the **base physical place** — ignore `INT/EXT` and
   time-of-day. `INT. COFFEE SHOP - DAY` and `EXT. COFFEE SHOP - NIGHT` are the
   same location "COFFEE SHOP".
4. Canonicalization must **reach into production views**: schedule
   "unique locations" stat, report groupings, and the Location Dashboard all
   collapse INT/EXT/TOD variants of a place into one location.

## Non-Goals

- No full normalized `locations` entity table with FK references from scenes
  (considered and rejected — too broad for "do the same as characters").
- No silent auto-merge on ingest (rejected — risks wrongly merging genuinely
  different places).
- No change to how INT/EXT or time-of-day themselves are parsed or stored.

## Design Decisions (locked during brainstorming)

| Decision | Choice |
|---|---|
| How far to go | Mirror characters (manual merge + alias table + prevention hook) **plus** automatic fuzzy suggestions |
| Merge key | **Base place name only** — strip INT/EXT and time-of-day |
| Reach of canonicalization | **Collapse to one physical place** in production counts/lists, not just spelling fix |
| Canonical storage | New stored `scenes.location_canonical` column (derive once at write-time) |
| Fuzzy method | `difflib.SequenceMatcher` (stdlib, no new dependency), ~0.82 threshold + short-string guards, after deterministic normalization |

### Why a stored `location_canonical` column

Characters merge cleanly because they are discrete JSONB array elements.
Locations are messy free-text from three ingest paths, and the "collapse to one
physical place" requirement means aggregation must group on base place. If we
re-derived "base place out of `setting`" independently in the worker, in
`report_service.py`, and in ~5 frontend components, that logic would drift.
Instead we derive it **once at write-time** into `scenes.location_canonical`,
and every aggregation groups on that column. Frontend reads the field directly
rather than re-parsing.

## Architecture — 7 components, each mirroring a character equivalent

### 1. `backend/services/location_resolver.py` (new — mirrors `entity_resolver.py`)

Pure functions, unit-testable in isolation.

- `derive_base_place(setting, int_ext=None, time_of_day=None, location_hierarchy=None) -> str`
  Returns the normalized base place. Logic:
  1. Prefer structured `location_hierarchy[0]` / `location_parent` when present
     (populated by the ScreenPy path).
  2. Otherwise parse `setting`: strip a leading `INT.`/`EXT.`/`INT./EXT.`
     prefix and a trailing time-of-day segment (`- DAY`, `- NIGHT`, etc.),
     reusing the existing patterns in `screenplay_parser._parse_location_hierarchy`
     and `_location_type_to_str`.
  3. `normalize_place(name)`: uppercase, collapse internal whitespace, strip a
     leading article (`THE`/`A`/`AN`), strip surrounding punctuation.
  Must be robust to the scene_enhancer rebuild form
  (`"{setting} - {int_ext} - {time_of_day}"`) which can append INT/EXT/TOD
  redundantly.

- `suggest_merges(base_places: list[str]) -> list[dict]`
  Clusters near-duplicate base places for a script.
  - Deterministic normalization first (catches article/spacing/case:
    `"THE COFFEE SHOP"` ≈ `"Coffee Shop"`).
  - Then `difflib.SequenceMatcher(None, a, b).ratio()` on normalized forms for
    true typos (`"COFEE SHOP"` ≈ `"COFFEE SHOP"`), threshold ~**0.82**, with a
    short-string guard (skip when either normalized name is < 4 chars, to avoid
    `"BAR"` ≈ `"CAR"` false positives).
  - Returns groups: `{ canonical, members: [...], reason: "typo"|"variant" }`.
    Proposed `canonical` = most frequent member (tie-break: shortest).
  - **Never applies** — suggestion only. Excludes pairs already recorded in
    `location_aliases`.

### 2. `scenes.location_canonical` column (new migration + backfill)

- Migration `034_add_scenes_location_canonical.sql`: `ALTER TABLE scenes ADD
  COLUMN location_canonical TEXT;` + index `idx_scenes_location_canonical
  (script_id, location_canonical)`.
- Populated wherever `setting` is written: upload/extraction, AI analysis scene
  write, manual scene edit, and merge.
- Backfill script `scripts/backfill_location_canonical.py`: derive
  `location_canonical` for every existing scene via `derive_base_place`, applying
  any existing `location_aliases`.

### 3. `location_aliases` table (new migration — mirrors `031_character_aliases.sql`)

Migration `035_location_aliases.sql`:
```sql
CREATE TABLE IF NOT EXISTS location_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    canonical_place TEXT NOT NULL,
    alias_place TEXT NOT NULL,
    merged_by UUID REFERENCES auth.users(id),
    merged_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(script_id, alias_place)
);
CREATE INDEX idx_location_aliases_script ON location_aliases(script_id);
CREATE INDEX idx_location_aliases_lookup ON location_aliases(script_id, alias_place);
```
RLS identical to `character_aliases`: script owner FOR ALL; team members FOR
SELECT (via `script_members`).

### 4. Merge + read endpoints (new — mirror the character routes)

In `backend/routes/supabase_routes.py`:

- `POST /api/scripts/<script_id>/locations/merge` (`@require_auth`) —
  body `{ canonical_place, aliases: [...] }`. Mirrors `merge_characters`:
  1. Normalize `canonical_place` and `aliases` (uppercase, strip, dedupe,
     drop canonical from aliases).
  2. Fetch scenes; for each scene whose derived base place ∈ aliases: rewrite
     the **place substring inside `setting`** (preserving INT/EXT + TOD) to the
     canonical place, and set `location_canonical = canonical_place`.
  3. Update matching `department_items` rows (`item_type = 'locations'`).
  4. Upsert each mapping into `location_aliases`
     (`on_conflict='script_id,alias_place'`).
  5. Return `{ success, canonical_place, aliases_merged, scenes_updated,
     total_scenes }`.

- `GET /api/scripts/<script_id>/locations/aliases` (`@optional_auth`) — returns
  `{ alias_map: {alias_place: canonical_place}, aliases: [...] }`. Mirrors
  `get_character_aliases`.

- `GET /api/scripts/<script_id>/locations/suggestions` (`@optional_auth`) —
  **net-new**. Collects distinct base places for the script, calls
  `suggest_merges`, returns candidate groups. Feeds the review panel.

Corresponding `apiService.js` methods: `mergeLocations`,
`getLocationAliases`, `getLocationSuggestions` (mirror `mergeCharacters` /
`getCharacterAliases` at `apiService.js:2046`).

### 5. Prevention hook (mirrors the `character_aliases` remap)

At every scene analysis write (the two sites in `supabase_routes.py` that
currently remap `character_aliases`, ~L2756 and ~L3270): after computing the
scene's `setting`, look up `location_aliases` for the script, derive the base
place, remap alias → canonical, and rebuild both `setting` (place substring
replaced) and `location_canonical`. Non-fatal on lookup failure, matching the
character hook's `try/except`.

### 6. Aggregation grouping (deliver the "collapse" requirement)

Switch location grouping keys from raw `setting` to `location_canonical`
(fallback to `derive_base_place(setting)` when the column is null, for safety
pre-backfill):

- **Backend worker** `analysis_worker.py`: `process_locations_job` buckets by
  `location_canonical` instead of `setting`; overview job uses `DISTINCT
  location_canonical`; `process_location_detail_job` matches on
  `location_canonical`.
- **Reports** `report_service.py`: `defaultdict` grouping (~L630) and the filter
  dimension `set()` (~L487) key on `location_canonical`.
- **Frontend** components read `scene.location_canonical` for grouping:
  `SceneViewer.jsx` (`locs` build ~L201), `LocationList.jsx`,
  `LocationDashboard.jsx`, and the schedule/stripboard unique-location stats
  (`DayColumn.jsx`, `SchedulePrintView.jsx`, `SelectionSummary.jsx`).
  Display of the full `setting` (with INT/EXT/TOD) is unchanged; only the
  **grouping key** changes.

### 7. Frontend suggestions review panel (net-new UX)

- A "Review location merges" panel (co-located with the existing location UI —
  `ScriptSummary.jsx` hosts the character merge today; locations panel lives
  near `LocationList.jsx` / `LocationDashboard.jsx`). It calls
  `getLocationSuggestions`, lists each suggested group ("These look like the
  same location — merge?"), lets the user pick/adjust the canonical, and
  confirms via `mergeLocations`. Nothing merges without an explicit click.
- A manual merge control (select 2+ locations → choose canonical → merge) for
  cases the suggester misses, mirroring the character merge affordance.

## Data Flow

```
INGEST (upload / AI / manual edit)
   setting written ──► derive_base_place() ──► apply location_aliases map
                                                    │
                                                    ▼
                              scenes.setting (place substring canonicalized)
                              scenes.location_canonical (grouping key)
   ────────────────────────────────────────────────────────────────────────
AGGREGATION (worker / reports / frontend)  ──► GROUP BY location_canonical
   ────────────────────────────────────────────────────────────────────────
SUGGEST:  distinct location_canonical ──► suggest_merges() ──► review panel
   ────────────────────────────────────────────────────────────────────────
USER MERGE: POST /locations/merge
   ├─ rewrite scenes.setting place substring + location_canonical
   ├─ update department_items (item_type='locations')
   └─ upsert location_aliases  ──► (feeds prevention hook on next write)
```

## Error Handling

- All alias-table lookups in the prevention hook are wrapped `try/except` and
  are non-fatal (parity with the character hook) — a lookup failure degrades to
  "no remap", never blocks the scene write.
- `department_items` updates per alias are individually wrapped so one failure
  doesn't abort the merge.
- Merge endpoint validates `canonical_place` non-empty and `aliases` a non-empty
  list; returns 400 otherwise.
- Backfill script is idempotent (re-deriving is deterministic) and safe to
  re-run.

## Testing

- **Unit — `location_resolver`:**
  - `derive_base_place` across all three setting formats (ScreenPy structured,
    regex `INT. X - DAY`, AI rebuild `X - INT - DAY`), article/whitespace
    normalization, and the scene_enhancer redundant-suffix form.
  - `suggest_merges`: typo cluster (`COFEE SHOP`/`COFFEE SHOP`), article variant
    (`THE COFFEE SHOP`/`COFFEE SHOP`), short-string false-positive guard
    (`BAR`/`CAR` must NOT cluster), and exclusion of already-aliased pairs.
- **Integration — merge endpoint:** setting place-substring rewrite preserves
  INT/EXT/TOD; `location_canonical` updated; `location_aliases` persisted;
  re-running analysis on a scene does **not** resurrect the merged-away spelling
  (prevention hook verified).
- **Aggregation:** worker/report grouping collapses INT-day + EXT-night of the
  same place into one location.

## Migration / Rollout

1. Ship migrations `034` (column) and `035` (`location_aliases` table).
2. Run `backfill_location_canonical.py` against existing scenes.
3. Deploy backend (resolver, endpoints, hook, aggregation changes).
4. Deploy frontend (grouping reads `location_canonical`, suggestions panel).

Aggregation reads fall back to `derive_base_place(setting)` when
`location_canonical` is null, so backend can deploy before backfill completes
without breaking counts.

## Open Questions / Risks

- **Setting rewrite fidelity:** replacing only the place substring inside a
  free-text `setting` must not corrupt INT/EXT/TOD. Mitigation: rewrite via the
  same parse that `derive_base_place` uses (reconstruct `setting` from parsed
  parts) rather than a blind string replace, where structured parts are
  available.
- **Fuzzy threshold tuning:** 0.82 is a starting point; may need adjustment
  after seeing real suggestion quality. Threshold lives in one constant in
  `location_resolver`.
