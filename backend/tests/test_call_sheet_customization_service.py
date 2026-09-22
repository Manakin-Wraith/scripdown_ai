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


def _roster_store(**overrides):
    return make_store(
        production_crew=[{"id": "cr1", "production_id": "p1", "contact_id": None}],
        casting=[{"id": "ca1", "script_id": "s1", "character_name": "HERO",
                  "actor_name": "Jo", "tier": "lead"}],
        **overrides)


def test_add_crew_stores_valid_extra_and_drops_unknown(monkeypatch):
    patch_svc(monkeypatch, _roster_store())
    row = svc.add_crew("cs1", "cr1", "06:00", None, {"vehicle": "Van 2", "bogus": "x"})
    assert row["extra"] == {"vehicle": "Van 2"}


def test_add_crew_extra_defaults_to_empty(monkeypatch):
    patch_svc(monkeypatch, _roster_store())
    assert svc.add_crew("cs1", "cr1")["extra"] == {}


def test_add_cast_validates_extra_types(monkeypatch):
    patch_svc(monkeypatch, _roster_store())
    with pytest.raises(ValueError, match="pickup"):
        svc.add_cast("cs1", "ca1", extra={"pickup": "noon"})
    row = svc.add_cast("cs1", "ca1", "07:00", "W", None, {"pickup": "06:15:00"})
    assert row["extra"] == {"pickup": "06:15"}


def test_update_crew_call_merges_extra(monkeypatch):
    store = _roster_store(call_sheet_crew=[
        {"id": "x", "call_sheet_id": "cs1", "crew_id": "cr1", "call_time": None,
         "extra": {"vehicle": "Van 2"}}])
    patch_svc(monkeypatch, store)
    row = svc.update_crew_call("cs1", "cr1", {"extra": {"vehicle": None}})
    assert row["extra"] == {}
    row = svc.update_crew_call("cs1", "cr1", {"extra": {"vehicle": "Truck"}})
    assert row["extra"] == {"vehicle": "Truck"}


def test_update_crew_call_leaves_extra_alone_when_not_sent(monkeypatch):
    store = _roster_store(call_sheet_crew=[
        {"id": "x", "call_sheet_id": "cs1", "crew_id": "cr1", "call_time": None,
         "extra": {"vehicle": "Van 2"}}])
    patch_svc(monkeypatch, store)
    row = svc.update_crew_call("cs1", "cr1", {"call_time": "05:00"})
    assert row["extra"] == {"vehicle": "Van 2"} and row["call_time"] == "05:00"


def test_update_cast_call_merges_extra(monkeypatch):
    store = _roster_store(call_sheet_cast=[
        {"id": "y", "call_sheet_id": "cs1", "casting_id": "ca1", "call_time": None,
         "extra": {"pickup": "06:00"}}])
    patch_svc(monkeypatch, store)
    row = svc.update_cast_call("cs1", "ca1", {"extra": {"pickup": "07:30", "zzz": "1"}})
    assert row["extra"] == {"pickup": "07:30"}


def _sensitive_cfg():
    cfg = full_config()
    cfg["crew_columns"] = [
        {"key": "vehicle", "label": "Vehicle", "type": "text", "sensitive": True},
        {"key": "note", "label": "Note", "type": "text", "sensitive": False}]
    cfg["cast_columns"] = [
        {"key": "pickup", "label": "P/U", "type": "time", "sensitive": False},
        {"key": "fee", "label": "Fee", "type": "text", "sensitive": True}]
    cfg["scene_columns"] = [
        {"key": "story_day", "label": "Story day", "type": "text", "sensitive": False},
        {"key": "budget", "label": "Budget", "type": "text", "sensitive": True}]
    cfg["day_fields"] += [{"key": "secret", "label": "Secret", "type": "text", "section": "notes",
                           "default": "", "sensitive": True, "visible": True, "builtin": False}]
    next(f for f in cfg["day_fields"] if f["key"] == "nearest_hospital")["sensitive"] = True
    return cfg


