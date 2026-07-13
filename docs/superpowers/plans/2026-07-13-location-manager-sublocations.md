# Location Manager with Sub-Locations & Propagating Renames — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users rename a parent location, rename a sub-location, reassign a scene's parent, and merge parents after analysis — with every change propagating to scenes, schedule, and reports, and staying sticky across re-analysis.

**Architecture:** All edits rewrite the existing scene fields (`setting`, `location_canonical`, `location_hierarchy`), which every downstream consumer already reads. A pure `resolve_location()` core (in `location_resolver.py`) applies parent + sub aliases; thin Flask endpoints do the DB glue. Parent renames persist in the existing `location_aliases` table; sub renames in a new `sub_location_aliases` table. The schedule board switches from grouping on raw `setting` to grouping on `location_canonical`.

**Tech Stack:** Flask (Python 3.13), supabase-py (service-role key), pytest; React 18 + Vite (plain JSX), no TS.

## Global Constraints

- Backend uses the Supabase **service-role key** (bypasses RLS); every script-scoped endpoint MUST gate on `_user_can_access_script(script_id, user_id)` explicitly — return 403 when it fails.
- Auth decorators: `@require_auth` on write endpoints. `get_user_id()` / `_user_can_access_script()` are imported in `backend/routes/supabase_routes.py`.
- Normalized place keys are produced ONLY by `normalize_place()` (uppercase, article-stripped, punctuation-trimmed). Alias table keys are normalized; user-facing target names keep their chosen spelling until stored via `canonicalize_setting()`.
- Frontend: no TypeScript. Gate the frontend on `npm run build` (run in `frontend/`); `npm run lint` is known broken repo-wide. No new axios instances — add calls to `frontend/src/services/apiService.js`.
- Migrations: `backend/db/migrations/NNN_*.sql`, applied via `backend/db/run_migration.py` (confirm arg form by reading it) or Supabase MCP `apply_migration`. Next number is **038**.
- Data model: `scenes.setting` (raw, canonicalized uppercase), `scenes.location_canonical` (normalized parent key), `scenes.location_hierarchy` (JSONB array, parent first).

---

## File Structure

- `backend/db/migrations/038_sub_location_aliases.sql` — **create** — new sticky sub-alias table (mirrors `035_location_aliases.sql`).
- `backend/services/location_resolver.py` — **modify** — add pure helpers `derive_sub_place`, `rewrite_place_token`, `resolve_location`.
- `backend/routes/supabase_routes.py` — **modify** — refactor `_apply_location_alias` to call `resolve_location`; add `_rename_parent`, `_rename_sub`, `_reassign_scene` helpers + four endpoints.
- `backend/tests/test_location_resolver.py` — **modify** — unit tests for the new pure helpers.
- `backend/tests/test_location_manager_routes.py` — **create** — auth + happy-path tests for the four endpoints.
- `frontend/src/utils/locationKey.js` — **modify** — add `subLocationLabel(scene)`.
- `frontend/src/components/board/boardModel.js` — **modify** — group by `locationKey`; add `subLocation` to strips.
- `frontend/src/services/apiService.js` — **modify** — add four API functions.
- `frontend/src/components/scenes/LocationManager.jsx` — **create** — the dedicated manager UI (tree + actions).
- `frontend/src/components/scenes/LocationManager.css` — **create** — styles.
- `frontend/src/components/scenes/SceneViewer.jsx` — **modify** — mount `LocationManager` behind a "Manage locations" button.

---

## Task 1: Migration — `sub_location_aliases` table

**Files:**
- Create: `backend/db/migrations/038_sub_location_aliases.sql`

**Interfaces:**
- Produces: table `sub_location_aliases(script_id UUID, parent_place TEXT, alias_sub TEXT, canonical_sub TEXT, renamed_by UUID, renamed_at TIMESTAMPTZ, UNIQUE(script_id, parent_place, alias_sub))`.

- [ ] **Step 1: Write migration 038**

Create `backend/db/migrations/038_sub_location_aliases.sql` (mirrors `035_location_aliases.sql`):

```sql
-- Migration 038: Sub-Location Aliases for sticky sub-location renames.
-- Parent-scoped analogue of location_aliases: keeps a sub-location rename
-- (e.g. POOL -> SWIMMING POOL under VILLA) from reverting on re-analysis.

CREATE TABLE IF NOT EXISTS sub_location_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    parent_place TEXT NOT NULL,
    alias_sub TEXT NOT NULL,
    canonical_sub TEXT NOT NULL,
    renamed_by UUID REFERENCES auth.users(id),
    renamed_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(script_id, parent_place, alias_sub)
);

CREATE INDEX idx_sub_location_aliases_script ON sub_location_aliases(script_id);
CREATE INDEX idx_sub_location_aliases_lookup
    ON sub_location_aliases(script_id, parent_place, alias_sub);

ALTER TABLE sub_location_aliases ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Script owner can manage sub location aliases"
    ON sub_location_aliases FOR ALL
    USING (
        script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
    );

CREATE POLICY "Team members can read sub location aliases"
    ON sub_location_aliases FOR SELECT
    USING (
        script_id IN (SELECT script_id FROM script_members WHERE user_id = auth.uid())
    );
```

- [ ] **Step 2: Apply the migration**

Read `backend/db/run_migration.py` to confirm the argument form, then run (from `backend/`): `python db/run_migration.py 038_sub_location_aliases.sql`, or apply via Supabase MCP `apply_migration` / SQL editor.

- [ ] **Step 3: Verify the table exists**

Run (Supabase SQL): `SELECT to_regclass('public.sub_location_aliases');`
Expected: returns `sub_location_aliases` (not null).

- [ ] **Step 4: Commit**

```bash
git add backend/db/migrations/038_sub_location_aliases.sql
git commit -m "feat(locations): add sub_location_aliases table (migration 038)"
```

---

## Task 2: Pure helper — `derive_sub_place`

**Files:**
- Modify: `backend/services/location_resolver.py`
- Test: `backend/tests/test_location_resolver.py`

