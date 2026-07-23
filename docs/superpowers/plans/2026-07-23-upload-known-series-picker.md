# Upload page: known-series picker + visual polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `SeriesPicker.jsx` real dark-navy/amber styling, and replace its "pick from scratch" 3-tab UI with a compact known-series view (season dropdown + editable episode-number field, explicitly supporting out-of-sequence numbers) when it's opened via a season's "Add episode" deep link.

**Architecture:** `SeriesPicker.jsx` gains a derived `isKnownSeries` flag and a new `overridden` escape-hatch state; when known, it renders a compact series-badge/season-select/episode-number row instead of the classic tabs, and owns the "next episode number" lookup itself (moved out of `ScriptUpload.jsx`, which shrinks to just forwarding `seriesId`/`seasonId` from the URL). A new `SeriesPicker.css` styles both render paths using the same CSS custom properties `ScriptTable.css` already uses.

**Tech Stack:** React 18 + react-router-dom v6 (frontend only — no backend changes, no new API endpoints).

## Global Constraints

- Frontend has no test runner (`npm test` doesn't exist) — frontend tasks are verified via `npm run build` plus manual browser checks. `npm run lint` is broken repo-wide; do not gate on it.
- No backend changes. Reuses `listSeries()`, `listSeasons()`, `listEpisodes()` from `frontend/src/services/apiService.js` exactly as they exist today (verified: lines 2278, 2312, 2327) — do not modify that file.
- Do not change `SeriesAssignmentModal.jsx` or its behavior — it calls `<SeriesPicker onAssign={handleAssign} autoFireNone={false} />` with no `initialSeriesId`/`initialSeasonId` (verified: `frontend/src/components/series/SeriesAssignmentModal.jsx:51-54`), so `isKnownSeries` is always `false` there and the classic tabs keep rendering — but do not rely on that by accident; the classic-tabs render path itself must stay behaviorally identical when `isKnownSeries` is false.
- No change to cold-upload behavior (`/upload` with no query params): still the classic 3-tab picker (none/existing/new), just visually styled.

---

### Task 1: `SeriesPicker.jsx` — known-series render path + moved episode-number logic

**Files:**
- Modify: `frontend/src/components/series/SeriesPicker.jsx` (full rewrite)

**Interfaces:**
- Consumes: `listSeries()`, `listSeasons(seriesId)`, `listEpisodes(seasonId)`, `createSeries(title)` from `frontend/src/services/apiService.js` (all unchanged, already exist).
- Produces: same public props as today (`onAssign`, `autoFireNone`, `initialSeriesId`, `initialSeasonId`, `initialEpisodeNumber`) — no signature change, so `SeriesAssignmentModal.jsx` needs no edits. `initialEpisodeNumber` becomes effectively unused on the known-series path (kept as a prop, harmless) since Task 1 now computes the suggested number itself from `listEpisodes`. Renders a `className="series-picker"` root div — Task 2 (`SeriesPicker.css`) targets this and the new class names introduced here: `.series-picker-known`, `.series-picker-known-badge`, `.series-picker-known-fields`, `.series-picker-known-hint`, `.series-picker-override-btn`.

- [ ] **Step 1: Replace `SeriesPicker.jsx` with the known-series-aware version**

Replace the full contents of `frontend/src/components/series/SeriesPicker.jsx` with:

```jsx
import { useState, useEffect, useRef } from 'react';
import { listSeries, createSeries, listSeasons, createSeason, listEpisodes } from '../../services/apiService';
import './SeriesPicker.css';

/**
 * SeriesPicker - three-state picker for assigning a script to a series/season,
 * plus a compact "known series" view used when arriving via a deep link.
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
 * both initialSeriesId and initialSeasonId are set, isKnownSeries is true
 * and the picker renders a compact "known series" view (series shown as
 * fixed context, season + episode number as live editable controls) instead
 * of the classic 3-tab picker -- unless the user clicks "Not this series?",
 * which sets overridden=true and reveals the classic tabs from a clean
 * 'none' state. initialEpisodeNumber is accepted but unused on the
 * known-series path -- the suggested episode number is now computed here
 * from listEpisodes() whenever the selected season changes, since numbering
 * is per-season and the season is a live dropdown in this view.
 */
export default function SeriesPicker({
    onAssign,
    autoFireNone = true,
    initialSeriesId = null,
    initialSeasonId = null,
    initialEpisodeNumber = null,
}) {
    const isKnownSeries = !!(initialSeriesId && initialSeasonId);
    const [overridden, setOverridden] = useState(false);
    const showKnownView = isKnownSeries && !overridden;

    const [mode, setMode] = useState(initialSeasonId && !isKnownSeries ? 'existing' : 'none');
    const [seriesList, setSeriesList] = useState([]);
    const [selectedSeriesId, setSelectedSeriesId] = useState(isKnownSeries ? initialSeriesId : '');
    const [seasons, setSeasons] = useState([]);
    const [selectedSeasonId, setSelectedSeasonId] = useState('');
    const [episodeNumber, setEpisodeNumber] = useState(
        initialEpisodeNumber != null ? String(initialEpisodeNumber) : ''
    );
    const [newSeriesTitle, setNewSeriesTitle] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const appliedInitialSeason = useRef(false);

    // Known-series view: fetch the series list once (to resolve the badge
    // name) and the season list for the known series -- unconditionally,
    // not gated behind mode === 'existing' like the classic view, since
    // there's no tab click to gate it on here.
    useEffect(() => {
        if (!showKnownView) return;
        listSeries()
            .then((data) => setSeriesList(data.series || []))
            .catch((err) => setError(err.message || 'Failed to load series'));
        listSeasons(initialSeriesId)
            .then((data) => setSeasons(data.seasons || []))
            .catch((err) => setError(err.message || 'Failed to load seasons'));
        setSelectedSeasonId(initialSeasonId);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [showKnownView]);

    // Known-series view: whenever the selected season changes, recompute the
    // suggested next episode number (numbering is per-season) and fire
    // onAssign so pendingSeasonAssignment in ScriptUpload stays in sync
    // without the user touching anything.
    useEffect(() => {
        if (!showKnownView || !selectedSeasonId) return;
        let cancelled = false;
        listEpisodes(selectedSeasonId)
            .then((data) => {
                if (cancelled) return;
                const episodes = data.episodes || [];
                const nextNumber = episodes.reduce(
                    (max, ep) => Math.max(max, ep.episode_number || 0),
                    0
                ) + 1;
                setEpisodeNumber(String(nextNumber));
                onAssign(selectedSeasonId, nextNumber);
            })
            .catch((err) => {
                if (!cancelled) setError(err.message || 'Failed to load episodes');
            });
        return () => {
            cancelled = true;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [showKnownView, selectedSeasonId]);

    useEffect(() => {
        if (showKnownView) return;
        if (mode !== 'existing') return;
        listSeries()
            .then((data) => setSeriesList(data.series || []))
            .catch((err) => setError(err.message || 'Failed to load series'));
    }, [mode, showKnownView]);

    useEffect(() => {
        if (showKnownView) return;
        let cancelled = false;
        const isFirstRunWithPrefill = !appliedInitialSeason.current && !!initialSeasonId;
        if (isFirstRunWithPrefill) {
            // Flip synchronously (not inside the .then() below) so a series
            // change that fires a second effect run before this promise
            // resolves sees the ref already set, and correctly treats
            // itself as a normal (non-prefill) run instead of racing to
            // apply the original prefill onto the newly selected series.
            appliedInitialSeason.current = true;
        } else {
            setSelectedSeasonId('');
        }
        if (!selectedSeriesId) {
            setSeasons([]);
            return;
        }
        listSeasons(selectedSeriesId)
            .then((data) => {
                if (cancelled) return;
                setSeasons(data.seasons || []);
                if (isFirstRunWithPrefill) {
                    setSelectedSeasonId(initialSeasonId);
                }
            })
            .catch((err) => {
                if (!cancelled) setError(err.message || 'Failed to load seasons');
            });
        return () => {
            cancelled = true;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedSeriesId, showKnownView]);

    useEffect(() => {
        if (showKnownView) return;
        if (mode === 'none' && autoFireNone) {
            onAssign(null, null);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [mode, showKnownView]);

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

    const handleOverride = () => {
        setOverridden(true);
        setMode('none');
        setSelectedSeriesId('');
        setSelectedSeasonId('');
        setEpisodeNumber('');
        setError(null);
    };

    const handleKnownSeasonChange = (e) => {
        setSelectedSeasonId(e.target.value);
    };

    const handleKnownEpisodeNumberChange = (e) => {
        const value = e.target.value;
        setEpisodeNumber(value);
        if (selectedSeasonId && value) {
            onAssign(selectedSeasonId, Number(value));
        }
    };

    if (showKnownView) {
        const knownSeries = seriesList.find((s) => s.id === initialSeriesId);
        const seriesLabel = knownSeries?.title || 'Series';

        return (
            <div className="series-picker">
                {error && <p className="series-picker-error">{error}</p>}
                <div className="series-picker-known">
                    <div className="series-picker-known-badge">{seriesLabel}</div>
                    <div className="series-picker-known-fields">
                        <div className="series-picker-known-field">
                            <label>Season</label>
                            <select value={selectedSeasonId} onChange={handleKnownSeasonChange}>
                                {seasons.map((s) => (
                                    <option key={s.id} value={s.id}>{s.title || `Season ${s.season_number}`}</option>
                                ))}
                            </select>
                        </div>
                        <div className="series-picker-known-field">
                            <label>Episode #</label>
                            <input
                                type="number"
                                min="1"
                                value={episodeNumber}
                                onChange={handleKnownEpisodeNumberChange}
                            />
                        </div>
                    </div>
                    <p className="series-picker-known-hint">
                        Suggested next — change to upload out of sequence
                    </p>
                    <button type="button" className="series-picker-override-btn" onClick={handleOverride}>
                        Not this series?
                    </button>
                </div>
            </div>
        );
    }

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
Expected: FAIL — `Failed to resolve import "./SeriesPicker.css"` (Task 2 creates this file next). This confirms the component code itself is wired correctly before the stylesheet exists.

- [ ] **Step 3: Commit**

Do not commit yet — Task 2 creates the CSS file this component now imports, and this component won't build without it. Proceed directly to Task 2; the commit happens at the end of Task 2 and covers both files together.

---

### Task 2: `SeriesPicker.css` — dark navy/amber styling for both render paths

**Files:**
- Create: `frontend/src/components/series/SeriesPicker.css`

**Interfaces:**
- Consumes: CSS custom properties already defined and used by `frontend/src/components/scripts/ScriptTable.css` (verified present there): `--gray-800`, `--gray-700`, `--primary-500`, `--primary-alpha-10`, `--primary-alpha-15`, `--border-color`, `--text-primary`, `--text-secondary`. Targets the class names Task 1 renders: `.series-picker`, `.series-picker-modes` (and its `button`/`button.active` children), `.series-picker-error`, `.series-picker-none`, `.series-picker-existing`, `.series-picker-new`, `.series-picker-known`, `.series-picker-known-badge`, `.series-picker-known-fields`, `.series-picker-known-field`, `.series-picker-known-hint`, `.series-picker-override-btn`.

- [ ] **Step 1: Create `SeriesPicker.css`**

Create `frontend/src/components/series/SeriesPicker.css`:

```css
.series-picker {
    background: var(--gray-800);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
}

.series-picker-error {
    color: #f87171;
    font-size: 0.85rem;
    margin: 0 0 0.75rem;
}

/* Classic 3-tab picker */
.series-picker-modes {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
}

.series-picker-modes button {
    background: var(--gray-700);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 6px 12px;
    color: var(--text-secondary);
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.2s;
}

.series-picker-modes button:hover {
    color: var(--text-primary);
}

.series-picker-modes button.active {
    background: var(--primary-alpha-15);
    border-color: var(--primary-500);
    color: var(--primary-500);
}

.series-picker-none,
.series-picker-existing,
.series-picker-new {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.series-picker-existing select,
.series-picker-existing input,
.series-picker-new select,
.series-picker-new input {
    background: var(--gray-700);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 6px 10px;
    color: var(--text-primary);
    font-size: 0.85rem;
}

.series-picker-existing input[type="number"],
.series-picker-new input[type="number"] {
    width: 90px;
}

.series-picker-existing button,
.series-picker-new button,
.series-picker-none button {
    background: var(--primary-alpha-10);
    border: 1px solid var(--primary-500);
    border-radius: 6px;
    padding: 6px 14px;
    color: var(--primary-500);
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.2s;
}

.series-picker-existing button:hover,
.series-picker-new button:hover:not(:disabled),
.series-picker-none button:hover {
    background: var(--primary-alpha-15);
}

.series-picker-new button:disabled {
    opacity: 0.6;
    cursor: default;
}

/* Known-series compact view */
.series-picker-known {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
}

.series-picker-known-badge {
    display: inline-flex;
    align-self: flex-start;
    background: var(--primary-alpha-15);
    color: var(--primary-500);
    border-radius: 10px;
    padding: 4px 12px;
    font-size: 0.85rem;
    font-weight: 600;
}

.series-picker-known-fields {
    display: flex;
    gap: 1rem;
}

.series-picker-known-field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.series-picker-known-field label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-secondary);
}

