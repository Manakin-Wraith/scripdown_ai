# FDX (Final Draft) Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users upload Final Draft `.fdx` files, parsed into the same scene/candidate structures the PDF path produces, so the entire downstream pipeline (AI breakdown, reports, stripboard) works unchanged.

**Architecture:** A new `backend/services/fdx_parser.py` adapter reads the FDX XML and returns the exact four values `process_script_v2` already consumes — `(pages, full_text, candidates, metadata)`. `process_script_v2` routes by file extension: `.fdx` → the new parser, everything else → the existing PDF path. FDX supplies scene structure, real scene numbers, and speakers; the AI phase fills breakdown categories FDX does not contain.

**Tech Stack:** Python 3.13, Flask, `defusedxml` (hardened XML parsing — same API as stdlib ElementTree, but safe against XXE / billion-laughs on untrusted uploads), pytest. Frontend: React + `react-dropzone`.

## Global Constraints

- Reuse the existing `PageData` and `SceneCandidate` dataclasses from `backend/services/extraction_pipeline.py` — do NOT define parallel types.
- Reuse `detect_scene_headers` (from `extraction_pipeline.py`) for INT/EXT/setting/time-of-day parsing so FDX matches PDF behavior.
- Reuse `compute_content_hash` (from `extraction_pipeline.py`) for all hashes.
- Reuse `calculate_eighths_from_content` convention from `backend/utils/scene_calculations.py`: ~55 lines/page, 8 eighths/page. Do NOT hardcode a different number.
- Scene numbers come from the FDX file, never invented. Only assign sequential numbers when the file has none.
- `parse_method = "fdx"` on every FDX-produced `SceneCandidate`.
- Parse FDX with `defusedxml`, NEVER stdlib `xml.etree.ElementTree` — FDX uploads are untrusted and stdlib XML is vulnerable to XXE and billion-laughs attacks. `defusedxml.ElementTree` is a drop-in for the `.parse()` call used here. Add `defusedxml` to `backend/requirements.txt`.
- Backend tests run from `backend/` with `pytest tests/ -v`. Test files put backend on the path via `sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))` (match `tests/test_screenplay_parser.py`).

---

## File Structure

- **Create** `backend/services/fdx_parser.py` — the adapter. All FDX logic lives here.
- **Create** `backend/tests/test_fdx_parser.py` — unit tests + inline FDX fixtures.
- **Modify** `backend/services/script_service.py` — add extension routing in `process_script_v2`.
- **Modify** `frontend/src/components/script/DropZone.jsx` — accept `.fdx`, update copy.

---

## Task 1: FDX paragraph + title-page extraction

**Files:**
- Create: `backend/services/fdx_parser.py`
- Modify: `backend/requirements.txt`
- Test: `backend/tests/test_fdx_parser.py`

**Interfaces:**
- Produces: `_read_fdx(file_path: str) -> tuple[list[dict], list[dict]]` returning `(content_paragraphs, titlepage_paragraphs)`, where each paragraph is `{"type": str, "text": str, "number": str | None}`. `type` is the FDX `Type` attribute (e.g. `"Scene Heading"`, `"Action"`, `"Character"`); `number` is the scene number attribute when present, else `None`. Paragraphs with no direct `<Text>` content and no type are skipped.

- [ ] **Step 0: Add the `defusedxml` dependency**

Append `defusedxml` to `backend/requirements.txt` (pin if the file pins others; otherwise a bare line is fine):

```
defusedxml
```

Install it into the venv:

Run: `cd backend && ./venv/bin/pip install defusedxml`
Expected: `Successfully installed defusedxml-...`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_fdx_parser.py`:

```python
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.fdx_parser import _read_fdx


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_fdx_parser.py::test_read_fdx_returns_content_and_titlepage -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.fdx_parser'`.

- [ ] **Step 3: Write minimal implementation**

Create `backend/services/fdx_parser.py`:

```python
"""
FDX (Final Draft) import adapter.

Reads Final Draft .fdx XML and emits the same (pages, full_text, candidates,
metadata) contract that process_script_v2 already consumes for PDFs. FDX is
structured, so scene boundaries, scene numbers, and speakers are read directly
rather than inferred.
"""

# defusedxml, NOT stdlib ElementTree: FDX uploads are untrusted (XXE / billion-laughs).
import defusedxml.ElementTree as ET


def _paragraph_text(para) -> str:
    """Concatenate the DIRECT <Text> children of a paragraph.

    Uses findall (not iter) so a DualDialogue wrapper paragraph does not
    absorb the text of its nested child paragraphs.
    """
    return "".join((t.text or "") for t in para.findall("Text"))


def _scene_number(para) -> str | None:
    """Read the scene number from the Paragraph's Number attribute, or from a
    child <SceneProperties Number="..."> element. Returns None when absent."""
    num = para.get("Number")
    if num:
        return num
    props = para.find("SceneProperties")
    if props is not None and props.get("Number"):
        return props.get("Number")
    return None


def _read_fdx(file_path: str):
    """Parse an .fdx file into (content_paragraphs, titlepage_paragraphs).

    Each paragraph is {"type": str, "text": str, "number": str | None}.
    Paragraphs with no type AND no direct text (e.g. DualDialogue wrappers)
    are skipped.
    """
    tree = ET.parse(file_path)
    root = tree.getroot()

    content_paras = []
    content_el = root.find("Content")
    if content_el is not None:
        for para in content_el.iter("Paragraph"):
            ptype = para.get("Type")
            text = _paragraph_text(para)
            if not ptype and not text:
                continue
            content_paras.append({
                "type": ptype or "",
                "text": text,
                "number": _scene_number(para),
            })

    titlepage_paras = []
    tp_el = root.find("TitlePage")
    if tp_el is not None:
        for para in tp_el.iter("Paragraph"):
            text = _paragraph_text(para)
            if text:
                titlepage_paras.append({
                    "type": para.get("Type") or "",
                    "text": text,
                    "number": None,
                })

    return content_paras, titlepage_paras
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_fdx_parser.py::test_read_fdx_returns_content_and_titlepage -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/fdx_parser.py backend/tests/test_fdx_parser.py backend/requirements.txt
git commit -m "feat(fdx): read FDX paragraphs and title page (defusedxml)"
```

---

## Task 2: Speaker name normalization

**Files:**
- Modify: `backend/services/fdx_parser.py`
- Test: `backend/tests/test_fdx_parser.py`

**Interfaces:**
- Produces: `_normalize_speaker(name: str) -> str` — uppercases, trims, and strips trailing dialogue extensions like `(CONT'D)`, `(V.O.)`, `(O.S.)`, `(O.C.)`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_fdx_parser.py`:

```python
from services.fdx_parser import _normalize_speaker


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_fdx_parser.py::test_normalize_speaker -v`
Expected: FAIL with `ImportError: cannot import name '_normalize_speaker'`.

- [ ] **Step 3: Write minimal implementation**

Add to `backend/services/fdx_parser.py` (add `import re` at the top, below the module docstring):

```python
import re

_SPEAKER_EXTENSION_RE = re.compile(r"\s*\((?:CONT'D|CONTD|V\.?O\.?|O\.?S\.?|O\.?C\.?)\)\s*$", re.IGNORECASE)


