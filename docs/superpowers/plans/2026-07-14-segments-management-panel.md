# Segments Management Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A "Segments" management panel (rename, recolour-by-type, reorder, delete, create) opened from the Scenes-tab header, plus the backend refinements that make renames and recolours show everywhere.

**Architecture:** A new `SegmentManager` modal follows the existing `LocationManager` pattern (self-contained manager, `useToast`, `useConfirmDialog`, `onChanged` refetch). Colour derives from the segment's type via a single shared `segmentTint` util reused by the panel and every display chip. Two small backend changes: `update_segment` recalculates story days on rename (so labels refresh), and `get_scenes` derives each scene's `segment_type` so chips can colour by type.

**Tech Stack:** Flask (Python 3.13), `supabase-py`, pytest; React 18 + Vite (plain JSX), axios via `apiService.js`.

## Global Constraints

- Supabase only, via the service-role `db` singleton / module `supabase` client. No SQLite.
- Backend gate: `pytest tests/` (run in `backend/`, use `venv/bin/python -m pytest` so `.env` loads). Frontend gate: `npm run build` (run in `frontend/`). `npm run lint` is broken repo-wide — do not use it.
- All frontend backend calls go through the shared `api` axios instance in `frontend/src/services/apiService.js`. No new axios instances. Reuse the existing `getSegments`/`createSegment`/`updateSegment`/`deleteSegment` methods — do not add new endpoints; reorder is `updateSegment(id, { display_order })`.
- Colour = segment type. The five types and their tints are the single source of truth in `frontend/src/utils/segmentTint.js`: MONTAGE amber `#fcd34d`, FLASHBACK purple `#d8b4fe`, DREAM blue `#93c5fd`, FANTASY pink `#f9a8d4`, TITLE_CARD slate `#cbd5e1`.
- Segment authorization is already enforced server-side (owner-or-member via `_load_segment_or_error`); do not weaken it.

---

## File Structure

- Modify: `backend/routes/segment_routes.py` — `update_segment` recalcs on rename.
- Modify: `backend/routes/supabase_routes.py` — `get_scenes` derives `segment_type`.
- Modify: `backend/tests/test_timeline_segments.py` — rename-recalc + get_scenes tests.
- Create: `frontend/src/utils/segmentTint.js` — type→colour single source of truth.
- Create: `frontend/src/components/scenes/SegmentManager.jsx` + `SegmentManager.css` — the panel.
- Modify: `frontend/src/components/scenes/SceneViewer.jsx` — "Segments" button + modal wiring.
- Modify: `frontend/src/components/scenes/SceneList.jsx` + `SceneList.css`, `frontend/src/components/board/StripCard.jsx`, `frontend/src/components/board/boardModel.js`, `frontend/src/components/schedule/ScheduleSceneCard.jsx`, `frontend/src/components/reports/Stripboard.jsx` — colour chips by type.

---

## Task 1: Backend — `update_segment` recalculates on rename

**Files:**
- Modify: `backend/routes/segment_routes.py` (`update_segment`)
- Test: `backend/tests/test_timeline_segments.py` (append)

**Interfaces:**
- Consumes: `db.get_timeline_segment`, `db.update_timeline_segment`, `recalculate_story_days`, `_load_segment_or_error` (all existing).
- Produces: PATCH `/api/segments/<id>` recalcs story days only when `name` changes.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_timeline_segments.py`. First extend `RouteFakeDB` (it currently has `get_timeline_segment`, `get_scene_script_id`, `update_scene`) with the two methods this route needs, by adding them to the class body:

```python
# --- add these methods to the existing RouteFakeDB class ---
    def get_timeline_segment(self, segment_id):
        return {'id': segment_id, 'script_id': 'scr-1', 'name': 'Old Name'}

    def update_timeline_segment(self, segment_id, **kwargs):
        return {'id': segment_id, 'script_id': 'scr-1', **kwargs}
```

(If `RouteFakeDB` already defines `get_timeline_segment`, replace it with the version above so it returns a `name`.)

Then add the tests:

```python
def _patch_client(monkeypatch, fake, recalced):
    monkeypatch.setattr(seg_routes, 'db', fake)
    monkeypatch.setattr(seg_routes, 'script_access', lambda *a, **k: 'ok')
    monkeypatch.setattr(seg_routes, 'recalculate_story_days',
                        lambda script_id, start_from_order=0: recalced.append((script_id, start_from_order)))
    monkeypatch.setenv('FLASK_ENV', 'development')
    from flask import Flask
    flask_app = Flask(__name__)
    flask_app.register_blueprint(seg_routes.segment_bp)
    return flask_app


