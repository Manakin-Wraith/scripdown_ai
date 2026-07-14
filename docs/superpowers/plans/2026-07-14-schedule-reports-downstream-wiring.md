# Schedule → Reports Downstream Wiring — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the report engine schedule-aware so the Schedule flows into the existing Report Studio pipeline (library, share, live preview, PDF), and retire the bespoke `SchedulePrintView`.

**Architecture:** One optional `schedule_id` is threaded through `aggregate_scene_data` → `generate_report`/`render_preview_html` → routes → frontend. When present, aggregation groups scenes by shooting day (from `shooting_day_scenes` + `shooting_days`) instead of script order. Three report types become schedule-backed (`one_liner`, `day_out_of_days`, new `shooting_schedule`); everything else is untouched. Two synchronized UI entry points: a `Generate ▾` deep-link on the Schedule page and a `Source: Schedule ▾` selector in the Report Studio rail.

**Tech Stack:** Backend — Flask (Python 3.13), supabase-py, pytest, WeasyPrint (HTML→PDF). Frontend — React 18 + Vite (plain JSX), axios via `apiService.js`, react-router-dom.

## Global Constraints

- Data access is Supabase only (service-role client `self.db.client`); never SQLite.
- Backend gate: `pytest tests/` must pass. Frontend gate: `npm run build` must pass (`npm run lint` is broken repo-wide — do not gate on it).
- Scene numbers come from script text, never invented.
- All frontend backend calls go through the single `frontend/src/services/apiService.js` — no per-feature axios instances.
- Schedule-backed report types render an empty state (not fake data, not an error) when no `schedule_id` is supplied.
- Old saved reports render from their stored `data_snapshot` — do not break snapshot-based rendering.

---

## File Structure

**Backend**
- `backend/services/report_service.py` — aggregation gains `schedule_id`; new DOOD compute helper; rewritten `_render_one_liner`/`_render_day_out_of_days`; new `_render_shooting_schedule`; `REPORT_TYPES` metadata + dispatch.
- `backend/routes/report_routes.py` — thread `schedule_id` through generate + preview-html routes.
- `backend/tests/test_schedule_reports.py` — new test module for schedule-aware aggregation, DOOD math, renderers.

**Frontend**
- `frontend/src/services/apiService.js` — `scheduleId` args on `generateReport`/`previewReportHtml`.
- `frontend/src/components/reports/ReportStudio.jsx` — `scheduleId` state, deep-link params, wiring, empty state.
- `frontend/src/components/reports/ReportRail.jsx` — `Source: Schedule ▾` selector.
- `frontend/src/components/schedule/ShootingSchedulePage.jsx` — `Generate ▾` menu, remove print modal.
- **Delete:** `frontend/src/components/schedule/SchedulePrintView.jsx`, `frontend/src/components/schedule/SchedulePrintView.css`.

---

## Task 1: Schedule-aware aggregation

**Files:**
- Modify: `backend/services/report_service.py` (`aggregate_scene_data`, currently line 554)
- Test: `backend/tests/test_schedule_reports.py` (create)

**Interfaces:**
- Consumes: existing `self.db.get_scenes(script_id)`, `self.db.client.table(...)`, `self._filter_scenes(scenes, filters)`.
- Produces: `aggregate_scene_data(self, script_id, filters=None, schedule_id=None, include_unscheduled=True) -> Dict`. When `schedule_id` is set the returned dict gains:
  - `data['schedule'] = {'id': str, 'name': str}`
  - `data['days'] = [{'id','day_number','shoot_date','status','scenes':[scene,...],'total_eighths':int,'cast':[str],'locations':[str]}]` (days ordered by `day_number`, scenes ordered by `sort_order`)
  - `data['unscheduled'] = [scene,...]` (present only when `include_unscheduled=True`)
  - Each `scene` in a day is the joined row shape from `shooting_day_scenes.select('*, scenes(...)')`, flattened to the scene dict.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_schedule_reports.py`:

```python
import pytest
from unittest.mock import MagicMock
from services.report_service import ReportService


def _svc_with_days(days_rows, day_scene_rows_by_day, scenes):
    """Build a ReportService whose db returns the given fixtures."""
    svc = ReportService()
    svc.db = MagicMock()
    svc.db.get_script.return_value = {'title': 'Test', 'total_pages': 10}
    svc.db.get_scenes.return_value = scenes

    # supabase-py fluent chain: table(...).select(...).eq(...).order(...).execute()
    def table(name):
        tbl = MagicMock()
        chain = MagicMock()
        tbl.select.return_value = chain
        chain.eq.return_value = chain
        chain.neq.return_value = chain
        chain.order.return_value = chain
        if name == 'shooting_schedules':
            chain.single.return_value.execute.return_value.data = {'id': 'sch1', 'name': 'Schedule 1'}
        elif name == 'shooting_days':
            chain.execute.return_value.data = days_rows
        elif name == 'shooting_day_scenes':
            # eq(shooting_day_id, X) → rows for that day; capture via side_effect
            def eq_side(col, val):
                inner = MagicMock()
                inner.order.return_value.execute.return_value.data = day_scene_rows_by_day.get(val, [])
                return inner
            chain.eq.side_effect = eq_side
            chain.execute.return_value.data = []
        else:
            chain.execute.return_value.data = []
        return tbl
    svc.db.client.table.side_effect = table
    return svc


