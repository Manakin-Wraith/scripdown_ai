# FDX Script Preview — Design

**Date:** 2026-07-09
**Status:** Approved design, ready for implementation planning
**Scope:** Give `.fdx`-uploaded scripts a faithful, scene-synced preview in the existing viewer panel by generating a screenplay-formatted PDF from the FDX.

## Problem

FDX import (shipped 2026-07-09) stores the uploaded file as `.fdx`
(`application/xml`). The viewer panel (`frontend/src/components/pdf/PdfViewerPanel.jsx`)
renders a **PDF** fetched via `get_pdf_url` (a signed URL to the stored file).
For an FDX script that stored file is XML, which the PDF `<Viewer>` cannot
render — so FDX scripts have a broken/empty preview. PDF-sourced scripts are
unaffected.

## Goal

Reproduce the original Final Draft document look for FDX scripts, with the same
UX as the PDF viewer — including scene-selection → jump-to-page sync — by
generating a real, screenplay-formatted PDF from the FDX and routing it through
the existing viewer, `get_pdf_url`, and `page-mapping` machinery.

**Guiding principle:** the preview shows the *original* script. Like the PDF
viewer (which shows the originally-uploaded PDF), it does not re-render after
later scene edits/reorders/omits. That is by design, not a gap.

## Non-Goals

- No preview regeneration on scene edits/reorder/omit (v1 shows the original,
  matching PDF-viewer behavior).
- No new frontend component or endpoint. The feature reuses `PdfViewerPanel`,
  `getPdfUrl`, and `getPageMapping` unchanged.
- No change to PDF-sourced scripts' behavior.
- FDX Tagger ingestion remains separate (see `docs/BACKLOG.md`).

## Approach — Generate a PDF from the FDX (chosen)

Turn the FDX's parsed scenes into screenplay-formatted HTML, render it to PDF
with WeasyPrint (already the report renderer), capture the real page each scene
lands on, store the PDF, and update each scene's page numbers to the generated
pagination. The existing viewer/endpoints then work with essentially zero
frontend change.

Rejected (per the "faithful Final Draft look" requirement): a formatted
text/HTML view rendered from `scene_text` (lower fidelity, no true pagination),
and client-side conversion.

## Verified Facts (grounding)

- `get_pdf_url` (`backend/routes/supabase_routes.py:2525`) signs
  `scripts.file_path` and returns `{pdf_url, file_name, title, expires_in}`.
- `/api/scripts/<id>/page-mapping` returns `{scene_pages: {scene_id: page},
  page_to_scenes: {page: [scene_id]}}`, derived from each scene's `page_start`.
  `PdfViewerPanel` consumes it via `SceneViewer` (`currentPdfPage`).
- The `/scenes` endpoint already exposes per-scene `id, scene_order, int_ext,
  setting, time_of_day, scene_number, scene_text, page_start, page_end`.
- WeasyPrint 62.3 is installed; `HTML(string=...).render().pages[i].anchors`
  returns `{anchor_id: (x, y)}` for anchors present on each page — verified.

## Architecture

New backend module: `backend/services/fdx_preview.py`. Frontend: unchanged.

```
.fdx upload (existing upload_script)
  → parse_fdx_upload + create_scenes_from_parsed (existing)
  → fetch created scenes (id, scene_order)
  → fdx_preview.generate_fdx_preview_pdf(fdx_path, scene_rows)
        → build_render_scenes(fdx_path, scene_rows)  # typed paragraphs + scene_id
        → render_fdx_html(render_scenes)             # screenplay HTML, one anchor per scene
        → WeasyPrint render → (pdf_bytes, {scene_id: page})
  → upload pdf_bytes to storage {script_id}/preview.pdf
  → set scripts.preview_pdf_path
  → update each scene.page_start/page_end to generated pages
  (all best-effort; failure never fails the upload)

viewer (unchanged):
  get_pdf_url -> signs preview_pdf_path or file_path
  page-mapping -> derives from updated page_start
  PdfViewerPanel -> renders the PDF, jumps to scene page
```

## Component Detail

### `services/fdx_preview.py`

