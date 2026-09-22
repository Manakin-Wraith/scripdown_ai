import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_render as render
import services.call_sheet_template_service as tpl
import services.department_service as ds
from call_sheet_customization_support import full_config


def _data(cfg=None, **kw):
    data = {
        "status": "published", "template": cfg or tpl.default_config(),
        "weather": "Sunny", "sunrise_time": "06:12", "nearest_hospital": "City Hospital",
        "safety_notes": "Officer Jo", "general_notes": "Bring water",
        "parking_notes": "SECRET-PARKING", "custom_values": {},
        "locations": [{"is_primary": True, "sort_order": 0,
                       "location": {"name": "Warehouse", "address": "1 Main St", "parking_notes": "Lot B"}}],
        "scenes": [{"id": "sc1", "scene_number": "12", "int_ext": "INT", "setting": "OFFICE",
                    "time_of_day": "DAY", "page_length_eighths": 3}],
        "scene_extras": {},
        "cast": [{"call_time": "06:00", "status_code": "W", "extra": {},
                  "casting": {"character_name": "HERO", "actor_name": "Jo", "tier": "lead"}}],
        "crew": [{"call_time": "05:30", "extra": {},
                  "crew": {"department_code": "camera", "role": "DoP",
                           "contact": {"name": "Gary"}}}],
    }
    data.update(kw)
    return data


CTX = {"day": {"day_number": 3, "shoot_date": "2026-10-01"},
       "production_title": "Farm Feature", "days_total": 12, "advanced": None}


def _html(data, ctx=None, monkeypatch=None):
    return render.render_html(data, ctx or CTX)


def _patch_depts(monkeypatch):
    monkeypatch.setattr(ds, "get_departments_list",
                        lambda: [{"code": "camera", "name": "Camera", "color": "#1"}])


def test_default_template_renders_v1_content_only(monkeypatch):
    _patch_depts(monkeypatch)
    html = _html(_data())
    for expected in ("Weather", "Sunny", "City Hospital", "Officer Jo", "Bring water",
                     "Warehouse", "Lot B", "HERO", "Gary", "OFFICE"):
        assert expected in html
    assert "SECRET-PARKING" not in html          # parking_notes hidden by default
    assert "General Call" not in html            # hidden by default
    assert "Extras" not in html and "Catering" not in html


def test_default_section_order_matches_v1(monkeypatch):
    _patch_depts(monkeypatch)
    html = _html(_data())
    order = [html.index(t) for t in ("Locations", "Scene Schedule", "Cast Call List", "Crew Call List")]
    assert order == sorted(order)


def test_header_shows_title_day_of_total_and_draft_banner(monkeypatch):
    _patch_depts(monkeypatch)
    html = _html(_data(status="draft"))
    assert "Farm Feature" in html and "Day 3 of 12" in html and "2026-10-01" in html
    assert "DRAFT" in html
    assert "DRAFT" not in _html(_data(status="published"))


