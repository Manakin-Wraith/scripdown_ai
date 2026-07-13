# Location Manager — Nesting & Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users manually nest a stray top-level location under another (keeping its name as a sub) and un-nest it, and replace the Location Manager's browser prompts / `(main)` jargon with inline editing and a purpose header.

**Architecture:** A new `nest`/`unnest` pair of operations reuses v1's rewrite machinery: `nest` rewrites a location's scenes to `INT. {parent} - {set} - {time}` with `location_canonical` = the parent **base** (fixing the v1 bug where a combined name became its own node), and persists stickiness via a new nullable `set_name` column on `location_aliases`, applied in the pure `resolve_location`. The frontend `LocationManager` is reworked in place: inline rename, `Move under…` / `Move out`, no `(main)` row, a purpose header.

**Tech Stack:** Flask (Python 3.13), supabase-py (service-role key), pytest; React 18 + Vite (plain JSX), no TS.

## Global Constraints

- Every script-scoped write endpoint gates on `_user_can_access_script(script_id, user_id)` → 403; `@require_auth`; body validation → 400.
- Normalized place keys are produced ONLY by `normalize_place()`.
- `nest` sets `location_canonical` to `normalize_place(parent_name)` (the parent **base**), NOT `normalize_place("{parent} - {set}")` — the latter was the v1 bug that produced `VILLA - BACKROOM` as its own top-level node.
- Nesting is **two-level only**: a location is top-level or a sub of one parent.
- `resolve_location` must apply the parent remap first, then the sub remap; a `location_aliases` row with a NULL `set_name` must behave EXACTLY as it does today (no regression).
- Frontend is plain JS (no TS); gate is `cd frontend && npm run build` (lint is pre-broken).
- Backend tests: `cd backend && source venv/bin/activate && python -m pytest tests/<file> -v`. Route tests set `middleware.auth.DEV_MODE` and monkeypatch module-level names on `routes.supabase_routes`.
- Migrations: `backend/db/migrations/NNN_*.sql`; next number is **039**. Apply via Supabase MCP `apply_migration` or `backend/db/run_migration.py`.
- Supabase project id: `twzfaizeyqwevmhjyicz`.

---

## File Structure

- `backend/db/migrations/039_location_aliases_set_name.sql` — **create** — add nullable `set_name` column.
- `backend/services/location_resolver.py` — **modify** — extend `resolve_location` with a `parent_set_map`.
- `backend/tests/test_location_resolver.py` — **modify** — unit tests for the `parent_set_map` behavior.
- `backend/routes/supabase_routes.py` — **modify** — `_apply_location_alias` builds/passes `parent_set_map`; add `_nest` + `_unnest` helpers and their two endpoints.
- `backend/tests/test_location_manager_routes.py` — **modify** — auth/validation + recording-stub tests for nest/unnest.
- `frontend/src/services/apiService.js` — **modify** — `nestLocation`, `unnestLocation`.
- `frontend/src/components/scenes/LocationManager.jsx` — **modify** — full rework (inline rename, Move under…/Move out, drop `(main)`, header).
- `frontend/src/components/scenes/LocationManager.css` — **modify** — styles for the new controls.

---

## Task 1: Migration — `set_name` column on `location_aliases`

**Files:**
- Create: `backend/db/migrations/039_location_aliases_set_name.sql`

**Interfaces:**
- Produces: `location_aliases.set_name TEXT` (nullable).

- [ ] **Step 1: Write migration 039**

Create `backend/db/migrations/039_location_aliases_set_name.sql`:

```sql
-- Migration 039: nesting support.
-- A nullable set_name on location_aliases turns a parent remap into a NEST:
-- when present, re-analysis rewrites the base to "{canonical_place} - {set_name}"
-- and keeps location_canonical = canonical_place (the parent base).
-- Existing rows keep set_name NULL and behave exactly as before.

ALTER TABLE location_aliases ADD COLUMN IF NOT EXISTS set_name TEXT;
```

- [ ] **Step 2: Apply the migration**

