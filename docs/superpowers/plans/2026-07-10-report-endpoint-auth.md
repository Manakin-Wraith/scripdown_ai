# Report Endpoint Auth Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gate the report blueprint behind `@require_auth` + owner/member access checks (it currently uses the service-role key with no ownership checks), while keeping public share links and static metadata public.

**Architecture:** A new `utils/report_access.py` provides `script_access` (owner-or-member) and `report_script_id` (report→script). `report_routes.py` gains two internal guard helpers (`_check_script`, `_check_report`) and applies `@require_auth` + a guard call to each data route. The frontend's Download/Print switch from `window.open(url)` to an authenticated blob fetch so those endpoints can require auth too.

**Tech Stack:** Flask (Python 3.13) + pytest backend; React 18 + Vite (plain JSX) frontend. No new dependencies.

## Global Constraints

- No schema change. `report_service.db.client` is the Supabase service-role client the routes use; pass it to the helpers.
- Blueprint `report_bp` is mounted at `/api/reports`.
- Access model: `script_access` returns `'ok'` if `scripts.user_id == user_id` OR a `script_members(script_id, user_id)` row exists; `'not_found'` if the script row is absent; `'forbidden'` otherwise.
- Error semantics: 401 (no/invalid JWT, from `@require_auth`), 403 `{'success': False, 'error': 'Not authorized'}` (authed non-owner/member), 404 (script/report missing).
- Leave PUBLIC (do not add auth): `GET /shared/<token>`, `/shared/<token>/pdf`, `/shared/<token>/print`, `/templates`, `/templates/<id>`, `/report-types`, `/report-presets`.
- `DEV_MODE = os.getenv('FLASK_ENV') == 'development'`; `@require_auth` bypasses to `DEV_USER_ID` when `DEV_MODE`. Tests set `middleware.auth.DEV_MODE` explicitly for determinism.
- Frontend `npm run lint` is PRE-BROKEN (eslint config error, unrelated) — gate frontend on `cd frontend && npm run build` only.
- Backend tests: `cd backend && python3 -m pytest tests/<file> -v`.
- Decorator order (matches `invite_routes.py`): `@report_bp.route(...)` first, then `@require_auth`, then `def`.

---

### Task 1: `report_access` helper module + unit tests

**Files:**
- Create: `backend/utils/report_access.py`
- Test: `backend/tests/test_report_access.py`

**Interfaces:**
- Consumes: a Supabase-style client exposing `client.table(name).select(...).eq(...).limit(...).execute()` returning an object with `.data` (list of dict rows).
- Produces:
  - `script_access(client, script_id, user_id) -> str` in `{'ok','forbidden','not_found'}`.
  - `report_script_id(client, report_id) -> str | None`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_report_access.py`:

```python
"""Owner-or-member access checks for report endpoints."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.report_access import script_access, report_script_id


class _FakeResp:
    def __init__(self, data): self.data = data


class _FakeQ:
    def __init__(self, rows): self._rows = rows
    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def execute(self): return _FakeResp(self._rows)


class _FakeClient:
    def __init__(self, scripts=None, members=None, reports=None):
        self._t = {
            'scripts': scripts or [],
            'script_members': members or [],
            'reports': reports or [],
        }
    def table(self, name): return _FakeQ(self._t.get(name, []))


def test_owner_is_ok():
    c = _FakeClient(scripts=[{'user_id': 'u1'}])
    assert script_access(c, 's1', 'u1') == 'ok'


def test_member_is_ok():
    c = _FakeClient(scripts=[{'user_id': 'owner'}], members=[{'id': 'm1'}])
    assert script_access(c, 's1', 'u2') == 'ok'


def test_stranger_is_forbidden():
    c = _FakeClient(scripts=[{'user_id': 'owner'}], members=[])
    assert script_access(c, 's1', 'u2') == 'forbidden'


def test_missing_script_is_not_found():
    c = _FakeClient(scripts=[])
    assert script_access(c, 's1', 'u1') == 'not_found'


def test_report_script_id_found():
    c = _FakeClient(reports=[{'script_id': 's9'}])
    assert report_script_id(c, 'r1') == 's9'


def test_report_script_id_missing():
    c = _FakeClient(reports=[])
    assert report_script_id(c, 'r1') is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python3 -m pytest tests/test_report_access.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'utils.report_access'`.

- [ ] **Step 3: Create the helper module**

Create `backend/utils/report_access.py`:

```python
"""Access control for report endpoints: owner-or-member script access.