def _normalize_speaker(name: str) -> str:
    """Normalize a character cue: uppercase, trimmed, extensions removed."""
    cleaned = _SPEAKER_EXTENSION_RE.sub("", name.strip())
    return cleaned.strip().upper()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_fdx_parser.py::test_normalize_speaker -v`
Expected: PASS (7 parametrized cases).

- [ ] **Step 5: Commit**

```bash
git add backend/services/fdx_parser.py backend/tests/test_fdx_parser.py
git commit -m "feat(fdx): normalize speaker names"
```

---

## Task 3: Assemble scenes into SceneCandidate objects

**Files:**
- Modify: `backend/services/fdx_parser.py`
- Test: `backend/tests/test_fdx_parser.py`

**Interfaces:**
- Consumes: `_read_fdx` (Task 1), `_normalize_speaker` (Task 2), and from `services.extraction_pipeline`: `SceneCandidate`, `ExtractionStatus`, `detect_scene_headers`, `compute_content_hash`; from `utils.scene_calculations`: `calculate_eighths_from_content`.
- Produces: `_build_scenes(content_paragraphs: list[dict]) -> tuple[list[SceneCandidate], str]` returning `(candidates, full_text)`. Each candidate has `parse_method="fdx"`, `speakers` pre-filled (a `{name: line_count}` dict), real `scene_number_original` when the FDX supplied one, sequential otherwise, and `page_start`/`page_end` derived from a running 55-line-per-page counter.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_fdx_parser.py`:

```python
from services.fdx_parser import _build_scenes

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_fdx_parser.py -k build_scenes -v`
Expected: FAIL with `ImportError: cannot import name '_build_scenes'`.

- [ ] **Step 3: Write minimal implementation**

Add to `backend/services/fdx_parser.py`:

```python
from services.extraction_pipeline import (
    SceneCandidate,
    ExtractionStatus,
    detect_scene_headers,
    compute_content_hash,
    assign_scene_numbers,
)

LINES_PER_PAGE = 55


def _parse_heading(heading_text: str) -> dict:
    """Parse a scene-heading line into int_ext/setting/time_of_day using the
    same regex the PDF path uses. Falls back to sensible defaults."""
    headers = detect_scene_headers(heading_text)
    if headers:
        h = headers[0]
        return {
            "int_ext": h["int_ext"],
            "setting": h["setting"],
            "time_of_day": h["time_of_day"],
        }
    return {"int_ext": "INT", "setting": heading_text.strip(), "time_of_day": "DAY"}


def _line_count(text: str) -> int:
    """Number of rendered lines, minimum 1."""
    return max(1, text.count("\n") + 1)


def _build_scenes(content_paragraphs):
    """Group paragraphs into scenes and return (candidates, full_text)."""
    # Split paragraphs into scene groups on each Scene Heading.
    groups = []  # list of dicts: {"heading": para, "body": [para, ...]}
    for para in content_paragraphs:
        if para["type"] == "Scene Heading":
            groups.append({"heading": para, "body": []})
        elif groups:
            groups[0:0] if False else groups[-1]["body"].append(para)
        # paragraphs before the first heading are ignored (title/front matter)

    candidates = []
    full_text = ""
    cumulative_lines = 0

    # Pre-assign scene numbers for headings that lack one, matching PDF behavior.
    pseudo_headers = [{"scene_number": g["heading"]["number"]} for g in groups]
    pseudo_headers = assign_scene_numbers(pseudo_headers)

    for i, group in enumerate(groups):
        heading_para = group["heading"]
        parsed = _parse_heading(heading_para["text"])

        # Assemble scene text: heading + body lines.
        lines = [heading_para["text"]]
        speakers = {}
        for body in group["body"]:
            lines.append(body["text"])
            if body["type"] == "Character" and body["text"].strip():
                name = _normalize_speaker(body["text"])
                if name:
                    speakers[name] = speakers.get(name, 0) + 1
        scene_text = "\n".join(lines)

        # Page range from running line counter (55 lines/page).
        page_start = cumulative_lines // LINES_PER_PAGE + 1
        cumulative_lines += _line_count(scene_text)
        page_end = max(page_start, (cumulative_lines - 1) // LINES_PER_PAGE + 1)

        text_start = len(full_text)
        full_text += scene_text + "\n"
        text_end = len(full_text)

        candidates.append(SceneCandidate(
            scene_number_original=pseudo_headers[i]["scene_number"],
            scene_order=i + 1,
            int_ext=parsed["int_ext"],
            setting=parsed["setting"],
            time_of_day=parsed["time_of_day"],
            page_start=page_start,
            page_end=page_end,
            text_start=text_start,
            text_end=text_end,
            content_hash=compute_content_hash(scene_text),
            status=ExtractionStatus.PENDING,
            speakers=speakers,
            parse_method="fdx",
        ))

    return candidates, full_text
```