.series-picker-known-field select,
.series-picker-known-field input {
    background: var(--gray-700);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 6px 10px;
    color: var(--text-primary);
    font-size: 0.85rem;
}

.series-picker-known-field input[type="number"] {
    width: 90px;
}

.series-picker-known-hint {
    margin: 0;
    color: var(--text-secondary);
    font-size: 0.78rem;
}

.series-picker-override-btn {
    align-self: flex-start;
    background: none;
    border: none;
    color: var(--text-secondary);
    font-size: 0.8rem;
    text-decoration: underline;
    cursor: pointer;
    padding: 0;
}

.series-picker-override-btn:hover {
    color: var(--primary-500);
}
```

- [ ] **Step 2: Verify the build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors (this repo has no frontend test runner — `npm run build` is the correctness gate for JS/JSX/CSS changes, and `npm run lint` is broken repo-wide, so don't gate on it).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/series/SeriesPicker.jsx frontend/src/components/series/SeriesPicker.css
git commit -m "$(cat <<'EOF'
feat(series): known-series picker view + SeriesPicker styling

SeriesPicker previously rendered unstyled browser-default controls
and showed the same "pick a series from scratch" 3-tab UI even when
arriving via a season's "Add episode" deep link. Adds a compact
known-series view (series badge, live season/episode-number fields,
explicit out-of-sequence support, "Not this series?" escape hatch)
plus a first stylesheet matching the app's dark navy/amber design
language. SeriesAssignmentModal's classic-tabs usage is unaffected
(it never passes initialSeriesId/initialSeasonId).
EOF
)"
```

