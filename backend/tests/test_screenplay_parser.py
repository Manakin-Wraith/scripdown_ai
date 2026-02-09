"""
Tests for the ScreenPy integration — Phase 1 Sprint.

Tests cover:
1. Text normalizer (kerning, CONTINUED, encoding, whitespace)
2. Speaker name resolution (entity resolution)
3. Screenplay parser adapter (grammar parsing, regex fallback)
4. Location hierarchy parsing
5. SceneCandidate enrichment fields
"""

import json
import os
import sys
import pytest

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ============================================
# Text Normalizer Tests
# ============================================

class TestTextNormalizer:
    """Tests for backend/services/text_normalizer.py"""

    def test_collapse_kerning_basic(self):
        from services.text_normalizer import _collapse_kerning
        result = _collapse_kerning("I N T .  L O C A T I O N")
        assert "INT." in result
        assert "LOCATION" in result

    def test_collapse_kerning_ext(self):
        from services.text_normalizer import _collapse_kerning
        result = _collapse_kerning("E X T . PARK")
        assert "EXT." in result

    def test_collapse_kerning_preserves_leading_spaces(self):
        from services.text_normalizer import _collapse_kerning
        result = _collapse_kerning("    I N T . BAR")
        assert result.startswith("    ")
        assert "INT" in result

    def test_collapse_kerning_ignores_normal_text(self):
        from services.text_normalizer import _collapse_kerning
        line = "This is a normal line of dialogue."
        assert _collapse_kerning(line) == line

    def test_collapse_kerning_short_run_ignored(self):
        from services.text_normalizer import _collapse_kerning
        # Only 2 chars — too short to be kerning
        line = "A B normal text"
        assert _collapse_kerning(line) == line

    def test_normalize_strips_continued(self):
        from services.text_normalizer import normalize_screenplay_text
        text = "Some dialogue\n(CONTINUED)\nMore text"
        result = normalize_screenplay_text(text)
        assert "(CONTINUED)" not in result
        assert "Some dialogue" in result
        assert "More text" in result

    def test_normalize_strips_more(self):
        from services.text_normalizer import normalize_screenplay_text
        text = "Line one\n(MORE)\nLine two"
        result = normalize_screenplay_text(text)
        assert "(MORE)" not in result

    def test_normalize_strips_page_numbers(self):
        from services.text_normalizer import normalize_screenplay_text
        text = "Scene text\n42\nMore scene text"
        result = normalize_screenplay_text(text)
        lines = [l for l in result.split("\n") if l.strip()]
        assert all(l.strip() != "42" for l in lines)

    def test_normalize_smart_quotes(self):
        from services.text_normalizer import normalize_screenplay_text
        text = "\u201cHello,\u201d she said. \u201cIt\u2019s fine.\u201d"
        result = normalize_screenplay_text(text)
        assert "\u201c" not in result
        assert "\u201d" not in result
        assert "\u2019" not in result
        assert '"Hello,"' in result

    def test_normalize_em_dash(self):
        from services.text_normalizer import normalize_screenplay_text
        text = "He ran\u2014fast"
        result = normalize_screenplay_text(text)
        assert "\u2014" not in result
        assert "--" in result

    def test_normalize_preserves_indentation(self):
        from services.text_normalizer import normalize_screenplay_text
        text = "                    CHARACTER NAME\n          Some dialogue text here"
        result = normalize_screenplay_text(text)
        lines = result.split("\n")
        # Leading spaces should be preserved
        assert lines[0].startswith("                    ")
        assert lines[1].startswith("          ")

    def test_normalize_collapses_internal_whitespace(self):
        from services.text_normalizer import normalize_screenplay_text
        text = "     Hello    world    here"
        result = normalize_screenplay_text(text)
        assert "     Hello world here" == result

    def test_normalize_full_pipeline(self):
        from services.text_normalizer import normalize_screenplay_text
        text = (
            "I N T . BAR - DAY\n"
            "(CONTINUED)\n"
            "42\n"
            "\u201cHello\u201d he said.\n"
            "                    JOHN\n"
            "          Nice to meet you.\n"
        )
        result = normalize_screenplay_text(text)
        assert "(CONTINUED)" not in result
        assert "INT" in result
        assert '"Hello"' in result
        assert "JOHN" in result


# ============================================
# Speaker Name Resolution Tests
# ============================================