The report blueprint uses the Supabase service-role client (RLS bypassed), so
these functions are the app-layer authorization for report data.
"""


def script_access(client, script_id, user_id):
    """Return 'ok' | 'forbidden' | 'not_found' for (script_id, user_id).

    'ok' if the user owns the script (scripts.user_id) or is a member
    (script_members row). 'not_found' if the script does not exist.
    """
    res = client.table('scripts').select('user_id').eq('id', script_id).limit(1).execute()
    if not res.data:
        return 'not_found'
    if res.data[0].get('user_id') == user_id:
        return 'ok'
    member = (
        client.table('script_members').select('id')
        .eq('script_id', script_id).eq('user_id', user_id).limit(1).execute()
    )
    return 'ok' if member.data else 'forbidden'


def report_script_id(client, report_id):
    """Return the report's script_id, or None if the report does not exist."""
    res = client.table('reports').select('script_id').eq('id', report_id).limit(1).execute()
    return res.data[0]['script_id'] if res.data else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_report_access.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/utils/report_access.py backend/tests/test_report_access.py
git commit -m "feat(reports): add owner-or-member access helper for report endpoints"
```

---

### Task 2: Gate script-keyed report routes

**Files:**
- Modify: `backend/routes/report_routes.py` (imports at top; add two module-level guard helpers; decorate + guard 7 routes)
- Test: `backend/tests/test_report_auth.py` (new)
- Modify: `backend/tests/test_report_preview_html.py` (existing tests call now-gated routes — update them)

**Interfaces:**
- Consumes: `script_access`, `report_script_id` from Task 1; `require_auth`, `get_user_id` from `middleware.auth`; `report_service.db.client`.
- Produces (used by Task 3):
  - `_check_script(script_id) -> (response, status) | None` — module-level in `report_routes.py`.
  - `_check_report(report_id) -> (response, status) | None`.

- [ ] **Step 1: Write the failing route tests**

Create `backend/tests/test_report_auth.py`:

```python
"""Report data endpoints require auth + owner/member access; share stays public."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.report_routes as rr


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_reports_list_requires_auth(monkeypatch):
    # Force production auth behavior: no bypass, no header -> 401.
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().get("/api/reports/scripts/s1/reports")
    assert resp.status_code == 401


def test_reports_list_forbidden_for_non_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)   # bypass auth layer
    monkeypatch.setattr(rr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(rr, "script_access", lambda c, sid, uid: "forbidden")
    resp = _client().get("/api/reports/scripts/s1/reports")
    assert resp.status_code == 403


def test_reports_list_ok_for_owner(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(rr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(rr, "script_access", lambda c, sid, uid: "ok")
    monkeypatch.setattr(rr.report_service, "get_script_reports", lambda sid: [])
    resp = _client().get("/api/reports/scripts/s1/reports")
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_missing_script_is_404(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(rr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(rr, "script_access", lambda c, sid, uid: "not_found")
    resp = _client().get("/api/reports/scripts/s1/reports")
    assert resp.status_code == 404


def test_shared_route_stays_public(monkeypatch):
    # Public share endpoint must work with NO auth even in production mode.
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    monkeypatch.setattr(rr.report_service, "get_report_by_token", lambda t: None)
    resp = _client().get("/api/reports/shared/sometoken")
    # 404 (token not found) proves the handler ran WITHOUT an auth rejection (not 401).
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python3 -m pytest tests/test_report_auth.py -v`
Expected: FAIL — `test_reports_list_requires_auth` gets 200 (route currently unauthenticated); `AttributeError` on `rr.script_access` (not imported yet).

- [ ] **Step 3: Update imports + add guard helpers**

In `backend/routes/report_routes.py`, change the import block (top of file) from:

```python
from middleware.auth import optional_auth, get_user_id
```

to:

```python
from middleware.auth import optional_auth, require_auth, get_user_id
from utils.report_access import script_access, report_script_id
```

Then add these two module-level helpers immediately after `report_bp = Blueprint('reports', __name__)`:

```python
def _check_script(script_id):
    """Guard: None if the current user may access script_id, else an error response."""
    status = script_access(report_service.db.client, script_id, get_user_id())
    if status == 'not_found':
        return jsonify({'success': False, 'error': 'Script not found'}), 404
    if status == 'forbidden':
        return jsonify({'success': False, 'error': 'Not authorized'}), 403
    return None


def _check_report(report_id):
    """Guard: None if the current user may access the report's script, else an error response."""
    script_id = report_script_id(report_service.db.client, report_id)
    if not script_id:
        return jsonify({'success': False, 'error': 'Report not found'}), 404
    return _check_script(script_id)
