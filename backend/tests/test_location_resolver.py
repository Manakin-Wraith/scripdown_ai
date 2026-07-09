"""
Tests for Location Resolver — base-place derivation and merge suggestions.
Mirrors test_entity_resolver.py.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.location_resolver import (
    normalize_place,
    derive_base_place,
    suggest_merges,
)


def test_normalize_strips_article_and_case():
    assert normalize_place("The Coffee Shop") == "COFFEE SHOP"
    assert normalize_place("  a   BARN ") == "BARN"
    assert normalize_place("AN OFFICE") == "OFFICE"


def test_normalize_empty():
    assert normalize_place("") == ""
    assert normalize_place(None) == ""


def test_normalize_strips_surrounding_punctuation():
    assert normalize_place("OFFICE.") == "OFFICE"
    assert normalize_place("  BAR, ") == "BAR"


def test_derive_from_screenpy_prefix_and_tod():
    # regex/grammar form: "INT. COFFEE SHOP - DAY"
    assert derive_base_place("INT. COFFEE SHOP - DAY") == "COFFEE SHOP"
    assert derive_base_place("EXT. THE COFFEE SHOP - NIGHT") == "COFFEE SHOP"


def test_derive_from_enhancer_rebuild_form():
    # scene_enhancer rebuild: "{setting} - {int_ext} - {time_of_day}"
    assert derive_base_place("COFFEE SHOP - INT - DAY") == "COFFEE SHOP"


def test_derive_prefers_location_hierarchy():
    assert derive_base_place(
        "INT. BURGER JOINT - KITCHEN - DAY",
        location_hierarchy=["BURGER JOINT", "KITCHEN"],
    ) == "BURGER JOINT"


def test_derive_hierarchy_json_string():
    # location_hierarchy may arrive as a JSON string from the DB
    assert derive_base_place(
        "INT. BARN - NIGHT",
        location_hierarchy='["BARN"]',
    ) == "BARN"


def test_derive_plain_name_no_prefix():
    assert derive_base_place("COFFEE SHOP") == "COFFEE SHOP"


def test_derive_empty_setting():
    assert derive_base_place("") == ""
    assert derive_base_place(None) == ""


def test_derive_does_not_strip_int_ext_inside_name():
    assert derive_base_place("INTERROGATION ROOM") == "INTERROGATION ROOM"
    assert derive_base_place("INT. INTERROGATION ROOM - DAY") == "INTERROGATION ROOM"
    assert derive_base_place("EXTERIOR COURTYARD - GARDEN") == "EXTERIOR COURTYARD"
    assert derive_base_place("INTERSTATE 5 - NIGHT") == "INTERSTATE 5"


def test_suggest_article_variant():
    groups = suggest_merges(["COFFEE SHOP", "THE COFFEE SHOP", "COFFEE SHOP"])
    assert len(groups) == 1
    g = groups[0]
    assert set(g["members"]) == {"COFFEE SHOP", "THE COFFEE SHOP"}
    assert g["canonical"] == "COFFEE SHOP"  # most frequent
    assert g["reason"] == "variant"


def test_suggest_typo():
    groups = suggest_merges(["COFFEE SHOP", "COFEE SHOP"])
    assert len(groups) == 1
    assert set(groups[0]["members"]) == {"COFFEE SHOP", "COFEE SHOP"}
    assert groups[0]["reason"] == "typo"


def test_suggest_canonical_tiebreak_shortest():
    # Equal counts -> shorter name wins as canonical
    groups = suggest_merges(["THE COFFEE SHOP", "COFFEE SHOP"])
    assert len(groups) == 1
    assert groups[0]["canonical"] == "COFFEE SHOP"
    assert groups[0]["reason"] == "variant"


def test_suggest_short_string_guard():
    # BAR vs CAR must NOT cluster (below MIN_FUZZY_LEN)
    groups = suggest_merges(["BAR", "CAR"])
    assert groups == []


def test_suggest_excludes_known_aliases():
    groups = suggest_merges(
        ["COFFEE SHOP", "COFEE SHOP"],
        existing_aliases={"COFEE SHOP": "COFFEE SHOP"},
    )
    assert groups == []


def test_suggest_distinct_places_not_grouped():
    groups = suggest_merges(["COFFEE SHOP", "POLICE STATION", "HOSPITAL"])
    assert groups == []
