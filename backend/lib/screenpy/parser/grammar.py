"""
Grammar definitions for screenplay parsing based on The Hollywood Standard.

Vendored from ScreenPy with the following changes:
- TIME_WORDS loaded from locale_config (config-driven, not hard-coded)
- Relative imports instead of absolute screenpy.*

This module defines the pyparsing grammar for shot headings, transitions,
and other screenplay elements according to industry standards.
"""

from typing import Set
from enum import Enum

import pyparsing as pp

from ..locale_config import get_locale

# ---------------------------------------------------------------------------
# Basic character sets and tokens
# ---------------------------------------------------------------------------
CAPS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = CAPS.lower()
DIGITS = "0123456789"
ALPHANUMS = CAPS + DIGITS + "'" + "\\" + "/" + '"' + "'" + "_" + "," + "-" + "."
ALL_CHARS = ALPHANUMS + LOWER

# Whitespace and punctuation
WH = pp.White().suppress()
HYPHEN = WH + pp.Literal("-").suppress() + WH
OHYPHEN = pp.Literal("-").suppress() + WH
LP = pp.Literal("(")
RP = pp.Literal(")")
EOL = pp.Or([pp.LineEnd().suppress(), pp.Literal("\n")])


class ShotTypeEnum(str, Enum):
    """Enumeration of shot types."""
    CLOSE = "CLOSE"
    EXTREME_CLOSE = "EXTREME CLOSE"
    WIDE = "WIDE"
    MEDIUM = "MEDIUM"
    TWO_SHOT = "TWO SHOT"
    THREE_SHOT = "THREE SHOT"
    ESTABLISHING = "ESTABLISHING"
    TRACKING = "TRACKING"
    MOVING = "MOVING"
    ANGLE = "ANGLE"
    REVERSE = "REVERSE"
    CRANE = "CRANE"
    TILT = "TILT"
    PAN = "PAN"
    ZOOM = "ZOOM"
    POV = "POV"
    INSERT = "INSERT"
    AERIAL = "AERIAL"
    UNDERWATER = "UNDERWATER"
    HANDHELD = "HANDHELD"


# ---------------------------------------------------------------------------
# Shot type definitions
# ---------------------------------------------------------------------------
CLOSE = pp.Combine(
    pp.Or([
        pp.Literal("CLOSE"),
        pp.Literal("CLOSE SHOT"),
        pp.Literal("CLOSEUP"),
        pp.Literal("CLOSE ANGLE"),
        pp.Literal("CLOSE-UP"),
    ]).setResultsName("close"),
    joinString=" ",
    adjacent=False,
)

XCLOSE = pp.Or([
    pp.Literal("EXTREME CLOSEUP"),
    pp.Literal("EXTREME CLOSE-UP"),
    pp.Literal("TIGHT CLOSE"),
    pp.Literal("ECU"),
]).setResultsName("extreme_close")

WIDE = pp.Or([
    pp.Literal("WIDE"),
    pp.Literal("WIDE SHOT"),
    pp.Literal("WIDE ANGLE"),
    pp.Literal("WS"),
]).setResultsName("wide")

MEDIUM = pp.Or([
    pp.Literal("MED. SHOT"),
    pp.Literal("MEDIUM SHOT"),
    pp.Literal("MED"),
    pp.Literal("MS"),
]).setResultsName("medium")

TWO_SHOT = pp.Or([
    pp.Literal("TWO SHOT"),
    pp.Literal("2 SHOT"),
    pp.Literal("TWO-SHOT"),
]).setResultsName("two_shot")

THREE_SHOT = pp.Or([
    pp.Literal("THREE SHOT"),
    pp.Literal("3 SHOT"),
    pp.Literal("THREE-SHOT"),
]).setResultsName("three_shot")

