"""
Text Normalizer for Screenplay PDF Extraction.

Cleans pdfplumber layout=True output for the ScreenPy grammar parser.
This is the critical layer between PDF extraction and grammar parsing.

IMPORTANT: Output is for the grammar parser ONLY, not for the regex
fallback path. The regex fallback operates on raw_text (unmodified
pdfplumber output) to avoid the Fallback Paradox described in
docs/SCREENPY_BRAINSTORM.md §3.5.

Normalizations applied:
1. Kerning collapse — detect spaced-out characters, collapse to words
2. CONTINUED marker removal — strip page-bottom (CONTINUED) artifacts
3. Page number removal — strip standalone page numbers
4. Encoding cleanup — smart quotes → ASCII, em-dashes → hyphens
5. Whitespace normalization — collapse redundant spaces while
   preserving leading indentation (critical for dialogue detection)
"""

import re
from typing import List


# Pre-compiled patterns
_KERNING_PATTERN = re.compile(r"^([A-Z])\s([A-Z])\s")
_CONTINUED_PATTERN = re.compile(
    r"^\s*\(?\s*CONTINUED\s*\)?\s*$", re.IGNORECASE
)
_MORE_PATTERN = re.compile(r"^\s*\(MORE\)\s*$", re.IGNORECASE)
_PAGE_NUMBER_PATTERN = re.compile(r"^\s*\d{1,3}\s*\.?\s*$")

# Smart quotes and typographic characters
_SMART_REPLACEMENTS = [
    ("\u2018", "'"),   # left single quote
    ("\u2019", "'"),   # right single quote
    ("\u201c", '"'),   # left double quote
    ("\u201d", '"'),   # right double quote
    ("\u2013", "-"),   # en-dash
    ("\u2014", "--"),  # em-dash
    ("\u2026", "..."), # ellipsis
    ("\u00a0", " "),   # non-breaking space
    ("\u200b", ""),    # zero-width space
    ("\ufeff", ""),    # BOM
]


def normalize_screenplay_text(raw_text: str) -> str:
    """
    Normalize PDF-extracted screenplay text for grammar parsing.

    Args:
        raw_text: Text from pdfplumber extract_text(layout=True)

    Returns:
        Normalized text suitable for ScreenPy grammar parser.
        Indentation is preserved; kerning, CONTINUED markers,
        page numbers, and encoding artifacts are cleaned.
    """
    lines = raw_text.split("\n")
    normalized: List[str] = []

    for line in lines:
        # 1. Fix kerning artifacts: "I N T ." → "INT."
        line = _collapse_kerning(line)

        # 2. Strip CONTINUED markers (page-bottom artifacts)
        if _CONTINUED_PATTERN.match(line):
            continue

        # 3. Strip (MORE) markers
        if _MORE_PATTERN.match(line):
            continue

        # 4. Strip standalone page numbers
        if _PAGE_NUMBER_PATTERN.match(line.strip()):
            continue

        # 5. Normalize smart quotes and typographic characters
        line = _normalize_encoding(line)

        # 6. Normalize whitespace (preserve leading indentation)
        line = _normalize_whitespace(line)

        normalized.append(line)

    return "\n".join(normalized)


def _collapse_kerning(line: str) -> str:
    """
    Collapse kerning artifacts where characters are space-separated.

    Detects patterns like "I N T ." or "E X T ." and collapses them.
    Uses regex to find runs of single non-space characters separated by
    single spaces (3+ characters in the run). Handles mixed uppercase
    and punctuation (e.g., "I N T ." → "INT.").
    """
    stripped = line.lstrip()
    leading = len(line) - len(stripped)

    if not stripped:
        return line

    # Quick check: does the line start with single-char-space pattern?
    if not _KERNING_PATTERN.match(stripped):
        return line

    # Find runs of "X Y Z" where each token is a single non-space char
    # separated by single spaces. Require 3+ tokens to qualify as kerning.
    def _collapse_match(m):
        tokens = m.group(0).split(" ")
        if len(tokens) >= 3 and all(len(t) == 1 for t in tokens):
            return "".join(tokens)
        return m.group(0)

    # Pattern: 3+ single non-space chars each separated by exactly one space
    # (\S) (\S) (\S)... — each \S must be length 1
    result = re.sub(
        r"(?<!\S)(\S(?:\s\S){2,})(?!\S)",
        _collapse_match,
        stripped,
    )

    return " " * leading + result


def _normalize_encoding(line: str) -> str:
    """Replace smart quotes, em-dashes, and other typographic characters."""
    for old, new in _SMART_REPLACEMENTS:
        line = line.replace(old, new)
    return line


def _normalize_whitespace(line: str) -> str:
    """
    Normalize internal whitespace while preserving leading indentation.

    Leading spaces are preserved exactly (critical for ScreenPy's
    indent-based dialogue detection). Internal runs of multiple spaces
    are collapsed to single spaces.
    """
    if not line.strip():
        return ""

    leading = len(line) - len(line.lstrip(" "))
    content = line.lstrip(" ")

    # Collapse internal multi-space runs to single space
    content = re.sub(r"  +", " ", content)

    return " " * leading + content


def resolve_speaker_name(raw_name: str) -> str:
    """
    Normalize a speaker name extracted from dialogue.

    Strips character modifiers like (CONT'D), (V.O.), (O.S.) etc.
    and normalizes whitespace.

    Examples:
        "LEROY (CONT'D)" → "LEROY"
        "DETECTIVE MARKS (V.O.)" → "DETECTIVE MARKS"
        "  SARAH  " → "SARAH"
    """
    # Remove parenthetical modifiers
    name = re.sub(r"\s*\([^)]*\)\s*", " ", raw_name)
    # Collapse whitespace and strip
    name = " ".join(name.split()).strip()
    return name
