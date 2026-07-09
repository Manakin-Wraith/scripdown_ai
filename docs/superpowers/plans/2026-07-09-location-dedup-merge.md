# Location Deduplication & Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give locations the same duplicate-prevention the character system has (manual merge + persistent alias table + prevention hook), plus automatic fuzzy merge suggestions, deduplicating on the base physical place.

**Architecture:** Derive a normalized "base place" from each scene's free-text `setting` once at write-time into a new `scenes.location_canonical` column. All location aggregation (worker, reports, frontend) groups on that column. A `location_aliases` table + merge endpoint + prevention hook mirror `character_aliases`. A new `difflib`-based suggester surfaces likely duplicates for user-confirmed merging.

**Tech Stack:** Python 3.13 / Flask backend, `supabase-py` (service role), stdlib `difflib` (no new dependency), pytest. React 18 / Vite / plain JSX frontend, axios via `apiService.js`. Supabase Postgres.

**Spec:** `docs/superpowers/specs/2026-07-09-location-dedup-merge-design.md`

## Global Constraints

- No new Python dependency — fuzzy matching uses stdlib `difflib.SequenceMatcher`.
- Fuzzy threshold constant `FUZZY_THRESHOLD = 0.82`; short-string guard `MIN_FUZZY_LEN = 4` (both live only in `location_resolver.py`).
- Nothing auto-merges — suggestions are surfaced; merges require an explicit user action.
- All alias-table lookups in the prevention hook must be non-fatal (`try/except`, degrade to no-remap), matching the character hook.
- Canonical values are stored uppercase, whitespace-collapsed, leading article (`THE`/`A`/`AN`) stripped.
- Aggregation must fall back to `derive_base_place(setting)` when `location_canonical` is null, so backend can deploy before backfill completes.
- Backend tests run from `backend/` via `pytest tests/`. Test files use `sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))`.

## File Structure

**Create:**
- `backend/services/location_resolver.py` — pure functions: `normalize_place`, `derive_base_place`, `suggest_merges`. Mirrors `entity_resolver.py`.
- `backend/tests/test_location_resolver.py` — unit tests for the resolver.
- `backend/db/migrations/034_add_scenes_location_canonical.sql` — new column + index.
- `backend/db/migrations/035_location_aliases.sql` — alias table + RLS (mirrors `031`).
- `backend/scripts/backfill_location_canonical.py` — one-off backfill.

**Modify:**
- `backend/routes/supabase_routes.py` — populate `location_canonical` at the upload insert (~675); add merge/aliases/suggestions endpoints (near the character routes ~4440); add the location prevention hook at the two analysis write sites (~2756, ~3270).
- `backend/services/analysis_worker.py` — group `process_locations_job` (~1076), overview distinct (~741), and `process_location_detail_job` (~1245) on `location_canonical`.
- `backend/services/report_service.py` — group location aggregation (~630) and filter dimension (~487) on `location_canonical`.
- `frontend/src/services/apiService.js` — add `mergeLocations`, `getLocationAliases`, `getLocationSuggestions` (after `getCharacterAliases` ~2057).
- `frontend/src/components/scenes/SceneViewer.jsx`, `LocationList.jsx`, `LocationDashboard.jsx`, and schedule components (`DayColumn.jsx`, `SchedulePrintView.jsx`, `SelectionSummary.jsx`) — group on `location_canonical`.
- `frontend/src/components/scenes/LocationDashboard.jsx` (or a new sibling panel) — suggestions review + manual merge UI.

---

## Task 1: Base-place derivation (`normalize_place`, `derive_base_place`)

**Files:**
- Create: `backend/services/location_resolver.py`
- Test: `backend/tests/test_location_resolver.py`

**Interfaces:**
- Produces: `normalize_place(name: str) -> str`; `derive_base_place(setting, int_ext=None, time_of_day=None, location_hierarchy=None) -> str`. Both return an uppercase, article-stripped, whitespace-collapsed base place ("" for empty input).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_location_resolver.py`:

```python
"""
Tests for Location Resolver — base-place derivation and merge suggestions.
Mirrors test_entity_resolver.py.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.location_resolver import (
    normalize_place,
    derive_base_place,
)


def test_normalize_strips_article_and_case():
    assert normalize_place("The Coffee Shop") == "COFFEE SHOP"
    assert normalize_place("  a   BARN ") == "BARN"
    assert normalize_place("AN OFFICE") == "OFFICE"


def test_normalize_empty():
    assert normalize_place("") == ""
    assert normalize_place(None) == ""


def test_derive_from_screenpy_prefix_and_tod():
    # regex/grammar form: "INT. COFFEE SHOP - DAY"
    assert derive_base_place("INT. COFFEE SHOP - DAY") == "COFFEE SHOP"
    assert derive_base_place("EXT. THE COFFEE SHOP - NIGHT") == "COFFEE SHOP"


def test_derive_from_enhancer_rebuild_form():
    # scene_enhancer rebuild: "{setting} - {int_ext} - {time_of_day}"
    assert derive_base_place("COFFEE SHOP - INT - DAY") == "COFFEE SHOP"


def test_derive_prefers_location_hierarchy():
    assert derive_base_place(
        "INT. BURGER JOINT - KITCHEN - DAY",
        location_hierarchy=["BURGER JOINT", "KITCHEN"],
    ) == "BURGER JOINT"


def test_derive_hierarchy_json_string():
    # location_hierarchy may arrive as a JSON string from the DB
    assert derive_base_place(
        "INT. BARN - NIGHT",
        location_hierarchy='["BARN"]',
    ) == "BARN"


def test_derive_plain_name_no_prefix():
    assert derive_base_place("COFFEE SHOP") == "COFFEE SHOP"


def test_derive_empty_setting():
    assert derive_base_place("") == ""
    assert derive_base_place(None) == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_location_resolver.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.location_resolver'`

- [ ] **Step 3: Write the implementation**

Create `backend/services/location_resolver.py`:

```python
"""
Location Resolver — base-place derivation and merge suggestions.