ESTABLISHING = pp.Or([
    pp.Literal("ESTABLISHING SHOT"),
    pp.Literal("ESTABLISHING"),
    pp.Literal("(ESTABLISHING)"),
    pp.Literal("TO ESTABLISH"),
    pp.Literal("EST"),
]).setResultsName("establishing")

# Camera movement shots
TRACKING = pp.Or([
    pp.Literal("TRACKING SHOT"),
    pp.Literal("TRACKING"),
    pp.Literal("DOLLY"),
    pp.Literal("DOLLY SHOT"),
]).setResultsName("tracking")

MOVING = pp.Or([
    pp.Literal("MOVING"),
    pp.Literal("MOVING SHOT"),
    pp.Literal("STEADICAM"),
]).setResultsName("moving")

ANGLE = pp.Or([
    pp.Literal("NEW ANGLE"),
    pp.Literal("ANGLE"),
    pp.Literal("UP ANGLE"),
    pp.Literal("DOWN ANGLE"),
    pp.Literal("HIGH ANGLE"),
    pp.Literal("LOW ANGLE"),
    pp.Literal("ANGLE ON"),
]).setResultsName("angle")

REVERSE = pp.Or([
    pp.Literal("REVERSE ANGLE"),
    pp.Literal("REVERSE"),
    pp.Literal("REVERSE SHOT"),
]).setResultsName("reverse")

CRANE = pp.Literal("CRANE").setResultsName("crane")
TILT = pp.Literal("TILT").setResultsName("tilt")
PAN = pp.Literal("PAN").setResultsName("pan")
ZOOM = pp.Literal("ZOOM").setResultsName("zoom")

# POV shots
WHAT_X_SEES = pp.Combine(
    pp.Literal("WHAT") + pp.Word(ALPHANUMS) + pp.Literal("SEES"),
    joinString=" ",
    adjacent=False,
)

X_POV = pp.Combine(
    pp.Word(ALPHANUMS) + pp.Literal("'S POV"),
    joinString="",
    adjacent=False,
)

POV = pp.Or([
    pp.Literal("P.O.V."),
    pp.Literal("POV"),
    pp.Literal("POINT OF VIEW"),
    pp.Literal("MYSTERY POV"),
    pp.Literal("ANONYMOUS POV"),
    pp.Literal("THROUGH SNIPER SCOPE"),
    pp.Literal("POV SHOT"),
    pp.Literal("BINOCULAR POV"),
    pp.Literal("MICROSCOPIC POV"),
    pp.Literal("SUBJECTIVE CAMERA"),
    WHAT_X_SEES,
    X_POV,
]).setResultsName("pov")

# Special shots
INSERT = pp.Or([
    pp.Literal("INSERT SHOT"),
    pp.Literal("INSERT"),
]).setResultsName("insert")

AERIAL = pp.Or([
    pp.Literal("AERIAL"),
    pp.Literal("AERIAL SHOT"),
    pp.Literal("HELICOPTER SHOT"),
]).setResultsName("aerial")

UNDERWATER = pp.Or([
    pp.Literal("UNDERWATER"),
    pp.Literal("UNDERWATER SHOT"),
]).setResultsName("underwater")

HANDHELD = pp.Or([
    pp.Literal("HANDHELD SHOT"),
    pp.Literal("HANDHELD"),
    pp.Literal("(HANDHELD)"),
]).setResultsName("handheld")


# ---------------------------------------------------------------------------
# Combine all shot types
# ---------------------------------------------------------------------------
SHOT_TYPES = pp.Or([
    CLOSE,
    XCLOSE,
    WIDE,
    MEDIUM,
    TWO_SHOT,
    THREE_SHOT,
    ESTABLISHING,
    TRACKING,
    MOVING,
    ANGLE,
    REVERSE,
    CRANE,
    TILT,
    PAN,
    ZOOM,
    POV,
    INSERT,
    AERIAL,
    UNDERWATER,
    HANDHELD,
]).setResultsName("shot_type")

