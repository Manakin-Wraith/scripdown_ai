"""
Screenplay Parser Adapter — Phase 1 Sprint.

Wires the vendored ScreenPy grammar parser into ScripDown's extraction
pipeline. This is the bridge between:

    pdfplumber PDF extraction → ScreenPy grammar → SceneCandidate output

Architecture (Dual Text Paths):
    pdfplumber → raw_text ─────────────────────→ Regex Fallback
             └→ Text Normalizer → normalized → ScreenPy Grammar Parser

The adapter:
1. Extracts text from PDF via pdfplumber (layout=True for grammar path)
2. Normalizes text for grammar parsing
3. Runs ScreenPy grammar parser with locale auto-detection
4. Falls back to regex if grammar returns 0 master segments
5. Outputs enriched SceneCandidate-compatible dicts with:
   - location_hierarchy (list)
   - speakers (dict of name → count)
   - shot_type (str or None)
   - transitions (list of dicts)
   - parse_method ('grammar' or 'regex')

See docs/SCREENPY_BRAINSTORM.md §7 for full architecture diagram.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pdfplumber

from services.text_normalizer import normalize_screenplay_text, resolve_speaker_name

logger = logging.getLogger(__name__)


@dataclass
class ParsedScene:
    """A scene detected by the grammar or regex parser, enriched with
    ScreenPy-extracted metadata beyond what the legacy pipeline provides."""

    scene_number_original: str
    scene_order: int
    int_ext: str
    setting: str
    time_of_day: str
    page_start: int
    page_end: int
    text_start: int
    text_end: int
    content_hash: str

    # Scene content
    scene_text: str = ""

    # ScreenPy enrichments
    location_hierarchy: List[str] = field(default_factory=list)
    speakers: Dict[str, int] = field(default_factory=dict)
    shot_type: Optional[str] = None
    transitions: List[Dict] = field(default_factory=list)
    parse_method: str = "regex"


def extract_text_dual_path(file_path: str) -> Tuple[List[Dict], str, str]:
    """
    Extract text from PDF using pdfplumber with dual text paths.

    Returns:
        - pages: List of page dicts with page_number, raw_text, layout_text
        - raw_full_text: Concatenated raw text (for regex fallback)
        - layout_full_text: Concatenated layout text (for grammar parser)
    """
    pages = []
    raw_parts = []
    layout_parts = []

    t0 = time.time()

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            raw_text = page.extract_text() or ""
            layout_text = page.extract_text(layout=True) or ""

            pages.append({
                "page_number": page_num,
                "raw_text": raw_text,
                "layout_text": layout_text,
            })

            raw_parts.append(raw_text)
            layout_parts.append(layout_text)

    raw_full = "\n".join(raw_parts)
    layout_full = "\n".join(layout_parts)

    elapsed = time.time() - t0
    logger.info(
        f"[ScreenplayParser] Extracted {len(pages)} pages in {elapsed:.2f}s "
        f"(raw={len(raw_full):,} chars, layout={len(layout_full):,} chars)"
    )

    return pages, raw_full, layout_full


def parse_screenplay(
    file_path: str,
    locale_codes: Optional[List[str]] = None,
) -> Tuple[List[ParsedScene], Dict]:
    """
    Parse a screenplay PDF using grammar-first with regex fallback.

    This is the main entry point for Phase 1 integration.

    Args:
        file_path: Path to the PDF file.
        locale_codes: Locale code(s) for parsing. Defaults to ["en"].
                     Pass ["en", "af"] for English + Afrikaans scripts.

    Returns:
        - scenes: List of ParsedScene objects
        - metadata: Dict with parse stats (method, timings, counts)
    """
    if locale_codes is None:
        locale_codes = ["en"]

    # Step 1: Extract text (dual paths)
    pages, raw_full_text, layout_full_text = extract_text_dual_path(file_path)

    # Step 2: Normalize layout text for grammar parser
    normalized_text = normalize_screenplay_text(layout_full_text)

    # Step 3: Try grammar parser first
    t0 = time.time()
    grammar_scenes, grammar_meta = _parse_with_grammar(
        normalized_text, pages, locale_codes
    )
    grammar_time = time.time() - t0

    # Step 4: If grammar found scenes, use them
    if grammar_scenes:
        logger.info(
            f"[ScreenplayParser] Grammar parser found {len(grammar_scenes)} scenes "
            f"in {grammar_time:.2f}s"
        )
        return grammar_scenes, {
            "parse_method": "grammar",
            "scene_count": len(grammar_scenes),
            "grammar_time_seconds": round(grammar_time, 2),
            "locale_codes": locale_codes,
            "total_pages": len(pages),
            "speaker_count": grammar_meta.get("speaker_count", 0),
            "transition_count": grammar_meta.get("transition_count", 0),
        }

    # Step 5: Fallback to regex on raw_text (NOT normalized)
    logger.warning(
        "[ScreenplayParser] Grammar returned 0 master segments, "
        "falling back to regex on raw_text"
    )
    t0 = time.time()
    regex_scenes = _parse_with_regex(raw_full_text, pages)
    regex_time = time.time() - t0

    logger.info(
        f"[ScreenplayParser] Regex fallback found {len(regex_scenes)} scenes "
        f"in {regex_time:.2f}s"
    )

    return regex_scenes, {
        "parse_method": "regex",
        "scene_count": len(regex_scenes),
        "grammar_time_seconds": round(grammar_time, 2),
        "regex_time_seconds": round(regex_time, 2),
        "locale_codes": locale_codes,
        "total_pages": len(pages),
        "grammar_failed_reason": "0 master segments",
    }


def _parse_with_grammar(
    normalized_text: str,
    pages: List[Dict],
    locale_codes: List[str],
) -> Tuple[List[ParsedScene], Dict]:
    """
    Run the vendored ScreenPy grammar parser on normalized text.

    Returns (scenes, metadata_dict). If the parser finds 0 master
    segments, returns ([], {}) to trigger regex fallback.
    """
    from lib.screenpy.parser import ScreenplayParser

    parser = ScreenplayParser(locale_codes=locale_codes)
    screenplay = parser.parse(normalized_text)

    # Get master segments only (Option A: 1 master header = 1 strip)
    master_segments = screenplay.master_segments
    if not master_segments:
        return [], {}

    # Build page offset map for position → page lookup
    page_offsets = _build_page_offsets(pages, key="layout_text")

    # Collect all transitions from the screenplay
    all_transitions = [
        {"type": t.type, "text": t.text}
        for t in screenplay.transitions
    ]

    # Collect speakers with resolved names
    resolved_speakers: Dict[str, int] = {}
    for raw_name, count in screenplay.characters.items():
        canonical = resolve_speaker_name(raw_name)
        if canonical:
            resolved_speakers[canonical] = (
                resolved_speakers.get(canonical, 0) + count
            )

    # Build ParsedScene for each master segment
    scenes: List[ParsedScene] = []

    for i, segment in enumerate(master_segments):
        heading = segment.heading
        if not heading:
            continue

        # Map location_type to INT/EXT string
        int_ext = _location_type_to_str(heading.location_type)

        # Location hierarchy from grammar
        location_hierarchy = heading.locations or []
        setting = " - ".join(location_hierarchy) if location_hierarchy else ""

        # Time of day
        time_of_day = heading.time_of_day or "DAY"

        # Shot type
        shot_type = heading.shot_type if heading.shot_type else None

        # Extract scene number from raw heading text
        scene_number = _extract_scene_number(heading.raw_text) or str(i + 1)

        # Text boundaries (line-based positions from the parser)
        text_start = segment.start_pos
        # Find end: next master segment start or end of text
        if i + 1 < len(master_segments):
            text_end = master_segments[i + 1].start_pos
        else:
            text_end = len(normalized_text)

        # Convert line positions to character positions for compatibility
        lines = normalized_text.split("\n")
        char_start = sum(len(lines[j]) + 1 for j in range(min(text_start, len(lines))))
        if i + 1 < len(master_segments):
            char_end = sum(
                len(lines[j]) + 1
                for j in range(min(text_end, len(lines)))
            )
        else:
            char_end = len(normalized_text)

        # Page range
        page_start = _char_pos_to_page(char_start, page_offsets)
        page_end = _char_pos_to_page(max(char_end - 1, char_start), page_offsets)

        # Content hash
        scene_text = normalized_text[char_start:char_end]
        from services.extraction_pipeline import compute_content_hash
        content_hash = compute_content_hash(scene_text)

        # Collect speakers for THIS scene (segments between this master
        # and the next master)
        scene_speakers = _collect_scene_speakers(
            screenplay.segments, segment.id,
            master_segments[i + 1].id if i + 1 < len(master_segments) else None,
        )

        # Collect transitions for this scene
        scene_transitions = _collect_scene_transitions(
            screenplay.segments, segment.id,
            master_segments[i + 1].id if i + 1 < len(master_segments) else None,
        )

        scenes.append(ParsedScene(
            scene_number_original=scene_number,
            scene_order=i + 1,
            int_ext=int_ext,
            setting=setting,
            time_of_day=time_of_day.upper(),
            page_start=page_start,
            page_end=page_end,
            text_start=char_start,
            text_end=char_end,
            content_hash=content_hash,
            scene_text=scene_text,
            location_hierarchy=location_hierarchy,
            speakers=scene_speakers,
            shot_type=shot_type,
            transitions=scene_transitions,
            parse_method="grammar",
        ))

    return scenes, {
        "speaker_count": len(resolved_speakers),
        "transition_count": len(all_transitions),
        "total_segments": len(screenplay.segments),
        "master_segments": len(master_segments),
    }


def _parse_with_regex(
    raw_text: str,
    pages: List[Dict],
) -> List[ParsedScene]:
    """
    Regex fallback — operates on raw_text (NOT normalized).

    Uses the existing detect_scene_headers + assign_scene_numbers logic
    from extraction_pipeline.py, then wraps results in ParsedScene with
    empty ScreenPy enrichment fields.
    """
    from services.extraction_pipeline import (
        detect_scene_headers,
        assign_scene_numbers,
        compute_content_hash,
    )

    # Build page offsets using raw_text
    page_offsets = _build_page_offsets(pages, key="raw_text")

    # Detect headers on full raw text
    all_headers = detect_scene_headers(raw_text)
    all_headers = assign_scene_numbers(all_headers)

    scenes: List[ParsedScene] = []

    for i, header in enumerate(all_headers):
        text_start = header["position"]
        if i + 1 < len(all_headers):
            text_end = all_headers[i + 1]["position"]
        else:
            text_end = len(raw_text)

        scene_text = raw_text[text_start:text_end]
        page_start = _char_pos_to_page(text_start, page_offsets)
        page_end = _char_pos_to_page(max(text_end - 1, text_start), page_offsets)

        # Parse location hierarchy from setting (simple dash-split)
        setting = header.get("setting", "")
        location_hierarchy = _parse_location_hierarchy(setting)

        scenes.append(ParsedScene(
            scene_number_original=header.get("scene_number", str(i + 1)),
            scene_order=i + 1,
            int_ext=header.get("int_ext", "INT"),
            setting=setting,
            time_of_day=header.get("time_of_day", "DAY"),
            page_start=page_start,
            page_end=page_end,
            text_start=text_start,
            text_end=text_end,
            content_hash=compute_content_hash(scene_text),
            scene_text=scene_text,
            location_hierarchy=location_hierarchy,
            speakers={},
            shot_type=None,
            transitions=[],
            parse_method="regex",
        ))

    return scenes


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _build_page_offsets(pages: List[Dict], key: str = "raw_text") -> List[Tuple[int, int, int]]:
    """
    Build a sorted list of (char_offset, char_end, page_number) tuples
    for mapping character positions to page numbers.
    """
    offsets = []
    current = 0
    for page in pages:
        text = page.get(key, "")
        page_len = len(text) + 1  # +1 for the join newline
        offsets.append((current, current + page_len, page["page_number"]))
        current += page_len
    return offsets


def _char_pos_to_page(char_pos: int, page_offsets: List[Tuple[int, int, int]]) -> int:
    """Map a character position to its page number."""
    for start, end, page_num in page_offsets:
        if start <= char_pos < end:
            return page_num
    # Default to last page
    return page_offsets[-1][2] if page_offsets else 1


def _location_type_to_str(location_type) -> str:
    """Convert LocationType enum to the standard string form."""
    mapping = {
        "INT.": "INT",
        "EXT.": "EXT",
        "INT./EXT.": "INT/EXT",
        "": "INT",
    }
    val = location_type if isinstance(location_type, str) else str(location_type)
    return mapping.get(val, val.replace(".", ""))


def _extract_scene_number(heading_text: str) -> Optional[str]:
    """Extract scene number from a heading line (e.g., '42. INT. BAR')."""
    match = re.match(r"^\s*(\d+[A-Z]?)\.\s", heading_text)
    if match:
        return match.group(1)

    # Also try without period: "42 INT."
    match = re.match(r"^\s*(\d+[A-Z]?)\s+(?:INT|EXT)", heading_text)
    if match:
        return match.group(1)

    return None


def _collect_scene_speakers(
    segments,
    master_id: int,
    next_master_id: Optional[int],
) -> Dict[str, int]:
    """
    Collect unique speakers from dialogue segments belonging to a
    specific master scene.
    """
    speakers: Dict[str, int] = {}

    for seg in segments:
        # Only look at segments within this master scene range
        if seg.id <= master_id:
            continue
        if next_master_id is not None and seg.id >= next_master_id:
            break

        if seg.dialogue and seg.dialogue.character:
            raw_name = seg.dialogue.character.name
            canonical = resolve_speaker_name(raw_name)
            if canonical:
                speakers[canonical] = speakers.get(canonical, 0) + 1

    return speakers


def _collect_scene_transitions(
    segments,
    master_id: int,
    next_master_id: Optional[int],
) -> List[Dict]:
    """Collect transitions from segments belonging to a specific master scene."""
    transitions = []

    for seg in segments:
        if seg.id <= master_id:
            continue
        if next_master_id is not None and seg.id >= next_master_id:
            break

        if seg.transition:
            transitions.append({
                "type": seg.transition.type,
                "text": seg.transition.text,
            })

    return transitions


def _parse_location_hierarchy(setting: str) -> List[str]:
    """
    Parse a flat setting string into a location hierarchy.

    Example: "BURGER JOINT - KITCHEN" → ["BURGER JOINT", "KITCHEN"]
    """
    if not setting:
        return []

    time_words = {
        "DAY", "NIGHT", "DUSK", "DAWN", "MORNING", "EVENING",
        "AFTERNOON", "CONTINUOUS", "LATER", "SAME",
    }

    parts = [p.strip() for p in re.split(r"\s*[-–—]\s*", setting) if p.strip()]
    locations = [p for p in parts if p.upper() not in time_words]

    return locations
