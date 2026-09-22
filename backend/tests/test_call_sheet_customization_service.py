import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_service as svc
import services.call_sheet_template_service as tpl
from call_sheet_customization_support import full_config, make_store, patch_svc, sheet_row
from test_call_sheet_service import _store


def test_get_call_sheet_includes_default_template_when_none_saved(monkeypatch):
    patch_svc(monkeypatch, _store(call_sheets=[sheet_row()]))
    data = svc.get_call_sheet("cs1")
    assert data["template"] == tpl.default_config()
    assert data["template_updated_at"] is None


def test_get_call_sheet_returns_saved_template_and_catering(monkeypatch):
    store = make_store(
        production_crew=[{"id": "cr1", "production_id": "p1", "contact_id": None}],
        call_sheet_crew=[{"id": "x", "call_sheet_id": "cs1", "crew_id": "cr1", "call_time": "06:00:00"}],
    )
    patch_svc(monkeypatch, store)
    data = svc.get_call_sheet("cs1")
    assert data["template"] == full_config()
    assert data["template_updated_at"] == "2026-09-21T00:00:00+00:00"
    assert data["catering_defaults"]["lunch"]["crew"] == 1
    assert data["catering_effective"]["lunch"]["crew"] == 1
    assert data["crew"][0]["call_time"] == "06:00"


def test_get_call_sheet_normalizes_times(monkeypatch):
    store = make_store(call_sheets=[sheet_row(sunrise_time="06:12:00", general_call="05:30:00")])
    patch_svc(monkeypatch, store)
    data = svc.get_call_sheet("cs1")
    assert data["sunrise_time"] == "06:12" and data["general_call"] == "05:30"


def test_catering_override_wins_in_effective(monkeypatch):
    store = make_store(call_sheets=[sheet_row(catering={"lunch": {"crew": 40}})])
    patch_svc(monkeypatch, store)
    assert svc.get_call_sheet("cs1")["catering_effective"]["lunch"]["crew"] == 40


def _patch_fields(monkeypatch, store, fields):
    patch_svc(monkeypatch, store)
    return svc.update_call_sheet_with_report("cs1", fields)


def test_custom_values_merge_preserves_other_keys(monkeypatch):
    store = make_store(call_sheets=[sheet_row(custom_values={"wind": "SSW", "old_removed": "keep"})])
    row, ignored = _patch_fields(monkeypatch, store, {"custom_values": {"map": "https://x.com/m"}})
    assert row["custom_values"] == {"wind": "SSW", "old_removed": "keep", "map": "https://x.com/m"}
    assert ignored == []


def test_custom_values_null_clears_and_unknown_is_ignored(monkeypatch):
    store = make_store(call_sheets=[sheet_row(custom_values={"wind": "SSW"})])
    row, ignored = _patch_fields(monkeypatch, store, {"custom_values": {"wind": None, "bogus": "x"}})
    assert row["custom_values"] == {}
    assert ignored == ["bogus"]


def test_custom_values_rejects_invalid_link(monkeypatch):
    with pytest.raises(ValueError, match="map"):
        _patch_fields(monkeypatch, make_store(), {"custom_values": {"map": "javascript:alert(1)"}})


def test_builtin_time_normalized_and_blank_clears(monkeypatch):
    store = make_store()
    row, _ = _patch_fields(monkeypatch, store, {"sunrise_time": "06:12:00", "general_call": ""})
    assert row["sunrise_time"] == "06:12" and row["general_call"] is None


def test_builtin_bad_time_rejected(monkeypatch):
    with pytest.raises(ValueError):
        _patch_fields(monkeypatch, make_store(), {"lunch_time": "noonish"})


def test_scene_extras_merge_and_unknown_scene_ignored(monkeypatch):
    store = make_store(
        scenes=[{"id": "sc1", "scene_number": "1"}],
        shooting_day_scenes=[{"shooting_day_id": "d1", "scene_id": "sc1", "sort_order": 0}],
    )
    row, ignored = _patch_fields(monkeypatch, store, {"scene_extras": {
        "sc1": {"story_day": "Day 4", "nope": "x"}, "scX": {"story_day": "y"}}})
    assert row["scene_extras"] == {"sc1": {"story_day": "Day 4"}}
    assert set(ignored) == {"sc1.nope", "scX"}


def test_dept_overrides(monkeypatch):
    row, ignored = _patch_fields(monkeypatch, make_store(), {"dept_overrides": {
        "wardrobe": {"call": "07:00:00", "as_per": "Sam"}, "art": {"call": "06:00"}}})
    assert row["dept_overrides"] == {"wardrobe": {"call": "07:00", "as_per": "Sam"}}
    assert ignored == ["art"]


def test_catering_patch_validates_counts(monkeypatch):
    row, _ = _patch_fields(monkeypatch, make_store(), {"catering": {"lunch": {"crew": 40}}})
    assert row["catering"] == {"lunch": {"crew": 40}}
    with pytest.raises(ValueError):
        _patch_fields(monkeypatch, make_store(), {"catering": {"lunch": {"crew": -2}}})


def test_header_values_and_block_overrides(monkeypatch):
    row, ignored = _patch_fields(monkeypatch, make_store(), {
        "header_values": {"director": "B. Other", "zzz": "x"},
        "block_overrides": {"safety": "Hard hats today"}})
    assert row["header_values"] == {"director": "B. Other"}
    assert row["block_overrides"] == {"safety": "Hard hats today"}
    assert ignored == ["zzz"]


def test_removed_field_value_restored_when_readded(monkeypatch):
    cfg = full_config()
    cfg["day_fields"] = [f for f in cfg["day_fields"] if f["key"] != "wind"]
    store = make_store(cfg=cfg, call_sheets=[sheet_row(custom_values={"wind": "SSW"})])
    patch_svc(monkeypatch, store)
    data = svc.get_call_sheet("cs1")
    assert data["custom_values"] == {"wind": "SSW"}   # stored, just not in template


def test_update_call_sheet_wrapper_returns_row_only(monkeypatch):
    patch_svc(monkeypatch, make_store())
    row = svc.update_call_sheet("cs1", {"weather": "Sunny"})
    assert row["weather"] == "Sunny"


def test_update_not_found(monkeypatch):
    patch_svc(monkeypatch, make_store())
    assert svc.update_call_sheet_with_report("nope", {"weather": "x"}) == (svc.NOT_FOUND, [])
