"""Shared fixtures for call sheet customization tests (not a test module)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_service as svc
import services.call_sheet_template_service as tpl
from test_call_sheet_service import MockSupabase, _store


def full_config():
    cfg = tpl.default_config()
    cfg["day_fields"] += [
        {"key": "wind", "label": "Wind", "type": "text", "section": "day_info",
         "default": "", "sensitive": False, "visible": True, "builtin": False},
        {"key": "map", "label": "Map", "type": "link", "section": "notes",
         "default": "", "sensitive": False, "visible": True, "builtin": False},
    ]
    cfg["scene_columns"] = [{"key": "story_day", "label": "Story day", "type": "text", "sensitive": False}]
    cfg["cast_columns"] = [{"key": "pickup", "label": "P/U", "type": "time", "sensitive": False}]
    cfg["crew_columns"] = [{"key": "vehicle", "label": "Vehicle", "type": "text", "sensitive": False}]
    cfg["departments"] = [{"key": "wardrobe", "label": "Wardrobe", "default_call": "06:00", "as_per": "Pippa"}]
    cfg["blocks"] = [{"key": "safety", "label": "Special notes", "body": "Closed shoes"}]
    cfg["key_crew"] = [{"key": "director", "label": "Director", "value": "A. Director"}]
    return cfg


def sheet_row(**kw):
    row = {"id": "cs1", "production_id": "p1", "shooting_day_id": "d1", "status": "draft"}
    row.update(kw)
    return row


def make_store(cfg=None, **overrides):
    base = _store(
        call_sheets=[sheet_row()],
        call_sheet_templates=[{"id": "t1", "production_id": "p1",
                               "config": cfg or full_config(),
                               "updated_at": "2026-09-21T00:00:00+00:00"}],
    )
    base.update(overrides)
    return base


def patch_svc(monkeypatch, store):
    mock = MockSupabase(store)
    monkeypatch.setattr(svc, "get_supabase_admin", lambda: mock)
    monkeypatch.setattr(tpl, "get_supabase_admin", lambda: mock)
    return mock
