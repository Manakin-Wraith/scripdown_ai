"""FDX script preview: render Final Draft scenes into a screenplay-formatted
PDF (via WeasyPrint) and capture the real page each scene lands on.

The preview flows through the existing PDF viewer / get_pdf_url / page-mapping
machinery, so no frontend changes are needed.
"""
import html as _html
import os

_FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
_FONT_REGULAR = os.path.abspath(os.path.join(_FONT_DIR, "CourierPrime-Regular.ttf"))
_FONT_BOLD = os.path.abspath(os.path.join(_FONT_DIR, "CourierPrime-Bold.ttf"))

# Map FDX paragraph type -> CSS class. Unknown types render as action.
_TYPE_CLASS = {
    "Scene Heading": "scene-heading",
    "Action": "action",
    "Character": "character",
    "Parenthetical": "parenthetical",
    "Dialogue": "dialogue",
    "Transition": "transition",
    "Shot": "action",
    "General": "action",
}


def screenplay_css() -> str:
    """Industry-standard screenplay stylesheet (US Letter, 12pt Courier)."""
    face = ""
    if os.path.exists(_FONT_REGULAR):
        face += (
            "@font-face { font-family: 'Courier Prime'; font-weight: normal; "
            f"src: url('file://{_FONT_REGULAR}'); }}\n"
        )
    if os.path.exists(_FONT_BOLD):
        face += (
            "@font-face { font-family: 'Courier Prime'; font-weight: bold; "
            f"src: url('file://{_FONT_BOLD}'); }}\n"
        )
    return face + """
@page { size: Letter; margin: 1in 1in 1in 1.5in; }
body { font-family: 'Courier Prime', 'Courier New', Courier, monospace;
       font-size: 12pt; line-height: 1; color: #000; }
.scene-heading { text-transform: uppercase; font-weight: bold;
                 margin: 1em 0 0.5em; page-break-after: avoid; }
.action { margin: 0 0 1em; white-space: pre-wrap; }
.character { margin: 1em 0 0 2.2in; text-transform: uppercase; }
.parenthetical { margin: 0 0 0 1.6in; }
.dialogue { margin: 0 1.5in 0 1in; }
.transition { text-align: right; text-transform: uppercase; margin: 1em 0; }
.dual-dialogue { display: flex; gap: 0.5in; }
.dual-col { flex: 1; }
"""


def render_fdx_html(render_scenes) -> str:
    """Render typed scene paragraphs into a screenplay HTML document.

    render_scenes: [{"scene_id": str, "paragraphs": [{"type","text"}, ...]}]
    Each scene's first paragraph (the heading) carries id="scene-{scene_id}".
    """
    parts = ["<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>"]
    for scene in render_scenes:
        sid = scene["scene_id"]
        for idx, para in enumerate(scene.get("paragraphs", [])):
            cls = _TYPE_CLASS.get(para.get("type"), "action")
            text = _html.escape(para.get("text", ""))
            if idx == 0:
                # heading paragraph is the page anchor for this scene
                parts.append(f'<div class="{cls}" id="scene-{sid}">{text}</div>')
            else:
                parts.append(f'<div class="{cls}">{text}</div>')
    parts.append("</body></html>")
    return "".join(parts)


def build_render_scenes(fdx_path: str, scene_rows):
    """Recover typed paragraphs from the .fdx and pair them to scene rows."""
    from services.fdx_parser import _read_fdx

    content_paras, _ = _read_fdx(fdx_path)

    # Group paragraphs by Scene Heading (same grouping as fdx_parser._build_scenes).
    groups = []
    for para in content_paras:
        if para["type"] == "Scene Heading":
            groups.append([para])
        elif groups:
            groups[-1].append(para)

    rows = sorted(scene_rows, key=lambda r: r["scene_order"])
    render = []
    for group, row in zip(groups, rows):
        render.append({"scene_id": str(row["id"]), "paragraphs": group})
    return render


def generate_fdx_preview_pdf(fdx_path: str, scene_rows):
    """Render the FDX scenes to a screenplay PDF and capture scene->page.

    Returns (pdf_bytes, {scene_id: 1-indexed page number}).
    """
    from weasyprint import HTML, CSS

    render_scenes = build_render_scenes(fdx_path, scene_rows)
    html_str = render_fdx_html(render_scenes)

    document = HTML(string=html_str).render(stylesheets=[CSS(string=screenplay_css())])
    pdf_bytes = document.write_pdf()

    scene_page_map = {}
    for page_index, page in enumerate(document.pages, start=1):
        for anchor in page.anchors:            # page.anchors is {anchor_id: (x, y)}
            if anchor.startswith("scene-"):
                sid = anchor[len("scene-"):]
                scene_page_map.setdefault(sid, page_index)  # first page it appears on
    return pdf_bytes, scene_page_map
