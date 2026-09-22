import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_template_service as tpl
from test_call_sheet_service import MockSupabase


def _paths(exc):
    return [e["path"] for e in exc.value.errors]


def _custom_field(key="wind", **kw):
    f = {"key": key, "label": "Wind", "type": "text", "section": "day_info",
         "default": "", "sensitive": False, "visible": True, "builtin": False}
    f.update(kw)
    return f


def test_default_config_is_valid_and_round_trips():
    cfg = tpl.default_config()
    assert tpl.validate_config(cfg) == cfg


def test_default_mirrors_v1_visibility_and_order():
    cfg = tpl.default_config()
    assert [s["key"] for s in cfg["sections"]] == list(tpl.SECTION_KEYS)
    visible = {s["key"] for s in cfg["sections"] if s["visible"]}
    assert visible == {"header", "day_info", "locations", "scenes", "cast", "crew", "notes"}
    fields = {f["key"]: f for f in cfg["day_fields"]}
    assert fields["parking_notes"]["visible"] is False       # v1 never printed it
    assert fields["general_call"]["visible"] is False
    assert fields["weather"]["section"] == "day_info"
    assert fields["nearest_hospital"]["section"] == "notes"


def test_custom_field_accepted_and_builtin_flag_forced_by_server():
    cfg = tpl.default_config()
    cfg["day_fields"].append(_custom_field())
    cfg["day_fields"][0]["builtin"] = False  # client lies about a builtin
    clean = tpl.validate_config(cfg)
    by_key = {f["key"]: f for f in clean["day_fields"]}
    assert by_key["weather"]["builtin"] is True
    assert by_key["wind"]["builtin"] is False


def test_duplicate_key_rejected():
    cfg = tpl.default_config()
    cfg["day_fields"] += [_custom_field(), _custom_field()]
    with pytest.raises(tpl.ConfigError) as ei:
        tpl.validate_config(cfg)
    assert any("duplicate" in e["message"].lower() for e in ei.value.errors)


@pytest.mark.parametrize("bad", ["Wind", "1wind", "wind-speed", "", "a" * 41])
def test_bad_key_format_rejected(bad):
    cfg = tpl.default_config()
    cfg["day_fields"].append(_custom_field(key=bad))
    with pytest.raises(tpl.ConfigError):
        tpl.validate_config(cfg)


def test_builtin_removal_rejected():
    cfg = tpl.default_config()
    cfg["day_fields"] = [f for f in cfg["day_fields"] if f["key"] != "weather"]
    with pytest.raises(tpl.ConfigError) as ei:
        tpl.validate_config(cfg)
    assert "day_fields" in _paths(ei)


def test_builtin_type_is_locked():
    cfg = tpl.default_config()
    next(f for f in cfg["day_fields"] if f["key"] == "sunrise_time")["type"] = "text"
    with pytest.raises(tpl.ConfigError):
        tpl.validate_config(cfg)


def test_bad_type_and_section_rejected():
    cfg = tpl.default_config()
    cfg["day_fields"].append(_custom_field(type="color"))
    with pytest.raises(tpl.ConfigError):
        tpl.validate_config(cfg)
    cfg = tpl.default_config()
    cfg["day_fields"].append(_custom_field(section="footer"))
    with pytest.raises(tpl.ConfigError):
        tpl.validate_config(cfg)


def test_invalid_default_for_time_field_rejected():
    cfg = tpl.default_config()
    cfg["day_fields"].append(_custom_field(key="wrap", type="time", default="soon"))
    with pytest.raises(tpl.ConfigError):
        tpl.validate_config(cfg)


def test_day_field_cap():
    cfg = tpl.default_config()
    cfg["day_fields"] += [_custom_field(key=f"f{i}") for i in range(31)]  # 10 + 31 = 41
    with pytest.raises(tpl.ConfigError):
        tpl.validate_config(cfg)


def test_missing_section_rejected():
    cfg = tpl.default_config()
    cfg["sections"] = [s for s in cfg["sections"] if s["key"] != "crew"]
    with pytest.raises(tpl.ConfigError) as ei:
        tpl.validate_config(cfg)
    assert "sections" in _paths(ei)


def test_columns_departments_blocks_key_crew_round_trip():
    cfg = tpl.default_config()
    cfg["cast_columns"] = [{"key": "pickup", "label": "P/U", "type": "time", "sensitive": False}]
    cfg["crew_columns"] = [{"key": "rate_note", "label": "Rate", "type": "text", "sensitive": True}]
    cfg["scene_columns"] = [{"key": "story_day", "label": "Story day", "type": "text", "sensitive": False}]
    cfg["departments"] = [{"key": "wardrobe", "label": "Wardrobe", "default_call": "06:00", "as_per": "Pippa"}]
    cfg["blocks"] = [{"key": "safety", "label": "Special notes", "body": "Closed shoes"}]
    cfg["key_crew"] = [{"key": "director", "label": "Director", "value": "A. Director"}]
    assert tpl.validate_config(cfg) == cfg


def test_department_call_must_be_time():
    cfg = tpl.default_config()
    cfg["departments"] = [{"key": "art", "label": "Art", "default_call": "early", "as_per": ""}]
    with pytest.raises(tpl.ConfigError):
        tpl.validate_config(cfg)


def test_unknown_props_are_stripped():
    cfg = tpl.default_config()
    cfg["day_fields"][0]["evil"] = "x"
    cfg["surprise"] = 1
    clean = tpl.validate_config(cfg)
    assert "evil" not in clean["day_fields"][0] and "surprise" not in clean


def test_get_template_default_creates_nothing():
    store = {"call_sheet_templates": []}
    got = tpl.get_template("p1", MockSupabase(store))
    assert got["is_default"] is True and got["updated_at"] is None
    assert got["config"] == tpl.default_config()
    assert store["call_sheet_templates"] == []


def test_save_template_creates_then_updates():
    store = {"call_sheet_templates": []}
    sb = MockSupabase(store)
    cfg = tpl.default_config()
    cfg["day_fields"].append(_custom_field())
    saved = tpl.save_template("p1", cfg, "u1", supabase=sb)
    assert saved["is_default"] is False
    assert len(store["call_sheet_templates"]) == 1
    cfg2 = copy.deepcopy(cfg)
    cfg2["day_fields"].append(_custom_field(key="wrap", label="Wrap"))
    tpl.save_template("p1", cfg2, "u1", supabase=sb)
    assert len(store["call_sheet_templates"]) == 1
    keys = [f["key"] for f in store["call_sheet_templates"][0]["config"]["day_fields"]]
    assert "wrap" in keys


def test_save_template_stale_expected_updated_at():
    store = {"call_sheet_templates": [
        {"id": "t1", "production_id": "p1", "config": tpl.default_config(),
         "updated_at": "2026-09-21T10:00:00+00:00"}]}
    sb = MockSupabase(store)
    with pytest.raises(tpl.StaleTemplate):
        tpl.save_template("p1", tpl.default_config(), "u1",
                          expected_updated_at="2026-09-21T09:00:00+00:00", supabase=sb)
    tpl.save_template("p1", tpl.default_config(), "u1",
                      expected_updated_at="2026-09-21T10:00:00+00:00", supabase=sb)


def test_save_template_invalid_raises_and_stores_nothing():
    store = {"call_sheet_templates": []}
    with pytest.raises(tpl.ConfigError):
        tpl.save_template("p1", {"v": 1}, "u1", supabase=MockSupabase(store))
    assert store["call_sheet_templates"] == []
