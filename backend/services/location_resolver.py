"""
Location Resolver — base-place derivation and merge suggestions.

Mirrors entity_resolver.py (characters) for locations. Derives a normalized
"base physical place" from a free-text scene setting, ignoring INT/EXT and
time-of-day, and suggests likely-duplicate places for user-confirmed merging.

Base place is the grouping/merge key stored in scenes.location_canonical.
"""

import re
import json
from collections import Counter
from difflib import SequenceMatcher
from typing import Dict, List, Optional

TIME_WORDS = {
    "DAY", "NIGHT", "DUSK", "DAWN", "MORNING", "EVENING",
    "AFTERNOON", "CONTINUOUS", "LATER", "SAME", "MAGIC HOUR",
}

INT_EXT_TOKENS = {"INT", "EXT", "INT/EXT", "I/E"}

FUZZY_THRESHOLD = 0.82
MIN_FUZZY_LEN = 4

_INT_EXT_PREFIX = re.compile(
    r"^\s*(INT\.?/EXT\.?|INT\.?|EXT\.?|I/E\.?)(?=[\s.\-:]|$)\s*[-.:]?\s*",
    re.IGNORECASE,
)
_LEADING_ARTICLE = re.compile(r"^(THE|A|AN)\s+", re.IGNORECASE)
_DASH_SPLIT = re.compile(r"\s*[-–—]\s*")


def normalize_place(name: Optional[str]) -> str:
    """Canonical form for matching/grouping: uppercase, collapsed whitespace,
    leading article stripped, surrounding punctuation stripped."""
    if not name:
        return ""
    s = re.sub(r"\s+", " ", str(name).strip().upper())
    s = _LEADING_ARTICLE.sub("", s)
    s = s.strip(" .,-–—:;")
    return s


def canonicalize_setting(setting: Optional[str]) -> str:
    """Canonical *display* form for a scene setting.

    Removes the casing / whitespace / curly-quote noise that produces false
    duplicate locations (``villa`` / ``viLLA`` / ``VILLA``), while keeping the
    setting human-readable: unlike :func:`normalize_place` it does NOT strip
    articles or internal/trailing punctuation. Deterministic and idempotent —
    applied at ingestion and on manual scene edits so variants never diverge.
    """
    if not setting:
        return ""
    s = str(setting).replace("’", "'").replace("‘", "'")
    s = re.sub(r"\s+", " ", s).strip()
    return s.upper()


def derive_base_place(
    setting: Optional[str],
    int_ext: Optional[str] = None,
    time_of_day: Optional[str] = None,
    location_hierarchy=None,
) -> str:
    """Return the normalized base physical place for a scene.

    1. Prefer structured location_hierarchy[0] when present.
    2. Otherwise strip a leading INT/EXT prefix and any INT/EXT or
       time-of-day segments from the setting, keep the first place token.
    """
    # 1. Structured hierarchy wins
    if location_hierarchy:
        if isinstance(location_hierarchy, str):
            try:
                location_hierarchy = json.loads(location_hierarchy)
            except (ValueError, TypeError):
                location_hierarchy = []
        if location_hierarchy:
            return normalize_place(location_hierarchy[0])

    # 2. Parse from the free-text setting
    s = _INT_EXT_PREFIX.sub("", setting or "")
    parts = [p.strip() for p in _DASH_SPLIT.split(s) if p.strip()]
    kept = [
        p for p in parts
        if p.upper() not in TIME_WORDS and normalize_place(p) not in INT_EXT_TOKENS
    ]
    base = kept[0] if kept else s
    return normalize_place(base)


