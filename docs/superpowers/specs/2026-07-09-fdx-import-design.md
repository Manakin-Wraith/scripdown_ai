# FDX (Final Draft) Import — Design

**Date:** 2026-07-09
**Status:** Approved design, ready for implementation planning
**Scope:** Add Final Draft `.fdx` import alongside the existing PDF upload path.

## Goal

Let users import scripts as Final Draft `.fdx` files, not just PDF. FDX is a
structured XML format that explicitly tags scene headings, action, characters,
dialogue, and transitions. Because the structure is explicit, FDX import is
*more* accurate than PDF parsing — no regex/AI guessing for scene boundaries or
who is in a scene. The existing AI breakdown phase still runs to fill the
production categories FDX does not contain (props, wardrobe, set dressing,
vehicles, SFX, makeup, etc.).

**Guiding rule:** FDX answers structure + who is in the scene; AI answers what is
needed to shoot the scene.

## Non-Goals

- Fountain, Celtx-native (`.celtx`), WriterDuet, or Fade In import. FDX only for
  this version. (Most of those tools export FDX or Fountain; the adapter pattern
  here leaves a clean seam to add Fountain next.)
- Requiring a companion PDF for accurate pagination. Page/eighths are estimated
  from text length.
- Changing anything downstream of scene-candidate creation (AI queue, reports,
  stripboard, scheduling).

## Approach — Format Adapter (chosen)

Add a new parser that emits the **same outputs** the current upload path already
consumes, and route by file extension at the top of `process_script_v2`. The
entire downstream pipeline (DB insert, `save_pages_to_db`,
`save_scene_candidates_to_db`, AI analysis queue, reports, stripboard) is
untouched. FDX becomes just a different way to fill the same tables.

Rejected alternatives:
- **Normalize everything to Fountain first** — lossy (Tagger data, dual dialogue,
  scene numbers flatten to text) and a larger rewrite of the working PDF path.
- **Full structured-import subsystem** — over-built for a single format today
  (YAGNI).

## Architecture & Routing

New module: `backend/services/fdx_parser.py`.

It exposes a single entry point that returns the four values
`process_script_v2` needs:

```python
def parse_fdx(file_path: str) -> tuple[list[PageData], str, list[SceneCandidate], dict]:
    """Returns (pages, full_text, candidates, metadata)."""
```

- `pages` — list of `PageData` objects (same dataclass used by the PDF path),
  synthesized by chunking `full_text` into ~55-line pages.
- `full_text` — the assembled plain text of the script (used for the `scripts`
  row and for `text_start`/`text_end` offsets).
- `candidates` — list of `SceneCandidate` objects (same dataclass the PDF path
  produces), with `parse_method = "fdx"`.
- `metadata` — same dict shape returned by `utils.metadata_extractor.extract_metadata`.

`process_script_v2` gains a dispatch at the top (after `file.save`):

```python
ext = os.path.splitext(filename)[1].lower()
if ext == '.fdx':
    pages, full_text, candidates, metadata = parse_fdx(file_path)
else:  # .pdf — unchanged
    pages, full_text = parse_pdf_with_pages(file_path)
    candidates = build_scene_candidates(pages, full_text)
    metadata = extract_metadata(file_path)
```

Everything after this block is unchanged.

`PageData` and `SceneCandidate` live in `services/extraction_pipeline.py`; the FDX
parser imports and reuses them rather than defining parallel types.

## What the FDX Parser Extracts

FDX structure: `<FinalDraft>` → `<Content>` → repeating
`<Paragraph Type="...">` elements. Relevant paragraph types: `Scene Heading`,
`Action`, `Character`, `Dialogue`, `Parenthetical`, `Transition`, `Shot`, plus
dual-dialogue grouping. Paragraph text lives in child `<Text>` elements (which
may carry style runs — concatenate their text content).

The parser walks `<Paragraph>` elements in document order:

1. **Scene boundaries** — every `Type="Scene Heading"` starts a new scene.
   - Scene number: read `<SceneProperties Number="...">` when present. This is the
     real scene number from the script — never invented. When absent, assign
     sequential numbers (reuse the existing `assign_scene_numbers` convention).
   - INT/EXT, setting, time-of-day: parse the heading text with the existing
     scene-header regex (`detect_scene_headers` patterns in
     `extraction_pipeline.py`) so behavior matches the PDF path.
2. **Scene text** — concatenate all paragraphs (heading + body) until the next
   Scene Heading into `scene_text`. Compute `content_hash` and
   `text_start`/`text_end` as offsets into the assembled `full_text`.
