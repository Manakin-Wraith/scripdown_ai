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

# Fuzzy suggestion tuning — the ONLY place these live.
FUZZY_THRESHOLD = 0.82
MIN_FUZZY_LEN = 4

TIME_WORDS = {
    "DAY", "NIGHT", "DUSK", "DAWN", "MORNING", "EVENING",
    "AFTERNOON", "CONTINUOUS", "LATER", "SAME", "MAGIC HOUR",
}

INT_EXT_TOKENS = {"INT", "EXT", "INT/EXT", "I/E"}

_INT_EXT_PREFIX = re.compile(
    r"^\s*(INT\.?/EXT\.?|INT\.?|EXT\.?|I/E\.?)\s*[-.:]?\s*",
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