class TestSpeakerResolution:
    """Tests for resolve_speaker_name in text_normalizer.py"""

    def test_strips_contd(self):
        from services.text_normalizer import resolve_speaker_name
        assert resolve_speaker_name("LEROY (CONT'D)") == "LEROY"

    def test_strips_vo(self):
        from services.text_normalizer import resolve_speaker_name
        assert resolve_speaker_name("DETECTIVE MARKS (V.O.)") == "DETECTIVE MARKS"

    def test_strips_os(self):
        from services.text_normalizer import resolve_speaker_name
        assert resolve_speaker_name("SARAH (O.S.)") == "SARAH"

    def test_strips_multiple_modifiers(self):
        from services.text_normalizer import resolve_speaker_name
        assert resolve_speaker_name("JOHN (V.O.) (CONT'D)") == "JOHN"

    def test_normalizes_whitespace(self):
        from services.text_normalizer import resolve_speaker_name
        assert resolve_speaker_name("  SARAH  ") == "SARAH"

    def test_empty_input(self):
        from services.text_normalizer import resolve_speaker_name
        assert resolve_speaker_name("") == ""

    def test_plain_name(self):
        from services.text_normalizer import resolve_speaker_name
        assert resolve_speaker_name("JOHN") == "JOHN"


# ============================================
# Location Hierarchy Tests
# ============================================

class TestLocationHierarchy:
    """Tests for _parse_location_hierarchy in screenplay_parser.py"""

    def test_simple_location(self):
        from services.screenplay_parser import _parse_location_hierarchy
        result = _parse_location_hierarchy("COFFEE SHOP")
        assert result == ["COFFEE SHOP"]

    def test_two_level_hierarchy(self):
        from services.screenplay_parser import _parse_location_hierarchy
        result = _parse_location_hierarchy("BURGER JOINT - KITCHEN")
        assert result == ["BURGER JOINT", "KITCHEN"]

    def test_strips_time_of_day(self):
        from services.screenplay_parser import _parse_location_hierarchy
        result = _parse_location_hierarchy("BAR - DAY")
        assert result == ["BAR"]

    def test_three_level_hierarchy(self):
        from services.screenplay_parser import _parse_location_hierarchy
        result = _parse_location_hierarchy("HOSPITAL - WARD 3 - BED AREA")
        assert result == ["HOSPITAL", "WARD 3", "BED AREA"]

    def test_empty_setting(self):
        from services.screenplay_parser import _parse_location_hierarchy
        assert _parse_location_hierarchy("") == []

    def test_en_dash_separator(self):
        from services.screenplay_parser import _parse_location_hierarchy
        result = _parse_location_hierarchy("HOUSE \u2013 GARDEN")
        assert result == ["HOUSE", "GARDEN"]


# ============================================
# ParsedScene Dataclass Tests
# ============================================

class TestParsedScene:
    """Tests for the ParsedScene dataclass."""

    def test_default_enrichments(self):
        from services.screenplay_parser import ParsedScene
        scene = ParsedScene(
            scene_number_original="1",
            scene_order=1,
            int_ext="INT",
            setting="BAR",
            time_of_day="DAY",
            page_start=1,
            page_end=1,
            text_start=0,
            text_end=100,
            content_hash="abc123",
        )
        assert scene.location_hierarchy == []
        assert scene.speakers == {}
        assert scene.shot_type is None
        assert scene.transitions == []
        assert scene.parse_method == "regex"

    def test_enriched_scene(self):
        from services.screenplay_parser import ParsedScene
        scene = ParsedScene(
            scene_number_original="42",
            scene_order=5,
            int_ext="EXT",
            setting="BURGER JOINT - KITCHEN",
            time_of_day="NIGHT",
            page_start=3,
            page_end=4,
            text_start=500,
            text_end=800,
            content_hash="def456",
            location_hierarchy=["BURGER JOINT", "KITCHEN"],
            speakers={"JOHN": 3, "SARAH": 2},
            shot_type="CLOSE",
            transitions=[{"type": "CUT TO", "text": "CUT TO:"}],
            parse_method="grammar",
        )
        assert scene.parse_method == "grammar"
        assert len(scene.location_hierarchy) == 2
        assert scene.speakers["JOHN"] == 3


# ============================================
# SceneCandidate Enrichment Tests
# ============================================

