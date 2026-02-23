"""
Shot heading parser for extracting structured information from shot headings.

Vendored from ScreenPy with the following changes:
- Relative imports instead of absolute screenpy.*
- Locale-aware time expression detection
"""

import re
from typing import Optional, List, Tuple

from ..models import ShotHeading, LocationType, ShotType
from .grammar import (
    LOCATION_TYPE, SHOT_TYPES, HYPHEN, WH, CAPS_SEGMENT,
    is_time_expression, is_shot_type, extract_trailing_time,
)


class ShotHeadingParser:
    """
    Parses shot headings according to screenplay grammar.

    Based on The Hollywood Standard:
    - Location type (INT/EXT)
    - Location hierarchy
    - Shot type
    - Subject
    - Time of day
    """

    def __init__(self, locale_codes: list[str] | None = None):
        self.locale_codes = locale_codes
        self._init_patterns()

        # Scene number prefix pattern: "1." or "14A." or FDX "1 " or revision "A1"
        self.scene_number_prefix = re.compile(r"^([A-Z]?\d+[A-Z]?)\.?\s+")

        # Structural prefixes that precede a real scene heading
        self.structural_prefix = re.compile(
            r"^(?:FLASHBACK|DREAM SEQUENCE|FANTASY|NIGHTMARE|VISION|HALLUCINATION)"
            r"\s*[-–—:]\s*",
            re.IGNORECASE,
        )

    def _init_patterns(self):
        """Initialize parsing patterns."""
        # Location type patterns
        self.int_pattern = re.compile(r"^INT\.?\s*", re.IGNORECASE)
        self.ext_pattern = re.compile(r"^EXT\.?\s*", re.IGNORECASE)
        self.int_ext_pattern = re.compile(r"^(INT\.?/EXT\.?|I/E)\s*", re.IGNORECASE)

        # Shot type keywords
        self.shot_keywords = {
            "CLOSE": ShotType.CLOSE,
            "CLOSEUP": ShotType.CLOSE,
            "CLOSE-UP": ShotType.CLOSE,
            "CU": ShotType.CLOSE,
            "EXTREME CLOSE": ShotType.EXTREME_CLOSE,
            "EXTREME CLOSEUP": ShotType.EXTREME_CLOSE,
            "TIGHT CLOSE": ShotType.EXTREME_CLOSE,
            "ECU": ShotType.EXTREME_CLOSE,
            "EXTREME WIDE": ShotType.EXTREME_WIDE,
            "EWS": ShotType.EXTREME_WIDE,
            "WIDE": ShotType.WIDE,
            "WIDE SHOT": ShotType.WIDE,
            "WS": ShotType.WIDE,
            "LONG SHOT": ShotType.LONG_SHOT,
            "LS": ShotType.LONG_SHOT,
            "FULL SHOT": ShotType.FULL_SHOT,
            "FS": ShotType.FULL_SHOT,
            "MEDIUM": ShotType.MEDIUM,
            "MED": ShotType.MEDIUM,
            "MS": ShotType.MEDIUM,
            "TWO SHOT": ShotType.TWO_SHOT,
            "2 SHOT": ShotType.TWO_SHOT,
            "THREE SHOT": ShotType.THREE_SHOT,
            "3 SHOT": ShotType.THREE_SHOT,
            "ESTABLISHING": ShotType.ESTABLISHING,
            "EST": ShotType.ESTABLISHING,
            "TRACKING": ShotType.TRACKING,
            "DOLLY": ShotType.TRACKING,
            "MOVING": ShotType.MOVING,
            "STEADICAM": ShotType.MOVING,
            "ANGLE": ShotType.ANGLE,
            "REVERSE": ShotType.REVERSE,
            "CRANE": ShotType.CRANE,
            "TILT": ShotType.TILT,
            "PAN": ShotType.PAN,
            "ZOOM": ShotType.ZOOM,
            "POV": ShotType.POV,
            "P.O.V.": ShotType.POV,
            "INSERT": ShotType.INSERT,
            "AERIAL": ShotType.AERIAL,
            "UNDERWATER": ShotType.UNDERWATER,
            "HANDHELD": ShotType.HANDHELD,
        }

        # Prepositions that can follow shot types
        self.shot_preps = {"ON", "OF", "TO", "TOWARDS", "FROM", "IN", "OVER", "ABOVE"}

    def parse(self, text: str, line_num: int = 0) -> Optional[ShotHeading]:
        """
        Parse a shot heading from text.

        Args:
            text: The heading text to parse
            line_num: Line number in the screenplay

        Returns:
            ShotHeading object or None if not a valid heading
        """
        original_text = text
        text = text.strip()

        if not text:
            return None

        # Strip leading scene number prefix (e.g., "1. EXT." → "EXT.")
        # Also handles FDX format without period: "1 INT." → "INT."
        scene_number = None
        sn_match = self.scene_number_prefix.match(text)
        if sn_match:
            # Only strip if what follows looks like a location type
            remainder = text[sn_match.end():]
            if any(remainder.upper().startswith(kw) for kw in ["INT", "EXT", "I/E", "E/I"]):
                scene_number = sn_match.group(1)
                text = remainder

        # Strip trailing mirrored scene number (FDX format: "INT. SHOP - DAY  42")
        if scene_number:
            text = re.sub(rf"\s+{re.escape(scene_number)}\s*$", "", text)

        # Strip structural prefix (e.g., "FLASHBACK - INT. SHOP" → "INT. SHOP")
        sp_match = self.structural_prefix.match(text)
        if sp_match:
            remainder = text[sp_match.end():]
            if any(remainder.upper().startswith(kw) for kw in ["INT", "EXT", "I/E", "E/I"]):
                text = remainder

        # Extract components
        location_type = self._extract_location_type(text)
        if location_type:
            text = self._remove_location_type(text, location_type)

        # Split by hyphens to extract components
        parts = self._split_heading(text)

        locations = []
        shot_type = None
        shot_modifier = None
        subject = None
        time_of_day = None

        # Process each part
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue

            # Check if it's a shot type
            detected_shot = self._detect_shot_type(part)
            if detected_shot and not shot_type:
                shot_type, shot_modifier, remainder = detected_shot
                if remainder:
                    subject = remainder
                continue

            # Check if it's purely a time expression (exact match)
            if self._is_time_expression(part):
                time_of_day = part
                continue

            # Check if part contains both location and time (no dash separator)
            # e.g., "CAR DUSK" → location="CAR", time="DUSK"
            # Also handles period separator: "Study. NIGHT" → location="Study", time="NIGHT"
            loc_part, time_part = extract_trailing_time(part, locale_codes=self.locale_codes)
            if loc_part and time_part:
                if location_type and not time_of_day:
                    locations.append(loc_part.rstrip('.').strip())
                    time_of_day = time_part
                continue

            # If we have location type, this might be a location
            if location_type and not shot_type and not time_of_day:
                locations.append(part)
            else:
                if not subject:
                    subject = part

        # Determine if this is a master heading
        is_master = location_type is not None

        # A heading must have at least one component
        if not any([location_type, locations, shot_type, subject, time_of_day]):
            return None

        return ShotHeading(
            location_type=location_type or LocationType.NONE,
            locations=locations,
            shot_type=shot_type,
            shot_modifier=shot_modifier,
            subject=subject,
            time_of_day=time_of_day,
            raw_text=original_text,
            start_pos=line_num,
            end_pos=line_num,
            is_master=is_master,
        )

    def _extract_location_type(self, text: str) -> Optional[LocationType]:
        """Extract location type (INT/EXT) from text."""
        if self.int_ext_pattern.match(text):
            return LocationType.INT_EXT
        elif self.int_pattern.match(text):
            return LocationType.INTERIOR
        elif self.ext_pattern.match(text):
            return LocationType.EXTERIOR
        return None

    def _remove_location_type(self, text: str, loc_type: LocationType) -> str:
        """Remove location type from text."""
        if loc_type == LocationType.INT_EXT:
            text = self.int_ext_pattern.sub("", text)
        elif loc_type == LocationType.INTERIOR:
            text = self.int_pattern.sub("", text)
        elif loc_type == LocationType.EXTERIOR:
            text = self.ext_pattern.sub("", text)
        return text.strip()

    def _split_heading(self, text: str) -> List[str]:
        """Split heading by hyphens while preserving certain patterns."""
        # Split by " - " or " – " or " — " but not by hyphens in words
        parts = re.split(r"\s+[-–—]\s+", text)
        return parts

    def _detect_shot_type(self, text: str) -> Optional[Tuple[ShotType, Optional[str], Optional[str]]]:
        """
        Detect shot type in text.

        Returns:
            Tuple of (shot_type, modifier, remainder) or None
        """
        text_upper = text.upper()

        for keyword, shot_type in self.shot_keywords.items():
            if keyword in text_upper:
                idx = text_upper.find(keyword)

                modifier = None
                modifier_match = re.search(r"\(([^)]+)\)", text[idx:])
                if modifier_match:
                    modifier = modifier_match.group(1)

                end_idx = idx + len(keyword)
                if modifier_match:
                    end_idx = idx + modifier_match.end()

                remainder = text[end_idx:].strip()

                for prep in self.shot_preps:
                    if remainder.upper().startswith(prep + " "):
                        remainder = remainder[len(prep):].strip()
                        break

                if remainder and remainder[0] in "-, ":
                    remainder = remainder[1:].strip()

                return shot_type, modifier, remainder if remainder else None

        return None

    def _is_time_expression(self, text: str) -> bool:
        """Check if text is a time expression (locale-aware)."""
        return is_time_expression(text, locale_codes=self.locale_codes)

    def _extract_parenthetical(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Extract parenthetical modifier from text.

        Returns:
            Tuple of (text_without_parenthetical, parenthetical_content)
        """
        match = re.search(r"\(([^)]+)\)", text)
        if match:
            modifier = match.group(1)
            text_clean = text[:match.start()] + text[match.end():]
            return text_clean.strip(), modifier
        return text, None