---

### Task 3: `ScriptUpload.jsx` — simplify the prefill effect

**Files:**
- Modify: `frontend/src/components/script/ScriptUpload.jsx`

**Interfaces:**
- Consumes: `SeriesPicker`'s existing `initialSeriesId`/`initialSeasonId` props (Task 1) — no longer needs `initialEpisodeNumber` since Task 1 computes the suggested number itself.
- Produces: `seriesPrefill` state shape simplifies from `{seriesId, seasonId, episodeNumber} | null` to `{seriesId, seasonId} | null`.

- [ ] **Step 1: Remove the now-unused `listEpisodes` import**

In `frontend/src/components/script/ScriptUpload.jsx`, change line 12 from:

```jsx
import { listEpisodes, updateScriptSeason } from '../../services/apiService';
```

to:

```jsx
import { updateScriptSeason } from '../../services/apiService';
```

- [ ] **Step 2: Replace the prefill effect with a direct pass-through**

Find this block (currently lines 41-66):

```jsx
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

Replace it with:

```jsx
    // Deep-link from ScriptTable's season "Add episode" action
    // (/upload?seriesId=..&seasonId=..): forward the series/season straight
    // through to SeriesPicker, which now owns the "next episode number"
    // lookup itself (numbering is per-season and the season is a live,
    // changeable dropdown in the known-series view). Re-runs on every reset
    // (uploadAttempt change) so uploading several episodes in a row from
    // the same link keeps working.
    useEffect(() => {
        const seasonId = searchParams.get('seasonId');
        const seriesId = searchParams.get('seriesId');
        if (!seasonId || !seriesId) return;
        setSeriesPrefill({ seriesId, seasonId });
    }, [uploadAttempt, searchParams]);
