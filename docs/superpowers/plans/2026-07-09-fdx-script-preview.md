# FDX Script Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `.fdx`-uploaded scripts a faithful, scene-synced preview by generating a screenplay-formatted PDF from the FDX and serving it through the existing PDF viewer.

**Architecture:** A new backend module `services/fdx_preview.py` renders the FDX's typed paragraphs into screenplay HTML, converts it to PDF with WeasyPrint, and reads back the real page each scene lands on (via `id="scene-{id}"` page anchors). The PDF is stored in the `scripts` bucket, `get_pdf_url` serves it for FDX scripts, and each scene's `page_start`/`page_end` is updated to the generated pagination — so the existing `page-mapping` endpoint and `PdfViewerPanel` work with no frontend change.

**Tech Stack:** Python 3.13, Flask, WeasyPrint 62.3 (already installed, the report renderer), Supabase (Postgres + Storage), pytest. Bundled Courier Prime font.

## Global Constraints

- No frontend changes. Reuse `PdfViewerPanel`, `getPdfUrl`, `getPageMapping` unchanged.
- Preview shows the **original** script; it is not regenerated on later scene edits (matches PDF-viewer behavior).
- Reuse `fdx_parser._read_fdx` to recover typed paragraphs — do not re-implement FDX parsing, and parse only via `defusedxml` (already how `_read_fdx` works).
- Scene page anchors use the exact id form `scene-{scene_id}` (scene_id is the Supabase `scenes.id` UUID string).
- Preview generation is **best-effort**: any failure must never fail the upload or the `get_pdf_url` request beyond the existing error path.
- WeasyPrint via `from weasyprint import HTML, CSS` (same import as `services/report_service.py`).
- Backend tests run from `backend/` with `./venv/bin/python -m pytest tests/ -v`. Test files put backend on the path via `sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))`.
- Screenplay CSS target: US Letter, 12pt monospace, ~55 lines/page, margins 1in top/bottom/right + 1.5in left.
- Stage only the files each task names (explicit `git add` paths; never `git add .`/`-a` — untracked `.claude/`, `.superpowers/`, and scratch dirs must stay out).

---

## File Structure

- **Create** `backend/services/fdx_preview.py` — FDX→HTML→PDF rendering + scene→page capture. All preview-rendering logic.
- **Create** `backend/assets/fonts/CourierPrime-Regular.ttf`, `CourierPrime-Bold.ttf` — bundled screenplay font (SIL OFL).
- **Create** `backend/tests/test_fdx_preview.py` — unit/integration tests for the module.
- **Modify** `backend/routes/supabase_routes.py` — `store_fdx_preview()` + `_lazy_generate_fdx_preview()` helpers; hook into `upload_script` FDX branch; extend `get_pdf_url`.
- **Modify** `backend/tests/test_fdx_route.py` — route-level tests for preview storage + serving.
- **Migration** — add nullable `scripts.preview_pdf_path` column (Supabase).

---

## Task 1: Add `scripts.preview_pdf_path` column

**Files:**
- Migration only (Supabase Postgres).

**Interfaces:**
- Produces: a nullable `text` column `preview_pdf_path` on `scripts`, read/written by Tasks 5–6.

> **Note for the controller:** this is a production schema change. Apply it via the Supabase MCP `apply_migration` tool (additive, nullable, non-breaking — no backfill). Do not delegate the apply to an unattended subagent without confirmation.

- [ ] **Step 1: Apply the migration**

Apply via Supabase MCP `apply_migration` with name `add_scripts_preview_pdf_path` and SQL:

```sql
ALTER TABLE scripts ADD COLUMN IF NOT EXISTS preview_pdf_path text;
```

- [ ] **Step 2: Verify the column exists**

Run (Supabase MCP `execute_sql`):

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'scripts' AND column_name = 'preview_pdf_path';
```
Expected: one row — `preview_pdf_path | text | YES`.

- [ ] **Step 3: Record the migration**

No code commit required (schema-only). Note the applied migration name in the task report.

---

## Task 2: Screenplay HTML + CSS renderer (`render_fdx_html`)

**Files:**
- Create: `backend/services/fdx_preview.py`
- Create: `backend/assets/fonts/CourierPrime-Regular.ttf`, `backend/assets/fonts/CourierPrime-Bold.ttf`
- Test: `backend/tests/test_fdx_preview.py`

**Interfaces:**
- Produces:
  - `render_fdx_html(render_scenes: list[dict]) -> str` — `render_scenes` items are `{"scene_id": str, "paragraphs": [{"type": str, "text": str}, ...]}` (first paragraph is the Scene Heading). Returns a full HTML document; each scene heading is `<div class="scene-heading" id="scene-{scene_id}">`.
  - `screenplay_css() -> str` — the screenplay stylesheet string (US Letter, 12pt monospace, standard margins).

- [ ] **Step 0: Bundle the Courier Prime font**

Download the SIL OFL Courier Prime TTFs into `backend/assets/fonts/` (create the dir):

Run:
```bash
mkdir -p backend/assets/fonts
curl -fsSL -o backend/assets/fonts/CourierPrime-Regular.ttf \
  https://github.com/quoteunquoteapps/CourierPrime/raw/master/fonts/ttf/CourierPrime-Regular.ttf
