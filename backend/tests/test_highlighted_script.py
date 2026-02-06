"""
Tests for Highlighted Script PDF Service

Validates:
- Line classification (scene heading, character cue, dialogue, etc.)
- HTML generation with highlights
- Overlap removal
- Legend and stats building
- Class filtering
- Screenplay body structure
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.highlighted_script_service import (
    _remove_overlaps,
    _classify_line,
    _build_screenplay_body,
    _highlight_line,
    _build_highlighted_html,
    _build_legend,
    _build_stats,
    _build_cover_page,
    _generate_class_css,
    HIGHLIGHT_COLORS
)


SAMPLE_TEXT = """INT. COFFEE SHOP - DAY

JANE WILLIAMS (30s, exhausted) sits at a corner table, clutching a worn briefcase.

JANE
(nervously)
You wanted to see me?

A WAITER brings over two espressos on a silver tray."""

SAMPLE_EXTRACTIONS = [
    {
        'extraction_class': 'scene_header',
        'extraction_text': 'INT. COFFEE SHOP - DAY',
        'text_start': 0,
        'text_end': 22,
        'attributes': {'int_ext': 'INT', 'setting': 'COFFEE SHOP', 'time_of_day': 'DAY'},
        'confidence': 1.0
    },
    {
        'extraction_class': 'character',
        'extraction_text': 'JANE WILLIAMS (30s, exhausted)',
        'text_start': 24,
        'text_end': 53,
        'attributes': {'name': 'JANE WILLIAMS', 'emotional_state': 'exhausted'},
        'confidence': 0.95
    },
    {
        'extraction_class': 'prop',
        'extraction_text': 'worn briefcase',
        'text_start': 80,
        'text_end': 94,
        'attributes': {'item_name': 'briefcase', 'condition': 'worn'},
        'confidence': 0.9
    },
    {
        'extraction_class': 'dialogue',
        'extraction_text': 'You wanted to see me?',
        'text_start': 110,
        'text_end': 131,
        'attributes': {'character': 'JANE', 'tone': 'nervous'},
        'confidence': 1.0
    },
    {
        'extraction_class': 'prop',
        'extraction_text': 'silver tray',
        'text_start': 175,
        'text_end': 186,
        'attributes': {'item_name': 'tray', 'condition': 'silver'},
        'confidence': 0.85
    }
]


class TestOverlapRemoval(unittest.TestCase):
    """Test the _remove_overlaps function."""

    def test_no_overlaps(self):
        """Non-overlapping extractions should all be kept."""
        result = _remove_overlaps(SAMPLE_EXTRACTIONS)
        self.assertEqual(len(result), len(SAMPLE_EXTRACTIONS))

    def test_overlapping_extractions_first_wins(self):
        """Overlapping spans should keep the first one."""
        overlapping = [
            {'extraction_class': 'character', 'text_start': 0, 'text_end': 20, 'attributes': {}},
            {'extraction_class': 'prop', 'text_start': 10, 'text_end': 30, 'attributes': {}},
            {'extraction_class': 'dialogue', 'text_start': 30, 'text_end': 50, 'attributes': {}},
        ]
        result = _remove_overlaps(overlapping)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['extraction_class'], 'character')
        self.assertEqual(result[1]['extraction_class'], 'dialogue')

    def test_empty_list(self):
        """Empty list should return empty."""
        result = _remove_overlaps([])
        self.assertEqual(result, [])

    def test_invalid_positions_skipped(self):
        """Extractions with None or invalid positions should be skipped."""
        invalid = [
            {'extraction_class': 'x', 'text_start': None, 'text_end': 10, 'attributes': {}},
            {'extraction_class': 'y', 'text_start': 5, 'text_end': 3, 'attributes': {}},
            {'extraction_class': 'z', 'text_start': 0, 'text_end': 10, 'attributes': {}},
        ]
        result = _remove_overlaps(invalid)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['extraction_class'], 'z')


class TestLineClassification(unittest.TestCase):
    """Test the _classify_line function for screenplay element detection."""

    def test_scene_heading_int(self):
        self.assertEqual(_classify_line('INT. COFFEE SHOP - DAY', 'blank'), 'scene_heading')

    def test_scene_heading_ext(self):
        self.assertEqual(_classify_line('EXT. PARK - NIGHT', 'blank'), 'scene_heading')

    def test_scene_heading_int_ext(self):
        self.assertEqual(_classify_line('INT/EXT. CAR - MOVING - DAY', 'blank'), 'scene_heading')

    def test_character_cue_simple(self):
        self.assertEqual(_classify_line('JANE', 'action'), 'character_cue')

    def test_character_cue_with_contd(self):
        self.assertEqual(_classify_line("JACQUES (CONT'D)", 'action'), 'character_cue')

    def test_character_cue_with_vo(self):
        self.assertEqual(_classify_line('NARRATOR (V.O.)', 'action'), 'character_cue')

    def test_character_cue_with_os(self):
        self.assertEqual(_classify_line('JANE (O.S.)', 'action'), 'character_cue')

    def test_dialogue_after_cue(self):
        self.assertEqual(_classify_line('You wanted to see me?', 'character_cue'), 'dialogue')

    def test_dialogue_continues(self):
        self.assertEqual(_classify_line('I was waiting here.', 'dialogue'), 'dialogue')

    def test_parenthetical(self):
        self.assertEqual(_classify_line('(nervously)', 'character_cue'), 'parenthetical')

    def test_parenthetical_in_dialogue(self):
        self.assertEqual(_classify_line('(beat)', 'dialogue'), 'parenthetical')

    def test_dialogue_after_parenthetical(self):
        self.assertEqual(_classify_line('Fine. Whatever.', 'parenthetical'), 'dialogue')

    def test_transition_cut_to(self):
        self.assertEqual(_classify_line('CUT TO:', 'action'), 'transition')

    def test_transition_fade_out(self):
        self.assertEqual(_classify_line('FADE OUT.', 'action'), 'transition')

    def test_transition_smash_cut(self):
        self.assertEqual(_classify_line('SMASH CUT TO:', 'action'), 'transition')

    def test_action_line(self):
        self.assertEqual(
            _classify_line('Jane walks into the room and sits down.', 'blank'),
            'action'
        )

    def test_blank_line(self):
        self.assertEqual(_classify_line('', 'action'), 'blank')
        self.assertEqual(_classify_line('   ', 'action'), 'blank')

    def test_action_not_misclassified_as_cue(self):
        """Long uppercase lines should not be classified as character cues."""
        self.assertEqual(
            _classify_line('JANE WILLIAMS (30s, exhausted) sits at a corner table.', 'blank'),
            'action'
        )


class TestHighlightLine(unittest.TestCase):
    """Test the _highlight_line function."""

    def test_basic_highlighting(self):
        """Highlights should produce span tags with correct classes."""
        line = "Hello World Test"
        extractions = [
            {
                'extraction_class': 'character',
                'extraction_text': 'World',
                'text_start': 6,
                'text_end': 11,
                'attributes': {'name': 'World'}
            }
        ]
        result = _highlight_line(line, 0, extractions)
        self.assertIn('class="hl hl-character"', result)
        self.assertIn('World', result)
        self.assertIn('Hello', result)
        self.assertIn('Test', result)

    def test_no_extractions(self):
        """No extractions should return escaped plain text."""
        line = "<script>alert('xss')</script>"
        result = _highlight_line(line, 0, [])
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)

    def test_html_escaping_in_highlight(self):
        """Special characters should be escaped in highlight text."""
        line = 'She said "hello" & left'
        extractions = [
            {
                'extraction_class': 'dialogue',
                'extraction_text': '"hello"',
                'text_start': 9,
                'text_end': 16,
                'attributes': {}
            }
        ]
        result = _highlight_line(line, 0, extractions)
        self.assertIn('&amp;', result)
        self.assertIn('&quot;hello&quot;', result)

    def test_cross_line_extraction_clamps(self):
        """Extractions spanning multiple lines should clamp to line boundaries."""
        line = "middle part"
        extractions = [
            {
                'extraction_class': 'dialogue',
                'extraction_text': 'bigger span',
                'text_start': 0,
                'text_end': 50,
                'attributes': {}
            }
        ]
        result = _highlight_line(line, 10, extractions)
        self.assertIn('hl-dialogue', result)
        self.assertIn('middle part', result)


class TestScreenplayBody(unittest.TestCase):
    """Test the _build_screenplay_body function produces proper structure."""

    def test_scene_heading_gets_css_class(self):
        """Scene headings should get sp-scene-heading class."""
        text = "INT. COFFEE SHOP - DAY\n\nAction here."
        result = _build_screenplay_body(text, [], None)
        self.assertIn('sp-scene-heading', result)

    def test_character_cue_gets_css_class(self):
        """Character cues should get sp-character-cue class."""
        text = "INT. ROOM - DAY\n\nAction.\n\nJANE\nHello there."
        result = _build_screenplay_body(text, [], None)
        self.assertIn('sp-character-cue', result)

    def test_dialogue_gets_css_class(self):
        """Dialogue lines should get sp-dialogue class."""
        text = "JANE\nHello there."
        result = _build_screenplay_body(text, [], None)
        self.assertIn('sp-dialogue', result)

    def test_parenthetical_gets_css_class(self):
        """Parentheticals should get sp-parenthetical class."""
        text = "JANE\n(nervously)\nHello there."
        result = _build_screenplay_body(text, [], None)
        self.assertIn('sp-parenthetical', result)

    def test_blank_lines_produce_spacing(self):
        """Blank lines should produce sp-blank divs."""
        text = "Line one.\n\nLine two."
        result = _build_screenplay_body(text, [], None)
        self.assertIn('sp-blank', result)

    def test_page_breaks_not_escaped(self):
        """Page break divs should appear as HTML, not escaped text."""
        text = "Line one.\nLine two."
        boundaries = [10]  # break before "Line two."
        result = _build_screenplay_body(text, [], boundaries)
        self.assertIn('<div class="page-break"></div>', result)
        self.assertNotIn('&lt;div', result)

    def test_highlights_within_lines(self):
        """Extractions should produce highlight spans within line divs."""
        text = "JANE\nHello there."
        extractions = [
            {
                'extraction_class': 'dialogue',
                'extraction_text': 'Hello there.',
                'text_start': 5,
                'text_end': 17,
                'attributes': {}
            }
        ]
        result = _build_screenplay_body(text, extractions, None)
        self.assertIn('hl-dialogue', result)


class TestLegendAndStats(unittest.TestCase):
    """Test legend and stats HTML builders."""

    def test_legend_contains_all_classes(self):
        """Legend should have an entry for each active class."""
        active = {'character', 'prop', 'dialogue'}
        result = _build_legend(active)
        self.assertIn('Character', result)
        self.assertIn('Prop', result)
        self.assertIn('Dialogue', result)
        self.assertIn('legend-item', result)

    def test_empty_legend(self):
        """Empty active classes should produce empty string."""
        result = _build_legend(set())
        self.assertEqual(result, '')

    def test_stats_counts(self):
        """Stats should count extractions per class."""
        result = _build_stats(SAMPLE_EXTRACTIONS, {'scene_header', 'character', 'prop', 'dialogue'}, 200)
        self.assertIn('Total Extractions', result)
        self.assertIn('5', result)  # total count
        self.assertIn('Text Coverage', result)

    def test_empty_stats(self):
        """Empty extractions should produce empty string."""
        result = _build_stats([], set(), 100)
        self.assertEqual(result, '')


class TestCoverPage(unittest.TestCase):
    """Test cover page generation."""

    def test_cover_includes_title(self):
        """Cover page should include the script title."""
        result = _build_cover_page('My Script', 'John Doe', {}, None)
        self.assertIn('My Script', result)
        self.assertIn('John Doe', result)
        self.assertIn('HIGHLIGHTED SCRIPT BREAKDOWN', result)

    def test_cover_with_filter(self):
        """Cover page should list filtered classes when provided."""
        result = _build_cover_page('Test', '', {}, ['character', 'prop'])
        self.assertIn('Character', result)
        self.assertIn('Prop', result)
        self.assertIn('Showing:', result)


class TestClassCss(unittest.TestCase):
    """Test CSS generation per class."""

    def test_generates_css_for_active_classes(self):
        """Should produce CSS rules for each class."""
        css = _generate_class_css({'character', 'prop'})
        self.assertIn('.hl-character', css)
        self.assertIn('.hl-prop', css)
        self.assertNotIn('.hl-dialogue', css)


class TestBuildHighlightedHtml(unittest.TestCase):
    """Test full HTML document assembly."""

    def test_full_html_structure(self):
        """Full HTML should contain all major sections."""
        result = _build_highlighted_html(
            script_text=SAMPLE_TEXT,
            extractions=SAMPLE_EXTRACTIONS,
            script_meta={'title': 'Die Testament', 'writer_name': 'Alex Burger'},
            filter_classes=None,
            page_boundaries=None
        )
        self.assertIn('<!DOCTYPE html>', result)
        self.assertIn('Die Testament', result)
        self.assertIn('Alex Burger', result)
        self.assertIn('hl-scene_header', result)
        self.assertIn('hl-character', result)
        self.assertIn('hl-prop', result)
        self.assertIn('hl-dialogue', result)
        self.assertIn('Extraction Legend', result)
        self.assertIn('Total Extractions', result)

    def test_screenplay_structure_present(self):
        """Full HTML should contain screenplay structural CSS classes."""
        result = _build_highlighted_html(
            script_text=SAMPLE_TEXT,
            extractions=SAMPLE_EXTRACTIONS,
            script_meta={'title': 'Test'},
            filter_classes=None,
            page_boundaries=None
        )
        self.assertIn('sp-scene-heading', result)
        self.assertIn('sp-character-cue', result)
        self.assertIn('sp-dialogue', result)

    def test_filter_classes(self):
        """Filtering should only include specified classes."""
        result = _build_highlighted_html(
            script_text=SAMPLE_TEXT,
            extractions=SAMPLE_EXTRACTIONS,
            script_meta={'title': 'Test'},
            filter_classes=['character'],
            page_boundaries=None
        )
        self.assertIn('hl-character', result)
        self.assertNotIn('hl-prop', result)
        self.assertNotIn('hl-dialogue', result)

    def test_xss_protection(self):
        """HTML should escape special characters."""
        result = _build_highlighted_html(
            script_text='<script>alert("xss")</script>',
            extractions=[],
            script_meta={'title': '<b>Bad Title</b>'},
            filter_classes=None,
            page_boundaries=None
        )
        self.assertNotIn('<script>alert', result)
        self.assertIn('&lt;b&gt;Bad Title&lt;/b&gt;', result)


if __name__ == '__main__':
    print("=" * 60)
    print("Running Highlighted Script PDF Service Tests")
    print("=" * 60)
    unittest.main(verbosity=2)
