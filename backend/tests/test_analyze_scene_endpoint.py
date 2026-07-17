"""Endpoint-level: failed analysis is recorded as failed, not fake-complete."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import routes.supabase_routes as sr
from services.gemini_client import GeminiError


class FakeTable:
    def __init__(self, store): self.store = store; self._id = None; self._upd = None
    def select(self, *_a, **_k): return self
    def eq(self, _c, v): self._id = v; return self
    def single(self): return self
    def order(self, *_a, **_k): return self
    def in_(self, *_a, **_k): return self
    def update(self, data): self._upd = data; return self
    def execute(self):
        if self._upd is not None:
            self.store.setdefault(self._id, {}).update(self._upd)
            u, self._upd = self._upd, None
            return type("R", (), {"data": [self.store[self._id]]})()
        return type("R", (), {"data": self.store.get(self._id)})()


@pytest.fixture
def client(monkeypatch):
    store = {"scene-1": {"id": "scene-1", "script_id": "scr-1", "scene_text": "INT. ROOM - DAY\nAction here.",
                          "scene_order": 1, "setting": "INT. ROOM - DAY"}}
    fake = FakeTable(store)
    monkeypatch.setattr(sr, "supabase", type("S", (), {"table": lambda self, _n: fake})())
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr("services.entitlement_service.get_user_id", lambda: "u1")
    monkeypatch.setattr("services.entitlement_service.get_entitlement", lambda uid: {
        'tier': 'tier_2_annual_team', 'status': 'active', 'breakdown_balance': 999,
        'seats_paid': 0, 'seats_used': 0, 'can_run_breakdown': True, 'can_use_teams': True,
    })
    from app import app
    app.config["TESTING"] = True
    return app.test_client(), store


def test_failed_scene_recorded_as_failed(client, monkeypatch):
    c, store = client
    monkeypatch.setattr(sr, "analyze_scene_with_gemini", lambda *a, **k: (_ for _ in ()).throw(GeminiError("timeout")))
    resp = c.post("/api/scenes/scene-1/analyze")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["analysis_status"] == "failed"
    assert body["analysis_error_category"] == "timeout"
    assert store["scene-1"]["analysis_status"] == "failed"
    assert store["scene-1"]["analysis_error"]  # non-empty friendly message