curl -fsSL -o backend/assets/fonts/CourierPrime-Bold.ttf \
  https://github.com/quoteunquoteapps/CourierPrime/raw/master/fonts/ttf/CourierPrime-Bold.ttf
ls -la backend/assets/fonts/
```
Expected: two `.ttf` files, each > 30 KB. If the download is blocked in your environment, obtain the two files manually (Courier Prime, Google Fonts / SIL OFL) and place them at these exact paths. The CSS falls back to system monospace if the files are absent, so tests still pass — but production fidelity needs them committed.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_fdx_preview.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_fdx_preview.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.fdx_preview'`.

- [ ] **Step 3: Write minimal implementation**

Create `backend/services/fdx_preview.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_fdx_preview.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/services/fdx_preview.py backend/tests/test_fdx_preview.py backend/assets/fonts/CourierPrime-Regular.ttf backend/assets/fonts/CourierPrime-Bold.ttf
git commit -m "feat(fdx-preview): screenplay HTML/CSS renderer + bundled font"
```

---

## Task 3: Correlate FDX paragraphs to scene rows (`build_render_scenes`)

**Files:**
- Modify: `backend/services/fdx_preview.py`
- Test: `backend/tests/test_fdx_preview.py`

**Interfaces:**
- Consumes: `services.fdx_parser._read_fdx(fdx_path) -> (content_paragraphs, titlepage_paragraphs)` where each content paragraph is `{"type": str, "text": str, "number": str|None, "length": str|None}`.
- Produces: `build_render_scenes(fdx_path: str, scene_rows: list[dict]) -> list[dict]` — groups content paragraphs by Scene Heading (same order as `fdx_parser._build_scenes`) and pairs each group to a `scene_row` (which has `id` + `scene_order`) by order, returning `[{"scene_id": str(row["id"]), "paragraphs": group}, ...]`. Pairs up to `min(len(groups), len(rows))`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_fdx_preview.py`:

```python
from services.fdx_preview import build_render_scenes

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_fdx_preview.py -k build_render_scenes -v`
Expected: FAIL — `ImportError: cannot import name 'build_render_scenes'`.

- [ ] **Step 3: Write minimal implementation**

Add to `backend/services/fdx_preview.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_fdx_preview.py -k build_render_scenes -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/services/fdx_preview.py backend/tests/test_fdx_preview.py
git commit -m "feat(fdx-preview): correlate FDX paragraphs to scene rows"
```

---

## Task 4: Render PDF + capture scene→page map (`generate_fdx_preview_pdf`)

**Files:**
- Modify: `backend/services/fdx_preview.py`
- Test: `backend/tests/test_fdx_preview.py`

**Interfaces:**
- Consumes: `build_render_scenes` (Task 3), `render_fdx_html` + `screenplay_css` (Task 2), WeasyPrint (`from weasyprint import HTML, CSS`).
- Produces: `generate_fdx_preview_pdf(fdx_path: str, scene_rows: list[dict]) -> tuple[bytes, dict[str, int]]` — returns `(pdf_bytes, scene_page_map)` where `scene_page_map` maps `str(scene_id) -> 1-indexed page number` read from `document.pages[i].anchors`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_fdx_preview.py`:

```python
from services.fdx_preview import generate_fdx_preview_pdf

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_fdx_preview.py -k generate_pdf -v`
Expected: FAIL — `ImportError: cannot import name 'generate_fdx_preview_pdf'`.

- [ ] **Step 3: Write minimal implementation**

Add to `backend/services/fdx_preview.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_fdx_preview.py -v`
Expected: PASS (all tests in the file).

- [ ] **Step 5: Commit**

```bash
git add backend/services/fdx_preview.py backend/tests/test_fdx_preview.py
git commit -m "feat(fdx-preview): render PDF and capture scene page anchors"
```

---

