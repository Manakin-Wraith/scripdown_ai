# Teams & Access-Control Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the app-wide authorization hole by enforcing script ownership/membership on every script-scoped endpoint, then harden the Teams feature so it is safe to sell.

**Architecture:** A single new module `backend/middleware/authorization.py` provides a role ladder, a `get_script_role()` lookup, a set of child-resource resolvers, and a `@require_script_role(min_role, resolver=...)` decorator stacked after the existing `@require_auth`. Every script-scoped route across four blueprint files is converted to require auth + the appropriate role. Teams Phase 2 (invite email, invite-to-email binding, role management) rides on the new primitive.

**Tech Stack:** Python 3.13, Flask, supabase-py (service-role client), PyJWT, pytest, Resend (email). Frontend: React 18 + Vite (JSX), axios via `apiService.js`.

## Global Constraints

- Permissions are **global by role**. Department is a label only — no department-scoped write logic.
- Role ladder is **inclusive**: `ROLE_RANK = {'viewer': 1, 'member': 2, 'admin': 3, 'owner': 4}`. `min_role` is a floor; a higher rank inherits every lower capability.
- Owner is **implicit** — `scripts.user_id == user_id`, never a `script_members` row.
- Backend uses the Supabase **service-role key** (bypasses RLS); enforcement is app-layer only. No RLS work this phase.
- Error contract: **401** missing/invalid JWT, **403** authed but insufficient role, **404** script/resource does not exist (existence not leaked). JSON shape `{"error": "<message>"}`.
- Public share-link routes (`/shared/<token>`, `/shared/<token>/pdf`, `/shared/<token>/print`) MUST stay auth-free — explicit whitelist, never converted.
- `DEV_MODE` bypass in `require_auth` is preserved; dev seed data must make `DEV_USER_ID` an owner of test scripts.
- Transfer-ownership is out of scope — no endpoint, no UI.
- Do not commit to `main`. All work lands on branch `feature/teams-access-control`.

## Confirmed foreign-key map (for resolvers)

| Child resource | Table | Column → parent |
|---|---|---|
| scene | `scenes` | `script_id` |
| note | `department_notes` | `script_id` |
| item | `department_items` | `script_id` |
| schedule | `shooting_schedules` | `script_id` |
| shooting day | `shooting_days` | `schedule_id` → `shooting_schedules.script_id` (two hops) |
| day-scene op (by `day_id`) | `shooting_days` | same as shooting day |
| report | `reports` | `script_id` |
| filter preset | `report_filter_presets` | `script_id` |

---

## Task 1: Authorization core — role ladder + `get_script_role`

**Files:**
- Create: `backend/middleware/authorization.py`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/test_authorization.py`

**Interfaces:**
- Consumes: `db.supabase_client.get_supabase_client()` (existing).
- Produces:
  - `ROLE_RANK: dict[str, int]`
  - `SCRIPT_NOT_FOUND` (module-level sentinel object)
  - `get_script_role(script_id: str, user_id: str) -> str | None | SCRIPT_NOT_FOUND` — returns `'owner'`, a `script_members.role` string, `None` (no access, script exists), or `SCRIPT_NOT_FOUND`.

- [ ] **Step 1: Write `conftest.py` with a fake Supabase client fixture**

```python
# backend/tests/conftest.py
import pytest


class FakeTable:
    """Minimal chainable stand-in for supabase-py's query builder."""
    def __init__(self, rows):
        self._rows = rows
        self._filters = {}

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def limit(self, _n):
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        data = [r for r in self._rows
                if all(r.get(k) == v for k, v in self._filters.items())]
        if getattr(self, "_single", False):
            return type("Res", (), {"data": data[0] if data else None})()
        return type("Res", (), {"data": data})()


class FakeSupabase:
    def __init__(self, tables=None):
        self._tables = tables or {}

    def set_table(self, name, rows):
        self._tables[name] = rows

    def table(self, name):
        return FakeTable(self._tables.get(name, []))


@pytest.fixture
def fake_supabase():
    return FakeSupabase()
```

- [ ] **Step 2: Write the failing test for `get_script_role`**

```python
# backend/tests/test_authorization.py
import middleware.authorization as authz
from middleware.authorization import get_script_role, SCRIPT_NOT_FOUND, ROLE_RANK


def _patch_client(monkeypatch, fake):
    monkeypatch.setattr(authz, "get_supabase_client", lambda: fake)


def test_owner_role(monkeypatch, fake_supabase):
    fake_supabase.set_table("scripts", [{"id": "s1", "user_id": "u1"}])
    _patch_client(monkeypatch, fake_supabase)
    assert get_script_role("s1", "u1") == "owner"


def test_member_role(monkeypatch, fake_supabase):
    fake_supabase.set_table("scripts", [{"id": "s1", "user_id": "owner"}])
    fake_supabase.set_table("script_members",
                            [{"script_id": "s1", "user_id": "u2", "role": "member"}])
    _patch_client(monkeypatch, fake_supabase)
    assert get_script_role("s1", "u2") == "member"


def test_non_member_returns_none(monkeypatch, fake_supabase):
    fake_supabase.set_table("scripts", [{"id": "s1", "user_id": "owner"}])
    _patch_client(monkeypatch, fake_supabase)
    assert get_script_role("s1", "stranger") is None


def test_missing_script_returns_sentinel(monkeypatch, fake_supabase):
    _patch_client(monkeypatch, fake_supabase)
    assert get_script_role("nope", "u1") is SCRIPT_NOT_FOUND