Apply via Supabase MCP `apply_migration` (project `twzfaizeyqwevmhjyicz`, name `039_location_aliases_set_name`) or `cd backend && python db/run_migration.py 039_location_aliases_set_name.sql`.

- [ ] **Step 3: Verify the column exists**

Run (Supabase SQL): `SELECT column_name FROM information_schema.columns WHERE table_name='location_aliases' AND column_name='set_name';`
Expected: one row, `set_name`.

- [ ] **Step 4: Commit**

```bash
git add backend/db/migrations/039_location_aliases_set_name.sql
git commit -m "feat(locations): add set_name column to location_aliases (migration 039)"
```

---

## Task 2: Extend `resolve_location` with `parent_set_map`

**Files:**
- Modify: `backend/services/location_resolver.py` (`resolve_location`)
- Test: `backend/tests/test_location_resolver.py`

**Interfaces:**
- Consumes: existing `derive_base_place`, `derive_sub_place`, `normalize_place`, `canonicalize_setting`, `rewrite_place_token`.
- Produces: `resolve_location(setting, int_ext=None, time_of_day=None, location_hierarchy=None, parent_alias_map=None, sub_alias_map=None, parent_set_map=None) -> (new_setting, canonical_norm)`. `parent_set_map`: `{base_norm: (parent_place, set_name)}` — when a scene's base matches, the base token is rewritten to `"{parent_place} - {set_name}"` and canonical becomes `normalize_place(parent_place)`.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_location_resolver.py`:

```python
def test_resolve_location_nest_sets_base_canonical_not_combined():
    # Nesting GARAGE / BACKROOM under VILLA: setting gets the parent prefixed,
    # but canonical is the parent BASE (VILLA), not "VILLA - GARAGE / BACKROOM".
    setting, canonical = resolve_location(
        "INT. GARAGE / BACKROOM - DAY", "INT", "DAY", None,
        parent_set_map={"GARAGE / BACKROOM": ("VILLA", "GARAGE / BACKROOM")},
    )
    assert setting == "INT. VILLA - GARAGE / BACKROOM - DAY"
    assert canonical == "VILLA"

def test_resolve_location_null_set_name_path_unchanged():
    # A plain parent alias (no set_name) still behaves exactly as before.
    setting, canonical = resolve_location(
        "INT. VILLA - BATHROOM - DAY", "INT", "DAY", None,
        parent_alias_map={"VILLA": "SMITH RESIDENCE"},
    )
    assert setting == "INT. SMITH RESIDENCE - BATHROOM - DAY"
    assert canonical == "SMITH RESIDENCE"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_location_resolver.py -k "nest_sets_base or null_set_name" -v`
Expected: FAIL (`parent_set_map` is an unexpected keyword argument).

- [ ] **Step 3: Rewrite `resolve_location`**

Replace the body of `resolve_location` in `backend/services/location_resolver.py` with (adds `parent_set_map`; the sub-alias block runs once for both branches — no duplication):

```python
def resolve_location(
    setting: Optional[str],
    int_ext: Optional[str] = None,
    time_of_day: Optional[str] = None,
    location_hierarchy=None,
    parent_alias_map: Optional[Dict[str, str]] = None,
    sub_alias_map: Optional[Dict] = None,
    parent_set_map: Optional[Dict] = None,
) -> tuple:
    """Apply parent, nest, then sub aliases to a scene setting (pure).

    Returns (new_setting, location_canonical_norm). A parent_set_map entry
    NESTS the base under a parent, keeping the base as a sub:
    base -> "{parent} - {set}", canonical -> normalize(parent). A plain
    parent_alias_map entry just remaps the base. The sub remap runs last.
    """
    parent_alias_map = parent_alias_map or {}
    sub_alias_map = sub_alias_map or {}
    parent_set_map = parent_set_map or {}

    setting = canonicalize_setting(setting)
    base = derive_base_place(setting, int_ext, time_of_day, location_hierarchy)
    new_setting = setting or ""

    if base in parent_set_map:
        parent_place, set_name = parent_set_map[base]
        if base:
            new_setting = rewrite_place_token(new_setting, base, f"{parent_place} - {set_name}")
        parent_norm = normalize_place(parent_place)
    else:
        canonical = parent_alias_map.get(base, base)
        if base and normalize_place(canonical) != base:
            new_setting = rewrite_place_token(new_setting, base, canonical)
        parent_norm = normalize_place(canonical)

    sub = derive_sub_place(new_setting, int_ext, time_of_day, None)
    if sub:
        new_sub = sub_alias_map.get((parent_norm, sub))
        if new_sub and normalize_place(new_sub) != sub:
            new_setting = rewrite_place_token(new_setting, sub, new_sub)

    return new_setting, parent_norm
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_location_resolver.py -v`
Expected: PASS (all resolver tests, including the two new + all prior).

