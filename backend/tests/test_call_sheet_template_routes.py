import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_template_service as tpl
from test_call_sheet_routes import _client, _store, _member_store, _patch

URL = "/api/productions/p1/call-sheet-template"


def _put(cfg, expected=None):
    return _client().put(URL, json={"config": cfg, "expected_updated_at": expected})


def test_get_returns_default_for_owner_and_creates_nothing(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _client().get(URL)
    assert resp.status_code == 200
    body = resp.get_json()["template"]
    assert body["is_default"] is True and body["config"] == tpl.default_config()
    assert body["default_config"] == tpl.default_config()
    assert store.get("call_sheet_templates", []) == []


def test_get_allowed_for_viewer_member(monkeypatch):
    _patch(monkeypatch, _member_store("viewer"))
    assert _client().get(URL).status_code == 200


def test_get_non_member_is_403(monkeypatch):
    _patch(monkeypatch, _store(productions=[{"id": "p1", "owner_id": "other", "title": "X"}]))
    assert _client().get(URL).status_code == 403


def test_get_anon_is_401(monkeypatch):
    _patch(monkeypatch, _store())
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    assert _client().get(URL).status_code == 401


def test_put_owner_saves(monkeypatch):
    store = _store()
    _patch(monkeypatch, store)
    resp = _put(tpl.default_config())
    assert resp.status_code == 200
    assert len(store["call_sheet_templates"]) == 1


def test_put_viewer_is_403(monkeypatch):
    _patch(monkeypatch, _member_store("viewer"))
    assert _put(tpl.default_config()).status_code == 403


def test_put_coordinator_needs_capability(monkeypatch):
    _patch(monkeypatch, _member_store("coordinator"))
    assert _put(tpl.default_config()).status_code == 403


def test_put_coordinator_with_capability_ok(monkeypatch):
    _patch(monkeypatch, _member_store("coordinator", can_edit_call_sheet_template=True))
    assert _put(tpl.default_config()).status_code == 200


def test_put_invalid_config_is_400_with_details(monkeypatch):
    _patch(monkeypatch, _store())
    resp = _put({"v": 1})
    assert resp.status_code == 400
    assert resp.get_json()["details"]


def test_put_stale_is_409(monkeypatch):
    store = _store()
    store["call_sheet_templates"] = [{"id": "t1", "production_id": "p1",
                                      "config": tpl.default_config(), "updated_at": "t1"}]
    _patch(monkeypatch, store)
    resp = _put(tpl.default_config(), expected="t0")
    assert resp.status_code == 409
    assert resp.get_json()["code"] == "stale_template"
    assert _put(tpl.default_config(), expected="t1").status_code == 200