## Task 5: Store preview + hook into upload (`store_fdx_preview`)

**Files:**
- Modify: `backend/routes/supabase_routes.py`
- Test: `backend/tests/test_fdx_route.py`

**Interfaces:**
- Consumes: `services.fdx_preview.generate_fdx_preview_pdf` (Task 4); module-global `supabase`.
- Produces: `store_fdx_preview(script_id: str, fdx_path: str) -> str | None` — fetches the script's scenes, generates the preview PDF, uploads it to `{script_id}/preview.pdf`, sets `scripts.preview_pdf_path`, updates each scene's `page_start`/`page_end` to the generated pages, and returns the storage path (or `None` if there are no scenes). Also: `upload_script` FDX branch calls it best-effort.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_fdx_route.py` (the file already defines `_FakeSupabase` with `storage`/`table`; extend it to record storage uploads and scene updates):

```python
def test_store_fdx_preview_uploads_and_updates(monkeypatch, tmp_path):
    import routes.supabase_routes as sr

    # Fake supabase that records inserts/updates/uploads and returns scenes.
    calls = {"uploads": [], "script_updates": [], "scene_updates": []}

    class Q:
        def __init__(self, table): self.table = table; self._filter = None
        def select(self, *a, **k): return self
        def eq(self, *a, **k): self._filter = a; return self
        def order(self, *a, **k): return self
        def execute(self):
            if self.table == "scenes":
                class R: data = [{"id": "s1", "scene_order": 1},
                                 {"id": "s2", "scene_order": 2}]
                return R()
            class R: data = []
            return R()
        def update(self, payload):
            (calls["script_updates"] if self.table == "scripts"
             else calls["scene_updates"]).append((self.table, payload))
            return self

    class Up:
        def upload(self, path, content, opts):
            calls["uploads"].append((path, opts)); return {}
    class St:
        def from_(self, b): return Up()
    class FS:
        storage = St()
        def table(self, name): return Q(name)

    monkeypatch.setattr(sr, "supabase", FS())
    monkeypatch.setattr(
        "services.fdx_preview.generate_fdx_preview_pdf",
        lambda fdx_path, rows: (b"%PDF-fake", {"s1": 1, "s2": 2}),
    )

    fdx = tmp_path / "x.fdx"; fdx.write_text("<FinalDraft/>", encoding="utf-8")
    path = sr.store_fdx_preview("script-9", str(fdx))

    assert path == "script-9/preview.pdf"
    assert calls["uploads"] and calls["uploads"][0][0] == "script-9/preview.pdf"
    assert calls["uploads"][0][1].get("content-type") == "application/pdf"
    # preview_pdf_path recorded on the script
    assert any(p.get("preview_pdf_path") == "script-9/preview.pdf"
               for _, p in calls["script_updates"])
    # both scenes got page_start updated to the generated pages
    starts = [p.get("page_start") for _, p in calls["scene_updates"]]
    assert 1 in starts and 2 in starts
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_fdx_route.py -k store_fdx_preview -v`
Expected: FAIL — `AttributeError: module 'routes.supabase_routes' has no attribute 'store_fdx_preview'`.

- [ ] **Step 3: Write minimal implementation**

In `backend/routes/supabase_routes.py`, add the helper (near `create_scenes_from_parsed`):

```python
def store_fdx_preview(script_id, fdx_path):
    """Generate the screenplay preview PDF for an FDX script, store it, and
    update scene page numbers to the generated pagination. Returns the storage
    path, or None if there are no scenes. Best-effort: callers wrap in try/except.
    """
    from services.fdx_preview import generate_fdx_preview_pdf

    scenes_res = supabase.table('scenes').select('id, scene_order') \
        .eq('script_id', script_id).order('scene_order').execute()
    scene_rows = scenes_res.data or []
    if not scene_rows:
        return None

    pdf_bytes, scene_page_map = generate_fdx_preview_pdf(fdx_path, scene_rows)

    preview_path = f"{script_id}/preview.pdf"
    supabase.storage.from_('scripts').upload(
        preview_path, pdf_bytes,
        {'content-type': 'application/pdf', 'upsert': 'true'}
    )
    supabase.table('scripts').update({'preview_pdf_path': preview_path}) \
        .eq('id', script_id).execute()

    ordered = sorted(scene_rows, key=lambda r: r['scene_order'])
    total_pages = max(scene_page_map.values(), default=1)
    for idx, row in enumerate(ordered):
        sid = str(row['id'])
        page_start = scene_page_map.get(sid)
        if not page_start:
            continue
        if idx + 1 < len(ordered):
            nxt = scene_page_map.get(str(ordered[idx + 1]['id']))
            page_end = max(page_start, nxt) if nxt else page_start
        else:
            page_end = max(page_start, total_pages)
        supabase.table('scenes').update({'page_start': page_start, 'page_end': page_end}) \
            .eq('id', sid).execute()

    return preview_path
