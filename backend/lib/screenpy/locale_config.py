"""
Configuration-driven locale schema for screenplay parsing.

Instead of hard-coding TIME_OF_DAY and LOCATION_TYPES into the grammar,
this module provides a registry of locales that can be extended at runtime.
This allows ScripDown to support Afrikaans, French, Spanish, etc. without
reforking the parser library.

Usage:
    from lib.screenpy.locale_config import get_locale, register_locale

    # Get merged locale (English + Afrikaans)
    locale = get_locale(["en", "af"])
    locale.times_of_day  # {"DAY", "NIGHT", ..., "DAG", "NAG", ...}

    # Register a new locale
    register_locale("fr", ScreenplayLocale(
        code="fr",
        name="French",
        times_of_day={"JOUR", "NUIT", "MATIN", "SOIR", "AUBE", "CRÉPUSCULE"},
        ...
    ))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Set


@dataclass(frozen=True)
class ScreenplayLocale:
    """Immutable locale definition for screenplay element parsing."""

    code: str
    name: str

    # Time of day words (used in scene headers after the dash)
    times_of_day: FrozenSet[str] = field(default_factory=frozenset)

    # Relative time expressions (LATER, CONTINUOUS, etc.)
    relative_times: FrozenSet[str] = field(default_factory=frozenset)

    # Location type prefixes (INT., EXT., etc.)
    location_types: FrozenSet[str] = field(default_factory=frozenset)

    # Transition keywords (CUT TO:, FADE IN:, etc.)
    transitions: FrozenSet[str] = field(default_factory=frozenset)

    # Seasons
    seasons: FrozenSet[str] = field(default_factory=frozenset)

    # Weather/atmospheric (sometimes used as time indicators)
    weather_time: FrozenSet[str] = field(default_factory=frozenset)

    # Character modifiers (V.O., O.S., etc.)
    character_modifiers: FrozenSet[str] = field(default_factory=frozenset)

    # Continued markers
    continued_markers: FrozenSet[str] = field(default_factory=frozenset)


# ---------------------------------------------------------------------------
# Built-in locales
# ---------------------------------------------------------------------------

ENGLISH = ScreenplayLocale(
    code="en",
    name="English",
    times_of_day=frozenset({
        "DAY", "NIGHT", "MORNING", "AFTERNOON", "EVENING",
        "DAWN", "DUSK", "SUNRISE", "SUNSET", "TWILIGHT",
        "NOON", "MIDNIGHT", "MIDDAY", "LATE NIGHT",
        "DAYBREAK", "SUNUP", "SUNDOWN",
        "FIRST LIGHT", "BREAK OF DAY", "FORENOON",
    }),
    relative_times=frozenset({
        "LATER", "MOMENTS LATER", "SECONDS LATER",
        "MINUTES LATER", "HOURS LATER", "DAYS LATER",
        "WEEKS LATER", "MONTHS LATER", "YEARS LATER",
        "EARLIER", "BEFORE", "AFTER",
        "CONTINUOUS", "CONTINUOUS ACTION", "CONT'D",
        "SAME TIME", "SAME", "MEANWHILE",
        "SIMULTANEOUSLY", "PRESENT", "PAST", "FUTURE",
        "FLASHBACK", "FLASH BACK", "FLASHFORWARD", "FLASH FORWARD",
        "BACK TO PRESENT", "BACK TO PRESENT DAY",
        "MOMENT'S LATER",
    }),
    location_types=frozenset({
        "INT.", "EXT.", "INT./EXT.", "EXT./INT.", "INT/EXT", "I/E", "E/I",
        "INT", "EXT",
    }),
    transitions=frozenset({
        "CUT TO:", "FADE IN:", "FADE OUT.", "FADE TO BLACK.",
        "DISSOLVE TO:", "MATCH CUT TO:", "HARD CUT TO:",
        "WIPE TO:", "SMASH CUT TO:", "TIME CUT TO:",
        "JUMP CUT TO:", "FADE TO:",
    }),
    seasons=frozenset({
        "SPRING", "SUMMER", "FALL", "AUTUMN", "WINTER",
    }),
    weather_time=frozenset({
        "STORMY", "RAINY", "SNOWY", "FOGGY", "MISTY",
        "CLEAR", "CLOUDY", "OVERCAST",
    }),
    character_modifiers=frozenset({
        "V.O.", "O.S.", "O.C.", "CONT'D", "CONT", "CONT.", "OFF",
    }),
    continued_markers=frozenset({
        "(CONTINUED)", "(CONT'D)", "(MORE)",
    }),
)

AFRIKAANS = ScreenplayLocale(
    code="af",
    name="Afrikaans",
    times_of_day=frozenset({
        "DAG", "NAG", "OGGEND", "MIDDAG", "AAND",
        "SKEMER", "DAERAAD", "SONSOPKOMS", "SONSONDERGANG",
        "NAAMIDDAG", "MIDDERNAG", "LAAT NAG",
    }),
    relative_times=frozenset({
        "LATER", "OOMBLIKKE LATER", "AANEENLOPEND",
        "GELYKTYDIG", "HEDE", "VERLEDE", "TOEKOMS",
        "TERUGFLITS", "VOORUITFLITS",
    }),
    location_types=frozenset({
        "BIN.", "BUIT.", "BIN./BUIT.", "BIN", "BUIT",
        # Also accept English INT/EXT in Afrikaans scripts
        "INT.", "EXT.", "INT", "EXT",
    }),
    transitions=frozenset({
        "SNOEI NA:", "VERVAAG IN:", "VERVAAG UIT.",
        # Many SA scripts use English transitions even in Afrikaans
        "CUT TO:", "FADE IN:", "FADE OUT.",
    }),
    seasons=frozenset({
        "LENTE", "SOMER", "HERFS", "WINTER",
    }),
    weather_time=frozenset({
        "STORMRIG", "REËNERIG", "SNEEU", "MISTIG",
    }),
    character_modifiers=frozenset({
        "V.O.", "O.S.", "VERV.", "VERV",
        # SA scripts commonly use English modifiers
        "CONT'D", "CONT",
    }),
    continued_markers=frozenset({
        "(VERVOLG)", "(CONTINUED)", "(CONT'D)",
    }),
)

FRENCH = ScreenplayLocale(
    code="fr",
    name="French",
    times_of_day=frozenset({
        "JOUR", "NUIT", "MATIN", "APRÈS-MIDI", "SOIR",
        "AUBE", "CRÉPUSCULE", "MIDI", "MINUIT",
    }),
    relative_times=frozenset({
        "PLUS TARD", "QUELQUES INSTANTS PLUS TARD",
        "CONTINU", "EN MÊME TEMPS", "PRÉSENT", "PASSÉ", "FUTUR",
        "FLASH-BACK", "FLASH-FORWARD",
    }),
    location_types=frozenset({
        "INT.", "EXT.", "INT./EXT.", "INT", "EXT",
    }),
    transitions=frozenset({
        "COUPE À:", "FONDU AU NOIR.", "FONDU ENCHAÎNÉ:",
        "OUVERTURE EN FONDU:",
    }),
    seasons=frozenset({
        "PRINTEMPS", "ÉTÉ", "AUTOMNE", "HIVER",
    }),
    weather_time=frozenset(),
    character_modifiers=frozenset({
        "V.O.", "H.C.", "SUITE",
    }),
    continued_markers=frozenset({
        "(SUITE)", "(CONTINUED)",
    }),
)

SPANISH = ScreenplayLocale(
    code="es",
    name="Spanish",
    times_of_day=frozenset({
        "DÍA", "DIA", "NOCHE", "MAÑANA", "TARDE",
        "AMANECER", "ANOCHECER", "MEDIODÍA", "MEDIANOCHE",
        "ATARDECER", "MADRUGADA",
    }),
    relative_times=frozenset({
        "DESPUÉS", "MOMENTOS DESPUÉS", "CONTINUO",
        "SIMULTÁNEAMENTE", "PRESENTE", "PASADO", "FUTURO",
        "FLASHBACK",
    }),
    location_types=frozenset({
        "INT.", "EXT.", "INT./EXT.", "INT", "EXT",
    }),
    transitions=frozenset({
        "CORTE A:", "FUNDIDO A NEGRO.", "DISOLVENCIA A:",
        "FUNDIDO DE APERTURA:",
    }),
    seasons=frozenset({
        "PRIMAVERA", "VERANO", "OTOÑO", "INVIERNO",
    }),
    weather_time=frozenset(),
    character_modifiers=frozenset({
        "V.O.", "F.C.", "CONT.",
    }),
    continued_markers=frozenset({
        "(CONTINÚA)", "(CONTINUED)",
    }),
)


# ---------------------------------------------------------------------------
# Locale Registry
# ---------------------------------------------------------------------------

_REGISTRY: Dict[str, ScreenplayLocale] = {
    "en": ENGLISH,
    "af": AFRIKAANS,
    "fr": FRENCH,
    "es": SPANISH,
}


def register_locale(code: str, locale: ScreenplayLocale) -> None:
    """Register a new locale or override an existing one."""
    _REGISTRY[code] = locale


def get_locale(codes: list[str] | str | None = None) -> ScreenplayLocale:
    """
    Get a merged locale from one or more locale codes.

    Args:
        codes: Locale code(s). Defaults to ["en"].
               Pass ["en", "af"] to merge English + Afrikaans.

    Returns:
        A merged ScreenplayLocale with all sets unioned.
    """
    if codes is None:
        codes = ["en"]
    if isinstance(codes, str):
        codes = [codes]

    if len(codes) == 1 and codes[0] in _REGISTRY:
        return _REGISTRY[codes[0]]

    # Merge multiple locales
    merged_name = " + ".join(
        _REGISTRY[c].name for c in codes if c in _REGISTRY
    )

    merged = ScreenplayLocale(
        code="+".join(codes),
        name=merged_name or "Custom",
        times_of_day=frozenset().union(
            *(_REGISTRY[c].times_of_day for c in codes if c in _REGISTRY)
        ),
        relative_times=frozenset().union(
            *(_REGISTRY[c].relative_times for c in codes if c in _REGISTRY)
        ),
        location_types=frozenset().union(
            *(_REGISTRY[c].location_types for c in codes if c in _REGISTRY)
        ),
        transitions=frozenset().union(
            *(_REGISTRY[c].transitions for c in codes if c in _REGISTRY)
        ),
        seasons=frozenset().union(
            *(_REGISTRY[c].seasons for c in codes if c in _REGISTRY)
        ),
        weather_time=frozenset().union(
            *(_REGISTRY[c].weather_time for c in codes if c in _REGISTRY)
        ),
        character_modifiers=frozenset().union(
            *(_REGISTRY[c].character_modifiers for c in codes if c in _REGISTRY)
        ),
        continued_markers=frozenset().union(
            *(_REGISTRY[c].continued_markers for c in codes if c in _REGISTRY)
        ),
    )

    return merged


def list_locales() -> list[str]:
    """Return all registered locale codes."""
    return list(_REGISTRY.keys())
