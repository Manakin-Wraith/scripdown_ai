# Series List/Detail Accordion Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse the `/series` → `/series/:seriesId` → `/series/:seriesId/seasons/:seasonId` click-through into a two-step flow by turning `SeriesListPage` into an accordion that expands seasons inline, removing `SeriesDetailPage` as a separate navigation.

**Architecture:** `SeriesListPage.jsx` gains local expand/collapse state keyed by series id, fetching each series' seasons lazily via the existing `listSeasons(seriesId)` API call on first expand (cached after that). `SeriesDetailPage.jsx` is deleted; its row/empty-state markup moves into the expanded-row rendering. The `series/:seriesId` route becomes a redirect (`<Navigate>`) to `/series?expand=:seriesId`, and `ScriptTable.jsx`'s "View series" action is repointed to link there directly. `SeasonPage.jsx` and all backend endpoints are untouched.

**Tech Stack:** React 18 (JSX, no TypeScript), react-router-dom v6 (`useSearchParams`, `<Navigate>`), existing `apiService.js` axios wrapper, plain CSS (no CSS-in-JS).

## Global Constraints

- No backend changes — `listSeries`/`listSeasons` API calls and shapes are reused as-is.
- Frontend has no test suite for these pages; verification gate is `npm run build` (run from `frontend/`) — `npm run lint` is broken repo-wide, do not use it as a gate.
- Follow existing CSS conventions in `frontend/src/pages/SeriesPages.css` (design tokens like `var(--text-primary)`, `var(--space-3)`, etc.) — no new token names.
- `SeriesAssignmentModal` styling, the `.series-page` left-alignment bug, and season-level metrics are explicitly out of scope for this plan.

---

### Task 1: Add expand/collapse state and lazy season-fetch to SeriesListPage

**Files:**
- Modify: `frontend/src/pages/SeriesListPage.jsx`
- Modify: `frontend/src/pages/SeriesPages.css` (new classes for the expand toggle and nested season list)

**Interfaces:**
- Consumes: `listSeries()` and `listSeasons(seriesId)` from `frontend/src/services/apiService.js` (both already exist; `listSeasons` currently only imported in `SeriesDetailPage.jsx`).
- Produces: `SeriesListPage` renders an accordion — no other file depends on its internals.

- [ ] **Step 1: Read the current file to confirm exact current contents before editing**

Run: read `frontend/src/pages/SeriesListPage.jsx` (already known from investigation — reproduced here for reference, no action needed if already open in your editor).

- [ ] **Step 2: Replace `SeriesListPage.jsx` with the accordion implementation**

