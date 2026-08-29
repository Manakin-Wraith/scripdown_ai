# backend/tests/test_conflict_ack_route.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from unittest.mock import MagicMock
import routes.schedule_routes as sr
import middleware.authorization as authz


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture(autouse=True)
def _bypass_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")


def _as_role(monkeypatch, role):
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: role)
    monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")


def _url(day_id="d1", scene_id="sc1"):
    return f"/api/shooting-days/{day_id}/scenes/{scene_id}/conflict-ack"


class TestConflictAck:
    def test_requires_member(self, monkeypatch):
        _as_role(monkeypatch, "viewer")
        r = _client().patch(_url(), json={"acknowledged": True, "reason": "x"})
        assert r.status_code == 403

    def test_member_sets_ack(self, monkeypatch):
        _as_role(monkeypatch, "member")
        mock = MagicMock()
        monkeypatch.setattr(sr, "supabase", mock)
        r = _client().patch(_url(), json={"acknowledged": True, "reason": "spoke to agent"})
        assert r.status_code == 200
        assert r.get_json() == {"success": True}

        mock.table.assert_any_call("shooting_day_scenes")
        update_call = mock.table.return_value.update
        payload = update_call.call_args[0][0]
        assert payload["conflict_ack"] is True
        assert payload["conflict_ack_reason"] == "spoke to agent"
        assert payload["conflict_ack_by"] == "u1"
        assert payload["conflict_ack_at"] is not None

        eq_chain = update_call.return_value.eq
        eq_chain.assert_any_call("shooting_day_id", "d1")
        eq_chain.return_value.eq.assert_any_call("scene_id", "sc1")

    def test_member_clears_ack(self, monkeypatch):
        _as_role(monkeypatch, "member")
        mock = MagicMock()
        monkeypatch.setattr(sr, "supabase", mock)
        r = _client().patch(_url(), json={"acknowledged": False})
        assert r.status_code == 200

        payload = mock.table.return_value.update.call_args[0][0]
        assert payload["conflict_ack"] is False
        assert payload["conflict_ack_reason"] is None
        assert payload["conflict_ack_at"] is None
        assert payload["conflict_ack_by"] is None