def test_rename_triggers_recalc(monkeypatch):
    recalced = []
    app = _patch_client(monkeypatch, RouteFakeDB(), recalced)
    with app.test_client() as client:
        resp = client.patch('/api/segments/seg-A', json={'name': 'New Name'})
    assert resp.status_code == 200
    assert recalced == [('scr-1', 0)]


def test_recolour_does_not_trigger_recalc(monkeypatch):
    recalced = []
    app = _patch_client(monkeypatch, RouteFakeDB(), recalced)
    with app.test_client() as client:
        resp = client.patch('/api/segments/seg-A', json={'segment_type': 'DREAM'})
    assert resp.status_code == 200
    assert recalced == []  # colour/order changes don't touch scene labels
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && venv/bin/python -m pytest tests/test_timeline_segments.py::test_rename_triggers_recalc tests/test_timeline_segments.py::test_recolour_does_not_trigger_recalc -v`
Expected: FAIL — the current `update_segment` never calls `recalculate_story_days`, so `test_rename_triggers_recalc` fails (`recalced == []`).

- [ ] **Step 3: Implement — recalc on rename**

Replace the body of `update_segment` in `backend/routes/segment_routes.py` with:

```python
@segment_bp.route('/api/segments/<segment_id>', methods=['PATCH'])
@require_auth
def update_segment(segment_id):
    segment, denied = _load_segment_or_error(segment_id)
    if denied:
        return denied
    body = request.get_json() or {}
    allowed = {k: body[k] for k in ('name', 'segment_type', 'color', 'display_order')
               if k in body}
    if 'segment_type' in allowed and allowed['segment_type'] not in VALID_TYPES:
        return jsonify({'error': 'invalid segment_type'}), 400
    if not allowed:
        return jsonify({'error': 'no updatable fields provided'}), 400
    updated = db.update_timeline_segment(segment_id, **allowed)
    # A rename changes the label shown on member scenes (story_day_label),
    # so refresh their labels. Colour/order changes don't affect labels.
    if 'name' in allowed and allowed['name'] != segment.get('name'):
        recalculate_story_days(segment['script_id'], start_from_order=0)
    return jsonify({'segment': updated}), 200
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && venv/bin/python -m pytest tests/test_timeline_segments.py -v`
Expected: PASS (all segment tests, including the two new ones).

- [ ] **Step 5: Commit**

```bash
git add backend/routes/segment_routes.py backend/tests/test_timeline_segments.py
git commit -m "feat(segments): recalc story days when a segment is renamed"
```

---

## Task 2: Backend — `get_scenes` derives `segment_type`

**Files:**
- Modify: `backend/routes/supabase_routes.py` (`get_scenes`, ~lines 1046-1118)
- Test: `backend/tests/test_timeline_segments.py` (append)

**Interfaces:**
- Consumes: module-level `supabase` client in `supabase_routes`.
- Produces: each scene object in the `/api/scripts/<id>/scenes` response includes `segment_type` (the type of its segment, or `None`).

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_timeline_segments.py`:

```python
import routes.supabase_routes as sup_routes


class _ScenesFakeSupabase:
    """Dispatches table() by name for get_scenes: scenes, shooting_day_scenes, timeline_segments."""

    def __init__(self, scenes, segments):
        self._scenes = scenes
        self._segments = segments

    def table(self, name):
        data = {
            'scenes': self._scenes,
            'shooting_day_scenes': [],
            'timeline_segments': self._segments,
        }.get(name, [])
        return _ScenesQuery(data)


class _ScenesQuery:
    def __init__(self, data):
        self._data = data

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def execute(self):
        class _R:
            pass
        r = _R()
        r.data = self._data
        return r


def test_get_scenes_includes_segment_type(monkeypatch):
    scenes = [
        {'id': 'sc-1', 'scene_number': '1', 'segment_id': 'seg-A'},
        {'id': 'sc-2', 'scene_number': '2', 'segment_id': None},
    ]
    segments = [{'id': 'seg-A', 'segment_type': 'FLASHBACK'}]
    monkeypatch.setattr(sup_routes, 'supabase', _ScenesFakeSupabase(scenes, segments))

    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(sup_routes.supabase_bp)
    with app.test_client() as client:
        resp = client.get('/api/scripts/scr-1/scenes')

    body = resp.get_json()
    by_id = {s['id']: s for s in body['scenes']}
    assert by_id['sc-1']['segment_type'] == 'FLASHBACK'
    assert by_id['sc-2']['segment_type'] is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_timeline_segments.py::test_get_scenes_includes_segment_type -v`
