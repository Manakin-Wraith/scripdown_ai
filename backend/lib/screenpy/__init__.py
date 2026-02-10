"""
ScripDown vendored fork of ScreenPy parser.

Original: https://github.com/drwiner/ScreenPy
Fork scope: parser/ + models.py only (no VSD/NLP dependencies)

Changes from upstream:
- Relative imports (no absolute screenpy.*)
- Pydantic v2 syntax (model_config, model_dump)
- Config-driven locale schema for TIME_OF_DAY + LOCATION_TYPES
- Afrikaans locale pre-loaded for SA market
"""

from .models import (
    Screenplay,
    Segment,
    ShotHeading,
    Dialogue,
    Transition,
    Character,
    LocationType,
    SegmentType,
    TransitionType,
    ShotType,
)
from .locale_config import ScreenplayLocale, get_locale, register_locale

__all__ = [
    "Screenplay",
    "Segment",
    "ShotHeading",
    "Dialogue",
    "Transition",
    "Character",
    "LocationType",
    "SegmentType",
    "TransitionType",
    "ShotType",
    "ScreenplayLocale",
    "get_locale",
    "register_locale",
]
