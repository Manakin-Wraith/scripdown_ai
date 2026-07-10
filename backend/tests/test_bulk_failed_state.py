"""Bulk worker records terminal scene failures as failed + friendly detail."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.supabase_routes as sr
from services.gemini_client import GeminiError


class OneSceneTable:
    def __init__(self): self.updates = []
    def update(self, data): self._u = data; return self
    def eq(self, _c, _v): return self
    def execute(self):
        self.updates.append(self._u); return type("R", (), {"data": []})()
    def select(self, *_a, **_k): return self
    def in_(self, *_a, **_k): return self
    def order(self, *_a, **_k): return self
    def insert(self, *_a, **_k): return self


def test_bulk_terminal_failure_marks_failed(monkeypatch):
    tbl = OneSceneTable()
    monkeypatch.setattr(sr, "supabase", type("S", (), {"table": lambda self, _n: tbl})())
    # analyze_scene_internal raises a terminal GeminiError every attempt
    monkeypatch.setattr(sr, "analyze_scene_internal",
                        lambda _sid: (_ for _ in ()).throw(GeminiError("timeout")))
    monkeypatch.setattr(sr.time, "sleep", lambda _s: None)
    sr.process_bulk_analysis_job("job-1", "scr-1", ["scene-1"])
    # The scene must have been marked failed with a category
    failed_updates = [u for u in tbl.updates if u.get("analysis_status") == "failed"]
    assert failed_updates, "scene was not marked failed"
    assert failed_updates[0]["analysis_error_category"] == "timeout"
    assert failed_updates[0]["analysis_error"]