Expected: FAIL with `KeyError: 'segment_type'` (the response has no such key yet).

- [ ] **Step 3: Implement — build a segment-type map and include it**

In `backend/routes/supabase_routes.py`, in `get_scenes`, right after the `scheduled_map` try/except block (just before `scenes = []`), add:

```python
        # Map scene segment_id -> segment_type so display chips can colour by type.
        seg_type_map = {}
        try:
            seg_result = supabase.table('timeline_segments') \
                .select('id, segment_type') \
                .eq('script_id', script_id) \
                .execute()
            for row in (seg_result.data or []):
                seg_type_map[row['id']] = row.get('segment_type')
        except Exception as seg_err:
            print(f"Warning: Could not fetch segment types for scenes: {seg_err}")
```

Then, in the per-scene dict, next to the existing `'segment_id': scene.get('segment_id'),` line, add:

```python
                'segment_type': seg_type_map.get(scene.get('segment_id')),
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && venv/bin/python -m pytest tests/test_timeline_segments.py::test_get_scenes_includes_segment_type -v`
Expected: PASS

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && venv/bin/python -m pytest tests/ -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/supabase_routes.py backend/tests/test_timeline_segments.py
git commit -m "feat(segments): include segment_type in the scenes payload"
```

---

## Task 3: Frontend — `segmentTint` util + `SegmentManager` component

**Files:**
- Create: `frontend/src/utils/segmentTint.js`
- Create: `frontend/src/components/scenes/SegmentManager.jsx`
- Create: `frontend/src/components/scenes/SegmentManager.css`

**Interfaces:**
- Consumes: `getSegments`, `createSegment`, `updateSegment`, `deleteSegment` (existing apiService methods); `useToast` (`toast.error(title, message)`), `useConfirmDialog` (`confirm({ title, message, confirmText }) → Promise<boolean>`).
- Produces:
  - `segmentTint(type) → { background, border, color }` and `segmentDotColor(type) → string` (used by Task 5).
  - `<SegmentManager scriptId scenes onClose onChanged />` — a modal.

- [ ] **Step 1: Create the tint util**

`frontend/src/utils/segmentTint.js`:

```javascript
// Single source of truth for segment (flashback/montage) colours, keyed by type.
const SEGMENT_TINTS = {
    MONTAGE:    { bg: 'rgba(245, 158, 11, 0.18)', border: 'rgba(245, 158, 11, 0.40)', color: '#fcd34d' },
    FLASHBACK:  { bg: 'rgba(168, 85, 247, 0.18)', border: 'rgba(168, 85, 247, 0.40)', color: '#d8b4fe' },
    DREAM:      { bg: 'rgba(59, 130, 246, 0.18)', border: 'rgba(59, 130, 246, 0.40)', color: '#93c5fd' },
    FANTASY:    { bg: 'rgba(236, 72, 153, 0.18)', border: 'rgba(236, 72, 153, 0.40)', color: '#f9a8d4' },
    TITLE_CARD: { bg: 'rgba(148, 163, 184, 0.18)', border: 'rgba(148, 163, 184, 0.40)', color: '#cbd5e1' },
};

const tintFor = (type) => SEGMENT_TINTS[(type || 'MONTAGE').toUpperCase()] || SEGMENT_TINTS.MONTAGE;

// Inline style for a segment chip (translucent bg + border + bright text).
export const segmentTint = (type) => {
    const t = tintFor(type);
    return { background: t.bg, border: `1px solid ${t.border}`, color: t.color };
};

// Solid bright colour for a swatch/dot.
export const segmentDotColor = (type) => tintFor(type).color;

