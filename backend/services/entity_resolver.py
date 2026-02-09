"""
Entity Resolver — Phase 2: AI Prompt Optimization.

Merges the deterministic speaker list (from ScreenPy grammar parsing)
with AI-extracted character names (from scene enhancement). Produces a
single canonical character list per scene with source attribution.

Design (from SCREENPY_BRAINSTORM.md §3.7):
1. Exact match (case-insensitive): merge → speaker wins as canonical
2. Substring match: "DETECTIVE MARKS" contains "MARKS" → merge
3. Speaker always wins as canonical name form
4. Unmatched AI characters added as action-line-only entities

Usage:
    from services.entity_resolver import resolve_character_entities

    merged = resolve_character_entities(
        speakers={"JOHN": 3, "SARAH": 1, "DETECTIVE MARKS": 5},
        ai_characters=["John", "THE COPS", "Sarah", "A WAITRESS", "Marks"],
    )
"""

from typing import Dict, List, Optional


def resolve_character_entities(
    speakers: Dict[str, int],
    ai_characters: List[str],
) -> List[Dict]:
    """
    Merge speaker list (from ScreenPy) with AI-extracted characters.

    Args:
        speakers: Dict of canonical_speaker_name → dialogue_count.
                  These come from grammar-based dialogue extraction and
                  are high-confidence identities.
        ai_characters: List of character names returned by AI from
                       action-line analysis. May overlap with speakers
                       under different name forms.

    Returns:
        List of resolved character entities, each with:
        - canonical_name: The authoritative name (speaker form preferred)
        - source: 'dialogue' | 'action_line' | 'both'
        - dialogue_count: Number of dialogue blocks (0 for action-only)
        - aliases: Other name forms found for this entity
    """
    if not speakers and not ai_characters:
        return []

    entities: List[Dict] = []
    matched_ai_indices: set = set()

    # Normalize speaker names for matching
    speaker_names = list(speakers.keys())

    # Phase 1: Build entities from speakers, try to match AI characters
    for speaker_name in speaker_names:
        entity = {
            "canonical_name": speaker_name,
            "source": "dialogue",
            "dialogue_count": speakers[speaker_name],
            "aliases": [],
        }

        for idx, ai_char in enumerate(ai_characters):
            if idx in matched_ai_indices:
                continue

            if _names_match(speaker_name, ai_char):
                entity["aliases"].append(ai_char)
                entity["source"] = "both"
                matched_ai_indices.add(idx)

        entities.append(entity)

    # Phase 2: Add unmatched AI characters as action-line-only entities
    for idx, ai_char in enumerate(ai_characters):
        if idx in matched_ai_indices:
            continue

        # Normalize the AI character name
        canonical = ai_char.strip().upper()
        if not canonical:
            continue

        # Check for duplicates among already-added action-line entities
        if any(
            e["canonical_name"] == canonical
            for e in entities
            if e["source"] == "action_line"
        ):
            continue

        entities.append({
            "canonical_name": canonical,
            "source": "action_line",
            "dialogue_count": 0,
            "aliases": [ai_char] if ai_char != canonical else [],
        })

    return entities


def merge_to_character_list(
    speakers: Dict[str, int],
    ai_characters: List[str],
) -> List[str]:
    """
    Convenience wrapper: returns a flat UPPERCASE character list
    suitable for storing in scenes.characters JSONB.

    This is the primary integration point — call after AI enhancement
    to produce the final merged character list for the scene.
    """
    entities = resolve_character_entities(speakers, ai_characters)
    return [e["canonical_name"] for e in entities]


def _names_match(speaker: str, ai_char: str) -> bool:
    """
    Determine if a speaker name and an AI-extracted character name
    refer to the same entity.

    Rules:
    1. Exact match (case-insensitive)
    2. One name is a substring of the other (case-insensitive)
       - "DETECTIVE MARKS" contains "MARKS" → match
       - "SARAH" matches "Sarah" → match
    3. Last-name match: split both names, compare last tokens
       - "DETECTIVE MARKS" vs "Marks" → last token match

    Excludes very short tokens (≤2 chars) to avoid false positives
    like "AL" matching "ALICE".
    """
    s = speaker.upper().strip()
    a = ai_char.upper().strip()

    if not s or not a:
        return False

    # Rule 1: Exact match
    if s == a:
        return True

    # Rule 2: Substring containment (require min 3 chars to avoid false positives)
    if len(a) >= 3 and a in s:
        return True
    if len(s) >= 3 and s in a:
        return True

    # Rule 3: Last-token match
    s_tokens = s.split()
    a_tokens = a.split()
    if s_tokens and a_tokens:
        s_last = s_tokens[-1]
        a_last = a_tokens[-1]
        if len(s_last) >= 3 and len(a_last) >= 3 and s_last == a_last:
            return True

    return False