> Note: the `groups[0:0] if False else ...` line is deliberately just `groups[-1]["body"].append(para)`. Write it plainly:
> ```python
> elif groups:
>     groups[-1]["body"].append(para)
> ```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_fdx_parser.py -k build_scenes -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/services/fdx_parser.py backend/tests/test_fdx_parser.py
git commit -m "feat(fdx): assemble scenes with speakers and page estimates"
```

---

## Task 4: Synthesize pages and extract title-page metadata

**Files:**
- Modify: `backend/services/fdx_parser.py`
- Test: `backend/tests/test_fdx_parser.py`

**Interfaces:**
- Consumes: `PageData`, `compute_content_hash` from `services.extraction_pipeline`.
- Produces:
  - `_synthesize_pages(full_text: str) -> list[PageData]` — chunks `full_text` into 55-line `PageData` pages (at least one page for non-empty text).
  - `_extract_fdx_metadata(titlepage_paragraphs: list[dict]) -> dict` — returns the `extract_metadata` dict shape with keys `writer_name`, `writer_email`, `writer_phone`, `draft_version`, `draft_date`, `copyright_info`, `wga_registration`, `additional_credits`, `title`; unknown fields are `None`. Detects an author line matching `written by X` / `by X`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_fdx_parser.py`:

```python
from services.fdx_parser import _synthesize_pages, _extract_fdx_metadata


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_fdx_parser.py -k "synthesize or metadata" -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write minimal implementation**

Add to `backend/services/fdx_parser.py` (extend the extraction_pipeline import to include `PageData`):

```python
from services.extraction_pipeline import PageData  # add to existing import block

_METADATA_KEYS = [
    "writer_name", "writer_email", "writer_phone", "draft_version",
    "draft_date", "copyright_info", "wga_registration", "additional_credits",
]

_AUTHOR_RE = re.compile(r"^(?:written\s+by|by)\s+(.+)$", re.IGNORECASE)


def _synthesize_pages(full_text: str):
    """Chunk full_text into ~55-line PageData pages."""
    if not full_text.strip():
        return []
    lines = full_text.split("\n")
    pages = []
    for page_num, start in enumerate(range(0, len(lines), LINES_PER_PAGE), start=1):
        page_text = "\n".join(lines[start:start + LINES_PER_PAGE])
        pages.append(PageData(
            page_number=page_num,
            text=page_text,
            content_hash=compute_content_hash(page_text),
        ))
    return pages


def _extract_fdx_metadata(titlepage_paragraphs):
    """Best-effort metadata from the FDX title page."""
    meta = {k: None for k in _METADATA_KEYS}
    meta["title"] = None
    for i, para in enumerate(titlepage_paragraphs):
        text = para["text"].strip()
        if not text:
            continue
        if meta["title"] is None:
            meta["title"] = text
        m = _AUTHOR_RE.match(text)
        if m and not meta["writer_name"]:
            meta["writer_name"] = m.group(1).strip()
    return meta
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_fdx_parser.py -k "synthesize or metadata" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/services/fdx_parser.py backend/tests/test_fdx_parser.py
git commit -m "feat(fdx): synthesize pages and extract title-page metadata"
```

---

## Task 5: `parse_fdx` entry point

**Files:**
- Modify: `backend/services/fdx_parser.py`
- Test: `backend/tests/test_fdx_parser.py`

**Interfaces:**
- Consumes: all helpers from Tasks 1–4.
- Produces: `parse_fdx(file_path: str) -> tuple[list[PageData], str, list[SceneCandidate], dict]` returning `(pages, full_text, candidates, metadata)` — the exact contract `process_script_v2` consumes.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_fdx_parser.py` (reuses `MINIMAL_FDX` and `_write_fdx` from Task 1):