**Interfaces:**
- Consumes: existing module constants `TIME_WORDS`, `INT_EXT_TOKENS`, `_INT_EXT_PREFIX`, `_DASH_SPLIT`, and `normalize_place`.
- Produces: `derive_sub_place(setting, int_ext=None, time_of_day=None, location_hierarchy=None) -> str` — the normalized sub-location (everything under the base place), `''` when none.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_location_resolver.py` (extend the import from `services.location_resolver` to include `derive_sub_place`):

```python
def test_derive_sub_place_from_setting():
    assert derive_sub_place("INT. VILLA - BATHROOM - DAY") == "BATHROOM"

def test_derive_sub_place_multi_segment():
    assert derive_sub_place("INT. VILLA - POOL HOUSE - CHANGING ROOM - NIGHT") \
        == "POOL HOUSE - CHANGING ROOM"

def test_derive_sub_place_none_when_no_sub():
    assert derive_sub_place("EXT. BEACH - DAY") == ""

def test_derive_sub_place_prefers_hierarchy():
    assert derive_sub_place("INT. VILLA - DAY", location_hierarchy=["VILLA", "Bathroom"]) \
        == "BATHROOM"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_location_resolver.py -k derive_sub_place -v`
Expected: FAIL (`derive_sub_place` not defined / ImportError).

- [ ] **Step 3: Implement `derive_sub_place`**

Add to `backend/services/location_resolver.py` (after `derive_base_place`):

```python
def derive_sub_place(
    setting: Optional[str],
    int_ext: Optional[str] = None,
    time_of_day: Optional[str] = None,
    location_hierarchy=None,
) -> str:
    """Return the normalized sub-location (everything under the base place).

    Mirrors derive_base_place but keeps parts[1:]. Prefers structured
    location_hierarchy[1:] when present; otherwise parses the free-text setting.
    Returns "" when the scene has no sub-location.
    """
    if location_hierarchy:
        if isinstance(location_hierarchy, str):
            try:
                location_hierarchy = json.loads(location_hierarchy)
            except (ValueError, TypeError):
                location_hierarchy = []
        if location_hierarchy:
            if len(location_hierarchy) > 1:
                return normalize_place(" - ".join(location_hierarchy[1:]))
            return ""

    s = _INT_EXT_PREFIX.sub("", setting or "")
    parts = [p.strip() for p in _DASH_SPLIT.split(s) if p.strip()]
    kept = [
        p for p in parts
        if p.upper() not in TIME_WORDS and normalize_place(p) not in INT_EXT_TOKENS
    ]
    if len(kept) > 1:
        return normalize_place(" - ".join(kept[1:]))
    return ""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_location_resolver.py -k derive_sub_place -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/services/location_resolver.py backend/tests/test_location_resolver.py
git commit -m "feat(locations): add derive_sub_place helper"
```

---

## Task 3: Pure helpers — `rewrite_place_token` and `resolve_location`

**Files:**
- Modify: `backend/services/location_resolver.py`
- Test: `backend/tests/test_location_resolver.py`

**Interfaces:**
- Consumes: `derive_base_place`, `derive_sub_place`, `normalize_place`, `canonicalize_setting`.
- Produces:
  - `rewrite_place_token(setting, from_token, to_token) -> str` — replace the first case-insensitive occurrence of `from_token` with `to_token`, preserving the rest.
  - `resolve_location(setting, int_ext, time_of_day, location_hierarchy, parent_alias_map=None, sub_alias_map=None) -> (str, str)` — apply parent then sub aliases; returns `(new_setting, location_canonical_norm)`. `parent_alias_map`: `{alias_base_norm: canonical_name}`. `sub_alias_map`: `{(parent_norm, alias_sub_norm): canonical_sub}`.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_location_resolver.py` (extend the import to include `rewrite_place_token, resolve_location`):

```python
def test_rewrite_place_token_preserves_rest():
    assert rewrite_place_token("INT. VILLA - BATHROOM - DAY", "VILLA", "SMITH RESIDENCE") \
        == "INT. SMITH RESIDENCE - BATHROOM - DAY"

def test_rewrite_place_token_first_occurrence_only():
    assert rewrite_place_token("INT. POOL - POOL DECK - DAY", "POOL", "SPA") \
        == "INT. SPA - POOL DECK - DAY"

def test_resolve_location_parent_alias():
    setting, canonical = resolve_location(
        "INT. VILLA - BATHROOM - DAY", "INT", "DAY", ["VILLA", "BATHROOM"],
        parent_alias_map={"VILLA": "SMITH RESIDENCE"},
    )
    assert setting == "INT. SMITH RESIDENCE - BATHROOM - DAY"
    assert canonical == "SMITH RESIDENCE"

def test_resolve_location_sub_alias_scoped_to_parent():
    # POOL under VILLA renames; POOL under HOTEL must NOT.
    sub_map = {("VILLA", "POOL"): "SWIMMING POOL"}
    s1, _ = resolve_location("EXT. VILLA - POOL - DAY", "EXT", "DAY", None, sub_alias_map=sub_map)
    s2, _ = resolve_location("EXT. HOTEL - POOL - DAY", "EXT", "DAY", None, sub_alias_map=sub_map)
    assert s1 == "EXT. VILLA - SWIMMING POOL - DAY"
    assert s2 == "EXT. HOTEL - POOL - DAY"

def test_resolve_location_no_maps_is_noop_canonical():
    setting, canonical = resolve_location("INT. VILLA - BATHROOM - DAY", "INT", "DAY", None)
    assert setting == "INT. VILLA - BATHROOM - DAY"
    assert canonical == "VILLA"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_location_resolver.py -k "rewrite_place_token or resolve_location" -v`
Expected: FAIL (names not defined).

- [ ] **Step 3: Implement the helpers**

Add to `backend/services/location_resolver.py` (after `derive_sub_place`):