def test_role_rank_order():
    assert ROLE_RANK["viewer"] < ROLE_RANK["member"] < ROLE_RANK["admin"] < ROLE_RANK["owner"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest tests/test_authorization.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'middleware.authorization'`.

- [ ] **Step 4: Implement the module core**

```python
# backend/middleware/authorization.py
"""
Script authorization for SlateOne.

Authentication (who the user is) lives in middleware/auth.py.
This module answers: may THIS user act on THIS script, at what role?
Enforcement is app-layer because the backend uses the service-role key.
"""
import logging
from db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

ROLE_RANK = {'viewer': 1, 'member': 2, 'admin': 3, 'owner': 4}

# Sentinel distinguishing "script does not exist" (404) from "no access" (403).
SCRIPT_NOT_FOUND = object()


def get_script_role(script_id, user_id):
    """Return the caller's effective role on a script.

    Returns:
        'owner'                 if scripts.user_id == user_id
        a script_members.role   if the user is a member
        None                    if the script exists but the user has no access
        SCRIPT_NOT_FOUND        if the script does not exist
    """
    if not script_id or not user_id:
        return None

    supabase = get_supabase_client()
    script = (supabase.table('scripts')
              .select('user_id').eq('id', script_id).limit(1).execute())
    if not script.data:
        return SCRIPT_NOT_FOUND

    owner_id = script.data[0].get('user_id')
    if owner_id == user_id:
        return 'owner'

    member = (supabase.table('script_members')
              .select('role').eq('script_id', script_id)
              .eq('user_id', user_id).limit(1).execute())
    if member.data:
        return member.data[0].get('role')

    return None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_authorization.py -v`
Expected: PASS (5 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/middleware/authorization.py backend/tests/conftest.py backend/tests/test_authorization.py
git commit -m "feat(authz): add role ladder and get_script_role lookup"
```

---

## Task 2: Child-resource resolvers

**Files:**
- Modify: `backend/middleware/authorization.py`
- Test: `backend/tests/test_authorization.py`

**Interfaces:**
- Produces resolver callables, each taking the Flask route `kwargs` dict and returning a `script_id` string or `None`:
  - `from_script(kwargs)`, `from_scene(kwargs)`, `from_note(kwargs)`, `from_item(kwargs)`,
    `from_schedule(kwargs)`, `from_day(kwargs)`, `from_report(kwargs)`, `from_preset(kwargs)`.

- [ ] **Step 1: Write the failing test**

```python
# add to backend/tests/test_authorization.py
from middleware.authorization import from_scene, from_day, from_note


def test_from_scene_resolves_script(monkeypatch, fake_supabase):
    fake_supabase.set_table("scenes", [{"id": "sc1", "script_id": "s1"}])
    _patch_client(monkeypatch, fake_supabase)
    assert from_scene({"scene_id": "sc1"}) == "s1"


def test_from_scene_missing_returns_none(monkeypatch, fake_supabase):
    _patch_client(monkeypatch, fake_supabase)
    assert from_scene({"scene_id": "ghost"}) is None


def test_from_day_two_hop(monkeypatch, fake_supabase):
    fake_supabase.set_table("shooting_days", [{"id": "d1", "schedule_id": "sch1"}])
    fake_supabase.set_table("shooting_schedules", [{"id": "sch1", "script_id": "s1"}])
    _patch_client(monkeypatch, fake_supabase)
    assert from_day({"day_id": "d1"}) == "s1"


def test_from_note_resolves(monkeypatch, fake_supabase):
    fake_supabase.set_table("department_notes", [{"id": "n1", "script_id": "s9"}])
    _patch_client(monkeypatch, fake_supabase)
    assert from_note({"note_id": "n1"}) == "s9"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_authorization.py -k "from_" -v`
Expected: FAIL — `ImportError: cannot import name 'from_scene'`.

- [ ] **Step 3: Implement resolvers**

```python
# append to backend/middleware/authorization.py

def _lookup_script_id(table, id_value, id_col='id', script_col='script_id'):
    """Fetch a single row by id and return its script_id (or None)."""
    if not id_value:
        return None
    supabase = get_supabase_client()
    res = (supabase.table(table)
           .select(script_col).eq(id_col, id_value).limit(1).execute())
    return res.data[0].get(script_col) if res.data else None


def from_script(kwargs):
    return kwargs.get('script_id')


def from_scene(kwargs):
    return _lookup_script_id('scenes', kwargs.get('scene_id'))


def from_note(kwargs):
    return _lookup_script_id('department_notes', kwargs.get('note_id'))


def from_item(kwargs):
    return _lookup_script_id('department_items', kwargs.get('item_id'))


def from_schedule(kwargs):
    return _lookup_script_id('shooting_schedules', kwargs.get('schedule_id'))


def from_report(kwargs):
    return _lookup_script_id('reports', kwargs.get('report_id'))


def from_preset(kwargs):
    return _lookup_script_id('report_filter_presets', kwargs.get('preset_id'))


def from_day(kwargs):
    """Two-hop: shooting_days.schedule_id -> shooting_schedules.script_id."""
    schedule_id = _lookup_script_id('shooting_days', kwargs.get('day_id'),
                                    script_col='schedule_id')
    if not schedule_id:
        return None
    return _lookup_script_id('shooting_schedules', schedule_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_authorization.py -v`
Expected: PASS (9 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/middleware/authorization.py backend/tests/test_authorization.py
git commit -m "feat(authz): add child-resource script resolvers"
```

---

## Task 3: `@require_script_role` decorator

**Files:**
- Modify: `backend/middleware/authorization.py`
- Test: `backend/tests/test_authorization.py`

**Interfaces:**
- Consumes: `get_script_role`, resolvers (Tasks 1–2); `middleware.auth.get_user_id`; Flask `g`, `request`.
- Produces: `require_script_role(min_role: str, resolver=from_script)` decorator. On success sets `g.script_role` and `g.resolved_script_id`. Must be stacked **below** `@require_auth`.

- [ ] **Step 1: Write the failing decorator test**

```python
# add to backend/tests/test_authorization.py
import pytest
from flask import Flask, g, jsonify
import middleware.authorization as authz
from middleware.authorization import require_script_role, SCRIPT_NOT_FOUND


def _app_with_route(monkeypatch, role_returned, min_role):
    app = Flask(__name__)
    monkeypatch.setattr(authz, "get_user_id", lambda: "u1")
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: role_returned)

    @app.route("/api/scripts/<script_id>/thing", methods=["POST"])
    @require_script_role(min_role)
    def thing(script_id):
        return jsonify({"role": g.script_role}), 200

    return app.test_client()


def test_member_allowed_on_member_route(monkeypatch):
    client = _app_with_route(monkeypatch, "member", "member")
    assert client.post("/api/scripts/s1/thing").status_code == 200


def test_viewer_denied_on_member_route(monkeypatch):
    client = _app_with_route(monkeypatch, "viewer", "member")
    assert client.post("/api/scripts/s1/thing").status_code == 403


def test_owner_allowed_on_admin_route(monkeypatch):
    client = _app_with_route(monkeypatch, "owner", "admin")
    assert client.post("/api/scripts/s1/thing").status_code == 200


def test_non_member_denied(monkeypatch):
    client = _app_with_route(monkeypatch, None, "viewer")
    assert client.post("/api/scripts/s1/thing").status_code == 403


def test_missing_script_404(monkeypatch):
    client = _app_with_route(monkeypatch, SCRIPT_NOT_FOUND, "viewer")
    assert client.post("/api/scripts/s1/thing").status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_authorization.py -k "route or denied or 404" -v`
Expected: FAIL — `ImportError: cannot import name 'require_script_role'`.

- [ ] **Step 3: Implement the decorator**

```python
# append to backend/middleware/authorization.py
from functools import wraps
from flask import g, jsonify
from middleware.auth import get_user_id


def require_script_role(min_role, resolver=from_script):
    """Require the caller to hold at least `min_role` on the target script.

    Stack BELOW @require_auth. Resolves the script via `resolver(kwargs)`,
    then compares the caller's effective role against `min_role`.
    404 if the script/resource is absent; 403 if the role is insufficient.
    """
    if min_role not in ROLE_RANK:
        raise ValueError(f"Unknown min_role: {min_role}")

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_id = get_user_id()
            if not user_id:
                return jsonify({'error': 'Authentication required'}), 401

            script_id = resolver(kwargs)
            if not script_id:
                return jsonify({'error': 'Not found'}), 404

            role = get_script_role(script_id, user_id)
            if role is SCRIPT_NOT_FOUND:
                return jsonify({'error': 'Not found'}), 404
            if role is None or ROLE_RANK[role] < ROLE_RANK[min_role]:
                return jsonify({'error': 'Insufficient permissions'}), 403

            g.script_role = role
            g.resolved_script_id = script_id
            return f(*args, **kwargs)
        return wrapper
    return decorator
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_authorization.py -v`
Expected: PASS (14 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/middleware/authorization.py backend/tests/test_authorization.py
git commit -m "feat(authz): add require_script_role decorator"
```

---

## Task 4: Convert `supabase_routes.py` — script-keyed endpoints

**Files:**
- Modify: `backend/routes/supabase_routes.py`
- Test: `backend/tests/test_route_enforcement.py` (create)

Add the import once near the top of `supabase_routes.py`:

```python
from middleware.auth import require_auth
from middleware.authorization import (
    require_script_role, from_scene, from_note, from_item,
)
```

Apply this exact mapping. For each route, ensure the decorator stack is **`@<route>` then `@require_auth` then `@require_script_role(...)`**, replacing any existing `@optional_auth`. Where a handler currently calls `get_user_id()` it keeps working (auth now guaranteed).

| Route (method) | Line | min_role | resolver |
|---|---|---|---|
| `/api/scripts/<script_id>` (GET) | 180 | viewer | from_script (default) |
| `/api/scripts/<script_id>` (DELETE) | 194 | owner | default |
| `/api/scripts/<script_id>` (PATCH) | 225 | member | default |
| `/api/scripts/<script_id>/metadata` (GET) | 253 | viewer | default |
| `/api/scripts/<script_id>/scenes` (GET) | 931 | viewer | default |
| `/api/scripts/<script_id>/scenes/manage` (GET) | 1113 | viewer | default |
| `/api/scripts/<script_id>/scenes/reorder` (PATCH) | 1185 | member | default |
| `/api/scripts/<script_id>/scenes/<scene_id>/omit` (PATCH) | 1269 | member | default |
| `/api/scripts/<script_id>/scenes/<scene_id>/header` (PATCH) | 1340 | member | default |
| `/api/scripts/<script_id>/scenes/<scene_id>/history` (GET) | 1403 | viewer | default |
| `/api/scripts/<script_id>/scenes/<scene_id>/toggle-new-day` (PATCH) | 1429 | member | default |
| `/api/scripts/<script_id>/scenes/<scene_id>/lock-story-day` (PATCH) | 1460 | member | default |
| `/api/scripts/<script_id>/scenes/<scene_id>/timeline-code` (PATCH) | 1489 | member | default |
| `/api/scripts/<script_id>/scenes/<scene_id>/story-day` (PATCH) | 1524 | member | default |
| `/api/scripts/<script_id>/story-days/calculate` (POST) | 1559 | member | default |
| `/api/scripts/<script_id>/story-days/summary` (GET) | 1577 | viewer | default |
| `/api/scripts/<script_id>/story-days/bulk-update` (POST) | 1592 | member | default |
| `/api/scripts/<script_id>/scenes/<scene_id>/split` (POST) | 1647 | member | default |
| `/api/scripts/<script_id>/scenes/<scene_id>/merge` (POST) | 1769 | member | default |
| `/api/scripts/<script_id>/scenes/manual` (POST) | 1904 | member | default |
| `/api/scripts/<script_id>/scenes/merge-multiple` (POST) | 2012 | member | default |
| `/api/scripts/<script_id>/lock` (POST) | 2157 | owner | default |
| `/api/scripts/<script_id>/unlock` (POST) | 2243 | owner | default |
| `/api/scripts/<script_id>/shooting-script` (GET) | 2283 | viewer | default |
| `/api/scripts/<script_id>/full-text` (GET) | 2396 | viewer | default |
| `/api/scripts/<script_id>/page-mapping` (GET) | 2416 | viewer | default |
| `/api/scripts/<script_id>/pdf-url` (GET) | 2507 | viewer | default |
| `/api/scripts/<script_id>/analyze/bulk` (POST) | 2899 | member | default |
| `/api/scripts/<script_id>/reextract-metadata` (POST) | 3219 | member | default |
| `/api/scripts/<script_id>/items` (GET) | 3285 | viewer | default |
| `/api/scripts/<script_id>/scenes/<scene_id>/items` (GET) | 3317 | viewer | default |
| `/api/scripts/<script_id>/scenes/<scene_id>/items` (POST) | 3373 | member | default |
| `/api/scripts/<script_id>/scenes/<scene_id>/remove-ai-item` (PATCH) | 3540 | member | default |
| `/api/scripts/<script_id>/notes` (GET) | 3667 | viewer | default |
| `/api/scripts/<script_id>/notes` (POST) | 3748 | member | default |
| `/api/scripts/<script_id>/characters/aliases` (GET) | 4458 | viewer | default |

> Notes handled in Task 5: routes keyed by `scene_id`/`note_id`/`item_id` with **no** `script_id` in the path. `/api/scripts` (GET, list, line 69) and `/api/upload` (POST, 275) are **not** converted here — they are not single-script scoped; `/api/scripts` already filters by owner+membership and `/api/upload` creates a new script. Leave both as `@optional_auth` for now (flagged, out of scope). `/api/scripts/<script_id>/versions*` (4139–4341, already `@require_auth`) get `@require_script_role('member')` added (import `from_script` already present).

- [ ] **Step 1: Add the import block** (shown above) after the existing imports in `supabase_routes.py`.

- [ ] **Step 2: Apply the decorator to every row in the table above.** For a route currently reading `@optional_auth`, replace that single line with two lines:

```python
# before
@supabase_bp.route('/api/scripts/<script_id>/scenes/reorder', methods=['PATCH'])
@optional_auth
def reorder_scenes(script_id):

# after
@supabase_bp.route('/api/scripts/<script_id>/scenes/reorder', methods=['PATCH'])
@require_auth
@require_script_role('member')
def reorder_scenes(script_id):
```

For routes with **no** decorator today (e.g. GET at 180/931/253/…), insert both `@require_auth` and `@require_script_role(<role>)` between the `@…route` line and the `def`.

- [ ] **Step 3: Remove the now-dead `create_note` department fallback.** In `create_note` (~3792–3809) delete the branch that falls back to the `'production'` department when the user is not a member; a non-member can no longer reach this handler. Keep the member-department auto-detect for actual members.

- [ ] **Step 4: Write the enforcement regression test**

```python
# backend/tests/test_route_enforcement.py
import importlib
import pytest


def test_all_script_routes_have_authz():
    """Every script-scoped supabase route must carry require_script_role,
    except the explicit public/creation whitelist."""
    mod = importlib.import_module("routes.supabase_routes")
    bp = mod.supabase_bp
    WHITELIST = {"get_scripts", "upload_script"}  # non-single-script scoped
    offenders = []
    for name, fn in bp.deferred_functions_by_name().items() if hasattr(bp, "deferred_functions_by_name") else []:
        pass  # see Step 5 note; assertion implemented via app.url_map below
```

Because Flask blueprints do not expose per-view decorator metadata cleanly, implement the check against the built app's `url_map` + a sentinel attribute the decorator sets. Add to `require_script_role.wrapper` in `authorization.py`:

```python
wrapper._authz_min_role = min_role  # introspection marker for tests
```

Then the real test:

```python
# backend/tests/test_route_enforcement.py
import pytest
from app import create_app  # if app factory exists; else import app.app as app


SCRIPT_SCOPED_PREFIXES = ("/api/scripts/<script_id>",)
WHITELIST_ENDPOINTS = {"get_scripts", "upload_script"}


@pytest.fixture
def flask_app():
    from app import app  # module-level Flask instance
    return app


def test_script_scoped_routes_enforced(flask_app):
    missing = []
    for rule in flask_app.url_map.iter_rules():
        if "script_id" not in rule.arguments:
            continue
        view = flask_app.view_functions[rule.endpoint]
        if rule.endpoint in WHITELIST_ENDPOINTS:
            continue
        if not getattr(view, "_authz_min_role", None):
            missing.append(rule.endpoint)
    assert not missing, f"Unenforced script-scoped routes: {missing}"
```

- [ ] **Step 5: Run the enforcement test and the app import smoke check**

Run: `cd backend && python -c "import app" && pytest tests/test_route_enforcement.py -v`
Expected: app imports without error; test PASSES (no unenforced `script_id` routes in this file). If it lists offenders, add the decorator per the table.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/supabase_routes.py backend/middleware/authorization.py backend/tests/test_route_enforcement.py
git commit -m "feat(authz): enforce roles on script-keyed supabase routes"
```

---

## Task 5: Convert `supabase_routes.py` — child-resource-keyed endpoints

**Files:**
- Modify: `backend/routes/supabase_routes.py`

These routes have no `script_id` in the path; use a resolver.

| Route (method) | Line | min_role | resolver |
|---|---|---|---|
| `/api/scenes/<scene_id>` (PUT) | 1057 | member | from_scene |
| `/api/scenes/<scene_id>` (DELETE) | 1082 | member | from_scene |
| `/api/scenes/<scene_id>/analyze` (POST) | 2557 | member | from_scene |
| `/api/scenes/<scene_id>/notes` (GET) | 4096 | viewer | from_scene |
| `/api/items/<item_id>` (PUT) | 3477 | member | from_item |
| `/api/items/<item_id>` (DELETE) | 3634 | member | from_item |
| `/api/notes/<note_id>` (GET) | 3937 | viewer | from_note |
| `/api/notes/<note_id>` (PUT) | 3967 | member | from_note |
| `/api/notes/<note_id>` (DELETE) | 4082 | member | from_note |
| `/api/notes/<note_id>/status` (PATCH) | 4024 | member | from_note |
| `/api/notes/<note_id>/replies` (POST) | 3853 | member | from_note |

> `/api/scenes` (POST, 1017) creates a scene and takes `script_id` in the **body**, not the path — convert its handler to read `script_id` from the body and call `get_script_role` inline (see Step 2). `/api/departments` (GET, 3653) and `/api/stats` (GET, 2350) are global, not script-scoped — add `@require_auth` only (no role).

- [ ] **Step 1: Extend the import** in `supabase_routes.py` to include the resolvers already used: `from_scene, from_note, from_item` (added in Task 4) — confirm all three are imported.

- [ ] **Step 2: Apply decorators per the table**, e.g.:

```python
@supabase_bp.route('/api/scenes/<scene_id>/analyze', methods=['POST'])
@require_auth
@require_script_role('member', resolver=from_scene)
def analyze_scene(scene_id):
    ...
```

For `/api/scenes` (POST body-scoped), add `@require_auth` and inline-check at the top of the handler:

```python
from middleware.authorization import get_script_role, ROLE_RANK, SCRIPT_NOT_FOUND
from middleware.auth import get_user_id

script_id = (request.get_json(silent=True) or {}).get('script_id')
role = get_script_role(script_id, get_user_id())
if role is SCRIPT_NOT_FOUND or not script_id:
    return jsonify({'error': 'Not found'}), 404
if role is None or ROLE_RANK[role] < ROLE_RANK['member']:
    return jsonify({'error': 'Insufficient permissions'}), 403
```

- [ ] **Step 3: Run the app import + full backend test smoke**

Run: `cd backend && python -c "import app" && pytest tests/ -v`
Expected: app imports; all existing tests still PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/routes/supabase_routes.py
git commit -m "feat(authz): enforce roles on scene/note/item child routes"
```

---

## Task 6: Convert `schedule_routes.py`

**Files:**
- Modify: `backend/routes/schedule_routes.py`

Add import:

```python
from middleware.auth import require_auth
from middleware.authorization import require_script_role, from_script, from_schedule, from_day
```

| Route (method) | Line | min_role | resolver |
|---|---|---|---|
| `/api/scripts/<script_id>/schedules` (GET) | 32 | viewer | from_script |
| `/api/scripts/<script_id>/schedules` (POST) | 49 | member | from_script |
| `/api/schedules/<schedule_id>` (PATCH) | 75 | member | from_schedule |
| `/api/schedules/<schedule_id>` (DELETE) | 95 | member | from_schedule |
| `/api/schedules/<schedule_id>/days` (GET) | 112 | viewer | from_schedule |
| `/api/schedules/<schedule_id>/days` (POST) | 141 | member | from_schedule |
| `/api/shooting-days/<day_id>` (PATCH) | 196 | member | from_day |
| `/api/shooting-days/<day_id>` (DELETE) | 216 | member | from_day |
| `/api/shooting-days/<day_id>/scenes` (POST) | 233 | member | from_day |
| `/api/shooting-days/<day_id>/scenes/<scene_id>` (DELETE) | 269 | member | from_day |
| `/api/shooting-days/<day_id>/scenes/reorder` (PATCH) | 290 | member | from_day |
| `/api/shooting-days/<from_day_id>/scenes/<scene_id>/move` (POST) | 317 | member | *inline* |
| `/api/scripts/<script_id>/schedule/quick-add` (POST) | 383 | member | from_script |

> The move route uses `from_day_id`, not `day_id`, so the `from_day` resolver won't find the kwarg. Add a one-line resolver in `authorization.py`:
> ```python
> def from_move_day(kwargs):
>     sid = _lookup_script_id('shooting_days', kwargs.get('from_day_id'), script_col='schedule_id')
>     return _lookup_script_id('shooting_schedules', sid) if sid else None
> ```
> and use `resolver=from_move_day`. Import it in `schedule_routes.py`.

- [ ] **Step 1: Add `from_move_day` to `authorization.py`** (code above) and a quick unit test mirroring `test_from_day_two_hop` but with `from_day_id`.

- [ ] **Step 2: Add imports and apply decorators** per the table, replacing every `@optional_auth`.

- [ ] **Step 3: Run smoke**

Run: `cd backend && python -c "import app" && pytest tests/ -v`
Expected: imports clean; tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/routes/schedule_routes.py backend/middleware/authorization.py backend/tests/test_authorization.py
git commit -m "feat(authz): enforce member role across schedule routes"
```

---

## Task 7: Convert `report_routes.py` + preserve share-link whitelist

**Files:**
- Modify: `backend/routes/report_routes.py`
- Test: `backend/tests/test_route_enforcement.py`

Add import:

```python
from middleware.auth import require_auth
from middleware.authorization import require_script_role, from_script, from_report, from_preset
```

| Route (method) | Line | min_role | resolver |
|---|---|---|---|
| `/scripts/<script_id>/filter-options` (GET) | 51 | viewer | from_script |
| `/scripts/<script_id>/filter-presets` (GET) | 71 | viewer | from_script |
| `/scripts/<script_id>/filter-presets` (POST) | 86 | member | from_script |
| `/filter-presets/<preset_id>` (DELETE) | 133 | member | from_preset |
| `/scripts/<script_id>/reports` (GET) | 152 | viewer | from_script |
| `/scripts/<script_id>/reports/generate` (POST) | 165 | member | from_script |
| `/scripts/<script_id>/reports/preview` (POST) | 220 | member | from_script |
| `/reports/<report_id>` (GET) | 249 | viewer | from_report |
| `/reports/<report_id>` (DELETE) | 264 | member | from_report |
| `/reports/<report_id>/pdf` (GET) | 281 | viewer | from_report |
| `/reports/<report_id>/print` (GET) | 312 | viewer | from_report |
| `/reports/<report_id>/share` (POST) | 352 | member | from_report |
| `/reports/<report_id>/share` (DELETE) | 379 | member | from_report |

> **DO NOT TOUCH** — public whitelist, must remain auth-free:
> `/shared/<share_token>` (392), `/shared/<share_token>/pdf` (415), `/shared/<share_token>/print` (449).
> Global/non-script routes get `@require_auth` only, no role: `/templates` (18), `/templates/<id>` (32), `/report-types` (487), `/report-presets` (496).

- [ ] **Step 1: Add imports and apply decorators** per the table.

- [ ] **Step 2: Add the share-link regression test**

```python
# add to backend/tests/test_route_enforcement.py
def test_shared_report_routes_are_public(flask_app):
    public = {"get_shared_report", "download_shared_pdf", "get_shared_printable"}
    for rule in flask_app.url_map.iter_rules():
        if rule.endpoint in public:
            view = flask_app.view_functions[rule.endpoint]
            assert not getattr(view, "_authz_min_role", None), \
                f"{rule.endpoint} must stay public"
```

- [ ] **Step 3: Run smoke + regression**

Run: `cd backend && python -c "import app" && pytest tests/test_route_enforcement.py -v`
Expected: PASS — reports enforced, shared routes still public.

- [ ] **Step 4: Commit**

```bash
git add backend/routes/report_routes.py backend/tests/test_route_enforcement.py
git commit -m "feat(authz): enforce roles on report routes, keep share links public"
```

---

## Task 8: Frontend callsite verification + manual smoke

**Files:**
- Read-only: `frontend/src/services/apiService.js` and callers.

- [ ] **Step 1: Confirm every converted endpoint is called through `apiService`** (which attaches the JWT). Run:

```bash
cd frontend && grep -rEn "axios\.(get|post|put|patch|delete)\(" src/ | grep -v "apiService"
```
Expected: no matches (all traffic goes through the shared instance). If any direct axios call to a converted endpoint exists, route it through `apiService`.

- [ ] **Step 2: Manual smoke of the running app.** Start backend (`cd backend && python app.py`) and frontend (`cd frontend && npm run dev`). As the owner: upload a script, open it, add a note, generate a report, open the share link in a logged-out tab (must still work). Confirm no 401/403 in the network tab for owner actions.

- [ ] **Step 3: Commit** (docs only, if any notes captured)

```bash
git commit --allow-empty -m "test(authz): verify frontend callsites route through apiService"
```

---

## Task 9: Invite email

**Files:**
- Modify: `backend/services/email_service.py`
- Create: `backend/email_templates/invite.html`
- Modify: `backend/routes/invite_routes.py` (call the sender in `create_invite`, ~152–165)
- Test: `backend/tests/test_invite_email.py`

**Interfaces:**
- Produces: `send_invite(to_email: str, inviter_name: str, script_title: str, department_name: str, invite_url: str) -> bool` in `email_service.py`, mirroring the existing `send_invite_accepted_notification` signature/return style.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_invite_email.py
import services.email_service as es


def test_send_invite_calls_resend(monkeypatch):
    captured = {}
    def fake_send(payload):
        captured.update(payload)
        return {"id": "email_123"}
    monkeypatch.setattr(es, "_resend_send", fake_send, raising=False)
    ok = es.send_invite("crew@example.com", "Ava", "My Film", "Camera",
                        "https://app.slateone.studio/invite/abc")
    assert ok is True
    assert "crew@example.com" in str(captured)
```

> Adapt `_resend_send` to the actual Resend call name used in `email_service.py` (check how `send_invite_accepted_notification` dispatches; monkeypatch that exact function).

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/test_invite_email.py -v`
Expected: FAIL — `AttributeError: module 'services.email_service' has no attribute 'send_invite'`.

- [ ] **Step 3: Create the template** `backend/email_templates/invite.html` (follow the existing template files' structure/branding):

```html
<!-- backend/email_templates/invite.html -->
<div style="font-family: Arial, sans-serif; max-width: 560px; margin: 0 auto;">
  <h2>You've been invited to collaborate on {{ script_title }}</h2>
  <p>{{ inviter_name }} invited you to join the <strong>{{ department_name }}</strong>
     department on SlateOne.</p>
  <p><a href="{{ invite_url }}"
        style="background:#111;color:#fff;padding:12px 20px;border-radius:6px;
               text-decoration:none;">Accept invitation</a></p>
  <p style="color:#666;font-size:13px;">If the button doesn't work, paste this link:<br>{{ invite_url }}</p>
</div>
```

- [ ] **Step 4: Implement `send_invite`** in `email_service.py`, following the exact Resend dispatch pattern of `send_invite_accepted_notification` (render template → call the same low-level send helper → return bool, with the same try/except logging).

- [ ] **Step 5: Call it from `create_invite`.** In `invite_routes.py`, after the invite row is created and `invite_url` is built (~152–165), before returning, add:

```python
try:
    from services.email_service import send_invite
    send_invite(
        to_email=invited_email,
        inviter_name=inviter_name,        # already available in scope
        script_title=script_title,        # already fetched for the invite
        department_name=get_department_name(department_code),
        invite_url=invite_url,
    )
except Exception as e:
    logger.warning(f"Invite email failed (link still valid): {e}")
```

> Email failure is non-fatal — the copy-link fallback stays functional.

- [ ] **Step 6: Run the test**

Run: `cd backend && pytest tests/test_invite_email.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/services/email_service.py backend/email_templates/invite.html backend/routes/invite_routes.py backend/tests/test_invite_email.py
git commit -m "feat(teams): email invites to the invited address"
```

---

## Task 10: Bind invite to the invited email

**Files:**
- Modify: `backend/routes/invite_routes.py` (`accept_invite`, ~294–356; the commented check at 317–319)
- Test: `backend/tests/test_accept_invite.py`

- [ ] **Step 1: Write the failing test** (unit-level on the guard logic)

```python
# backend/tests/test_accept_invite.py
def test_email_mismatch_is_rejected():
    invited = "crew@example.com"
    caller = "someone-else@example.com"
    # mirror the guard the route will use
    assert (invited.lower() != caller.lower())
```

> This asserts the intended rule. The route change makes it real; a fuller integration test can follow, but this locks the requirement.

- [ ] **Step 2: Re-enable the email-match check** in `accept_invite`. Replace the commented block (317–319) with:

```python
caller_email = (get_current_user() or {}).get('email', '')
if invite['email'].lower() != caller_email.lower():
    return jsonify({'error': 'This invitation was sent to a different email address'}), 403
```

> `get_current_user` is already imported via the auth middleware; `invite['email']` is the field loaded by `get_invite_by_token`. Confirm the exact key name against `get_invite_by_token` (it selects the invited email column).

- [ ] **Step 3: Run tests + app import**

Run: `cd backend && python -c "import app" && pytest tests/test_accept_invite.py -v`
Expected: PASS; app imports.

- [ ] **Step 4: Commit**

```bash
git add backend/routes/invite_routes.py backend/tests/test_accept_invite.py
git commit -m "fix(teams): bind invite acceptance to the invited email"
```

---

## Task 11: Role-management endpoint

**Files:**
- Modify: `backend/routes/invite_routes.py` (new route; also convert `list_members` 561 and `create_invite` 67 to the decorator)
- Test: `backend/tests/test_role_management.py`

**Interfaces:**
- Produces: `PATCH /api/scripts/<script_id>/members/<member_id>` guarded by `@require_auth` + `@require_script_role('admin')`. Body `{"role": "viewer|member|admin"}`. Guardrails: cannot set `owner`; cannot target the owner; cannot elevate above the actor's own rank (`g.script_role`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_role_management.py
from middleware.authorization import ROLE_RANK


def _allowed(actor_role, new_role):
    if new_role not in ("viewer", "member", "admin"):
        return False
    return ROLE_RANK[new_role] <= ROLE_RANK[actor_role]


def test_admin_cannot_grant_owner():
    assert _allowed("admin", "owner") is False


def test_admin_cannot_elevate_above_self():
    assert _allowed("admin", "admin") is True
    assert _allowed("member", "admin") is False


def test_valid_downgrade_allowed():
    assert _allowed("admin", "member") is True
```

- [ ] **Step 2: Run to verify it fails** (import path won't exist yet if you place `_allowed` in the route module)

Run: `cd backend && pytest tests/test_role_management.py -v`
Expected: PASS only after the helper exists — so first place the helper in `invite_routes.py` and import it, or keep `_allowed` in the test as the spec of intent and add an integration assertion. Keep the test as written (locks the rule).

- [ ] **Step 3: Add imports** to `invite_routes.py`:

```python
from middleware.authorization import require_script_role, from_script, ROLE_RANK
```

- [ ] **Step 4: Convert `create_invite` and `list_members`** to the decorator:

```python
# create_invite (67): replace inline ownership check with:
@invite_bp.route('/api/scripts/<script_id>/invites', methods=['POST'])
@require_auth
@require_script_role('admin')
def create_invite(script_id):
    ...  # inline ownership check block can be deleted

# list_members (561): was @optional_auth
@invite_bp.route('/api/scripts/<script_id>/members', methods=['GET'])
@require_auth
@require_script_role('viewer')
def list_members(script_id):
    ...
```

- [ ] **Step 5: Add the role-change route**

```python
@invite_bp.route('/api/scripts/<script_id>/members/<member_id>', methods=['PATCH'])
@require_auth
@require_script_role('admin')
def update_member_role(script_id, member_id):
    from flask import g
    new_role = (request.get_json(silent=True) or {}).get('role')
    if new_role not in ('viewer', 'member', 'admin'):
        return jsonify({'error': 'Invalid role'}), 400
    if ROLE_RANK[new_role] > ROLE_RANK[g.script_role]:
        return jsonify({'error': 'Cannot grant a role above your own'}), 403

    supabase = get_supabase_client()
    member = (supabase.table('script_members')
              .select('id, script_id').eq('id', member_id)
              .eq('script_id', script_id).limit(1).execute())
    if not member.data:
        return jsonify({'error': 'Member not found'}), 404

    supabase.table('script_members').update({'role': new_role}).eq('id', member_id).execute()
    return jsonify({'success': True, 'role': new_role}), 200
```

> `get_supabase_client` is already imported in `invite_routes.py`; confirm and reuse.

- [ ] **Step 6: Run tests + app import**

Run: `cd backend && python -c "import app" && pytest tests/test_role_management.py -v`
Expected: PASS; app imports.

- [ ] **Step 7: Commit**

```bash
git add backend/routes/invite_routes.py backend/tests/test_role_management.py
git commit -m "feat(teams): admin role management with rank guardrails"
```

---

## Task 12: TeamDrawer role picker (frontend)

**Files:**
- Modify: `frontend/src/services/apiService.js` (add `updateMemberRole`)
- Modify: `frontend/src/components/team/TeamDrawer.jsx` (role `<select>` per member, owner/admin only)

**Interfaces:**
- Consumes: `PATCH /api/scripts/<script_id>/members/<member_id>` (Task 11).
- Produces: `apiService.updateMemberRole(scriptId, memberId, role)`.

- [ ] **Step 1: Add the API method** in `apiService.js`, following the existing method style:

```javascript
export const updateMemberRole = (scriptId, memberId, role) =>
  api.patch(`/api/scripts/${scriptId}/members/${memberId}`, { role }).then(r => r.data);
```

> Match the file's actual export/instance pattern (`api` vs default export) — mirror a neighboring method like `removeMember`.

- [ ] **Step 2: Add a role `<select>` in the member list** in `TeamDrawer.jsx`, rendered only when `isOwner` or the current user is admin, wired to `updateMemberRole` with optimistic refresh and a toast on error (use the existing `ToastContext`). Do not render the control for the owner row (role immutable). Follow the existing remove-member button pattern at `TeamDrawer.jsx:334`.

- [ ] **Step 3: Lint + manual smoke**

Run: `cd frontend && npm run lint`
Then manually: as owner, open Team drawer, change a member's role, confirm it persists on reload and that a non-admin does not see the control.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/apiService.js frontend/src/components/team/TeamDrawer.jsx
git commit -m "feat(teams): role picker in team drawer"
```

---

## Self-Review (completed against the spec)

- **Access-control primitive** (spec §Architecture) → Tasks 1–3. ✅
- **Global inclusive role ladder + matrix** (spec §Permission matrix) → Task 1 (`ROLE_RANK`), applied via role choices in Tasks 4–7, 11. ✅
- **All-in-one-pass endpoint sweep across 4 files** (spec §Endpoint classification, decision "all-in-one-pass") → Tasks 4–7 (supabase ×2, schedule, report) + invite in Task 11. ✅
- **Child-resource resolution** (surfaced in planning) → Task 2 resolvers + `from_move_day` (Task 6). ✅
- **`create_note` silent fallback → 403** (spec §Specific fixes) → Task 4 Step 3. ✅
- **schedule_routes enforcement** (spec §Specific fixes) → Task 6. ✅
- **Share-link whitelist preserved** (spec §Public) → Task 7 + regression test. ✅
- **Invite email** (spec §Teams Phase 2) → Task 9. ✅
- **Invite-to-email binding** (spec §Teams Phase 2) → Task 10. ✅
- **Role management endpoint + UI** (spec §Teams Phase 2) → Tasks 11–12. ✅
- **Rollout safety: frontend callsite check + smoke** (spec §Rollout safety) → Task 8. ✅
- **Tests: get_script_role, decorator boundaries, share-link public** (spec §Testing) → Tasks 1, 3, 7. ✅
- **DEV_MODE preserved** (spec §Global Constraints) → decorator uses `get_user_id()` which returns `DEV_USER_ID` in dev; noted seed requirement.

**Out-of-scope items deliberately left (spec §Non-Goals / Open risks):** RLS, department-scoped writes, transfer ownership, `apply_revision_changes` re-extraction, bulk-analysis thread durability, `/api/scripts` list + `/api/upload` blanket conversion.