```python
from services.fdx_parser import parse_fdx


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_fdx_parser.py::test_parse_fdx_end_to_end -v`
Expected: FAIL with `ImportError: cannot import name 'parse_fdx'`.

- [ ] **Step 3: Write minimal implementation**

Add to `backend/services/fdx_parser.py`:

```python
def parse_fdx(file_path: str):
    """Parse an .fdx file into the (pages, full_text, candidates, metadata)
    contract consumed by process_script_v2."""
    content_paras, titlepage_paras = _read_fdx(file_path)
    candidates, full_text = _build_scenes(content_paras)
    pages = _synthesize_pages(full_text)
    metadata = _extract_fdx_metadata(titlepage_paras)
    return pages, full_text, candidates, metadata
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_fdx_parser.py -v`
Expected: PASS (all tests in the file).

- [ ] **Step 5: Commit**

```bash
git add backend/services/fdx_parser.py backend/tests/test_fdx_parser.py
git commit -m "feat(fdx): parse_fdx entry point"
```

---

## Task 6: Route `.fdx` uploads in `process_script_v2`

**Files:**
- Modify: `backend/services/script_service.py:12-104`
- Test: `backend/tests/test_fdx_parser.py`

**Interfaces:**
- Consumes: `parse_fdx` (Task 5).
- Produces: `process_script_v2` handles `.fdx` files by routing to `parse_fdx`; `.pdf` and all other extensions keep the existing path. No signature change.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_fdx_parser.py` a routing test that exercises the dispatch logic directly (DB is not available in unit tests, so test the routing helper, not the DB write):

First, the routing decision must be extractable. Add a small pure helper to `script_service.py` and test it.

```python
from services.script_service import _is_fdx


def test_is_fdx_detection():
    assert _is_fdx("My Script.fdx") is True
    assert _is_fdx("My Script.FDX") is True
    assert _is_fdx("My Script.pdf") is False
    assert _is_fdx("noext") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_fdx_parser.py::test_is_fdx_detection -v`
Expected: FAIL with `ImportError: cannot import name '_is_fdx'`.

- [ ] **Step 3: Write minimal implementation**

In `backend/services/script_service.py`, add the helper near the top (after imports):

```python
def _is_fdx(filename: str) -> bool:
    """True when the uploaded filename is a Final Draft .fdx file."""
    return os.path.splitext(filename)[1].lower() == ".fdx"
```

Then modify `process_script_v2` to route. Replace the parse block (currently lines ~41-52, from the `# Parse PDF with page awareness` comment through the `extract_metadata` call) with:

```python
    # Route by file type: FDX is structured; PDF is text-extracted.
    if _is_fdx(filename):
        from services.fdx_parser import parse_fdx
        print(f"[Upload] Parsing Final Draft FDX: {filename}")
        pages, full_text, candidates, metadata = parse_fdx(file_path)
    else:
        print(f"[Upload] Parsing PDF with page awareness: {filename}")
        pages, full_text = parse_pdf_with_pages(file_path)
        candidates = build_scene_candidates(pages, full_text)
        metadata = extract_metadata(file_path)

    print(f"[Upload] Parsed {len(pages)} pages, {len(candidates)} candidates")
```