Mirrors entity_resolver.py (characters) for locations. Derives a normalized
"base physical place" from a free-text scene setting, ignoring INT/EXT and
time-of-day, and suggests likely-duplicate places for user-confirmed merging.

Base place is the grouping/merge key stored in scenes.location_canonical.
"""

import re
import json
from collections import Counter
from difflib import SequenceMatcher
from typing import Dict, List, Optional

# Fuzzy suggestion tuning — the ONLY place these live.
FUZZY_THRESHOLD = 0.82
MIN_FUZZY_LEN = 4

TIME_WORDS = {
    "DAY", "NIGHT", "DUSK", "DAWN", "MORNING", "EVENING",
    "AFTERNOON", "CONTINUOUS", "LATER", "SAME", "MAGIC HOUR",
}

INT_EXT_TOKENS = {"INT", "EXT", "INT/EXT", "I/E"}

_INT_EXT_PREFIX = re.compile(
    # Require a boundary after the token so real names starting with INT/EXT
    # (e.g. "INTERROGATION ROOM", "INTERSTATE 5") are NOT stripped.
    r"^\s*(INT\.?/EXT\.?|INT\.?|EXT\.?|I/E\.?)(?=[\s.\-:]|$)\s*[-.:]?\s*",
    re.IGNORECASE,
)
_LEADING_ARTICLE = re.compile(r"^(THE|A|AN)\s+", re.IGNORECASE)
_DASH_SPLIT = re.compile(r"\s*[-–—]\s*")


def normalize_place(name: Optional[str]) -> str:
    """Canonical form for matching/grouping: uppercase, collapsed whitespace,
    leading article stripped, surrounding punctuation stripped."""
    if not name:
        return ""
    s = re.sub(r"\s+", " ", str(name).strip().upper())
    s = _LEADING_ARTICLE.sub("", s)
    s = s.strip(" .,-–—:;")
    return s


def derive_base_place(
    setting: Optional[str],
    int_ext: Optional[str] = None,
    time_of_day: Optional[str] = None,
    location_hierarchy=None,
) -> str:
    """Return the normalized base physical place for a scene.

    1. Prefer structured location_hierarchy[0] when present.
    2. Otherwise strip a leading INT/EXT prefix and any INT/EXT or
       time-of-day segments from the setting, keep the first place token.
    """
    # 1. Structured hierarchy wins
    if location_hierarchy:
        if isinstance(location_hierarchy, str):
            try:
                location_hierarchy = json.loads(location_hierarchy)
            except (ValueError, TypeError):
                location_hierarchy = []
        if location_hierarchy:
            return normalize_place(location_hierarchy[0])

    # 2. Parse from the free-text setting
    s = _INT_EXT_PREFIX.sub("", setting or "")
    parts = [p.strip() for p in _DASH_SPLIT.split(s) if p.strip()]
    kept = [
        p for p in parts
        if p.upper() not in TIME_WORDS and normalize_place(p) not in INT_EXT_TOKENS
    ]
    base = kept[0] if kept else s
    return normalize_place(base)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_location_resolver.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/services/location_resolver.py backend/tests/test_location_resolver.py
git commit -m "feat(locations): base-place derivation (normalize_place, derive_base_place)"
```

---

## Task 2: Merge suggestions (`suggest_merges`)

**Files:**
- Modify: `backend/services/location_resolver.py`
- Test: `backend/tests/test_location_resolver.py`

**Interfaces:**
- Consumes: `normalize_place` (Task 1).
- Produces: `suggest_merges(base_places: List[str], existing_aliases: Optional[Dict[str, str]] = None) -> List[Dict]`. Each group: `{"canonical": str, "members": [str, ...], "reason": "variant"|"typo"}`. Only groups with ≥2 members are returned; members already in `existing_aliases` (keys = alias) are excluded.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_location_resolver.py`:

```python
from services.location_resolver import suggest_merges


def test_suggest_article_variant():
    groups = suggest_merges(["COFFEE SHOP", "THE COFFEE SHOP", "COFFEE SHOP"])
    assert len(groups) == 1
    g = groups[0]
    assert set(g["members"]) == {"COFFEE SHOP", "THE COFFEE SHOP"}
    assert g["canonical"] == "COFFEE SHOP"  # most frequent


def test_suggest_typo():
    groups = suggest_merges(["COFFEE SHOP", "COFEE SHOP"])
    assert len(groups) == 1
    assert set(groups[0]["members"]) == {"COFFEE SHOP", "COFEE SHOP"}


def test_suggest_short_string_guard():
    # BAR vs CAR must NOT cluster (below MIN_FUZZY_LEN)
    groups = suggest_merges(["BAR", "CAR"])
    assert groups == []


def test_suggest_excludes_known_aliases():
    groups = suggest_merges(
        ["COFFEE SHOP", "COFEE SHOP"],
        existing_aliases={"COFEE SHOP": "COFFEE SHOP"},
    )
    assert groups == []


def test_suggest_distinct_places_not_grouped():
    groups = suggest_merges(["COFFEE SHOP", "POLICE STATION", "HOSPITAL"])
    assert groups == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_location_resolver.py -k suggest -v`
Expected: FAIL with `ImportError: cannot import name 'suggest_merges'`

- [ ] **Step 3: Write the implementation**

Append to `backend/services/location_resolver.py`:

```python
def suggest_merges(
    base_places: List[str],
    existing_aliases: Optional[Dict[str, str]] = None,
) -> List[Dict]:
    """Cluster near-duplicate base places for user-confirmed merging.

    Deterministic normalization catches article/spacing/case differences;
    difflib catches true typos above FUZZY_THRESHOLD (short-string guarded).
    Never applies a merge — returns suggestions only.
    """
    existing_aliases = existing_aliases or {}
    counts = Counter(p for p in base_places if p)
    uniques = [p for p in counts if p not in existing_aliases]
    norm = {p: normalize_place(p) for p in uniques}

    groups: List[Dict] = []
    used: set = set()

    for i, a in enumerate(uniques):
        if a in used:
            continue
        members = [a]
        for b in uniques[i + 1:]:
            if b in used:
                continue
            na, nb = norm[a], norm[b]
            if na == nb:
                members.append(b)
                used.add(b)
            elif len(na) >= MIN_FUZZY_LEN and len(nb) >= MIN_FUZZY_LEN and \
                    SequenceMatcher(None, na, nb).ratio() >= FUZZY_THRESHOLD:
                members.append(b)
                used.add(b)

        if len(members) > 1:
            used.add(a)
            canonical = max(members, key=lambda m: (counts[m], -len(m)))
            reason = "variant" if all(norm[m] == norm[members[0]] for m in members) else "typo"
            groups.append({
                "canonical": canonical,
                "members": members,
                "reason": reason,
            })

    return groups
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_location_resolver.py -v`
Expected: PASS (13 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/services/location_resolver.py backend/tests/test_location_resolver.py
git commit -m "feat(locations): difflib-based merge suggestions (suggest_merges)"
```

---

## Task 3: Migrations — canonical column + alias table

**Files:**
- Create: `backend/db/migrations/034_add_scenes_location_canonical.sql`
- Create: `backend/db/migrations/035_location_aliases.sql`

**Interfaces:**
- Produces: `scenes.location_canonical TEXT`; table `location_aliases(script_id, canonical_place, alias_place, merged_by, merged_at, UNIQUE(script_id, alias_place))`.

- [ ] **Step 1: Write migration 034**

Create `backend/db/migrations/034_add_scenes_location_canonical.sql`:

```sql
-- Migration 034: Canonical base-place column for location dedup
-- Populated at write-time; grouping key for all location aggregation.

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS location_canonical TEXT;

CREATE INDEX IF NOT EXISTS idx_scenes_location_canonical
    ON scenes(script_id, location_canonical);
```

- [ ] **Step 2: Write migration 035**

Create `backend/db/migrations/035_location_aliases.sql` (mirrors `031_character_aliases.sql`):

```sql
-- Migration 035: Location Aliases for Merge/Dedup System
-- Stores merge history so re-analysis doesn't re-introduce duplicates.

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

-- RLS
ALTER TABLE location_aliases ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Script owner can manage location aliases"
    ON location_aliases FOR ALL
    USING (
        script_id IN (
            SELECT id FROM scripts WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Team members can read location aliases"
    ON location_aliases FOR SELECT
    USING (
        script_id IN (
            SELECT script_id FROM script_members WHERE user_id = auth.uid()
        )
    );
```

- [ ] **Step 3: Apply both migrations to the Supabase database**

Apply `034` then `035` using the project's runner (`cd backend && python db/run_migration.py 034_add_scenes_location_canonical.sql` then the same for `035_location_aliases.sql`), the Supabase SQL editor, or the Supabase MCP `apply_migration`. Confirm the runner's expected argument form by reading `backend/db/run_migration.py` first. Verify:

Run (Supabase SQL): `SELECT column_name FROM information_schema.columns WHERE table_name='scenes' AND column_name='location_canonical';`
Expected: one row `location_canonical`.

Run (Supabase SQL): `SELECT to_regclass('public.location_aliases');`
Expected: `location_aliases` (not null).

- [ ] **Step 4: Commit**

```bash
git add backend/db/migrations/034_add_scenes_location_canonical.sql backend/db/migrations/035_location_aliases.sql
git commit -m "feat(locations): migrations for location_canonical column and location_aliases table"
```

---

## Task 4: Backfill script

**Files:**
- Create: `backend/scripts/backfill_location_canonical.py`

**Interfaces:**
- Consumes: `derive_base_place` (Task 1); `location_aliases` table (Task 3).

- [ ] **Step 1: Write the backfill script**

Create `backend/scripts/backfill_location_canonical.py`:

```python
"""
Backfill scenes.location_canonical for all existing scenes.