```

- [ ] **Step 4: Decorate + guard the 7 script-keyed routes**

For EACH route below: (a) add `@require_auth` on the line directly under its `@report_bp.route(...)` decorator (for the two `filter-presets` routes, REPLACE the existing `@optional_auth` with `@require_auth`); (b) insert the guard as the first two lines inside the function body (before the existing `try:`):

```python
    denied = _check_script(script_id)
    if denied:
        return denied
```

Routes (function names in `report_routes.py`):
- `get_filter_options` (`/scripts/<script_id>/filter-options`) — add `@require_auth` + guard.
- `get_filter_presets` (`/scripts/<script_id>/filter-presets` GET) — replace `@optional_auth` with `@require_auth` + guard.
- `save_filter_preset` (`/scripts/<script_id>/filter-presets` POST) — replace `@optional_auth` with `@require_auth` + guard.
- `get_script_reports` (`/scripts/<script_id>/reports` GET) — add `@require_auth` + guard.
- `generate_report` (`/scripts/<script_id>/reports/generate` POST) — add `@require_auth` + guard.
- `preview_report` (`/scripts/<script_id>/reports/preview` POST) — add `@require_auth` + guard.
- `preview_report_html` (`/scripts/<script_id>/reports/preview-html` POST) — add `@require_auth` + guard.

Example (get_script_reports) — before:

```python
@report_bp.route('/scripts/<script_id>/reports', methods=['GET'])
def get_script_reports(script_id):
    """Get all reports for a script."""
    try:
```

after:

```python
@report_bp.route('/scripts/<script_id>/reports', methods=['GET'])
@require_auth
def get_script_reports(script_id):
    """Get all reports for a script."""
    denied = _check_script(script_id)
    if denied:
        return denied
    try:
```

- [ ] **Step 5: Fix the existing preview/list tests broken by gating**

`preview_report_html`, `preview_report`, and `get_script_reports` are now gated. The existing tests in `backend/tests/test_report_preview_html.py` call `POST /api/reports/scripts/<id>/reports/preview-html` and `GET /api/reports/scripts/<id>/reports` without auth, so they will now fail (401/404). Fix all three tests in that file by adding, at the START of each test body, an auth bypass + access grant:

```python
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(rr, "script_access", lambda c, sid, uid: "ok")
```

(Each of the three tests already receives `monkeypatch` and imports `routes.report_routes as rr`.) Add these two lines before the existing `monkeypatch.setattr(...)` calls in `test_preview_html_returns_html_and_counts`, `test_preview_html_invalid_type_returns_400`, and `test_reports_list_includes_config_and_type`. Do not weaken existing assertions.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_report_auth.py tests/test_report_preview_html.py -v`
Expected: PASS (5 in test_report_auth.py + 3 in test_report_preview_html.py = 8 passed).

