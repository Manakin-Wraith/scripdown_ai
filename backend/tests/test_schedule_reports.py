import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock
from services.report_service import ReportService


def _svc_with_days(days_rows, day_scene_rows_by_day, scenes, schedule_rows=None):
    """Build a ReportService whose db returns the given fixtures."""
    svc = ReportService()
    svc.db = MagicMock()
    svc.db.get_script.return_value = {'title': 'Test', 'total_pages': 10}
    svc.db.get_scenes.return_value = scenes

    if schedule_rows is None:
        schedule_rows = [{'id': 'sch1', 'name': 'Schedule 1'}]

    # supabase-py fluent chain: table(...).select(...).eq(...).order(...).execute()
    def table(name):
        tbl = MagicMock()
        chain = MagicMock()
        tbl.select.return_value = chain
        chain.eq.return_value = chain
        chain.neq.return_value = chain
        chain.order.return_value = chain
        if name == 'shooting_schedules':
            chain.limit.return_value.execute.return_value.data = schedule_rows
            chain.single.return_value.execute.side_effect = Exception('no rows')
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


def test_aggregate_missing_schedule_degrades_gracefully():
    scenes = [
        {'id': 's1', 'scene_number': '1', 'characters': ['ALICE'], 'page_length_eighths': 8, 'setting': 'KITCHEN'},
    ]
    svc = _svc_with_days(days_rows=[], day_scene_rows_by_day={}, scenes=scenes, schedule_rows=[])

    data = svc.aggregate_scene_data('scr1', schedule_id='gone')

    assert data['days'] is None
    assert data['schedule'] is None
    assert data['unscheduled'] is None


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


def test_report_types_flag_schedule_backed():
    svc = ReportService()
    assert svc.REPORT_TYPES['day_out_of_days'].get('requires_schedule') is True
    assert svc.REPORT_TYPES['one_liner'].get('requires_schedule') is True
    assert svc.REPORT_TYPES['shooting_schedule'].get('requires_schedule') is True
    assert svc.REPORT_TYPES['scene_breakdown'].get('requires_schedule', False) is False


def test_shooting_schedule_is_valid_type():
    svc = ReportService()
    assert 'shooting_schedule' in svc.VALID_REPORT_TYPES


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


def test_full_breakdown_dood_scene_fallback_without_schedule():
    """full_breakdown must fall back to scene-based DOOD when there is no shooting schedule."""
    svc = ReportService()
    data = {
        'summary': {},
        'scenes': [],
        'characters': {
            'ALICE': {'count': 2, 'scenes': ['1', '3'], 'story_days': ['1']},
        },
        'locations': {},
    }
    html = svc._render_full_breakdown(data)
    assert 'ALICE' in html
    assert 'Character Schedule' in html
    assert 'needs a shooting schedule' not in html