```

- [ ] **Step 3: Update the `seriesPrefill` state comment and `SeriesPicker` props**

Find this line (currently line 35):

```jsx
    const [seriesPrefill, setSeriesPrefill] = useState(null); // {seriesId, seasonId, episodeNumber} | null
```

Replace it with:

```jsx
    const [seriesPrefill, setSeriesPrefill] = useState(null); // {seriesId, seasonId} | null
```

Find this block (currently lines 244-252):

```jsx
                        <SeriesPicker
                            key={uploadAttempt}
                            initialSeriesId={seriesPrefill?.seriesId || null}
                            initialSeasonId={seriesPrefill?.seasonId || null}
                            initialEpisodeNumber={seriesPrefill?.episodeNumber || null}
                            onAssign={(seasonId, episodeNumber) =>
                                setPendingSeasonAssignment(seasonId ? { seasonId, episodeNumber } : null)
                            }
                        />
```

Replace it with:

```jsx
                        <SeriesPicker
                            key={uploadAttempt}
                            initialSeriesId={seriesPrefill?.seriesId || null}
                            initialSeasonId={seriesPrefill?.seasonId || null}
                            onAssign={(seasonId, episodeNumber) =>
                                setPendingSeasonAssignment(seasonId ? { seasonId, episodeNumber } : null)
                            }
                        />