- [ ] **Step 7: Commit**

```bash
git add backend/routes/report_routes.py backend/tests/test_report_auth.py backend/tests/test_report_preview_html.py
git commit -m "feat(reports): require auth + owner/member access on script-keyed report routes"
```

---

### Task 3: Gate report-keyed routes + filter-preset delete

**Files:**
- Modify: `backend/routes/report_routes.py` (decorate + guard 6 report-keyed routes; upgrade `delete_filter_preset`)
- Test: `backend/tests/test_report_auth.py` (append)

**Interfaces:**
- Consumes: `_check_report` and `_check_script` (Task 2), `require_auth`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_report_auth.py`:

```python
def test_print_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().get("/api/reports/reports/r1/print")
    assert resp.status_code == 401


def test_print_forbidden_for_non_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(rr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(rr, "report_script_id", lambda c, rid: "s1")
    monkeypatch.setattr(rr, "script_access", lambda c, sid, uid: "forbidden")
    resp = _client().get("/api/reports/reports/r1/print")
    assert resp.status_code == 403


def test_print_ok_for_owner(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(rr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(rr, "report_script_id", lambda c, rid: "s1")
    monkeypatch.setattr(rr, "script_access", lambda c, sid, uid: "ok")
    monkeypatch.setattr(rr.report_service, "get_report",
                        lambda rid: {"title": "R", "report_type": "scene_breakdown", "data_snapshot": {}})
    monkeypatch.setattr(rr.report_service, "_render_report_html", lambda report: "<html><body>x</body></html>")
    monkeypatch.setattr(rr.report_service, "_get_report_css", lambda: "")
    resp = _client().get("/api/reports/reports/r1/print")
    assert resp.status_code == 200


def test_missing_report_is_404(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(rr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(rr, "report_script_id", lambda c, rid: None)
    resp = _client().get("/api/reports/reports/r1/print")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python3 -m pytest tests/test_report_auth.py -v`
Expected: FAIL — `test_print_requires_auth` gets 200 (route currently unauthenticated).

- [ ] **Step 3: Decorate + guard the 6 report-keyed routes**

For EACH route below: add `@require_auth` under its `@report_bp.route(...)`, and insert as the first two lines of the body (before `try:`):

```python
    denied = _check_report(report_id)
    if denied:
        return denied
```

Routes (function names): `get_report` (`GET /reports/<report_id>`), `delete_report` (`DELETE /reports/<report_id>`), `download_pdf` (`GET /reports/<report_id>/pdf`), `get_printable_html` (`GET /reports/<report_id>/print`), `create_share_link` (`POST /reports/<report_id>/share`), `revoke_share_link` (`DELETE /reports/<report_id>/share`).

Example (`get_printable_html`) — before:

```python
@report_bp.route('/reports/<report_id>/print', methods=['GET'])
def get_printable_html(report_id):
    """Get printable HTML version of report."""
    try:
```

after:

```python
@report_bp.route('/reports/<report_id>/print', methods=['GET'])
@require_auth
def get_printable_html(report_id):
    """Get printable HTML version of report."""
    denied = _check_report(report_id)
    if denied:
        return denied
    try:
```

- [ ] **Step 4: Upgrade `delete_filter_preset`**

For `delete_filter_preset` (`DELETE /filter-presets/<preset_id>`): REPLACE its `@optional_auth` decorator with `@require_auth`. Do NOT add a `_check_report`/`_check_script` guard — the service method already scopes the delete to the caller's `user_id`. (The route already calls `get_user_id()` internally; leave that body as-is.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_report_auth.py -v`
Expected: PASS (9 passed — 5 from Task 2 + 4 appended here).

- [ ] **Step 6: Commit**

```bash
git add backend/routes/report_routes.py backend/tests/test_report_auth.py
git commit -m "feat(reports): require auth + access on report-keyed routes and preset delete"
```

---

### Task 4: Frontend authenticated print fetch

**Files:**
- Modify: `frontend/src/services/apiService.js` (add `fetchReportPrintUrl`)
- Modify: `frontend/src/components/reports/ReportStudio.jsx` (`handleDownload`/`handlePrint`)

**Interfaces:**
- Consumes: the existing `api` axios instance (attaches JWT).
- Produces: `fetchReportPrintUrl(reportId) -> Promise<string>` — resolves to an object URL for the printable HTML blob (throws on failure).

- [ ] **Step 1: Add the authenticated fetch helper**

In `frontend/src/services/apiService.js`, add near `getReportPrintUrl`:

```javascript
/**
 * Fetch a report's printable HTML with auth (JWT) and return an object URL.
 * Caller is responsible for opening it and revoking the URL.
 */
export const fetchReportPrintUrl = async (reportId) => {
    const response = await api.get(`/api/reports/reports/${reportId}/print`, { responseType: 'blob' });
    return URL.createObjectURL(response.data);
};
```

- [ ] **Step 2: Rewire Download/Print in ReportStudio**

In `frontend/src/components/reports/ReportStudio.jsx`:

- Add `fetchReportPrintUrl` to the existing apiService import (the import block that already brings in `getReportPrintUrl`); `getReportPrintUrl` may be removed from the import if no longer referenced.
- Replace the two handlers:

```javascript
    const handleDownload = (report) => openPrintable(report);
    const handlePrint = (report) => openPrintable(report);
```

- Add the shared helper above them (opens the tab synchronously in the click gesture to avoid popup blockers, then points it at the fetched blob):

```javascript
    const openPrintable = async (report) => {
        const win = window.open('', '_blank');
        try {
            const url = await fetchReportPrintUrl(report.id);
            if (win) win.location = url; else window.open(url, '_blank');
            setTimeout(() => URL.revokeObjectURL(url), 60000);
        } catch (e) {
            if (win) win.close();
            toast.error('Error', 'Could not open the report');
        }
    };
```

(`toast` is already available in the component via `useToast()`.)

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds. (Skip lint — pre-broken.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/apiService.js frontend/src/components/reports/ReportStudio.jsx
git commit -m "feat(reports): fetch printable report with auth (blob) instead of bare window.open"
```

---

### Task 5: Manual end-to-end verification

**Files:** none (verification only).

- [ ] **Step 1: Start the stack**

Backend: `cd backend && python3 app.py` (needs env vars). Frontend: `cd frontend && npm run dev`.

- [ ] **Step 2: Verify, one at a time**

1. Logged in as a script's owner: Reports page loads, Generate works, and Download/Print open the printable report in a new tab.
2. Log in as a **different** user who is not a member of that script and hit the same report/script ids (e.g. via devtools/manual URL to `/api/reports/scripts/<id>/reports`): the API returns 403.
3. With no auth at all (curl `/api/reports/scripts/<id>/reports` without a token): returns 401.
4. A previously created **public share link** (`/shared/<token>`) still opens with no login.

Expected: all four behave as described; no console errors on the happy path.

- [ ] **Step 3: Commit (if fixes were needed)**

```bash
git add -A
git commit -m "fix(reports): address issues found in auth-hardening manual verification"
```

---

## Notes for the implementer

- Do NOT add auth to the `/shared/<token>*`, `/templates*`, `/report-types`, or `/report-presets` routes — they are intentionally public.
- The guard helpers evaluate `report_service.db.client` to pass into `script_access`; in route tests `script_access`/`report_script_id` are monkeypatched, so the client is not actually queried there.
- Keep `getReportPrintUrl`/`getReportPdfUrl` URL builders in `apiService.js` even if unused now (cheap, and referenced by the path string); removing them is not required.
