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


import routes.segment_routes as seg_routes


class RouteFakeDB:
    def __init__(self):
        self.updates = []
        # script_access is monkeypatched per-test to ignore this, but
        # _check_script evaluates db.client as an argument regardless.
        self.client = None

    def get_timeline_segment(self, segment_id):
        return {'id': segment_id, 'script_id': 'scr-1', 'name': 'Old Name'}

    def get_scene_script_id(self, scene_id):
        return 'scr-1'

    def update_scene(self, scene_id, **kwargs):
        self.updates.append((scene_id, kwargs))
        return {'id': scene_id, **kwargs}

    def update_timeline_segment(self, segment_id, **kwargs):
        return {'id': segment_id, 'script_id': 'scr-1', **kwargs}


def test_attach_scenes_clears_flags_and_recalcs(monkeypatch):
    fake = RouteFakeDB()
    recalced = {}
    monkeypatch.setattr(seg_routes, 'db', fake)
    monkeypatch.setattr(seg_routes, 'script_access', lambda *a, **k: 'ok')
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


def test_attach_scenes_forbidden_for_non_owner(monkeypatch):
    fake = RouteFakeDB()
    monkeypatch.setattr(seg_routes, 'db', fake)
    monkeypatch.setattr(seg_routes, 'script_access', lambda *a, **k: 'forbidden')
    monkeypatch.setenv('FLASK_ENV', 'development')

    from flask import Flask
    flask_app = Flask(__name__)
    flask_app.register_blueprint(seg_routes.segment_bp)
    with flask_app.test_client() as client:
        resp = client.post(
            '/api/segments/seg-A/scenes',
            json={'scene_ids': ['sc-2'], 'script_id': 'scr-1'},
        )

    assert resp.status_code == 403
    assert fake.updates == []  # no scene mutated when authorization fails


def test_attach_rejects_cross_script_scene_without_mutation(monkeypatch):
    fake = RouteFakeDB()
    monkeypatch.setattr(seg_routes, 'db', fake)
    monkeypatch.setattr(seg_routes, 'script_access', lambda *a, **k: 'ok')
    # Scene belongs to a different script than the segment.
    monkeypatch.setattr(fake, 'get_scene_script_id', lambda scene_id: 'other-script')
    monkeypatch.setenv('FLASK_ENV', 'development')

    from flask import Flask
    flask_app = Flask(__name__)
    flask_app.register_blueprint(seg_routes.segment_bp)
    with flask_app.test_client() as client:
        resp = client.post(
            '/api/segments/seg-A/scenes',
            json={'scene_ids': ['sc-2'], 'script_id': 'scr-1'},
        )
    assert resp.status_code == 400
    assert fake.updates == []  # nothing mutated when validation fails


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

    import middleware.authorization as authz
    monkeypatch.setattr(authz, 'get_script_role', lambda sid, uid: 'owner')

    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(sup_routes.supabase_bp)
    with app.test_client() as client:
        resp = client.get('/api/scripts/scr-1/scenes')

    body = resp.get_json()
    by_id = {s['id']: s for s in body['scenes']}
    assert by_id['sc-1']['segment_type'] == 'FLASHBACK'
    assert by_id['sc-2']['segment_type'] is None
