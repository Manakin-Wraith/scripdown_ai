# Timeline Segments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users manually group flashback/montage scenes into named "timeline segments" that carry their own identity, are excluded from the numeric story-day continuity count, but remain fully schedulable.

**Architecture:** A new `timeline_segments` table holds one row per segment; scenes gain a nullable `segment_id` FK. The story-day recalc skips segment scenes (no `story_day` number, no counter advance, excluded from `total_story_days`) and labels them with the segment name. A small `segment_bp` Flask blueprint exposes CRUD + attach/detach, each mutation ending in a recalc. Frontend gets `apiService` methods, a segment-assignment control on `SceneDetail`, and label rendering for segment scenes across the scene/board/report views.

**Tech Stack:** Flask (Python 3.13), `supabase-py` (service-role key), pytest; React 18 + Vite (plain JSX), axios via `apiService.js`.

## Global Constraints

- Data access is Supabase only (project `slateone`/`twzfaizeyqwevmhjyicz`), via the service-role `db` singleton in `backend/db/supabase_client.py`. Never SQLite.
- Backend gate: `pytest tests/` (run in `backend/`). Frontend gate: `npm run build` (run in `frontend/`) — `npm run lint` is known-broken repo-wide, do not gate on it.
- All frontend backend calls go through the single axios instance in `frontend/src/services/apiService.js`. No new axios instances.
- A scene belongs to the numeric story-day timeline **or** to a segment, never both: when `segment_id IS NOT NULL`, its `story_day` is `NULL`.
- Segment types are the existing timeline codes: `FLASHBACK`, `DREAM`, `FANTASY`, `MONTAGE`, `TITLE_CARD`.

---

## File Structure

- Create: `backend/db/migrations/040_timeline_segments.sql` — table + column + indexes.
- Modify: `backend/db/supabase_client.py` — segment CRUD methods; add `segment_id` to `get_scenes_ordered` select.
- Modify: `backend/services/story_day_service.py` — recalc skips segment scenes; summary counts segments.
- Create: `backend/routes/segment_routes.py` — `segment_bp` CRUD + attach/detach.
- Modify: `backend/app.py` — register `segment_bp`.
- Create: `backend/tests/test_timeline_segments.py` — recalc + route logic tests.
- Modify: `frontend/src/services/apiService.js` — segment API methods.
- Modify: `frontend/src/components/scenes/SceneDetail.jsx` — segment-assignment control + segment label.
- Modify: `frontend/src/components/scenes/SceneList.jsx`, `frontend/src/components/board/StripCard.jsx`, `frontend/src/components/schedule/ScheduleSceneCard.jsx`, `frontend/src/components/reports/Stripboard.jsx` — render segment name for segment scenes.

---

## Task 1: Database migration

**Files:**
- Create: `backend/db/migrations/040_timeline_segments.sql`

**Interfaces:**
- Produces: table `timeline_segments (id, script_id, name, segment_type, display_order, color, created_at)`; column `scenes.segment_id uuid` nullable.

- [ ] **Step 1: Write the migration SQL**

```sql
-- 040_timeline_segments.sql
-- Off-timeline flashback/montage grouping. See
-- docs/superpowers/specs/2026-07-14-timeline-segments-design.md

CREATE TABLE IF NOT EXISTS timeline_segments (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id     uuid NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    name          text NOT NULL,
    segment_type  text NOT NULL DEFAULT 'FLASHBACK',
    display_order integer NOT NULL DEFAULT 0,
    color         text,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_timeline_segments_script
    ON timeline_segments(script_id);

ALTER TABLE scenes
    ADD COLUMN IF NOT EXISTS segment_id uuid
    REFERENCES timeline_segments(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_scenes_segment
    ON scenes(segment_id);
```

- [ ] **Step 2: Apply the migration to Supabase**

Apply via the Supabase MCP `apply_migration` tool (name `040_timeline_segments`) or the SQL editor against project `twzfaizeyqwevmhjyicz`. Verify:

Run (SQL editor): `SELECT column_name FROM information_schema.columns WHERE table_name='scenes' AND column_name='segment_id';`
Expected: one row, `segment_id`.