3. **Speakers** — collect `Type="Character"` names within the scene (including
   both sides of dual dialogue) into `speakers` (persisted to the `speaker_list`
   column). Normalize names (strip `(CONT'D)`, `(V.O.)`, `(O.S.)` extensions) so
   they match downstream entity resolution.
4. **Transitions / shot type** — from `Transition` paragraphs and `Shot`-type
   paragraphs → existing `transitions` / `shot_type` enrichment columns.
5. **Page / eighths** — FDX has no reliable fixed pages. Synthesize page ranges
   by accumulating estimated line counts using the same convention as
   `utils.scene_calculations.calculate_eighths_from_content` (~55 lines/page,
   8 eighths/page). This yields sensible `page_start`/`page_end` and keeps the
   existing eighths math working unchanged. Set `parse_method = "fdx"`.

## Final Draft Tagger Data ("maximize FDX")

If the writer used Final Draft's Tagger, scenes carry breakdown tags (cast,
props, etc.). In FDX these appear as tagger category data associated with a
scene (e.g. within `<SceneProperties>` / `<TaggerData>` or category elements).

- **When present:** the parser reads the tags and seeds breakdown elements for
  that scene, and marks those scenes so the AI phase can **skip or merely
  verify** the categories the file already answered.
- **When absent (common case):** scenes flow to AI breakdown exactly as PDF
  scenes do.

Either way, scene structure and speakers always come from FDX, so the AI phase
never re-derives scene detection or characters.

**Note:** the exact FDX Tagger XML shape varies by Final Draft version. The
implementation must confirm the real element/attribute names against a
Tagger-tagged sample fixture before wiring the seeding logic; if a tagged sample
is unavailable, Tagger ingestion degrades gracefully (no tags read, AI fills
everything) and can ship in a follow-up without blocking structure + speaker
import.

## Metadata, Pages Storage, Frontend, Testing

### Metadata
Read the FDX `<TitlePage>` content for title / author / draft info and return the
same dict shape as `extract_metadata` (`writer_name`, `writer_email`,
`writer_phone`, `draft_version`, `draft_date`, `copyright_info`,
`wga_registration`, `additional_credits`). Fields not present in the title page
are `None`. The `script_name` stored is the uploaded filename, matching the PDF
path.

### Synthetic pages
Still populate `script_pages`: chunk `full_text` into ~55-line "pages" as
`PageData` objects so any page-based scene-text reads keep working. Content hash
per synthetic page as usual.

### Frontend
- Add `.fdx` to the upload input's `accept` attribute and client-side file-type
  validation.
- Update helper copy to indicate "PDF or Final Draft (.fdx)".
- No change to `apiService.js` — same `/upload_script` endpoint and multipart
  upload. The backend routes by extension.

### Testing
Unit tests for `fdx_parser.py` using small FDX fixtures:
- Numbered scenes → scene numbers preserved from `<SceneProperties Number>`.
- Unnumbered scenes → sequential numbers assigned.
- Dual dialogue → both speakers captured.
- Title page → metadata fields populated.
- A Tagger-tagged sample → breakdown seeds produced (or graceful no-op if the
  Tagger shape can't be confirmed).
- Every scene → `eighths > 0` and non-empty `scene_text`.

## Data Flow Summary

```
.fdx upload
  → process_script_v2 (routes on extension)
    → parse_fdx()
        → walk <Paragraph> elements
        → SceneCandidate[] (parse_method="fdx", speakers pre-filled,
                            page/eighths estimated, optional Tagger seeds)
        → synthetic PageData[]  → full_text  → metadata dict
  → scripts row insert (unchanged)
  → save_pages_to_db / save_scene_candidates_to_db (unchanged)
  → user triggers AI analysis (unchanged; skips/verifies Tagger-seeded scenes)
  → reports / stripboard / scheduling (unchanged)
```

## Risks & Mitigations

- **FDX dialect variance** (scene number location, Tagger shape, style runs):
  drive parsing off real fixtures; degrade gracefully when optional data is
  absent.
- **Page/eighths accuracy**: estimated from text length by explicit decision;
  acceptable for scheduling and consistent with the existing
  `calculate_eighths_from_content` path.
- **Malformed / non-Final-Draft `.fdx`**: parser raises a clear error surfaced by
  the existing `upload_script` try/except (returns 500 with message), same as a
  corrupt PDF today.