def test_aggregate_groups_scenes_by_shooting_day():
    scenes = [
        {'id': 's1', 'scene_number': '1', 'characters': ['ALICE'], 'page_length_eighths': 8, 'setting': 'KITCHEN'},
        {'id': 's2', 'scene_number': '2', 'characters': ['BOB'], 'page_length_eighths': 8, 'setting': 'BAR'},
        {'id': 's3', 'scene_number': '3', 'characters': ['ALICE'], 'page_length_eighths': 8, 'setting': 'KITCHEN'},
    ]
    days_rows = [
        {'id': 'd1', 'day_number': 1, 'shoot_date': '2026-08-01', 'status': 'draft'},
        {'id': 'd2', 'day_number': 2, 'shoot_date': None, 'status': 'draft'},
    ]
    day_scene_rows = {
        'd1': [{'scene_id': 's1', 'sort_order': 0, 'scenes': scenes[0]}],
        'd2': [{'scene_id': 's2', 'sort_order': 0, 'scenes': scenes[1]}],
    }
    svc = _svc_with_days(days_rows, day_scene_rows, scenes)

    data = svc.aggregate_scene_data('scr1', schedule_id='sch1')

    assert [d['day_number'] for d in data['days']] == [1, 2]
    assert [s['scene_number'] for s in data['days'][0]['scenes']] == ['1']
    assert data['days'][0]['total_eighths'] == 8
    assert data['days'][0]['cast'] == ['ALICE']
    # s3 is on no day → unscheduled
    assert [s['scene_number'] for s in data['unscheduled']] == ['3']
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_schedule_reports.py::test_aggregate_groups_scenes_by_shooting_day -v`
Expected: FAIL — `aggregate_scene_data() got an unexpected keyword argument 'schedule_id'`.

- [ ] **Step 3: Implement schedule grouping**

In `backend/services/report_service.py`, change the signature and add day-grouping. Replace the `def aggregate_scene_data(self, script_id: str, filters: Optional[Dict] = None) -> Dict[str, Any]:` line with:

```python
    def aggregate_scene_data(self, script_id: str, filters: Optional[Dict] = None,
                             schedule_id: Optional[str] = None,
                             include_unscheduled: bool = True) -> Dict[str, Any]:
