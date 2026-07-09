"""
FDX (Final Draft) import adapter.

Reads Final Draft .fdx XML and emits the (pages_data, full_text, metadata,
parsed_scenes) contract that the live upload path consumes for PDFs. FDX is
structured, so scene boundaries, scene numbers, and speakers are read directly
rather than inferred.
"""

import os
import re

# defusedxml, NOT stdlib ElementTree: FDX uploads are untrusted (XXE / billion-laughs).
import defusedxml.ElementTree as ET

from services.extraction_pipeline import (
    detect_scene_headers,
    compute_content_hash,
    assign_scene_numbers,
)
from services.screenplay_parser import ParsedScene, _parse_location_hierarchy

LINES_PER_PAGE = 55


_SPEAKER_EXTENSION_RE = re.compile(r"\s*\((?:CONT'D|CONTD|V\.?O\.?|O\.?S\.?|O\.?C\.?)\)\s*$", re.IGNORECASE)

_AUTHOR_RE = re.compile(r"^(?:written\s+by|by)\s+(.+)$", re.IGNORECASE)


def _is_fdx(filename: str) -> bool:
    """True when the uploaded filename is a Final Draft .fdx file."""
    return os.path.splitext(filename)[1].lower() == ".fdx"


def _normalize_speaker(name: str) -> str:
    """Normalize a character cue: uppercase, trimmed, extensions removed."""
    cleaned = _SPEAKER_EXTENSION_RE.sub("", name.strip())
    return cleaned.strip().upper()


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
            groups[-1]["body"].append(para)
        # paragraphs before the first heading are ignored (title/front matter)

    scenes = []
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

        scenes.append(ParsedScene(
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
            scene_text=scene_text,
            location_hierarchy=_parse_location_hierarchy(parsed["setting"]),
            speakers=speakers,
            parse_method="fdx",
        ))

    return scenes, full_text


def _synthesize_page_dicts(full_text: str):
    """Chunk full_text into ~55-line {'page_number', 'text'} dicts."""
    if not full_text.strip():
        return []
    lines = full_text.split("\n")
    pages = []
    for page_num, start in enumerate(range(0, len(lines), LINES_PER_PAGE), start=1):
        page_text = "\n".join(lines[start:start + LINES_PER_PAGE])
        pages.append({
            "page_number": page_num,
            "text": page_text,
        })
    return pages


def _extract_fdx_metadata(titlepage_paragraphs):
    """Best-effort metadata from the FDX title page."""
    meta = {"title": None, "writers": None}
    for para in titlepage_paragraphs:
        text = para["text"].strip()
        if not text:
            continue
        if meta["title"] is None:
            meta["title"] = text
        m = _AUTHOR_RE.match(text)
        if m and not meta["writers"]:
            meta["writers"] = m.group(1).strip()
    return meta


def parse_fdx_upload(file_path: str):
    """Parse an .fdx into the live-upload contract:
    (pages_data, full_text, metadata, parsed_scenes).
    pages_data is a list of {'page_number': int, 'text': str} dicts.
    parsed_scenes is a list of ParsedScene. metadata has 'title'/'writers'.
    """
    content_paras, titlepage_paras = _read_fdx(file_path)
    parsed_scenes, full_text = _build_scenes(content_paras)
    pages_data = _synthesize_page_dicts(full_text)
    metadata = _extract_fdx_metadata(titlepage_paras)
    return pages_data, full_text, metadata, parsed_scenes