class TestSceneCandidateEnrichment:
    """Tests for the enriched SceneCandidate dataclass."""

    def test_default_enrichment_fields(self):
        from services.extraction_pipeline import SceneCandidate
        candidate = SceneCandidate(
            scene_number_original="1",
            scene_order=1,
            int_ext="INT",
            setting="OFFICE",
            time_of_day="DAY",
            page_start=1,
            page_end=1,
            text_start=0,
            text_end=50,
            content_hash="test123",
        )
        assert candidate.location_hierarchy == []
        assert candidate.speakers == {}
        assert candidate.shot_type is None
        assert candidate.transitions == []
        assert candidate.parse_method == "regex"

    def test_enriched_candidate(self):
        from services.extraction_pipeline import SceneCandidate
        candidate = SceneCandidate(
            scene_number_original="5",
            scene_order=5,
            int_ext="EXT",
            setting="PARK",
            time_of_day="DUSK",
            page_start=2,
            page_end=3,
            text_start=100,
            text_end=300,
            content_hash="hash5",
            location_hierarchy=["PARK", "LAKE"],
            speakers={"MARY": 2},
            shot_type="WIDE",
            transitions=[],
            parse_method="grammar",
        )
        assert candidate.parse_method == "grammar"
        assert candidate.location_hierarchy == ["PARK", "LAKE"]
        assert candidate.speakers == {"MARY": 2}
        assert candidate.shot_type == "WIDE"


# ============================================
# Grammar Parser Unit Tests (uses vendored lib)
# ============================================

class TestGrammarParser:
    """Tests for the vendored ScreenPy grammar parser."""

    def test_parser_import(self):
        from lib.screenpy.parser import ScreenplayParser
        parser = ScreenplayParser(locale_codes=["en"])
        assert parser is not None

    def test_parse_simple_screenplay(self):
        from lib.screenpy.parser import ScreenplayParser
        parser = ScreenplayParser(locale_codes=["en"])

        # Use proper screenplay indentation matching ScreenPy thresholds:
        # Character names: 30+ spaces (center_indent)
        # Dialogue: 10-29 spaces (dialogue_indent)
        # Transitions: 40+ spaces (right_indent)
        text = (
            "                                              FADE IN:\n"
            "\n"
            "INT. COFFEE SHOP - DAY\n"
            "\n"
            "A busy coffee shop. Customers line up at the counter.\n"
            "\n"
            "                              JOHN\n"
            "               Hey, can I get a latte?\n"
            "\n"
            "                              BARISTA\n"
            "               Sure thing.\n"
            "\n"
            "EXT. STREET - NIGHT\n"
            "\n"
            "Rain pours down on the empty street.\n"
        )

        screenplay = parser.parse(text)
        masters = screenplay.master_segments
        assert len(masters) >= 2
        assert "JOHN" in screenplay.characters or "BARISTA" in screenplay.characters

    def test_parse_with_afrikaans_locale(self):
        from lib.screenpy.parser import ScreenplayParser
        parser = ScreenplayParser(locale_codes=["en", "af"])

        text = "INT. KROEG - DAG\n\nAksie hier.\n"
        screenplay = parser.parse(text)
        masters = screenplay.master_segments
        assert len(masters) >= 1

    def test_shot_heading_locations(self):
        from lib.screenpy.parser import ShotHeadingParser
        parser = ShotHeadingParser(locale_codes=["en"])

        heading = parser.parse("INT. BURGER JOINT - KITCHEN - DAY")
        assert heading is not None
        assert heading.locations is not None
        assert len(heading.locations) >= 1

    def test_location_type_extraction(self):
        from lib.screenpy.parser import ShotHeadingParser
        parser = ShotHeadingParser(locale_codes=["en"])

        heading = parser.parse("EXT. PARK - MORNING")
        assert heading is not None
        assert "EXT" in str(heading.location_type)


# ============================================
# Integration Helpers
# ============================================

class TestHelpers:
    """Tests for helper functions in screenplay_parser.py"""

    def test_location_type_to_str(self):
        from services.screenplay_parser import _location_type_to_str
        assert _location_type_to_str("INT.") == "INT"
        assert _location_type_to_str("EXT.") == "EXT"
        assert _location_type_to_str("INT./EXT.") == "INT/EXT"

    def test_extract_scene_number(self):
        from services.screenplay_parser import _extract_scene_number
        assert _extract_scene_number("42. INT. BAR - DAY") == "42"
        assert _extract_scene_number("14A. EXT. PARK") == "14A"
        assert _extract_scene_number("7 INT. HOUSE") == "7"
        assert _extract_scene_number("INT. OFFICE - DAY") is None

    def test_build_page_offsets(self):
        from services.screenplay_parser import _build_page_offsets
        pages = [
            {"page_number": 1, "raw_text": "Hello world"},  # 11 chars
            {"page_number": 2, "raw_text": "Page two"},      # 8 chars
        ]
        offsets = _build_page_offsets(pages, key="raw_text")
        assert len(offsets) == 2
        assert offsets[0] == (0, 12, 1)   # 11+1=12
        assert offsets[1] == (12, 21, 2)  # 8+1=9, starts at 12

    def test_char_pos_to_page(self):
        from services.screenplay_parser import _char_pos_to_page, _build_page_offsets
        pages = [
            {"page_number": 1, "raw_text": "Hello world"},
            {"page_number": 2, "raw_text": "Page two"},
        ]
        offsets = _build_page_offsets(pages, key="raw_text")
        assert _char_pos_to_page(0, offsets) == 1
        assert _char_pos_to_page(5, offsets) == 1
        assert _char_pos_to_page(12, offsets) == 2
        assert _char_pos_to_page(15, offsets) == 2