Everything after this block (the `scripts` INSERT, `save_pages_to_db`, `save_scene_candidates_to_db`, and the return dict) stays exactly as-is — it already consumes `pages`, `full_text`, `candidates`, and `metadata`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_fdx_parser.py -v`
Expected: PASS (all tests).

Then run the full suite to confirm nothing regressed:
Run: `cd backend && pytest tests/ -v`
Expected: PASS (existing tests still green).

- [ ] **Step 5: Commit**

```bash
git add backend/services/script_service.py backend/tests/test_fdx_parser.py
git commit -m "feat(fdx): route .fdx uploads through parse_fdx"
```

---

## Task 7: Accept `.fdx` in the frontend upload UI

**Files:**
- Modify: `frontend/src/components/script/DropZone.jsx`

**Interfaces:**
- No JS interface change; `onFileSelect` still receives a single `File`. The backend routes by extension.

- [ ] **Step 1: Update the dropzone accept config and copy**

In `frontend/src/components/script/DropZone.jsx`, change the `accept` map (lines 15-17) to include FDX:

```jsx
        accept: {
            'application/pdf': ['.pdf'],
            'application/xml': ['.fdx'],
            'text/xml': ['.fdx'],
        },
```

Update the reject message (line 33):

```jsx
                        <p className="dropzone-text error">PDF or Final Draft (.fdx) files only, please</p>
```

Update the subtitle (line 48):

```jsx
                        <p className="dropzone-subtitle">
                            Drag and drop a PDF or Final Draft (.fdx) file here, or click to browse
                        </p>
```

Update the hint (line 51):

```jsx
                        <div className="dropzone-hint">
                            Supports Screenplay PDFs and Final Draft .fdx (max 10MB)
                        </div>
```

- [ ] **Step 2: Verify the build/lint passes**

Run: `cd frontend && npm run lint`
Expected: no new lint errors in `DropZone.jsx`.

- [ ] **Step 3: Manual smoke check**

Run: `cd frontend && npm run dev`, open the upload screen, confirm a `.fdx` file is accepted by the dropzone (not rejected) and a `.pdf` still is too.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/script/DropZone.jsx
git commit -m "feat(fdx): accept Final Draft .fdx in upload dropzone"
```

---

## Task 8 (Optional / follow-up): Final Draft Tagger breakdown seeds

> Ship only after a real Tagger-tagged `.fdx` sample confirms the XML shape. This task is pure parsing + tests; persistence into the AI/scenes flow is a separate follow-up because breakdown data lives on the `scenes` table populated by the AI worker (`services/analysis_worker.py`), not on `scene_candidates`. Without a confirmed sample, skip this task — core structure + speaker import is complete after Task 7.

**Files:**
- Modify: `backend/services/fdx_parser.py`
- Test: `backend/tests/test_fdx_parser.py`

**Interfaces:**
- Produces: `_extract_tagger_tags(file_path: str) -> dict[str, dict[str, list[str]]]` mapping scene number → `{category: [values]}` (e.g. `{"1": {"Cast Members": ["JOHN"], "Props": ["COFFEE CUP"]}}`). Returns `{}` when no Tagger data is present.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_fdx_parser.py`. Use a fixture built from a REAL Tagger-tagged sample; the XML below is a placeholder shape that MUST be corrected against the actual sample before implementing:

```python
from services.fdx_parser import _extract_tagger_tags


def test_extract_tagger_tags_returns_empty_when_absent(tmp_path):
    path = _write_fdx(tmp_path, MINIMAL_FDX)  # MINIMAL_FDX has no tagger data
    assert _extract_tagger_tags(path) == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_fdx_parser.py::test_extract_tagger_tags_returns_empty_when_absent -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write minimal implementation (graceful empty default)**

Add to `backend/services/fdx_parser.py`:

```python
def _extract_tagger_tags(file_path: str):
    """Extract Final Draft Tagger breakdown tags keyed by scene number.

    Returns {} when the file has no Tagger data. The exact FDX Tagger element
    names vary by Final Draft version and MUST be confirmed against a real
    tagged sample before extending this beyond the empty default.
    """
    tree = ET.parse(file_path)
    root = tree.getroot()
    tagger = root.find("TagData")  # PLACEHOLDER element name — confirm vs sample
    if tagger is None:
        return {}
    result = {}
    # TODO(after sample): walk tagger categories into {scene: {category: [values]}}
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_fdx_parser.py::test_extract_tagger_tags_returns_empty_when_absent -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/fdx_parser.py backend/tests/test_fdx_parser.py
git commit -m "feat(fdx): tagger tag extraction scaffold (empty default)"
```