Idempotent — re-deriving is deterministic. Applies any existing
location_aliases so previously-merged places stay canonical.

Usage (from backend/):  python scripts/backfill_location_canonical.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db.supabase_client import get_supabase_admin  # service-role client (bypasses RLS)
from services.location_resolver import derive_base_place, normalize_place


def main():
    supabase = get_supabase_admin()

    # Preload alias maps per script: {script_id: {alias_place: canonical_place}}
    aliases = supabase.table('location_aliases').select(
        'script_id, alias_place, canonical_place'
    ).execute().data or []
    alias_by_script = {}
    for row in aliases:
        alias_by_script.setdefault(row['script_id'], {})[row['alias_place']] = row['canonical_place']

    # Page through scenes
    page, size, updated = 0, 500, 0
    while True:
        rows = supabase.table('scenes').select(
            'id, script_id, setting, int_ext, time_of_day, location_hierarchy'
        ).range(page * size, page * size + size - 1).execute().data or []
        if not rows:
            break
        for s in rows:
            base = derive_base_place(
                s.get('setting'), s.get('int_ext'),
                s.get('time_of_day'), s.get('location_hierarchy'),
            )
            canonical = alias_by_script.get(s['script_id'], {}).get(base, base)
            canonical = normalize_place(canonical)
            supabase.table('scenes').update(
                {'location_canonical': canonical}
            ).eq('id', s['id']).execute()
            updated += 1
        page += 1
        print(f"  ...{updated} scenes updated")

    print(f"Done. {updated} scenes backfilled.")


