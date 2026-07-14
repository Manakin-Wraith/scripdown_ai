import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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
