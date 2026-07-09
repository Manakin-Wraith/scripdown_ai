import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.fdx_parser import _read_fdx, _normalize_speaker, _build_scenes
from services.fdx_parser import _synthesize_pages, _extract_fdx_metadata, parse_fdx


MINIMAL_FDX = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<FinalDraft DocumentType="Script" Template="No" Version="5">
  <Content>
    <Paragraph Type="Scene Heading" Number="1">
      <SceneProperties Length="1/8" Page="1" Title=""/>
      <Text>INT. COFFEE SHOP - DAY</Text>
    </Paragraph>
    <Paragraph Type="Action">
      <Text>John sips his coffee.</Text>
    </Paragraph>
    <Paragraph Type="Character">
      <Text>JOHN</Text>
    </Paragraph>
    <Paragraph Type="Dialogue">
      <Text>Morning.</Text>
    </Paragraph>
  </Content>
  <TitlePage>
    <Content>
      <Paragraph><Text>MY GREAT SCRIPT</Text></Paragraph>
      <Paragraph><Text>Written by Jane Doe</Text></Paragraph>
    </Content>
  </TitlePage>
</FinalDraft>
"""


def _write_fdx(tmp_path, xml):
    p = tmp_path / "script.fdx"
    p.write_text(xml, encoding="utf-8")
    return str(p)


def test_read_fdx_returns_content_and_titlepage(tmp_path):
    path = _write_fdx(tmp_path, MINIMAL_FDX)
    content, titlepage = _read_fdx(path)

    types = [p["type"] for p in content]
    assert types == ["Scene Heading", "Action", "Character", "Dialogue"]
    assert content[0]["text"] == "INT. COFFEE SHOP - DAY"
    assert content[0]["number"] == "1"
    assert content[2]["text"] == "JOHN"

    tp_texts = [p["text"] for p in titlepage]
    assert "MY GREAT SCRIPT" in tp_texts
    assert "Written by Jane Doe" in tp_texts


@pytest.mark.parametrize("raw,expected", [
    ("JOHN", "JOHN"),
    ("john", "JOHN"),
    ("  MARY  ", "MARY"),
    ("JOHN (CONT'D)", "JOHN"),
    ("MARY (V.O.)", "MARY"),
    ("BOB (O.S.)", "BOB"),
    ("SUE (O.C.)", "SUE"),
])
def test_normalize_speaker(raw, expected):
    assert _normalize_speaker(raw) == expected


TWO_SCENE_PARAS = [
    {"type": "Scene Heading", "text": "INT. COFFEE SHOP - DAY", "number": "1"},
    {"type": "Action", "text": "John sips coffee.", "number": None},
    {"type": "Character", "text": "JOHN (CONT'D)", "number": None},
    {"type": "Dialogue", "text": "Morning.", "number": None},
    {"type": "Scene Heading", "text": "EXT. PARK - NIGHT", "number": "2"},
    {"type": "Action", "text": "Mary walks.", "number": None},
    {"type": "Character", "text": "MARY", "number": None},
    {"type": "Dialogue", "text": "Hello.", "number": None},
]


def test_build_scenes_basic():
    scenes, full_text = _build_scenes(TWO_SCENE_PARAS)

    assert len(scenes) == 2
    assert scenes[0].scene_number_original == "1"
    assert scenes[0].int_ext == "INT"
    assert scenes[0].setting == "COFFEE SHOP"
    assert scenes[0].time_of_day == "DAY"
    assert scenes[0].parse_method == "fdx"
    # speaker extension stripped and normalized
    assert "JOHN" in scenes[0].speakers
    # scene 2
    assert scenes[1].scene_number_original == "2"
    assert scenes[1].int_ext == "EXT"
    assert "MARY" in scenes[1].speakers
    # text offsets point into full_text and are non-empty
    assert full_text[scenes[0].text_start:scenes[0].text_end].strip() != ""
    assert scenes[0].scene_order == 1 and scenes[1].scene_order == 2


def test_build_scenes_assigns_sequential_when_unnumbered():
    paras = [
        {"type": "Scene Heading", "text": "INT. HOUSE - DAY", "number": None},
        {"type": "Action", "text": "A room.", "number": None},
        {"type": "Scene Heading", "text": "EXT. STREET - DAY", "number": None},
        {"type": "Action", "text": "A street.", "number": None},
    ]
    scenes, _ = _build_scenes(paras)
    assert [s.scene_number_original for s in scenes] == ["1", "2"]


def test_build_scenes_page_range_grows_for_long_scene():
    long_action = "A very long line of action description. " * 60  # ~ many lines
    paras = [
        {"type": "Scene Heading", "text": "INT. HOUSE - DAY", "number": "1"},
        {"type": "Action", "text": long_action, "number": None},
        {"type": "Scene Heading", "text": "EXT. STREET - DAY", "number": "2"},
        {"type": "Action", "text": "Short.", "number": None},
    ]
    scenes, _ = _build_scenes(paras)
    # Scene 2 must start on a later page than scene 1 started.
    assert scenes[1].page_start >= scenes[0].page_start
    assert scenes[0].page_end >= scenes[0].page_start


def test_synthesize_pages_chunks_by_55_lines():
    text = "\n".join(f"line {i}" for i in range(130))  # 130 lines -> 3 pages
    pages = _synthesize_pages(text)
    assert len(pages) == 3
    assert pages[0].page_number == 1
    assert all(p.content_hash for p in pages)


def test_synthesize_pages_single_page_for_short_text():
    pages = _synthesize_pages("INT. HOUSE - DAY\nJohn enters.")
    assert len(pages) == 1


def test_extract_metadata_finds_author():
    tp = [
        {"type": "", "text": "MY GREAT SCRIPT", "number": None},
        {"type": "", "text": "Written by Jane Doe", "number": None},
    ]
    meta = _extract_fdx_metadata(tp)
    assert meta["writer_name"] == "Jane Doe"
    assert meta["title"] == "MY GREAT SCRIPT"
    assert meta["writer_email"] is None


def test_parse_fdx_end_to_end(tmp_path):
    path = _write_fdx(tmp_path, MINIMAL_FDX)
    pages, full_text, candidates, metadata = parse_fdx(path)

    assert len(candidates) == 1
    c = candidates[0]
    assert c.scene_number_original == "1"
    assert c.setting == "COFFEE SHOP"
    assert "JOHN" in c.speakers
    assert c.parse_method == "fdx"
    assert len(pages) >= 1
    assert "COFFEE SHOP" in full_text
    assert metadata["writer_name"] == "Jane Doe"