```python
def rewrite_place_token(setting: Optional[str], from_token: str, to_token: str) -> str:
    """Replace the first case-insensitive occurrence of from_token with to_token,
    preserving the rest of the setting. Used for base and sub renames."""
    if not setting or not from_token:
        return setting or ""
    return re.sub(re.escape(from_token), to_token, setting, count=1, flags=re.IGNORECASE)


def resolve_location(
    setting: Optional[str],
    int_ext: Optional[str] = None,
    time_of_day: Optional[str] = None,
    location_hierarchy=None,
    parent_alias_map: Optional[Dict[str, str]] = None,
    sub_alias_map: Optional[Dict] = None,
) -> tuple:
    """Apply parent then sub aliases to a scene setting (pure).

    Returns (new_setting, location_canonical_norm). Parent map is applied first
    so the sub lookup is keyed on the final parent. Sub is re-derived from the
    rewritten setting (not the possibly-stale hierarchy).
    """
    parent_alias_map = parent_alias_map or {}
    sub_alias_map = sub_alias_map or {}

    setting = canonicalize_setting(setting)
    base = derive_base_place(setting, int_ext, time_of_day, location_hierarchy)
    canonical = parent_alias_map.get(base, base)

    new_setting = setting or ""
    if base and normalize_place(canonical) != base:
        new_setting = re.sub(re.escape(base), canonical, new_setting, flags=re.IGNORECASE)

    parent_norm = normalize_place(canonical)
    sub = derive_sub_place(new_setting, int_ext, time_of_day, None)
    if sub:
        new_sub = sub_alias_map.get((parent_norm, sub))
        if new_sub and normalize_place(new_sub) != sub:
            new_setting = rewrite_place_token(new_setting, sub, new_sub)

    return new_setting, parent_norm
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_location_resolver.py -v`
Expected: PASS (all resolver tests, including prior ones).

- [ ] **Step 5: Commit**

```bash
git add backend/services/location_resolver.py backend/tests/test_location_resolver.py
git commit -m "feat(locations): add rewrite_place_token and resolve_location"
```

---

## Task 4: Refactor `_apply_location_alias` onto `resolve_location`

**Files:**
- Modify: `backend/routes/supabase_routes.py` (`_apply_location_alias`, ~lines 4779-4798; imports at line 24-28)

**Interfaces:**
- Consumes: `resolve_location` (Task 3), `sub_location_aliases` table (Task 1).
- Produces: unchanged signature `_apply_location_alias(script_id, setting, int_ext, time_of_day, location_hierarchy) -> (setting, location_canonical)`, now also applying sub aliases.

- [ ] **Step 1: Extend the import**

In `backend/routes/supabase_routes.py`, update the `from services.location_resolver import (...)` block (starts line 24) to also import `resolve_location`:

```python
from services.location_resolver import (
    normalize_place,
    canonicalize_setting,
    derive_base_place,
    suggest_merges,
    resolve_location,
)
```

- [ ] **Step 2: Replace the body of `_apply_location_alias`**

Replace the function (currently lines ~4779-4798) with:

```python
def _apply_location_alias(script_id, setting, int_ext, time_of_day, location_hierarchy):
    """Return (setting, location_canonical) with parent + sub aliases applied.
    Non-fatal on lookup failure (degrades to derived base place)."""
    parent_map = {}
    sub_map = {}
    try:
        rows = supabase.table('location_aliases').select(
            'alias_place, canonical_place'
        ).eq('script_id', script_id).execute().data or []
        parent_map = {r['alias_place']: r['canonical_place'] for r in rows}
    except Exception as alias_err:
        print(f"[LocMerge] parent alias lookup skipped (non-fatal): {alias_err}")
    try:
        srows = supabase.table('sub_location_aliases').select(
            'parent_place, alias_sub, canonical_sub'
        ).eq('script_id', script_id).execute().data or []
        sub_map = {(r['parent_place'], r['alias_sub']): r['canonical_sub'] for r in srows}
    except Exception as sub_err:
        print(f"[LocMerge] sub alias lookup skipped (non-fatal): {sub_err}")
    return resolve_location(
        setting, int_ext, time_of_day, location_hierarchy, parent_map, sub_map
    )
```

- [ ] **Step 3: Verify no regression in the resolver contract**

Run: `cd backend && pytest tests/test_location_resolver.py -v`
Expected: PASS (behaviour of `resolve_location` unchanged; this task only rewires the caller).

- [ ] **Step 4: Sanity-check import + app boot**