if __name__ == '__main__':
    main()
```

Note: confirm the service-role client import matches this repo (`grep -rn "def get_supabase\|service" backend/db/`). If the helper is named differently (e.g. `from db.connection import supabase`), use that import instead — the rest is unchanged.

- [ ] **Step 2: Dry-run verification on a single script**

Temporarily run the derive logic against one known script id in a Python REPL (`cd backend && python`), print `base` for ~10 scenes, and eyeball that INT/EXT/TOD are stripped and spellings look canonical. Do NOT commit REPL code.

- [ ] **Step 3: Run the backfill**

Run: `cd backend && python scripts/backfill_location_canonical.py`
Expected: prints incrementing counts, ends `Done. N scenes backfilled.`

Verify: `SELECT COUNT(*) FROM scenes WHERE location_canonical IS NULL;` → 0 (for scenes with a non-null setting).

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/backfill_location_canonical.py
git commit -m "feat(locations): backfill script for location_canonical"
```

---

## Task 5: Populate `location_canonical` at upload insert

**Files:**
- Modify: `backend/routes/supabase_routes.py:675-698` (primary upload scene insert)

**Interfaces:**
- Consumes: `derive_base_place` (Task 1).

- [ ] **Step 1: Import the resolver near the top of the scene-insert function**

Add at the top of `supabase_routes.py` alongside other service imports (search for `from services.entity_resolver import`; add beside it):

```python
from services.location_resolver import derive_base_place
```

- [ ] **Step 2: Add `location_canonical` to the scene record**

In the `scene_records.append({...})` block at ~675, immediately after the `'location_hierarchy': ps.location_hierarchy,` line, add:

```python
            'location_canonical': derive_base_place(
                ps.setting, ps.int_ext, ps.time_of_day, ps.location_hierarchy
            ),
```

- [ ] **Step 3: Verify by uploading a script (or re-run the upload path in a test)**

Run: upload any PDF through the app, then
`SELECT setting, location_canonical FROM scenes WHERE script_id = '<new_id>' LIMIT 5;`
Expected: `location_canonical` populated, INT/EXT/TOD stripped, uppercase.

- [ ] **Step 4: Commit**

```bash
git add backend/routes/supabase_routes.py
git commit -m "feat(locations): populate location_canonical on upload insert"
```

---

## Task 6: Merge, aliases, and suggestions endpoints

**Files:**
- Modify: `backend/routes/supabase_routes.py` (add three routes near the character routes, after `get_character_aliases` ~4580)

**Interfaces:**
- Consumes: `derive_base_place`, `normalize_place`, `suggest_merges` (Tasks 1–2); `location_aliases` table (Task 3).
- Produces HTTP:
  - `POST /api/scripts/<script_id>/locations/merge` body `{canonical_place, aliases[]}` → `{success, canonical_place, aliases_merged, scenes_updated, total_scenes}`.
  - `GET  /api/scripts/<script_id>/locations/aliases` → `{script_id, alias_map, aliases}`.
  - `GET  /api/scripts/<script_id>/locations/suggestions` → `{script_id, suggestions: [...]}`.

