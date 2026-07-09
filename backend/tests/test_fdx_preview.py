import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.fdx_preview import render_fdx_html, screenplay_css, build_render_scenes, generate_fdx_preview_pdf


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


_FDX_XML = """<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Version="5">
  <Content>
    <Paragraph Type="Scene Heading" Number="1"><Text>INT. COFFEE SHOP - DAY</Text></Paragraph>
    <Paragraph Type="Action"><Text>John sips.</Text></Paragraph>
    <Paragraph Type="Character"><Text>JOHN</Text></Paragraph>
    <Paragraph Type="Dialogue"><Text>Morning.</Text></Paragraph>
    <Paragraph Type="Scene Heading" Number="2"><Text>EXT. PARK - NIGHT</Text></Paragraph>
    <Paragraph Type="Action"><Text>Mary walks.</Text></Paragraph>
  </Content>
</FinalDraft>
"""


def _write(tmp_path, xml):
    p = tmp_path / "s.fdx"
    p.write_text(xml, encoding="utf-8")
    return str(p)


def test_build_render_scenes_pairs_by_order(tmp_path):
    path = _write(tmp_path, _FDX_XML)
    rows = [{"id": "id-1", "scene_order": 1}, {"id": "id-2", "scene_order": 2}]
    render = build_render_scenes(path, rows)
    assert [r["scene_id"] for r in render] == ["id-1", "id-2"]
    assert render[0]["paragraphs"][0]["type"] == "Scene Heading"
    assert render[0]["paragraphs"][0]["text"] == "INT. COFFEE SHOP - DAY"
    # scene 1 group carries its body paragraphs
    assert any(p["text"] == "Morning." for p in render[0]["paragraphs"])
    assert render[1]["paragraphs"][0]["text"] == "EXT. PARK - NIGHT"


def test_build_render_scenes_handles_unsorted_rows(tmp_path):
    path = _write(tmp_path, _FDX_XML)
    rows = [{"id": "id-2", "scene_order": 2}, {"id": "id-1", "scene_order": 1}]
    render = build_render_scenes(path, rows)
    assert [r["scene_id"] for r in render] == ["id-1", "id-2"]


_FDX_TWO_PAGE = """<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Version="5">
  <Content>
    <Paragraph Type="Scene Heading" Number="1"><Text>INT. ROOM ONE - DAY</Text></Paragraph>
    <Paragraph Type="Action"><Text>{filler}</Text></Paragraph>
    <Paragraph Type="Scene Heading" Number="2"><Text>INT. ROOM TWO - DAY</Text></Paragraph>
    <Paragraph Type="Action"><Text>Short.</Text></Paragraph>
  </Content>
</FinalDraft>
"""


def test_generate_pdf_returns_bytes_and_mapping(tmp_path):
    # Long filler action forces scene 2 onto a later page.
    filler = "This is a line of action description that wraps. " * 120
    p = tmp_path / "two.fdx"
    p.write_text(_FDX_TWO_PAGE.replace("{filler}", filler), encoding="utf-8")
    rows = [{"id": "s1", "scene_order": 1}, {"id": "s2", "scene_order": 2}]

    pdf_bytes, scene_page_map = generate_fdx_preview_pdf(str(p), rows)

    assert pdf_bytes[:5] == b"%PDF-"
    assert set(scene_page_map.keys()) == {"s1", "s2"}
    assert scene_page_map["s1"] == 1
    assert scene_page_map["s2"] >= 2          # pushed to a later page by the filler
    assert scene_page_map["s2"] >= scene_page_map["s1"]
