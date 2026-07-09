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
