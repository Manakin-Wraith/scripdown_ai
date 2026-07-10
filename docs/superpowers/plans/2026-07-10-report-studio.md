# Report Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fragmented Report page with a single-screen "Report Studio" — type icon-list + filters on a left rail, a live rendered report preview on the right, and past reports in a Library drawer that reopens a report's saved config for editing.

**Architecture:** One new backend endpoint renders report HTML from unsaved config by reusing the existing `_render_report_html()` path (WYSIWYG with the PDF). The frontend `ReportBuilder` is refactored into a `ReportStudio` shell composing four focused components (`ReportRail`, `ReportPreviewPane`, `ReportLibraryDrawer`, and the reused `ReportFilterPanel`). Preview refreshes manually via an "Update Preview" button.

**Tech Stack:** Flask (Python 3.13) + pytest on the backend; React 18 + Vite (plain JSX) on the frontend. No new dependencies.

## Global Constraints

- Backend: no new tables, no schema migration. Reuse `report_service` singleton already imported in `backend/routes/report_routes.py`.
- Backend blueprint `report_bp` is mounted at url_prefix `/api/reports` (so a route `'/scripts/<id>/reports/preview-html'` is reached at `/api/reports/scripts/<id>/reports/preview-html`).
- Frontend has **no test runner**. Frontend tasks are verified with `cd frontend && npm run lint` and `npm run build`, plus manual desktop checks — do NOT add vitest/jest.
- Frontend: all backend calls go through the single axios instance in `frontend/src/services/apiService.js`. Do not create new axios instances.
- Preview must reuse `report_service._render_report_html()` so preview output equals the PDF/print output. No divergent rendering.
- Existing endpoints (generate, pdf, print, share, filter-options, filter-presets, report-types) are reused unchanged.
- Route swap: the redesigned page keeps the existing route `scripts/:scriptId/reports` in `frontend/src/App.jsx`.

---

### Task 1: Backend — `render_preview_html` service method + `preview-html` endpoint

**Files:**
- Modify: `backend/services/report_service.py` (add `render_preview_html` method to the `ReportService` class, near `generate_report` ~line 782)
- Modify: `backend/routes/report_routes.py` (add route after the existing `preview_report`, ~line 243)
- Test: `backend/tests/test_report_preview_html.py`

