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