# Prepositions
BASIC_PREP = pp.oneOf([
    "ON", "OF", "WITH", "TO", "TOWARDS", "FROM", "IN",
    "UNDER", "OVER", "ABOVE", "AROUND", "INTO", "THROUGH"
])
PREP = BASIC_PREP + WH

# Transitions
CUT = pp.Literal("CUT")
DISSOLVE = pp.Literal("DISSOLVE")
FADE = pp.Literal("FADE")
WIPE = pp.Literal("WIPE")
MATCH = pp.Literal("MATCH")
HARD = pp.Literal("HARD")

TRANSITION_TYPES = [
    "CUT TO:",
    "FADE IN:",
    "FADE OUT.",
    "FADE TO BLACK.",
    "DISSOLVE TO:",
    "MATCH CUT TO:",
    "HARD CUT TO:",
    "WIPE TO:",
    "SMASH CUT TO:",
    "TIME CUT TO:",
    "JUMP CUT TO:",
    "FADE TO:",
]

TRANSITIONS = pp.Combine(
    pp.Optional(pp.Word(ALPHANUMS)) +
    pp.Or([CUT, DISSOLVE, FADE, WIPE, MATCH, HARD]) +
    pp.Optional(pp.Word(ALPHANUMS)) +
    pp.Optional(pp.Literal(":").suppress()),
    joinString=" ",
    adjacent=False,
).setResultsName("transition")

# Intercut and montage
INTERCUT = pp.Or([
    pp.Literal("INTERCUTTING"),
    pp.Literal("INTERCUT"),
    pp.Literal("CUTTING"),
    pp.Literal("CUTS"),
    pp.Literal("MONTAGE"),
    pp.Literal("VARIOUS SHOTS"),
    pp.Literal("SERIES OF SHOTS"),
]).setResultsName("intercut")


# ---------------------------------------------------------------------------
# Time of day — config-driven via locale_config
# ---------------------------------------------------------------------------
def build_time_words(locale_codes: list[str] | None = None) -> Set[str]:
    """
    Build the TIME_WORDS set from the locale registry.

    This replaces the hard-coded set in upstream ScreenPy.
    """
    locale = get_locale(locale_codes)
    words: Set[str] = set()
    # Add times_of_day (lowercased for matching)
    words.update(w.lower() for w in locale.times_of_day)
    # Add relative times
    words.update(w.lower() for w in locale.relative_times)
    # Add seasons
    words.update(w.lower() for w in locale.seasons)
    # Add weather
    words.update(w.lower() for w in locale.weather_time)
    return words


# Default: English-only (callers can rebuild with more locales)
TIME_WORDS: Set[str] = build_time_words(["en"])

ENUMERATED_TIME_WORD = pp.oneOf(list(TIME_WORDS), caseless=False)

# Location types
INT = pp.Or([pp.Literal("INT."), pp.Literal("INT")]).setResultsName("interior")
EXT = pp.Or([pp.Literal("EXT."), pp.Literal("EXT")]).setResultsName("exterior")
INT_EXT = pp.Or([
    pp.Literal("INT./EXT."),
    pp.Literal("INT/EXT"),
    pp.Literal("I/E"),
]).setResultsName("int_ext")

LOCATION_TYPE = pp.Or([INT_EXT, INT, EXT]).setResultsName("location_type")

# Segment parsing helpers
IN_CAPS = pp.OneOrMore(pp.Word(ALPHANUMS), stopOn=pp.Or([HYPHEN, EOL]))
IN_CAPS_W_CONDITION = IN_CAPS.addCondition(
    lambda toks: len(toks) > 1 or len(toks[0]) > 1
)
CAPS_SEGMENT = pp.Combine(IN_CAPS_W_CONDITION, joinString=" ", adjacent=False)

# Title detection (for character names)
TITLE = pp.Combine(
    pp.Word(ALPHANUMS, exact=1) + pp.Word(LOWER),
    joinString="",
    adjacent=True,
)

