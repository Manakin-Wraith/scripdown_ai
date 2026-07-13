"""Deterministic quality checks for a scene's derived location.

The single source of truth for "is this location clean?" — consumed by the
locations/health endpoint, the backfill's verification pass, and the golden
regression tests. Pure: no I/O, never raises on odd input.
"""
import re
from typing import List, Dict

from services.location_resolver import (
    normalize_place, derive_base_place, derive_sub_place,
    TIME_WORDS, INT_EXT_TOKENS, suggest_merges,
)

# A segment that is only numbers, "<n> <n>" (split scene-time like "2 7"), or a
# truncated "<n> A(.M.)" — noise, never a real place.
_DIGIT_NOISE = re.compile(r"^\d+(?:[ /]\d+| [A-Z])?$")
# Prose thresholds — a real place is short; longer/among these signals a caught
# stage direction. Flag-only, so false positives are acceptable.
_MAX_PLACE_WORDS = 6
_MAX_PLACE_CHARS = 45
# Modifiers that combine with a bare TIME_WORDS entry into a still-a-time-of-day
# phrase ("EARLY MORNING", "LATE NIGHT") — TIME_WORDS itself only holds the
# single-token forms, so a whole-segment membership check misses these.
_TIME_MODIFIERS = {"EARLY", "LATE"}


def _looks_like_time(n: str) -> bool:
    if n in TIME_WORDS:
        return True
    words = n.split()
    if not words:
        return False
    return any(w in TIME_WORDS for w in words) and \
        all(w in TIME_WORDS or w in _TIME_MODIFIERS for w in words)


def _issue(code, severity, message, auto_fixable, suggestion=None):
    d = {"code": code, "severity": severity, "message": message, "auto_fixable": auto_fixable}
    if suggestion:
        d["suggestion"] = suggestion
    return d


def _segments(base: str, sub: str) -> List[str]:
    parts = []
    for chunk in (base or "", sub or ""):
        parts.extend(p for p in chunk.split(" - ") if p.strip())
    return parts


def classify_location(base: str, sub: str, setting: str, sibling_bases: List[str]) -> List[Dict]:
    """Return the list of issues for one location (empty == clean)."""
    issues: List[Dict] = []
    base = (base or "").strip()
    sub = (sub or "").strip()

    for seg in _segments(base, sub):
        n = normalize_place(seg)
        if not n:
            continue
        if _looks_like_time(n):
            issues.append(_issue("TIME_RESIDUE", "warn", f"'{seg}' looks like a time of day", True))
        if _DIGIT_NOISE.match(n):
            issues.append(_issue("DIGIT_NOISE", "warn", f"'{seg}' looks like stray numbers", True))
        if n in INT_EXT_TOKENS or seg.strip().startswith("/"):
            issues.append(_issue("INT_EXT_RESIDUE", "warn", f"'{seg}' has an INT/EXT remnant", True))
        if len(n.split()) > _MAX_PLACE_WORDS or len(n) > _MAX_PLACE_CHARS:
            issues.append(_issue("DESCRIPTION_BLEED", "warn",
                                 f"'{seg}' looks like description text, not a location", False))

    # POSSIBLE_PARENT: base is another sibling base plus trailing words.
    nb = normalize_place(base)
    for other in sibling_bases:
        no = normalize_place(other)
        if no and no != nb and nb.startswith(no + " "):
            issues.append(_issue("POSSIBLE_PARENT", "info",
                                 f"Could group under '{other}'", False, suggestion=other))
            break

    # NEAR_DUPLICATE: this base clusters with a differently-spelled sibling.
    # suggest_merges picks ONE member as "canonical" per group, which may
    # coincide with this very base (e.g. it's the shortest spelling) — that
    # doesn't make the cluster any less of a duplicate, so flag whenever this
    # base sits in a group with more than one distinct spelling, and point the
    # suggestion at whichever member differs from this one.
    for group in suggest_merges(sibling_bases):
        members = group.get("members", [])
        norm_members = {normalize_place(m) for m in members}
        if nb in norm_members and len(norm_members) > 1:
            canonical = group.get("canonical")
            if normalize_place(canonical) == nb:
                canonical = next((m for m in members if normalize_place(m) != nb), canonical)
            issues.append(_issue("NEAR_DUPLICATE", "info",
                                 f"Looks like a duplicate of '{canonical}'", False, suggestion=canonical))
            break

    # De-dupe by (code, suggestion) preserving order.
    seen, out = set(), []
    for i in issues:
        k = (i["code"], i.get("suggestion"))
        if k not in seen:
            seen.add(k)
            out.append(i)
    return out


def lint_script_locations(scenes: List[Dict]) -> Dict:
    """Build the per-location issue report for a script's scenes."""
    entries = []  # (base, sub, setting)
    bases = []
    for s in scenes or []:
        if s.get("is_omitted"):
            continue
        base = s.get("location_canonical") or derive_base_place(
            s.get("setting"), s.get("int_ext"), s.get("time_of_day"), s.get("location_hierarchy"))
        sub = derive_sub_place(
            s.get("setting"), s.get("int_ext"), s.get("time_of_day"), s.get("location_hierarchy"))
        if base:
            entries.append((base, sub, s.get("setting") or ""))
            bases.append(base)

    sibling_bases = sorted(set(bases))
    by_key: Dict[str, List[Dict]] = {}
    for base, sub, setting in entries:
        key = f"{base}|{sub}" if sub else base
        if key in by_key:
            continue
        issues = classify_location(base, sub, setting, sibling_bases)
        if issues:
            by_key[key] = issues
    return {"total": len(by_key), "by_key": by_key}