def derive_sub_place(
    setting: Optional[str],
    int_ext: Optional[str] = None,
    time_of_day: Optional[str] = None,
    location_hierarchy=None,
) -> str:
    """Return the normalized sub-location (everything under the base place).

    Mirrors derive_base_place but keeps parts[1:]. Prefers structured
    location_hierarchy[1:] when present; otherwise parses the free-text setting.
    Returns "" when the scene has no sub-location.
    """
    if location_hierarchy:
        if isinstance(location_hierarchy, str):
            try:
                location_hierarchy = json.loads(location_hierarchy)
            except (ValueError, TypeError):
                location_hierarchy = []
        if location_hierarchy:
            if len(location_hierarchy) > 1:
                return normalize_place(" - ".join(location_hierarchy[1:]))
            return ""

    s = _INT_EXT_PREFIX.sub("", setting or "")
    parts = [p.strip() for p in _DASH_SPLIT.split(s) if p.strip()]
    kept = [
        p for p in parts
        if p.upper() not in TIME_WORDS and normalize_place(p) not in INT_EXT_TOKENS
    ]
    if len(kept) > 1:
        return normalize_place(" - ".join(kept[1:]))
    return ""


def suggest_merges(
    base_places: List[str],
    existing_aliases: Optional[Dict[str, str]] = None,
) -> List[Dict]:
    """Cluster near-duplicate base places for user-confirmed merging.

    Deterministic normalization catches article/spacing/case differences;
    difflib catches true typos above FUZZY_THRESHOLD (short-string guarded).
    Never applies a merge — returns suggestions only.
    """
    existing_aliases = existing_aliases or {}
    counts = Counter(p for p in base_places if p)
    uniques = [p for p in counts if p not in existing_aliases]
    norm = {p: normalize_place(p) for p in uniques}

    groups: List[Dict] = []
    used: set = set()

    for i, a in enumerate(uniques):
        if a in used:
            continue
        members = [a]
        for b in uniques[i + 1:]:
            if b in used:
                continue
            na, nb = norm[a], norm[b]
            if na == nb:
                members.append(b)
                used.add(b)
            elif len(na) >= MIN_FUZZY_LEN and len(nb) >= MIN_FUZZY_LEN and \
                    SequenceMatcher(None, na, nb).ratio() >= FUZZY_THRESHOLD:
                members.append(b)
                used.add(b)

        if len(members) > 1:
            used.add(a)
            canonical = max(members, key=lambda m: (counts[m], -len(m)))
            reason = "variant" if all(norm[m] == norm[members[0]] for m in members) else "typo"
            groups.append({
                "canonical": canonical,
                "members": members,
                "reason": reason,
            })

    return groups


def rewrite_place_token(setting: Optional[str], from_token: str, to_token: str) -> str:
    """Replace the first case-insensitive occurrence of from_token with to_token,
    preserving the rest of the setting. Used for base and sub renames."""
    if not setting or not from_token:
        return setting or ""
    return re.sub(re.escape(from_token), to_token, setting, count=1, flags=re.IGNORECASE)


def resolve_location(
    setting: Optional[str],
    int_ext: Optional[str] = None,
    time_of_day: Optional[str] = None,
    location_hierarchy=None,
    parent_alias_map: Optional[Dict[str, str]] = None,
    sub_alias_map: Optional[Dict] = None,
) -> tuple:
    """Apply parent then sub aliases to a scene setting (pure).

    Returns (new_setting, location_canonical_norm). Parent map is applied first
    so the sub lookup is keyed on the final parent. Sub is re-derived from the
    rewritten setting (not the possibly-stale hierarchy).
    """
    parent_alias_map = parent_alias_map or {}
    sub_alias_map = sub_alias_map or {}

    setting = canonicalize_setting(setting)
    base = derive_base_place(setting, int_ext, time_of_day, location_hierarchy)
    canonical = parent_alias_map.get(base, base)

    new_setting = setting or ""
    if base and normalize_place(canonical) != base:
        new_setting = re.sub(re.escape(base), canonical, new_setting, flags=re.IGNORECASE)

    parent_norm = normalize_place(canonical)
    sub = derive_sub_place(new_setting, int_ext, time_of_day, None)
    if sub:
        new_sub = sub_alias_map.get((parent_norm, sub))
        if new_sub and normalize_place(new_sub) != sub:
            new_setting = rewrite_place_token(new_setting, sub, new_sub)

    return new_setting, parent_norm