# Indentation parsing
def num_spaces(tokens):
    """Count the number of spaces in indentation."""
    return len(tokens[0])


SPACES = pp.OneOrMore(pp.White(ws=" ", min=1)).addParseAction(num_spaces)
MIN_2_SPACES = pp.OneOrMore(pp.White(ws=" ", min=2)).addParseAction(num_spaces)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def is_time_expression(text: str, locale_codes: list[str] | None = None) -> bool:
    """
    Check if text IS a time expression (the entire text, not just a substring).

    Uses the locale-aware TIME_WORDS set. If locale_codes is provided,
    builds a fresh set; otherwise uses the module-level default.
    """
    if locale_codes:
        time_words = build_time_words(locale_codes)
    else:
        time_words = TIME_WORDS

    text_lower = text.strip().rstrip('.').strip().lower()

    # Check if the whole text matches a known time word exactly
    if text_lower in time_words:
        return True

    # Check for time patterns (e.g., "3 AM", "10:30")
    import re
    time_patterns = [
        r"^\d{1,2}:\d{2}(?:\s*[AP]\.?M\.?)?$",  # 10:30, 10:30 PM
        r"^\d{1,2}\s*[AP]\.?M\.?$",  # 3 AM, 10 P.M.
    ]

    for pattern in time_patterns:
        if re.match(pattern, text.strip(), re.IGNORECASE):
            return True

    return False


def extract_trailing_time(text: str, locale_codes: list[str] | None = None):
    """
    Try to split a trailing time expression from a combined location+time string.

    For headings without a dash separator, e.g., "CAR DUSK" → ("CAR", "DUSK").

    Returns:
        (location_part, time_part) if a trailing time word is found,
        (None, None) otherwise.
    """
    if locale_codes:
        time_words = build_time_words(locale_codes)
    else:
        time_words = TIME_WORDS

    text_stripped = text.strip()
    words = text_stripped.split()
    if len(words) < 2:
        return None, None

    # Try progressively longer suffixes (from right) as time expressions
    # e.g., "SOME PLACE LATE NIGHT" → try "NIGHT", then "LATE NIGHT"
    # Strip trailing periods from candidates (FDX format: "LOCATION. NIGHT.")
    for n in range(min(3, len(words) - 1), 0, -1):
        candidate_time = " ".join(words[-n:]).lower().rstrip('.')
        if candidate_time in time_words:
            location_part = " ".join(words[:-n])
            time_part = " ".join(words[-n:]).rstrip('.')
            return location_part, time_part

    return None, None


def is_shot_type(text: str) -> bool:
    """Check if text contains a shot type."""
    shot_keywords = [
        "SHOT", "ANGLE", "CLOSE", "WIDE", "MEDIUM", "POV",
        "TRACKING", "PAN", "TILT", "ZOOM", "CRANE",
        "AERIAL", "INSERT", "ESTABLISHING",
    ]

    text_upper = text.upper()
    for keyword in shot_keywords:
        if keyword in text_upper:
            return True

    return False


__all__ = [
    # Character sets
    "CAPS", "LOWER", "DIGITS", "ALPHANUMS", "ALL_CHARS",

    # Basic tokens
    "WH", "HYPHEN", "OHYPHEN", "LP", "RP", "EOL",

    # Shot types
    "SHOT_TYPES", "ShotTypeEnum",

    # Transitions
    "TRANSITIONS", "TRANSITION_TYPES",

    # Location types
    "LOCATION_TYPE", "INT", "EXT", "INT_EXT",

    # Time expressions
    "TIME_WORDS", "ENUMERATED_TIME_WORD", "is_time_expression",
    "build_time_words",

    # Helper functions
    "is_shot_type",

    # Parsing helpers
    "CAPS_SEGMENT", "TITLE", "SPACES", "MIN_2_SPACES",
]