- `render_fdx_html(render_scenes: list[dict]) -> str`
  Build a full HTML document of screenplay elements. Each `render_scene` is
  `{"scene_id": str, "paragraphs": [{"type": str, "text": str}, ...]}` (the
  heading is the group's first paragraph). Each scene starts with
  `<div class="scene-heading" id="scene-{scene_id}">`, and the body is rendered
  by paragraph type (action, character, dialogue, parenthetical, transition,
  dual dialogue).

- `_screenplay_css() -> str`
  US Letter; 12pt **Courier Prime** via `@font-face` (bundled `.ttf`);
  page margins 1″ top/bottom/right, 1.5″ left; element rules:
  - scene heading: uppercase, bold, blank line before
  - action: full text width
  - character: left indent ~2.2″, uppercase
  - dialogue: left indent ~1″, right indent ~1.5″
  - parenthetical: left indent ~1.6″
  - transition: right-aligned, uppercase
  - dual dialogue: two side-by-side columns
  Target ~55 lines/page (industry standard) so pagination is faithful.

- `build_render_scenes(fdx_path: str, scene_rows: list[dict]) -> list[dict]`
  Recovers typed paragraphs from the original `.fdx` and pairs them to created
  scene rows. Re-parses via `fdx_parser._read_fdx` and groups paragraphs by
  scene (same grouping as `_build_scenes`); correlates each group to a
  `scene_row` by position/`scene_order`; returns the `render_scenes` list
  (`{"scene_id", "paragraphs"}`) that `render_fdx_html` consumes.

- `generate_fdx_preview_pdf(fdx_path: str, scene_rows: list[dict]) -> tuple[bytes, dict[str, int]]`
  Calls `build_render_scenes` → `render_fdx_html` → WeasyPrint. Writes PDF
  bytes, and scans `document.pages[i].anchors` for each `scene-{scene_id}`
  anchor to build `{scene_id: page_number}` (1-indexed). Returns
  `(pdf_bytes, scene_page_map)`.

**Scene text source.** `render_fdx_html` needs typed paragraphs (heading vs
action vs character vs dialogue) to style correctly. The stored `scene_text` is
a flat newline-joined string that loses paragraph types, so generation re-parses
the original `.fdx` (via `build_render_scenes`) rather than reading `scene_text`.
Scene rows carry `id` + `scene_order` for anchoring and correlation.

### Font asset

Bundle **Courier Prime** (open-source screenplay font, SIL OFL) as
`backend/assets/fonts/CourierPrime-Regular.ttf` (+ Bold), referenced by absolute
path in the `@font-face` `src`. WeasyPrint embeds it, guaranteeing consistent
rendering on Railway's Linux image (which lacks Courier).

### Upload integration (`routes/supabase_routes.py::upload_script`)

After the FDX branch creates scenes (`create_scenes_from_parsed`), and only when
`is_fdx`:
1. Fetch the created scenes for `script_id` (`id, scene_order`) ordered by
   `scene_order`.
2. Call the preview generator with the `.fdx` temp path + scene rows.
3. Upload the PDF to `{script_id}/preview.pdf` (`application/pdf`).
4. `supabase.table('scripts').update({'preview_pdf_path': path}).eq('id', ...)`.
5. Batch-update each scene's `page_start`/`page_end` to the generated pages
   (`page_end` = next scene's start page, clamped ≥ `page_start`; last scene =
   total pages).
All wrapped in try/except with logging — a failure leaves `preview_pdf_path`
NULL and the scenes' estimated pages intact; the upload still returns 201.

### Serving (`get_pdf_url`)

- Select `preview_pdf_path` in addition to `file_path`.
- Sign `preview_pdf_path or file_path`.
- **Lazy fallback:** if the script is FDX (by `file_name`/`file_path`
  extension) and `preview_pdf_path` is NULL, generate the preview on demand
  (re-download the `.fdx` from storage to a temp file, run the generator,
  upload, set `preview_pdf_path`, update scene pages), then sign it. If
  generation fails, return the existing 404/500 so the panel shows its
  error+retry state.

### Schema migration

Add nullable column: `ALTER TABLE scripts ADD COLUMN preview_pdf_path text;`
(Supabase migration.) No backfill required — lazy fallback covers pre-existing
FDX scripts on first preview.

## Data Flow (sync)

Scene selection in `SceneViewer` → looks up `pageMapping.scene_pages[scene.id]`
(now populated from the generated PDF's real pages) → sets `currentPdfPage` →
`PdfViewerPanel.jumpToPage`. Reverse (PDF scroll → select scene) via
`page_to_scenes`. No frontend code changes.

## Error Handling

- Preview generation is best-effort at upload; never fails the upload.
- Missing font / WeasyPrint error → no `preview_pdf_path` → viewer shows its
  existing "Failed to load PDF" + Retry. Retry triggers `get_pdf_url` → lazy
  generation.
- Malformed/edited state: preview reflects the original FDX (by design).

## Testing

- `render_fdx_html`: emits one `id="scene-{id}"` anchor per scene and the
  expected element classes (heading/action/character/dialogue); dual dialogue
  produces two columns.
- `generate_fdx_preview_pdf`: on a multi-scene FDX returns non-empty PDF bytes
  (starts with `%PDF`) and a `scene_page_map` covering every scene id, with
  page numbers ≥ 1 and non-decreasing by scene order.
- Anchor→page capture: a fixture forcing a page break between two scenes maps
  them to pages 1 and 2 respectively.
- `get_pdf_url`: with `preview_pdf_path` set, signs that path (monkeypatched
  storage); with it NULL for an FDX script, triggers the lazy generator
  (generator monkeypatched) and then signs the produced path.

## Risks & Mitigations

- **Font availability on Railway** → bundle Courier Prime and reference by
  absolute path; test that the rendered PDF embeds it.
- **Pagination fidelity vs real Final Draft** → 12pt Courier + ~55 lines/page +
  standard margins approximate FD closely; exact match isn't required, but
  scene→page sync uses the *generated* PDF's own pages, so sync is always
  internally correct regardless of how closely it matches FD.
- **Upload latency** → generation is best-effort and can be made lazy; if
  upload-time cost is a concern in practice, the lazy path already exists as the
  fallback and could become the primary trigger without further design.
- **Dual dialogue / unusual elements** → styled best-effort; anchors are on
  scene headings only, so mapping is unaffected by body-rendering quirks.
