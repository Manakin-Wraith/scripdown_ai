"""Pure value validation / per-key merge helpers for call sheet customization.

No DB access. See docs/superpowers/specs/2026-09-21-call-sheet-customization-design.md
("Validation rules").
"""
import re
from urllib.parse import urlparse

TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?$")
MAX_TEXT = 2000
MAX_TEXTAREA = 10000
MAX_COUNT = 10000
MEALS = ("craft", "breakfast", "lunch", "dinner")
CATERING_GROUPS = ("crew", "cast", "add_crew", "extras")


def normalize_time(value):
    """'06:30:00' -> '06:30'; ''/None -> None; anything else -> ValueError."""
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not TIME_RE.match(value):
        raise ValueError("must be a time like 06:30")
    return value[:5]


def validate_value(ftype, value):
    """Validate one value for a field type. None means 'clear this key'."""
    if value is None:
        return None
    if ftype == "time":
        return normalize_time(value)
    if ftype in ("text", "textarea"):
        if not isinstance(value, str):
            raise ValueError("must be text")
        limit = MAX_TEXTAREA if ftype == "textarea" else MAX_TEXT
        if len(value) > limit:
            raise ValueError(f"must be at most {limit} characters")
        return value
    if ftype == "number":
        if isinstance(value, bool):
            raise ValueError("must be a number")
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            if value == "":
                return None
            try:
                return float(value) if "." in value else int(value)
            except ValueError:
                raise ValueError("must be a number")
        raise ValueError("must be a number")
    if ftype == "link":
        if value == "":
            return None
        if not isinstance(value, str) or len(value) > MAX_TEXT:
            raise ValueError("must be a link")
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("must be an http(s) link")
        return value
    if ftype == "count":
        if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > MAX_COUNT:
            raise ValueError(f"must be a whole number 0-{MAX_COUNT}")
        return value
    raise ValueError(f"unknown type {ftype}")


def merge_values(existing, incoming, types):
    """Per-key merge. Returns (merged, ignored_keys).

    Keys not in `types` are ignored (reported), never stored. `None` clears a
    key. Stored keys absent from `types` (e.g. a field later removed from the
    template) are left untouched so re-adding the field restores them.
    """
    if not isinstance(incoming, dict):
        raise ValueError("must be an object")
    merged = dict(existing or {})
    ignored = []
    for key, raw in incoming.items():
        if key not in types:
            ignored.append(key)
            continue
        try:
            value = validate_value(types[key], raw)
        except ValueError as e:
            raise ValueError(f"{key}: {e}")
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    return merged, ignored


def merge_nested(existing, incoming, allowed_outer, inner_types):
    """Two-level per-key merge ({outer: {inner: value}}). Returns (merged, ignored)."""
    if not isinstance(incoming, dict):
        raise ValueError("must be an object")
    merged = {k: dict(val) for k, val in (existing or {}).items() if isinstance(val, dict)}
    ignored = []
    for outer, inner in incoming.items():
        if outer not in allowed_outer:
            ignored.append(outer)
            continue
        try:
            new_inner, ign = merge_values(merged.get(outer, {}), inner, inner_types)
        except ValueError as e:
            raise ValueError(f"{outer}.{e}")
        ignored.extend(f"{outer}.{k}" for k in ign)
        if new_inner:
            merged[outer] = new_inner
        else:
            merged.pop(outer, None)
    return merged, ignored


def catering_defaults(crew_rows, cast_rows):
    """Roster-derived headcounts, the same for every meal until overridden."""
    extras = sum(1 for r in cast_rows if (r.get("casting") or {}).get("tier") == "background")
    counts = {"crew": len(crew_rows), "cast": len(cast_rows) - extras,
              "add_crew": 0, "extras": extras}
    return {meal: dict(counts) for meal in MEALS}


def effective_catering(defaults, overrides):
    out = {meal: dict(groups) for meal, groups in defaults.items()}
    for meal, groups in (overrides or {}).items():
        if meal in out and isinstance(groups, dict):
            for group, n in groups.items():
                if group in out[meal]:
                    out[meal][group] = n
    return out