```

Then hook it into the FDX branch of `upload_script`. Find (around line 415):

```python
            if is_fdx:
                scenes_detected, parse_meta = create_scenes_from_parsed(
                    script_id, parsed_scenes, full_text, pages_data, {'parse_method': 'fdx'}
                )
```

and add, immediately after that `create_scenes_from_parsed(...)` call (still inside the `if is_fdx:` block, before the `else:`):

```python
                # Best-effort: generate the screenplay preview PDF from the FDX.
                # A failure must never fail the upload.
                try:
                    store_fdx_preview(script_id, tmp_path)
                except Exception as preview_err:
                    print(f"Warning: FDX preview generation failed: {preview_err}")
```

(`tmp_path` — the `.fdx` temp file — is still valid here; it is only removed in the outer `finally`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_fdx_route.py -k store_fdx_preview -v`
Expected: PASS.

Then confirm the module imports and the suite is green:
Run: `cd backend && ./venv/bin/python -c "import routes.supabase_routes" && ./venv/bin/python -m pytest tests/ -q`
Expected: import OK; all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/supabase_routes.py backend/tests/test_fdx_route.py
git commit -m "feat(fdx-preview): generate+store preview on FDX upload"
```

---

## Task 6: Serve preview via `get_pdf_url` + lazy fallback

**Files:**
- Modify: `backend/routes/supabase_routes.py`
- Test: `backend/tests/test_fdx_route.py`

**Interfaces:**
- Consumes: `store_fdx_preview` (Task 5); module-global `supabase`.
- Produces:
  - `_lazy_generate_fdx_preview(script_id: str, fdx_storage_path: str) -> str | None` — downloads the `.fdx` from storage to a temp file, calls `store_fdx_preview`, returns the preview path (or `None` on failure).
  - `get_pdf_url` now selects `preview_pdf_path`, serves `preview_pdf_path or file_path`, and for FDX scripts with no `preview_pdf_path` lazily generates one first.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_fdx_route.py`:

```python
def test_get_pdf_url_prefers_preview_path(monkeypatch):
    import routes.supabase_routes as sr
    try:
        import app as app_module
    except Exception:
        import pytest; pytest.skip("Flask app requires env vars")

    class Q:
        def __init__(self, table): self.table = table
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def single(self): return self
        def execute(self):
            class R: data = {"file_path": "sid/orig.fdx", "file_name": "orig.fdx",
                             "title": "T", "preview_pdf_path": "sid/preview.pdf"}
            return R()
    class Signed:
        def create_signed_url(self, path, ttl):
            return {"signedURL": f"https://signed/{path}"}
    class St:
        def from_(self, b): return Signed()
    class FS:
        storage = St()
        def table(self, name): return Q(name)

    monkeypatch.setattr(sr, "supabase", FS())
    client = app_module.app.test_client()
    r = client.get("/api/scripts/sid/pdf-url")
    assert r.status_code == 200
    assert r.get_json()["pdf_url"] == "https://signed/sid/preview.pdf"


def test_get_pdf_url_lazy_generates_for_fdx(monkeypatch):
    import routes.supabase_routes as sr
    try:
        import app as app_module
    except Exception:
        import pytest; pytest.skip("Flask app requires env vars")

    signed = {}
    class Q:
        def __init__(self, table): self.table = table
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def single(self): return self
        def execute(self):
            class R: data = {"file_path": "sid/orig.fdx", "file_name": "orig.fdx",
                             "title": "T", "preview_pdf_path": None}
            return R()
    class Signed:
        def create_signed_url(self, path, ttl):
            signed["path"] = path
            return {"signedURL": f"https://signed/{path}"}
    class St:
        def from_(self, b): return Signed()
    class FS:
        storage = St()
        def table(self, name): return Q(name)

    monkeypatch.setattr(sr, "supabase", FS())
    monkeypatch.setattr(sr, "_lazy_generate_fdx_preview",
                        lambda script_id, fdx_path: "sid/preview.pdf")
    client = app_module.app.test_client()
    r = client.get("/api/scripts/sid/pdf-url")
    assert r.status_code == 200
    assert signed["path"] == "sid/preview.pdf"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_fdx_route.py -k "pdf_url" -v`