- [ ] **Step 5: Commit**

```bash
git add backend/services/location_resolver.py backend/tests/test_location_resolver.py
git commit -m "feat(locations): resolve_location supports nest via parent_set_map"
```

---

## Task 3: Wire `parent_set_map` through `_apply_location_alias`

**Files:**
- Modify: `backend/routes/supabase_routes.py` (`_apply_location_alias`)

**Interfaces:**
- Consumes: `resolve_location` (Task 2), `location_aliases.set_name` (Task 1).
- Produces: `_apply_location_alias(script_id, setting, int_ext, time_of_day, location_hierarchy) -> (setting, location_canonical)` — unchanged signature; now also applies nest aliases.

- [ ] **Step 1: Read the current function**

Read `_apply_location_alias` in `backend/routes/supabase_routes.py` (search for `def _apply_location_alias`). It currently builds `parent_map` and `sub_map` from `location_aliases` / `sub_location_aliases` and calls `resolve_location(..., parent_map, sub_map)`.

- [ ] **Step 2: Replace the parent-map build + the call**

Change the `location_aliases` select to include `set_name`, split rows into plain vs nest maps, and pass `parent_set_map`. The function becomes:

```python
def _apply_location_alias(script_id, setting, int_ext, time_of_day, location_hierarchy):
    """Return (setting, location_canonical) with parent, nest, and sub aliases
    applied. Non-fatal on lookup failure (degrades to derived base place)."""
    parent_map = {}
    parent_set_map = {}
    sub_map = {}
    try:
        rows = supabase.table('location_aliases').select(
            'alias_place, canonical_place, set_name'
        ).eq('script_id', script_id).execute().data or []
        for r in rows:
            if r.get('set_name'):
                parent_set_map[r['alias_place']] = (r['canonical_place'], r['set_name'])
            else:
                parent_map[r['alias_place']] = r['canonical_place']
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
        setting, int_ext, time_of_day, location_hierarchy,
        parent_map, sub_map, parent_set_map,
    )
```

- [ ] **Step 3: Verify import boot + resolver suite**

Run: `cd backend && source venv/bin/activate && python -c "import routes.supabase_routes" && python -m pytest tests/test_location_resolver.py -q`
Expected: no ImportError; resolver tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/routes/supabase_routes.py
git commit -m "refactor(locations): apply nest aliases in _apply_location_alias"
```

---

## Task 4: `nest` endpoint

**Files:**
- Modify: `backend/routes/supabase_routes.py` (add `_nest` + route beside the other location endpoints)
- Test: `backend/tests/test_location_manager_routes.py`

**Interfaces:**
- Consumes: `normalize_place`, `canonicalize_setting`.
- Produces:
  - `_nest(script_id, source_canonical, parent_name, user_id) -> int`.
  - `POST /api/scripts/<script_id>/locations/nest` body `{ source_canonical, parent_name }` → `{ success, scenes_updated }`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_location_manager_routes.py`:

```python
def test_nest_forbidden_for_non_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: False)
    resp = _client().post("/api/scripts/s1/locations/nest",
                          json={"source_canonical": "GARAGE", "parent_name": "VILLA"})
    assert resp.status_code == 403

def test_nest_validates_body(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    resp = _client().post("/api/scripts/s1/locations/nest", json={"parent_name": "VILLA"})
    assert resp.status_code == 400

def test_nest_ok_calls_helper(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    monkeypatch.setattr(sr, "_nest", lambda script_id, src, parent, uid: 5)
    resp = _client().post("/api/scripts/s1/locations/nest",
                          json={"source_canonical": "GARAGE", "parent_name": "VILLA"})
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "scenes_updated": 5}

def test_nest_helper_sets_parent_base_canonical(monkeypatch):
    # _nest must set location_canonical to the parent BASE (VILLA), write
    # hierarchy [VILLA, set], and upsert a location_aliases row with set_name.
    calls = []
    class _Q:
        def __init__(self, table):
            self.table = table; self._eq = {}; self._update = None; self._upsert = None
        def select(self, *a, **k): return self
        def update(self, payload): self._update = payload; return self
        def upsert(self, payload, *a, **k): self._upsert = payload; return self
        def eq(self, col, val): self._eq[col] = val; return self
        def execute(self):
            calls.append((self.table, self._update, self._upsert, dict(self._eq)))
            class _R:
                data = [{"id": "sc1", "int_ext": "INT", "time_of_day": "DAY"}] \
                    if self.table == "scenes" and self._update is None else []
            return _R()
    class _FakeSupa:
        def table(self, name): return _Q(name)
    monkeypatch.setattr(sr, "supabase", _FakeSupa())
    n = sr._nest("s1", "GARAGE / BACKROOM", "VILLA", "u1")
    assert n == 1
    scene_updates = [u for (t, u, _up, _eq) in calls if t == "scenes" and u is not None]
    assert scene_updates and scene_updates[0]["location_canonical"] == "VILLA"
    assert scene_updates[0]["location_hierarchy"] == ["VILLA", "GARAGE / BACKROOM"]
    upserts = [up for (t, _u, up, _eq) in calls if t == "location_aliases" and up is not None]
    assert upserts and upserts[0]["set_name"] == "GARAGE / BACKROOM" \
        and upserts[0]["canonical_place"] == "VILLA" and upserts[0]["alias_place"] == "GARAGE / BACKROOM"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_location_manager_routes.py -k nest -v`
Expected: FAIL (route 404 / `_nest` missing).

- [ ] **Step 3: Implement `_nest` + route**

Add to `backend/routes/supabase_routes.py`, beside the other `locations/*` routes (e.g. after `merge_parent_locations`):

```python
def _nest(script_id, source_canonical, parent_name, user_id):
    """Nest a location under a parent, keeping its name as the sub. Every scene
    under source_canonical is rewritten to "{int_ext}. {parent} - {set} - {time}",
    location_canonical set to the parent BASE, hierarchy [parent, set]; a sticky
    location_aliases row (with set_name) is upserted. Returns scenes updated."""
    source_norm = normalize_place(source_canonical)
    parent_norm = normalize_place(parent_name)

    set_name = source_norm
    for sep in (' - ', ', ', ' '):
        prefix = parent_norm + sep
        if set_name.startswith(prefix):
            set_name = set_name[len(prefix):].strip(' -,')
            break
    if not set_name:
        set_name = source_norm

    result = supabase.table('scenes').select(
        'id, int_ext, time_of_day'
    ).eq('script_id', script_id).eq('location_canonical', source_norm).execute()
    scenes = result.data or []
    updated = 0
    for scene in scenes:
        ie = (scene.get('int_ext') or 'INT').strip().rstrip('.')
        tod = (scene.get('time_of_day') or '').strip()
        new_setting = f"{ie}. {parent_norm} - {set_name}"
        if tod:
            new_setting += f" - {tod}"
        supabase.table('scenes').update({
            'setting': canonicalize_setting(new_setting),
            'location_canonical': parent_norm,
            'location_hierarchy': [parent_norm, set_name],
        }).eq('id', scene['id']).execute()
        updated += 1

    try:
        supabase.table('location_aliases').upsert({
            'script_id': script_id,
            'alias_place': source_norm,
            'canonical_place': parent_norm,
            'set_name': set_name,
            'merged_by': user_id,
        }, on_conflict='script_id,alias_place').execute()
    except Exception as nest_err:
        print(f"Warning: failed to store nest alias: {nest_err}")

    return updated


@supabase_bp.route('/api/scripts/<script_id>/locations/nest', methods=['POST'])
@require_auth
def nest_location(script_id):
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        data = request.get_json() or {}
        source_canonical = (data.get('source_canonical') or '').strip()
        parent_name = (data.get('parent_name') or '').strip()
        user_id = get_user_id()
        if not _user_can_access_script(script_id, user_id):
            return jsonify({'error': 'Not authorized for this script'}), 403
        if not source_canonical or not parent_name:
            return jsonify({'error': 'source_canonical and parent_name are required'}), 400
        updated = _nest(script_id, source_canonical, parent_name, user_id)
        return jsonify({'success': True, 'scenes_updated': updated}), 200
    except Exception as e:
        print(f"Error nesting location: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_location_manager_routes.py -k nest -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/routes/supabase_routes.py backend/tests/test_location_manager_routes.py
git commit -m "feat(locations): nest endpoint"
```