- [ ] **Step 3: Commit**

```bash
git add backend/db/migrations/040_timeline_segments.sql
git commit -m "feat(db): timeline_segments table + scenes.segment_id"
```

---

## Task 2: DB client — segment CRUD + segment_id in ordered fetch

**Files:**
- Modify: `backend/db/supabase_client.py:355-371` (`get_scenes_ordered` select) and append new methods after `update_script_total_story_days` (ends line 394)

**Interfaces:**
- Consumes: `self.client` (supabase client), existing `update_scene(scene_id, **kwargs)`.
- Produces:
  - `create_timeline_segment(script_id: str, name: str, segment_type: str = 'FLASHBACK', color: str = None, display_order: int = 0) -> dict`
  - `get_timeline_segments(script_id: str) -> list`
  - `update_timeline_segment(segment_id: str, **kwargs) -> dict`
  - `delete_timeline_segment(segment_id: str) -> bool`
  - `get_scenes_ordered` rows now include `segment_id`.

- [ ] **Step 1: Add `segment_id` to the `get_scenes_ordered` select**

In `get_scenes_ordered`, change the select string (currently ending `...'story_day_is_manual, story_day_is_locked, timeline_code'`) to also request `segment_id`:

```python
        result = self.client.table('scenes').select(
            'id, script_id, scene_number, scene_number_original, scene_order, '
            'int_ext, setting, time_of_day, description, '
            'story_day, story_day_label, time_transition, '
            'is_new_story_day, story_day_confidence, '
            'story_day_is_manual, story_day_is_locked, timeline_code, segment_id'
        ).eq('script_id', script_id).order('scene_order').execute()
```

- [ ] **Step 2: Append segment CRUD methods** (immediately after `update_script_total_story_days`, before the singleton block at line 396)

```python
    # ============================================
    # Timeline Segments (flashbacks / montages)
    # ============================================

    def create_timeline_segment(self, script_id: str, name: str,
                                segment_type: str = 'FLASHBACK',
                                color: str = None, display_order: int = 0) -> dict:
        """Create a timeline segment for a script."""
        data = {
            'script_id': script_id,
            'name': name,
            'segment_type': segment_type,
            'color': color,
            'display_order': display_order,
        }
        result = self.client.table('timeline_segments').insert(data).execute()
        return result.data[0] if result.data else None

    def get_timeline_segments(self, script_id: str) -> list:
        """List timeline segments for a script, ordered by display_order."""
        result = self.client.table('timeline_segments').select('*') \
            .eq('script_id', script_id).order('display_order').execute()
        return result.data or []

    def update_timeline_segment(self, segment_id: str, **kwargs) -> dict:
        """Update a timeline segment (name/segment_type/color/display_order)."""
        result = self.client.table('timeline_segments').update(kwargs) \
            .eq('id', segment_id).execute()
        return result.data[0] if result.data else None

    def delete_timeline_segment(self, segment_id: str) -> bool:
        """Delete a timeline segment. Member scenes' segment_id is SET NULL by FK."""
        self.client.table('timeline_segments').delete().eq('id', segment_id).execute()
        return True
```

- [ ] **Step 3: Sanity-check import**

Run: `cd backend && python -c "from db.supabase_client import db; print(hasattr(db, 'create_timeline_segment'), hasattr(db, 'get_timeline_segments'))"`
Expected: `True True`

- [ ] **Step 4: Commit**

```bash
git add backend/db/supabase_client.py
git commit -m "feat(db): timeline segment CRUD methods + segment_id in ordered fetch"
```

---

## Task 3: Recalc skips segment scenes + summary counts

**Files:**
- Modify: `backend/services/story_day_service.py` (`recalculate_story_days`, `get_story_day_summary`)
- Test: `backend/tests/test_timeline_segments.py`

**Interfaces:**
- Consumes: `db.get_scenes_ordered` (rows now include `segment_id`), `db.get_timeline_segments`, `db.bulk_update_story_days`, `db.update_script_total_story_days`.
- Produces: after recalc, scenes with `segment_id` have `story_day=None` and `story_day_label=<segment name>`; `get_story_day_summary` returns extra key `segment_scene_count`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_timeline_segments.py`:

```python
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.story_day_service as sds


