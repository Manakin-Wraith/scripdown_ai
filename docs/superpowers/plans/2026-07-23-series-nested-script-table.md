# Series/Season Grouping in My Scripts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Group scripts by series/season in the My Scripts table (nested, collapsible), and let users jump straight into uploading the next episode of a season without re-navigating the full series-picker flow.

**Architecture:** A backend join enriches `GET /api/scripts` with series/season names (currently only IDs are returned). `ScriptTable.jsx` buckets the enriched script list into series → season → episode groups client-side and renders them as collapsible header rows (state persisted in `localStorage`) above the existing flat rows for unassigned scripts. A season group header's "+ Add episode" action deep-links to `/upload?seriesId=..&seasonId=..`, which `ScriptUpload.jsx` reads to pre-fill `SeriesPicker` with the target season and the next sequential episode number — fully editable, never locked in.

**Tech Stack:** Flask + supabase-py (backend), React 18 + react-router-dom v6 (frontend), pytest (backend tests only — no frontend test runner exists in this repo).

## Global Constraints

- Frontend has no test runner (`npm test` doesn't exist) — frontend tasks are verified via `npm run build` plus manual browser checks, not automated tests. `npm run lint` is broken repo-wide; do not gate on it.
- Backend tasks are verified via `pytest tests/<file> -v`.
- No database migration needed — `series`/`seasons` tables and `scripts.season_id`/`episode_number` already exist (migration `045_series_seasons.sql`).
- Do not modify `SeriesAssignmentModal.jsx` or the per-episode row reassignment behavior — out of scope per the design doc.
- Do not touch Board/Scheduling/Reporting code — out of scope per the design doc.

---

### Task 1: Backend — join series/season names into `GET /api/scripts`

**Files:**
- Modify: `backend/routes/supabase_routes.py` (add helper function near the top of the file, call it from `get_scripts`, lines 90-202)
- Test: `backend/tests/test_get_scripts_series_info.py` (new)

**Interfaces:**
- Produces: each script dict returned by `GET /api/scripts` gains four new keys — `series_id` (str|None), `series_title` (str|None), `season_number` (int|None), `season_title` (str|None) — alongside the existing `season_id`/`episode_number`. Later tasks (frontend grouping) consume these exact key names.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_get_scripts_series_info.py`:

```python
"""GET /api/scripts: series/season join enrichment (season_id -> seasons -> series)."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.supabase_routes as sr


class FakeQuery:
    """Minimal chainable supabase-py stand-in supporting select/eq/is_/in_/single/execute."""

    def __init__(self, rows):
        self._filtered = list(rows)
        self._single = False

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._filtered = [r for r in self._filtered if r.get(col) == val]
        return self

    def is_(self, col, _val):
        # Only ever called as .is_('user_id', 'null') in this codebase.
        self._filtered = [r for r in self._filtered if r.get(col) is None]
        return self

    def in_(self, col, values):
        values = set(values)
        self._filtered = [r for r in self._filtered if r.get(col) in values]
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        if self._single:
            return SimpleNamespace(data=self._filtered[0] if self._filtered else None)
        return SimpleNamespace(data=self._filtered)


class FakeSupabase:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        return FakeQuery(self.store.get(name, []))


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def _store(scripts=None, seasons=None, series=None):
    return {
        "scripts": scripts or [],
        "script_members": [],
        "seasons": seasons or [],
        "series": series or [],
        "scenes": [],
    }


def test_get_scripts_attaches_series_and_season_info(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    store = _store(
        scripts=[
            {
                "id": "ep1", "user_id": "u1", "title": "Pilot",
                "created_at": "2026-07-20T00:00:00Z",
                "season_id": "sea1", "episode_number": 1,
            },
        ],
        seasons=[{"id": "sea1", "series_id": "ser1", "season_number": 1, "title": None}],
        series=[{"id": "ser1", "title": "Die Testament"}],
    )
    monkeypatch.setattr(sr, "supabase", FakeSupabase(store))

    resp = _client().get("/api/scripts")

    assert resp.status_code == 200
    script = resp.get_json()["scripts"][0]
    assert script["series_id"] == "ser1"
    assert script["series_title"] == "Die Testament"
    assert script["season_number"] == 1
    assert script["season_title"] is None


def test_get_scripts_unassigned_script_has_null_series_fields(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    store = _store(
        scripts=[
            {
                "id": "s1", "user_id": "u1", "title": "Standalone",
                "created_at": "2026-07-20T00:00:00Z",
                "season_id": None, "episode_number": None,
            },
        ],
    )
    monkeypatch.setattr(sr, "supabase", FakeSupabase(store))

    resp = _client().get("/api/scripts")

    assert resp.status_code == 200
    script = resp.get_json()["scripts"][0]
    assert script["series_id"] is None
    assert script["series_title"] is None
    assert script["season_number"] is None
    assert script["season_title"] is None


def test_get_scripts_season_with_titled_season_and_multiple_episodes(monkeypatch):
    """Two episodes in the same titled season both resolve the same series/season names."""
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    store = _store(
        scripts=[
            {
                "id": "ep1", "user_id": "u1", "title": "Ep 1",
                "created_at": "2026-07-20T00:00:00Z",
                "season_id": "sea1", "episode_number": 1,
            },
            {
                "id": "ep2", "user_id": "u1", "title": "Ep 2",
                "created_at": "2026-07-21T00:00:00Z",
                "season_id": "sea1", "episode_number": 2,
            },
        ],
        seasons=[{"id": "sea1", "series_id": "ser1", "season_number": 1, "title": "The Beginning"}],
        series=[{"id": "ser1", "title": "Die Testament"}],
    )
    monkeypatch.setattr(sr, "supabase", FakeSupabase(store))

    resp = _client().get("/api/scripts")

    assert resp.status_code == 200
    scripts_by_id = {s["id"]: s for s in resp.get_json()["scripts"]}
    for script_id in ("ep1", "ep2"):
        assert scripts_by_id[script_id]["series_title"] == "Die Testament"
        assert scripts_by_id[script_id]["season_title"] == "The Beginning"
        assert scripts_by_id[script_id]["season_number"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && pytest tests/test_get_scripts_series_info.py -v`
Expected: FAIL — `KeyError: 'series_id'` (or assertion `None != 'ser1'`), since the endpoint doesn't return these fields yet.

- [ ] **Step 3: Add the join helper and wire it into `get_scripts`**

In `backend/routes/supabase_routes.py`, add this function directly above the `@supabase_bp.route('/api/scripts', methods=['GET'])` line (currently line 90):

```python
def _attach_series_info(scripts):
    """Enrich each script dict with series_id/series_title/season_number/season_title
    by joining season_id -> seasons -> series. Scripts with no season_id (the common
    case) get all four keys set to None, matching the existing null pattern used for
    season_id/episode_number on unassigned scripts."""
    season_ids = {s['season_id'] for s in scripts if s.get('season_id')}
    season_map = {}
    if season_ids and supabase:
        seasons_result = supabase.table('seasons').select(
            'id, series_id, season_number, title'
        ).in_('id', list(season_ids)).execute()
        for season in seasons_result.data or []:
            season_map[season['id']] = season

    series_ids = {season['series_id'] for season in season_map.values() if season.get('series_id')}
    series_map = {}
    if series_ids and supabase:
        series_result = supabase.table('series').select('id, title').in_('id', list(series_ids)).execute()
        for series in series_result.data or []:
            series_map[series['id']] = series

    for script in scripts:
        season = season_map.get(script.get('season_id'))
        if season:
            series = series_map.get(season.get('series_id'))
            script['series_id'] = season.get('series_id')
            script['series_title'] = series.get('title') if series else None
            script['season_number'] = season.get('season_number')
            script['season_title'] = season.get('title')
        else:
            script['series_id'] = None
            script['series_title'] = None
            script['season_number'] = None
            script['season_title'] = None

    return scripts
```

Then, in `get_scripts`, find this line (currently line 195-196):

```python
        # Sort by created_at descending
        scripts.sort(key=lambda x: x['created_at'], reverse=True)
```

Change it to:

```python
        scripts = _attach_series_info(scripts)

        # Sort by created_at descending
        scripts.sort(key=lambda x: x['created_at'], reverse=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && pytest tests/test_get_scripts_series_info.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full backend suite to check for regressions**

Run: `cd backend && source venv/bin/activate && pytest tests/ -v 2>&1 | tail -30`
Expected: All tests pass (no regressions from the `get_scripts` change).

- [ ] **Step 6: Commit**

```bash
git add backend/routes/supabase_routes.py backend/tests/test_get_scripts_series_info.py
git commit -m "$(cat <<'EOF'
feat(scripts): join series/season names into GET /api/scripts

Enables grouping scripts by series/season in the frontend without
per-script or per-series follow-up requests.
EOF
)"
```

---

### Task 2: Frontend — group scripts by series/season in `ScriptTable.jsx`

**Files:**
- Modify: `frontend/src/components/scripts/ScriptTable.jsx` (full rewrite of the render logic)
- Modify: `frontend/src/components/scripts/ScriptTable.css` (append new styles)

**Interfaces:**
- Consumes: `series_id`, `series_title`, `season_number`, `season_title` fields on each `script` object (Task 1's output); `onView`, `onDelete`, `onRename`, `onUpdateWriter`, `onAssignSeries`, `locationHealthCounts` props (unchanged from today).
- Produces: no new props exposed to `ScriptLibrary.jsx` — this task is self-contained within `ScriptTable.jsx`. Navigates to `/series/:seriesId` (View series link) and `/upload?seriesId=<id>&seasonId=<id>` (Add episode link) via `useNavigate`. Task 4 (`ScriptUpload.jsx`) consumes that `?seriesId=&seasonId=` query-string shape.

- [ ] **Step 1: Replace `ScriptTable.jsx` with the grouped-rendering version**

Replace the full contents of `frontend/src/components/scripts/ScriptTable.jsx` with:

```jsx
import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Trash2,
    ChevronDown,
    ChevronUp,
    ChevronRight,
    Sparkles,
    Pencil,
    Check,
    X,
    Layers,
    Plus,
    ExternalLink
} from 'lucide-react';
import AnalysisStatusBadge from '../common/AnalysisStatusBadge';
import './ScriptTable.css';

const EXPANDED_GROUPS_STORAGE_KEY = 'scriptTable.expandedGroups';

function loadExpandedGroups() {
    try {
        const raw = localStorage.getItem(EXPANDED_GROUPS_STORAGE_KEY);
        return raw ? JSON.parse(raw) : {};
    } catch {
        return {};
    }
}

function saveExpandedGroups(state) {
    try {
        localStorage.setItem(EXPANDED_GROUPS_STORAGE_KEY, JSON.stringify(state));
    } catch {
        // best-effort only (e.g. private browsing may block localStorage)
    }
}

function groupScripts(scripts) {
    const seriesMap = new Map();

    for (const script of scripts) {
        if (!script.series_id) continue;
        if (!seriesMap.has(script.series_id)) {
            seriesMap.set(script.series_id, {
                id: script.series_id,
                title: script.series_title,
                seasons: new Map(),
            });
        }
        const series = seriesMap.get(script.series_id);
        if (!series.seasons.has(script.season_id)) {
            series.seasons.set(script.season_id, {
                id: script.season_id,
                seasonNumber: script.season_number,
                title: script.season_title,
                episodes: [],
            });
        }
        series.seasons.get(script.season_id).episodes.push(script);
    }

    return Array.from(seriesMap.values())
        .sort((a, b) => (a.title || '').localeCompare(b.title || ''))
        .map((series) => ({
            ...series,
            seasons: Array.from(series.seasons.values())
                .sort((a, b) => (a.seasonNumber || 0) - (b.seasonNumber || 0))
                .map((season) => ({
                    ...season,
                    episodes: [...season.episodes].sort(
                        (a, b) => (a.episode_number || 0) - (b.episode_number || 0)
                    ),
                })),
        }));
}

const ScriptTable = ({ scripts, onView, onDelete, onRename, onUpdateWriter, onAssignSeries, locationHealthCounts = {} }) => {
    const navigate = useNavigate();
    const [sortConfig, setSortConfig] = useState({ key: 'upload_date', direction: 'desc' });
    const [editingId, setEditingId] = useState(null);
    const [editingField, setEditingField] = useState(null); // 'name' or 'writer'
    const [editValue, setEditValue] = useState('');
    const [expandedGroups, setExpandedGroups] = useState(loadExpandedGroups);
    const inputRef = useRef(null);

    useEffect(() => {
        if (editingId && inputRef.current) {
            inputRef.current.focus();
            inputRef.current.select();
        }
    }, [editingId, editingField]);

    const toggleGroup = (id) => {
        setExpandedGroups((prev) => {
            const next = { ...prev, [id]: !prev[id] };
            saveExpandedGroups(next);
            return next;
        });
    };

    const startEditing = (e, script, field) => {
        e.stopPropagation();
        setEditingId(script.script_id);
        setEditingField(field);
        setEditValue(field === 'writer' ? (script.writer_name || '') : (script.script_name || ''));
    };

    const cancelEditing = (e) => {
        if (e) e.stopPropagation();
        setEditingId(null);
        setEditingField(null);
        setEditValue('');
    };

    const saveEdit = async (e, scriptId) => {
        if (e) e.stopPropagation();
        const trimmed = editValue.trim();
        if (editingField === 'name') {
            if (!trimmed) return cancelEditing();
            if (onRename) await onRename(scriptId, trimmed);
        } else if (editingField === 'writer') {
            if (onUpdateWriter) await onUpdateWriter(scriptId, trimmed || null);
        }
        setEditingId(null);
        setEditingField(null);
        setEditValue('');
    };

    const handleKeyDown = (e, scriptId) => {
        if (e.key === 'Enter') {
            saveEdit(e, scriptId);
        } else if (e.key === 'Escape') {
            cancelEditing(e);
        }
    };

    const handleSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    const sortedUngrouped = scripts
        .filter((s) => !s.series_id)
        .sort((a, b) => {
            if (a[sortConfig.key] < b[sortConfig.key]) {
                return sortConfig.direction === 'asc' ? -1 : 1;
            }
            if (a[sortConfig.key] > b[sortConfig.key]) {
                return sortConfig.direction === 'asc' ? 1 : -1;
            }
            return 0;
        });

    const seriesGroups = groupScripts(scripts);

    const SortIcon = ({ columnKey }) => {
        if (sortConfig.key !== columnKey) return null;
        return sortConfig.direction === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />;
    };

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    };

    const renderScriptRow = (script, indent = 0) => (
        <tr
            key={script.script_id}
            className="clickable-row"
            onClick={() => onView(script.script_id)}
        >
            <td className="name-cell" style={indent ? { paddingLeft: `${1.5 + indent}rem` } : undefined}>
                {editingId === script.script_id && editingField === 'name' ? (
                    <div className="name-edit-row">
                        <input
                            ref={inputRef}
                            className="name-edit-input"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onKeyDown={(e) => handleKeyDown(e, script.script_id)}
                            onClick={(e) => e.stopPropagation()}
                        />
                        <button className="name-edit-btn save" onClick={(e) => saveEdit(e, script.script_id)} title="Save"><Check size={14} /></button>
                        <button className="name-edit-btn cancel" onClick={cancelEditing} title="Cancel"><X size={14} /></button>
                    </div>
                ) : (
                    <div className="script-name-row">
                        {indent > 0 && script.episode_number != null && (
                            <span className="episode-badge">Ep {script.episode_number}</span>
                        )}
                        <div className="script-name">{script.script_name}</div>
                        {locationHealthCounts[script.script_id] > 0 && (
                            <span
                                className="location-health-badge"
                                title={`${locationHealthCounts[script.script_id]} location${locationHealthCounts[script.script_id] === 1 ? '' : 's'} need review`}
                            >
                                ⚠ {locationHealthCounts[script.script_id]}
                            </span>
                        )}
                        <button
                            className="rename-btn"
                            onClick={(e) => startEditing(e, script, 'name')}
                            title="Rename script"
                        >
                            <Pencil size={13} />
                        </button>
                    </div>
                )}
            </td>
            <td className="writer-cell">
                {editingId === script.script_id && editingField === 'writer' ? (
                    <div className="name-edit-row">
                        <input
                            ref={inputRef}
                            className="name-edit-input writer-edit-input"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onKeyDown={(e) => handleKeyDown(e, script.script_id)}
                            onClick={(e) => e.stopPropagation()}
                            placeholder="Writer name"
                        />
                        <button className="name-edit-btn save" onClick={(e) => saveEdit(e, script.script_id)} title="Save"><Check size={14} /></button>
                        <button className="name-edit-btn cancel" onClick={cancelEditing} title="Cancel"><X size={14} /></button>
                    </div>
                ) : (
                    <div className="script-name-row">
                        <span className="writer-name">{script.writer_name || '—'}</span>
                        <button
                            className="rename-btn"
                            onClick={(e) => startEditing(e, script, 'writer')}
                            title="Edit writer"
                        >
                            <Pencil size={13} />
                        </button>
                    </div>
                )}
            </td>
            <td className="date-cell">
                {formatDate(script.upload_date)}
            </td>
            <td className="scenes-cell">
                <span className="scene-count-badge">{script.scene_count}</span>
            </td>
            <td className="analysis-cell">
                <span className="analysis-progress">
                    {script.analyzed_scenes || 0}/{script.scene_count || 0} scenes
                </span>
            </td>
            <td className="actions-cell">
                {onAssignSeries && (
                    <button
                        className="action-icon-btn"
                        onClick={(e) => {
                            e.stopPropagation();
                            onAssignSeries(script);
                        }}
                        title={script.episode_number ? `Episode ${script.episode_number} of a series` : 'Assign to a series'}
                    >
                        <Layers size={18} />
                    </button>
                )}
                <button
                    className="action-icon-btn danger"
                    onClick={(e) => {
                        e.stopPropagation();
                        onDelete(script.script_id, script.script_name);
                    }}
                    title="Delete Script"
                >
                    <Trash2 size={18} />
                </button>
            </td>
        </tr>
    );

    return (
        <div className="table-container">
            <table className="script-table">
                <thead>
                    <tr>
                        <th onClick={() => handleSort('script_name')}>
                            <div className="th-content">Script Name <SortIcon columnKey="script_name" /></div>
                        </th>
                        <th onClick={() => handleSort('writer_name')}>
                            <div className="th-content">Writer <SortIcon columnKey="writer_name" /></div>
                        </th>
                        <th onClick={() => handleSort('upload_date')}>
                            <div className="th-content">Date Uploaded <SortIcon columnKey="upload_date" /></div>
                        </th>
                        <th onClick={() => handleSort('scene_count')}>
                            <div className="th-content">Scenes <SortIcon columnKey="scene_count" /></div>
                        </th>
                        <th>
                            <div className="th-content">
                                <Sparkles size={14} />
                                AI Analysis
                            </div>
                        </th>
                        <th className="actions-col">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {seriesGroups.map((series) => {
                        const seriesExpanded = !!expandedGroups[series.id];
                        const totalEpisodes = series.seasons.reduce((sum, s) => sum + s.episodes.length, 0);
                        return (
                            <React.Fragment key={series.id}>
                                <tr className="group-header-row series-header-row" onClick={() => toggleGroup(series.id)}>
                                    <td colSpan={6}>
                                        <div className="group-header-content">
                                            {seriesExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                            <span className="group-title">{series.title || 'Untitled Series'}</span>
                                            <span className="group-count">{totalEpisodes} episode{totalEpisodes === 1 ? '' : 's'}</span>
                                            <button
                                                className="group-header-link"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    navigate(`/series/${series.id}`);
                                                }}
                                                title="View series"
                                            >
                                                <ExternalLink size={14} />
                                                View series
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                                {seriesExpanded && series.seasons.map((season) => {
                                    const seasonExpanded = !!expandedGroups[season.id];
                                    return (
                                        <React.Fragment key={season.id}>
                                            <tr className="group-header-row season-header-row" onClick={() => toggleGroup(season.id)}>
                                                <td colSpan={6}>
                                                    <div className="group-header-content indent-1">
                                                        {seasonExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                                        <span className="group-title">{season.title || `Season ${season.seasonNumber}`}</span>
                                                        <span className="group-count">{season.episodes.length} episode{season.episodes.length === 1 ? '' : 's'}</span>
                                                        <button
                                                            className="group-header-link"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                navigate(`/upload?seriesId=${series.id}&seasonId=${season.id}`);
                                                            }}
                                                            title="Add the next episode to this season"
                                                        >
                                                            <Plus size={14} />
                                                            Add episode
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                            {seasonExpanded && season.episodes.map((script) => renderScriptRow(script, 2))}
                                        </React.Fragment>
                                    );
                                })}
                            </React.Fragment>
                        );
                    })}
                    {sortedUngrouped.map((script) => renderScriptRow(script, 0))}
                </tbody>
            </table>
        </div>
    );
};

export default ScriptTable;
```

- [ ] **Step 2: Append grouping styles to `ScriptTable.css`**

Append to the end of `frontend/src/components/scripts/ScriptTable.css`:

```css
/* Series/season grouping */
.group-header-row {
    cursor: pointer;
    background-color: var(--gray-800);
}

.group-header-row:hover {
    background-color: var(--gray-700);
}

.group-header-row td {
    padding: 0.75rem 1.5rem;
}

.group-header-content {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    color: var(--text-primary);
}

.group-header-content.indent-1 {
    padding-left: 1.5rem;
}

.group-title {
    font-weight: 600;
}

.group-count {
    color: var(--text-secondary);
    font-size: 0.85rem;
}

.group-header-link {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    margin-left: auto;
    background: none;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 4px 10px;
    color: var(--text-secondary);
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.2s;
}

.group-header-link:hover {
    background-color: var(--primary-alpha-10);
    color: var(--primary-500);
    border-color: var(--primary-alpha-30);
}

.episode-badge {
    display: inline-flex;
    align-items: center;
    background-color: var(--primary-alpha-15);
    color: var(--primary-500);
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.75rem;
    font-weight: 600;
    flex-shrink: 0;
}
```

- [ ] **Step 3: Verify the build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors (this repo has no frontend test runner — `npm run build` is the correctness gate for JS/JSX changes, and `npm run lint` is broken repo-wide, so don't gate on it).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/scripts/ScriptTable.jsx frontend/src/components/scripts/ScriptTable.css
git commit -m "$(cat <<'EOF'
feat(scripts): group My Scripts table by series/season

Nested, collapsible series -> season -> episode groups (collapsed by
default, state persisted in localStorage), with a "View series" link
to /series/:id and a season-level "Add episode" quick action.
Scripts with no series assignment keep rendering as flat, sortable
rows below the groups, unchanged from today.
EOF
)"
```

---

### Task 3: Frontend — `SeriesPicker.jsx` deep-link prefill support

**Files:**
- Modify: `frontend/src/components/series/SeriesPicker.jsx` (full rewrite)

**Interfaces:**
- Consumes: nothing new from other tasks.
- Produces: three new optional props — `initialSeriesId` (string|null), `initialSeasonId` (string|null), `initialEpisodeNumber` (number|null). When `initialSeasonId` is set, the picker mounts in `'existing'` mode with that series/season/episode-number pre-selected but fully editable. Task 4 (`ScriptUpload.jsx`) is the consumer of these props.

- [ ] **Step 1: Replace `SeriesPicker.jsx` with the prefill-aware version**

Replace the full contents of `frontend/src/components/series/SeriesPicker.jsx` with:

```jsx
import { useState, useEffect, useRef } from 'react';
import { listSeries, createSeries, listSeasons, createSeason } from '../../services/apiService';

/**
 * SeriesPicker - three-state picker for assigning a script to a series/season.
 *
 * States: 'none' (default, no assignment), 'existing' (pick a series +
 * season), 'new' (create a series, season defaults to 1).
 *
 * Calls onAssign(seasonId, episodeNumber) when the user has made a
 * complete selection; onAssign(null, null) for the 'none' state. The
 * caller (ScriptUpload or a reassignment surface) decides what to do with
 * that -- fire it immediately, or wait for a "confirm" action.
 *
 * autoFireNone (default true): in the upload flow, landing on 'none' means
 * "the script simply isn't part of a series" and should report that the
 * instant the user picks it (or on initial mount, since 'none' is the
 * default). In a reassignment context (SeriesAssignmentModal), 'none' means
 * "remove this script's existing assignment" -- a destructive action that
 * must NOT fire just because the modal opened with 'none' as the initial
 * mode. Pass autoFireNone={false} there; the 'none' panel then renders an
 * explicit "Remove from series" button instead of firing automatically.
 *
 * initialSeriesId/initialSeasonId/initialEpisodeNumber: optional deep-link
 * prefill (used by the "+ Add episode" action on a season's group header in
 * ScriptTable, which navigates to /upload?seriesId=..&seasonId=..). When
 * initialSeasonId is set, the picker starts in 'existing' mode with that
 * series/season/episode-number pre-selected -- fully editable, not locked
 * in, matching the "assignment is always overridable" principle used
 * elsewhere in this component.
 */
export default function SeriesPicker({
    onAssign,
    autoFireNone = true,
    initialSeriesId = null,
    initialSeasonId = null,
    initialEpisodeNumber = null,
}) {
    const [mode, setMode] = useState(initialSeasonId ? 'existing' : 'none');
    const [seriesList, setSeriesList] = useState([]);
    const [selectedSeriesId, setSelectedSeriesId] = useState(initialSeriesId || '');
    const [seasons, setSeasons] = useState([]);
    const [selectedSeasonId, setSelectedSeasonId] = useState('');
    const [episodeNumber, setEpisodeNumber] = useState(
        initialEpisodeNumber != null ? String(initialEpisodeNumber) : ''
    );
    const [newSeriesTitle, setNewSeriesTitle] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const appliedInitialSeason = useRef(false);

    useEffect(() => {
        if (mode !== 'existing') return;
        listSeries()
            .then((data) => setSeriesList(data.series || []))
            .catch((err) => setError(err.message || 'Failed to load series'));
    }, [mode]);

    useEffect(() => {
        const isFirstRunWithPrefill = !appliedInitialSeason.current && !!initialSeasonId;
        if (!isFirstRunWithPrefill) {
            setSelectedSeasonId('');
        }
        if (!selectedSeriesId) {
            setSeasons([]);
            return;
        }
        listSeasons(selectedSeriesId)
            .then((data) => {
                setSeasons(data.seasons || []);
                if (isFirstRunWithPrefill) {
                    setSelectedSeasonId(initialSeasonId);
                    appliedInitialSeason.current = true;
                }
            })
            .catch((err) => setError(err.message || 'Failed to load seasons'));
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedSeriesId]);

    useEffect(() => {
        if (mode === 'none' && autoFireNone) {
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

            {mode === 'none' && !autoFireNone && (
                <div className="series-picker-none">
                    <button type="button" onClick={() => onAssign(null, null)}>
                        Remove from series
                    </button>
                </div>
            )}

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

- [ ] **Step 2: Verify the build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/series/SeriesPicker.jsx
git commit -m "$(cat <<'EOF'
feat(series): support deep-link prefill in SeriesPicker

Adds optional initialSeriesId/initialSeasonId/initialEpisodeNumber
props so a caller can open the picker pre-set to a specific
series/season -- fully editable, not locked in. No behavior change
when the props are omitted (SeriesAssignmentModal's usage is
unaffected).
EOF
)"
```

---

### Task 4: Frontend — `?seriesId=&seasonId=` deep-link handling in `ScriptUpload.jsx`

**Files:**
- Modify: `frontend/src/components/script/ScriptUpload.jsx`

**Interfaces:**
- Consumes: `SeriesPicker`'s `initialSeriesId`/`initialSeasonId`/`initialEpisodeNumber` props (Task 3); `listEpisodes(seasonId)` from `apiService.js` (already exists, returns `{ episodes: [{ episode_number, ... }] }` ordered by episode number).
- Produces: reads `seriesId`/`seasonId` from the URL query string (the shape `ScriptTable.jsx`'s "Add episode" link produces, Task 2).

- [ ] **Step 1: Update imports**

In `frontend/src/components/script/ScriptUpload.jsx`, change line 2 from:

```jsx
import { useNavigate } from 'react-router-dom';
```

to:

```jsx
import { useNavigate, useSearchParams } from 'react-router-dom';
```

And change line 12 from:

```jsx
import { updateScriptSeason } from '../../services/apiService';
```

to:

```jsx
import { listEpisodes, updateScriptSeason } from '../../services/apiService';
```

- [ ] **Step 2: Add prefill state and the lookup effect**

Find this block (currently lines 26-38):

```jsx
const ScriptUpload = () => {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [uploadResult, setUploadResult] = useState(null);
    const [error, setError] = useState(null);
    const [isAiDetecting, setIsAiDetecting] = useState(false);
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    const [pendingSeasonAssignment, setPendingSeasonAssignment] = useState(null); // {seasonId, episodeNumber} | null
    const [uploadAttempt, setUploadAttempt] = useState(0);
    const navigate = useNavigate();
    const toast = useToast();
```

Replace it with:

```jsx
const ScriptUpload = () => {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [uploadResult, setUploadResult] = useState(null);
    const [error, setError] = useState(null);
    const [isAiDetecting, setIsAiDetecting] = useState(false);
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    const [pendingSeasonAssignment, setPendingSeasonAssignment] = useState(null); // {seasonId, episodeNumber} | null
    const [seriesPrefill, setSeriesPrefill] = useState(null); // {seriesId, seasonId, episodeNumber} | null
    const [uploadAttempt, setUploadAttempt] = useState(0);
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const toast = useToast();

    // Deep-link from ScriptTable's season "Add episode" action
    // (/upload?seriesId=..&seasonId=..): pre-fill the series picker with
    // that season and the next sequential episode number. Re-runs on every
    // reset (uploadAttempt change) so uploading several episodes in a row
    // from the same link keeps suggesting the correct next number.
    useEffect(() => {
        const seasonId = searchParams.get('seasonId');
        const seriesId = searchParams.get('seriesId');
        if (!seasonId) return;

        listEpisodes(seasonId)
            .then((data) => {
                const episodes = data.episodes || [];
                const maxEpisodeNumber = episodes.reduce(
                    (max, ep) => Math.max(max, ep.episode_number || 0),
                    0
                );
                const nextEpisodeNumber = maxEpisodeNumber + 1;
                setSeriesPrefill({ seriesId, seasonId, episodeNumber: nextEpisodeNumber });
                setPendingSeasonAssignment({ seasonId, episodeNumber: nextEpisodeNumber });
            })
            .catch((err) => {
                console.error('Failed to prefill season assignment:', err);
            });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [uploadAttempt]);
```

- [ ] **Step 3: Pass the prefill down to `SeriesPicker`**

Find this block (currently lines 213-222):

```jsx
                {!uploading && !uploadResult ? (
                    <>
                        <SeriesPicker
                            key={uploadAttempt}
                            onAssign={(seasonId, episodeNumber) =>
                                setPendingSeasonAssignment(seasonId ? { seasonId, episodeNumber } : null)
                            }
                        />
                        <DropZone onFileSelect={processFile} disabled={false} />
                    </>
```

Replace it with:

```jsx
                {!uploading && !uploadResult ? (
                    <>
                        <SeriesPicker
                            key={uploadAttempt}
                            initialSeriesId={seriesPrefill?.seriesId || null}
                            initialSeasonId={seriesPrefill?.seasonId || null}
                            initialEpisodeNumber={seriesPrefill?.episodeNumber || null}
                            onAssign={(seasonId, episodeNumber) =>
                                setPendingSeasonAssignment(seasonId ? { seasonId, episodeNumber } : null)
                            }
                        />
                        <DropZone onFileSelect={processFile} disabled={false} />
                    </>
```

- [ ] **Step 4: Verify the build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors. (`useEffect` is already imported on line 1 of this file — no import change needed there.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/script/ScriptUpload.jsx
git commit -m "$(cat <<'EOF'
feat(upload): prefill series/season from ?seriesId=&seasonId=

Landing on /upload via a season's "Add episode" link now pre-selects
that season and suggests the next sequential episode number in
SeriesPicker, instead of requiring the full pick-series/pick-season
flow again. Still fully editable before uploading.
EOF
)"
```

---

### Task 5: Manual end-to-end verification

**Files:** none (verification only)

- [ ] **Step 1: Start both dev servers**

Run in `backend/`: `source venv/bin/activate && python app.py`
Run in `frontend/`: `npm run dev`

- [ ] **Step 2: Verify grouping renders correctly**

In the browser, go to My Scripts (`/`). If real multi-episode series data exists (e.g. "Die Testament"), confirm:
- The series appears as a collapsed group header row with the correct title and episode count.
- Clicking the series header expands it to show season header row(s), collapsed by default.
- Clicking a season header expands it to show its episodes, sorted by episode number, each with an "Ep N" badge.
- Scripts with no series assignment still render as flat rows below all groups, still sortable by clicking column headers.

- [ ] **Step 3: Verify collapse-state persistence**

Expand a series and a season, then reload the page (`Cmd+R` / `F5`). Confirm both remain expanded (localStorage persistence working).

- [ ] **Step 4: Verify "View series" link**

Click "View series" on a series group header. Confirm it navigates to `/series/<id>` (the existing `SeriesDetailPage`) without also toggling the group's collapse state (the click should not bubble to the header row's own toggle handler).

- [ ] **Step 5: Verify "Add episode" deep-link prefill**

Click "Add episode" on a season group header. Confirm:
- It navigates to `/upload?seriesId=...&seasonId=...`.
- The `SeriesPicker` on the upload page opens already in "Add to existing series" mode, with that series and season pre-selected, and the episode number field pre-filled with the correct next number (one higher than the highest existing episode in that season).
- The prefilled selection is still editable (can change series/season/episode number, or switch to "Not part of a series" to override it) before uploading.
- After uploading a file with the prefill untouched, the new script appears in My Scripts correctly nested under that series/season.

- [ ] **Step 6: Verify unassigned upload flow is unchanged**

Go to `/upload` directly (no query params). Confirm `SeriesPicker` opens in its default "Not part of a series" mode as before, with no prefill.

- [ ] **Step 7: Report results**

If any check fails, note exactly which step and what was observed, and fix before considering the plan complete.