export const SEGMENT_TYPES = [
    { code: 'MONTAGE', label: 'Montage' },
    { code: 'FLASHBACK', label: 'Flashback' },
    { code: 'DREAM', label: 'Dream' },
    { code: 'FANTASY', label: 'Fantasy' },
    { code: 'TITLE_CARD', label: 'Title Card' },
];
```

- [ ] **Step 2: Create the component**

`frontend/src/components/scenes/SegmentManager.jsx`:

```jsx
import React, { useState, useEffect, useCallback } from 'react';
import { X, Trash2, ChevronUp, ChevronDown, Plus, Clapperboard } from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { useConfirmDialog } from '../../context/ConfirmDialogContext';
import { getSegments, createSegment, updateSegment, deleteSegment } from '../../services/apiService';
import { segmentDotColor, SEGMENT_TYPES } from '../../utils/segmentTint';
import './SegmentManager.css';

/**
 * SegmentManager — manage timeline segments (flashbacks / montages) for a script.
 * Colour is derived from a segment's type. Renames refresh scene labels server-side.
 */
const SegmentManager = ({ scriptId, scenes, onClose, onChanged }) => {
    const toast = useToast();
    const { confirm } = useConfirmDialog();
    const [segments, setSegments] = useState([]);
    const [busy, setBusy] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [editName, setEditName] = useState('');
    const [typePickerId, setTypePickerId] = useState(null);
    const [newName, setNewName] = useState('');
    const [newType, setNewType] = useState('MONTAGE');

    const load = useCallback(async () => {
        try { setSegments(await getSegments(scriptId)); }
        catch { setSegments([]); }
    }, [scriptId]);
    useEffect(() => { load(); }, [load]);

    const countFor = useCallback(
        (segId) => (scenes || []).filter(s => s.segment_id === segId).length,
        [scenes]
    );

    const run = async (fn, errMsg) => {
        if (busy) return;
        setBusy(true);
        try {
            await fn();
            await load();
            if (onChanged) await onChanged();
        } catch (e) {
            console.error('[SegmentManager]', e);
            toast.error('Something went wrong', errMsg);
        } finally {
            setBusy(false);
        }
    };

    const startRename = (seg) => { setEditingId(seg.id); setEditName(seg.name); };
    const saveRename = (seg) => {
        const name = editName.trim();
        setEditingId(null);
        if (!name || name === seg.name) return;
        run(() => updateSegment(seg.id, { name }), 'Couldn’t rename the segment. Try again.');
    };

    const setType = (seg, code) => {
        setTypePickerId(null);
        if (code === seg.segment_type) return;
        run(() => updateSegment(seg.id, { segment_type: code }), 'Couldn’t recolour the segment. Try again.');
    };

    const move = (index, dir) => {
        const target = index + dir;
        if (target < 0 || target >= segments.length) return;
        const a = segments[index];
        const b = segments[target];
        const aOrder = a.display_order ?? index;
        const bOrder = b.display_order ?? target;
        run(async () => {
            await updateSegment(a.id, { display_order: bOrder });
            await updateSegment(b.id, { display_order: aOrder });
        }, 'Couldn’t reorder the segments. Try again.');
    };

    const remove = async (seg) => {
        const ok = await confirm({
            title: 'Delete segment',
            message: `Delete “${seg.name}”? Its scenes return to the story-day timeline.`,
            confirmText: 'Delete',
        });
        if (!ok) return;
        run(() => deleteSegment(seg.id, scriptId), 'Couldn’t delete the segment. Try again.');
    };

    const create = () => {
        const name = newName.trim();
        if (!name) return;
        run(async () => {
            await createSegment(scriptId, { name, segment_type: newType });
            setNewName('');
            setNewType('MONTAGE');
        }, 'Couldn’t create the segment. Try again.');
    };

    return (
        <div className="segmgr-overlay" onClick={onClose}>
            <div className="segmgr" onClick={e => e.stopPropagation()} role="dialog" aria-modal="true">
                <div className="segmgr-header">
                    <div className="segmgr-title"><Clapperboard size={16} /> Segments</div>
                    <button className="segmgr-close" onClick={onClose} aria-label="Close"><X size={18} /></button>
                </div>

                <div className="segmgr-body">
                    {segments.length === 0 && (
                        <p className="segmgr-empty">
                            No segments yet. Group flashback or montage scenes from a scene’s detail panel,
                            or create one below.
                        </p>
                    )}
                    {segments.map((seg, i) => {
                        const n = countFor(seg.id);
                        return (
                            <div className="segmgr-row" key={seg.id}>
                                <div className="segmgr-swatch-wrap">
                                    <button
                                        className="segmgr-swatch"
                                        style={{ background: segmentDotColor(seg.segment_type) }}
                                        onClick={() => setTypePickerId(typePickerId === seg.id ? null : seg.id)}
                                        disabled={busy}
                                        title="Change type / colour"
                                    />
                                    {typePickerId === seg.id && (
                                        <div className="segmgr-type-picker">
                                            {SEGMENT_TYPES.map(t => (
                                                <button
                                                    key={t.code}
                                                    className="segmgr-type-option"
                                                    onClick={() => setType(seg, t.code)}
                                                >
                                                    <span className="segmgr-dot" style={{ background: segmentDotColor(t.code) }} />
                                                    {t.label}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>

                                {editingId === seg.id ? (
                                    <input
                                        className="segmgr-name-input"
                                        value={editName}
                                        autoFocus
                                        onChange={e => setEditName(e.target.value)}
                                        onBlur={() => saveRename(seg)}
                                        onKeyDown={e => {
                                            if (e.key === 'Enter') saveRename(seg);
                                            if (e.key === 'Escape') setEditingId(null);
                                        }}
                                    />
                                ) : (
                                    <button className="segmgr-name" onClick={() => startRename(seg)} title="Click to rename">
                                        {seg.name}
                                    </button>
                                )}

                                <span className="segmgr-count">{n} {n === 1 ? 'scene' : 'scenes'}</span>

                                <div className="segmgr-actions">
                                    <button className="segmgr-icon-btn" disabled={busy || i === 0} onClick={() => move(i, -1)} title="Move up"><ChevronUp size={15} /></button>
                                    <button className="segmgr-icon-btn" disabled={busy || i === segments.length - 1} onClick={() => move(i, 1)} title="Move down"><ChevronDown size={15} /></button>
                                    <button className="segmgr-icon-btn segmgr-delete" disabled={busy} onClick={() => remove(seg)} title="Delete"><Trash2 size={15} /></button>
                                </div>
                            </div>
                        );
                    })}
                </div>

                <div className="segmgr-create">
                    <select className="segmgr-type-select" value={newType} onChange={e => setNewType(e.target.value)}>
                        {SEGMENT_TYPES.map(t => <option key={t.code} value={t.code}>{t.label}</option>)}
                    </select>
                    <input
                        className="segmgr-create-input"
                        placeholder="New segment name"
                        value={newName}
                        onChange={e => setNewName(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') create(); }}
                    />
                    <button className="segmgr-add" onClick={create} disabled={!newName.trim() || busy} title="Create segment"><Plus size={16} /></button>
                </div>
            </div>
        </div>
    );
};

export default SegmentManager;
```

- [ ] **Step 3: Create the stylesheet**

`frontend/src/components/scenes/SegmentManager.css`:

```css
.segmgr-overlay {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(2, 6, 23, 0.6);
    padding: 1rem;
}

.segmgr {
    width: 100%;
    max-width: 520px;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    background: var(--gray-800, #1e293b);
    border: 1px solid var(--border-color, rgba(148, 163, 184, 0.2));
    border-radius: 12px;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5);
    overflow: hidden;
}

.segmgr-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.85rem 1rem;
    border-bottom: 1px solid var(--border-color, rgba(148, 163, 184, 0.15));
}

.segmgr-title {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 700;
    color: var(--gray-100, #f1f5f9);
}

.segmgr-close {
    display: inline-flex;
    border: none;
    background: none;
    color: var(--gray-400, #94a3b8);
    cursor: pointer;
    border-radius: 6px;
    padding: 0.2rem;
}

.segmgr-close:hover { background: rgba(148, 163, 184, 0.12); color: var(--gray-100, #f1f5f9); }

.segmgr-body {
    padding: 0.5rem;
    overflow-y: auto;
    flex: 1;
}

.segmgr-empty {
    color: var(--gray-400, #94a3b8);
    font-size: 0.85rem;
    text-align: center;
    padding: 1.5rem 1rem;
    line-height: 1.5;
}

.segmgr-row {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.45rem 0.5rem;
    border-radius: 8px;
}

.segmgr-row:hover { background: rgba(148, 163, 184, 0.06); }

.segmgr-swatch-wrap { position: relative; display: inline-flex; }

.segmgr-swatch {
    width: 16px;
    height: 16px;
    border-radius: 5px;
    border: 1px solid rgba(255, 255, 255, 0.15);
    cursor: pointer;
    flex: none;
}

.segmgr-type-picker {
    position: absolute;
    top: calc(100% + 6px);
    left: 0;
    z-index: 10;
    min-width: 150px;
    padding: 0.3rem;
    background: var(--gray-750, #263449);
    border: 1px solid var(--border-color, rgba(148, 163, 184, 0.25));
    border-radius: 8px;
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.45);
}

.segmgr-type-option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.35rem 0.45rem;
    border: none;
    background: none;
    border-radius: 6px;
    color: var(--gray-200, #e2e8f0);
    font-size: 0.8rem;
    text-align: left;
    cursor: pointer;
}

.segmgr-type-option:hover { background: rgba(148, 163, 184, 0.12); }

.segmgr-dot { width: 9px; height: 9px; border-radius: 50%; flex: none; }

.segmgr-name {
    flex: 1;
    min-width: 0;
    text-align: left;
    border: none;
    background: none;
    color: var(--gray-100, #f1f5f9);
    font-size: 0.9rem;
    cursor: pointer;
    padding: 0.2rem 0.25rem;
    border-radius: 5px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.segmgr-name:hover { background: rgba(148, 163, 184, 0.1); }

.segmgr-name-input {
    flex: 1;
    min-width: 0;
    padding: 0.25rem 0.4rem;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(245, 158, 11, 0.5);
    border-radius: 5px;
    color: var(--gray-100, #f1f5f9);
    font-size: 0.9rem;
}

.segmgr-name-input:focus { outline: none; box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.15); }

.segmgr-count {
    flex: none;
    font-size: 0.72rem;
    color: var(--gray-500, #64748b);
    min-width: 62px;
    text-align: right;
}

.segmgr-actions { display: inline-flex; gap: 0.15rem; flex: none; }

.segmgr-icon-btn {
    display: inline-flex;
    padding: 0.3rem;
    border: none;
    background: none;
    color: var(--gray-400, #94a3b8);
    border-radius: 5px;
    cursor: pointer;
}

.segmgr-icon-btn:hover:not(:disabled) { background: rgba(148, 163, 184, 0.14); color: var(--gray-100, #f1f5f9); }
.segmgr-icon-btn:disabled { opacity: 0.35; cursor: default; }
.segmgr-delete:hover:not(:disabled) { background: rgba(239, 68, 68, 0.15); color: #fca5a5; }

.segmgr-create {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.6rem;
    border-top: 1px solid var(--border-color, rgba(148, 163, 184, 0.15));
}

.segmgr-type-select {
    flex: none;
    padding: 0.4rem 0.5rem;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid var(--border-color, rgba(148, 163, 184, 0.25));
    border-radius: 6px;
    color: var(--gray-100, #f1f5f9);
    font-size: 0.8rem;
}

.segmgr-create-input {
    flex: 1;
    min-width: 0;
    padding: 0.45rem 0.55rem;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid var(--border-color, rgba(148, 163, 184, 0.25));
    border-radius: 6px;
    color: var(--gray-100, #f1f5f9);
    font-size: 0.85rem;
}

.segmgr-create-input:focus { outline: none; border-color: rgba(245, 158, 11, 0.5); box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.15); }

.segmgr-add {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: none;
    width: 34px;
    height: 34px;
    border: none;
    border-radius: 6px;
    background: rgba(245, 158, 11, 0.18);
    color: #fbbf24;
    cursor: pointer;
}

.segmgr-add:hover:not(:disabled) { background: rgba(245, 158, 11, 0.3); }
.segmgr-add:disabled { opacity: 0.4; cursor: default; }
```

- [ ] **Step 4: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/segmentTint.js frontend/src/components/scenes/SegmentManager.jsx frontend/src/components/scenes/SegmentManager.css
git commit -m "feat(segments): SegmentManager panel + segmentTint util"
```

---

## Task 4: Frontend — wire the "Segments" button in SceneViewer

**Files:**
- Modify: `frontend/src/components/scenes/SceneViewer.jsx`

**Interfaces:**
- Consumes: `SegmentManager` (Task 3); existing `scenes`, `scriptId`, `refreshScenes`, `notifyStoryDayChange` (via `useStoryDayNotify`).
- Produces: a "Segments" button in `.sidebar-header-actions` that opens the modal.

- [ ] **Step 1: Add imports and state**

At the top of `SceneViewer.jsx`, add `Clapperboard` to the existing `lucide-react` import (the line currently importing `AlertCircle, ChevronDown, ...`), and add these imports after the other component imports:

```jsx
import SegmentManager from './SegmentManager';
import { useStoryDayNotify } from '../../context/StoryDayContext';
```

Inside the component body (near the other `useState` hooks, e.g. beside `const [storyDayFilter, setStoryDayFilter] = useState(null);`):

```jsx
    const [showSegmentManager, setShowSegmentManager] = useState(false);
    const notifyStoryDayChange = useStoryDayNotify();
```

(If `SceneViewer` already imports/uses `useStoryDayNotify` or `notifyStoryDayChange`, reuse the existing one instead of adding a duplicate.)

- [ ] **Step 2: Add the button in the sidebar header**

In `SceneViewer.jsx`, inside `.sidebar-header-actions` (which currently holds the story-day filter `<select>` and the `pdf-toggle-btn`), add this button just before the `pdf-toggle-btn`:

```jsx
                            <button
                                className="segmgr-open-btn"
                                onClick={() => setShowSegmentManager(true)}
                                title="Manage flashback / montage segments"
                            >
                                <Clapperboard size={16} />
                            </button>
```

- [ ] **Step 3: Render the modal**

In `SceneViewer.jsx`, just before the final closing of the component's returned JSX (e.g. after the `.scene-viewer-layout` div closes, alongside other conditionally-rendered overlays), add:

```jsx
            {showSegmentManager && (
                <SegmentManager
                    scriptId={scriptId}
                    scenes={scenes}
                    onClose={() => setShowSegmentManager(false)}
                    onChanged={async () => {
                        await refreshScenes();
                        notifyStoryDayChange(scriptId);
                    }}
                />
            )}
```

(`refreshScenes` is the existing scene refetch passed to `SceneDetail` as `onRefreshScene`. If its name differs in this file, use the actual scene-refetch function — grep for the function passed as `onRefreshScene`.)

- [ ] **Step 4: Style the button (reuse the PDF-toggle style)**

Confirm the button looks consistent with `pdf-toggle-btn`. If `SceneViewer`'s CSS has a `.pdf-toggle-btn` rule, add `.segmgr-open-btn` to the same selector list (find the `.pdf-toggle-btn { ... }` rule in the SceneViewer stylesheet and change the selector to `.pdf-toggle-btn, .segmgr-open-btn`). If you cannot find it quickly, add a minimal rule to the same CSS file:

```css
.segmgr-open-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.35rem;
    border: 1px solid var(--border-color, rgba(148, 163, 184, 0.25));
    background: transparent;
    color: var(--gray-400, #94a3b8);
    border-radius: 6px;
    cursor: pointer;
}
.segmgr-open-btn:hover { color: #fbbf24; border-color: rgba(245, 158, 11, 0.4); }
```

- [ ] **Step 5: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/scenes/SceneViewer.jsx
git commit -m "feat(segments): open SegmentManager from the Scenes header"
```

---

## Task 5: Frontend — colour segment chips by type

Now that `segment_type` is in the scene payload (Task 2), colour every segment chip by type using the shared `segmentTint` util instead of the fixed amber.

**Files:**
- Modify: `frontend/src/components/scenes/SceneList.jsx` (chip ~line 192) + `frontend/src/components/scenes/SceneList.css` (`.scene-segment-chip`)
- Modify: `frontend/src/components/board/boardModel.js` (~line 149) + `frontend/src/components/board/StripCard.jsx` (~line 143)
- Modify: `frontend/src/components/schedule/ScheduleSceneCard.jsx` (~lines 109, 149)
- Modify: `frontend/src/components/reports/Stripboard.jsx` (~line 413)

**Interfaces:**
- Consumes: `segmentTint(type) → { background, border, color }` from `frontend/src/utils/segmentTint.js` (Task 3); `scene.segment_type` (Task 2).

- [ ] **Step 1: SceneList chip**

In `SceneList.jsx`, add the import near the top:

```jsx
import { segmentTint } from '../../utils/segmentTint';
```

Replace the existing segment chip block (currently `<span className="scene-segment-chip" title={scene.story_day_label}>{scene.story_day_label || 'Segment'}</span>`) with:

```jsx
                                        {!scene.story_day && scene.segment_id && (
                                            <span
                                                className="scene-segment-chip"
                                                style={segmentTint(scene.segment_type)}
                                                title={scene.story_day_label}
                                            >
                                                {scene.story_day_label || 'Segment'}
                                            </span>
                                        )}
```

Then in `SceneList.css`, change `.scene-segment-chip` to keep only layout (drop its hard-coded amber `background`/`border`/`color`, which the inline style now supplies):

```css
.scene-segment-chip {
    display: inline-flex;
    align-items: center;
    max-width: 120px;
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    flex-shrink: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
```

- [ ] **Step 2: Board strip chip**

In `boardModel.js`, next to the existing `segmentId: scene.segment_id,` line (~149), add:

```javascript
            segmentType: scene.segment_type,
```

In `StripCard.jsx`, add the import:

```jsx
import { segmentTint } from '../../utils/segmentTint';
```

Replace the existing strip segment chip (currently `<span className="strip-segment-chip" title={strip.storyDayLabel}>...`) with:

```jsx
                {!strip.storyDay && strip.segmentId && (
                    <span className="strip-segment-chip" style={segmentTint(strip.segmentType)} title={strip.storyDayLabel}>
                        {strip.storyDayLabel || 'Segment'}
                    </span>
                )}
```

- [ ] **Step 3: Schedule card chips**

In `ScheduleSceneCard.jsx`, add the import:

```jsx
import { segmentTint } from '../../utils/segmentTint';
```

Add `style={segmentTint(scene.segment_type)}` to both segment spans (the `.ssc-segment` span ~line 109 and the `.ssc-tt-segment` span ~line 149). For example the first becomes:

```jsx
                {!storyDay && scene.segment_id && (
                    <span className="ssc-story-day ssc-segment" style={segmentTint(scene.segment_type)} title={scene.story_day_label}>
                        {scene.story_day_label || 'Segment'}
                    </span>
                )}
```

and the second:

```jsx
                        {!storyDay && scene.segment_id && (
                            <span className="ssc-tt-badge ssc-tt-segment" style={segmentTint(scene.segment_type)}>{scene.story_day_label || 'Segment'}</span>
                        )}
```

- [ ] **Step 4: Reports Stripboard chip**

In `reports/Stripboard.jsx`, add the import:

```jsx
import { segmentTint } from '../../utils/segmentTint';
```

Add `style={segmentTint(scene.segment_type)}` to the segment badge (~line 413):

```jsx
                        {!scene.story_day && scene.segment_id && (
                            <span className="sb-day-badge sb-segment-badge" style={segmentTint(scene.segment_type)} title={scene.story_day_label}>
                                {scene.story_day_label || 'Segment'}
                            </span>
                        )}
```

- [ ] **Step 5: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/scenes/SceneList.jsx frontend/src/components/scenes/SceneList.css frontend/src/components/board/boardModel.js frontend/src/components/board/StripCard.jsx frontend/src/components/schedule/ScheduleSceneCard.jsx frontend/src/components/reports/Stripboard.jsx
git commit -m "feat(segments): colour segment chips by type across views"
```

---

## Self-Review Notes

- **Spec coverage:** rename → Task 1 (recalc) + Task 3 (inline edit); recolour-by-type → Task 3 (picker) + Task 2/5 (visible everywhere); reorder → Task 3 (`display_order` swap); delete → Task 3 (confirm) + existing FK/recalc; create row → Task 3; scene count → Task 3 (from `scenes`); entry point → Task 4; rename-staleness fix → Task 1; colour-invisibility fix → Task 2 + Task 5. All spec sections map to a task.
- **Colour source of truth:** `segmentTint`/`segmentDotColor` in `frontend/src/utils/segmentTint.js` (Task 3) is the only place tints are defined; the panel and all five display chips consume it — no palette duplication.
- **No new endpoints:** reorder/recolour/rename all use the existing `updateSegment`; delete uses `deleteSegment`. Confirmed against the Global Constraints.
- **Assumptions flagged for the implementer:** Task 4 assumes the scene-refetch is named `refreshScenes` and that `.sidebar-header-actions` / `.pdf-toggle-btn` exist as anchors — the steps tell the implementer to grep and adapt if a name differs.