---

## Task 5: `unnest` endpoint

**Files:**
- Modify: `backend/routes/supabase_routes.py` (add `_unnest` + route after Task 4)
- Test: `backend/tests/test_location_manager_routes.py`

**Interfaces:**
- Consumes: `derive_sub_place`, `normalize_place`, `canonicalize_setting`.
- Produces:
  - `_unnest(script_id, parent_canonical, set_name, user_id) -> int`.
  - `POST /api/scripts/<script_id>/locations/unnest` body `{ parent_canonical, set_name }` → `{ success, scenes_updated }`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_location_manager_routes.py`:

```python
def test_unnest_forbidden_for_non_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: False)
    resp = _client().post("/api/scripts/s1/locations/unnest",
                          json={"parent_canonical": "VILLA", "set_name": "GARAGE"})
    assert resp.status_code == 403

def test_unnest_validates_body(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    resp = _client().post("/api/scripts/s1/locations/unnest", json={"parent_canonical": "VILLA"})
    assert resp.status_code == 400

def test_unnest_ok_calls_helper(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    monkeypatch.setattr(sr, "_unnest", lambda script_id, parent, setn, uid: 2)
    resp = _client().post("/api/scripts/s1/locations/unnest",
                          json={"parent_canonical": "VILLA", "set_name": "GARAGE"})
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "scenes_updated": 2}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_location_manager_routes.py -k unnest -v`
Expected: FAIL.

- [ ] **Step 3: Implement `_unnest` + route**

Add after the `nest` route:

```python
def _unnest(script_id, parent_canonical, set_name, user_id):
    """Promote a nested set back to its own top-level location. Scenes under
    parent_canonical whose sub == set_name are rewritten to
    "{int_ext}. {set} - {time}", location_canonical set to the set, hierarchy
    [set]; the sticky nest alias for this set under this parent is removed.
    Returns scenes updated."""
    parent_norm = normalize_place(parent_canonical)
    set_norm = normalize_place(set_name)

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
        if sub != set_norm:
            continue
        ie = (scene.get('int_ext') or 'INT').strip().rstrip('.')
        tod = (scene.get('time_of_day') or '').strip()
        new_setting = f"{ie}. {set_norm}"
        if tod:
            new_setting += f" - {tod}"
        supabase.table('scenes').update({
            'setting': canonicalize_setting(new_setting),
            'location_canonical': set_norm,
            'location_hierarchy': [set_norm],
        }).eq('id', scene['id']).execute()
        updated += 1

    try:
        supabase.table('location_aliases').delete().eq(
            'script_id', script_id
        ).eq('canonical_place', parent_norm).eq('set_name', set_norm).execute()
    except Exception as unnest_err:
        print(f"Warning: failed to remove nest alias: {unnest_err}")

    return updated


@supabase_bp.route('/api/scripts/<script_id>/locations/unnest', methods=['POST'])
@require_auth
def unnest_location(script_id):
    if not supabase:
        return jsonify({'error': 'Supabase not configured'}), 500
    try:
        data = request.get_json() or {}
        parent_canonical = (data.get('parent_canonical') or '').strip()
        set_name = (data.get('set_name') or '').strip()
        user_id = get_user_id()
        if not _user_can_access_script(script_id, user_id):
            return jsonify({'error': 'Not authorized for this script'}), 403
        if not parent_canonical or not set_name:
            return jsonify({'error': 'parent_canonical and set_name are required'}), 400
        updated = _unnest(script_id, parent_canonical, set_name, user_id)
        return jsonify({'success': True, 'scenes_updated': updated}), 200
    except Exception as e:
        print(f"Error un-nesting location: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_location_manager_routes.py -v`
Expected: PASS (all route tests, nest + unnest + prior).

- [ ] **Step 5: Commit**

```bash
git add backend/routes/supabase_routes.py backend/tests/test_location_manager_routes.py
git commit -m "feat(locations): unnest endpoint"
```

---

## Task 6: apiService `nestLocation` / `unnestLocation`

**Files:**
- Modify: `frontend/src/services/apiService.js` (near the other `locations/*` functions)

**Interfaces:**
- Produces (return `response.data`):
  - `nestLocation(scriptId, sourceCanonical, parentName)` → POST `/locations/nest` body `{ source_canonical, parent_name }`.
  - `unnestLocation(scriptId, parentCanonical, setName)` → POST `/locations/unnest` body `{ parent_canonical, set_name }`.

- [ ] **Step 1: Add the functions**

Add after `mergeParentLocations` in `frontend/src/services/apiService.js`:

```javascript
export const nestLocation = async (scriptId, sourceCanonical, parentName) => {
    const response = await api.post(`/api/scripts/${scriptId}/locations/nest`, {
        source_canonical: sourceCanonical,
        parent_name: parentName,
    });
    return response.data;
};

export const unnestLocation = async (scriptId, parentCanonical, setName) => {
    const response = await api.post(`/api/scripts/${scriptId}/locations/unnest`, {
        parent_canonical: parentCanonical,
        set_name: setName,
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
git commit -m "feat(locations): apiService nest/unnest functions"
```

---

## Task 7: Rework `LocationManager` — inline rename, Move under…/Move out, drop `(main)`, header

**Files:**
- Modify: `frontend/src/components/scenes/LocationManager.jsx`
- Modify: `frontend/src/components/scenes/LocationManager.css`

**Interfaces:**
- Consumes: `locationKey`, `subLocationLabel`; `renameParentLocation`, `renameSubLocation`, `reassignSceneLocation`, `mergeParentLocations`, `nestLocation`, `unnestLocation`; `useToast`.
- Produces: default export `LocationManager({ scriptId, scenes, onClose, onChanged })` (unchanged props).

- [ ] **Step 1: Replace `LocationManager.jsx`**

Replace the entire file `frontend/src/components/scenes/LocationManager.jsx` with:

```javascript
import React, { useMemo, useState, useCallback } from 'react';
import { X, MapPin } from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { locationKey, subLocationLabel } from '../../utils/locationKey';
import {
    renameParentLocation,
    renameSubLocation,
    nestLocation,
    unnestLocation,
} from '../../services/apiService';
import './LocationManager.css';

// Build parent -> real subs tree. A parent whose scenes sit directly on it
// (no sub-location) simply carries a higher count; no "(main)" row is rendered.
function buildTree(scenes) {
    const parents = {};
    (scenes || []).forEach((scene) => {
        if (scene.is_omitted) return;
        const parent = locationKey(scene);
        const sub = subLocationLabel(scene);
        if (!parents[parent]) parents[parent] = { name: parent, count: 0, subs: {} };
        parents[parent].count += 1;
        if (sub) {
            if (!parents[parent].subs[sub]) parents[parent].subs[sub] = { name: sub, count: 0 };
            parents[parent].subs[sub].count += 1;
        }
    });
    return Object.values(parents)
        .map((p) => ({ ...p, subs: Object.values(p.subs).sort((a, b) => a.name.localeCompare(b.name)) }))
        .sort((a, b) => a.name.localeCompare(b.name));
}

const LocationManager = ({ scriptId, scenes, onClose, onChanged }) => {
    const toast = useToast();
    const [busy, setBusy] = useState(false);
    const [editing, setEditing] = useState(null); // { kind:'parent'|'sub', parent, name }
    const [editValue, setEditValue] = useState('');
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
            setEditing(null);
        }
    }, [busy, toast, onChanged]);

    const startEdit = (kind, parent, name) => {
        setEditing({ kind, parent, name });
        setEditValue(name);
    };

    const commitEdit = () => {
        if (!editing) return;
        const to = editValue.trim();
        if (!to || to === editing.name) { setEditing(null); return; }
        if (editing.kind === 'parent') {
            run('Location renamed', () => renameParentLocation(scriptId, editing.name, to));
        } else {
            run('Sub-location renamed', () => renameSubLocation(scriptId, editing.parent, editing.name, to));
        }
    };

    const onEditKey = (e) => {
        if (e.key === 'Enter') commitEdit();
        else if (e.key === 'Escape') setEditing(null);
    };

    const doNest = (source, parentName) => {
        if (!parentName) return;
        run('Location nested', () => nestLocation(scriptId, source, parentName));
    };

    const doUnnest = (parent, setName) => {
        run('Location moved out', () => unnestLocation(scriptId, parent, setName));
    };

    // A top-level location may be nested under another only if it has no real
    // subs of its own (two-level constraint). Any other top-level is a valid target.
    const parentNames = tree.map((p) => p.name);

    const renderName = (kind, parent, name) => {
        const isEditing = editing && editing.kind === kind && editing.name === name
            && (kind === 'parent' || editing.parent === parent);
        if (isEditing) {
            return (
                <input
                    className="locmgr-edit"
                    autoFocus
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onKeyDown={onEditKey}
                    onBlur={commitEdit}
                    disabled={busy}
                />
            );
        }
        return (
            <button className="locmgr-name" onClick={() => startEdit(kind, parent, name)} title="Click to rename">
                {name}
            </button>
        );
    };

    return (
        <div className="locmgr-overlay" onClick={onClose}>
            <div className="locmgr-modal" onClick={(e) => e.stopPropagation()}>
                <div className="locmgr-header">
                    <span><MapPin size={16} /> Manage Locations</span>
                    <button className="locmgr-close" onClick={onClose} aria-label="Close"><X size={18} /></button>
                </div>
                <p className="locmgr-purpose">
                    Group your locations the way you'll shoot them — nest rooms and areas under
                    the building or place they belong to.
                </p>
                <div className="locmgr-body">
                    {tree.length === 0 && <p className="locmgr-empty">No locations yet.</p>}
                    {tree.map((parent) => {
                        const nestable = parent.subs.length === 0;
                        return (
                            <div key={parent.name} className="locmgr-parent">
                                <div className="locmgr-parent-row">
                                    <span className="locmgr-parent-name">
                                        {renderName('parent', null, parent.name)}
                                        <span className="locmgr-count">{parent.count}</span>
                                    </span>
                                    {nestable && (
                                        <select
                                            className="locmgr-move"
                                            disabled={busy}
                                            value=""
                                            onChange={(e) => doNest(parent.name, e.target.value)}
                                        >
                                            <option value="">Move under…</option>
                                            {parentNames
                                                .filter((n) => n !== parent.name)
                                                .map((n) => <option key={n} value={n}>{n}</option>)}
                                        </select>
                                    )}
                                </div>
                                {parent.subs.map((sub) => (
                                    <div key={sub.name} className="locmgr-sub-row">
                                        <span className="locmgr-sub-name">
                                            {renderName('sub', parent.name, sub.name)}
                                            <span className="locmgr-count">{sub.count}</span>
                                        </span>
                                        <button
                                            className="locmgr-moveout"
                                            disabled={busy}
                                            onClick={() => doUnnest(parent.name, sub.name)}
                                        >
                                            Move out
                                        </button>
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

- [ ] **Step 2: Update `LocationManager.css`**

Replace the entire file `frontend/src/components/scenes/LocationManager.css` with:

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
.locmgr-purpose {
    margin: 0; padding: 0.6rem 1rem; font-size: 0.82em; line-height: 1.35;
    color: var(--gray-400, #9ca3af); border-bottom: 1px solid var(--gray-800, #1f2937);
}
.locmgr-body { padding: 0.5rem 0.75rem; overflow-y: auto; }
.locmgr-empty { opacity: 0.7; padding: 1rem; text-align: center; }
.locmgr-parent { border-bottom: 1px solid var(--gray-800, #1f2937); padding: 0.4rem 0; }
.locmgr-parent-row, .locmgr-sub-row {
    display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;
}
.locmgr-sub-row { padding: 0.2rem 0 0.2rem 1.6rem; font-size: 0.9em; opacity: 0.95; }
.locmgr-parent-name, .locmgr-sub-name { display: inline-flex; align-items: center; gap: 0.4rem; }
.locmgr-parent-name .locmgr-name { font-weight: 600; }
.locmgr-name {
    background: none; border: none; color: inherit; cursor: text;
    padding: 0.2rem 0.15rem; text-align: left; border-radius: 4px;
}
.locmgr-name:hover { background: var(--gray-800, #1f2937); }
.locmgr-edit {
    background: var(--gray-800, #1f2937); color: inherit;
    border: 1px solid var(--primary-500, #f59e0b); border-radius: 4px;
    padding: 0.2rem 0.35rem; font: inherit; min-width: 12rem;
}
.locmgr-count {
    background: var(--gray-700, #374151); border-radius: 999px;
    padding: 0 0.5rem; font-size: 0.75em;
}
.locmgr-move, .locmgr-moveout {
    background: var(--gray-800, #1f2937); color: inherit;
    border: 1px solid var(--gray-700, #374151); border-radius: 6px;
    padding: 0.2rem 0.5rem; font-size: 0.78em; cursor: pointer;
}
.locmgr-move:hover:not(:disabled), .locmgr-moveout:hover:not(:disabled) {
    border-color: var(--primary-500, #f59e0b);
}
.locmgr-move:disabled, .locmgr-moveout:disabled { opacity: 0.5; cursor: default; }
```

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Manual verification (deferred to user for full E2E)**

Reviewer/implementer confirms the build compiles. Full manual E2E is a user step: open Manage Locations on a script; confirm (a) no browser prompt appears on rename — the name becomes an inline field; (b) no `(main)` row; (c) a stray location shows a `Move under…` dropdown and choosing a parent nests it; (d) a sub shows `Move out`; (e) the purpose line renders.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/scenes/LocationManager.jsx frontend/src/components/scenes/LocationManager.css
git commit -m "feat(locations): rework LocationManager — inline rename, nest/unnest, no (main)"
```

---

## Self-Review Notes

- **Spec coverage:** nest op (T2 resolve + T4 endpoint), unnest (T5), sticky set_name (T1 column + T2/T3 resolve), canonical=parent-base fix (T2 test + T4 helper), inline rename / no `(main)` / purpose header / Move under…/Move out (T7), apiService (T6). All spec sections mapped.
- **Canonical-base guarantee:** both the `resolve_location` nest branch (T2) and `_nest` (T4) set canonical to `normalize_place(parent)`, never the combined `"parent - set"` — asserted by `test_resolve_location_nest_sets_base_canonical_not_combined` and `test_nest_helper_sets_parent_base_canonical`.
- **No regression:** a NULL `set_name` alias row routes to the plain `parent_alias_map` branch (T3) and through the unchanged `resolve_location` else-branch (T2), covered by `test_resolve_location_null_set_name_path_unchanged`.
- **Type consistency:** endpoint bodies (`source_canonical`, `parent_name`, `parent_canonical`, `set_name`) match the apiService payloads (T6) and the helper params (`_nest(script_id, source_canonical, parent_name, user_id)`, `_unnest(script_id, parent_canonical, set_name, user_id)`), consistent across tasks and monkeypatched by the same names in tests.
- **Two-level constraint** enforced in the UI: `Move under…` renders only when `parent.subs.length === 0` (T7).
- **DRY:** `resolve_location` runs the sub-alias block once for both branches (T2), avoiding the verbatim-duplication defect.
