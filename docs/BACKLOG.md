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

---

## Two-tier pricing / PayFast billing — outstanding fixes

**Status:** Open, tracked against `feat/two-tier-pricing` (not merged to main). Branch
is functionally verified end-to-end against live PayFast sandbox transactions
for all three charge types, but not yet safe to ship as-is.

### `routes/analysis_routes.py` has no auth at all

**Found:** 2026-07-18, via live adversarial testing (curl against a locally
running instance in non-dev auth mode).

**Context.** Every route in this blueprint — `GET /api/scripts/<id>/analysis/status`,
`GET .../characters`, `GET .../characters/<name>`, `GET .../story-arc`, `POST
.../cancel` — is registered in `app.py` with no `@require_auth`. Confirmed live:
all returned data or succeeded with no Authorization header. This is separate
from the write-side analysis endpoints in `supabase_routes.py`
(`/api/scenes/<id>/analyze`, `/api/scripts/<id>/analyze/bulk`), which correctly
require both `@require_auth` and `@require_breakdown_entitlement`.

**Impact.** Any anonymous caller who knows or guesses a numeric `script_id` can
read that script's character breakdown and story-arc data, and can cancel
another user's in-progress analysis job with no auth at all — a griefing vector
against a paying customer.

**Fix.** Add `@require_auth` (and an ownership/entitlement check, matching the
pattern used elsewhere) to every route in `backend/routes/analysis_routes.py`.
Small, contained change.

### Renewal automation not built

**Context.** `tier_2_license` (Annual Team License) uses PayFast tokenization
(migration `042_payfast_tokenization.sql`, `profiles.subscription_payfast_token`)
because true Recurring Billing isn't enabled on this merchant account. The token
is captured on activation, but there is no scheduled job that calls PayFast's
Recurring Billing API to charge it before each license's year expires.

**Why deferred.** Needed before `tier_2_license` is production-ready, but the
charge-type itself has been verified working; this is the follow-up piece.

**Scope when picked up.** A scheduled job (cron / Supabase pg_cron) that finds
licenses nearing expiry, charges the stored token via PayFast's API, and
updates `profiles.subscription_status` based on the result — which also feeds
directly into the failed-renewal gap below.

### Failed-renewal downgrade gap

**Context.** `get_entitlement` (`backend/services/entitlement_service.py`)
correctly denies team access once `subscription_status != 'active'`, but
nothing currently writes `status = 'expired'` when a renewal charge fails —
because renewal automation (above) doesn't exist yet to fail in the first
place. Flagged in the original two-tier pricing design doc, never closed.

**Why deferred.** Needs a real failed-renewal ITN payload (or the renewal job
itself) to test against; blocked on the renewal-automation item above.

### `list_members` IDOR-shaped gap

**Context.** Noted during Task 10 (team gating). The tier-2 gating check on
`list_members` verifies the *caller's own* tier, not whether the caller
belongs to the *specific script* being queried. Any tier-2 user can list any
script's team roster by ID.

**Why deferred.** Separate from the billing work in scope for this branch; a
straightforward authorization-check fix once picked up (verify membership on
the specific script, not just tier).

**References.**
- `backend/routes/analysis_routes.py`, `backend/routes/supabase_routes.py`
- `backend/services/entitlement_service.py` — `get_entitlement`, `activate_license`
- `backend/db/migrations/042_payfast_tokenization.sql`
- Team gating: wherever `list_members` is implemented (routes handling
  `/api/scripts/<id>/team` or similar)

---

## Report Studio: CSV export

**Status:** Not started — feature request.

**Context.** Report Studio (`frontend/src/components/reports/ReportStudio.jsx`,
`ReportPreviewPane.jsx`) and the backend `services/report_service.py` currently
only produce the WeasyPrint-rendered PDF/HTML report. There is no CSV export
path — grep of `report_service.py` / `report_routes.py` turns up nothing CSV-
related today.

**Scope when picked up.** Brainstorm before implementing (see
`superpowers:brainstorming`) — open questions: which report types get a CSV
export (stripboard, breakdown, all of them?), whether it reuses the same
filtered/configured view the PDF export uses (`report_config` column,
`029_report_filter_presets.sql`), and where the download entry point lives in
the UI (`ReportRail.jsx` / `ReportPreviewPane.jsx`).

**References.**
- `backend/services/report_service.py`, `backend/routes/report_routes.py`
- `frontend/src/components/reports/ReportStudio.jsx`,
  `ReportPreviewPane.jsx`, `ReportRail.jsx`

---

## Report version control and tracking

**Status:** Not started — feature request.

**Context.** No versioning of generated reports exists today — `report_config`
(migration `023_report_config_column.sql`) stores the current config for a
report, but there's no history of prior configs/generations, and no way to see
what changed between two versions of the same report or roll back.

**Scope when picked up.** Brainstorm before implementing — open questions:
version on every generation vs. only on explicit save; whether this tracks the
`report_config` (the filter/settings state) or the generated output (PDF/CSV)
itself, or both; retention (keep all versions forever vs. prune); how this
surfaces in `ReportLibraryDrawer.jsx` (version history per report).

**References.**
- `backend/db/migrations/023_report_config_column.sql`,
  `029_report_filter_presets.sql`
- `frontend/src/components/reports/ReportLibraryDrawer.jsx`,
  `ReportStudio.jsx`

---

## Seat purchase flow — RESOLVED, shipped

**Status:** Done. Was "Discuss: user flow when a script Owner buys a Seat for
a team member" — brainstormed, designed, planned, and implemented on
`feat/two-tier-pricing`.

**What shipped.** Seats stay a fungible pool (no per-seat assignment records).
The overbooking race is fixed: `_fetch_seats_used` now counts pending invites
toward the limit, not just accepted ones, so a seat is reserved the instant an
invite is sent rather than only once accepted. Two entry points: proactive
purchase from Billing (now with a quantity picker, was hardcoded to 1), and a
reactive "buy seats" panel in the invite modal when a `402
no_seats_available` is hit — the in-progress invite survives the PayFast
redirect via a sessionStorage draft and the Owner lands back on the same
script's team page with the invite pre-filled, ready to send. A cross-task
review caught and fixed one timing bug: the resume redirect was gated on the
generic `can_run_breakdown || can_use_teams` settle-check, which is already
true for a tier-2 owner before a seat purchase (seat count doesn't move those
booleans) — now gated on `seats_paid` growing past a captured pre-purchase
baseline instead.

**References.**
- Design: `docs/superpowers/specs/2026-07-18-seat-purchase-flow-design.md`
- Plan: `docs/superpowers/plans/2026-07-18-seat-purchase-flow.md`
- `backend/services/entitlement_service.py` — `_fetch_seats_used`, `grant_seats`
- `frontend/src/components/team/InviteModal.jsx`,
  `frontend/src/pages/PaymentResultPage.jsx`,
  `frontend/src/utils/pendingSeatInviteDraft.js`