```

- [ ] **Step 4: Verify the build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/script/ScriptUpload.jsx
git commit -m "$(cat <<'EOF'
refactor(upload): simplify series prefill effect

The next-episode-number lookup moved into SeriesPicker's known-series
view (numbering is per-season and the season is now a live dropdown
there), so ScriptUpload's prefill effect just forwards seriesId/
seasonId from the URL instead of precomputing the suggested number
itself.
EOF
)"
```

---

### Task 4: Manual end-to-end verification

**Files:** none (verification only)

- [ ] **Step 1: Start both dev servers**

Run in `backend/`: `source venv/bin/activate && python app.py`
Run in `frontend/`: `npm run dev`

- [ ] **Step 2: Verify cold-upload styling**

Go to `/upload` directly (no query params). Confirm:
- `SeriesPicker` now renders with dark-card styling (no raw browser-default buttons/selects) matching the app's navy/amber look.
- The 3 tabs (Not part of a series / Add to existing series / Create new series) still work exactly as before — switching tabs, picking a series/season, entering an episode number, creating a new series.

- [ ] **Step 3: Verify known-series view via deep link**

From My Scripts, click "Add episode" on a season group header (navigates to `/upload?seriesId=...&seasonId=...`). Confirm:
- `SeriesPicker` shows the compact known-series view: a series-name badge, a season `<select>` (pre-set to that season), and an episode-number field pre-filled with one higher than the highest existing episode in that season.
- No classic 3-tab UI is shown in this state.
- Changing the episode-number field to a lower/non-sequential number (e.g. episode 2 when the suggestion was 6) is accepted without error, and that value is what gets assigned after upload — confirm by uploading and checking the script's episode number in My Scripts.
- Changing the season dropdown to a different season of the same series updates the suggested episode number to that season's next number.

- [ ] **Step 4: Verify the "Not this series?" override**

On the known-series view, click "Not this series?". Confirm:
- It reveals the classic 3-tab picker, starting from the "Not part of a series" tab (not pre-filled with the series that was just dismissed).
- The user can then pick a completely different series/season, or leave it as "Not part of a series", and upload normally.

- [ ] **Step 5: Verify `SeriesAssignmentModal` is unchanged**

From My Scripts, click the series icon on any script row's Actions column to open the reassignment modal. Confirm it still shows the classic unstyled(ish) 3-tab picker with a "Remove from series" option when set to "Not part of a series" — no known-series view appears here (it never receives `initialSeriesId`/`initialSeasonId`).

- [ ] **Step 6: Report results**

If any check fails, note exactly which step and what was observed, and fix before considering the plan complete.