```jsx
import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Layers, ChevronRight, ChevronDown, Plus, Film } from 'lucide-react';
import { listSeries, listSeasons } from '../services/apiService';
import PageHeader from '../components/layout/PageHeader';
import { Spinner } from '../components/ui';
import './SeriesPages.css';

export default function SeriesListPage() {
    const [searchParams] = useSearchParams();
    const [series, setSeries] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Per-series expand/fetch state, keyed by series id.
    const [expanded, setExpanded] = useState(() => new Set());
    const [seasonsBySeries, setSeasonsBySeries] = useState({});
    const [seasonsLoading, setSeasonsLoading] = useState(() => new Set());
    const [seasonsError, setSeasonsError] = useState({});

    useEffect(() => {
        listSeries()
            .then((data) => setSeries(data.series || []))
            .catch((err) => setError(err.message || 'Failed to load series'))
            .finally(() => setLoading(false));
    }, []);

    const fetchSeasonsFor = (seriesId) => {
        setSeasonsLoading((prev) => new Set(prev).add(seriesId));
        setSeasonsError((prev) => {
            const next = { ...prev };
            delete next[seriesId];
            return next;
        });
        listSeasons(seriesId)
            .then((data) => {
                setSeasonsBySeries((prev) => ({ ...prev, [seriesId]: data.seasons || [] }));
            })
            .catch((err) => {
                setSeasonsError((prev) => ({
                    ...prev,
                    [seriesId]: err.message || 'Failed to load seasons',
                }));
            })
            .finally(() => {
                setSeasonsLoading((prev) => {
                    const next = new Set(prev);
                    next.delete(seriesId);
                    return next;
                });
            });
    };

    const toggleSeries = (seriesId) => {
        setExpanded((prev) => {
            const next = new Set(prev);
            if (next.has(seriesId)) {
                next.delete(seriesId);
            } else {
                next.add(seriesId);
                if (!(seriesId in seasonsBySeries)) {
                    fetchSeasonsFor(seriesId);
                }
            }
            return next;
        });
    };

    // Auto-expand the series named in ?expand=<id>, once the series list
    // has loaded and that id is present -- covers both the
    // series/:seriesId redirect and ScriptTable's "View series" link.
    useEffect(() => {
        const expandId = searchParams.get('expand');
        if (!expandId || loading) return;
        if (!series.some((s) => s.id === expandId)) return;
        setExpanded((prev) => {
            if (prev.has(expandId)) return prev;
            const next = new Set(prev);
            next.add(expandId);
            return next;
        });
        if (!(expandId in seasonsBySeries)) {
            fetchSeasonsFor(expandId);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [searchParams, loading, series]);

    if (loading) {
        return (
            <div className="series-page-loading">
                <Spinner size={32} />
            </div>
        );
    }

    if (error) {
        return <p className="series-page-error">{error}</p>;
    }

    return (
        <div className="series-page">
            <PageHeader title="Series" subtitle="Group related episode scripts together" />

            {series.length === 0 ? (
                <div className="series-empty-state">
                    <div className="series-empty-content">
                        <div className="series-empty-icon-wrapper">
                            <Layers size={28} className="series-empty-icon" />
                        </div>
                        <h2>No series yet</h2>
                        <p>Group related episodes together by assigning a series when you upload a script, or from the "Series" action on an existing script in My Scripts.</p>
                        <Link to="/upload" className="series-empty-cta">
                            <Plus size={16} />
                            Upload a Script
                        </Link>
                    </div>
                </div>
            ) : (
                <div className="series-row-list">
                    {series.map((s) => {
                        const isExpanded = expanded.has(s.id);
                        const seasons = seasonsBySeries[s.id];
                        const isSeasonsLoading = seasonsLoading.has(s.id);
                        const seasonsErr = seasonsError[s.id];
                        return (
                            <div key={s.id} className="series-accordion-item">
                                <button
                                    type="button"
                                    className="series-row series-row-toggle"
                                    onClick={() => toggleSeries(s.id)}
                                    aria-expanded={isExpanded}
                                >
                                    <div className="series-row-left">
                                        <span className="series-row-badge">
                                            <Layers size={16} />
                                        </span>
                                        <span className="series-row-title">{s.title}</span>
                                    </div>
                                    {isExpanded ? (
                                        <ChevronDown size={18} className="series-row-chevron" />
                                    ) : (
                                        <ChevronRight size={18} className="series-row-chevron" />
                                    )}
                                </button>

                                {isExpanded && (
                                    <div className="series-accordion-panel">
                                        {isSeasonsLoading && (
                                            <div className="series-accordion-loading">
                                                <Spinner size={20} />
                                            </div>
                                        )}
                                        {seasonsErr && (
                                            <p className="series-page-error series-accordion-error">{seasonsErr}</p>
                                        )}
                                        {!isSeasonsLoading && !seasonsErr && seasons && seasons.length === 0 && (
                                            <div className="series-accordion-empty">
                                                <Film size={20} className="series-empty-icon" />
                                                <p>This series doesn't have any seasons yet. Assign an episode to it from My Scripts to create one.</p>
                                            </div>
                                        )}
                                        {!isSeasonsLoading && !seasonsErr && seasons && seasons.length > 0 && (
                                            <div className="series-row-list series-row-list-nested">
                                                {seasons.map((season) => (
                                                    <Link
                                                        key={season.id}
                                                        to={`/series/${s.id}/seasons/${season.id}`}
                                                        className="series-row"
                                                    >
                                                        <div className="series-row-left">
                                                            <span className="series-row-badge">
                                                                <span className="series-row-num">{season.season_number}</span>
                                                            </span>
                                                            <span className="series-row-title">
                                                                {season.title || `Season ${season.season_number}`}
                                                            </span>
                                                        </div>
                                                        <ChevronRight size={18} className="series-row-chevron" />
                                                    </Link>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
```

- [ ] **Step 3: Add accordion-specific CSS to `SeriesPages.css`**

Append to `frontend/src/pages/SeriesPages.css`:

```css
/* Accordion (SeriesListPage) -- toggle rows and their expanded panels */
.series-accordion-item {
    display: flex;
    flex-direction: column;
}

.series-row-toggle {
    width: 100%;
    border: 1px solid var(--border-color);
    cursor: pointer;
    font: inherit;
}

.series-accordion-panel {
    padding: var(--space-3) 0 var(--space-1) var(--space-6);
}

.series-row-list-nested {
    gap: var(--space-2);
}

.series-accordion-loading {
    display: flex;
    justify-content: flex-start;
    padding: var(--space-3) 0;
}

.series-accordion-error {
    padding: var(--space-3);
}

.series-accordion-empty {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-4);
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    color: var(--text-secondary);
    font-size: 0.875rem;
}
.series-accordion-empty p {
    margin: 0;
}
```

- [ ] **Step 4: Build the frontend to verify no compile errors**

Run (from `frontend/`): `npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SeriesListPage.jsx frontend/src/pages/SeriesPages.css
git commit -m "feat(series): accordion-expand seasons inline on SeriesListPage"
```

---

### Task 2: Remove SeriesDetailPage and redirect its route

