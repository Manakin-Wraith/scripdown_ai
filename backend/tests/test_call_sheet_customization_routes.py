import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_service as cs_svc
from call_sheet_customization_support import full_config, sheet_row
from test_call_sheet_routes import _client, _store, _member_store, _patch


def _cfg():
    cfg = full_config()
    cfg["cast_columns"] = [
        {"key": "pickup", "label": "P/U", "type": "time", "sensitive": False},
        {"key": "fee", "label": "Fee", "type": "text", "sensitive": True}]
    return cfg


def _extra_tables(store):
    store["casting"] = [{"id": "ca1", "script_id": "s1", "character_name": "HERO", "tier": "lead"}]
    store["call_sheet_templates"] = [{"id": "t1", "production_id": "p1", "config": _cfg(),
                                      "updated_at": "t"}]
    return store


def _coordinator_store():
    return _extra_tables(_member_store("coordinator", can_edit_call_sheets=True))


def _owner_store():
    return _extra_tables(_store(call_sheets=[sheet_row()]))


BODY = {"casting_id": "ca1", "extra": {"pickup": "06:00", "fee": "1000"}}


def test_cast_add_redacts_sensitive_extra_for_non_sensitive_member(monkeypatch):
    _patch(monkeypatch, _coordinator_store())
    resp = _client().post("/api/call-sheets/cs1/cast", json=BODY)
    assert resp.status_code == 201
    assert resp.get_json()["cast"]["extra"] == {"pickup": "06:00"}


def test_cast_add_shows_sensitive_extra_to_owner(monkeypatch):
    _patch(monkeypatch, _owner_store())
    resp = _client().post("/api/call-sheets/cs1/cast", json=BODY)
    assert resp.get_json()["cast"]["extra"] == {"pickup": "06:00", "fee": "1000"}


def test_cast_update_redacts(monkeypatch):
    store = _coordinator_store()
    store["call_sheet_cast"] = [{"id": "y", "call_sheet_id": "cs1", "casting_id": "ca1",
                                 "extra": {"pickup": "06:00", "fee": "1000"}}]
    _patch(monkeypatch, store)
    resp = _client().patch("/api/call-sheets/cs1/cast/ca1", json={"extra": {"pickup": "07:00"}})
    assert resp.status_code == 200
    assert resp.get_json()["cast"]["extra"] == {"pickup": "07:00"}


def test_cast_add_bad_extra_is_400(monkeypatch):
    _patch(monkeypatch, _owner_store())
    resp = _client().post("/api/call-sheets/cs1/cast",
                          json={"casting_id": "ca1", "extra": {"pickup": "noon"}})
    assert resp.status_code == 400


def test_get_call_sheet_redacts_and_flags_sensitivity(monkeypatch):
    store = _coordinator_store()
    store["call_sheet_cast"] = [{"id": "y", "call_sheet_id": "cs1", "casting_id": "ca1",
                                 "extra": {"pickup": "06:00", "fee": "1000"}}]
    _patch(monkeypatch, store)
    body = _client().get("/api/call-sheets/cs1").get_json()["call_sheet"]
    assert body["can_view_sensitive"] is False
    assert body["cast"][0]["extra"] == {"pickup": "06:00"}


def test_get_by_day_flags_sensitivity_for_owner(monkeypatch):
    _patch(monkeypatch, _owner_store())
    body = _client().get("/api/shooting-days/d1/call-sheet").get_json()["call_sheet"]
    assert body["can_view_sensitive"] is True


def test_patch_returns_ignored_keys(monkeypatch):
    _patch(monkeypatch, _owner_store())
    resp = _client().patch("/api/call-sheets/cs1", json={"custom_values": {"wind": "SSW", "gone": "x"}})
    assert resp.status_code == 200
    assert resp.get_json()["ignored_keys"] == ["gone"]
    assert resp.get_json()["call_sheet"]["custom_values"] == {"wind": "SSW"}


def test_patch_invalid_value_is_400(monkeypatch):
    _patch(monkeypatch, _owner_store())
    resp = _client().patch("/api/call-sheets/cs1", json={"custom_values": {"map": "javascript:x"}})
    assert resp.status_code == 400 and "map" in resp.get_json()["error"]


def test_pdf_route_passes_sensitivity(monkeypatch):
    seen = {}

    def fake(call_sheet_id, can_view_sensitive=False):
        seen["v"] = can_view_sensitive
        return b"%PDF-1.4"

    monkeypatch.setattr(cs_svc, "render_call_sheet_pdf", fake)
    _patch(monkeypatch, _coordinator_store())
    assert _client().get("/api/call-sheets/cs1/pdf").status_code == 200
    assert seen["v"] is False
    _patch(monkeypatch, _owner_store())
    _client().get("/api/call-sheets/cs1/pdf")
    assert seen["v"] is True