class FakeDB:
    """In-memory stand-in for the supabase db singleton used by recalc."""

    def __init__(self, scenes, segments):
        self._scenes = scenes
        self._segments = segments
        self.total_days_written = None

    def get_scenes_ordered(self, script_id):
        return self._scenes

    def get_timeline_segments(self, script_id):
        return self._segments

    def bulk_update_story_days(self, updates):
        by_id = {s['id']: s for s in self._scenes}
        for u in updates:
            by_id[u['id']]['story_day'] = u['story_day']
            by_id[u['id']]['story_day_label'] = u['story_day_label']
        return True

    def update_script_total_story_days(self, script_id, total_days):
        self.total_days_written = total_days
        return {}


def _scene(order, **kw):
    base = {
        'id': f'sc-{order}', 'scene_order': order, 'story_day': None,
        'story_day_label': None, 'time_transition': '', 'timeline_code': 'PRESENT',
        'is_new_story_day': False, 'story_day_is_locked': False, 'segment_id': None,
    }
    base.update(kw)
    return base


def test_segment_scene_excluded_from_count_and_labeled(monkeypatch):
    # Day 1: sc1. sc2 is in a segment. sc3 resumes present (new day).
    scenes = [
        _scene(1),
        _scene(2, segment_id='seg-A'),
        _scene(3, is_new_story_day=True),
    ]
    segments = [{'id': 'seg-A', 'name': 'Training Montage'}]
    fake = FakeDB(scenes, segments)
    monkeypatch.setattr(sds, 'db', fake)

    result = sds.recalculate_story_days('scr-1', start_from_order=0)

    by_id = {s['id']: s for s in scenes}
    assert by_id['sc-1']['story_day'] == 1
    # Segment scene: no numeric day, labeled with segment name
    assert by_id['sc-2']['story_day'] is None
    assert by_id['sc-2']['story_day_label'] == 'Training Montage'
    # Counter is NOT advanced by the segment; sc3's new-day bump goes 1 -> 2
    assert by_id['sc-3']['story_day'] == 2
    # total_days excludes the segment scene
    assert result['total_days'] == 2
    assert fake.total_days_written == 2
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && pytest tests/test_timeline_segments.py::test_segment_scene_excluded_from_count_and_labeled -v`
Expected: FAIL (segment scene gets a numeric `story_day` today, and label is `None`/`"Flashback — Day N"`).

- [ ] **Step 3: Implement — build a segment-name map and skip segment scenes**

In `recalculate_story_days`, right after `scenes = db.get_scenes_ordered(script_id)` and the empty-guard (after line 44), add:

```python
    # Map segment_id -> name for labeling off-timeline scenes.
    segment_names = {s['id']: s.get('name') for s in db.get_timeline_segments(script_id)}
```

Then, inside the `for i, scene in enumerate(scenes):` loop, immediately after computing `scene_order` and the `start_from_order` skip block (after line 65, before the "Respect locked days" block), insert:

```python
        # Off-timeline scenes (flashback/montage segments): no numeric day,
        # do not advance the counter, label with the segment name.
        seg_id = scene.get('segment_id')
        if seg_id:
            label = segment_names.get(seg_id) or 'Segment'
            if scene.get('story_day') is not None or scene.get('story_day_label') != label:
                scenes_to_update.append({
                    'id': scene['id'],
                    'story_day': None,
                    'story_day_label': label,
                })
            scene['story_day'] = None
            scene['story_day_label'] = label
            continue
```

(The existing `all_days` set at the bottom already excludes these because their `story_day` is now `None`.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && pytest tests/test_timeline_segments.py::test_segment_scene_excluded_from_count_and_labeled -v`
Expected: PASS

- [ ] **Step 5: Add the summary test**

Append to `backend/tests/test_timeline_segments.py`:

```python
def test_summary_counts_segment_scenes_separately(monkeypatch):
    scenes = [
        _scene(1, story_day=1),
        _scene(2, segment_id='seg-A', story_day=None),
        _scene(3, story_day=None),  # genuinely unassigned present-day scene
    ]
    segments = [{'id': 'seg-A', 'name': 'Dream'}]
    monkeypatch.setattr(sds, 'db', FakeDB(scenes, segments))

    summary = sds.get_story_day_summary('scr-1')

    assert summary['segment_scene_count'] == 1
    assert summary['unassigned_count'] == 1  # only the non-segment null-day scene
    assert summary['scenes_per_day'] == {1: 1}
```

- [ ] **Step 6: Run it to verify it fails**

Run: `cd backend && pytest tests/test_timeline_segments.py::test_summary_counts_segment_scenes_separately -v`
Expected: FAIL with `KeyError: 'segment_scene_count'`.

- [ ] **Step 7: Implement the summary change**

In `get_story_day_summary`, add a `segment_scenes` counter. Replace the loop and return (lines 186-206) with:

```python
    scenes_per_day = {}
    timeline_breakdown = {}
    unassigned = 0
    segment_scenes = 0

    for scene in scenes:
        sd = scene.get('story_day')
        tc = scene.get('timeline_code', 'PRESENT')

        if scene.get('segment_id'):
            segment_scenes += 1
        elif sd is not None:
            scenes_per_day[sd] = scenes_per_day.get(sd, 0) + 1
        else:
            unassigned += 1

        timeline_breakdown[tc] = timeline_breakdown.get(tc, 0) + 1

    return {
        'total_days': len(scenes_per_day),
        'scenes_per_day': scenes_per_day,
        'timeline_breakdown': timeline_breakdown,
        'unassigned_count': unassigned,
        'segment_scene_count': segment_scenes,
    }
```

Also update the early empty-return dict (lines 178-183) to include `'segment_scene_count': 0`.

- [ ] **Step 8: Run the full test file**

Run: `cd backend && pytest tests/test_timeline_segments.py -v`
Expected: both tests PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/services/story_day_service.py backend/tests/test_timeline_segments.py
git commit -m "feat(story-days): recalc skips segment scenes; summary counts them separately"
```

---

## Task 4: Segment routes blueprint

**Files:**
- Create: `backend/routes/segment_routes.py`
- Modify: `backend/app.py:20` (import) and `:54` (register)
- Test: `backend/tests/test_timeline_segments.py` (append route tests)

**Interfaces:**
- Consumes: `db` segment methods (Task 2), `recalculate_story_days` (Task 3), `require_auth`/`get_user_id` from `middleware.auth`.
- Produces: blueprint `segment_bp` with routes:
  - `GET    /api/scripts/<script_id>/segments`
  - `POST   /api/scripts/<script_id>/segments`
  - `PATCH  /api/segments/<segment_id>`
  - `DELETE /api/segments/<segment_id>?script_id=<id>`
  - `POST   /api/segments/<segment_id>/scenes`  body `{ "scene_ids": [...], "script_id": "..." }`
  - `DELETE /api/segments/<segment_id>/scenes/<scene_id>?script_id=<id>`

- [ ] **Step 1: Write the blueprint**

Create `backend/routes/segment_routes.py`:

```python
"""
Timeline Segment Routes for SlateOne (ScripDown AI)

CRUD for off-timeline flashback/montage segments plus scene attach/detach.
Every mutation ends with a story-day recalc so the numeric timeline and
total_story_days stay correct. See
docs/superpowers/specs/2026-07-14-timeline-segments-design.md
"""

from flask import Blueprint, request, jsonify
from middleware.auth import require_auth
from db.supabase_client import db
from services.story_day_service import recalculate_story_days

segment_bp = Blueprint('segments', __name__)

VALID_TYPES = {'FLASHBACK', 'DREAM', 'FANTASY', 'MONTAGE', 'TITLE_CARD'}


@segment_bp.route('/api/scripts/<script_id>/segments', methods=['GET'])
@require_auth
def list_segments(script_id):
    segments = db.get_timeline_segments(script_id)
    return jsonify({'segments': segments}), 200