**Files:**
- Delete: `frontend/src/pages/SeriesDetailPage.jsx`
- Modify: `frontend/src/App.jsx`

**Interfaces:**
- Consumes: nothing new — `Navigate` is a standard `react-router-dom` v6 export already available (package.json confirms `react-router-dom: ^6.20.0`).
- Produces: `series/:seriesId` route now redirects instead of rendering a page component.

- [ ] **Step 1: Delete `SeriesDetailPage.jsx`**

```bash
git rm frontend/src/pages/SeriesDetailPage.jsx
```

- [ ] **Step 2: Update `App.jsx` imports and route**

In `frontend/src/App.jsx`, find these two lines (around line 45-47):

```jsx
import SeriesListPage from './pages/SeriesListPage';
import SeriesDetailPage from './pages/SeriesDetailPage';
import SeasonPage from './pages/SeasonPage';
```

Replace with:

```jsx
import SeriesListPage from './pages/SeriesListPage';
import SeasonPage from './pages/SeasonPage';
```

`Navigate` is already imported at the top of `App.jsx`:

```jsx
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
```

Add `useParams` to that same import:

```jsx
import { BrowserRouter as Router, Routes, Route, Navigate, useParams } from 'react-router-dom';
```

Find the route block (around line 76-78):

```jsx
<Route path="series" element={<SeriesListPage />} />
<Route path="series/:seriesId" element={<SeriesDetailPage />} />
<Route path="series/:seriesId/seasons/:seasonId" element={<SeasonPage />} />
```

Replace with:

```jsx
<Route path="series" element={<SeriesListPage />} />
<Route path="series/:seriesId" element={<SeriesRedirect />} />
<Route path="series/:seriesId/seasons/:seasonId" element={<SeasonPage />} />
```

Add a small redirect helper component near the top of `App.jsx`, right after the imports (it needs `useParams` and `Navigate`, both from `react-router-dom`):

```jsx
function SeriesRedirect() {
    const { seriesId } = useParams();
    return <Navigate to={`/series?expand=${seriesId}`} replace />;
}
```

- [ ] **Step 3: Build the frontend to verify no compile errors and no dangling import**

Run (from `frontend/`): `npm run build`
Expected: build succeeds with no errors (in particular, no "SeriesDetailPage not found" or unused-import failures).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "refactor(series): remove SeriesDetailPage, redirect series/:seriesId to accordion"
```

---

### Task 3: Repoint ScriptTable's "View series" link

**Files:**
- Modify: `frontend/src/components/scripts/ScriptTable.jsx:323`

**Interfaces:**
- Consumes: nothing new.
- Produces: nothing consumed elsewhere — this is a leaf UI change.

- [ ] **Step 1: Update the navigate call**

In `frontend/src/components/scripts/ScriptTable.jsx`, find (around line 323):

```jsx
navigate(`/series/${series.id}`);
```

Replace with:

```jsx
navigate(`/series?expand=${series.id}`);
```

- [ ] **Step 2: Build the frontend to verify no compile errors**

Run (from `frontend/`): `npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/scripts/ScriptTable.jsx
git commit -m "fix(series): View series link goes straight to pre-expanded accordion"
```

---

### Task 4: Manual verification pass

**Files:** none (verification only, no code changes).

- [ ] **Step 1: Start the frontend dev server**

Run (from `frontend/`): `npm run dev`

- [ ] **Step 2: Verify the accordion on `/series`**

Navigate to `/series` in a browser. Confirm:
- Series rows render as before, but clicking a row expands it in place (chevron rotates from right-pointing to down-pointing) instead of navigating away.
- A spinner briefly appears in the expanded panel on first expand, then season rows appear.
- Clicking the same series row again collapses it; expanding it a third time does NOT show the loading spinner again (seasons were cached from the first fetch) — confirm via the Network tab that `GET /api/series/:id/seasons` fires only once per series across multiple expand/collapse cycles.
- A series with zero seasons shows the inline empty-state message instead of season rows.

- [ ] **Step 3: Verify deep-link and redirect behavior**

- Navigate directly to `/series/<a-real-series-id>` (the old detail-page URL). Confirm it redirects to `/series?expand=<that-id>` and that series is pre-expanded on load.
- From My Scripts (`/scripts` or wherever `ScriptTable` renders), click "View series" on a grouped series header. Confirm it lands on `/series?expand=<id>` with that series pre-expanded, no intermediate page flash.

- [ ] **Step 4: Verify the season page is still reachable and unchanged**

Click a season row inside an expanded series. Confirm it navigates to `/series/:seriesId/seasons/:seasonId` and `SeasonPage` renders exactly as before (episodes list, combined cast table).

- [ ] **Step 5: Final full build check**

Run (from `frontend/`): `npm run build`
Expected: build succeeds with no errors.

No commit for this task — it's verification only. If any step reveals a bug, fix it in the relevant task's file and amend that task's commit (or add a small follow-up commit), then re-run this verification pass.