```

Then, immediately before the final `return {` block (currently ~line 726), insert the day-grouping build. It reuses the already-filtered `scenes` list in scope:

```python
        # ── Schedule-aware grouping ────────────────────────────────────────────
        schedule_block = None
        days_block = None
        unscheduled_block = None
        if schedule_id:
            sched = self.db.client.table('shooting_schedules').select(
                'id, name').eq('id', schedule_id).single().execute().data
            schedule_block = {'id': schedule_id, 'name': (sched or {}).get('name', 'Schedule')}

            scene_by_id = {s.get('id'): s for s in scenes}
            included_ids = set(scene_by_id.keys())

            day_rows = self.db.client.table('shooting_days').select('*').eq(
                'schedule_id', schedule_id).order('day_number', desc=False).execute().data or []

            days_block = []
            scheduled_ids = set()
            for d in day_rows:
                ds_rows = self.db.client.table('shooting_day_scenes').select(
                    '*, scenes(id, scene_number, setting, location_canonical, int_ext, '
                    'time_of_day, story_day, characters, page_length_eighths, page_start, '
                    'page_end, is_omitted)'
                ).eq('shooting_day_id', d['id']).order('sort_order', desc=False).execute().data or []

                day_scenes = []
                for row in ds_rows:
                    sid = row.get('scene_id')
                    scene = row.get('scenes') or scene_by_id.get(sid)
                    if not scene or sid not in included_ids:
                        continue  # filtered out or missing
                    scheduled_ids.add(sid)
                    day_scenes.append(scene)

                active = [s for s in day_scenes if not s.get('is_omitted')]
                cast, locs = set(), set()
                for s in active:
                    for c in (s.get('characters') or []):
                        cast.add(c if isinstance(c, str) else c.get('name', str(c)))
                    locs.add(s.get('location_canonical') or s.get('setting') or 'UNKNOWN')
                days_block.append({
                    'id': d['id'],
                    'day_number': d.get('day_number'),
                    'shoot_date': d.get('shoot_date'),
                    'status': d.get('status', 'draft'),
                    'scenes': day_scenes,
                    'total_eighths': sum(s.get('page_length_eighths', 8) for s in active),
                    'cast': sorted(cast),
                    'locations': sorted(locs),
                })

            if include_unscheduled:
                unscheduled_block = [scene_by_id[i] for i in included_ids if i not in scheduled_ids]
```

Then add these keys inside the returned dict (after `'scenes': scenes,`):

```python
            'schedule': schedule_block,
            'days': days_block,
            'unscheduled': unscheduled_block,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_schedule_reports.py::test_aggregate_groups_scenes_by_shooting_day -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/report_service.py backend/tests/test_schedule_reports.py
git commit -m "feat(reports): schedule-aware aggregation via schedule_id"
```

---

## Task 2: Day Out of Days computation (S/W/H/F)

**Files:**
- Modify: `backend/services/report_service.py` (add module-level `compute_dood`)
- Test: `backend/tests/test_schedule_reports.py`

**Interfaces:**
- Consumes: `data['days']` shape from Task 1.
- Produces: module-level `compute_dood(days: list) -> dict` returning:
  `{'day_numbers': [int,...], 'cast': [{'name': str, 'cells': {day_number: 'S'|'W'|'H'|'F'|''}, 'work_days': int, 'hold_days': int, 'span': int}]}`.
  Rules: first appearance day = `S`; last = `F`; appearance days between = `W`; non-appearance days between S and F = `H`; outside the span = `''`. `span = F_index - S_index + 1` counted in shoot days. Cast ordered by start day then name. If a member appears on a single day, that day is `S` (start and finish collapse to `S`).

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_schedule_reports.py`:

```python
from services.report_service import compute_dood


def _day(n, *char_lists):
    return {'day_number': n, 'scenes': [{'characters': cl} for cl in char_lists]}


def test_compute_dood_start_work_hold_finish():
    days = [
        _day(1, ['ALICE']),            # ALICE start
        _day(2, ['BOB']),              # ALICE hold, BOB start
        _day(3, ['ALICE', 'BOB']),     # ALICE work, BOB work
        _day(4, ['BOB']),              # ALICE finished before this; BOB finish
    ]
    dood = compute_dood(days)
    assert dood['day_numbers'] == [1, 2, 3, 4]

    alice = next(c for c in dood['cast'] if c['name'] == 'ALICE')
    assert alice['cells'] == {1: 'S', 2: 'H', 3: 'F', 4: ''}
    assert alice['work_days'] == 2 and alice['hold_days'] == 1 and alice['span'] == 3

    bob = next(c for c in dood['cast'] if c['name'] == 'BOB')
    assert bob['cells'] == {1: '', 2: 'S', 3: 'W', 4: 'F'}
    assert bob['work_days'] == 3 and bob['hold_days'] == 0 and bob['span'] == 3


def test_compute_dood_single_day_actor():
    days = [_day(1, ['CARL']), _day(2, [])]
    dood = compute_dood(days)
    carl = next(c for c in dood['cast'] if c['name'] == 'CARL')
    assert carl['cells'] == {1: 'S', 2: ''}
    assert carl['work_days'] == 1 and carl['hold_days'] == 0 and carl['span'] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_schedule_reports.py -k compute_dood -v`
Expected: FAIL — `ImportError: cannot import name 'compute_dood'`.

- [ ] **Step 3: Implement compute_dood**

Add at module scope in `backend/services/report_service.py` (near the top, after imports):

```python
def compute_dood(days: list) -> dict:
    """Compute a Day Out of Days grid from ordered shooting days.

    Returns day_numbers plus per-cast cells of 'S'/'W'/'H'/'F'/'' and totals.
    """
    day_numbers = [d.get('day_number') for d in days]

    # cast name -> set of day indices they appear on
    appearances = {}
    for idx, d in enumerate(days):
        for scene in (d.get('scenes') or []):
            for c in (scene.get('characters') or []):
                name = c if isinstance(c, str) else c.get('name', str(c))
                appearances.setdefault(name, set()).add(idx)

    cast = []
    for name, idxs in appearances.items():
        if not idxs:
            continue
        start, finish = min(idxs), max(idxs)
        cells, work, hold = {}, 0, 0
        for idx, dn in enumerate(day_numbers):
            if idx < start or idx > finish:
                cells[dn] = ''
            elif idx == start:
                cells[dn] = 'S'; work += 1
            elif idx == finish:
                cells[dn] = 'F'; work += 1
            elif idx in idxs:
                cells[dn] = 'W'; work += 1
            else:
                cells[dn] = 'H'; hold += 1
        cast.append({
            'name': name, 'cells': cells,
            'work_days': work, 'hold_days': hold,
            'span': finish - start + 1,
            '_start': start,
        })

    cast.sort(key=lambda c: (c['_start'], c['name']))
    for c in cast:
        del c['_start']
    return {'day_numbers': day_numbers, 'cast': cast}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_schedule_reports.py -k compute_dood -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add backend/services/report_service.py backend/tests/test_schedule_reports.py
git commit -m "feat(reports): Day Out of Days S/W/H/F computation"
```

---

## Task 3: Report type registry + schedule_id threading

**Files:**
- Modify: `backend/services/report_service.py` (`REPORT_TYPES`, `VALID_REPORT_TYPES`, `generate_report`, `render_preview_html`, render dispatch)
- Modify: `backend/routes/report_routes.py` (generate + preview-html routes)
- Test: `backend/tests/test_schedule_reports.py`

**Interfaces:**
- Consumes: `aggregate_scene_data(..., schedule_id=...)` (Task 1).
- Produces:
  - `REPORT_TYPES` entries gain `'requires_schedule': bool`; new `'shooting_schedule'` entry.
  - `generate_report(self, script_id, report_type, config=None, title=None, user_id=None, filters=None, schedule_id=None)` — stores `schedule_id` in `merged_config['schedule_id']` and passes to aggregation.
  - `render_preview_html(self, script_id, report_type, config=None, title=None, filters=None, schedule_id=None)`.
  - Routes read `schedule_id` from request JSON and pass it through.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_schedule_reports.py`:

```python
def test_report_types_flag_schedule_backed():
    svc = ReportService()
    assert svc.REPORT_TYPES['day_out_of_days'].get('requires_schedule') is True
    assert svc.REPORT_TYPES['one_liner'].get('requires_schedule') is True
    assert svc.REPORT_TYPES['shooting_schedule'].get('requires_schedule') is True
    assert svc.REPORT_TYPES['scene_breakdown'].get('requires_schedule', False) is False


def test_shooting_schedule_is_valid_type():
    svc = ReportService()
    assert 'shooting_schedule' in svc.VALID_REPORT_TYPES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_schedule_reports.py -k "schedule_backed or valid_type" -v`
Expected: FAIL — `KeyError: 'shooting_schedule'` / assertion on missing `requires_schedule`.

- [ ] **Step 3: Update registry + threading**

In `backend/services/report_service.py`:

Update `REPORT_TYPES` — add `requires_schedule` to the three schedule-backed types and add the new type:

```python
        'day_out_of_days': {
            'name': 'Day Out of Days',
            'description': 'Cast working/hold days across the shooting schedule',
            'requires_schedule': True
        },
        ...
        'one_liner': {
            'name': 'One-Liner / Stripboard',
            'description': 'Compact scene list in shooting order',
            'requires_schedule': True
        },
        'shooting_schedule': {
            'name': 'Shooting Schedule',
            'description': 'Full day-by-day shooting schedule',
            'requires_schedule': True
        },
```

Add `"shooting_schedule"` to the `VALID_REPORT_TYPES` list (currently ~line 215).

Thread `schedule_id` in `generate_report` — change signature to add `schedule_id: Optional[str] = None`, then have it read from config as fallback and pass through:

```python
        schedule_id = schedule_id or (config or {}).get('schedule_id')
        data = self.aggregate_scene_data(script_id, filters=filters, schedule_id=schedule_id)
```

and ensure it persists — after `merged_config = config or {}`:

```python
        if schedule_id:
            merged_config['schedule_id'] = schedule_id
```

Thread `schedule_id` in `render_preview_html` — add `schedule_id: Optional[str] = None` param, read fallback from config, and pass to aggregation:

```python
        schedule_id = schedule_id or (config or {}).get('schedule_id')
        data = self.aggregate_scene_data(script_id, filters=filters, schedule_id=schedule_id)
```

In `backend/routes/report_routes.py`, in `generate_report`, read and pass it:

```python
        schedule_id = data.get('schedule_id')
        ...
        report = report_service.generate_report(
            script_id=script_id,
            report_type=report_type,
            config=config,
            title=title,
            filters=filters,
            schedule_id=schedule_id,
        )
```

And in `preview_report_html`, read and pass it:

```python
        schedule_id = data.get('schedule_id')
        ...
        result = report_service.render_preview_html(
            script_id=script_id,
            report_type=report_type,
            config=config,
            title=title,
            filters=filters,
            schedule_id=schedule_id,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_schedule_reports.py -k "schedule_backed or valid_type" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/report_service.py backend/routes/report_routes.py backend/tests/test_schedule_reports.py
git commit -m "feat(reports): register shooting_schedule + thread schedule_id through generate/preview"
```

---

## Task 4: Schedule-backed renderers (one_liner, DOOD, shooting_schedule)

**Files:**
- Modify: `backend/services/report_service.py` (`_render_one_liner`, `_render_day_out_of_days`, new `_render_shooting_schedule`, dispatch, empty-state helper)
- Reference (port markup): `frontend/src/components/schedule/SchedulePrintView.jsx`, `SchedulePrintView.css`
- Test: `backend/tests/test_schedule_reports.py`

**Interfaces:**
- Consumes: `data['days']`, `data['unscheduled']`, `data['schedule']` (Task 1); `compute_dood` (Task 2).
- Produces: three renderers returning HTML strings that consume day-grouped data; a `_render_schedule_empty_state(report_type)` returned when `data.get('days')` is falsy; dispatch routes `shooting_schedule` to `_render_shooting_schedule`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_schedule_reports.py`:

```python
def _data_with_days():
    return {
        'script': {'title': 'Test', 'writer': 'W', 'draft': '', 'total_pages': 10},
        'schedule': {'id': 'sch1', 'name': 'Schedule 1'},
        'days': [
            {'id': 'd1', 'day_number': 1, 'shoot_date': '2026-08-01', 'status': 'draft',
             'total_eighths': 8, 'cast': ['ALICE'], 'locations': ['KITCHEN'],
             'scenes': [{'scene_number': '1', 'int_ext': 'INT', 'setting': 'KITCHEN',
                         'time_of_day': 'DAY', 'characters': ['ALICE'],
                         'page_length_eighths': 8, 'is_omitted': False}]},
        ],
        'unscheduled': [],
    }


def test_render_one_liner_has_day_banner_and_totals():
    svc = ReportService()
    html = svc._render_one_liner(_data_with_days())
    assert 'Day 1' in html
    assert 'KITCHEN' in html
    assert 'Scene' in html or '1' in html


def test_render_shooting_schedule_renders_days():
    svc = ReportService()
    html = svc._render_shooting_schedule(_data_with_days())
    assert 'Day 1' in html
    assert '2026-08-01' in html


def test_render_dood_lists_cast():
    svc = ReportService()
    html = svc._render_day_out_of_days(_data_with_days())
    assert 'ALICE' in html
    assert 'S' in html


def test_schedule_backed_empty_state_when_no_days():
    svc = ReportService()
    html = svc._render_one_liner({'script': {'title': 'T'}, 'days': None})
    assert 'schedule' in html.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_schedule_reports.py -k "render_one_liner or shooting_schedule or render_dood or empty_state" -v`
Expected: FAIL — `_render_shooting_schedule` missing / old `_render_one_liner` ignores `days`.

- [ ] **Step 3: Implement renderers**

In `backend/services/report_service.py`, add an empty-state helper:

```python
    def _render_schedule_empty_state(self, report_type: str) -> str:
        name = self.REPORT_TYPES.get(report_type, {}).get('name', 'This report')
        return (
            '<div class="report-empty" style="padding:48px;text-align:center;color:#555">'
            f'<h2>{name} needs a shooting schedule</h2>'
            '<p>Select a schedule as the source, or build one on the Schedule tab, '
            'then generate this report.</p></div>'
        )
```

Replace the body of `_render_one_liner` so it consumes `days` (fall back to empty state):

```python
    def _render_one_liner(self, data: Dict) -> str:
        days = data.get('days')
        if not days:
            return self._render_schedule_empty_state('one_liner')
        rows = []
        for d in days:
            date = d.get('shoot_date') or ''
            rows.append(
                f'<tr class="ol-daybreak"><td colspan="5"><strong>Day {d.get("day_number")}</strong>'
                f' &middot; {date} &middot; {format_eighths(d.get("total_eighths", 0))} pgs'
                f' &middot; {len(d.get("scenes", []))} sc &middot; {len(d.get("cast", []))} cast</td></tr>'
            )
            for s in d.get('scenes', []):
                rows.append(
                    '<tr>'
                    f'<td>{s.get("scene_number","")}</td>'
                    f'<td>{s.get("int_ext","")}</td>'
                    f'<td>{s.get("location_canonical") or s.get("setting","")}</td>'
                    f'<td>{s.get("time_of_day","")}</td>'
                    f'<td>{format_eighths(s.get("page_length_eighths",8))}</td>'
                    '</tr>'
                )
        return (
            '<table class="report-table one-liner"><thead><tr>'
            '<th>Sc</th><th>I/E</th><th>Set</th><th>D/N</th><th>Pgs</th>'
            '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
        )
```

Replace the body of `_render_day_out_of_days` so it consumes `compute_dood(days)`:

```python
    def _render_day_out_of_days(self, data: Dict) -> str:
        days = data.get('days')
        if not days:
            return self._render_schedule_empty_state('day_out_of_days')
        dood = compute_dood(days)
        head = ''.join(f'<th>{dn}</th>' for dn in dood['day_numbers'])
        body = []
        for c in dood['cast']:
            cells = ''.join(f'<td>{c["cells"].get(dn,"")}</td>' for dn in dood['day_numbers'])
            body.append(
                f'<tr><td class="dood-name">{c["name"]}</td>{cells}'
                f'<td>{c["work_days"]}</td><td>{c["hold_days"]}</td><td>{c["span"]}</td></tr>'
            )
        return (
            '<table class="report-table dood"><thead><tr><th>Cast</th>' + head +
            '<th>Work</th><th>Hold</th><th>Span</th></tr></thead><tbody>' +
            ''.join(body) + '</tbody></table>'
        )
```

Add `_render_shooting_schedule` (port the day-section layout from `SchedulePrintView.jsx`):

```python
    def _render_shooting_schedule(self, data: Dict) -> str:
        days = data.get('days')
        if not days:
            return self._render_schedule_empty_state('shooting_schedule')
        sections = []
        for d in days:
            date = d.get('shoot_date') or 'No date'
            rows = ''.join(
                '<tr>'
                f'<td>{s.get("scene_number","")}</td>'
                f'<td>{s.get("int_ext","")}</td>'
                f'<td>{s.get("location_canonical") or s.get("setting","")}</td>'
                f'<td>{s.get("time_of_day","")}</td>'
                f'<td>{format_eighths(s.get("page_length_eighths",8))}</td>'
                f'<td>{", ".join(c if isinstance(c,str) else c.get("name","") for c in (s.get("characters") or []))}</td>'
                '</tr>'
                for s in d.get('scenes', [])
            )
            sections.append(
                f'<div class="sched-day"><h3>Day {d.get("day_number")} &middot; {date}</h3>'
                f'<div class="sched-day-meta">{format_eighths(d.get("total_eighths",0))} pgs'
                f' &middot; {len(d.get("cast",[]))} cast &middot; {len(d.get("locations",[]))} locations</div>'
                '<table class="report-table"><thead><tr>'
                '<th>Sc</th><th>I/E</th><th>Set</th><th>D/N</th><th>Pgs</th><th>Cast</th>'
                f'</tr></thead><tbody>{rows}</tbody></table></div>'
            )
        return ''.join(sections)
```

Add the dispatch branch in `_render_report_html` (after the `one_liner` branch, ~line 1080):

```python
        elif report_type == 'shooting_schedule':
            body = self._render_shooting_schedule(data)
```

> Note: `format_eighths` is already imported at the top of `report_service.py` from `utils.scene_calculations` (`from utils.scene_calculations import format_eighths, calculate_total_script_length`) and is used by the existing `_render_one_liner`/`_render_scene_breakdown`. Call it as a plain function (`format_eighths(...)`), not a method.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_schedule_reports.py -v`
Expected: PASS (all tests in the module).

- [ ] **Step 5: Commit**

```bash
git add backend/services/report_service.py backend/tests/test_schedule_reports.py
git commit -m "feat(reports): schedule-backed renderers for one-liner, DOOD, shooting schedule"
```

---

## Task 5: Frontend apiService — scheduleId params

**Files:**
- Modify: `frontend/src/services/apiService.js` (`generateReport` line 660, `previewReportHtml` line 704)

**Interfaces:**
- Consumes: existing axios instance and endpoints.
- Produces:
  - `generateReport(scriptId, reportType, title=null, config=null, filters=null, groupBy=null, categories=null, scheduleId=null)` — includes `schedule_id` in the POST body when set.
  - `previewReportHtml(scriptId, reportType, filters=null, groupBy=null, categories=null, title=null, scheduleId=null)` — includes `schedule_id` in the POST body when set.

- [ ] **Step 1: Update generateReport**

In `frontend/src/services/apiService.js`, extend `generateReport` (line 660). Add the param and include it in the request payload object (alongside `report_type`, `filters`, etc.):

```javascript
export const generateReport = async (scriptId, reportType, title = null, config = null, filters = null, groupBy = null, categories = null, scheduleId = null) => {
    // ...existing payload construction...
    // add to the body object:
    //   ...(scheduleId ? { schedule_id: scheduleId } : {})
```

Locate the object passed to `apiClient.post(...)` inside this function and add `...(scheduleId ? { schedule_id: scheduleId } : {})` to it.

- [ ] **Step 2: Update previewReportHtml**

Extend `previewReportHtml` (line 704) the same way — add `scheduleId = null` as the last param and `...(scheduleId ? { schedule_id: scheduleId } : {})` to its POST body.

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds (no syntax errors).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/apiService.js
git commit -m "feat(reports): pass scheduleId through generate/preview API calls"
```

---

## Task 6: Report Studio — scheduleId state, deep-link, empty state

**Files:**
- Modify: `frontend/src/components/reports/ReportStudio.jsx`

**Interfaces:**
- Consumes: `getSchedules(scriptId)` (apiService line 2006), `previewReportHtml`/`generateReport` with `scheduleId` (Task 5), `reportTypes[type].requires_schedule` (Task 3).
- Produces: `scheduleId` state + `schedules` list passed to `ReportRail` (Task 7); deep-link `?type=&schedule=` read on mount; schedule-backed types with no `scheduleId` skip preview and show a hint.

- [ ] **Step 1: Add state + load schedules**

In `ReportStudio.jsx`, add imports and state:

```javascript
import { useSearchParams } from 'react-router-dom';
import { getSchedules } from '../../services/apiService';
```

```javascript
    const [searchParams] = useSearchParams();
    const [scheduleId, setScheduleId] = useState(null);
    const [schedules, setSchedules] = useState([]);
```

Add a ref so the stable preview fn reads the latest scheduleId (mirroring `filtersRef`):

```javascript
    const scheduleIdRef = useRef(scheduleId);
    scheduleIdRef.current = scheduleId;
```

In the existing initial `fetchData` effect, also load schedules:

```javascript
                try {
                    const schedRes = await getSchedules(scriptId);
                    setSchedules(schedRes.schedules || []);
                } catch (e) { console.warn('schedules', e); }
```

- [ ] **Step 2: Read deep-link params on mount**

Add an effect after schedules load (depends on `schedules`, `reportTypes`):

```javascript
    useEffect(() => {
        const t = searchParams.get('type');
        const s = searchParams.get('schedule');
        if (t && reportTypes[t]) setSelectedType(t);
        if (s) setScheduleId(s);
        if (t || s) triggerPreview();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [schedules, reportTypes]);
```

- [ ] **Step 3: Pass scheduleId into preview + generate**

In `handleUpdatePreview`, add a guard and pass the id. Right after `const f = filtersRef.current;`:

```javascript
        const requiresSchedule = reportTypes[typeRef.current]?.requires_schedule;
        if (requiresSchedule && !scheduleIdRef.current) {
            setPreviewHtml('');
            setPreviewError('Select a schedule source to generate this report.');
            setPreviewLoading(false);
            return;
        }
```

Change the preview call to pass the id (last arg):

```javascript
            const res = await previewReportHtml(scriptId, typeRef.current, activeFilters, groupBy, categories, titleRef.current || null, scheduleIdRef.current);
```

In `handleGenerate`, pass `scheduleId` as the final arg to `generateReport`:

```javascript
            const res = await generateReport(scriptId, selectedType, customTitle || null, null, activeFilters, groupBy, categories, scheduleId);
```

- [ ] **Step 4: Pass schedule props to the rail**

Add to the `ReportRail` props in the JSX:

```javascript
                        schedules={schedules}
                        scheduleId={scheduleId}
                        onScheduleChange={(id) => { setScheduleId(id); triggerPreview(); }}
```

- [ ] **Step 5: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/reports/ReportStudio.jsx
git commit -m "feat(reports): Report Studio schedule source state + deep-link"
```

---

## Task 7: Report Rail — Source selector

**Files:**
- Modify: `frontend/src/components/reports/ReportRail.jsx`

**Interfaces:**
- Consumes: `reportTypes[selectedType].requires_schedule` (Task 3); `schedules`, `scheduleId`, `onScheduleChange` props (Task 6).
- Produces: a `Source: Schedule ▾` section rendered only when the selected type is schedule-backed.

- [ ] **Step 1: Add the selector**

In `ReportRail.jsx`, extend the destructured props:

```javascript
const ReportRail = ({
    reportTypes,
    selectedType,
    onSelectType,
    customTitle,
    onTitleChange,
    filterPanelProps,
    schedules = [],
    scheduleId = null,
    onScheduleChange,
}) => {
```

Add a source section immediately after the `rail-type-list` closing tags, before the filters section:

```javascript
            {reportTypes?.[selectedType]?.requires_schedule && (
                <div className="rail-section">
                    <span className="rail-label">Source schedule</span>
                    <select
                        className="rail-title-input"
                        value={scheduleId || ''}
                        onChange={(e) => onScheduleChange?.(e.target.value || null)}
                    >
                        <option value="">— Select a schedule —</option>
                        {schedules.map((s) => (
                            <option key={s.id} value={s.id}>{s.name}</option>
                        ))}
                    </select>
                </div>
            )}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/reports/ReportRail.jsx
git commit -m "feat(reports): rail source-schedule selector for schedule-backed types"
```

---

## Task 8: Schedule page — Generate ▾ menu, retire the bespoke print

**Files:**
- Modify: `frontend/src/components/schedule/ShootingSchedulePage.jsx`
- Delete: `frontend/src/components/schedule/SchedulePrintView.jsx`, `frontend/src/components/schedule/SchedulePrintView.css`

**Interfaces:**
- Consumes: `useNavigate` (already imported), `activeScheduleId`, `scriptId`.
- Produces: a `Generate ▾` dropdown that navigates to `/scripts/${scriptId}/reports?type=<type>&schedule=${activeScheduleId}` for `one_liner` / `day_out_of_days` / `shooting_schedule`.

- [ ] **Step 1: Replace the print button with a Generate menu**

In `ShootingSchedulePage.jsx`, remove the `showPrintPreview` state, the print-preview `useEffect` (body-scroll lock), the `Print / Export` button, and the entire `{showPrintPreview && (...)}` modal block. Remove the `SchedulePrintView` import and the `Printer` import if unused elsewhere.

Add a small dropdown state near the other state hooks:

```javascript
    const [genMenuOpen, setGenMenuOpen] = useState(false);
```

Replace the print button (lines ~186-195) with:

```javascript
                    {activeScheduleId && days.length > 0 && (
                        <div className="schedule-gen-wrapper">
                            <button
                                className="schedule-print-btn"
                                onClick={() => setGenMenuOpen((o) => !o)}
                                title="Generate a report from this schedule"
                            >
                                <FileText size={14} /> Generate ▾
                            </button>
                            {genMenuOpen && (
                                <div className="schedule-gen-menu" onMouseLeave={() => setGenMenuOpen(false)}>
                                    {[
                                        ['one_liner', 'One-Liner / Stripboard'],
                                        ['day_out_of_days', 'Day Out of Days'],
                                        ['shooting_schedule', 'Shooting Schedule'],
                                    ].map(([type, label]) => (
                                        <button
                                            key={type}
                                            className="schedule-gen-item"
                                            onClick={() => {
                                                setGenMenuOpen(false);
                                                navigate(`/scripts/${scriptId}/reports?type=${type}&schedule=${activeScheduleId}`);
                                            }}
                                        >
                                            {label}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
```

Update the `lucide-react` import line to include `FileText` and drop `Printer` if it is now unused:

```javascript
import { Plus, CalendarDays, Trash2, Pencil, Check, X, ZoomIn, ZoomOut, Maximize, RotateCcw, FileText } from 'lucide-react';
```

- [ ] **Step 2: Add minimal menu styling**

In `frontend/src/components/schedule/ShootingSchedule.css`, append:

```css
.schedule-gen-wrapper { position: relative; display: inline-block; }
.schedule-gen-menu {
    position: absolute; top: 100%; right: 0; margin-top: 4px; z-index: 50;
    background: var(--surface, #fff); border: 1px solid var(--border, #ddd);
    border-radius: 6px; box-shadow: 0 4px 16px rgba(0,0,0,.12); min-width: 200px;
}
.schedule-gen-item {
    display: block; width: 100%; text-align: left; padding: 8px 12px;
    background: none; border: none; cursor: pointer; font-size: 13px;
}
.schedule-gen-item:hover { background: var(--surface-hover, #f3f4f6); }
```

- [ ] **Step 3: Delete SchedulePrintView**

```bash
git rm frontend/src/components/schedule/SchedulePrintView.jsx frontend/src/components/schedule/SchedulePrintView.css
```

- [ ] **Step 4: Verify no dangling references + build**

Run: `cd frontend && grep -rn "SchedulePrintView" src/ ; npm run build`
Expected: grep prints nothing; build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/schedule/ShootingSchedulePage.jsx frontend/src/components/schedule/ShootingSchedule.css
git commit -m "feat(schedule): Generate menu deep-links to Reports; retire SchedulePrintView"
```

---

## Task 9: Regression + full verification

**Files:** none (verification only)

- [ ] **Step 1: Backend regression — scene-based types ignore schedule_id**

Append to `backend/tests/test_schedule_reports.py`:

```python
def test_scene_based_type_ignores_schedule_id():
    scenes = [{'id': 's1', 'scene_number': '1', 'characters': ['ALICE'],
               'page_length_eighths': 8, 'setting': 'KITCHEN'}]
    svc = ReportService()
    svc.db = MagicMock()
    svc.db.get_script.return_value = {'title': 'T', 'total_pages': 1}
    svc.db.get_scenes.return_value = scenes
    svc.db.client.table.return_value.select.return_value.eq.return_value.neq.return_value.execute.return_value.data = []
    data = svc.aggregate_scene_data('scr1')  # no schedule_id
    assert data.get('days') is None
    assert data['summary']['total_scenes'] == 1
```

Run: `cd backend && pytest tests/test_schedule_reports.py -v`
Expected: PASS.

- [ ] **Step 2: Full backend suite**

Run: `cd backend && pytest tests/`
Expected: PASS (no regressions in the existing report tests).

- [ ] **Step 3: Full frontend build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Manual smoke (documented, run if a dev server is available)**

1. Open a script with a schedule that has ≥2 days and assigned scenes.
2. On the Schedule tab, click `Generate ▾` → `Day Out of Days`. Confirm it navigates to Reports with the DOOD type selected, the source schedule pre-filled, and a live preview showing the cast grid.
3. In the rail, switch `Source schedule` and confirm the preview refreshes.
4. Select a schedule-backed type with the source cleared → confirm the empty-state message, not fake data.
5. Click Generate → confirm the report saves to the Library and Share/Download work.
6. Confirm the old Print/Export modal no longer exists on the Schedule tab.

- [ ] **Step 5: Commit (if any test files changed)**

```bash
git add backend/tests/test_schedule_reports.py
git commit -m "test(reports): regression — scene-based types ignore schedule_id"
```

---

## Self-Review Notes

- **Spec coverage:** §1 data contract → Tasks 1, 3, 5, 6. §2 report types (one_liner/DOOD/shooting_schedule, requires-schedule, full_breakdown wrinkle, old-snapshot wrinkle) → Tasks 3, 4 + Task 9 regression; the `full_breakdown` upgrade is covered by Task 1 supplying `days` when a `schedule_id` is passed (its embedded `_render_day_out_of_days` now reads `days`). §3 entry points (push + rail) → Tasks 6, 7, 8. §4 retire print → Task 8.
- **Old snapshot safety:** renderers read from `data` which, for saved reports, is the stored `data_snapshot`; empty-state only triggers when `days` is falsy, so pre-existing snapshots without `days` fall to the empty state rather than crashing — acceptable since new generation always includes `days`.
- **Deferred (not in plan, per spec):** `call_sheet`, the upstream unscheduled-scenes bin, and the nav/naming refactor.
- **Verified:** the eighths-formatting helper is the module-level `format_eighths` (imported from `utils.scene_calculations`), used as a plain function — not a method on the service.
