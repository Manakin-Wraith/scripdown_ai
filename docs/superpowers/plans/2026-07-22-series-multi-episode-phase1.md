# Series / Multi-Episode Analysis — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Series → Season → Episode grouping layer on top of the existing single-script data model, with a combined (exact-name-grouped) cast view per season, and zero changes to per-script upload/parsing/analysis/billing.

**Architecture:** Two new Postgres tables (`series`, `seasons`) plus two new nullable columns on `scripts` (`season_id`, `episode_number`). A new Flask blueprint (`series_routes.py`) exposes CRUD + a combined-cast aggregation endpoint, reusing the existing `get_script_role` per-episode access check (no new permission system). Frontend gets a reusable series/season picker component (used both at upload time and for later reassignment) and two new pages (series list, season detail with combined cast).

**Tech Stack:** Flask + supabase-py (backend), React 18 + Vite + React Router v6 + axios (frontend), Postgres/Supabase migrations.

## Global Constraints

- Backend gate: `pytest tests/` from `backend/` must pass (frontend `npm run lint` is broken repo-wide — do not gate on it; use `npm run build` for frontend).
- No changes to `extraction_pipeline.py`, `entity_resolver.py`, `entitlement_service.py`, or any billing/PayFast code — this feature has zero entitlement impact by design (spec §3.3).
- Every new route must require `@require_auth`; per-episode visibility must use `get_script_role` (`middleware/authorization.py`), never a new/parallel access check.
- `scripts.season_id` / `scripts.episode_number` are nullable and default to `NULL` — no backfill, no behavior change for scripts not in a series.
- Follow existing code conventions exactly: Blueprint-per-domain, `get_supabase_admin()` for the module's own table ops, `jsonify`/try-except-print(500) error shape, snake_case JSON fields — matching `backend/routes/invite_routes.py`.

---

## File Structure

- **Create:** `backend/db/migrations/045_series_seasons.sql` — new tables, columns, indexes, RLS.
- **Create:** `backend/routes/series_routes.py` — all new backend routes for this feature.
- **Modify:** `backend/app.py` — register the new blueprint.
- **Modify:** `backend/tests/test_route_enforcement.py` — add the single-script-scoped `PATCH /api/scripts/<id>/season` route to the existing regression coverage.
- **Create:** `backend/tests/test_series_routes.py` — all new route tests (CRUD, access filtering, cast grouping).
- **Modify:** `frontend/src/services/apiService.js` — new API wrapper functions.
- **Create:** `frontend/src/components/series/SeriesPicker.jsx` — the reusable 3-state picker (none / existing season / new series), used at upload time and for later reassignment.
- **Modify:** `frontend/src/components/script/ScriptUpload.jsx` — wire in `SeriesPicker`, fire the reassignment call after a successful upload.
- **Create:** `frontend/src/pages/SeriesListPage.jsx` — `/series` route.
- **Create:** `frontend/src/pages/SeasonPage.jsx` — `/series/:seriesId/seasons/:seasonId` route, including the combined cast view.
- **Modify:** `frontend/src/App.jsx` — add the two new routes.

---

### Task 1: Migration — `series`, `seasons` tables and `scripts` columns

**Files:**
- Create: `backend/db/migrations/045_series_seasons.sql`

**Interfaces:**
- Produces: `series(id, owner_id, title, created_at)`, `seasons(id, series_id, season_number, title, created_at)`, `scripts.season_id` (nullable FK → `seasons.id`), `scripts.episode_number` (nullable int). Every later task's SQL/supabase-py calls assume these exact column names.

- [ ] **Step 1: Write the migration**

```sql
-- Migration 045: Series / Season grouping (Phase 1 -- grouping layer only)
-- A series groups seasons; a season groups episode scripts. Purely
-- organizational -- no changes to scripts.* analysis/billing columns,
-- and no changes to how an individual script is uploaded or analyzed.
-- scripts.season_id / scripts.episode_number are both nullable: a
-- standalone script (the common case, unchanged) has both NULL.

CREATE TABLE IF NOT EXISTS series (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_series_owner ON series(owner_id);

CREATE TABLE IF NOT EXISTS seasons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    series_id UUID NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    season_number INT NOT NULL,
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (series_id, season_number)
);

CREATE INDEX idx_seasons_series ON seasons(series_id);

ALTER TABLE scripts
    ADD COLUMN IF NOT EXISTS season_id UUID REFERENCES seasons(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS episode_number INT;

CREATE INDEX IF NOT EXISTS idx_scripts_season ON scripts(season_id);

-- RLS: owner-only, matching the existing pattern in
-- 030_shooting_schedules.sql. The backend uses the service-role key and
-- bypasses RLS for all app-layer access (per-episode team access is
-- enforced in Python via get_script_role, not here) -- this is a
-- defense-in-depth backstop for any direct client-side table access.
ALTER TABLE series ENABLE ROW LEVEL SECURITY;
ALTER TABLE seasons ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own series"
    ON series FOR SELECT
    USING (owner_id = auth.uid());

CREATE POLICY "Users can manage their own series"
    ON series FOR ALL
    USING (owner_id = auth.uid());

CREATE POLICY "Users can view seasons of their series"
    ON seasons FOR SELECT
    USING (
        series_id IN (SELECT id FROM series WHERE owner_id = auth.uid())
    );

CREATE POLICY "Users can manage seasons of their series"
    ON seasons FOR ALL
    USING (
        series_id IN (SELECT id FROM series WHERE owner_id = auth.uid())
    );
```

- [ ] **Step 2: Apply the migration to the local/dev Supabase project and confirm it runs cleanly**

