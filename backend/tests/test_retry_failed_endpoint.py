"""retry-failed enqueues only failed scenes."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import routes.supabase_routes as sr


def _allow_entitlement(monkeypatch):
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr("services.entitlement_service.get_user_id", lambda: "u1")
    monkeypatch.setattr("services.entitlement_service.get_entitlement", lambda uid: {
        'tier': 'tier_2_annual_team', 'status': 'active', 'breakdown_balance': 999,
        'seats_paid': 0, 'seats_used': 0, 'can_run_breakdown': True, 'can_use_teams': True,
    })


class SelectTable:
    """Returns a fixed set of failed scenes; captures inserts; no-ops threads."""
    def __init__(self, failed): self.failed = failed
    def select(self, *_a, **_k): return self
    def eq(self, *_a, **_k): return self
    def in_(self, *_a, **_k): return self
    def order(self, *_a, **_k): return self
    def insert(self, *_a, **_k): return self
    def update(self, *_a, **_k): return self
    def execute(self):
        return type("R", (), {"data": self.failed})()


def test_retry_failed_enqueues_failed_only(monkeypatch):
    failed = [{"id": "s1", "scene_number": 1}, {"id": "s2", "scene_number": 2}]
    monkeypatch.setattr(sr, "supabase", type("S", (), {"table": lambda self, _n: SelectTable(failed)})())
    _allow_entitlement(monkeypatch)
    started = {}
    monkeypatch.setattr(sr.threading, "Thread",
                        lambda **kw: type("T", (), {"start": lambda self: started.update(kw.get("args") and {"args": kw["args"]})})())
    from app import app
    app.config["TESTING"] = True
    resp = app.test_client().post("/api/scripts/scr-1/scenes/retry-failed")
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["retrying"] == 2


def test_retry_failed_zero(monkeypatch):
    monkeypatch.setattr(sr, "supabase", type("S", (), {"table": lambda self, _n: SelectTable([])})())
    _allow_entitlement(monkeypatch)
    from app import app
    app.config["TESTING"] = True
    resp = app.test_client().post("/api/scripts/scr-1/scenes/retry-failed")
    assert resp.status_code == 200
    assert resp.get_json()["retrying"] == 0
