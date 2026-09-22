"""Per-production call sheet template: defaults, validation, storage.

See docs/superpowers/specs/2026-09-21-call-sheet-customization-design.md.
Gated at the route layer by production_authz; this module trusts its caller.
"""
import re

from db.supabase_client import get_supabase_admin
from services import call_sheet_values as values

CONFIG_VERSION = 1

SECTION_KEYS = ("header", "day_info", "locations", "scenes", "cast", "extras",
                "crew", "dept_calls", "catering", "notes", "advanced")
SECTION_LABELS = {
    "header": "Header", "day_info": "Day Info", "locations": "Locations",
    "scenes": "Scene Schedule", "cast": "Cast Call List", "extras": "Extras",
    "crew": "Crew Call List", "dept_calls": "Department Calls",
    "catering": "Catering", "notes": "Notes", "advanced": "Advanced Schedule",
}
# v1 rendered exactly these sections.
DEFAULT_VISIBLE = {"header", "day_info", "locations", "scenes", "cast", "crew", "notes"}

FIELD_TYPES = ("text", "textarea", "time", "link", "number")
FIELD_SECTIONS = ("header", "day_info", "notes")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
CAPS = {"day_fields": 40, "cast_columns": 15, "crew_columns": 15, "scene_columns": 15,
        "departments": 30, "blocks": 20, "key_crew": 20}
MAX_LABEL, MAX_SHORT, MAX_DEFAULT, MAX_BODY = 60, 200, 2000, 10000

# (key, label, type, section, visible) -- v1's weather/sun/meal times print in
# the day-info strip; hospital/safety/general notes print in the footer;
# parking_notes was never printed by v1, so it defaults hidden.
_BUILTIN_SPEC = (
    ("weather", "Weather", "text", "day_info", True),
    ("sunrise_time", "Sunrise", "time", "day_info", True),
    ("sunset_time", "Sunset", "time", "day_info", True),
    ("breakfast_time", "Breakfast", "time", "day_info", True),
    ("lunch_time", "Lunch", "time", "day_info", True),
    ("general_call", "General Call", "time", "header", False),
    ("nearest_hospital", "Nearest Hospital", "text", "notes", True),
    ("safety_notes", "Safety / COVID Officer", "textarea", "notes", True),
    ("general_notes", "General Notes", "textarea", "notes", True),
    ("parking_notes", "Parking Notes", "textarea", "notes", False),
)
BUILTIN_TYPES = {key: ftype for key, _l, ftype, _s, _v in _BUILTIN_SPEC}
BUILTIN_KEYS = tuple(BUILTIN_TYPES)


class ConfigError(Exception):
    def __init__(self, errors):
        super().__init__("Invalid template")
        self.errors = errors


class StaleTemplate(Exception):
    pass


def default_config():
    return {
        "v": CONFIG_VERSION,
        "sections": [{"key": k, "label": SECTION_LABELS[k], "visible": k in DEFAULT_VISIBLE}
                     for k in SECTION_KEYS],
        "day_fields": [
            {"key": k, "label": label, "type": t, "section": s, "default": "",
             "sensitive": False, "visible": vis, "builtin": True}
            for k, label, t, s, vis in _BUILTIN_SPEC],
        "cast_columns": [], "crew_columns": [], "scene_columns": [],
        "departments": [], "blocks": [], "key_crew": [],
    }


# ---------- validation ----------

def _err(errors, path, message):
    errors.append({"path": path, "message": message})


def _items(raw, name, errors):
    if raw is None:
        return []
    if not isinstance(raw, list):
        _err(errors, name, "must be a list")
        return []
    if len(raw) > CAPS[name]:
        _err(errors, name, f"at most {CAPS[name]} entries")
        return []
    return raw


def _key(item, path, seen, errors):
    key = item.get("key") if isinstance(item, dict) else None
    if not isinstance(key, str) or not KEY_RE.match(key):
        _err(errors, f"{path}.key",
             "key must be lowercase letters, digits and underscores, starting with a letter (max 40)")
        return None
    if key in seen:
        _err(errors, f"{path}.key", f"duplicate key '{key}'")
        return None
    seen.add(key)
    return key


def _text(item, field, path, errors, limit, required=True):
    val = item.get(field, "")
    if not isinstance(val, str):
        _err(errors, f"{path}.{field}", "must be text")
        return ""
    if required and not val.strip():
        _err(errors, f"{path}.{field}", "is required")
    if len(val) > limit:
        _err(errors, f"{path}.{field}", f"must be at most {limit} characters")
    return val


def _validate_sections(raw, errors):
    out, seen = [], set()
    if not isinstance(raw, list):
        _err(errors, "sections", "must be a list")
        return out
    for i, item in enumerate(raw):
        path = f"sections[{i}]"
        if not isinstance(item, dict) or item.get("key") not in SECTION_KEYS:
            _err(errors, path, "unknown section key")
            continue
        if item["key"] in seen:
            _err(errors, path, f"duplicate section '{item['key']}'")
            continue
        seen.add(item["key"])
        out.append({"key": item["key"],
                    "label": _text(item, "label", path, errors, MAX_LABEL),
                    "visible": bool(item.get("visible", True))})
    missing = [k for k in SECTION_KEYS if k not in seen]
    if missing:
        _err(errors, "sections", f"missing sections: {', '.join(missing)}")
    return out


