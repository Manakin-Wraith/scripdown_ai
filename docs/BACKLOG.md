# Backlog

Deferred work items with enough context to pick up later. Each entry states the
gap, current state, and options — not a committed design. Brainstorm before
implementing (see `superpowers:brainstorming`).

---

## FDX Tagger breakdown ingestion

**Status:** Deferred — gated on obtaining a real Final Draft Tagger-tagged `.fdx` sample.

**Context.** FDX import (shipped 2026-07-09) reads scene structure, scene
numbers, speakers, and dialogue, then relies on the AI pass for breakdown
categories (props, wardrobe, cast, SFX, etc.). When a writer has used Final
Draft's **Tagger**, those breakdown categories are already stored inside the
FDX (e.g. under `<SceneProperties>` / `<TaggerData>` or category elements) and
could be ingested directly instead of re-derived by AI.

**Why deferred.** The exact Tagger XML shape varies by Final Draft version and
we have no tagged sample to confirm element/attribute names against. Implementing
against a guessed shape risks silent wrong-parsing.

**Scope when picked up.**
- Obtain a real Tagger-tagged `.fdx`; confirm the element/attribute names.
- Parse tags → per-scene `{category: [values]}` (scaffold exists in the plan as
  `_extract_tagger_tags`, currently a safe empty-default).
- Seed breakdown elements on the `scenes`/`scene_candidates` records and mark
  those scenes so the AI pass **skips or merely verifies** the categories the
  file already answered.
- Degrade gracefully when Tagger data is absent (the common case) — unchanged
  behavior.

**References.**
- Design: `docs/superpowers/specs/2026-07-09-fdx-import-design.md` (§3)
- Plan: `docs/superpowers/plans/2026-07-09-fdx-import.md` (Task 8, optional/gated)
- Parser: `backend/services/fdx_parser.py`

---

## Script preview for FDX formats

**Status:** Deferred — real gap for `.fdx`-uploaded scripts.

**Context.** The right-side viewer (`frontend/src/components/pdf/PdfViewerPanel.jsx`)
fetches a `pdf_url` and renders the original **PDF**. FDX uploads have no PDF —
the file is stored as `.fdx` with `application/xml` — so the preview panel has
nothing to render for FDX-sourced scripts (empty/broken preview). PDF-sourced
scripts are unaffected.

**What exists to build on.** On FDX upload we already persist the reconstructed
screenplay text: `scripts.full_text` and per-scene `scene_text` (with scene
headings, action, character cues, and dialogue in order). So a preview does not
require the original PDF.

**Options (to brainstorm).**
1. **Formatted text view (lowest effort).** Render `full_text` / assembled
   `scene_text` in a read-only, screenplay-styled panel (monospace / element
   styling). No new storage or conversion. Loses exact pagination/layout.
2. **FDX → HTML render.** Parse the FDX structure into a formatted HTML
   screenplay view (proper element styling: scene headings, action, dialogue,
   parentheticals, dual dialogue). More faithful; more work.
3. **FDX → PDF on upload.** Convert to PDF at upload time (e.g. WeasyPrint, which
   the backend already uses for reports) and store it, so the existing PDF
   viewer works unchanged. Most faithful to current UX; adds a conversion step,
   storage, and layout-fidelity questions.

**Also decide:** how the viewer picks a mode — detect source format from the
script record (e.g. `file_name` extension / `file_path`) and route FDX scripts
to the FDX preview, PDF scripts to the existing PDF viewer.

**References.**
- Viewer: `frontend/src/components/pdf/PdfViewerPanel.jsx`
- FDX text source: `backend/services/fdx_parser.py` (`parse_fdx_upload` →
  `full_text`, per-scene `scene_text`)
- Upload/persistence: `backend/routes/supabase_routes.py::upload_script`

---

## PayFast ITN: claim-and-grant is not a single transaction

**Status:** Deferred — narrow residual gap; no money is lost or double-charged.

**Context.** The ITN handler (`backend/routes/payfast_routes.py`, shipped
2026-07-16) makes granting idempotent by *claiming* the intent row before
granting: `_claim_intent` runs a conditional `UPDATE ... WHERE id = ? AND
status = 'pending'`, and Postgres row serialisation guarantees exactly one of
two racing ITNs gets a row back. This closed the original double-grant window,
where granting happened before the row was marked and two concurrent callbacks
could both pass the `_already_processed` SELECT.

**The remaining gap.** The claim and the grant are two separate round-trips, not
one transaction. If the process dies *between* them, `_release_claim` never
runs: the row is left `status = 'complete'` with nothing granted, and PayFast's
retry sees a claimed row and declines to redo it. The user has paid and received
nothing, needing manual repair. Ordinary grant exceptions are already handled —
`_release_claim` returns the row to `pending` — so this is specifically a
crash/OOM/redeploy window of a few milliseconds.

**Why deferred.** The failure direction is deliberate and safe: a *missed* grant
(visible, repairable) rather than a *double* grant (silent, refund-requiring).
The window is small and PayFast retries are spaced out.

**Options when picked up.**
1. **Postgres function (most correct).** Move claim + grant into a single
   `SECURITY DEFINER` plpgsql function called via RPC, so both commit atomically.
   The Supabase client cannot span statements in one transaction, which is why
   this can't be fixed in Python alone.
2. **Reconciliation sweep (cheapest).** A periodic job finding
   `payfast_transactions` rows that are `complete` but have no corresponding
   grant (no `breakdown_credits` / `account_seats` row, no active licence), and
   either granting or alerting. Also catches unrelated drift.
3. **Claim leases.** Record `claimed_at` and treat a `complete` row with no
   grant after N minutes as reclaimable, letting a later retry finish it.

**References.**
- `backend/routes/payfast_routes.py` — `_claim_intent`, `_release_claim`,
  `payfast_notify`
- `backend/tests/test_payfast_itn_route.py` — `test_claim_happens_before_granting`,
  `test_failed_grant_releases_the_claim`
- Grant side: `backend/services/entitlement_service.py`
