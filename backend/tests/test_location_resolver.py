"""
Tests for Location Resolver — base-place derivation and merge suggestions.
Mirrors test_entity_resolver.py.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.location_resolver import (
    normalize_place,
    canonicalize_setting,
    derive_base_place,
    derive_sub_place,
    suggest_merges,
    rewrite_place_token,
    resolve_location,
)


def test_canonicalize_uppercases_and_trims():
    assert canonicalize_setting("villa") == "VILLA"
    assert canonicalize_setting("  Villa  ") == "VILLA"
    assert canonicalize_setting("viLLA") == "VILLA"


def test_canonicalize_collapses_internal_whitespace():
    assert canonicalize_setting("VILLA  -  next morning") == "VILLA - NEXT MORNING"
    assert canonicalize_setting("sphe & Jessie house, lounge   nighT") == \
        "SPHE & JESSIE HOUSE, LOUNGE NIGHT"


def test_canonicalize_straightens_curly_quotes():
    # Curly apostrophe (U+2019) and opening single quote (U+2018) -> straight.
    assert canonicalize_setting("tam’s room") == "TAM'S ROOM"
    assert canonicalize_setting("‘quote’") == "'QUOTE'"
    # Distinct spellings that only differed by quote style now match.
    assert canonicalize_setting("TAM'S ROOM") == canonicalize_setting("tam’s room")


def test_canonicalize_keeps_articles_and_internal_punctuation():
    # Unlike normalize_place, canonicalize is display-facing: keep articles,
    # keep internal/trailing punctuation, only kill casing/whitespace/quote noise.
    assert canonicalize_setting("the beach") == "THE BEACH"
    assert canonicalize_setting("Black.") == "BLACK."
    assert canonicalize_setting("beach, the boys") == "BEACH, THE BOYS"


def test_canonicalize_is_idempotent():
    for raw in ["villa", "  Tam’s   Room ", "Black.", "beach, the boys"]:
        once = canonicalize_setting(raw)
        assert canonicalize_setting(once) == once


def test_canonicalize_empty():
    assert canonicalize_setting("") == ""
    assert canonicalize_setting(None) == ""


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


def test_normalize_folds_curly_apostrophe_to_straight():
    # A curly apostrophe must normalize to the same key as a straight one, so a
    # location can't split into two lanes over a typographic quote. Mirrors
    # canonicalize_setting's curly-quote folding.
    assert normalize_place("TAM’S ROOM") == "TAM'S ROOM"
    assert normalize_place("TAM’S ROOM") == normalize_place("TAM'S ROOM")
    assert normalize_place("KABS‘ PAD") == "KABS' PAD"


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


def test_derive_base_splits_on_comma():
    # A comma marks a sub-area of a place — group by the base before the comma.
    assert derive_base_place("TK'S HOUSE, KITCHEN") == "TK'S HOUSE"
    assert derive_base_place("ABI'S HOUSE, BATHROOM") == "ABI'S HOUSE"
    assert derive_base_place("SPHE & JESSIE HOUSE, LOUNGE NIGHT") == "SPHE & JESSIE HOUSE"


def test_derive_base_keeps_hyphenated_names():
    # A dash WITHOUT surrounding spaces is part of the name, not a separator.
    assert derive_base_place("C-MAX PRISON, DAVEYTON") == "C-MAX PRISON"
    assert derive_base_place("C-MAX PRISON") == "C-MAX PRISON"


def test_derive_base_cleans_dirty_hierarchy_entry():
    # A single dirty hierarchy entry collapses to its base segment.
    assert derive_base_place("whatever", location_hierarchy=["TK'S HOUSE, KITCHEN"]) == "TK'S HOUSE"


def test_derive_sub_from_comma():
    assert derive_sub_place("TK'S HOUSE, KITCHEN") == "KITCHEN"
    assert derive_sub_place("C-MAX PRISON, DAVEYTON") == "DAVEYTON"
    assert derive_sub_place("whatever", location_hierarchy=["ABI'S HOUSE, BATHROOM"]) == "BATHROOM"


def test_period_slugline_base_and_sub():
    # "HOME. BEDROOM. DAY" -> base HOME, sub BEDROOM (period+space separates).
    assert derive_base_place("OPULENT SANDTON HOME. BEDROOM. DAY") == "OPULENT SANDTON HOME"
    assert derive_sub_place("OPULENT SANDTON HOME. BEDROOM. DAY") == "BEDROOM"


def test_period_slugline_trailing_period_time_dropped():
    # Real settings end with a trailing period ("GARDEN. DAY."); the time token
    # must still be recognized and dropped from the sub.
    assert derive_sub_place("HOMELESS SHELTER. GARDEN. DAY.") == "GARDEN"
    assert derive_sub_place("COURTROOM. DAY.") == ""
    assert derive_base_place("COURTROOM. DAY.") == "COURTROOM"


def test_period_split_protects_abbreviations():
    # A period after MR/MRS/ST/single-letter is part of the name, not a separator.
    assert derive_base_place("MRS. JONES' HOUSE, KITCHEN") == "MRS. JONES' HOUSE"
    assert derive_sub_place("MRS. JONES' HOUSE, KITCHEN") == "KITCHEN"
    assert derive_base_place("ST. JOHN'S CHURCH") == "ST. JOHN'S CHURCH"


def test_compound_time_words_dropped():
    assert derive_sub_place("INT. SHELTER. OFFICE. EARLY MORNING.") == "OFFICE"
    assert derive_sub_place("INT. HOME. LOUNGE. PRESENT DAY.") == "LOUNGE"


def test_digit_noise_dropped_from_sub():
    assert derive_sub_place("INT. HOME. KITCHEN. 2 7") == "KITCHEN"
    assert derive_sub_place("EXT. CITY STREETS. 3 A") == ""


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


def test_derive_sub_place_from_setting():
    assert derive_sub_place("INT. VILLA - BATHROOM - DAY") == "BATHROOM"


def test_derive_sub_place_multi_segment():
    assert derive_sub_place("INT. VILLA - POOL HOUSE - CHANGING ROOM - NIGHT") \
        == "POOL HOUSE - CHANGING ROOM"


def test_derive_sub_place_none_when_no_sub():
    assert derive_sub_place("EXT. BEACH - DAY") == ""


def test_derive_sub_place_prefers_hierarchy():
    assert derive_sub_place("INT. VILLA - DAY", location_hierarchy=["VILLA", "Bathroom"]) \
        == "BATHROOM"


def test_rewrite_place_token_preserves_rest():
    assert rewrite_place_token("INT. VILLA - BATHROOM - DAY", "VILLA", "SMITH RESIDENCE") \
        == "INT. SMITH RESIDENCE - BATHROOM - DAY"


def test_rewrite_place_token_first_occurrence_only():
    assert rewrite_place_token("INT. POOL - POOL DECK - DAY", "POOL", "SPA") \
        == "INT. SPA - POOL DECK - DAY"


def test_resolve_location_parent_alias():
    setting, canonical = resolve_location(
        "INT. VILLA - BATHROOM - DAY", "INT", "DAY", ["VILLA", "BATHROOM"],
        parent_alias_map={"VILLA": "SMITH RESIDENCE"},
    )
    assert setting == "INT. SMITH RESIDENCE - BATHROOM - DAY"
    assert canonical == "SMITH RESIDENCE"


def test_resolve_location_sub_alias_scoped_to_parent():
    # POOL under VILLA renames; POOL under HOTEL must NOT.
    sub_map = {("VILLA", "POOL"): "SWIMMING POOL"}
    s1, _ = resolve_location("EXT. VILLA - POOL - DAY", "EXT", "DAY", None, sub_alias_map=sub_map)
    s2, _ = resolve_location("EXT. HOTEL - POOL - DAY", "EXT", "DAY", None, sub_alias_map=sub_map)
    assert s1 == "EXT. VILLA - SWIMMING POOL - DAY"
    assert s2 == "EXT. HOTEL - POOL - DAY"


def test_resolve_location_no_maps_is_noop_canonical():
    setting, canonical = resolve_location("INT. VILLA - BATHROOM - DAY", "INT", "DAY", None)
    assert setting == "INT. VILLA - BATHROOM - DAY"
    assert canonical == "VILLA"


def test_resolve_location_parent_recurs_in_sub():
    # Base name repeating inside the sub-location must not be double-replaced.
    setting, canonical = resolve_location(
        "INT. POOL - POOL DECK - DAY", "INT", "DAY", None,
        parent_alias_map={"POOL": "SPA"},
    )
    assert setting == "INT. SPA - POOL DECK - DAY"
    assert canonical == "SPA"


def test_resolve_location_nest_sets_base_canonical_not_combined():
    # Nesting GARAGE / BACKROOM under VILLA: setting gets the parent prefixed,
    # but canonical is the parent BASE (VILLA), not "VILLA - GARAGE / BACKROOM".
    setting, canonical = resolve_location(
        "INT. GARAGE / BACKROOM - DAY", "INT", "DAY", None,
        parent_set_map={"GARAGE / BACKROOM": ("VILLA", "GARAGE / BACKROOM")},
    )
    assert setting == "INT. VILLA - GARAGE / BACKROOM - DAY"
    assert canonical == "VILLA"


def test_resolve_location_null_set_name_path_unchanged():
    # A plain parent alias (no set_name) still behaves exactly as before.
    setting, canonical = resolve_location(
        "INT. VILLA - BATHROOM - DAY", "INT", "DAY", None,
        parent_alias_map={"VILLA": "SMITH RESIDENCE"},
    )
    assert setting == "INT. SMITH RESIDENCE - BATHROOM - DAY"
    assert canonical == "SMITH RESIDENCE"