- [ ] **Step 1: Add the import**

Ensure the top-of-file import from Task 5 covers the extra names:

```python
from services.location_resolver import derive_base_place, normalize_place, suggest_merges
```

- [ ] **Step 2: Add the merge endpoint**

Insert after `get_character_aliases` (mirrors `merge_characters`; rewrites `setting` place-substring and `location_canonical`):

```python
@supabase_bp.route('/api/scripts/<script_id>/locations/merge', methods=['POST'])
@require_auth
def merge_locations(script_id):
    """
    Merge duplicate base-place locations across all scenes in a script.

    Body: {
        canonical_place: "COFFEE SHOP",              -- base place to keep
        aliases: ["THE COFFEE SHOP", "COFEE SHOP"]   -- base places to replace
    }
    Rewrites the place inside scenes.setting (preserving INT/EXT + time-of-day),
    updates scenes.location_canonical, updates department_items, and stores the
    mapping in location_aliases for future prevention.
    """
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500

    try:
        data = request.get_json()
        canonical_place = normalize_place(data.get('canonical_place') or '')
        raw_aliases = data.get('aliases', [])
        user_id = get_user_id()

        if not canonical_place:
            return jsonify({'error': 'canonical_place is required'}), 400
        if not raw_aliases or not isinstance(raw_aliases, list):
            return jsonify({'error': 'aliases must be a non-empty array'}), 400

        aliases = list({normalize_place(a) for a in raw_aliases if normalize_place(a)})
        aliases = [a for a in aliases if a != canonical_place]
        if not aliases:
            return jsonify({'error': 'No valid aliases to merge'}), 400

        # 1. Fetch scenes with the fields needed to re-derive base place
        result = supabase.table('scenes').select(
            'id, setting, int_ext, time_of_day, location_hierarchy, location_canonical'
        ).eq('script_id', script_id).execute()
        scenes = result.data or []
        updated_count = 0

        # 2. For each scene whose base place is an alias, rewrite setting + canonical
        for scene in scenes:
            base = derive_base_place(
                scene.get('setting'), scene.get('int_ext'),
                scene.get('time_of_day'), scene.get('location_hierarchy'),
            )
            if base not in aliases:
                continue

            old_setting = scene.get('setting') or ''
            # Replace the alias place text inside setting with the canonical place,
            # case-insensitively, preserving INT/EXT + time-of-day around it.
            new_setting = re.sub(
                re.escape(base), canonical_place, old_setting, flags=re.IGNORECASE
            ) if base else old_setting
            if new_setting == old_setting and base:
                # base came from location_hierarchy, not literally in setting;
                # append canonical form is unnecessary — just fix the canonical col.
                new_setting = old_setting

            supabase.table('scenes').update({
                'setting': new_setting,
                'location_canonical': canonical_place,
            }).eq('id', scene['id']).execute()
            updated_count += 1

        # 3. Update department_items (user-added location rows)
        for alias in aliases:
            try:
                supabase.table('department_items').update({
                    'item_name': canonical_place
                }).eq('script_id', script_id).eq(
                    'item_type', 'locations'
                ).eq('item_name', alias).execute()
            except Exception as di_err:
                print(f"Warning: department_items update failed for '{alias}': {di_err}")

        # 4. Store alias mappings for future prevention
        for alias in aliases:
            try:
                supabase.table('location_aliases').upsert({
                    'script_id': script_id,
                    'canonical_place': canonical_place,
                    'alias_place': alias,
                    'merged_by': user_id,
                }, on_conflict='script_id,alias_place').execute()
            except Exception as alias_err:
                print(f"Warning: failed to store location alias '{alias}': {alias_err}")

        return jsonify({
            'success': True,
            'canonical_place': canonical_place,
            'aliases_merged': aliases,
            'scenes_updated': updated_count,
            'total_scenes': len(scenes),
        }), 200

    except Exception as e:
        print(f"Error merging locations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 3: Add the aliases + suggestions endpoints**

Immediately after `merge_locations`:

```python
@supabase_bp.route('/api/scripts/<script_id>/locations/aliases', methods=['GET'])
@optional_auth
def get_location_aliases(script_id):
    """Get all location alias mappings for a script (for prevention + suggestions)."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        result = supabase.table('location_aliases').select('*').eq(
            'script_id', script_id
        ).execute()
        alias_map = {row['alias_place']: row['canonical_place'] for row in (result.data or [])}
        return jsonify({
            'script_id': script_id,
            'alias_map': alias_map,
            'aliases': result.data or [],
        }), 200
    except Exception as e:
        print(f"Error fetching location aliases: {e}")
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/locations/suggestions', methods=['GET'])
@optional_auth
def get_location_suggestions(script_id):
    """Suggest likely-duplicate base places for user-confirmed merging."""
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        scenes = supabase.table('scenes').select(
            'setting, int_ext, time_of_day, location_hierarchy, location_canonical'
        ).eq('script_id', script_id).execute().data or []

        base_places = []
        for s in scenes:
            base = s.get('location_canonical') or derive_base_place(
                s.get('setting'), s.get('int_ext'),
                s.get('time_of_day'), s.get('location_hierarchy'),
            )
            if base:
                base_places.append(base)

        existing = supabase.table('location_aliases').select(
            'alias_place, canonical_place'
        ).eq('script_id', script_id).execute().data or []
        existing_aliases = {r['alias_place']: r['canonical_place'] for r in existing}

        suggestions = suggest_merges(base_places, existing_aliases)
        return jsonify({'script_id': script_id, 'suggestions': suggestions}), 200
    except Exception as e:
        print(f"Error building location suggestions: {e}")
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 4: Verify `re` is imported at module top**

Run: `grep -n "^import re" backend/routes/supabase_routes.py`
Expected: a match. If none, add `import re` to the top imports.

- [ ] **Step 5: Manual verification with curl**

Start the backend (`cd backend && python app.py`), then against a script with a known duplicate:

Run: `curl -s "http://localhost:5000/api/scripts/<id>/locations/suggestions" | python -m json.tool`
Expected: JSON with a `suggestions` array containing at least the known duplicate group.

Run merge:
`curl -s -X POST "http://localhost:5000/api/scripts/<id>/locations/merge" -H 'Content-Type: application/json' -d '{"canonical_place":"COFFEE SHOP","aliases":["THE COFFEE SHOP"]}'`
Expected: `{"success": true, ...}` and `SELECT DISTINCT location_canonical ...` no longer lists `THE COFFEE SHOP`.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/supabase_routes.py
git commit -m "feat(locations): merge, aliases, and suggestions endpoints"
```

---

## Task 7: Prevention hook at the two analysis write sites

**Files:**
- Modify: `backend/routes/supabase_routes.py` — the two scene-analysis `update_data` blocks (~2776 and ~3296).

**Interfaces:**
- Consumes: `derive_base_place`, `normalize_place` (Task 1); `location_aliases` table.

- [ ] **Step 1: Add a helper above the first analysis route**

Add this module-level helper (place it near `merge_locations` or above the first analysis handler):

```python
def _apply_location_alias(script_id, setting, int_ext, time_of_day, location_hierarchy):
    """Return (setting, location_canonical) with location_aliases applied.
    Non-fatal on lookup failure (degrades to derived base place)."""
    base = derive_base_place(setting, int_ext, time_of_day, location_hierarchy)
    canonical = base
    try:
        rows = supabase.table('location_aliases').select(
            'alias_place, canonical_place'
        ).eq('script_id', script_id).execute().data or []
        alias_map = {r['alias_place']: r['canonical_place'] for r in rows}
        canonical = alias_map.get(base, base)
    except Exception as alias_err:
        print(f"[LocMerge] Alias map lookup skipped (non-fatal): {alias_err}")
    new_setting = setting or ''
    if base and canonical != base:
        new_setting = re.sub(re.escape(base), canonical, new_setting, flags=re.IGNORECASE)
    return new_setting, normalize_place(canonical)
```

- [ ] **Step 2: Apply it at the first write site (~2776)**

Immediately before `update_data = {` at ~2776, add:

```python
        loc_setting, loc_canonical = _apply_location_alias(
            scene['script_id'], scene.get('setting'), scene.get('int_ext'),
            scene.get('time_of_day'), scene.get('location_hierarchy'),
        )
```

Then inside the `update_data` dict, add these two keys (after `'analysis_status': 'complete',`):

```python
            'setting': loc_setting,
            'location_canonical': loc_canonical,
```

- [ ] **Step 3: Apply it at the second write site (~3296)**

Find the second `update_data = {` block (the one following the `character_aliases` remap near ~3270). Immediately before it, add the same call:

```python
        loc_setting, loc_canonical = _apply_location_alias(
            scene['script_id'], scene.get('setting'), scene.get('int_ext'),
            scene.get('time_of_day'), scene.get('location_hierarchy'),
        )
```

And add the same two keys to that `update_data` dict:

```python
            'setting': loc_setting,
            'location_canonical': loc_canonical,
```

- [ ] **Step 4: Verify prevention holds**

After a merge (Task 6), re-run analysis on a scene that was at an alias location, then:
`SELECT setting, location_canonical FROM scenes WHERE id = '<scene_id>';`
Expected: the alias spelling is NOT resurrected — `location_canonical` equals the canonical place, `setting` uses the canonical place text.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/supabase_routes.py
git commit -m "feat(locations): prevention hook applies location_aliases on analysis writes"
```

---

## Task 8: Aggregate worker jobs on `location_canonical`

**Files:**
- Modify: `backend/services/analysis_worker.py:1087-1101` (`process_locations_job`), `:741-742` (overview distinct), `:1247-1251` (`process_location_detail_job`).

- [ ] **Step 1: Group `process_locations_job` by canonical**

Replace the SELECT + bucket loop at ~1087:

```python
        cursor.execute("""
            SELECT COALESCE(NULLIF(location_canonical, ''), setting) AS loc,
                   scene_number, description
            FROM scenes WHERE script_id = ?
            ORDER BY loc, scene_number
        """, (script_id,))

        location_scenes = {}
        for row in cursor.fetchall():
            setting = row[0] or 'UNKNOWN'
            if setting not in location_scenes:
                location_scenes[setting] = []
            location_scenes[setting].append({
                'scene_number': row[1],
                'description': row[2]
            })
```

- [ ] **Step 2: Group overview distinct by canonical (~741)**

Replace:

```python
        cursor.execute(
            "SELECT DISTINCT COALESCE(NULLIF(location_canonical, ''), setting) "
            "FROM scenes WHERE script_id = ?",
            (script_id,),
        )
        locations = [row[0] for row in cursor.fetchall() if row[0]]
```

- [ ] **Step 3: Match location detail by canonical (~1247)**

Replace the detail SELECT:

```python
        cursor.execute("""
            SELECT scene_number, setting, description, characters
            FROM scenes
            WHERE script_id = ?
              AND UPPER(COALESCE(NULLIF(location_canonical, ''), setting)) = UPPER(?)
            ORDER BY scene_number
        """, (script_id, location_name))
```

- [ ] **Step 4: Verify a re-run of the locations job**

Trigger a locations analysis job for a script with a merged place; confirm the merged variants appear as ONE location in the job output/log (`Analyzed N locations` where N reflects collapsed places).

- [ ] **Step 5: Commit**

```bash
git add backend/services/analysis_worker.py
git commit -m "feat(locations): worker aggregation groups on location_canonical"
```

---

## Task 9: Aggregate reports on `location_canonical`

**Files:**
- Modify: `backend/services/report_service.py:~630` (grouping) and `:~487` (filter dimension).

- [ ] **Step 1: Add a base-place helper usage**

At the location-grouping site (~630, currently `setting = scene.get('setting','UNKNOWN')`), replace with:

```python
                setting = scene.get('location_canonical') or scene.get('setting', 'UNKNOWN')
```

- [ ] **Step 2: Group the filter dimension by canonical (~487)**

Where the location filter dimension builds a `set()` of settings, key it on `location_canonical` with a `setting` fallback:

```python
        location_values = sorted({
            (s.get('location_canonical') or s.get('setting') or 'UNKNOWN')
            for s in scenes
        })
```

(Adapt the variable name to the existing code; the change is: read `location_canonical` first, fall back to `setting`.)

- [ ] **Step 3: Verify a generated location report**

Generate the "Location Report" preset for a script with a merged place; confirm the merged variants show as one grouped location.

- [ ] **Step 4: Commit**

```bash
git add backend/services/report_service.py
git commit -m "feat(locations): report aggregation groups on location_canonical"
```

---

## Task 10: Frontend apiService methods

**Files:**
- Modify: `frontend/src/services/apiService.js` (after `getCharacterAliases` ~2057)

**Interfaces:**
- Produces JS: `mergeLocations(scriptId, canonicalPlace, aliases)`, `getLocationAliases(scriptId)`, `getLocationSuggestions(scriptId)`.

- [ ] **Step 1: Add the three methods**

Insert after `getCharacterAliases`:

```javascript
export const mergeLocations = async (scriptId, canonicalPlace, aliases) => {
    const response = await api.post(`/api/scripts/${scriptId}/locations/merge`, {
        canonical_place: canonicalPlace,
        aliases,
    });
    return response.data;
};

export const getLocationAliases = async (scriptId) => {
    const response = await api.get(`/api/scripts/${scriptId}/locations/aliases`);
    return response.data;
};

export const getLocationSuggestions = async (scriptId) => {
    const response = await api.get(`/api/scripts/${scriptId}/locations/suggestions`);
    return response.data;
};
```

- [ ] **Step 2: Lint**

Run: `cd frontend && npm run lint`
Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/apiService.js
git commit -m "feat(locations): apiService methods for merge/aliases/suggestions"
```

---

## Task 11: Frontend grouping reads `location_canonical`

**Files:**
- Modify: `frontend/src/components/scenes/SceneViewer.jsx:~201` (`locs` build), `LocationList.jsx`, `LocationDashboard.jsx:~41-90`, `DayColumn.jsx:~34`, `SchedulePrintView.jsx:~103`, `SelectionSummary.jsx:~78`.

**Interfaces:**
- Consumes: `scene.location_canonical` (falls back to `scene.setting`).

- [ ] **Step 1: Add a shared grouping helper**

Create `frontend/src/utils/locationKey.js`:

```javascript
// Canonical grouping key for a scene's physical location.
// Backend populates location_canonical; fall back to raw setting.
export const locationKey = (scene) =>
    (scene && (scene.location_canonical || scene.setting)) || 'UNKNOWN';
```

- [ ] **Step 2: Use it in SceneViewer `locs` build (~201)**

Where `locs[scene.setting]` is used to bucket scenes, import and switch the key:

```javascript
import { locationKey } from '../../utils/locationKey';
// ...
const key = locationKey(scene);
if (!locs[key]) locs[key] = [];
locs[key].push(scene);
```

- [ ] **Step 3: Use it in the schedule unique-location stats**

In `DayColumn.jsx` (~34), `SchedulePrintView.jsx` (~103), `SelectionSummary.jsx` (~78), replace `new Set(scenes.map(s => s.setting))` with:

```javascript
import { locationKey } from '../../utils/locationKey';
// ...
new Set(scenes.map(locationKey))
```

(Adjust the relative import depth per file location.)

- [ ] **Step 4: Use it in LocationList / LocationDashboard grouping**

In `LocationList.jsx` and `LocationDashboard.jsx`, wherever scenes are grouped by `setting` for counts, group by `locationKey(scene)` instead. Keep displaying the full `setting` string on individual scene rows (only the grouping key changes).

- [ ] **Step 5: Lint + visual check**

Run: `cd frontend && npm run lint` → no new errors.
Then `npm run dev`, open a script with a merged place, confirm the Location list/dashboard and the schedule unique-location count show the collapsed place.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/utils/locationKey.js frontend/src/components/scenes/SceneViewer.jsx frontend/src/components/scenes/LocationList.jsx frontend/src/components/scenes/LocationDashboard.jsx frontend/src/components/schedule/DayColumn.jsx frontend/src/components/schedule/SchedulePrintView.jsx frontend/src/components/schedule/SelectionSummary.jsx
git commit -m "feat(locations): frontend groups locations on location_canonical"
```

---

## Task 12: Frontend suggestions review + manual merge UI

**Files:**
- Create: `frontend/src/components/scenes/LocationMergePanel.jsx`
- Modify: `frontend/src/components/scenes/LocationDashboard.jsx` (mount the panel)

**Interfaces:**
- Consumes: `getLocationSuggestions`, `mergeLocations` (Task 10).

- [ ] **Step 1: Build the panel**

Create `frontend/src/components/scenes/LocationMergePanel.jsx`:

```jsx
import { useEffect, useState } from 'react';
import { getLocationSuggestions, mergeLocations } from '../../services/apiService';

// Surfaces auto-suggested duplicate locations. Merges are user-confirmed.
export default function LocationMergePanel({ scriptId, onMerged }) {
    const [suggestions, setSuggestions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [busyIdx, setBusyIdx] = useState(null);

    const load = async () => {
        setLoading(true);
        try {
            const data = await getLocationSuggestions(scriptId);
            setSuggestions(data.suggestions || []);
        } catch (e) {
            console.error('Failed to load location suggestions', e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { if (scriptId) load(); }, [scriptId]);

    const handleMerge = async (group, idx) => {
        setBusyIdx(idx);
        try {
            const aliases = group.members.filter((m) => m !== group.canonical);
            await mergeLocations(scriptId, group.canonical, aliases);
            await load();
            if (onMerged) onMerged();
        } catch (e) {
            console.error('Merge failed', e);
        } finally {
            setBusyIdx(null);
        }
    };

    if (loading) return <div className="location-merge-panel">Checking for duplicate locations…</div>;
    if (!suggestions.length) return null;

    return (
        <div className="location-merge-panel">
            <h4>Possible duplicate locations</h4>
            {suggestions.map((g, idx) => (
                <div key={idx} className="location-merge-suggestion">
                    <span>
                        {g.members.join('  ·  ')} → <strong>{g.canonical}</strong>
                        {g.reason === 'typo' ? ' (possible typo)' : ' (name variant)'}
                    </span>
                    <button disabled={busyIdx === idx} onClick={() => handleMerge(g, idx)}>
                        {busyIdx === idx ? 'Merging…' : 'Merge'}
                    </button>
                </div>
            ))}
        </div>
    );
}
```

- [ ] **Step 2: Mount it in LocationDashboard**

In `LocationDashboard.jsx`, import and render the panel near the top of the dashboard, passing the script id and a refresh callback:

```jsx
import LocationMergePanel from './LocationMergePanel';
// ...inside the returned JSX, above the location cards:
<LocationMergePanel scriptId={scriptId} onMerged={() => analyzeLocations(scriptId)} />
```

(Use whatever the component already has for `scriptId` and its data-refresh function; `analyzeLocations` is already imported there.)

- [ ] **Step 3: Lint + end-to-end check**

Run: `cd frontend && npm run lint` → no new errors.
`npm run dev`, open a script with a known duplicate: the panel lists the suggestion; clicking **Merge** collapses it and the panel refreshes (suggestion disappears, dashboard count drops).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/scenes/LocationMergePanel.jsx frontend/src/components/scenes/LocationDashboard.jsx
git commit -m "feat(locations): suggestions review + manual merge UI"
```

---

## Self-Review Notes (for the implementer)

- **Backend-before-backfill safety:** every aggregation reads `location_canonical` with a `setting` fallback, so Tasks 8–9 work even on scenes not yet backfilled.
- **Import consolidation:** Tasks 5–7 all touch the top-of-file import in `supabase_routes.py`; ensure the final import line is `from services.location_resolver import derive_base_place, normalize_place, suggest_merges`.
- **Setting rewrite fidelity:** merge/prevention use `re.sub(re.escape(base), canonical, setting, flags=IGNORECASE)` so INT/EXT/TOD around the place text are preserved. When `base` came from `location_hierarchy` and isn't literally in `setting`, only `location_canonical` changes — acceptable, since grouping keys on the canonical column.
- **Service-role client (Task 4):** `get_supabase_admin()` from `db.supabase_client` bypasses RLS — required for the cross-user backfill.