---

## Self-Review

**Spec coverage:**
- Architecture & routing (spec §1) → Task 6.
- FDX extraction: scene boundaries, numbers, text, speakers, transitions/shot, page/eighths (spec §2) → Tasks 1–5. (Transitions/shot_type: `SceneCandidate` defaults `transitions=[]`/`shot_type=None` are left as-is; FDX `Transition` paragraphs are captured in scene text. Explicit transition-column population is not required by the core goal and is omitted per YAGNI; note this to the reviewer.)
- Tagger data (spec §3) → Task 8 (optional, gated on a real sample).
- Metadata (spec §4) → Task 4.
- Synthetic pages (spec §4) → Task 4.
- Frontend (spec §4) → Task 7.
- Testing (spec §4) → tests in Tasks 1–6, plus Task 8.

**Security:** FDX uploads are untrusted. All XML parsing goes through `defusedxml` (Global Constraints + Task 1 Step 0), closing XXE and billion-laughs vectors. The malformed-file risk from the spec is handled by the existing `upload_script` try/except returning a 500 with the error message.

**Placeholder scan:** The only intentional placeholder is the Tagger element name in Task 8, which is explicitly gated on obtaining a real sample and defaults to a safe empty result. All other steps contain complete code.

**Type consistency:** `parse_fdx` returns `(pages, full_text, candidates, metadata)` consistently across Tasks 5 and 6. `_build_scenes` returns `(candidates, full_text)` consistently across Tasks 3 and 5. `SceneCandidate`, `PageData`, `compute_content_hash`, `detect_scene_headers`, `assign_scene_numbers`, `ExtractionStatus` are all imported from `services.extraction_pipeline` as they exist there. `calculate_eighths_from_content` convention (55 lines/page) is applied via the `LINES_PER_PAGE` constant.

**Note on transitions:** `SceneCandidate.__post_init__` initializes `transitions=[]` and `shot_type=None`, so constructing candidates without those kwargs is valid.

---

## REVISION (2026-07-09, post-final-review): correct the integration target

**Defect found by final review:** Tasks 1–6 built a correct FDX parser but wired routing into `process_script_v2` / `POST /api/upload_script` (`script_bp`), which is **dead code**. The live upload is `POST /api/upload` → `backend/routes/supabase_routes.py::upload_script` (Supabase/Postgres, `pdfplumber`, storage upload, `detect_and_create_scenes_v2`). The parser core (fdx_parser.py, Tasks 1–5) is sound and retained; only the output shape and integration point change.

**Live-path contracts (verified):**
- Scene detection consumes **`ParsedScene`** objects (from `services.screenplay_parser`) — fields: `scene_number_original, scene_order, int_ext, setting, time_of_day, page_start, page_end, text_start, text_end, content_hash, scene_text, location_hierarchy, speakers (dict), shot_type, transitions, parse_method`.
- `upload_script` needs `pages_data` as `list[{'page_number': int, 'text': str}]`, a `full_text` string, and a `metadata` dict read via `.get()` with keys among `title, writers, draft_version, based_on, production_company, phone, email, address, copyright, wga_registration` (missing keys → `None`, so FDX supplies only `title` + `writers`).
- `get_user_id()` (middleware) and `@optional_auth` already decorate the route — unchanged.

### Task R1: Retarget FDX parser output to the live-path shapes

**Files:** Modify `backend/services/fdx_parser.py`, `backend/tests/test_fdx_parser.py`. Revert the dead-code edit in `backend/services/script_service.py` (remove the `_is_fdx` helper + `.fdx` routing added in Task 6 — it targeted dead code).