Run: `cd backend && python -c "import routes.supabase_routes"`
Expected: no ImportError.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/supabase_routes.py
git commit -m "refactor(locations): apply parent+sub aliases via resolve_location"
```

---

## Task 5: Endpoint — rename parent

**Files:**
- Modify: `backend/routes/supabase_routes.py` (add helper `_rename_parent` + route, beside `merge_locations` ~line 4801)
- Test: `backend/tests/test_location_manager_routes.py` (create)

**Interfaces:**
- Consumes: `rewrite_place_token`, `normalize_place`, `canonicalize_setting`, `_user_can_access_script`, `get_user_id`.
- Produces:
  - `_rename_parent(script_id, from_canonical, to_name, user_id) -> int` (scenes updated).
  - `POST /api/scripts/<script_id>/locations/rename-parent` body `{ from_canonical, to_name }` → `{ success, scenes_updated }`.

- [ ] **Step 1: Write the failing auth tests**

Create `backend/tests/test_location_manager_routes.py`:

```python
"""Location manager endpoints require auth + owner/member access."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.supabase_routes as sr


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_rename_parent_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().post("/api/scripts/s1/locations/rename-parent",
                          json={"from_canonical": "VILLA", "to_name": "SMITH RESIDENCE"})
    assert resp.status_code == 401


def test_rename_parent_forbidden_for_non_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: False)
    resp = _client().post("/api/scripts/s1/locations/rename-parent",
                          json={"from_canonical": "VILLA", "to_name": "SMITH RESIDENCE"})
    assert resp.status_code == 403


def test_rename_parent_ok_calls_helper(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    monkeypatch.setattr(sr, "_rename_parent", lambda script_id, frm, to, uid: 4)
    resp = _client().post("/api/scripts/s1/locations/rename-parent",
                          json={"from_canonical": "VILLA", "to_name": "SMITH RESIDENCE"})
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "scenes_updated": 4}


def test_rename_parent_validates_body(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    resp = _client().post("/api/scripts/s1/locations/rename-parent", json={"to_name": "X"})
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_location_manager_routes.py -k rename_parent -v`
Expected: FAIL (route 404 / helper missing).

- [ ] **Step 3: Implement helper + route**

Add to `backend/routes/supabase_routes.py`, immediately before the `merge_locations` route (~line 4801). First the import line at the top's resolver block — add `rewrite_place_token`:

```python
from services.location_resolver import (
    normalize_place,
    canonicalize_setting,
    derive_base_place,
    derive_sub_place,
    suggest_merges,
    resolve_location,
    rewrite_place_token,
)
```

Then the helper + route:

```python
def _rename_parent(script_id, from_canonical, to_name, user_id):
    """Rename a parent location across every scene grouped under it. Preserves
    each scene's sub-location, updates department_items, and stores a sticky
    location_aliases mapping. Returns the number of scenes updated."""
    from_norm = normalize_place(from_canonical)
    to_norm = normalize_place(to_name)

    result = supabase.table('scenes').select(
        'id, setting, location_hierarchy'
    ).eq('script_id', script_id).eq('location_canonical', from_norm).execute()
    scenes = result.data or []
    updated = 0
    for scene in scenes:
        new_setting = rewrite_place_token(scene.get('setting') or '', from_norm, to_name)
        hierarchy = scene.get('location_hierarchy') or []
        if isinstance(hierarchy, list) and hierarchy:
            hierarchy = [to_name] + hierarchy[1:]
        supabase.table('scenes').update({
            'setting': canonicalize_setting(new_setting),
            'location_canonical': to_norm,
            'location_hierarchy': hierarchy,
        }).eq('id', scene['id']).execute()
        updated += 1

    try:
        supabase.table('department_items').update({
            'item_name': to_name
        }).eq('script_id', script_id).eq(
            'item_type', 'locations'
        ).ilike('item_name', from_norm).execute()
    except Exception as di_err:
        print(f"Warning: department_items rename failed: {di_err}")

    if to_norm != from_norm:
        try:
            supabase.table('location_aliases').upsert({
                'script_id': script_id,
                'canonical_place': to_norm,
                'alias_place': from_norm,
                'merged_by': user_id,
            }, on_conflict='script_id,alias_place').execute()
        except Exception as alias_err:
            print(f"Warning: failed to store location alias: {alias_err}")

    return updated


@supabase_bp.route('/api/scripts/<script_id>/locations/rename-parent', methods=['POST'])
@require_auth
def rename_parent_location(script_id):
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        data = request.get_json() or {}
        from_canonical = (data.get('from_canonical') or '').strip()
        to_name = (data.get('to_name') or '').strip()
        user_id = get_user_id()
        if not _user_can_access_script(script_id, user_id):
            return jsonify({'error': 'Not authorized for this script'}), 403
        if not from_canonical or not to_name:
            return jsonify({'error': 'from_canonical and to_name are required'}), 400
        updated = _rename_parent(script_id, from_canonical, to_name, user_id)
        return jsonify({'success': True, 'scenes_updated': updated}), 200
    except Exception as e:
        print(f"Error renaming parent location: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_location_manager_routes.py -k rename_parent -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/routes/supabase_routes.py backend/tests/test_location_manager_routes.py
git commit -m "feat(locations): rename-parent endpoint"
```

---

## Task 6: Endpoint — rename sub-location

**Files:**
- Modify: `backend/routes/supabase_routes.py` (add `_rename_sub` + route after Task 5's route)
- Test: `backend/tests/test_location_manager_routes.py`

**Interfaces:**
- Consumes: `derive_sub_place`, `rewrite_place_token`, `normalize_place`, `canonicalize_setting`.
- Produces:
  - `_rename_sub(script_id, parent_canonical, from_sub, to_sub, user_id) -> int`.
  - `POST /api/scripts/<script_id>/locations/rename-sub` body `{ parent_canonical, from_sub, to_sub }` → `{ success, scenes_updated }`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_location_manager_routes.py`:

```python
def test_rename_sub_forbidden_for_non_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: False)
    resp = _client().post("/api/scripts/s1/locations/rename-sub",
                          json={"parent_canonical": "VILLA", "from_sub": "POOL", "to_sub": "SWIMMING POOL"})
    assert resp.status_code == 403


def test_rename_sub_ok_calls_helper(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    monkeypatch.setattr(sr, "_rename_sub", lambda script_id, parent, frm, to, uid: 2)
    resp = _client().post("/api/scripts/s1/locations/rename-sub",
                          json={"parent_canonical": "VILLA", "from_sub": "POOL", "to_sub": "SWIMMING POOL"})
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "scenes_updated": 2}


def test_rename_sub_validates_body(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    resp = _client().post("/api/scripts/s1/locations/rename-sub",
                          json={"parent_canonical": "VILLA", "from_sub": "POOL"})
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_location_manager_routes.py -k rename_sub -v`
Expected: FAIL.

- [ ] **Step 3: Implement helper + route**

Add after the rename-parent route:

```python
def _rename_sub(script_id, parent_canonical, from_sub, to_sub, user_id):
    """Rename a sub-location under one parent across the scenes that use it.
    location_canonical is unchanged. Stores a sticky sub_location_aliases row.
    Returns the number of scenes updated."""
    parent_norm = normalize_place(parent_canonical)
    from_norm = normalize_place(from_sub)
    to_norm = normalize_place(to_sub)

    result = supabase.table('scenes').select(
        'id, setting, int_ext, time_of_day, location_hierarchy'
    ).eq('script_id', script_id).eq('location_canonical', parent_norm).execute()
    scenes = result.data or []
    updated = 0
    for scene in scenes:
        sub = derive_sub_place(
            scene.get('setting'), scene.get('int_ext'),
            scene.get('time_of_day'), scene.get('location_hierarchy'),
        )
        if sub != from_norm:
            continue
        new_setting = rewrite_place_token(scene.get('setting') or '', from_norm, to_sub)
        hierarchy = scene.get('location_hierarchy') or []
        if isinstance(hierarchy, list) and len(hierarchy) > 1:
            hierarchy = hierarchy[:1] + [to_sub] + hierarchy[2:]
        supabase.table('scenes').update({
            'setting': canonicalize_setting(new_setting),
            'location_hierarchy': hierarchy,
        }).eq('id', scene['id']).execute()
        updated += 1

    if to_norm != from_norm:
        try:
            supabase.table('sub_location_aliases').upsert({
                'script_id': script_id,
                'parent_place': parent_norm,
                'alias_sub': from_norm,
                'canonical_sub': to_norm,
                'renamed_by': user_id,
            }, on_conflict='script_id,parent_place,alias_sub').execute()
        except Exception as sub_err:
            print(f"Warning: failed to store sub alias: {sub_err}")

    return updated


@supabase_bp.route('/api/scripts/<script_id>/locations/rename-sub', methods=['POST'])
@require_auth
def rename_sub_location(script_id):
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        data = request.get_json() or {}
        parent_canonical = (data.get('parent_canonical') or '').strip()
        from_sub = (data.get('from_sub') or '').strip()
        to_sub = (data.get('to_sub') or '').strip()
        user_id = get_user_id()
        if not _user_can_access_script(script_id, user_id):
            return jsonify({'error': 'Not authorized for this script'}), 403
        if not parent_canonical or not from_sub or not to_sub:
            return jsonify({'error': 'parent_canonical, from_sub and to_sub are required'}), 400
        updated = _rename_sub(script_id, parent_canonical, from_sub, to_sub, user_id)
        return jsonify({'success': True, 'scenes_updated': updated}), 200
    except Exception as e:
        print(f"Error renaming sub-location: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_location_manager_routes.py -k rename_sub -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/routes/supabase_routes.py backend/tests/test_location_manager_routes.py
git commit -m "feat(locations): rename-sub endpoint"
```

---

## Task 7: Endpoints — reassign scene & merge parents

**Files:**
- Modify: `backend/routes/supabase_routes.py` (add `_reassign_scene` + two routes after Task 6)
- Test: `backend/tests/test_location_manager_routes.py`

**Interfaces:**
- Consumes: `_rename_parent` (Task 5), `rewrite_place_token`, `normalize_place`, `canonicalize_setting`.
- Produces:
  - `_reassign_scene(script_id, scene_id, to_parent_name) -> int`.
  - `POST /api/scripts/<script_id>/locations/reassign-scene` body `{ scene_id, to_parent_name }` → `{ success, scenes_updated }`.
  - `POST /api/scripts/<script_id>/locations/merge-parents` body `{ canonical_name, source_canonicals: [] }` → `{ success, scenes_updated }`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_location_manager_routes.py`:

```python
def test_reassign_scene_forbidden(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: False)
    resp = _client().post("/api/scripts/s1/locations/reassign-scene",
                          json={"scene_id": "sc1", "to_parent_name": "HOTEL"})
    assert resp.status_code == 403


def test_reassign_scene_ok(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    monkeypatch.setattr(sr, "_reassign_scene", lambda script_id, scid, to: 1)
    resp = _client().post("/api/scripts/s1/locations/reassign-scene",
                          json={"scene_id": "sc1", "to_parent_name": "HOTEL"})
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "scenes_updated": 1}


def test_merge_parents_ok_sums_sources(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    calls = []
    monkeypatch.setattr(sr, "_rename_parent",
                        lambda script_id, frm, to, uid: calls.append((frm, to)) or 3)
    resp = _client().post("/api/scripts/s1/locations/merge-parents",
                          json={"canonical_name": "VILLA", "source_canonicals": ["THE VILLA", "VILLA HOUSE"]})
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "scenes_updated": 6}
    assert calls == [("THE VILLA", "VILLA"), ("VILLA HOUSE", "VILLA")]


def test_merge_parents_validates_body(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    resp = _client().post("/api/scripts/s1/locations/merge-parents",
                          json={"canonical_name": "VILLA", "source_canonicals": []})
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_location_manager_routes.py -k "reassign or merge_parents" -v`
Expected: FAIL.

- [ ] **Step 3: Implement helper + routes**

Add after the rename-sub route:

```python
def _reassign_scene(script_id, scene_id, to_parent_name):
    """Move one scene to a different parent location, preserving its
    sub-location. Returns 1 if updated, else 0."""
    to_norm = normalize_place(to_parent_name)
    result = supabase.table('scenes').select(
        'id, setting, location_canonical, location_hierarchy'
    ).eq('script_id', script_id).eq('id', scene_id).limit(1).execute()
    if not result.data:
        return 0
    scene = result.data[0]
    old_base = normalize_place(scene.get('location_canonical') or '')
    new_setting = rewrite_place_token(scene.get('setting') or '', old_base, to_parent_name)
    hierarchy = scene.get('location_hierarchy') or []
    if isinstance(hierarchy, list) and hierarchy:
        hierarchy = [to_parent_name] + hierarchy[1:]
    supabase.table('scenes').update({
        'setting': canonicalize_setting(new_setting),
        'location_canonical': to_norm,
        'location_hierarchy': hierarchy,
    }).eq('id', scene['id']).execute()
    return 1


@supabase_bp.route('/api/scripts/<script_id>/locations/reassign-scene', methods=['POST'])
@require_auth
def reassign_scene_location(script_id):
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        data = request.get_json() or {}
        scene_id = (data.get('scene_id') or '').strip()
        to_parent_name = (data.get('to_parent_name') or '').strip()
        user_id = get_user_id()
        if not _user_can_access_script(script_id, user_id):
            return jsonify({'error': 'Not authorized for this script'}), 403
        if not scene_id or not to_parent_name:
            return jsonify({'error': 'scene_id and to_parent_name are required'}), 400
        updated = _reassign_scene(script_id, scene_id, to_parent_name)
        return jsonify({'success': True, 'scenes_updated': updated}), 200
    except Exception as e:
        print(f"Error reassigning scene location: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@supabase_bp.route('/api/scripts/<script_id>/locations/merge-parents', methods=['POST'])
@require_auth
def merge_parent_locations(script_id):
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        data = request.get_json() or {}
        canonical_name = (data.get('canonical_name') or '').strip()
        sources = data.get('source_canonicals') or []
        user_id = get_user_id()
        if not _user_can_access_script(script_id, user_id):
            return jsonify({'error': 'Not authorized for this script'}), 403
        if not canonical_name or not isinstance(sources, list) or not sources:
            return jsonify({'error': 'canonical_name and non-empty source_canonicals are required'}), 400
        total = 0
        for source in sources:
            source = (source or '').strip()
            if not source or normalize_place(source) == normalize_place(canonical_name):
                continue
            total += _rename_parent(script_id, source, canonical_name, user_id)
        return jsonify({'success': True, 'scenes_updated': total}), 200
    except Exception as e:
        print(f"Error merging parent locations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_location_manager_routes.py -v`
Expected: PASS (all endpoint tests).

- [ ] **Step 5: Commit**

```bash
git add backend/routes/supabase_routes.py backend/tests/test_location_manager_routes.py
git commit -m "feat(locations): reassign-scene and merge-parents endpoints"
```

---

## Task 8: Frontend helper — `subLocationLabel`

**Files:**
- Modify: `frontend/src/utils/locationKey.js`

**Interfaces:**
- Consumes: scene object fields `location_canonical`, `setting`.
- Produces: `subLocationLabel(scene) -> string` — the sub-location text (`''` when none), derived from `setting` (authoritative; hierarchy may be stale after re-analysis). Mirrors backend `derive_sub_place`.

- [ ] **Step 1: Implement the helper**

Replace `frontend/src/utils/locationKey.js` with:

```javascript
// Canonical grouping key for a scene's physical location.
// Backend populates location_canonical; fall back to raw setting.
export const locationKey = (scene) =>
    (scene && (scene.location_canonical || scene.setting)) || 'UNKNOWN';

const TIME_WORDS = new Set([
    'DAY', 'NIGHT', 'DUSK', 'DAWN', 'MORNING', 'EVENING',
    'AFTERNOON', 'CONTINUOUS', 'LATER', 'SAME', 'MAGIC HOUR',
]);
const INT_EXT_TOKENS = new Set(['INT', 'EXT', 'INT/EXT', 'I/E']);
const INT_EXT_PREFIX = /^\s*(INT\.?\/EXT\.?|INT\.?|EXT\.?|I\/E\.?)(?=[\s.\-:]|$)\s*[-.:]?\s*/i;

// Sub-location label (everything under the base place), parsed from the setting
// so it stays correct after renames. Mirrors backend derive_sub_place: drop the
// INT/EXT prefix, split on dashes, drop time + INT/EXT tokens, drop the base
// (first kept part), join the rest.
export const subLocationLabel = (scene) => {
    if (!scene || !scene.setting) return '';
    const stripped = scene.setting.toUpperCase().replace(INT_EXT_PREFIX, '');
    const parts = stripped
        .split(/\s*[-–—]\s*/)
        .map((p) => p.trim())
        .filter(Boolean);
    const kept = parts.filter(
        (p) => !TIME_WORDS.has(p) && !INT_EXT_TOKENS.has(p)
    );
    return kept.slice(1).join(' - ');
};
```

- [ ] **Step 2: Verify with a node check**

Run:
```bash
cd frontend && node --input-type=module -e "
import { subLocationLabel, locationKey } from './src/utils/locationKey.js';
const t = (s, exp) => console.log(subLocationLabel(s) === exp ? 'PASS' : 'FAIL got '+JSON.stringify(subLocationLabel(s)));
t({ setting: 'INT. VILLA - BATHROOM - DAY' }, 'BATHROOM');
t({ setting: 'EXT. BEACH - DAY' }, '');
t({ setting: 'INT. VILLA - POOL HOUSE - CHANGING ROOM - NIGHT' }, 'POOL HOUSE - CHANGING ROOM');
console.log('locationKey', locationKey({ location_canonical: 'VILLA' }) === 'VILLA' ? 'PASS' : 'FAIL');
"
```
Expected: four `PASS` lines.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/utils/locationKey.js
git commit -m "feat(locations): subLocationLabel helper"
```

---

## Task 9: Schedule board groups by parent location

**Files:**
- Modify: `frontend/src/components/board/boardModel.js` (`groupScenes` ~line 81; strip builder ~line 131)

**Interfaces:**
- Consumes: `locationKey`, `subLocationLabel` (Task 8).
- Produces: `groupScenes(scenes, 'location')` keyed on `locationKey(scene)`; each strip gains `subLocation: subLocationLabel(scene)`.

- [ ] **Step 1: Add the import**

At the top of `frontend/src/components/board/boardModel.js`, add (next to the existing `getSceneEighths` import):

```javascript
import { locationKey, subLocationLabel } from '../../utils/locationKey';
```

- [ ] **Step 2: Group by canonical parent**

In `groupScenes`, replace the `'location'` case:

```javascript
        case 'location':
            return groupByKey(scenes, s => locationKey(s));
```

- [ ] **Step 3: Add sub-location to each strip**

In `buildBoardViewModel`, inside the `strips: grouped[key].map(scene => ({ ... }))` object, add one field (next to `setting: scene.setting,`):

```javascript
            subLocation: subLocationLabel(scene),
```

- [ ] **Step 4: Verify grouping with a node check**

Run:
```bash
cd frontend && node --input-type=module -e "
import { groupScenes } from './src/components/board/boardModel.js';
const scenes = [
  { id:1, setting:'INT. VILLA - BATHROOM - DAY', location_canonical:'VILLA' },
  { id:2, setting:'EXT. VILLA - POOL - DAY',     location_canonical:'VILLA' },
  { id:3, setting:'INT. OFFICE - DAY',           location_canonical:'OFFICE' },
];
const g = groupScenes(scenes, 'location');
console.log(Object.keys(g).sort().join(',') === 'OFFICE,VILLA' ? 'PASS' : 'FAIL '+Object.keys(g));
console.log(g['VILLA'].length === 2 ? 'PASS' : 'FAIL');
"
```
Expected: two `PASS` lines. (If the module has other imports that break standalone node, skip to Step 5 and rely on the build + manual check.)

- [ ] **Step 5: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/board/boardModel.js
git commit -m "feat(schedule): group board lanes by parent location"
```

---

## Task 10: API service functions

**Files:**
- Modify: `frontend/src/services/apiService.js` (near `mergeLocations`, ~line 2102)

**Interfaces:**
- Produces (all return `response.data`):
  - `renameParentLocation(scriptId, fromCanonical, toName)`
  - `renameSubLocation(scriptId, parentCanonical, fromSub, toSub)`
  - `reassignSceneLocation(scriptId, sceneId, toParentName)`
  - `mergeParentLocations(scriptId, canonicalName, sourceCanonicals)`

- [ ] **Step 1: Add the functions**

Add after `mergeLocations` in `frontend/src/services/apiService.js`:

```javascript
export const renameParentLocation = async (scriptId, fromCanonical, toName) => {
    const response = await api.post(`/api/scripts/${scriptId}/locations/rename-parent`, {
        from_canonical: fromCanonical,
        to_name: toName,
    });
    return response.data;
};

export const renameSubLocation = async (scriptId, parentCanonical, fromSub, toSub) => {
    const response = await api.post(`/api/scripts/${scriptId}/locations/rename-sub`, {
        parent_canonical: parentCanonical,
        from_sub: fromSub,
        to_sub: toSub,
    });
    return response.data;
};

export const reassignSceneLocation = async (scriptId, sceneId, toParentName) => {
    const response = await api.post(`/api/scripts/${scriptId}/locations/reassign-scene`, {
        scene_id: sceneId,
        to_parent_name: toParentName,
    });
    return response.data;
};

export const mergeParentLocations = async (scriptId, canonicalName, sourceCanonicals) => {
    const response = await api.post(`/api/scripts/${scriptId}/locations/merge-parents`, {
        canonical_name: canonicalName,
        source_canonicals: sourceCanonicals,
    });
    return response.data;
};
```

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/apiService.js
git commit -m "feat(locations): apiService functions for location manager"
```

---

## Task 11: LocationManager component

**Files:**
- Create: `frontend/src/components/scenes/LocationManager.jsx`
- Create: `frontend/src/components/scenes/LocationManager.css`

**Interfaces:**
- Consumes: `locationKey`, `subLocationLabel` (Task 8); `renameParentLocation`, `renameSubLocation`, `reassignSceneLocation`, `mergeParentLocations` (Task 10); `useToast` (`../../context/ToastContext`).
- Produces: `default` export `LocationManager({ scriptId, scenes, onClose, onChanged })` — modal that renders a parent → sub tree with rename/reassign/merge actions; calls `onChanged()` after a successful mutation so the parent can refetch scenes.

- [ ] **Step 1: Create the component**

Create `frontend/src/components/scenes/LocationManager.jsx`:

```javascript
import React, { useMemo, useState, useCallback } from 'react';
import { X, MapPin, Edit3 } from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { locationKey, subLocationLabel } from '../../utils/locationKey';
import {
    renameParentLocation,
    renameSubLocation,
    reassignSceneLocation,
    mergeParentLocations,
} from '../../services/apiService';
import './LocationManager.css';

// Build parent -> sub -> scenes tree from the loaded scenes list (client-side).
function buildTree(scenes) {
    const parents = {};
    (scenes || []).forEach((scene) => {
        if (scene.is_omitted) return;
        const parent = locationKey(scene);
        const sub = subLocationLabel(scene) || '(main)';
        if (!parents[parent]) parents[parent] = { name: parent, count: 0, subs: {} };
        if (!parents[parent].subs[sub]) parents[parent].subs[sub] = { name: sub, scenes: [] };
        parents[parent].subs[sub].scenes.push(scene);
        parents[parent].count += 1;
    });
    return Object.values(parents).sort((a, b) => a.name.localeCompare(b.name));
}

const LocationManager = ({ scriptId, scenes, onClose, onChanged }) => {
    const toast = useToast();
    const [busy, setBusy] = useState(false);
    const [expanded, setExpanded] = useState({});
    const tree = useMemo(() => buildTree(scenes), [scenes]);

    const run = useCallback(async (label, fn) => {
        if (busy) return;
        setBusy(true);
        try {
            const res = await fn();
            toast.success(label, `${res?.scenes_updated ?? 0} scene(s) updated.`);
            if (onChanged) await onChanged();
        } catch (e) {
            toast.error('Update failed', e?.response?.data?.error || e.message);
        } finally {
            setBusy(false);
        }
    }, [busy, toast, onChanged]);

    const doRenameParent = (parent) => {
        const to = window.prompt(`Rename location "${parent.name}" to:`, parent.name);
        if (!to || to.trim() === parent.name) return;
        run('Location renamed', () => renameParentLocation(scriptId, parent.name, to.trim()));
    };

    const doRenameSub = (parent, sub) => {
        if (sub.name === '(main)') return;
        const to = window.prompt(`Rename sub-location "${sub.name}" under ${parent.name} to:`, sub.name);
        if (!to || to.trim() === sub.name) return;
        run('Sub-location renamed', () => renameSubLocation(scriptId, parent.name, sub.name, to.trim()));
    };

    const doReassign = (scene) => {
        const to = window.prompt(`Move scene #${scene.scene_number} to which location?`, '');
        if (!to || !to.trim()) return;
        run('Scene reassigned', () => reassignSceneLocation(scriptId, scene.id || scene.scene_id, to.trim()));
    };

    const doMerge = (parent) => {
        const src = window.prompt(`Merge which location INTO "${parent.name}"? (exact name)`, '');
        if (!src || !src.trim()) return;
        run('Locations merged', () => mergeParentLocations(scriptId, parent.name, [src.trim()]));
    };

    return (
        <div className="locmgr-overlay" onClick={onClose}>
            <div className="locmgr-modal" onClick={(e) => e.stopPropagation()}>
                <div className="locmgr-header">
                    <span><MapPin size={16} /> Manage Locations</span>
                    <button className="locmgr-close" onClick={onClose} aria-label="Close"><X size={18} /></button>
                </div>
                <div className="locmgr-body">
                    {tree.length === 0 && <p className="locmgr-empty">No locations yet.</p>}
                    {tree.map((parent) => {
                        const open = expanded[parent.name] !== false;
                        return (
                            <div key={parent.name} className="locmgr-parent">
                                <div className="locmgr-parent-row">
                                    <button
                                        className="locmgr-toggle"
                                        onClick={() => setExpanded((s) => ({ ...s, [parent.name]: !open }))}
                                    >
                                        {open ? '▼' : '▶'} <strong>{parent.name}</strong>
                                        <span className="locmgr-count">{parent.count}</span>
                                    </button>
                                    <span className="locmgr-actions">
                                        <button disabled={busy} onClick={() => doRenameParent(parent)}>Rename</button>
                                        <button disabled={busy} onClick={() => doMerge(parent)}>Merge…</button>
                                    </span>
                                </div>
                                {open && Object.values(parent.subs).map((sub) => (
                                    <div key={sub.name} className="locmgr-sub-row">
                                        <span className="locmgr-sub-name">
                                            {sub.name} <span className="locmgr-count">{sub.scenes.length}</span>
                                        </span>
                                        <span className="locmgr-actions">
                                            {sub.name !== '(main)' && (
                                                <button disabled={busy} onClick={() => doRenameSub(parent, sub)}>
                                                    <Edit3 size={12} /> Rename
                                                </button>
                                            )}
                                            <button
                                                disabled={busy}
                                                onClick={() => doReassign(sub.scenes[0])}
                                                title="Reassign the first scene here to another location"
                                            >
                                                Reassign scene
                                            </button>
                                        </span>
                                    </div>
                                ))}
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default LocationManager;
```

- [ ] **Step 2: Create the stylesheet**

Create `frontend/src/components/scenes/LocationManager.css`:

```css
.locmgr-overlay {
    position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5);
    display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.locmgr-modal {
    background: var(--gray-900, #111827); color: var(--gray-100, #f3f4f6);
    width: min(560px, 92vw); max-height: 82vh; border-radius: 10px;
    display: flex; flex-direction: column; overflow: hidden;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}
.locmgr-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.9rem 1rem; border-bottom: 1px solid var(--gray-700, #374151); font-weight: 600;
}
.locmgr-header > span { display: inline-flex; align-items: center; gap: 0.4rem; }
.locmgr-close { background: none; border: none; color: inherit; cursor: pointer; }
.locmgr-body { padding: 0.5rem 0.75rem; overflow-y: auto; }
.locmgr-empty { opacity: 0.7; padding: 1rem; text-align: center; }
.locmgr-parent { border-bottom: 1px solid var(--gray-800, #1f2937); padding: 0.35rem 0; }
.locmgr-parent-row, .locmgr-sub-row {
    display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;
}
.locmgr-sub-row { padding: 0.2rem 0 0.2rem 1.6rem; font-size: 0.9em; opacity: 0.95; }
.locmgr-toggle {
    background: none; border: none; color: inherit; cursor: pointer;
    display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.3rem 0; text-align: left;
}
.locmgr-count {
    background: var(--gray-700, #374151); border-radius: 999px;
    padding: 0 0.5rem; margin-left: 0.4rem; font-size: 0.75em;
}
.locmgr-actions { display: inline-flex; gap: 0.35rem; }
.locmgr-actions button {
    background: var(--gray-800, #1f2937); color: inherit;
    border: 1px solid var(--gray-700, #374151); border-radius: 6px;
    padding: 0.2rem 0.5rem; font-size: 0.78em; cursor: pointer;
    display: inline-flex; align-items: center; gap: 0.25rem;
}
.locmgr-actions button:disabled { opacity: 0.5; cursor: default; }
.locmgr-actions button:hover:not(:disabled) { border-color: var(--primary-500, #f59e0b); }
```

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds (component compiles even before it is mounted).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/scenes/LocationManager.jsx frontend/src/components/scenes/LocationManager.css
git commit -m "feat(locations): LocationManager modal component"
```

---

## Task 12: Mount LocationManager in SceneViewer

**Files:**
- Modify: `frontend/src/components/scenes/SceneViewer.jsx` (imports; `ScriptSummary` render ~line 605)

**Interfaces:**
- Consumes: `LocationManager` (Task 11); the existing `scenes` array and refetch callback in `SceneViewer`.
- Produces: a "Manage locations" button that opens the modal; on change, triggers the existing scene refetch.

- [ ] **Step 1: Confirm the refetch handler**

`SceneViewer` already defines `const refreshScenes = useCallback(async () => {...})` at ~line 111 (passed to the breakdown drawer as `onRefreshScene`). This is the reload function to reuse — it re-fetches scenes and updates state. Confirm it still exists before wiring.

- [ ] **Step 2: Add import + state**

Add the import near the other component imports:

```javascript
import LocationManager from './LocationManager';
```

Add state near the other `useState` hooks in `SceneViewer`:

```javascript
    const [showLocationManager, setShowLocationManager] = useState(false);
```

- [ ] **Step 3: Add the trigger button and modal**

Next to where `ScriptSummary` is rendered (~line 605), add a button and the modal. Use the `scriptId` and `scenes` variables already in scope and the `refreshScenes` handler from Step 1:

```jsx
                    <button
                        className="pill-btn"
                        onClick={() => setShowLocationManager(true)}
                    >
                        Manage locations
                    </button>

                    {showLocationManager && (
                        <LocationManager
                            scriptId={scriptId}
                            scenes={scenes}
                            onClose={() => setShowLocationManager(false)}
                            onChanged={refreshScenes}
                        />
                    )}
```

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Manual verification**

Start the app (`cd frontend && npm run dev`, backend running). On a script with a location that has sub-locations:
1. Open "Manage locations" → confirm the parent → sub tree shows correct counts.
2. Rename a parent → confirm scenes, and the schedule board (grouped by location), regroup under the new name and a report reflects it.
3. Rename a sub-location → confirm the sub label updates and `location_canonical` is unchanged.
4. Reassign a scene → confirm only that scene moves.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/scenes/SceneViewer.jsx
git commit -m "feat(locations): mount LocationManager in SceneViewer"
```

---

## Self-Review Notes

- **Spec coverage:** rename parent (T5), rename sub (T6), reassign (T7), merge parents (T7), sticky parent alias (T5 + T4), sticky sub alias (T6 + T4 via `sub_location_aliases` T1), schedule propagation (T8/T9), dedicated manager UI (T11/T12). All spec sections mapped.
- **Sub-label authority:** `subLocationLabel` and `derive_sub_place` both parse from `setting` (never stale hierarchy), so renames applied to `setting` show correctly even after re-analysis.
- **Type consistency:** endpoint bodies (`from_canonical`, `to_name`, `parent_canonical`, `from_sub`, `to_sub`, `scene_id`, `to_parent_name`, `canonical_name`, `source_canonicals`) match the apiService payloads in T10. Helper names (`_rename_parent`, `_rename_sub`, `_reassign_scene`) are consistent across tasks and monkeypatched by the same names in tests.
- **Known limitation:** `subLocationLabel` groups a sub named `(main)` for scenes with no sub-location — display-only bucket, not persisted.
