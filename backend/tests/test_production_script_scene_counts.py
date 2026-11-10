"""Production script cards need real analysis progress.

scripts.analysis_status is not maintained (all rows stay 'pending'), so the
production payload reports per-script counts derived from scenes, like the
script library does.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.production_service import attach_scene_counts
from test_production_member_routes import MockSupabase


def _scene(sid, script_id, status):
    return {"id": sid, "script_id": script_id, "analysis_status": status}


def test_attach_scene_counts_derives_progress_from_scenes():
    store = {"scenes": [
        _scene("a", "s1", "complete"), _scene("b", "s1", "complete"),
        _scene("c", "s1", "analyzing"), _scene("d", "s1", "failed"),
        _scene("e", "s1", "pending"),
        _scene("f", "s2", "complete"),
    ]}
    scripts = [{"id": "s1", "analysis_status": "pending"}, {"id": "s2", "analysis_status": "pending"}]

    out = attach_scene_counts(MockSupabase(store), scripts)

    assert out[0]["scene_count"] == 5
    assert out[0]["analyzed_scenes"] == 2
    assert out[0]["analyzing_scenes"] == 1
    assert out[0]["failed_scenes"] == 1
    assert (out[1]["scene_count"], out[1]["analyzed_scenes"]) == (1, 1)


def test_attach_scene_counts_script_without_scenes_is_zero():
    out = attach_scene_counts(MockSupabase({"scenes": []}), [{"id": "s9"}])
    assert (out[0]["scene_count"], out[0]["analyzed_scenes"],
            out[0]["analyzing_scenes"], out[0]["failed_scenes"]) == (0, 0, 0, 0)


def test_attach_scene_counts_empty_list():
    assert attach_scene_counts(MockSupabase({}), []) == []