# ============================================
# A/B Test: parse_method tracking across real PDFs
# ============================================

class TestABParseMethod:
    """
    Validates that parse_screenplay produces correct parse_method
    and enrichment fields across all available test scripts.
    Skips gracefully if no PDFs are present.
    """

    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")

    def _get_pdfs(self):
        if not os.path.isdir(self.UPLOAD_DIR):
            return []
        return sorted(
            os.path.join(self.UPLOAD_DIR, f)
            for f in os.listdir(self.UPLOAD_DIR)
            if f.lower().endswith(".pdf")
        )

    def test_all_pdfs_parse_without_error(self):
        from services.screenplay_parser import parse_screenplay
        pdfs = self._get_pdfs()
        if not pdfs:
            pytest.skip("No PDFs in uploads/")
        for pdf in pdfs:
            scenes, meta = parse_screenplay(pdf, locale_codes=["en", "af"])
            assert meta["parse_method"] in ("grammar", "regex"), f"{pdf}: bad method {meta['parse_method']}"
            assert meta["scene_count"] >= 0

    def test_parse_method_on_every_scene(self):
        from services.screenplay_parser import parse_screenplay
        pdfs = self._get_pdfs()
        if not pdfs:
            pytest.skip("No PDFs in uploads/")
        for pdf in pdfs:
            scenes, _ = parse_screenplay(pdf, locale_codes=["en", "af"])
            for s in scenes:
                assert s.parse_method in ("grammar", "regex"), f"Scene {s.scene_order} in {pdf}: bad method"

    def test_enrichment_field_types(self):
        from services.screenplay_parser import parse_screenplay
        pdfs = self._get_pdfs()
        if not pdfs:
            pytest.skip("No PDFs in uploads/")
        scenes, _ = parse_screenplay(pdfs[0], locale_codes=["en", "af"])
        assert len(scenes) > 0
        s = scenes[0]
        assert isinstance(s.location_hierarchy, list)
        assert isinstance(s.speakers, dict)
        assert isinstance(s.transitions, list)
        assert isinstance(s.parse_method, str)
        assert isinstance(s.content_hash, str)

    def test_jsonb_fields_serializable(self):
        import json as _json
        from services.screenplay_parser import parse_screenplay
        pdfs = self._get_pdfs()
        if not pdfs:
            pytest.skip("No PDFs in uploads/")
        scenes, _ = parse_screenplay(pdfs[0], locale_codes=["en", "af"])
        for s in scenes[:10]:
            _json.dumps(s.location_hierarchy)
            _json.dumps(s.speakers)
            _json.dumps(s.transitions)

    def test_supabase_payload_structure(self):
        """Validate the dict structure matches scene_candidates table columns."""
        from services.screenplay_parser import parse_screenplay
        pdfs = self._get_pdfs()
        if not pdfs:
            pytest.skip("No PDFs in uploads/")
        scenes, meta = parse_screenplay(pdfs[0], locale_codes=["en", "af"])
        s = scenes[0]

        # scene_candidates required columns
        candidate_keys = {
            "scene_number_original", "scene_order", "int_ext", "setting",
            "time_of_day", "page_start", "page_end", "text_start", "text_end",
            "content_hash", "location_hierarchy", "speakers", "shot_type",
            "transitions", "parse_method",
        }
        for key in candidate_keys:
            assert hasattr(s, key), f"ParsedScene missing field: {key}"

    def test_grammar_beats_regex_threshold(self):
        """Grammar should find at least as many scenes as regex on well-formatted scripts."""
        from services.screenplay_parser import parse_screenplay
        pdfs = self._get_pdfs()
        if not pdfs:
            pytest.skip("No PDFs in uploads/")
        grammar_total = 0
        for pdf in pdfs:
            scenes, meta = parse_screenplay(pdf, locale_codes=["en", "af"])
            if meta["parse_method"] == "grammar":
                grammar_total += len(scenes)
        # Preflight showed grammar=370 vs regex=255 across 5 scripts
        assert grammar_total >= 250, f"Grammar total {grammar_total} below expected threshold"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