def test_hidden_section_is_omitted(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = tpl.default_config()
    next(s for s in cfg["sections"] if s["key"] == "scenes")["visible"] = False
    html = _html(_data(cfg))
    assert "Scene Schedule" not in html and "OFFICE" not in html


def test_section_order_and_label_follow_template(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = tpl.default_config()
    secs = {s["key"]: s for s in cfg["sections"]}
    secs["crew"]["label"] = "Crew Calls"
    cfg["sections"] = [secs["header"], secs["crew"], secs["cast"]] + \
        [s for s in cfg["sections"] if s["key"] not in ("header", "crew", "cast")]
    html = _html(_data(cfg))
    assert html.index("Crew Calls") < html.index("Cast Call List")


def test_custom_field_renders_only_in_its_section_and_once(monkeypatch):
    _patch_depts(monkeypatch)
    html = _html(_data(full_config(), custom_values={"wind": "SSW 15"}))
    assert html.count("SSW 15") == 1
    assert html.index("Wind") < html.index("Locations")     # day_info is above locations


def test_field_default_used_when_no_value(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = full_config()
    next(f for f in cfg["day_fields"] if f["key"] == "wind")["default"] = "Calm"
    assert "Calm" in _html(_data(cfg))


def test_link_field_renders_anchor_and_escapes(monkeypatch):
    _patch_depts(monkeypatch)
    html = _html(_data(full_config(), custom_values={"map": "https://x.com/m?a=1&b=2"}))
    assert '<a href="https://x.com/m?a=1&amp;b=2">' in html


def test_user_text_is_escaped(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = full_config()
    cfg["day_fields"][0]["label"] = "<script>alert(1)</script>"
    cfg["blocks"][0]["body"] = "<img src=x onerror=alert(1)>"
    html = _html(_data(cfg, weather="<b>bold</b>"))
    assert "<script>" not in html and "<img" not in html and "<b>bold</b>" not in html
    assert "&lt;script&gt;" in html


def test_scene_and_cast_and_crew_custom_columns(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = full_config()
    data = _data(cfg,
                 scene_extras={"sc1": {"story_day": "Day 4"}},
                 cast=[{"call_time": "06:00", "status_code": "W", "extra": {"pickup": "05:15"},
                        "casting": {"character_name": "HERO", "actor_name": "Jo", "tier": "lead"}}],
                 crew=[{"call_time": "05:30", "extra": {"vehicle": "Van 2"},
                        "crew": {"department_code": "camera", "role": "DoP", "contact": {"name": "Gary"}}}])
    html = _html(data)
    for expected in ("Story day", "Day 4", "P/U", "05:15", "Vehicle", "Van 2"):
        assert expected in html


def test_background_cast_stays_in_cast_when_extras_hidden():
    cfg = tpl.default_config()
    bg = {"call_time": None, "extra": {}, "casting": {"character_name": "CROWD", "tier": "background"}}
    main, extras = render.split_cast(_data(cfg, cast=[bg]), cfg)
    assert main == [bg] and extras == []


def test_background_cast_moves_to_extras_when_visible():
    cfg = tpl.default_config()
    next(s for s in cfg["sections"] if s["key"] == "extras")["visible"] = True
    lead = {"extra": {}, "casting": {"character_name": "HERO", "tier": "lead"}}
    bg = {"extra": {}, "casting": {"character_name": "CROWD", "tier": "background"}}
    main, extras = render.split_cast(_data(cfg, cast=[lead, bg]), cfg)
    assert main == [lead] and extras == [bg]


def test_notes_blocks_with_day_override(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = full_config()
    html = _html(_data(cfg))
    assert "Special notes" in html and "Closed shoes" in html
    html = _html(_data(cfg, block_overrides={"safety": "Hard hats today"}))
    assert "Hard hats today" in html and "Closed shoes" not in html


def test_key_crew_and_general_call_in_header(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = full_config()
    next(f for f in cfg["day_fields"] if f["key"] == "general_call")["visible"] = True
    data = _data(cfg, general_call="06:00", header_values={"director": "B. Other"})
    html = _html(data)
    assert "General Call" in html and "06:00" in html
    assert "Director" in html and "B. Other" in html and "A. Director" not in html


def test_unknown_section_key_in_config_is_a_noop(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = tpl.default_config()
    cfg["sections"].append({"key": "mystery", "label": "Mystery", "visible": True})
    assert "Mystery" not in _html(_data(cfg))


def _enable(cfg, *keys):
    for s in cfg["sections"]:
        if s["key"] in keys:
            s["visible"] = True
    return cfg


def test_extras_section_lists_background_rows(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = _enable(full_config(), "extras")
    lead = {"call_time": "06:00", "extra": {}, "casting": {"character_name": "HERO", "actor_name": "Jo", "tier": "lead"}}
    bg = {"call_time": "07:00", "extra": {"pickup": "06:30"},
          "casting": {"character_name": "CROWD", "actor_name": "Extras Co", "tier": "background"}}
    html = _html(_data(cfg, cast=[lead, bg]))
    extras_part = html[html.index("Extras"):]
    assert "CROWD" in extras_part and "06:30" in extras_part
    cast_part = html[html.index("Cast Call List"):html.index("Extras")]
    assert "HERO" in cast_part and "CROWD" not in cast_part


def test_extras_section_omitted_when_no_background(monkeypatch):
    _patch_depts(monkeypatch)
    assert "Extras" not in _html(_data(_enable(full_config(), "extras")))


def test_dept_calls_use_default_then_override(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = _enable(full_config(), "dept_calls")
    html = _html(_data(cfg))
    assert "Wardrobe" in html and "06:00" in html and "Pippa" in html
    html = _html(_data(cfg, dept_overrides={"wardrobe": {"call": "07:15", "as_per": "Sam"}}))
    assert "07:15" in html and "Sam" in html and "Pippa" not in html


def test_dept_calls_omitted_when_none_configured(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = _enable(tpl.default_config(), "dept_calls")
    assert "Department Calls" not in _html(_data(cfg))


def test_catering_grid_uses_effective_counts_and_totals(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = _enable(full_config(), "catering")
    eff = {m: {"crew": 40, "cast": 10, "add_crew": 0, "extras": 1}
           for m in ("craft", "breakfast", "lunch", "dinner")}
    eff["dinner"] = {"crew": 0, "cast": 0, "add_crew": 0, "extras": 0}
    html = _html(_data(cfg, catering_effective=eff))
    assert "Catering" in html and "<td>40</td>" in html and "<td>51</td>" in html


def test_catering_falls_back_to_roster_counts(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = _enable(full_config(), "catering")
    html = _html(_data(cfg))       # 1 crew + 1 cast in _data()
    assert "Catering" in html and "<td>2</td>" in html


def test_catering_omitted_when_everything_is_zero(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = _enable(full_config(), "catering")
    assert "Catering" not in _html(_data(cfg, crew=[], cast=[]))


def test_advanced_schedule_renders_next_day_scenes(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = _enable(full_config(), "advanced")
    ctx = dict(CTX, advanced={
        "day": {"day_number": 4, "shoot_date": "2026-10-02"},
        "scenes": [{"id": "n1", "scene_number": "44", "int_ext": "EXT", "setting": "FARM",
                    "time_of_day": "NIGHT", "page_length_eighths": 5}]})
    html = _html(_data(cfg), ctx)
    assert "Advanced Schedule" in html and "Day 4" in html and "FARM" in html and "5/8" in html


def test_advanced_schedule_omitted_without_next_day(monkeypatch):
    _patch_depts(monkeypatch)
    cfg = _enable(full_config(), "advanced")
    assert "Advanced Schedule" not in _html(_data(cfg), CTX)