Expected: FAIL — the current `get_pdf_url` neither selects `preview_pdf_path` nor calls a lazy generator (`_lazy_generate_fdx_preview` missing / preview path ignored).

- [ ] **Step 3: Write minimal implementation**

In `backend/routes/supabase_routes.py`, add the lazy helper (near `store_fdx_preview`):

```python
def _lazy_generate_fdx_preview(script_id, fdx_storage_path):
    """Download the stored .fdx and generate+store its preview PDF on demand.
    Returns the preview storage path, or None on failure."""
    if not fdx_storage_path:
        return None
    import tempfile
    try:
        data = supabase.storage.from_('scripts').download(fdx_storage_path)
        fd, tmp = tempfile.mkstemp(suffix='.fdx')
        try:
            os.write(fd, data)
            os.close(fd)
            return store_fdx_preview(script_id, tmp)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    except Exception as e:
        print(f"Lazy FDX preview generation failed: {e}")
        return None
```

Then update `get_pdf_url` (around line 2537-2560). Replace the select + file_path resolution + signing with:

```python
        # Get the file paths from the script record
        result = supabase.table('scripts') \
            .select('file_path, file_name, title, preview_pdf_path') \
            .eq('id', script_id).single().execute()

        if not result.data:
            return jsonify({'error': 'Script not found'}), 404

        file_path = result.data.get('file_path')
        file_name = (result.data.get('file_name') or '')
        serve_path = result.data.get('preview_pdf_path')

        # FDX scripts: generate the screenplay preview PDF on first request.
        if not serve_path and file_name.lower().endswith('.fdx'):
            serve_path = _lazy_generate_fdx_preview(script_id, file_path)

        serve_path = serve_path or file_path
        if not serve_path:
            return jsonify({'error': 'No file associated with this script'}), 404

        # Generate a signed URL valid for 1 hour
        signed_url_response = supabase.storage.from_('scripts').create_signed_url(
            serve_path,
            3600  # 1 hour expiry
        )
```

(The rest of `get_pdf_url` — the `signedURL` check and the `return jsonify({...})` — is unchanged.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_fdx_route.py -k "pdf_url" -v`
Expected: PASS (2 tests; or SKIPPED if the app can't import for lack of env — acceptable locally it imports).

Then the full suite:
Run: `cd backend && ./venv/bin/python -m pytest tests/ -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/supabase_routes.py backend/tests/test_fdx_route.py
git commit -m "feat(fdx-preview): serve preview PDF via get_pdf_url with lazy fallback"
```

---

## Self-Review

**Spec coverage:**
- Architecture / no-frontend-change / reuse existing endpoints → Tasks 5–6 (serve through `get_pdf_url`, scene pages feed existing `page-mapping`).
- `render_fdx_html` + `screenplay_css` + Courier Prime font (spec §"services/fdx_preview.py", "Font asset") → Task 2.
- `build_render_scenes` (spec "Scene text source") → Task 3.
- `generate_fdx_preview_pdf` + anchor→page capture (spec §3) → Task 4.
- Upload integration best-effort (spec "Upload integration") → Task 5.
- `preview_pdf_path` column (spec "Schema migration") → Task 1.
- `get_pdf_url` serve + lazy fallback (spec "Serving") → Task 6.
- Scene page-number update feeding sync (spec §3, "Data Flow") → Task 5 (`store_fdx_preview` updates `page_start`/`page_end`).
- Testing (spec "Testing") → Tasks 2–6 tests.

**Placeholder scan:** No TBD/TODO. The only non-code setup step is the font download (Task 2 Step 0), which has an explicit command and a documented manual fallback; the CSS degrades to system monospace if absent so tests don't depend on it.

**Type consistency:** `generate_fdx_preview_pdf(fdx_path, scene_rows) -> (bytes, {scene_id:int})` used consistently in Tasks 4–5. `build_render_scenes(fdx_path, scene_rows) -> [{scene_id, paragraphs}]` matches `render_fdx_html`'s input in Tasks 2–3. `store_fdx_preview(script_id, fdx_path) -> str|None` and `_lazy_generate_fdx_preview(script_id, fdx_storage_path) -> str|None` consistent across Tasks 5–6. Anchor id form `scene-{scene_id}` consistent (Tasks 2 render, 4 capture).

**Note on WeasyPrint page anchors:** `page.anchors` is a dict keyed by the element `id`; iterating yields the ids. Verified against WeasyPrint 62.3 (`{'a': (x,y)}` per page). If a future WeasyPrint changes this shape, Task 4's capture is the single place to adjust.