**Changes:**
- Import `ParsedScene` and `_parse_location_hierarchy` from `services.screenplay_parser`.
- `_build_scenes` now emits `ParsedScene` objects (not `SceneCandidate`): set `scene_text` (already computed), `location_hierarchy=_parse_location_hierarchy(setting)`, `speakers`, `parse_method="fdx"`; drop the `status` field. Remove now-unused `SceneCandidate`/`ExtractionStatus` imports (keep `detect_scene_headers`, `compute_content_hash`, `assign_scene_numbers`).
- `_extract_fdx_metadata` returns the live-route shape: `{'title': <first title-page line>, 'writers': <author or None>}`. (Rename the author key from `writer_name` → `writers`.)
- Add `_is_fdx(filename) -> bool` here (canonical home) — `os.path.splitext(filename)[1].lower() == ".fdx"`.
- Add `parse_fdx_upload(file_path) -> (pages_data, full_text, metadata, parsed_scenes)`: `pages_data` is `list[{'page_number','text'}]` dicts (from `_synthesize_pages`, converted to dicts, or a dict-returning helper); `parsed_scenes` is the `_build_scenes` list; `metadata` from `_extract_fdx_metadata`. Remove the old `parse_fdx` (SceneCandidate/PageData variant) — it fed only the dead path.
- Update tests to the new shapes: `metadata['writers']`, `ParsedScene` fields incl. `.scene_text`/`.location_hierarchy`, `pages_data` dicts, `parse_fdx_upload` end-to-end, and `_is_fdx`. Keep `_read_fdx`/`_normalize_speaker`/`_build_scenes` behavior tests (adjust type expectations).

**Verify:** `cd backend && ./venv/bin/python -m pytest tests/test_fdx_parser.py -v` (all green); `./venv/bin/python -c "import services.fdx_parser"`; confirm `script_service.py` reverted cleanly (`./venv/bin/python -c "import services.script_service"`).

### Task R2: Wire `.fdx` into the live Supabase upload path

**Files:** Modify `backend/routes/supabase_routes.py`. Add a test `backend/tests/test_fdx_route.py`.

**Changes:**
- **Refactor** `detect_and_create_scenes_v2`: extract the scene-record-building + batch-insert body (current lines ~619–732) into a new module function `create_scenes_from_parsed(script_id, parsed_scenes, full_text, pages_data, parse_meta) -> (scenes_created, parse_meta)`. `detect_and_create_scenes_v2` keeps its `parse_screenplay(pdf_path)` call + fallbacks, then delegates to `create_scenes_from_parsed`. PDF behavior byte-identical.
- **`upload_script`:** detect FDX via `_is_fdx(filename)` (import from `services.fdx_parser`).
  - Temp file suffix `.fdx` (vs `.pdf`); storage `content-type` `application/xml` (vs `application/pdf`).
  - FDX branch: `pages_data, full_text, metadata, parsed_scenes = parse_fdx_upload(tmp_path)`; `total_pages = len(pages_data)`; build the same `script_data` dict (title/writers via the shared `metadata.get(...)` calls — other keys resolve to None); insert script + `script_pages` exactly as the PDF branch does; then `scenes_detected, parse_meta = create_scenes_from_parsed(script_id, parsed_scenes, full_text, pages_data, {'parse_method': 'fdx'})`.
  - PDF branch: unchanged (still `pdfplumber` + `detect_and_create_scenes_v2`).
- **Test** (`test_fdx_route.py`): monkeypatch `supabase_routes.supabase` with a stub that records `.table(name).insert(rows).execute()` calls, then call `create_scenes_from_parsed(...)` with a small hand-built `ParsedScene` list and assert the `scenes`/`scene_candidates` rows have correct `scene_number`, `speakers` (list for scenes, dict for candidates), `parse_method='fdx'`, and non-zero `page_length_eighths`. This exercises the load-bearing new persistence path without a real DB.

**Verify:** `cd backend && ./venv/bin/python -m pytest tests/test_fdx_route.py tests/test_fdx_parser.py -v`; `./venv/bin/python -c "import routes.supabase_routes"`; full suite `./venv/bin/python -m pytest tests/ -v` (no regressions).