**Interfaces:**
- Consumes: existing `ReportService.aggregate_scene_data(script_id, filters)`, `ReportService._render_report_html(report_dict)`, `ReportService.db.get_scenes(script_id)`, `ReportService.REPORT_TYPES`.
- Produces:
  - `ReportService.render_preview_html(script_id, report_type, config=None, title=None, filters=None) -> dict` returning `{ 'html': str, 'match_count': int, 'total_count': int }`. Raises `ValueError` on invalid `report_type`.
  - `POST /api/reports/scripts/<script_id>/reports/preview-html` returning JSON `{ success, html, match_count, total_count }`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_report_preview_html.py`:

```python
"""preview-html renders report HTML from unsaved config without persisting."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import routes.report_routes as rr


FAKE_DATA = {
    "script": {"title": "Midnight Run"},
    "summary": {"total_scenes": 3},
    "scenes": [1, 2, 3],
}


def test_preview_html_returns_html_and_counts(monkeypatch):
    calls = {"insert": 0}

    monkeypatch.setattr(rr.report_service, "aggregate_scene_data",
                        lambda script_id, filters=None: FAKE_DATA)
    monkeypatch.setattr(rr.report_service, "_render_report_html",
                        lambda report: "<html><body><h1>Preview</h1></body></html>")
    # total_count comes from db.get_scenes
    monkeypatch.setattr(rr.report_service.db, "get_scenes",
                        lambda script_id: [1, 2, 3, 4, 5])
    # Guard: generating/persisting must never happen on preview
    def _boom(*a, **k):
        calls["insert"] += 1
        raise AssertionError("preview must not persist a report")
    monkeypatch.setattr(rr.report_service, "generate_report", _boom)

    from app import app
    app.config["TESTING"] = True
    resp = app.test_client().post(
        "/api/reports/scripts/scr-1/reports/preview-html",
        json={"report_type": "scene_breakdown", "filters": {"locations": ["INT. KITCHEN"]}},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert "<h1>Preview</h1>" in body["html"]
    assert body["match_count"] == 3
    assert body["total_count"] == 5
    assert calls["insert"] == 0


def test_preview_html_invalid_type_returns_400(monkeypatch):
    from app import app
    app.config["TESTING"] = True
    resp = app.test_client().post(
        "/api/reports/scripts/scr-1/reports/preview-html",
        json={"report_type": "not_a_type"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_report_preview_html.py -v`
Expected: FAIL — route returns 404 (endpoint not defined) / AttributeError.

- [ ] **Step 3: Add the service method**

In `backend/services/report_service.py`, add this method to `ReportService` (place it immediately after `generate_report`):

```python
    def render_preview_html(
        self,
        script_id: str,
        report_type: str,
        config: Optional[Dict] = None,
        title: Optional[str] = None,
        filters: Optional[Dict] = None,
    ) -> Dict:
        """
        Render report HTML from unsaved config for live preview.
        Reuses the exact render path as PDF/print. Does NOT persist anything.
        Returns { 'html', 'match_count', 'total_count' }.
        """
        if report_type not in self.REPORT_TYPES:
            raise ValueError(f"Invalid report type: {report_type}")

        data = self.aggregate_scene_data(script_id, filters=filters)

        merged_config = dict(config or {})
        if filters:
            merged_config['filters'] = filters

        if not title:
            title = f"{data['script']['title']} - {self.REPORT_TYPES[report_type]['name']}"

        # In-memory report dict — same shape _render_report_html expects, never saved.
        report = {
            'report_type': report_type,
            'title': title,
            'config': merged_config,
            'data_snapshot': data,
        }
        html = self._render_report_html(report)

        match_count = data.get('summary', {}).get('total_scenes', 0)
        total_count = len(self.db.get_scenes(script_id))

        return {'html': html, 'match_count': match_count, 'total_count': total_count}
```

- [ ] **Step 4: Add the route**

In `backend/routes/report_routes.py`, add immediately after the `preview_report` function (~line 243):

```python
@report_bp.route('/scripts/<script_id>/reports/preview-html', methods=['POST'])
def preview_report_html(script_id):
    """
    Render report HTML from unsaved config for live preview. Does not persist.
    Body: { report_type, filters, group_by, categories, title }
    """
    try:
        data = request.get_json() or {}
        report_type = data.get('report_type', 'scene_breakdown')
        filters = data.get('filters')
        group_by = data.get('group_by')
        categories = data.get('categories')
        title = data.get('title')

        config = {}
        if group_by:
            config['group_by'] = group_by
        if categories:
            config['categories'] = categories

        if report_type not in report_service.REPORT_TYPES:
            return jsonify({
                'success': False,
                'error': f'Invalid report type. Valid types: {list(report_service.REPORT_TYPES.keys())}'
            }), 400

        result = report_service.render_preview_html(
            script_id=script_id,
            report_type=report_type,
            config=config,
            title=title,
            filters=filters,
        )
        return jsonify({
            'success': True,
            'html': result['html'],
            'match_count': result['match_count'],
            'total_count': result['total_count'],
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_report_preview_html.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/services/report_service.py backend/routes/report_routes.py backend/tests/test_report_preview_html.py
git commit -m "feat(reports): add preview-html endpoint for live report preview"
```

---

### Task 2: Backend — confirm reports list returns `config` + `report_type`

**Files:**
- Verify (likely no change): `backend/services/report_service.py:get_script_reports` (uses `select('*')`) and `backend/routes/report_routes.py:get_script_reports`.
- Test: `backend/tests/test_report_preview_html.py` (append)

**Interfaces:**
- Consumes: `GET /api/reports/scripts/<script_id>/reports` returning `{ success, reports: [...] }`.
- Produces: guarantee each report item includes `report_type` and `config` (needed by the Library reopen feature).

- [ ] **Step 1: Write the failing/guard test**

Append to `backend/tests/test_report_preview_html.py`:

```python
def test_reports_list_includes_config_and_type(monkeypatch):
    fake_reports = [
        {"id": "r1", "report_type": "scene_breakdown",
         "config": {"filters": {"locations": ["INT. KITCHEN"]}, "group_by": "location"},
         "title": "Wk1", "generated_at": "2026-07-08T00:00:00", "is_public": False},
    ]
    monkeypatch.setattr(rr.report_service, "get_script_reports",
                        lambda script_id: fake_reports)
    from app import app
    app.config["TESTING"] = True
    resp = app.test_client().get("/api/reports/scripts/scr-1/reports")
    assert resp.status_code == 200
    reports = resp.get_json()["reports"]
    assert reports[0]["report_type"] == "scene_breakdown"
    assert reports[0]["config"]["group_by"] == "location"
```

- [ ] **Step 2: Run test**

Run: `cd backend && python3 -m pytest tests/test_report_preview_html.py::test_reports_list_includes_config_and_type -v`
Expected: PASS if the route already forwards full rows. If it FAILS (route strips fields), edit `get_script_reports` in `backend/routes/report_routes.py` to return the service rows verbatim (do not whitelist fields), then re-run.

- [ ] **Step 3: Commit (only if a change was needed)**

```bash
git add backend/routes/report_routes.py backend/tests/test_report_preview_html.py
git commit -m "test(reports): guarantee reports list exposes config + report_type"
```

---

### Task 3: Frontend — `previewReportHtml` API helper

**Files:**
- Modify: `frontend/src/services/apiService.js` (add after the existing `previewReport`, ~line 686)

**Interfaces:**
- Consumes: the `api` axios instance already defined in the file.
- Produces: `previewReportHtml(scriptId, reportType, filters=null, groupBy=null, categories=null, title=null) -> Promise<{ success, html, match_count, total_count }>`.

- [ ] **Step 1: Add the helper**

In `frontend/src/services/apiService.js`, add:

```javascript
/**
 * Render report HTML from unsaved config for live preview (no DB write).
 */
export const previewReportHtml = async (scriptId, reportType, filters = null, groupBy = null, categories = null, title = null) => {
    try {
        const response = await api.post(`/api/reports/scripts/${scriptId}/reports/preview-html`, {
            report_type: reportType,
            filters,
            group_by: groupBy,
            categories,
            title,
        });
        return response.data;
    } catch (error) {
        console.error('Error rendering report preview:', error);
        return { success: false, error: error.response?.data?.error || error.message };
    }
};
```

- [ ] **Step 2: Verify lint + build**

Run: `cd frontend && npm run lint && npm run build`
Expected: no new lint errors; build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/apiService.js
git commit -m "feat(reports): add previewReportHtml API helper"
```

---

### Task 4: Frontend — `ReportPreviewPane` component

**Files:**
- Create: `frontend/src/components/reports/ReportPreviewPane.jsx`
- Create: `frontend/src/components/reports/ReportPreviewPane.css`

**Interfaces:**
- Consumes: props `{ html, matchCount, totalCount, loading, error, onRefresh }`.
- Produces: a self-contained pane rendering `html` inside a sandboxed iframe with empty/loading/error states and an "Update Preview" button that calls `onRefresh`.

- [ ] **Step 1: Create the component**

Create `frontend/src/components/reports/ReportPreviewPane.jsx`:

```jsx
import React from 'react';
import { RefreshCw, FileText } from 'lucide-react';
import { Spinner, Button } from '../ui';
import './ReportPreviewPane.css';

const ReportPreviewPane = ({ html, matchCount, totalCount, loading, error, onRefresh }) => {
    return (
        <div className="report-preview-pane">
            <div className="preview-toolbar">
                <span className="preview-status">
                    {typeof matchCount === 'number' && typeof totalCount === 'number'
                        ? `${matchCount} of ${totalCount} scenes match`
                        : 'Live preview'}
                </span>
                <Button variant="secondary" onClick={onRefresh} disabled={loading}>
                    <RefreshCw size={16} />
                    Update Preview
                </Button>
            </div>

            <div className="preview-surface">
                {loading && (
                    <div className="preview-overlay">
                        <Spinner size={28} />
                        <p>Rendering preview…</p>
                    </div>
                )}

                {!loading && error && (
                    <div className="preview-message error">
                        <p>Couldn’t render preview.</p>
                        <p className="preview-message-detail">{error}</p>
                    </div>
                )}

                {!loading && !error && !html && (
                    <div className="preview-message">
                        <FileText size={32} />
                        <p>Configure on the left, then hit <strong>Update Preview</strong>.</p>
                    </div>
                )}

                {!loading && !error && html && (
                    <iframe
                        className="preview-frame"
                        title="Report preview"
                        sandbox=""
                        srcDoc={html}
                    />
                )}
            </div>
        </div>
    );
};

export default ReportPreviewPane;
```

- [ ] **Step 2: Create the stylesheet**

Create `frontend/src/components/reports/ReportPreviewPane.css`:

```css
.report-preview-pane { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.preview-toolbar { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-bottom: 1px solid var(--border, #2a2a2a); }
.preview-status { font-size: 12px; opacity: 0.7; }
.preview-surface { position: relative; flex: 1; min-height: 400px; background: #f4f4f4; overflow: auto; }
.preview-frame { width: 100%; height: 100%; min-height: 600px; border: 0; background: #fff; }
.preview-overlay { position: absolute; inset: 0; display: flex; flex-direction: column; gap: 8px; align-items: center; justify-content: center; background: rgba(0,0,0,0.35); color: #fff; }
.preview-message { display: flex; flex-direction: column; gap: 8px; align-items: center; justify-content: center; height: 100%; color: #555; text-align: center; padding: 24px; }
.preview-message.error { color: #b91c1c; }
.preview-message-detail { font-size: 12px; opacity: 0.7; }
```

- [ ] **Step 3: Verify lint + build**

Run: `cd frontend && npm run lint && npm run build`
Expected: no new lint errors; build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/reports/ReportPreviewPane.jsx frontend/src/components/reports/ReportPreviewPane.css
git commit -m "feat(reports): add ReportPreviewPane with iframe live preview"
```

---

### Task 5: Frontend — `ReportRail` component (type list + filters + title)

**Files:**
- Create: `frontend/src/components/reports/ReportRail.jsx`
- Create: `frontend/src/components/reports/ReportRail.css`

**Interfaces:**
- Consumes:
  - props `{ reportTypes, selectedType, onSelectType, customTitle, onTitleChange, filterPanelProps }`.
  - `reportTypes` is the object from `getReportTypes()` (`{ [type]: { name, description } }`).
  - `filterPanelProps` is the full prop bundle passed straight through to the existing `ReportFilterPanel` (filterOptions, filters, onFilterChange, presets, onLoadPreset, onSavePreset, onDeletePreset).
  - Reuses `REPORT_ICONS` (moved to a shared module in this task).
- Produces: the left rail UI. Type selection calls `onSelectType(type)`. Title input calls `onTitleChange(value)`.

- [ ] **Step 1: Extract the shared icon map**

Create `frontend/src/components/reports/reportIcons.js`:

```javascript
import {
    FileText, Users, MapPin, Package, Shirt, Film, List, BookOpen,
    UserPlus, Zap, Flame,
} from 'lucide-react';

export const REPORT_ICONS = {
    scene_breakdown: Film,
    day_out_of_days: Users,
    location: MapPin,
    props: Package,
    wardrobe: Shirt,
    one_liner: List,
    full_breakdown: BookOpen,
    extras: UserPlus,
    sfx: Zap,
    special_effects: Zap,
    stunts: Flame,
};

export const reportIcon = (type) => REPORT_ICONS[type] || FileText;
```

- [ ] **Step 2: Create the rail component**

Create `frontend/src/components/reports/ReportRail.jsx`:

```jsx
import React from 'react';
import { reportIcon } from './reportIcons';
import ReportFilterPanel from './ReportFilterPanel';
import './ReportRail.css';

const ReportRail = ({
    reportTypes,
    selectedType,
    onSelectType,
    customTitle,
    onTitleChange,
    filterPanelProps,
}) => {
    return (
        <div className="report-rail">
            <div className="rail-section">
                <span className="rail-label">Report type</span>
                <div className="rail-type-list">
                    {Object.entries(reportTypes || {}).map(([type, info]) => {
                        const Icon = reportIcon(type);
                        return (
                            <button
                                key={type}
                                className={`rail-type ${selectedType === type ? 'on' : ''}`}
                                onClick={() => onSelectType(type)}
                                title={info.description}
                            >
                                <Icon size={16} />
                                <span>{info.name}</span>
                            </button>
                        );
                    })}
                </div>
            </div>

            <div className="rail-section rail-filters">
                <ReportFilterPanel {...filterPanelProps} isCollapsed={false} />
            </div>

            <div className="rail-section">
                <label className="rail-label" htmlFor="report-title">Title (optional)</label>
                <input
                    id="report-title"
                    type="text"
                    className="rail-title-input"
                    value={customTitle}
                    onChange={(e) => onTitleChange(e.target.value)}
                    placeholder="e.g. Week 1 — Interiors"
                />
            </div>
        </div>
    );
};

export default ReportRail;
```

- [ ] **Step 3: Create the stylesheet**

Create `frontend/src/components/reports/ReportRail.css`:

```css
.report-rail { display: flex; flex-direction: column; gap: 14px; height: 100%; overflow-y: auto; padding: 12px; }
.rail-section { display: flex; flex-direction: column; gap: 6px; }
.rail-label { font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.6; }
.rail-type-list { display: flex; flex-direction: column; gap: 2px; }
.rail-type { display: flex; align-items: center; gap: 8px; padding: 7px 9px; border: 0; border-radius: 6px; background: transparent; color: inherit; cursor: pointer; text-align: left; font-size: 13px; }
.rail-type:hover { background: rgba(255,255,255,0.06); }
.rail-type.on { background: #F59E0B; color: #000; font-weight: 700; }
.rail-title-input { width: 100%; padding: 8px 10px; border: 1px solid var(--border, #444); border-radius: 6px; background: transparent; color: inherit; font-size: 13px; }
.rail-filters :where(.filter-panel) { width: 100%; }
```

- [ ] **Step 4: Verify lint + build**

Run: `cd frontend && npm run lint && npm run build`
Expected: no new lint errors; build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/reports/ReportRail.jsx frontend/src/components/reports/ReportRail.css frontend/src/components/reports/reportIcons.js
git commit -m "feat(reports): add ReportRail (type list + reused filters + title)"
```

---

### Task 6: Frontend — `ReportLibraryDrawer` component

**Files:**
- Create: `frontend/src/components/reports/ReportLibraryDrawer.jsx`
- Create: `frontend/src/components/reports/ReportLibraryDrawer.css`

**Interfaces:**
- Consumes: props `{ open, reports, onClose, onReopen, onDownload, onShare, onDelete }`.
  - `reports` is the array from `getScriptReports` (each has `id, title, report_type, config, generated_at, is_public`).
  - `onReopen(report)` restores the report's type + config into the rail.
- Produces: a slide-over drawer with client-side search and per-item actions.

- [ ] **Step 1: Create the component**

Create `frontend/src/components/reports/ReportLibraryDrawer.jsx`:

```jsx
import React, { useState } from 'react';
import { X, Search, Download, Share2, Trash2 } from 'lucide-react';
import { Badge } from '../ui';
import { reportIcon } from './reportIcons';
import './ReportLibraryDrawer.css';

const ReportLibraryDrawer = ({ open, reports, onClose, onReopen, onDownload, onShare, onDelete }) => {
    const [query, setQuery] = useState('');

    const filtered = (reports || []).filter((r) => {
        const q = query.trim().toLowerCase();
        if (!q) return true;
        return (r.title || '').toLowerCase().includes(q) || (r.report_type || '').toLowerCase().includes(q);
    });

    return (
        <>
            {open && <div className="library-backdrop" onClick={onClose} />}
            <aside className={`library-drawer ${open ? 'open' : ''}`} aria-hidden={!open}>
                <div className="library-header">
                    <strong>Library · past reports</strong>
                    <button className="library-close" onClick={onClose} title="Close"><X size={18} /></button>
                </div>

                <div className="library-search">
                    <Search size={14} />
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search reports…"
                    />
                </div>

                <div className="library-list">
                    {filtered.length === 0 ? (
                        <p className="library-empty">No reports yet.</p>
                    ) : filtered.map((report) => {
                        const Icon = reportIcon(report.report_type);
                        const date = report.generated_at ? new Date(report.generated_at).toLocaleDateString() : '';
                        return (
                            <div key={report.id} className="library-item">
                                <button className="library-item-main" onClick={() => onReopen(report)} title="Reopen to edit">
                                    <Icon size={18} />
                                    <span className="library-item-text">
                                        <span className="library-item-title">
                                            {report.title}
                                            {report.is_public && <Badge variant="success" icon={Share2}>Shared</Badge>}
                                        </span>
                                        <span className="library-item-meta">{date} · click to reopen &amp; edit</span>
                                    </span>
                                </button>
                                <div className="library-item-actions">
                                    <button className="lib-action" onClick={() => onDownload(report)} title="Download"><Download size={15} /></button>
                                    <button className="lib-action" onClick={() => onShare(report)} title="Share"><Share2 size={15} /></button>
                                    <button className="lib-action danger" onClick={() => onDelete(report)} title="Delete"><Trash2 size={15} /></button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </aside>
        </>
    );
};

export default ReportLibraryDrawer;
```

- [ ] **Step 2: Create the stylesheet**

Create `frontend/src/components/reports/ReportLibraryDrawer.css`:

```css
.library-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 40; }
.library-drawer { position: fixed; top: 0; right: 0; bottom: 0; width: min(420px, 90vw); background: var(--surface, #141414); border-left: 1px solid var(--border, #2a2a2a); box-shadow: -10px 0 30px rgba(0,0,0,0.5); z-index: 41; transform: translateX(100%); transition: transform 0.2s ease; display: flex; flex-direction: column; }
.library-drawer.open { transform: translateX(0); }
.library-header { display: flex; justify-content: space-between; align-items: center; padding: 14px; border-bottom: 1px solid var(--border, #2a2a2a); }
.library-close { background: none; border: 0; color: inherit; cursor: pointer; }
.library-search { display: flex; align-items: center; gap: 6px; margin: 12px; padding: 8px 10px; border: 1px solid var(--border, #444); border-radius: 6px; }
.library-search input { flex: 1; background: transparent; border: 0; color: inherit; outline: none; font-size: 13px; }
.library-list { flex: 1; overflow-y: auto; padding: 0 12px 12px; }
.library-empty { opacity: 0.6; font-size: 13px; padding: 12px; }
.library-item { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px; border: 1px solid var(--border, #2c2c2c); border-radius: 8px; margin-bottom: 8px; }
.library-item-main { flex: 1; display: flex; align-items: center; gap: 8px; background: none; border: 0; color: inherit; cursor: pointer; text-align: left; }
.library-item-text { display: flex; flex-direction: column; gap: 2px; }
.library-item-title { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.library-item-meta { font-size: 11px; opacity: 0.6; }
.library-item-actions { display: flex; gap: 2px; }
.lib-action { background: none; border: 0; color: inherit; opacity: 0.75; cursor: pointer; padding: 4px; border-radius: 4px; }
.lib-action:hover { opacity: 1; background: rgba(255,255,255,0.08); }
.lib-action.danger:hover { color: #f87171; }
```

- [ ] **Step 3: Verify lint + build**

Run: `cd frontend && npm run lint && npm run build`
Expected: no new lint errors; build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/reports/ReportLibraryDrawer.jsx frontend/src/components/reports/ReportLibraryDrawer.css
git commit -m "feat(reports): add ReportLibraryDrawer with search + reopen"
```

---

### Task 7: Frontend — `ReportStudio` shell + route swap

**Files:**
- Create: `frontend/src/components/reports/ReportStudio.jsx`
- Create: `frontend/src/components/reports/ReportStudio.css`
- Modify: `frontend/src/App.jsx` (swap the reports route import + element)
- Keep: `frontend/src/components/reports/ReportBuilder.jsx` unchanged on disk (no longer routed; can be removed in a later cleanup).

**Interfaces:**
- Consumes: `ReportRail`, `ReportPreviewPane`, `ReportLibraryDrawer`, `ShareModal`, and existing apiService functions (`getReportTypes`, `getScriptMetadata`, `getScriptReports`, `getFilterOptions`, `getFilterPresets`, `saveFilterPreset`, `deleteFilterPreset`, `generateReport`, `deleteReport`, `getReportPrintUrl`, `previewReportHtml`).
- Produces: the routed Report Studio page at `scripts/:scriptId/reports`.

- [ ] **Step 1: Create the shell component**

Create `frontend/src/components/reports/ReportStudio.jsx`:

```jsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { FileText, LibraryBig, Plus, Download, Printer, Share2 } from 'lucide-react';
import { Spinner, Button } from '../ui';
import { useToast } from '../../context/ToastContext';
import { useConfirmDialog } from '../../context/ConfirmDialogContext';
import { useScript } from '../../context/ScriptContext';
import { useSubscription } from '../../hooks/useSubscription';
import { SubscriptionGate } from '../subscription';
import PageHeader from '../layout/PageHeader';
import {
    getReportTypes, generateReport, getScriptReports, deleteReport,
    getReportPrintUrl, getScriptMetadata, getFilterOptions, getFilterPresets,
    saveFilterPreset, deleteFilterPreset, previewReportHtml,
} from '../../services/apiService';
import ReportRail from './ReportRail';
import ReportPreviewPane from './ReportPreviewPane';
import ReportLibraryDrawer from './ReportLibraryDrawer';
import ShareModal from './ShareModal';
import './ReportStudio.css';

const EMPTY_FILTERS = {
    locations: [], location_parents: [], characters: [], int_ext: [], time_of_day: [],
    story_days: [], scene_numbers: [], scene_range: { from: '', to: '' },
    timeline_codes: [], categories: [], group_by: 'scene_number',
};

// Pure helper — strip empty values from any filters object. Module scope so it is
// stable across renders (no exhaustive-deps churn in the callbacks that use it).
const computeActiveFilters = (f) => {
    const active = {};
    if (f.locations?.length) active.locations = f.locations;
    if (f.location_parents?.length) active.location_parents = f.location_parents;
    if (f.characters?.length) active.characters = f.characters;
    if (f.int_ext?.length) active.int_ext = f.int_ext;
    if (f.time_of_day?.length) active.time_of_day = f.time_of_day;
    if (f.story_days?.length) active.story_days = f.story_days;
    if (f.scene_numbers?.length) active.scene_numbers = f.scene_numbers;
    if (f.scene_range?.from || f.scene_range?.to) active.scene_range = f.scene_range;
    if (f.timeline_codes?.length) active.timeline_codes = f.timeline_codes;
    return Object.keys(active).length > 0 ? active : null;
};

const ReportStudio = () => {
    const { scriptId } = useParams();
    const toast = useToast();
    const { confirm } = useConfirmDialog();
    const { setScript } = useScript();
    const { canAccess } = useSubscription();

    const [reportTypes, setReportTypes] = useState({});
    const [selectedType, setSelectedType] = useState('scene_breakdown');
    const [customTitle, setCustomTitle] = useState('');
    const [existingReports, setExistingReports] = useState([]);
    const [activeReport, setActiveReport] = useState(null);
    const [loading, setLoading] = useState(true);

    const [filterOptions, setFilterOptions] = useState(null);
    const [filterPresets, setFilterPresets] = useState([]);
    const [filters, setFilters] = useState(EMPTY_FILTERS);

    const [previewHtml, setPreviewHtml] = useState('');
    const [previewCounts, setPreviewCounts] = useState({ match: null, total: null });
    const [previewLoading, setPreviewLoading] = useState(false);
    const [previewError, setPreviewError] = useState(null);

    const [libraryOpen, setLibraryOpen] = useState(false);
    const [shareModalReport, setShareModalReport] = useState(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [previewNonce, setPreviewNonce] = useState(0);

    // Refs mirror the latest config so the (stable) preview fn never reads stale state,
    // even when called synchronously right after setState (e.g. Library reopen).
    const filtersRef = useRef(filters);
    const typeRef = useRef(selectedType);
    const titleRef = useRef(customTitle);
    filtersRef.current = filters;
    typeRef.current = selectedType;
    titleRef.current = customTitle;

    // Single refresh trigger: bump the nonce; the effect below runs the render.
    const triggerPreview = useCallback(() => setPreviewNonce((n) => n + 1), []);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                const typesRes = await getReportTypes();
                if (typesRes.success) setReportTypes(typesRes.report_types);
                try {
                    const metadata = await getScriptMetadata(scriptId);
                    setScript({ id: scriptId, title: metadata?.title || metadata?.script_name });
                } catch (e) { console.warn('metadata', e); }
                const reportsRes = await getScriptReports(scriptId);
                if (reportsRes.success) setExistingReports(reportsRes.reports);
                try {
                    const filterRes = await getFilterOptions(scriptId);
                    if (filterRes.success) setFilterOptions(filterRes.options);
                } catch (e) { console.warn('filter options', e); }
                try {
                    const presetsRes = await getFilterPresets(scriptId);
                    if (presetsRes.success) setFilterPresets(presetsRes.presets);
                } catch (e) { console.warn('presets', e); }
            } catch (error) {
                toast.error('Error', 'Failed to load report data');
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [scriptId]);

    const buildActiveFilters = useCallback(() => computeActiveFilters(filters), [filters]);

    // Stable ([] deps): always reads the latest config via refs, so it is safe to
    // fire from the button, from onSelectType, or synchronously after a reopen.
    const handleUpdatePreview = useCallback(async () => {
        const f = filtersRef.current;
        setPreviewLoading(true);
        setPreviewError(null);
        try {
            const activeFilters = computeActiveFilters(f);
            const groupBy = f.group_by !== 'scene_number' ? f.group_by : null;
            const categories = f.categories?.length > 0 ? f.categories : null;
            const res = await previewReportHtml(scriptId, typeRef.current, activeFilters, groupBy, categories, titleRef.current || null);
            if (res.success) {
                setPreviewHtml(res.html);
                setPreviewCounts({ match: res.match_count, total: res.total_count });
            } else {
                setPreviewError(res.error || 'Failed to render preview');
            }
        } catch (e) {
            setPreviewError(e.message || 'Failed to render preview');
        } finally {
            setPreviewLoading(false);
        }
    }, [scriptId]);

    // The one automatic refresh path: runs whenever triggerPreview() bumps the nonce.
    // Refs are already updated (set during render, before this post-commit effect), so
    // handleUpdatePreview reads the current type/filters/title.
    useEffect(() => {
        if (!loading && previewNonce > 0) handleUpdatePreview();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [previewNonce]);

    const handleGenerate = async () => {
        setIsGenerating(true);
        try {
            const activeFilters = buildActiveFilters();
            const groupBy = filters.group_by !== 'scene_number' ? filters.group_by : null;
            const categories = filters.categories?.length > 0 ? filters.categories : null;
            const res = await generateReport(scriptId, selectedType, customTitle || null, null, activeFilters, groupBy, categories);
            if (res.success) {
                toast.success('Report Generated', 'Your report is ready!');
                setExistingReports((prev) => [res.report, ...prev]);
                setActiveReport(res.report);
            } else {
                toast.error('Error', res.error || 'Failed to generate report');
            }
        } catch (error) {
            toast.error('Error', error.message || 'Failed to generate report');
        } finally {
            setIsGenerating(false);
        }
    };

    const handleReopen = (report) => {
        setSelectedType(report.report_type || 'scene_breakdown');
        const cfg = report.config || {};
        setFilters({
            ...EMPTY_FILTERS,
            ...(cfg.filters || {}),
            categories: cfg.categories || [],
            group_by: cfg.group_by || 'scene_number',
        });
        setCustomTitle(report.title || '');
        setActiveReport(report);
        setLibraryOpen(false);
        // Refs update during the re-render these setStates cause; the nonce effect then
        // reads the restored config. Works for both same-type and cross-type reopens.
        triggerPreview();
    };

    const handleDownload = (report) => window.open(getReportPrintUrl(report.id), '_blank');
    const handlePrint = (report) => window.open(getReportPrintUrl(report.id), '_blank');

    const handleDelete = async (report) => {
        const ok = await confirm({ title: 'Delete Report?', message: 'This report will be permanently deleted.', variant: 'danger' });
        if (!ok) return;
        try {
            await deleteReport(report.id);
            setExistingReports((prev) => prev.filter((r) => r.id !== report.id));
            if (activeReport?.id === report.id) setActiveReport(null);
            toast.success('Deleted', 'Report deleted');
        } catch (error) {
            toast.error('Error', 'Failed to delete report');
        }
    };

    const filterPanelProps = {
        filterOptions,
        filters,
        onFilterChange: setFilters,
        onToggleCollapse: () => {},
        presets: filterPresets,
        onLoadPreset: (preset) => {
            setFilters({
                ...EMPTY_FILTERS,
                ...(preset.filters || {}),
                categories: preset.categories || [],
                group_by: preset.group_by || 'scene_number',
            });
            toast.success('Preset Loaded', `Applied "${preset.name}"`);
        },
        onSavePreset: async (name) => {
            try {
                const res = await saveFilterPreset(scriptId, {
                    name, filters: buildActiveFilters() || {},
                    categories: filters.categories || [], group_by: filters.group_by || 'scene_number',
                });
                if (res.success) {
                    setFilterPresets((prev) => [...prev, res.preset]);
                    toast.success('Preset Saved', `"${name}" saved`);
                }
            } catch (e) { toast.error('Error', 'Failed to save preset'); }
        },
        onDeletePreset: async (presetId) => {
            try {
                await deleteFilterPreset(presetId);
                setFilterPresets((prev) => prev.filter((p) => p.id !== presetId));
                toast.success('Deleted', 'Preset deleted');
            } catch (e) { toast.error('Error', 'Failed to delete preset'); }
        },
    };

    if (loading) {
        return (
            <div className="report-studio-loading">
                <Spinner size={32} />
                <p>Loading report studio…</p>
            </div>
        );
    }

    if (!canAccess('reports')) {
        return (
            <div className="report-studio page-container">
                <PageHeader icon={<FileText size={24} />} title="Reports" />
                <SubscriptionGate feature="reports" showBlur blurAmount={8}>
                    <div className="report-studio-preview">
                        <p>Generate professional reports including scene breakdowns, day-out-of-days, location reports, and more.</p>
                    </div>
                </SubscriptionGate>
            </div>
        );
    }

    const hasActive = Boolean(activeReport);

    return (
        <div className="report-studio">
            <div className="studio-toolbar">
                <div className="studio-title"><FileText size={18} /> Report Studio</div>
                <div className="studio-actions">
                    <Button variant="secondary" onClick={() => setLibraryOpen(true)}>
                        <LibraryBig size={16} /> Library
                    </Button>
                    <Button variant="primary" onClick={handleGenerate} disabled={isGenerating}>
                        {isGenerating ? <Spinner size={16} /> : <Plus size={16} />} Generate
                    </Button>
                    <button className="studio-icon-btn" disabled={!hasActive} onClick={() => hasActive && handleDownload(activeReport)} title="Download"><Download size={16} /></button>
                    <button className="studio-icon-btn" disabled={!hasActive} onClick={() => hasActive && handlePrint(activeReport)} title="Print"><Printer size={16} /></button>
                    <button className="studio-icon-btn" disabled={!hasActive} onClick={() => hasActive && setShareModalReport(activeReport)} title="Share"><Share2 size={16} /></button>
                </div>
            </div>

            <div className="studio-body">
                <div className="studio-rail">
                    <ReportRail
                        reportTypes={reportTypes}
                        selectedType={selectedType}
                        onSelectType={(t) => { setSelectedType(t); triggerPreview(); }}
                        customTitle={customTitle}
                        onTitleChange={setCustomTitle}
                        filterPanelProps={filterPanelProps}
                    />
                </div>
                <div className="studio-preview">
                    <ReportPreviewPane
                        html={previewHtml}
                        matchCount={previewCounts.match}
                        totalCount={previewCounts.total}
                        loading={previewLoading}
                        error={previewError}
                        onRefresh={triggerPreview}
                    />
                </div>
            </div>

            <ReportLibraryDrawer
                open={libraryOpen}
                reports={existingReports}
                onClose={() => setLibraryOpen(false)}
                onReopen={handleReopen}
                onDownload={handleDownload}
                onShare={(report) => setShareModalReport(report)}
                onDelete={handleDelete}
            />

            {shareModalReport && (
                <ShareModal
                    report={shareModalReport}
                    onClose={() => setShareModalReport(null)}
                    onUpdate={(updated) => {
                        setExistingReports((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
                        if (activeReport?.id === updated.id) setActiveReport(updated);
                    }}
                />
            )}
        </div>
    );
};

export default ReportStudio;
```

- [ ] **Step 2: Create the stylesheet**

Create `frontend/src/components/reports/ReportStudio.css`:

```css
.report-studio { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.report-studio-loading { display: flex; flex-direction: column; gap: 12px; align-items: center; justify-content: center; padding: 80px 0; }
.studio-toolbar { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; border-bottom: 1px solid var(--border, #2a2a2a); }
.studio-title { display: flex; align-items: center; gap: 8px; font-weight: 700; }
.studio-actions { display: flex; align-items: center; gap: 6px; }
.studio-icon-btn { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border: 1px solid var(--border, #444); border-radius: 6px; background: transparent; color: inherit; cursor: pointer; }
.studio-icon-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.studio-body { flex: 1; display: grid; grid-template-columns: minmax(280px, 34%) 1fr; min-height: 0; }
.studio-rail { border-right: 1px solid var(--border, #2a2a2a); min-height: 0; overflow: hidden; }
.studio-preview { min-height: 0; }
@media (max-width: 900px) {
    .studio-body { grid-template-columns: 1fr; }
    .studio-rail { border-right: 0; border-bottom: 1px solid var(--border, #2a2a2a); }
}
```

- [ ] **Step 3: Swap the route in App.jsx**

In `frontend/src/App.jsx`, change the ReportBuilder import (line ~31):

```jsx
// Before:
// import ReportBuilder from './components/reports/ReportBuilder';
// After:
import ReportStudio from './components/reports/ReportStudio';
```

And the route element (line ~67):

```jsx
// Before:
// <Route path="scripts/:scriptId/reports" element={<ReportBuilder />} />
// After:
<Route path="scripts/:scriptId/reports" element={<ReportStudio />} />
```

- [ ] **Step 4: Verify lint + build**

Run: `cd frontend && npm run lint && npm run build`
Expected: no new lint errors; build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/reports/ReportStudio.jsx frontend/src/components/reports/ReportStudio.css frontend/src/App.jsx
git commit -m "feat(reports): wire ReportStudio shell + swap reports route"
```

---

### Task 8: Manual end-to-end verification (desktop)

**Files:** none (verification only).

**Interfaces:** exercises the full flow against a running dev stack.

- [ ] **Step 1: Start the stack**

Run backend: `cd backend && python3 app.py` (needs env vars per CLAUDE.md).
Run frontend: `cd frontend && npm run dev` (opens on :5173).

- [ ] **Step 2: Exercise the iterate loop**

Navigate to a script's Reports page and verify, one at a time:
1. Left rail shows the report-type icon list; clicking a type refreshes the preview automatically.
2. Editing filters + clicking **Update Preview** re-renders the pane; the status line shows "N of M scenes match" and N drops as filters narrow.
3. **Generate** creates a report, shows a toast, and enables the Download/Print/Share toolbar icons.
4. **Library** opens the drawer; search filters the list; clicking a report restores its type + filters into the rail and refreshes the preview; Download/Share/Delete work.
5. Empty state (before first preview) and loading spinner appear as designed.

Expected: all five behave as described; no console errors.

- [ ] **Step 3: Commit (if any fixes were needed)**

```bash
git add -A
git commit -m "fix(reports): address issues found in Report Studio manual verification"
```

---

## Notes for the implementer

- `ReportFilterPanel` is reused as-is; its `filters` state shape is exactly the `EMPTY_FILTERS` object. Do not fork it.
- The preview is intentionally manual-refresh except on report-type change. Do not add debounced auto-refresh (out of scope).
- `getReportPrintUrl(reportId)` opens the server-rendered printable HTML (used for both Download and Print here, matching the current app behavior). PDF download via `getReportPdfUrl` can be substituted later if desired.
- `ReportBuilder.jsx` is left on disk but unrouted; remove it in a follow-up once the Studio is confirmed in production.