Run this via whatever mechanism the repo already uses to apply migrations to the connected Supabase project (check `backend/db/migrations/044_payfast_reject_reason.sql`'s deploy note / project conventions — there's no local migration-runner script in this repo; migrations are applied directly against the Supabase project's SQL editor or CLI). Confirm no errors and that `series`, `seasons` exist and `scripts` has the two new nullable columns.

- [ ] **Step 3: Commit**

```bash
git add backend/db/migrations/045_series_seasons.sql
git commit -m "feat(series): add series/seasons tables and scripts.season_id/episode_number columns"
```

---

### Task 2: Series & season CRUD routes

**Files:**
- Create: `backend/routes/series_routes.py`
- Test: `backend/tests/test_series_routes.py`

**Interfaces:**
- Consumes: `get_supabase_admin()` (`db/supabase_client.py`), `require_auth`/`get_user_id()` (`middleware/auth.py`).
- Produces: `series_bp` (Flask Blueprint, imported by Task 5's `app.py` change and by Task 3/4's additions to the same file). Routes: `POST /api/series`, `GET /api/series`, `POST /api/series/<series_id>/seasons`, `GET /api/series/<series_id>/seasons`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_series_routes.py`:

```python
"""
Series/season CRUD route tests.

Mirrors the MockTable/MockSupabase pattern from test_accept_invite.py --
a minimal chainable supabase-py stand-in supporting select/insert/eq/order/
single, backed by a shared in-memory store so route code and any
get_script_role calls see the same data.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.series_routes as sr
from middleware.auth import DEV_USER_ID


class MockTable:
    """Chainable supabase-py stand-in supporting select/insert/eq/order/single."""

    def __init__(self, name, store):
        self.name = name
        self.store = store
        self._filters = {}
        self._op = None
        self._payload = None
        self._single = False
        self._order_col = None

    def select(self, *_a, **_k):
        self._op = "select"
        return self

    def insert(self, data):
        self._op = "insert"
        self._payload = data
        return self

    def update(self, data):
        self._op = "update"
        self._payload = data
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def order(self, col, desc=False):
        self._order_col = (col, desc)
        return self

    def single(self):
        self._single = True
        return self

    def _rows(self):
        return self.store.setdefault(self.name, [])

    def _filtered(self):
        rows = self._rows()
        matches = [r for r in rows if all(r.get(k) == v for k, v in self._filters.items())]
        if self._order_col:
            col, desc = self._order_col
            matches = sorted(matches, key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
        return matches

    def execute(self):
        if self._op == "select":
            matches = self._filtered()
            if self._single:
                return SimpleNamespace(data=matches[0] if matches else None)
            return SimpleNamespace(data=matches)
        if self._op == "insert":
            new_row = dict(self._payload)
            new_row.setdefault("id", f"{self.name}-{len(self._rows()) + 1}")
            self._rows().append(new_row)
            return SimpleNamespace(data=[new_row])
        if self._op == "update":
            matches = self._filtered()
            for row in matches:
                row.update(self._payload)
            return SimpleNamespace(data=matches)
        return SimpleNamespace(data=None)


class MockSupabase:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        return MockTable(name, self.store)


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def _base_store():
    return {"series": [], "seasons": [], "scripts": [], "script_members": []}


def test_create_series_creates_series_and_first_season(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))

    resp = _client().post("/api/series", json={"title": "Crime Drama"})

    assert resp.status_code == 201
    body = resp.get_json()
    assert body["series"]["title"] == "Crime Drama"
    assert body["series"]["owner_id"] == DEV_USER_ID
    assert body["season"]["season_number"] == 1
    assert body["season"]["series_id"] == body["series"]["id"]


def test_create_series_requires_title(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))

    resp = _client().post("/api/series", json={})

    assert resp.status_code == 400


def test_list_series_returns_only_callers_own(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["series"] = [
        {"id": "ser1", "owner_id": DEV_USER_ID, "title": "Mine"},
        {"id": "ser2", "owner_id": "someone-else", "title": "Not Mine"},
    ]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))

    resp = _client().get("/api/series")

    assert resp.status_code == 200
    titles = [s["title"] for s in resp.get_json()["series"]]
    assert titles == ["Mine"]


def test_create_season_requires_series_ownership(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["series"] = [{"id": "ser1", "owner_id": "someone-else", "title": "Not Mine"}]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))

    resp = _client().post("/api/series/ser1/seasons", json={"season_number": 2})

    assert resp.status_code == 403
    assert store["seasons"] == []


def test_list_seasons_for_owned_series(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["series"] = [{"id": "ser1", "owner_id": DEV_USER_ID, "title": "Mine"}]
    store["seasons"] = [
        {"id": "sea2", "series_id": "ser1", "season_number": 2, "title": None},
        {"id": "sea1", "series_id": "ser1", "season_number": 1, "title": None},
    ]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))

    resp = _client().get("/api/series/ser1/seasons")

    assert resp.status_code == 200
    numbers = [s["season_number"] for s in resp.get_json()["seasons"]]
    assert numbers == [1, 2]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_series_routes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'routes.series_routes'` (module doesn't exist yet).

- [ ] **Step 3: Write the minimal implementation**

Create `backend/routes/series_routes.py`:

```python
"""
Series / Season / Episode grouping routes (Phase 1 -- grouping and
reporting layer only).

A series groups seasons; a season groups episode scripts. Purely
organizational on top of the existing single-script model -- no changes
to upload, parsing, AI analysis, or entitlement/billing. Access to a
season/episode list is inherited per-episode from the caller's existing
script role (owner or a script_members row) via get_script_role -- there
is no separate series-level permission system for READING episode data.

Series/season STRUCTURE (creating seasons, moving episodes) is gated on
series ownership: only the user who created a series can add seasons to
it or move a script into/out of one of its seasons. This is stricter than
the read path (which any team member with episode access can see) and
mirrors how script structure changes (e.g. deleting a script) are
owner-gated elsewhere in this codebase.
"""
from flask import Blueprint, request, jsonify
from db.supabase_client import get_supabase_admin
from middleware.auth import require_auth, get_user_id
from middleware.authorization import require_script_role, get_script_role, SCRIPT_NOT_FOUND

series_bp = Blueprint('series', __name__)


def _get_series(supabase, series_id):
    result = supabase.table('series').select('*').eq('id', series_id).single().execute()
    return result.data


def _user_owns_series(supabase, series_id, user_id):
    series = _get_series(supabase, series_id)
    return bool(series and series.get('owner_id') == user_id)


@series_bp.route('/api/series', methods=['POST'])
@require_auth
def create_series():
    """
    Create a series, plus its first season.

    Body: {"title": "Show Name", "season_number": 1, "season_title": null}
    season_number/season_title are optional -- default to 1 / None.
    """
    supabase = get_supabase_admin()
    user_id = get_user_id()
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'title is required'}), 400

    season_number = data.get('season_number') or 1
    season_title = data.get('season_title')

    series_result = supabase.table('series').insert({
        'owner_id': user_id, 'title': title,
    }).execute()
    if not series_result.data:
        return jsonify({'error': 'Failed to create series'}), 500
    series = series_result.data[0]

    season_result = supabase.table('seasons').insert({
        'series_id': series['id'], 'season_number': season_number,
        'title': season_title,
    }).execute()
    season = season_result.data[0] if season_result.data else None

    return jsonify({'series': series, 'season': season}), 201


@series_bp.route('/api/series', methods=['GET'])
@require_auth
def list_series():
    """
    List series the caller owns.

    Note: this is intentionally owner-scoped, not "every series I have an
    accessible episode in" -- discovery of someone else's series isn't a
    surface this phase builds. A team member who has episode access via a
    direct link still gets correctly-filtered season/episode/cast views
    (see list_seasons, list_episodes, get_season_cast below); they just
    won't see that series in their own /api/series listing.
    """
    supabase = get_supabase_admin()
    user_id = get_user_id()
    result = supabase.table('series').select('*').eq('owner_id', user_id).execute()
    return jsonify({'series': result.data or []})


@series_bp.route('/api/series/<series_id>/seasons', methods=['POST'])
@require_auth
def create_season(series_id):
    """Add a season to a series. Series-owner only."""
    supabase = get_supabase_admin()
    user_id = get_user_id()

    series = _get_series(supabase, series_id)
    if not series:
        return jsonify({'error': 'Series not found'}), 404
    if series.get('owner_id') != user_id:
        return jsonify({'error': 'Insufficient permissions'}), 403

    data = request.get_json(silent=True) or {}
    season_number = data.get('season_number')
    if not season_number:
        return jsonify({'error': 'season_number is required'}), 400

    result = supabase.table('seasons').insert({
        'series_id': series_id, 'season_number': season_number,
        'title': data.get('title'),
    }).execute()
    if not result.data:
        return jsonify({'error': 'Failed to create season'}), 500

    return jsonify({'season': result.data[0]}), 201


@series_bp.route('/api/series/<series_id>/seasons', methods=['GET'])
@require_auth
def list_seasons(series_id):
    """
    List a series' seasons, ordered by season_number.

    Visible to the series owner, or to anyone with viewer-or-above access
    to at least one script inside any of this series' seasons -- so a team
    member following a shared season link can still see season structure.
    """
    supabase = get_supabase_admin()
    user_id = get_user_id()

    series = _get_series(supabase, series_id)
    if not series:
        return jsonify({'error': 'Series not found'}), 404

    is_owner = series.get('owner_id') == user_id
    seasons_result = supabase.table('seasons').select('*').eq(
        'series_id', series_id
    ).order('season_number').execute()
    seasons = seasons_result.data or []

    if not is_owner:
        visible = False
        for season in seasons:
            scripts_result = supabase.table('scripts').select('id').eq(
                'season_id', season['id']
            ).execute()
            for script in (scripts_result.data or []):
                role = get_script_role(script['id'], user_id)
                if role not in (None, SCRIPT_NOT_FOUND):
                    visible = True
                    break
            if visible:
                break
        if not visible:
            return jsonify({'error': 'Insufficient permissions'}), 403

    return jsonify({'seasons': seasons})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_series_routes.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/routes/series_routes.py backend/tests/test_series_routes.py
git commit -m "feat(series): add series/season create + list routes"
```

---

### Task 3: Episode listing + script reassignment

**Files:**
- Modify: `backend/routes/series_routes.py`
- Test: `backend/tests/test_series_routes.py`

**Interfaces:**
- Consumes: `series_bp` from Task 2, `require_script_role` (`middleware/authorization.py`).
- Produces: `GET /api/seasons/<season_id>/episodes`, `PATCH /api/scripts/<script_id>/season` — both consumed by Task 4 (cast view reuses the same episode-filtering logic, factored into `_visible_episode_scripts`) and by the frontend in Task 7/9.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_series_routes.py`:

```python
def test_list_episodes_filters_to_accessible_scripts(monkeypatch):
    """
    The core access-control guarantee of this feature: a season's episode
    list must never leak a script the caller can't otherwise see, even
    though it's returned by season_id rather than the usual
    /api/scripts/<script_id> path.
    """
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["scripts"] = [
        {"id": "ep1", "user_id": DEV_USER_ID, "season_id": "sea1", "episode_number": 1, "title": "Ep 1"},
        {"id": "ep2", "user_id": "someone-else", "season_id": "sea1", "episode_number": 2, "title": "Ep 2"},
    ]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().get("/api/seasons/sea1/episodes")

    assert resp.status_code == 200
    episodes = resp.get_json()["episodes"]
    assert [e["id"] for e in episodes] == ["ep1"]  # ep2 filtered out, not owner or member


def test_list_episodes_orders_by_episode_number(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["scripts"] = [
        {"id": "ep2", "user_id": DEV_USER_ID, "season_id": "sea1", "episode_number": 2, "title": "Ep 2"},
        {"id": "ep1", "user_id": DEV_USER_ID, "season_id": "sea1", "episode_number": 1, "title": "Ep 1"},
    ]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().get("/api/seasons/sea1/episodes")

    numbers = [e["episode_number"] for e in resp.get_json()["episodes"]]
    assert numbers == [1, 2]


def test_update_script_season_requires_series_ownership(monkeypatch):
    """A member on the script cannot move it into a season on a series they
    don't own -- prevents sneaking a script into someone else's series."""
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["scripts"] = [{"id": "s1", "user_id": DEV_USER_ID, "season_id": None, "episode_number": None}]
    store["series"] = [{"id": "ser1", "owner_id": "someone-else", "title": "Not Mine"}]
    store["seasons"] = [{"id": "sea1", "series_id": "ser1", "season_number": 1}]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().patch("/api/scripts/s1/season", json={"season_id": "sea1", "episode_number": 3})

    assert resp.status_code == 403
    assert store["scripts"][0]["season_id"] is None


def test_update_script_season_assigns_when_owned(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["scripts"] = [{"id": "s1", "user_id": DEV_USER_ID, "season_id": None, "episode_number": None}]
    store["series"] = [{"id": "ser1", "owner_id": DEV_USER_ID, "title": "Mine"}]
    store["seasons"] = [{"id": "sea1", "series_id": "ser1", "season_number": 1}]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().patch("/api/scripts/s1/season", json={"season_id": "sea1", "episode_number": 3})

    assert resp.status_code == 200
    assert store["scripts"][0]["season_id"] == "sea1"
    assert store["scripts"][0]["episode_number"] == 3


def test_update_script_season_clears_assignment(monkeypatch):
    """season_id: null removes a script from its season -- the reassignment
    surface's 'None' state."""
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["scripts"] = [{"id": "s1", "user_id": DEV_USER_ID, "season_id": "sea1", "episode_number": 3}]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().patch("/api/scripts/s1/season", json={"season_id": None})

    assert resp.status_code == 200
    assert store["scripts"][0]["season_id"] is None
    assert store["scripts"][0]["episode_number"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_series_routes.py -v -k "episodes or update_script_season"`
Expected: FAIL — `404 NOT FOUND` (routes don't exist yet), assertion errors.

- [ ] **Step 3: Write the minimal implementation**

Append to `backend/routes/series_routes.py`:

```python
def _visible_episode_scripts(supabase, season_id, user_id):
    """Scripts in this season, filtered to ones the caller can access,
    ordered by episode_number. Shared by list_episodes and (Task 4's)
    get_season_cast."""
    scripts_result = supabase.table('scripts').select('*').eq(
        'season_id', season_id
    ).order('episode_number').execute()

    visible = []
    for script in (scripts_result.data or []):
        role = get_script_role(script['id'], user_id)
        if role not in (None, SCRIPT_NOT_FOUND):
            visible.append(script)
    return visible


@series_bp.route('/api/seasons/<season_id>/episodes', methods=['GET'])
@require_auth
def list_episodes(season_id):
    """Episodes in a season, filtered to the caller's accessible scripts."""
    supabase = get_supabase_admin()
    user_id = get_user_id()
    episodes = _visible_episode_scripts(supabase, season_id, user_id)
    return jsonify({'episodes': episodes})


@series_bp.route('/api/scripts/<script_id>/season', methods=['PATCH'])
@require_auth
@require_script_role('member')
def update_script_season(script_id):
    """
    Assign, reassign, or clear a script's season/episode-number.

    Body: {"season_id": "<uuid>" | null, "episode_number": 3}
    season_id: null clears the assignment (episode_number is cleared too,
    regardless of what's in the body, since an episode number without a
    season is meaningless).

    Requires @require_script_role('member') on the script (the caller must
    already have at least edit access to it) AND ownership of the target
    season's series -- you can't move your own script into someone else's
    series just because you can edit the script.
    """
    supabase = get_supabase_admin()
    user_id = get_user_id()
    data = request.get_json(silent=True) or {}

    season_id = data.get('season_id')
    if season_id is None:
        supabase.table('scripts').update({
            'season_id': None, 'episode_number': None,
        }).eq('id', script_id).execute()
        return jsonify({'success': True, 'season_id': None, 'episode_number': None})

    season_result = supabase.table('seasons').select('*').eq('id', season_id).single().execute()
    season = season_result.data
    if not season:
        return jsonify({'error': 'Season not found'}), 404

    if not _user_owns_series(supabase, season['series_id'], user_id):
        return jsonify({'error': 'Insufficient permissions'}), 403

    episode_number = data.get('episode_number')
    supabase.table('scripts').update({
        'season_id': season_id, 'episode_number': episode_number,
    }).eq('id', script_id).execute()

    return jsonify({'success': True, 'season_id': season_id, 'episode_number': episode_number})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_series_routes.py -v`
Expected: PASS (9 tests total).

- [ ] **Step 5: Commit**

```bash
git add backend/routes/series_routes.py backend/tests/test_series_routes.py
git commit -m "feat(series): add episode listing and script season reassignment"
```

---

### Task 4: Combined cast view

**Files:**
- Modify: `backend/routes/series_routes.py`
- Test: `backend/tests/test_series_routes.py`

**Interfaces:**
- Consumes: `_visible_episode_scripts` (Task 3).
- Produces: `GET /api/seasons/<season_id>/cast` — consumed by the frontend `SeasonPage.jsx` (Task 9).

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_series_routes.py`:

```python
def test_combined_cast_groups_exact_name_case_insensitive(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["scripts"] = [
        {"id": "ep1", "user_id": DEV_USER_ID, "season_id": "sea1", "episode_number": 1, "title": "Ep 1"},
        {"id": "ep2", "user_id": DEV_USER_ID, "season_id": "sea1", "episode_number": 2, "title": "Ep 2"},
    ]
    store["scenes"] = [
        {"id": "sc1", "script_id": "ep1", "characters": ["JOHN", "MARY"]},
        {"id": "sc2", "script_id": "ep2", "characters": ["John", "SAM"]},  # case-only variant of JOHN
    ]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().get("/api/seasons/sea1/cast")

    assert resp.status_code == 200
    cast = {row["name"]: row["episodes"] for row in resp.get_json()["cast"]}
    assert set(cast.keys()) == {"JOHN", "MARY", "SAM"}
    assert sorted(cast["JOHN"]) == ["Ep 1", "Ep 2"]  # grouped across both episodes
    assert cast["MARY"] == ["Ep 1"]
    assert cast["SAM"] == ["Ep 2"]


def test_combined_cast_only_includes_accessible_episodes(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["scripts"] = [
        {"id": "ep1", "user_id": DEV_USER_ID, "season_id": "sea1", "episode_number": 1, "title": "Ep 1"},
        {"id": "ep2", "user_id": "someone-else", "season_id": "sea1", "episode_number": 2, "title": "Ep 2"},
    ]
    store["scenes"] = [
        {"id": "sc1", "script_id": "ep1", "characters": ["JOHN"]},
        {"id": "sc2", "script_id": "ep2", "characters": ["SECRET"]},
    ]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().get("/api/seasons/sea1/cast")

    names = {row["name"] for row in resp.get_json()["cast"]}
    assert names == {"JOHN"}  # SECRET (from the inaccessible ep2) never leaks
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_series_routes.py -v -k combined_cast`
Expected: FAIL — 404 NOT FOUND.

- [ ] **Step 3: Write the minimal implementation**

Append to `backend/routes/series_routes.py`:

```python
@series_bp.route('/api/seasons/<season_id>/cast', methods=['GET'])
@require_auth
def get_season_cast(season_id):
    """
    Combined cast view: one row per distinct character name across the
    season's visible episodes, grouped by exact case-insensitive match
    (the same .strip().upper() normalization merge_characters already
    uses in supabase_routes.py, for consistency). This is explicitly NOT
    identity resolution -- "JOHN" and "Jon" are two different rows. That
    gap is Phase 2 (cross-episode entity continuity), out of scope here.
    """
    supabase = get_supabase_admin()
    user_id = get_user_id()

    episodes = _visible_episode_scripts(supabase, season_id, user_id)
    episode_titles_by_id = {ep['id']: ep.get('title', 'Untitled') for ep in episodes}

    groups = {}  # normalized name -> set of episode titles
    for script_id, title in episode_titles_by_id.items():
        scenes_result = supabase.table('scenes').select('characters').eq(
            'script_id', script_id
        ).execute()
        for scene in (scenes_result.data or []):
            for raw_name in (scene.get('characters') or []):
                name = (raw_name or '').strip().upper()
                if not name:
                    continue
                groups.setdefault(name, set()).add(title)

    cast = [
        {'name': name, 'episodes': sorted(titles)}
        for name, titles in sorted(groups.items())
    ]
    return jsonify({'cast': cast})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_series_routes.py -v`
Expected: PASS (11 tests total).

- [ ] **Step 5: Commit**

```bash
git add backend/routes/series_routes.py backend/tests/test_series_routes.py
git commit -m "feat(series): add combined cast view with exact-name grouping"
```

---

### Task 5: Register the blueprint + extend route-enforcement coverage

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/tests/test_route_enforcement.py`

**Interfaces:**
- Consumes: `series_bp` (Tasks 2-4).

- [ ] **Step 1: Register the blueprint**

In `backend/app.py`, add the import alongside the other route imports:

```python
from routes.series_routes import series_bp
```

And register it alongside the other blueprints (after `payfast_bp`):

```python
app.register_blueprint(series_bp)  # Series/season grouping routes at /api/series/*, /api/seasons/*, /api/scripts/:id/season
```

- [ ] **Step 2: Run the full backend suite to confirm nothing else broke**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/ -q`
Expected: all passing (previous count + 11 new tests), no import errors, no route collisions.

- [ ] **Step 3: Extend `test_route_enforcement.py` for the new single-script-scoped route**

Open `backend/tests/test_route_enforcement.py`. Add `"series."` to `BLUEPRINT_PREFIXES` so the new blueprint's script-scoped route gets the same regression guarantee as `supabase.`/`reports.`/`schedule.`/`invite.`:

```python
BLUEPRINT_PREFIXES = ("supabase.", "reports.", "schedule.", "invite.", "series.")
```

`update_script_season` already carries `@require_script_role('member')`, so it will pass the existing assertion loop unmodified as long as its URL argument name (`script_id`) is already in `SCOPED_ARG_NAMES` — confirm it is (it already is, from `supabase.`'s routes). The three non-script-scoped `series.` routes (`create_series`, `list_series`, `create_season`, `list_seasons`, `list_episodes`, `get_season_cast` — none take a `script_id` URL argument) will simply be skipped by the existing scoping filter, same as `supabase.get_scripts`/`supabase.upload_script` are today — no whitelist entry needed for them since the filter already only inspects routes whose URL rule contains one of `SCOPED_ARG_NAMES`.

- [ ] **Step 4: Run the route-enforcement test to verify it still passes with the new blueprint included**

Run: `cd backend && source venv/bin/activate && python -m pytest tests/test_route_enforcement.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app.py backend/tests/test_route_enforcement.py
git commit -m "feat(series): register series blueprint, extend route-enforcement coverage"
```

---

### Task 6: Frontend API service functions

**Files:**
- Modify: `frontend/src/services/apiService.js`

**Interfaces:**
- Consumes: the `api` axios instance already defined at the top of `apiService.js`.
- Produces: `createSeries`, `listSeries`, `createSeason`, `listSeasons`, `listEpisodes`, `getSeasonCast`, `updateScriptSeason` — consumed by `SeriesPicker.jsx` (Task 7), `ScriptUpload.jsx` (Task 7), `SeriesListPage.jsx`/`SeasonPage.jsx` (Task 9).

- [ ] **Step 1: Add the functions**

Append to `frontend/src/services/apiService.js` (matching the existing `getPdfUrl`-style try/catch/rethrow pattern):

```javascript
/**
 * Create a series (plus its first season).
 * @param {string} title
 * @param {{season_number?: number, season_title?: string}} [options]
 * @returns {Promise<{series: object, season: object}>}
 */
export const createSeries = async (title, options = {}) => {
    try {
        const response = await api.post('/api/series', { title, ...options });
        return response.data;
    } catch (error) {
        console.error('Error creating series:', error);
        throw error;
    }
};

/**
 * List series the current user owns.
 * @returns {Promise<{series: object[]}>}
 */
export const listSeries = async () => {
    try {
        const response = await api.get('/api/series');
        return response.data;
    } catch (error) {
        console.error('Error listing series:', error);
        throw error;
    }
};

/**
 * Add a season to a series.
 * @param {string} seriesId
 * @param {number} seasonNumber
 * @param {string} [title]
 * @returns {Promise<{season: object}>}
 */
export const createSeason = async (seriesId, seasonNumber, title) => {
    try {
        const response = await api.post(`/api/series/${seriesId}/seasons`, {
            season_number: seasonNumber, title,
        });
        return response.data;
    } catch (error) {
        console.error('Error creating season:', error);
        throw error;
    }
};

/**
 * List a series' seasons.
 * @param {string} seriesId
 * @returns {Promise<{seasons: object[]}>}
 */
export const listSeasons = async (seriesId) => {
    try {
        const response = await api.get(`/api/series/${seriesId}/seasons`);
        return response.data;
    } catch (error) {
        console.error('Error listing seasons:', error);
        throw error;
    }
};

/**
 * List a season's episodes (filtered to the caller's accessible scripts).
 * @param {string} seasonId
 * @returns {Promise<{episodes: object[]}>}
 */
export const listEpisodes = async (seasonId) => {
    try {
        const response = await api.get(`/api/seasons/${seasonId}/episodes`);
        return response.data;
    } catch (error) {
        console.error('Error listing episodes:', error);
        throw error;
    }
};

/**
 * Get the combined (exact-name-grouped) cast view for a season.
 * @param {string} seasonId
 * @returns {Promise<{cast: {name: string, episodes: string[]}[]}>}
 */
export const getSeasonCast = async (seasonId) => {
    try {
        const response = await api.get(`/api/seasons/${seasonId}/cast`);
        return response.data;
    } catch (error) {
        console.error('Error getting season cast:', error);
        throw error;
    }
};

/**
 * Assign, reassign, or clear a script's season/episode-number.
 * @param {string} scriptId
 * @param {string|null} seasonId - null clears the assignment
 * @param {number} [episodeNumber]
 * @returns {Promise<{success: boolean, season_id: string|null, episode_number: number|null}>}
 */
export const updateScriptSeason = async (scriptId, seasonId, episodeNumber) => {
    try {
        const response = await api.patch(`/api/scripts/${scriptId}/season`, {
            season_id: seasonId, episode_number: episodeNumber,
        });
        return response.data;
    } catch (error) {
        console.error('Error updating script season:', error);
        throw error;
    }
};
```

- [ ] **Step 2: Verify the build still passes**

Run: `cd frontend && npm run build`
Expected: builds successfully, no new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/apiService.js
git commit -m "feat(series): add frontend API service functions for series/season endpoints"
```

---

### Task 7: `SeriesPicker` component + upload-flow wiring

**Files:**
- Create: `frontend/src/components/series/SeriesPicker.jsx`
- Modify: `frontend/src/components/script/ScriptUpload.jsx`

**Interfaces:**
- Consumes: `listSeries`, `createSeries`, `listSeasons`, `createSeason`, `updateScriptSeason` (Task 6).
- Produces: `SeriesPicker` React component — `<SeriesPicker onAssign={(seasonId, episodeNumber) => void}>` — also reused by Task 9's reassignment surface (a script's own settings can render the same component).

- [ ] **Step 1: Create the picker component**

Create `frontend/src/components/series/SeriesPicker.jsx`:

```jsx
import { useState, useEffect } from 'react';
import { listSeries, createSeries, listSeasons, createSeason } from '../../services/apiService';

/**
 * SeriesPicker - three-state picker for assigning a script to a series/season.
 *
 * States: 'none' (default, no assignment), 'existing' (pick a series +
 * season), 'new' (create a series, season defaults to 1).
 *
 * Calls onAssign(seasonId, episodeNumber) when the user has made a
 * complete selection; onAssign(null, null) if they pick 'none'. The
 * caller (ScriptUpload or a reassignment surface) decides what to do with
 * that -- fire it immediately, or wait for a "confirm" action.
 */
export default function SeriesPicker({ onAssign }) {
    const [mode, setMode] = useState('none');
    const [seriesList, setSeriesList] = useState([]);
    const [selectedSeriesId, setSelectedSeriesId] = useState('');
    const [seasons, setSeasons] = useState([]);
    const [selectedSeasonId, setSelectedSeasonId] = useState('');
    const [episodeNumber, setEpisodeNumber] = useState('');
    const [newSeriesTitle, setNewSeriesTitle] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (mode !== 'existing') return;
        listSeries()
            .then((data) => setSeriesList(data.series || []))
            .catch((err) => setError(err.message || 'Failed to load series'));
    }, [mode]);

    useEffect(() => {
        if (!selectedSeriesId) {
            setSeasons([]);
            return;
        }
        listSeasons(selectedSeriesId)
            .then((data) => setSeasons(data.seasons || []))
            .catch((err) => setError(err.message || 'Failed to load seasons'));
    }, [selectedSeriesId]);

    useEffect(() => {
        if (mode === 'none') {
            onAssign(null, null);
        }
    }, [mode]); // eslint-disable-line react-hooks/exhaustive-deps

    const handleExistingConfirm = () => {
        if (!selectedSeasonId || !episodeNumber) {
            setError('Pick a season and enter an episode number');
            return;
        }
        onAssign(selectedSeasonId, Number(episodeNumber));
    };

    const handleNewConfirm = async () => {
        if (!newSeriesTitle.trim() || !episodeNumber) {
            setError('Enter a series title and episode number');
            return;
        }
        setLoading(true);
        setError(null);
        try {
            const { season } = await createSeries(newSeriesTitle.trim());
            onAssign(season.id, Number(episodeNumber));
        } catch (err) {
            setError(err.message || 'Failed to create series');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="series-picker">
            <div className="series-picker-modes">
                <button type="button" className={mode === 'none' ? 'active' : ''} onClick={() => setMode('none')}>
                    Not part of a series
                </button>
                <button type="button" className={mode === 'existing' ? 'active' : ''} onClick={() => setMode('existing')}>
                    Add to existing series
                </button>
                <button type="button" className={mode === 'new' ? 'active' : ''} onClick={() => setMode('new')}>
                    Create new series
                </button>
            </div>

            {error && <p className="series-picker-error">{error}</p>}

            {mode === 'existing' && (
                <div className="series-picker-existing">
                    <select value={selectedSeriesId} onChange={(e) => setSelectedSeriesId(e.target.value)}>
                        <option value="">Select a series...</option>
                        {seriesList.map((s) => (
                            <option key={s.id} value={s.id}>{s.title}</option>
                        ))}
                    </select>
                    <select
                        value={selectedSeasonId}
                        onChange={(e) => setSelectedSeasonId(e.target.value)}
                        disabled={!selectedSeriesId}
                    >
                        <option value="">Select a season...</option>
                        {seasons.map((s) => (
                            <option key={s.id} value={s.id}>{s.title || `Season ${s.season_number}`}</option>
                        ))}
                    </select>
                    <input
                        type="number"
                        min="1"
                        placeholder="Episode #"
                        value={episodeNumber}
                        onChange={(e) => setEpisodeNumber(e.target.value)}
                    />
                    <button type="button" onClick={handleExistingConfirm}>Assign</button>
                </div>
            )}

            {mode === 'new' && (
                <div className="series-picker-new">
                    <input
                        type="text"
                        placeholder="Series title"
                        value={newSeriesTitle}
                        onChange={(e) => setNewSeriesTitle(e.target.value)}
                    />
                    <input
                        type="number"
                        min="1"
                        placeholder="Episode #"
                        value={episodeNumber}
                        onChange={(e) => setEpisodeNumber(e.target.value)}
                    />
                    <button type="button" onClick={handleNewConfirm} disabled={loading}>
                        {loading ? 'Creating...' : 'Create & Assign'}
                    </button>
                </div>
            )}
        </div>
    );
}
```

- [ ] **Step 2: Wire it into `ScriptUpload.jsx`**

In `frontend/src/components/script/ScriptUpload.jsx`:

1. Add the imports near the other imports:

```javascript
import SeriesPicker from '../series/SeriesPicker';
import { updateScriptSeason } from '../../services/apiService';
```

2. Add state to hold the pending assignment, near the component's other `useState` calls:

```javascript
const [pendingSeasonAssignment, setPendingSeasonAssignment] = useState(null); // {seasonId, episodeNumber} | null
```

3. Render `<SeriesPicker onAssign={(seasonId, episodeNumber) => setPendingSeasonAssignment(seasonId ? { seasonId, episodeNumber } : null)} />` somewhere sensible in the upload form's JSX (near the file picker, before the submit button).

4. Immediately after a successful upload — at the existing site around line 130 (`if (uploadResult?.script_id) { navigate(...) }`), fire the reassignment call first if one is pending:

```javascript
if (uploadResult?.script_id) {
    if (pendingSeasonAssignment) {
        try {
            await updateScriptSeason(
                uploadResult.script_id,
                pendingSeasonAssignment.seasonId,
                pendingSeasonAssignment.episodeNumber
            );
        } catch (err) {
            console.error('Failed to assign script to season:', err);
            // Non-fatal: the script uploaded successfully either way. The
            // user can still assign it later via the reassignment surface
            // (Task 9) if this call fails.
        }
    }
    navigate(`/scenes/${uploadResult.script_id}`);
}
```

- [ ] **Step 3: Verify the build still passes**

Run: `cd frontend && npm run build`
Expected: builds successfully.

- [ ] **Step 4: Manual verification**

Start the dev server (`npm run dev` in `frontend/`, backend running locally too) and walk through all three `SeriesPicker` modes during a real upload: "Not part of a series" (upload proceeds unchanged), "Create new series" (creates a series + season 1, assigns the uploaded script), "Add to existing series" (after at least one series exists, pick it, pick a season, assign). Confirm no console errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/series/SeriesPicker.jsx frontend/src/components/script/ScriptUpload.jsx
git commit -m "feat(series): add SeriesPicker component, wire into upload flow"
```

---

### Task 8: Series list page and season detail page

**Files:**
- Create: `frontend/src/pages/SeriesListPage.jsx`
- Create: `frontend/src/pages/SeasonPage.jsx`
- Modify: `frontend/src/App.jsx`

**Interfaces:**
- Consumes: `listSeries`, `listSeasons`, `listEpisodes`, `getSeasonCast` (Task 6), `PageHeader`/`Spinner` (`frontend/src/components/layout/PageHeader.jsx`, `frontend/src/components/ui`).

- [ ] **Step 1: Create the series list page**

Create `frontend/src/pages/SeriesListPage.jsx`:

```jsx
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listSeries } from '../services/apiService';
import PageHeader from '../components/layout/PageHeader';
import { Spinner } from '../components/ui';

export default function SeriesListPage() {
    const [series, setSeries] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        listSeries()
            .then((data) => setSeries(data.series || []))
            .catch((err) => setError(err.message || 'Failed to load series'))
            .finally(() => setLoading(false));
    }, []);

    return (
        <div className="series-list-page">
            <PageHeader title="Series" subtitle="Group related episode scripts together" />
            {loading && <Spinner size={32} />}
            {error && <p className="series-list-error">{error}</p>}
            {!loading && !error && series.length === 0 && (
                <p>No series yet. Create one from the upload page.</p>
            )}
            <ul className="series-list">
                {series.map((s) => (
                    <li key={s.id}>
                        <Link to={`/series/${s.id}`}>{s.title}</Link>
                    </li>
                ))}
            </ul>
        </div>
    );
}
```

- [ ] **Step 2: Create the season detail page**

Create `frontend/src/pages/SeasonPage.jsx`. Note this reads `seriesId` from the URL but the current API surface is season-scoped (`listSeasons(seriesId)` returns all seasons for the series; the page finds the matching one by `seasonId` client-side, since there's no single-season GET endpoint in this phase):

```jsx
import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { listSeasons, listEpisodes, getSeasonCast } from '../services/apiService';
import PageHeader from '../components/layout/PageHeader';
import { Spinner } from '../components/ui';

export default function SeasonPage() {
    const { seriesId, seasonId } = useParams();
    const [season, setSeason] = useState(null);
    const [episodes, setEpisodes] = useState([]);
    const [cast, setCast] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        Promise.all([
            listSeasons(seriesId),
            listEpisodes(seasonId),
            getSeasonCast(seasonId),
        ])
            .then(([seasonsData, episodesData, castData]) => {
                const match = (seasonsData.seasons || []).find((s) => s.id === seasonId);
                setSeason(match || null);
                setEpisodes(episodesData.episodes || []);
                setCast(castData.cast || []);
            })
            .catch((err) => setError(err.message || 'Failed to load season'))
            .finally(() => setLoading(false));
    }, [seriesId, seasonId]);

    if (loading) return <Spinner size={32} />;
    if (error) return <p className="season-page-error">{error}</p>;

    return (
        <div className="season-page">
            <PageHeader
                title={season?.title || `Season ${season?.season_number ?? ''}`}
                subtitle={`${episodes.length} episode${episodes.length === 1 ? '' : 's'}`}
            />

            <section className="season-episodes">
                <h2>Episodes</h2>
                <ol>
                    {episodes.map((ep) => (
                        <li key={ep.id}>
                            <Link to={`/scenes/${ep.id}`}>
                                Episode {ep.episode_number}: {ep.title}
                            </Link>
                        </li>
                    ))}
                </ol>
            </section>

            <section className="season-cast">
                <h2>Combined Cast</h2>
                <table>
                    <thead>
                        <tr><th>Character</th><th>Appears In</th></tr>
                    </thead>
                    <tbody>
                        {cast.map((row) => (
                            <tr key={row.name}>
                                <td>{row.name}</td>
                                <td>{row.episodes.join(', ')}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </section>
        </div>
    );
}
```

- [ ] **Step 3: Add the routes**

In `frontend/src/App.jsx`:

1. Add the imports near the other page imports:

```javascript
import SeriesListPage from './pages/SeriesListPage';
import SeasonPage from './pages/SeasonPage';
```

2. Add the routes inside the existing protected `<Route path="/" ...>` block, alongside `billing`/`profile`:

```javascript
<Route path="series" element={<SeriesListPage />} />
<Route path="series/:seriesId/seasons/:seasonId" element={<SeasonPage />} />
```

- [ ] **Step 4: Verify the build still passes**

Run: `cd frontend && npm run build`
Expected: builds successfully.

- [ ] **Step 5: Manual verification**

With the dev server running and at least one series/season/episode created via Task 7's upload flow, navigate to `/series`, confirm the series list renders and links through to `/series/:seriesId/seasons/:seasonId`, confirm the season page shows the episode list (correct order) and the combined cast table (character names grouped across episodes as expected).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/SeriesListPage.jsx frontend/src/pages/SeasonPage.jsx frontend/src/App.jsx
git commit -m "feat(series): add series list and season detail pages with combined cast view"
```

---

## Self-Review Notes

- **Spec coverage:** §3 (data model) → Task 1. §3.2 (access control) → Tasks 2-4's owner/episode-role checks, verified by the dedicated access-filtering tests in Tasks 3-4 (the spec's own §7 flagged this as the highest-risk area). §3.3 (no billing impact) → no task touches `entitlement_service.py` or any PayFast code; confirmed by Global Constraints. §4 (upload flow) → Task 7. §5 (series/season page + combined cast, exact-name grouping) → Tasks 2-4 (backend) and Task 8 (frontend). §6 (out of scope) → nothing in this plan touches Phase 2, season-wide scheduling, cross-episode reports beyond cast, or discounted billing. §7 (testing plan) → Task 5 explicitly extends `test_route_enforcement.py`; Tasks 2-4 include the CRUD/access/grouping tests; Task 7/8 include frontend build + manual verification steps.
- **Placeholder scan:** no TBD/TODO; every code step contains complete, runnable code.
- **Type consistency:** `season_id`/`episode_number` field names are identical across the migration (Task 1), all backend routes (Tasks 2-4), the API service functions (Task 6), and the frontend components (Tasks 7-8). `get_script_role`'s three-value contract (`None`/`SCRIPT_NOT_FOUND`/a role string) is handled identically in every place it's called (`_visible_episode_scripts`, `list_seasons`).

---

**Plan complete and saved to `docs/superpowers/plans/2026-07-22-series-multi-episode-phase1.md`.**
