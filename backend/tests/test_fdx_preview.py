import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.fdx_preview import render_fdx_html, screenplay_css


SCENES = [
    {"scene_id": "aaa-1", "paragraphs": [
        {"type": "Scene Heading", "text": "INT. COFFEE SHOP - DAY"},
        {"type": "Action", "text": "John sips coffee."},
        {"type": "Character", "text": "JOHN"},
        {"type": "Parenthetical", "text": "(tired)"},
        {"type": "Dialogue", "text": "Morning."},
        {"type": "Transition", "text": "CUT TO:"},
    ]},
    {"scene_id": "bbb-2", "paragraphs": [
        {"type": "Scene Heading", "text": "EXT. PARK - NIGHT"},
        {"type": "Action", "text": "Mary walks."},
    ]},
]


def test_render_html_has_one_anchor_per_scene():
    html = render_fdx_html(SCENES)
    assert 'id="scene-aaa-1"' in html
    assert 'id="scene-bbb-2"' in html
    # exactly one anchor per scene
    assert html.count('id="scene-') == 2


def test_render_html_styles_by_paragraph_type():
    html = render_fdx_html(SCENES)
    assert 'class="scene-heading"' in html
    assert 'class="action"' in html
    assert 'class="character"' in html
    assert 'class="parenthetical"' in html
    assert 'class="dialogue"' in html
    assert 'class="transition"' in html
    # scene body text present and HTML-escaped-safe
    assert "Morning." in html


def test_render_html_escapes_text():
    scenes = [{"scene_id": "x", "paragraphs": [
        {"type": "Scene Heading", "text": "INT. LAB <SECRET> - DAY"},
        {"type": "Action", "text": "A & B <tag>"},
    ]}]
    html = render_fdx_html(scenes)
    assert "&lt;SECRET&gt;" in html
    assert "A &amp; B &lt;tag&gt;" in html


def test_screenplay_css_is_letter_monospace():
    css = screenplay_css()
    assert "Letter" in css
    assert "12pt" in css
    assert "monospace" in css
