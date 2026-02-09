"""
Tests for Entity Resolver — Phase 2: AI Prompt Optimization.

Validates the merge logic between ScreenPy speaker lists and
AI-extracted character names.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.entity_resolver import (
    resolve_character_entities,
    merge_to_character_list,
    _names_match,
)


# ============================================
# _names_match tests
# ============================================

def test_exact_match_case_insensitive():
    assert _names_match("JOHN", "John") is True
    assert _names_match("SARAH", "sarah") is True
    assert _names_match("DETECTIVE MARKS", "Detective Marks") is True


def test_substring_match():
    """Speaker contains AI char or vice versa."""
    assert _names_match("DETECTIVE MARKS", "MARKS") is True
    assert _names_match("MARKS", "DETECTIVE MARKS") is True


def test_last_token_match():
    """Last name matches across different title/role prefixes."""
    assert _names_match("DETECTIVE MARKS", "Marks") is True
    assert _names_match("DR WILLIAMS", "Williams") is True


def test_no_false_positive_short_names():
    """Short tokens (≤2 chars) should NOT trigger substring match."""
    assert _names_match("AL", "ALICE") is False
    assert _names_match("ED", "EDWARD") is False


def test_no_match_different_names():
    assert _names_match("JOHN", "SARAH") is False
    assert _names_match("THE COPS", "DETECTIVE MARKS") is False


def test_empty_names():
    assert _names_match("", "JOHN") is False
    assert _names_match("JOHN", "") is False
    assert _names_match("", "") is False


# ============================================
# resolve_character_entities tests
# ============================================

def test_basic_merge():
    """Speakers + overlapping AI characters merge correctly."""
    speakers = {"JOHN": 3, "SARAH": 1}
    ai_chars = ["John", "Sarah", "A WAITRESS"]

    entities = resolve_character_entities(speakers, ai_chars)

    names = {e["canonical_name"] for e in entities}
    assert "JOHN" in names
    assert "SARAH" in names
    assert "A WAITRESS" in names
    assert len(entities) == 3

    # JOHN should be "both" source
    john = next(e for e in entities if e["canonical_name"] == "JOHN")
    assert john["source"] == "both"
    assert john["dialogue_count"] == 3

    # A WAITRESS should be action_line only
    waitress = next(e for e in entities if e["canonical_name"] == "A WAITRESS")
    assert waitress["source"] == "action_line"
    assert waitress["dialogue_count"] == 0


def test_speaker_canonical_wins():
    """Speaker name form is preserved as canonical."""
    speakers = {"DETECTIVE MARKS": 5}
    ai_chars = ["Marks"]

    entities = resolve_character_entities(speakers, ai_chars)

    assert len(entities) == 1
    assert entities[0]["canonical_name"] == "DETECTIVE MARKS"
    assert entities[0]["source"] == "both"
    assert "Marks" in entities[0]["aliases"]


def test_no_speakers():
    """When no speakers, all AI characters become action_line entities."""
    speakers = {}
    ai_chars = ["JOHN", "SARAH"]

    entities = resolve_character_entities(speakers, ai_chars)

    assert len(entities) == 2
    assert all(e["source"] == "action_line" for e in entities)


def test_no_ai_characters():
    """When no AI characters, all speakers remain dialogue-only."""
    speakers = {"JOHN": 3, "SARAH": 1}
    ai_chars = []

    entities = resolve_character_entities(speakers, ai_chars)

    assert len(entities) == 2
    assert all(e["source"] == "dialogue" for e in entities)


def test_empty_both():
    assert resolve_character_entities({}, []) == []


def test_duplicate_ai_characters():
    """Duplicate AI characters should not create duplicate entities."""
    speakers = {}
    ai_chars = ["John", "JOHN", "john"]

    entities = resolve_character_entities(speakers, ai_chars)

    # All three normalize to "JOHN", so should be 1 entity
    assert len(entities) == 1
    assert entities[0]["canonical_name"] == "JOHN"


def test_complex_merge_scenario():
    """Real-world scenario: brainstorm §3.7 example."""
    speakers = {"DETECTIVE MARKS": 5, "SARAH": 2}
    ai_chars = ["Marks", "THE COPS", "Sarah", "A WAITRESS"]

    entities = resolve_character_entities(speakers, ai_chars)

    names = {e["canonical_name"] for e in entities}

    # DETECTIVE MARKS absorbs "Marks"
    assert "DETECTIVE MARKS" in names
    # SARAH absorbs "Sarah"
    assert "SARAH" in names
    # THE COPS and A WAITRESS are new
    assert "THE COPS" in names
    assert "A WAITRESS" in names

    assert len(entities) == 4

    marks = next(e for e in entities if e["canonical_name"] == "DETECTIVE MARKS")
    assert marks["source"] == "both"
    assert marks["dialogue_count"] == 5

    cops = next(e for e in entities if e["canonical_name"] == "THE COPS")
    assert cops["source"] == "action_line"
    assert cops["dialogue_count"] == 0


def test_multiple_aliases():
    """A speaker might match multiple AI names."""
    speakers = {"DETECTIVE MARKS": 5}
    ai_chars = ["Marks", "DETECTIVE MARKS", "Det. Marks"]

    entities = resolve_character_entities(speakers, ai_chars)

    assert len(entities) == 1
    marks = entities[0]
    assert marks["canonical_name"] == "DETECTIVE MARKS"
    # "DETECTIVE MARKS" exact match and "Marks" substring both matched
    assert len(marks["aliases"]) >= 1


# ============================================
# merge_to_character_list tests
# ============================================

def test_merge_to_flat_list():
    speakers = {"JOHN": 3, "SARAH": 1}
    ai_chars = ["John", "A WAITRESS"]

    result = merge_to_character_list(speakers, ai_chars)

    assert "JOHN" in result
    assert "SARAH" in result
    assert "A WAITRESS" in result
    assert len(result) == 3


def test_merge_preserves_speaker_order():
    """Speakers come first in the output list."""
    speakers = {"ALPHA": 1, "BRAVO": 2}
    ai_chars = ["CHARLIE"]

    result = merge_to_character_list(speakers, ai_chars)

    # Speakers should appear before action-line-only characters
    alpha_idx = result.index("ALPHA")
    charlie_idx = result.index("CHARLIE")
    assert alpha_idx < charlie_idx


def test_merge_empty():
    assert merge_to_character_list({}, []) == []


# ============================================
# Run tests
# ============================================

if __name__ == "__main__":
    test_funcs = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    passed = 0
    failed = 0

    for func in test_funcs:
        try:
            func()
            print(f"  ✓ {func.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {func.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {func.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{passed}/{passed + failed} tests passed")
    if failed:
        exit(1)