@segment_bp.route('/api/scripts/<script_id>/segments', methods=['POST'])
@require_auth
def create_segment(script_id):
    body = request.get_json() or {}
    name = (body.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400
    segment_type = body.get('segment_type', 'FLASHBACK')
    if segment_type not in VALID_TYPES:
        return jsonify({'error': f'invalid segment_type: {segment_type}'}), 400
    segment = db.create_timeline_segment(
        script_id=script_id,
        name=name,
        segment_type=segment_type,
        color=body.get('color'),
        display_order=body.get('display_order', 0),
    )
    return jsonify({'segment': segment}), 201


@segment_bp.route('/api/segments/<segment_id>', methods=['PATCH'])
@require_auth
def update_segment(segment_id):
    body = request.get_json() or {}
    allowed = {k: body[k] for k in ('name', 'segment_type', 'color', 'display_order')
               if k in body}
    if 'segment_type' in allowed and allowed['segment_type'] not in VALID_TYPES:
        return jsonify({'error': 'invalid segment_type'}), 400
    if not allowed:
        return jsonify({'error': 'no updatable fields provided'}), 400
    segment = db.update_timeline_segment(segment_id, **allowed)
    return jsonify({'segment': segment}), 200


@segment_bp.route('/api/segments/<segment_id>', methods=['DELETE'])
@require_auth
def delete_segment(segment_id):
    script_id = request.args.get('script_id')
    db.delete_timeline_segment(segment_id)
    if script_id:
        # Member scenes fell back to the timeline via ON DELETE SET NULL.
        recalculate_story_days(script_id, start_from_order=0)
    return jsonify({'success': True}), 200


@segment_bp.route('/api/segments/<segment_id>/scenes', methods=['POST'])
@require_auth
def attach_scenes(segment_id):
    body = request.get_json() or {}
    scene_ids = body.get('scene_ids') or []
    script_id = body.get('script_id')
    if not scene_ids or not script_id:
        return jsonify({'error': 'scene_ids and script_id are required'}), 400
    for scene_id in scene_ids:
        # Joining a segment clears manual day flags and the numeric day.
        db.update_scene(
            scene_id,
            segment_id=segment_id,
            story_day=None,
            is_new_story_day=False,
            story_day_is_locked=False,
        )
    recalculate_story_days(script_id, start_from_order=0)
    return jsonify({'success': True}), 200


@segment_bp.route('/api/segments/<segment_id>/scenes/<scene_id>', methods=['DELETE'])
@require_auth
def detach_scene(segment_id, scene_id):
    script_id = request.args.get('script_id')
    db.update_scene(scene_id, segment_id=None)
    if script_id:
        recalculate_story_days(script_id, start_from_order=0)
    return jsonify({'success': True}), 200
```

- [ ] **Step 2: Register the blueprint in `app.py`**

Add the import near the other route imports (after line 20):

```python
from routes.segment_routes import segment_bp
```

Add the registration after the `schedule_bp` line (after line 54):

```python
app.register_blueprint(segment_bp)  # Timeline segment routes at /api/segments/* and /api/scripts/:id/segments
```

- [ ] **Step 3: Write the route logic test (attach clears flags + recalcs)**

Append to `backend/tests/test_timeline_segments.py`:

```python
import routes.segment_routes as seg_routes


class RouteFakeDB:
    def __init__(self):
        self.updates = []

    def update_scene(self, scene_id, **kwargs):
        self.updates.append((scene_id, kwargs))
        return {'id': scene_id, **kwargs}


def test_attach_scenes_clears_flags_and_recalcs(monkeypatch):
    fake = RouteFakeDB()
    recalced = {}
    monkeypatch.setattr(seg_routes, 'db', fake)
    monkeypatch.setattr(seg_routes, 'recalculate_story_days',
                        lambda script_id, start_from_order=0: recalced.update(
                            {'script_id': script_id, 'start': start_from_order}))

    app = seg_routes.segment_bp
    # Invoke the view function directly with a pushed request context.
    from flask import Flask
    flask_app = Flask(__name__)
    flask_app.register_blueprint(app)
    # Bypass @require_auth by disabling it is not needed: use test client with
    # auth disabled via FLASK_ENV dev bypass.
    monkeypatch.setenv('FLASK_ENV', 'development')

    with flask_app.test_client() as client:
        resp = client.post(
            '/api/segments/seg-A/scenes',
            json={'scene_ids': ['sc-2'], 'script_id': 'scr-1'},
        )

    assert resp.status_code == 200
    scene_id, kwargs = fake.updates[0]
    assert scene_id == 'sc-2'
    assert kwargs['segment_id'] == 'seg-A'
    assert kwargs['story_day'] is None
    assert kwargs['is_new_story_day'] is False
    assert kwargs['story_day_is_locked'] is False
    assert recalced == {'script_id': 'scr-1', 'start': 0}
```

Note: `@require_auth` honors the `FLASK_ENV=development` dev bypass (`DEV_USER_ID`) documented in CLAUDE.md, so the test client call is authorized. If your local `require_auth` does not bypass without `DEV_USER_ID` set, also `monkeypatch.setenv('DEV_USER_ID', 'test-user')`.

- [ ] **Step 4: Run the route test to verify it fails**

Run: `cd backend && pytest tests/test_timeline_segments.py::test_attach_scenes_clears_flags_and_recalcs -v`
Expected: FAIL before the blueprint exists / passes only once `segment_routes.py` is in place. (If Step 1–2 are already done, it should pass — in that case confirm it fails by temporarily importing before creating the file is unnecessary; proceed.)

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && pytest tests/ -q`
Expected: all pass (new file green, no regressions).

- [ ] **Step 6: Commit**

```bash
git add backend/routes/segment_routes.py backend/app.py backend/tests/test_timeline_segments.py
git commit -m "feat(api): timeline segment CRUD + scene attach/detach blueprint"
```

---

## Task 5: Frontend apiService methods

**Files:**
- Modify: `frontend/src/services/apiService.js` (append after existing scene helpers, e.g. after `deleteSceneById` ~line 240)

**Interfaces:**
- Consumes: the shared `api` axios instance already defined in the file.
- Produces: `getSegments`, `createSegment`, `updateSegment`, `deleteSegment`, `attachScenesToSegment`, `detachSceneFromSegment`.

- [ ] **Step 1: Add the API methods**

```javascript
// ============================================
// Timeline Segments (flashbacks / montages)
// ============================================

export const getSegments = async (scriptId) => {
    const response = await api.get(`/api/scripts/${scriptId}/segments`);
    return response.data.segments || [];
};

export const createSegment = async (scriptId, { name, segment_type = 'FLASHBACK', color = null }) => {
    const response = await api.post(`/api/scripts/${scriptId}/segments`, { name, segment_type, color });
    return response.data.segment;
};

export const updateSegment = async (segmentId, updates) => {
    const response = await api.patch(`/api/segments/${segmentId}`, updates);
    return response.data.segment;
};

export const deleteSegment = async (segmentId, scriptId) => {
    const response = await api.delete(`/api/segments/${segmentId}`, { params: { script_id: scriptId } });
    return response.data;
};

export const attachScenesToSegment = async (segmentId, scriptId, sceneIds) => {
    const response = await api.post(`/api/segments/${segmentId}/scenes`, { script_id: scriptId, scene_ids: sceneIds });
    return response.data;
};

export const detachSceneFromSegment = async (segmentId, sceneId, scriptId) => {
    const response = await api.delete(`/api/segments/${segmentId}/scenes/${sceneId}`, { params: { script_id: scriptId } });
    return response.data;
};
```

- [ ] **Step 2: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/apiService.js
git commit -m "feat(api-client): timeline segment endpoints"
```

---

## Task 6: SceneDetail — assign scene to a segment + show segment label

**Files:**
- Modify: `frontend/src/components/scenes/SceneDetail.jsx` (story-day controls block ~lines 429-460; imports at top)

**Interfaces:**
- Consumes: `getSegments`, `createSegment`, `attachScenesToSegment`, `detachSceneFromSegment` from `apiService`; `useStoryDayNotify` from `StoryDayContext`; the `scene` prop (now carries `segment_id`, and `story_day_label` = segment name when in a segment).
- Produces: UI to move the current scene into a segment (existing or newly named) and to remove it; a badge showing the segment name for segment scenes.

- [ ] **Step 1: Add imports and segment state**

At the top of `SceneDetail.jsx`, add to the `apiService` import and context import:

```javascript
import { getSegments, createSegment, attachScenesToSegment, detachSceneFromSegment } from '../../services/apiService';
import { useStoryDayNotify } from '../../context/StoryDayContext';
```

Inside the component body (near the other `useState` hooks around line 97):

```javascript
    const notifyStoryDayChange = useStoryDayNotify();
    const [segments, setSegments] = useState([]);
    const [segmentMenuOpen, setSegmentMenuOpen] = useState(false);

    useEffect(() => {
        if (!scene?.script_id) return;
        getSegments(scene.script_id).then(setSegments).catch(() => setSegments([]));
    }, [scene?.script_id]);

    const handleAssignSegment = async (segmentId) => {
        await attachScenesToSegment(segmentId, scene.script_id, [scene.id]);
        setSegmentMenuOpen(false);
        notifyStoryDayChange(scene.script_id);
    };

    const handleCreateAndAssign = async (name) => {
        const seg = await createSegment(scene.script_id, { name });
        await handleAssignSegment(seg.id);
    };

    const handleRemoveFromSegment = async () => {
        await detachSceneFromSegment(scene.segment_id, scene.id, scene.script_id);
        notifyStoryDayChange(scene.script_id);
    };
```

- [ ] **Step 2: Render the segment badge / assignment control**

In the `story-day-controls` block, add a branch for segment scenes. Immediately after the closing of the `{!scene.story_day && !storyDayEditing && (...)}` block (the "No Day" button, ~line 458), insert:

```jsx
                        {scene.segment_id && (
                            <button
                                className="story-day-badge timeline-segment editable-badge"
                                onClick={handleRemoveFromSegment}
                                title="Click to remove from segment (returns to story-day timeline)"
                            >
                                <CalendarDays size={12} />
                                {scene.story_day_label || 'Segment'}
                            </button>
                        )}
                        {!scene.segment_id && (
                            <div className="segment-assign">
                                <button
                                    className="story-day-badge editable-badge"
                                    onClick={() => setSegmentMenuOpen(o => !o)}
                                    title="Move to a flashback/montage segment (off the story-day count)"
                                >
                                    + Segment
                                </button>
                                {segmentMenuOpen && (
                                    <div className="segment-assign-menu">
                                        {segments.map(seg => (
                                            <button key={seg.id} onClick={() => handleAssignSegment(seg.id)}>
                                                {seg.name}
                                            </button>
                                        ))}
                                        <button
                                            onClick={() => {
                                                const name = window.prompt('New segment name (e.g. "Training Montage")');
                                                if (name && name.trim()) handleCreateAndAssign(name.trim());
                                            }}
                                        >
                                            + New segment…
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}
```

- [ ] **Step 3: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/scenes/SceneDetail.jsx
git commit -m "feat(ui): assign scenes to timeline segments from SceneDetail"
```

---

## Task 7: Render segment name for segment scenes across views

Segment scenes have `story_day = null`, so views that gate day chips on `scene.story_day` currently render nothing for them. Add a fallback that shows `story_day_label` (the segment name) when `segment_id` is set.

**Files:**
- Modify: `frontend/src/components/scenes/SceneList.jsx:129,187`
- Modify: `frontend/src/components/board/StripCard.jsx:138`
- Modify: `frontend/src/components/schedule/ScheduleSceneCard.jsx:108,143`
- Modify: `frontend/src/components/reports/Stripboard.jsx:187`

**Interfaces:**
- Consumes: `scene.segment_id`, `scene.story_day_label`; `StripCard` uses a `strip` model (`strip.storyDay`) — confirm whether the strip model carries `segmentId`/`segmentLabel`; if not, thread them through from the scene where the strip is built.

- [ ] **Step 1: SceneList — show the segment chip on the row**

In `SceneList.jsx`, next to the existing `{scene.story_day && (<span…>D{scene.story_day}</span>)}` at line ~187, add:

```jsx
                                        {!scene.story_day && scene.segment_id && (
                                            <span className="scene-segment-chip" title={scene.story_day_label}>
                                                {scene.story_day_label || 'Segment'}
                                            </span>
                                        )}
```

- [ ] **Step 2: ScheduleSceneCard — show the segment name where the day badge is**

In `ScheduleSceneCard.jsx`, after line 108 (`{storyDay && <span className="ssc-story-day">D{storyDay}</span>}`), add:

```jsx
                {!storyDay && scene.segment_id && (
                    <span className="ssc-story-day ssc-segment" title={scene.story_day_label}>
                        {scene.story_day_label || 'Segment'}
                    </span>
                )}
```

- [ ] **Step 3: reports/Stripboard — keep segment scenes out of the day buckets, group them under a "Segments" label**

In `Stripboard.jsx`, the day-bucketing loop at line 187 (`if (scene.story_day) { … }`) already skips segment scenes (their `story_day` is null), so they won't inflate day buckets — no change needed there. Confirm segment scenes still render in the flat scene list (the filter block at line 205). No code change unless a day-only view hides them; if so, mirror the Step-1 chip pattern where scene rows render.

- [ ] **Step 4: StripCard — show segment label instead of the D-chip**

In `StripCard.jsx` at line 138, the chip is gated on `strip.storyDay`. If the strip model carries the segment name (check `boardModel.js` for a `segmentLabel`/`segmentId` field), render it; otherwise thread it in from the scene when strips are built in `boardModel.js`, then:

```jsx
                {strip.storyDay ? (
                    <span className="strip-day-chip">D{strip.storyDay}</span>
                ) : strip.segmentLabel ? (
                    <span className="strip-segment-chip" title={strip.segmentLabel}>{strip.segmentLabel}</span>
                ) : null}
```

If `boardModel.js` builds strips from scenes, add `segmentId: scene.segment_id` and `segmentLabel: scene.story_day_label` to the strip object there so the above renders.

- [ ] **Step 5: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 6: Manual smoke check**

Run: `cd frontend && npm run dev`, open a script, move a scene into a new segment via SceneDetail, and confirm:
- The scene loses its "Day N" and shows the segment name in SceneDetail, SceneList, and the schedule card.
- The story-day count elsewhere drops by that scene's former day (if it was a solo day).
- Removing it from the segment restores a numeric day.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/scenes/SceneList.jsx frontend/src/components/board/StripCard.jsx frontend/src/components/board/boardModel.js frontend/src/components/schedule/ScheduleSceneCard.jsx frontend/src/components/reports/Stripboard.jsx
git commit -m "feat(ui): show segment name for off-timeline scenes across views"
```

---

## Self-Review Notes

- **Spec coverage:** table + `segment_id` (Task 1); a-scene-is-timeline-or-segment invariant enforced in attach (Task 4) + recalc nulling (Task 3); exclusion from count + labeling (Task 3); still-schedulable rendering (Task 7); manual grouping UI (Task 6); join clears flags / leave falls back to recalc (Task 4 attach/detach + Task 3); API surface (Task 4); `apiService` calls only (Task 5). All spec sections map to a task.
- **Segment name on recalc:** recalc fetches `db.get_timeline_segments` once per run and maps `id -> name`; renaming a segment requires a recalc to refresh `story_day_label` — the PATCH route (Task 4) does **not** currently recalc. If live rename-label-refresh is desired, add `recalculate_story_days(script_id, 0)` to `update_segment` (needs `script_id`; fetch it from the segment row or pass as a query param). Left out of v1 to keep PATCH cheap; note for the implementer.
- **StripCard uncertainty:** Task 7 Step 4 depends on the `boardModel.js` strip shape; the step instructs verifying and threading `segmentId`/`segmentLabel` if absent.