def _validate_day_fields(raw, errors):
    out, seen = [], set()
    for i, item in enumerate(_items(raw, "day_fields", errors)):
        path = f"day_fields[{i}]"
        if not isinstance(item, dict):
            _err(errors, path, "must be an object")
            continue
        key = _key(item, path, seen, errors)
        if key is None:
            continue
        builtin = key in BUILTIN_TYPES
        ftype = item.get("type")
        if ftype not in FIELD_TYPES:
            _err(errors, f"{path}.type", f"type must be one of {', '.join(FIELD_TYPES)}")
            continue
        if builtin and ftype != BUILTIN_TYPES[key]:
            _err(errors, f"{path}.type", "type is locked for built-in fields")
            continue
        if item.get("section") not in FIELD_SECTIONS:
            _err(errors, f"{path}.section", f"section must be one of {', '.join(FIELD_SECTIONS)}")
            continue
        default = _text(item, "default", path, errors, MAX_DEFAULT, required=False)
        if default != "":
            try:
                values.validate_value(ftype, default)
            except ValueError as e:
                _err(errors, f"{path}.default", str(e))
        out.append({"key": key, "label": _text(item, "label", path, errors, MAX_LABEL),
                    "type": ftype, "section": item["section"], "default": default,
                    "sensitive": bool(item.get("sensitive", False)),
                    "visible": bool(item.get("visible", True)), "builtin": builtin})
    missing = [k for k in BUILTIN_KEYS if k not in seen]
    if missing:
        _err(errors, "day_fields", f"built-in fields cannot be removed: {', '.join(missing)}")
    return out


def _validate_columns(raw, name, errors):
    out, seen = [], set()
    for i, item in enumerate(_items(raw, name, errors)):
        path = f"{name}[{i}]"
        if not isinstance(item, dict):
            _err(errors, path, "must be an object")
            continue
        key = _key(item, path, seen, errors)
        if key is None:
            continue
        if item.get("type") not in FIELD_TYPES:
            _err(errors, f"{path}.type", f"type must be one of {', '.join(FIELD_TYPES)}")
            continue
        out.append({"key": key, "label": _text(item, "label", path, errors, MAX_LABEL),
                    "type": item["type"], "sensitive": bool(item.get("sensitive", False))})
    return out


def _validate_departments(raw, errors):
    out, seen = [], set()
    for i, item in enumerate(_items(raw, "departments", errors)):
        path = f"departments[{i}]"
        if not isinstance(item, dict):
            _err(errors, path, "must be an object")
            continue
        key = _key(item, path, seen, errors)
        if key is None:
            continue
        call = item.get("default_call", "")
        try:
            call = values.normalize_time(call) or ""
        except ValueError as e:
            _err(errors, f"{path}.default_call", str(e))
            call = ""
        out.append({"key": key, "label": _text(item, "label", path, errors, MAX_LABEL),
                    "default_call": call,
                    "as_per": _text(item, "as_per", path, errors, MAX_SHORT, required=False)})
    return out


def _validate_labelled(raw, name, value_field, limit, errors):
    out, seen = [], set()
    for i, item in enumerate(_items(raw, name, errors)):
        path = f"{name}[{i}]"
        if not isinstance(item, dict):
            _err(errors, path, "must be an object")
            continue
        key = _key(item, path, seen, errors)
        if key is None:
            continue
        out.append({"key": key, "label": _text(item, "label", path, errors, MAX_LABEL),
                    value_field: _text(item, value_field, path, errors, limit, required=False)})
    return out


def validate_config(config):
    """Return a clean copy (unknown props stripped, builtin flags server-set)
    or raise ConfigError with a list of {path, message}."""
    if not isinstance(config, dict):
        raise ConfigError([{"path": "config", "message": "must be an object"}])
    errors = []
    if config.get("v") != CONFIG_VERSION:
        _err(errors, "v", f"unsupported config version (expected {CONFIG_VERSION})")
    clean = {
        "v": CONFIG_VERSION,
        "sections": _validate_sections(config.get("sections"), errors),
        "day_fields": _validate_day_fields(config.get("day_fields"), errors),
        "cast_columns": _validate_columns(config.get("cast_columns"), "cast_columns", errors),
        "crew_columns": _validate_columns(config.get("crew_columns"), "crew_columns", errors),
        "scene_columns": _validate_columns(config.get("scene_columns"), "scene_columns", errors),
        "departments": _validate_departments(config.get("departments"), errors),
        "blocks": _validate_labelled(config.get("blocks"), "blocks", "body", MAX_BODY, errors),
        "key_crew": _validate_labelled(config.get("key_crew"), "key_crew", "value", MAX_SHORT, errors),
    }
    if errors:
        raise ConfigError(errors)
    return clean


# ---------- storage ----------

def _lookup(supabase, production_id):
    res = (supabase.table("call_sheet_templates").select("*")
           .eq("production_id", production_id).limit(1).execute())
    return res.data[0] if res.data else None


def get_template(production_id, supabase=None):
    """Stored config, or the default. Never creates a row."""
    supabase = supabase or get_supabase_admin()
    row = _lookup(supabase, production_id)
    if row:
        return {"config": row["config"], "updated_at": row.get("updated_at"), "is_default": False}
    return {"config": default_config(), "updated_at": None, "is_default": True}


def save_template(production_id, config, user_id, expected_updated_at=None, supabase=None):
    clean = validate_config(config)
    supabase = supabase or get_supabase_admin()
    existing = _lookup(supabase, production_id)
    if existing:
        # Strict: a client that loaded the default (None) while a row now
        # exists is stale too.
        if expected_updated_at != existing.get("updated_at"):
            raise StaleTemplate()
        res = (supabase.table("call_sheet_templates")
               .update({"config": clean, "updated_by": user_id})
               .eq("id", existing["id"]).execute())
        saved = res.data[0]
    else:
        saved = (supabase.table("call_sheet_templates")
                 .insert({"production_id": production_id, "config": clean,
                          "updated_by": user_id}).execute().data[0])
    return {"config": saved["config"], "updated_at": saved.get("updated_at"), "is_default": False}
