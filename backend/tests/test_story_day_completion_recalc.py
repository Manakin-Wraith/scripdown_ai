"""Story-day recalc must do a FULL pass (start_from_order=0) when the
single-scene analysis path finishes the last scene of a script.

Root cause of NULL story days: the single-scene endpoint only ever did an
incremental recalc (start_from_order=current_order), and the Day-1 baseline in
recalculate_story_days is only set when start_from_order == 0. So a script
analyzed entirely through the single-scene path never got a full recalc and its
story_day column stayed NULL. This guards the completion-detection fix.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import routes.supabase_routes as sr


class _Resp:
    def __init__(self, count, data):
        self.count = count
        self.data = data


def _fake_supabase(count, data):
    class _Table:
        def select(self, *a, **k):
            return self

        def eq(self, *a, **k):
            return self

        def in_(self, *a, **k):
            return self

        def execute(self):
            return _Resp(count, data)

    return type("S", (), {"table": lambda self, _n: _Table()})()


def test_full_recalc_when_no_scenes_remaining(monkeypatch):
    # No scenes left pending/analyzing -> this was the last scene -> full recalc.
    monkeypatch.setattr(sr, "supabase", _fake_supabase(0, []))
    assert sr._recalc_start_order("scr-1", 5) == 0


def test_incremental_recalc_while_scenes_remain(monkeypatch):
    # Scenes still pending/analyzing -> mid-run -> incremental from current_order.
    monkeypatch.setattr(sr, "supabase", _fake_supabase(2, [{"id": "a"}, {"id": "b"}]))
    assert sr._recalc_start_order("scr-1", 5) == 5


def test_falls_back_to_len_when_count_is_none(monkeypatch):
    # Some PostgREST responses omit count; fall back to len(data).
    monkeypatch.setattr(sr, "supabase", _fake_supabase(None, [{"id": "a"}]))
    assert sr._recalc_start_order("scr-1", 5) == 5


def test_current_order_zero_stays_zero_mid_run(monkeypatch):
    # current_order falsy + scenes remaining -> 0 (harmless, matches old default).
    monkeypatch.setattr(sr, "supabase", _fake_supabase(1, [{"id": "a"}]))
    assert sr._recalc_start_order("scr-1", 0) == 0