def _sensitive_data(monkeypatch):
    store = make_store(
        cfg=_sensitive_cfg(),
        call_sheets=[sheet_row(nearest_hospital="City Hospital",
                               custom_values={"secret": "s3", "wind": "SSW"},
                               scene_extras={"sc1": {"story_day": "4", "budget": "9"}})],
        production_crew=[{"id": "cr1", "production_id": "p1", "contact_id": None, "job_rate": 5}],
        call_sheet_crew=[{"id": "x", "call_sheet_id": "cs1", "crew_id": "cr1",
                          "extra": {"vehicle": "Van", "note": "n"}}],
        casting=[{"id": "ca1", "script_id": "s1", "character_name": "H", "tier": "lead"}],
        call_sheet_cast=[{"id": "y", "call_sheet_id": "cs1", "casting_id": "ca1",
                          "extra": {"pickup": "06:00", "fee": "1000"}}],
    )
    patch_svc(monkeypatch, store)
    return svc.get_call_sheet("cs1")


def test_redact_strips_sensitive_custom_data(monkeypatch):
    data = svc.redact_roster(_sensitive_data(monkeypatch), can_view_sensitive=False)
    assert data["crew"][0]["extra"] == {"note": "n"}
    assert data["cast"][0]["extra"] == {"pickup": "06:00"}
    assert data["scene_extras"] == {"sc1": {"story_day": "4"}}
    assert data["custom_values"] == {"wind": "SSW"}
    assert data["nearest_hospital"] is None            # sensitive builtin blanked
    assert "job_rate" not in data["crew"][0]["crew"]   # v1 behaviour retained


def test_redact_noop_for_sensitive_viewer(monkeypatch):
    data = svc.redact_roster(_sensitive_data(monkeypatch), can_view_sensitive=True)
    assert data["crew"][0]["extra"]["vehicle"] == "Van"
    assert data["custom_values"]["secret"] == "s3"
    assert data["nearest_hospital"] == "City Hospital"


def test_redact_row_with_explicit_template(monkeypatch):
    row = {"crew": [{"extra": {"vehicle": "Van", "note": "n"}}]}
    out = svc.redact_roster(row, False, _sensitive_cfg())
    assert out["crew"][0]["extra"] == {"note": "n"}


def test_pdf_html_redacts_by_default(monkeypatch):
    _sensitive_data(monkeypatch)
    captured = {}

    def fake_render(data, ctx):
        captured["data"] = data
        return "<html></html>"

    monkeypatch.setattr(svc.render, "render_html", fake_render)
    svc.build_call_sheet_html("cs1")
    assert captured["data"]["cast"][0]["extra"] == {"pickup": "06:00"}
    svc.build_call_sheet_html("cs1", can_view_sensitive=True)
    assert captured["data"]["cast"][0]["extra"]["fee"] == "1000"


def _multi_day_store(**overrides):
    return make_store(
        shooting_days=[
            {"id": "d1", "schedule_id": "sch1", "day_number": 1, "shoot_date": "2026-10-01"},
            {"id": "d2", "schedule_id": "sch1", "day_number": 2, "shoot_date": "2026-10-02"},
            {"id": "d3", "schedule_id": "sch1", "day_number": 3, "shoot_date": "2026-10-03"},
            {"id": "x9", "schedule_id": "other", "day_number": 2, "shoot_date": "2026-10-09"}],
        **overrides)


def test_render_context_finds_next_day_with_scenes(monkeypatch):
    store = _multi_day_store(
        scenes=[{"id": "sc2", "scene_number": "7"}],
        shooting_day_scenes=[{"shooting_day_id": "d2", "scene_id": "sc2", "sort_order": 0}])
    sb = patch_svc(monkeypatch, store)
    data = svc.get_call_sheet("cs1")
    day = store["shooting_days"][0]
    ctx = svc._render_context(sb, data, day)
    assert ctx["days_total"] == 3                      # other schedule's day excluded
    assert ctx["advanced"]["day"]["id"] == "d2"
    assert [s["id"] for s in ctx["advanced"]["scenes"]] == ["sc2"]


def test_render_context_advanced_none_when_next_day_has_no_scenes(monkeypatch):
    sb = patch_svc(monkeypatch, _multi_day_store())
    ctx = svc._render_context(sb, svc.get_call_sheet("cs1"), _multi_day_store()["shooting_days"][0])
    assert ctx["advanced"] is None


def test_render_context_advanced_none_on_last_day(monkeypatch):
    store = _multi_day_store(call_sheets=[sheet_row(shooting_day_id="d3")])
    sb = patch_svc(monkeypatch, store)
    ctx = svc._render_context(sb, svc.get_call_sheet("cs1"), store["shooting_days"][2])
    assert ctx["advanced"] is None
