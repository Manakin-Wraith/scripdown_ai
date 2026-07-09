import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.fdx_parser import _read_fdx, _normalize_speaker, _build_scenes
from services.fdx_parser import _synthesize_page_dicts, _extract_fdx_metadata, parse_fdx_upload
from services.fdx_parser import _is_fdx


def test_is_fdx_detection():
    assert _is_fdx("My Script.fdx") is True
    assert _is_fdx("My Script.FDX") is True
    assert _is_fdx("My Script.pdf") is False
    assert _is_fdx("noext") is False


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
    # scene content / location hierarchy populated
    assert scenes[0].scene_text != ""
    assert isinstance(scenes[0].location_hierarchy, list)
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


def test_synthesize_page_dicts_chunks_by_55_lines():
    text = "\n".join(f"line {i}" for i in range(130))  # 130 lines -> 3 pages
    pages = _synthesize_page_dicts(text)
    assert len(pages) == 3
    assert [p["page_number"] for p in pages] == [1, 2, 3]
    assert all("text" in p for p in pages)


def test_synthesize_page_dicts_single_page_for_short_text():
    pages = _synthesize_page_dicts("INT. HOUSE - DAY\nJohn enters.")
    assert len(pages) == 1


def test_synthesize_page_dicts_empty_for_blank_text():
    assert _synthesize_page_dicts("") == []
    assert _synthesize_page_dicts("   \n  ") == []


def test_extract_metadata_finds_author():
    tp = [
        {"type": "", "text": "MY GREAT SCRIPT", "number": None},
        {"type": "", "text": "Written by Jane Doe", "number": None},
    ]
    meta = _extract_fdx_metadata(tp)
    assert meta["writers"] == "Jane Doe"
    assert meta["title"] == "MY GREAT SCRIPT"


def test_parse_fdx_upload_end_to_end(tmp_path):
    path = _write_fdx(tmp_path, MINIMAL_FDX)
    pages_data, full_text, metadata, parsed_scenes = parse_fdx_upload(path)

    assert len(parsed_scenes) == 1
    s = parsed_scenes[0]
    assert s.scene_number_original == "1"
    assert s.setting == "COFFEE SHOP"
    assert "JOHN" in s.speakers
    assert s.parse_method == "fdx"
    assert s.scene_text != ""
    assert len(pages_data) >= 1
    assert pages_data[0]["page_number"] == 1
    assert "COFFEE SHOP" in full_text
    assert metadata["writers"] == "Jane Doe"


# ---------------------------------------------------------------------------
# Eighths: prefer Final Draft <SceneProperties Length>, else spacing-aware estimate
# ---------------------------------------------------------------------------

from services.fdx_parser import _parse_fdx_length, _estimate_scene_eighths


@pytest.mark.parametrize("raw,expected", [
    ("1/8", 1),
    ("2/8", 2),
    ("7/8", 7),
    ("8/8", 8),
    ("1 3/8", 11),
    ("2 0/8", 16),
    ("2", 16),
    ("", None),
    (None, None),
    ("garbage", None),
    ("0/8", None),
])
def test_parse_fdx_length(raw, expected):
    assert _parse_fdx_length(raw) == expected


def test_estimate_scene_eighths_grows_with_paragraph_count():
    short = _estimate_scene_eighths(["INT. HOUSE - DAY", "A quiet room."])
    dialogue_heavy = _estimate_scene_eighths(
        ["INT. HOUSE - DAY"] + [t for _ in range(20) for t in ("JOHN", "A line of dialogue here.")]
    )
    assert short >= 1
    # 41 elements with per-element blank lines must read as well over 1/8.
    assert dialogue_heavy >= 8
    assert dialogue_heavy > short


def test_build_scenes_uses_fdx_length_when_present():
    paras = [
        {"type": "Scene Heading", "text": "INT. HOUSE - DAY", "number": "1", "length": "2/8"},
        {"type": "Action", "text": "Short.", "number": None, "length": None},
    ]
    scenes, _ = _build_scenes(paras)
    assert scenes[0].length_eighths == 2   # from FDX Length, not the tiny content estimate


def test_build_scenes_estimates_eighths_when_length_absent():
    body = [t for _ in range(20) for t in ("JOHN", "A line of dialogue here.")]
    paras = [{"type": "Scene Heading", "text": "INT. HOUSE - DAY", "number": None, "length": None}]
    paras += [{"type": ("Character" if t == "JOHN" else "Dialogue"), "text": t, "number": None, "length": None} for t in body]
    scenes, _ = _build_scenes(paras)
    # No Length -> spacing-aware estimate; a 40-line dialogue scene must exceed 1/8.
    assert scenes[0].length_eighths >= 8


def test_parse_fdx_upload_populates_length_eighths(tmp_path):
    path = _write_fdx(tmp_path, MINIMAL_FDX)
    _, _, _, parsed_scenes = parse_fdx_upload(path)
    assert parsed_scenes[0].length_eighths == 1   # MINIMAL_FDX heading has Length="1/8"
