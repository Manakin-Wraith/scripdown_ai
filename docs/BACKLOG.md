# Backlog

Deferred work items with enough context to pick up later. Each entry states the
gap, current state, and options — not a committed design. Brainstorm before
implementing (see `superpowers:brainstorming`).

---

## Backend test suite has no CI gate — RESOLVED, shipped

**Status:** Done. `.github/workflows/backend-tests.yml` merged via PR #8
(commit `d3e086e`, 2026-07-21). Runs `pytest tests/` on every PR with dummy,
non-secret env vars; advisory only (not yet wired into branch protection).
Flipping the check to "required" remains an open follow-up if desired.

**Original context (kept for history):**

**Context.** There is no `.github/workflows/` directory in this repo at all.
The only checks currently wired to GitHub PRs are GitGuardian (secret
scanning) and Vercel's preview-deploy + comment bot — both frontend/deploy
concerned, neither runs `backend/tests/`. Confirmed on PR #7
(`feature/teams-access-control`): all 3 checks passed, but the 427-test
backend suite was only ever run locally, never gated in CI. A backend
regression can merge to `main` with a fully green PR.

**Scope when picked up.** Add a GitHub Actions workflow
(`.github/workflows/backend-tests.yml`) that, on PRs touching `backend/**`
(or unconditionally — decide breadth when picked up):
- Sets up Python 3.13, installs `backend/requirements.txt`.
- Runs `pytest tests/` from `backend/`.
- Fails the check on any non-zero exit, surfacing in the PR checks list
  alongside GitGuardian/Vercel.

**Also decide:** whether to require the required env vars
(`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`,
`RESEND_API_KEY`) via repo/CI secrets for the suite to run at all (per
`utils/env_validator.py`, the app — and by extension some tests — refuses
to start without them), or whether the test suite already mocks around
that boundary cleanly enough to run without real credentials; whether to
gate on this new check being required before merge (branch protection)
or advisory-only at first; and whether frontend gets an equivalent
`npm run build` CI gate at the same time (`npm run lint` is broken
repo-wide — see other memory — so build, not lint, should be the
frontend gate if added).

**References.**
- `backend/tests/` (427 tests as of PR #7)
- `backend/requirements.txt`, `backend/utils/env_validator.py`
- No existing `.github/workflows/*` to pattern-match against — this would
  be the first workflow in the repo.

---

## Production billing was fully broken for 3 days — RESOLVED, fixed

**Found:** 2026-07-21, when the user (an existing annual subscriber) tried to
subscribe/buy breakdowns/buy seats on production and got a generic "Could
not start checkout" error. **Fixed:** same day, across three independent
root causes discovered in sequence.

**Context.** The two-tier-pricing/PayFast billing backend (merged to `main`
2026-07-18) had never actually served traffic in production — every
`/api/billing/*` and `/api/payfast/notify` request returned a plain 404 as
if the routes didn't exist, despite the code being in `main` for three
days and every PR since showing green. Diagnosing this took three separate
investigations:

**1. Deploy pipeline never went live (backend/Dockerfile, backend/railway.json).**
`backend/Dockerfile`'s `CMD` and `backend/railway.json`'s `deploy.startCommand`
both hardcoded `--bind 0.0.0.0:8080`, ignoring Railway's dynamically-assigned
`$PORT` — every deploy attempt failed Railway's healthcheck (`service
unavailable`, every retry, every attempt) and Railway silently kept serving
whatever old pre-payfast build was last successful. First fix attempt
(`${PORT:-8080}` in `railway.json`'s `startCommand`) made it worse — Railway
executes `startCommand` without a shell, so the string was passed to
gunicorn *unexpanded* (`Error: '${PORT' is not a valid port number.`,
confirmed via real runtime logs). Final fix: removed the `startCommand`
override entirely so Railway falls back to the Dockerfile's own
`CMD ["sh", "-c", "..."]` array form, which Docker guarantees runs through
a real shell regardless of how the platform invokes it — matching the
repo-root `Dockerfile`/`railway.json`, which never had this bug. Verified
locally via `docker run` with a custom `PORT` injected before touching
production.

**2. `api.slateone.studio` DNS pointed at a dead Vercel deployment.**
`PAYFAST_API_URL` defaults to `https://api.slateone.studio`, used to build
PayFast's `notify_url`. That domain's DNS was pointed at Vercel (`server:
Vercel`, `DEPLOYMENT_NOT_FOUND`) with no project actually configured to
answer it — meaning even once (1) was fixed, PayFast's ITN webhook had
nowhere to reach. An interim attempt to override `PAYFAST_API_URL` to the
raw `*.up.railway.app` domain got rejected by PayFast's own checkout
form ("The notify url format is invalid" — PayFast validates/whitelists the
notify domain against the merchant's registered settings). Real fix: added
a CNAME for `api.slateone.studio` directly to Railway's custom-domain
target (Railway supports attaching custom domains straight to a service;
no reason for API traffic to route through Vercel at all), keeping
`PAYFAST_API_URL` on its branded default. Verified via `dig @ns1.vercel-dns.com`
(Vercel's own authoritative nameserver) and public resolvers (8.8.8.8,
1.1.1.1) resolving correctly to Railway, plus a live `/health` 200 over
the branded domain.

**3. `is_valid_payfast_ip` silently rejected legitimate ITNs.**
Even with (1) and (2) fixed, real checkouts still got stuck `status:
'pending'` forever with `pf_payment_id: NULL` (PayFast believed the payment
succeeded; our webhook never claimed the row). Added a diagnostic
`reject_reason` column (migration `044_payfast_reject_reason.sql`) so
`_reject()` in `payfast_routes.py` records *why* an ITN was rejected,
directly queryable via Supabase — this replaced several rounds of unreliable
Railway log copy-pasting. First real evidence: `reject_reason: 'untrusted
source ip 152.233.12.24x'`. `is_valid_payfast_ip` live-resolved 5 hardcoded
PayFast hostnames via DNS and rejected any ITN from an IP outside that
snapshot; PayFast's actual sandbox ITN sender IPs weren't in the resolved
set at all (confirmed: 66 IPs resolved, none in the `152.x` range). This
check has likely been silently dropping legitimate ITNs since it was
written, not just this week. Removed `is_valid_payfast_ip`,
`_resolve_payfast_ips`, and `PAYFAST_HOSTS` entirely — signature
verification (`verify_itn_signature`) plus the server-to-server
confirmation call (`confirm_with_payfast`, which asks PayFast directly "did
you send this?") remain as the security boundary; the latter is the check
PayFast's own integration guidance actually recommends and doesn't depend
on a moment-in-time DNS snapshot.

**Verification.** After all three fixes, two real sandbox purchases (10
breakdown credits, 9 team seats) went all the way through: transaction rows
show `status: 'complete'` with a real `pf_payment_id`; `breakdown_credits`
ledger shows a correctly-linked `+10` row; `account_seats` shows a
correctly-linked `9`-seat grant with a proper `term_expires_at`. Backend
suite (422 tests) passes after the IP-check removal.

**Outstanding follow-up — corrected 2026-07-31.** The four stuck-`pending`
transactions from the diagnosis window were PayFast **sandbox** test
transactions, not real customer payments — no manual grant needed, nothing
to repair. The real remaining follow-up: production is still configured
against **PayFast sandbox credentials**, not live. Needs switching to real
PayFast merchant credentials (merchant ID/key, live passphrase, live
API host) in Railway's env vars before any real customer traffic can be
processed. Check `backend/services/payfast_service.py` /
`backend/routes/payfast_routes.py` for where sandbox vs. live host/creds
are read from, and confirm `PAYFAST_API_URL`/webhook config still points
at the correct (now-live) merchant settings after the switch — re-verify
with a real low-value live transaction once switched, same pattern used to
verify the sandbox flow.

**References.**
- `backend/Dockerfile`, `backend/railway.json` — `$PORT` binding fix
- `backend/db/migrations/044_payfast_reject_reason.sql` — diagnostic column
- `backend/routes/payfast_routes.py`, `backend/services/payfast_service.py`
  — IP-check removal
- `backend/tests/test_payfast_itn_route.py`,
  `backend/tests/test_payfast_itn_validation.py` — updated for IP-check removal
- DNS: `api.slateone.studio` CNAME, now pointed directly at Railway

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

## Script preview for FDX formats — RESOLVED, already shipped

**Status:** Done. Discovered 2026-07-22 while scoping this entry for a
brainstorm — it turned out to already be merged to `main` on 2026-07-09
(`5ca0b03`, "faithful FDX screenplay preview with scene→page sync"),
predating and superseding this backlog entry, which had gone stale.

**What shipped.** Combines and exceeds options 2 and 3 originally
sketched here: `backend/services/fdx_preview.py` renders FDX scenes into
a proper screenplay-formatted HTML/CSS document (scene headings, action,
dialogue, parentheticals — 12pt Courier Prime, industry margins) and
converts it to a real PDF via WeasyPrint. Each scene heading is embedded
as a PDF anchor, so `generate_fdx_preview_pdf` also captures a genuine
scene→page map, giving FDX scripts the same scene-list/preview-panel
sync PDF-sourced scripts have. `get_pdf_url` (`supabase_routes.py`)
lazily generates and caches the preview on first request
(`preview_pdf_path` column, `scripts` storage bucket) — **no frontend
changes were needed**, since `PdfViewerPanel.jsx` already just renders
whatever PDF `getPdfUrl` returns, regardless of source format.

**Verification.** `backend/tests/test_fdx_preview.py` (13 tests) and
`backend/tests/test_fdx_route.py` pass.

**References.**
- `backend/services/fdx_preview.py` — HTML/CSS render + WeasyPrint PDF + page-anchor capture
- `backend/routes/supabase_routes.py` — `_lazy_generate_fdx_preview`, `store_fdx_preview`, `get_pdf_url`
- `frontend/src/components/pdf/PdfViewerPanel.jsx` — unchanged, format-agnostic
- `backend/tests/test_fdx_preview.py`, `test_fdx_route.py`

---

## PayFast ITN: claim-and-grant is not a single transaction — RESOLVED, fixed

**Found:** Originally noted as deferred in the backlog (narrow residual gap where crash between claim and grant would leave row `complete` with nothing granted). **Fixed:** 2026-07-21.

**Context.** The ITN handler (`backend/routes/payfast_routes.py`, shipped 2026-07-16) claimed the intent row before granting to make granting idempotent, closing the double-grant window. However, claim and grant were two separate round-trips — if the process crashed *between* them, `_release_claim` never ran, leaving the row `status = 'complete'` with nothing granted, requiring manual repair.

**Fix.** Migration `backend/db/migrations/043_payfast_atomic_claim_grant.sql` added a `SECURITY DEFINER` Postgres function `payfast_claim_and_grant` that performs the claim UPDATE and the charge-type-specific grant (breakdown_credits / profiles / account_seats) in a single transaction. A mid-call crash now rolls back both, closing the gap entirely. `backend/routes/payfast_routes.py::payfast_notify` was rewired to call this function via a single `_claim_and_grant` RPC seam, replacing the old `_claim_intent` / grant-dispatch / `_release_claim` orchestration. The admin manual-approval path (`admin_routes.py`) deliberately left unchanged since it has no race to close.

**Verification.** All scenarios verified against a real local Postgres (Docker): each of the 3 charge types (`tier_1_credits`, `tier_2_license`, `tier_2_seats`) grants correctly; a duplicate call returns `'duplicate'` without double-granting; a forced failure rolls back the claim too; and two genuinely concurrent calls on the same row grant exactly once. `backend/tests/test_payfast_itn_route.py` rewritten for the new single-call mock seam — seven affected tests updated, structural changes (one test deleted, one renamed).

**Deploy note.** Migration 043 must be applied to the real Supabase project before (or atomically with) deploying this branch's `backend/routes/payfast_routes.py`. If the code deploys first, the `payfast_claim_and_grant` RPC call fails with "function does not exist," which `payfast_notify` catches and turns into an HTTP 200 -- telling PayFast to stop retrying, so a real payment in that window is silently lost (no claim, no grant, no retry). Separately: the Docker verification above called the function via raw `psycopg2`, and every automated test mocks `_claim_and_grant` wholesale, so the actual runtime boundary -- `get_supabase_admin().rpc('payfast_claim_and_grant', {...}).execute()` returning `resp.data` as a bare string (`'granted'`/`'duplicate'`) -- has never been exercised for real. Recommend one manual `get_supabase_admin().rpc(...)` smoke call against a throwaway pending row right after applying the migration, to confirm `resp.data` is actually the bare string the Python code assumes (and not, say, a list or dict wrapping it).

**References.**
- `backend/db/migrations/043_payfast_atomic_claim_grant.sql` — new atomic function definition
- `backend/routes/payfast_routes.py` — `payfast_notify` rewired to call `_claim_and_grant` via RPC
- `backend/tests/test_payfast_itn_route.py` — test suite updated for single-call seam
- Grant side: `backend/services/entitlement_service.py` (unchanged for ITN path)

---

## Two-tier pricing / PayFast billing — outstanding fixes

**Status:** Open, tracked against `feat/two-tier-pricing` (merged to `main`
2026-07-18). Branch was functionally verified end-to-end against live
PayFast sandbox transactions pre-merge — that verification did NOT reflect
the actual deployed Railway service, which had never gone live in
production at all until 2026-07-21 (see "Production billing was fully
broken for 3 days" above). The anonymous-access vulnerability below is
fixed and merged; renewal automation remains open post-merge. The
`list_members` gap below is now resolved.

### `routes/analysis_routes.py` has no auth at all — RESOLVED, fixed

**Found:** 2026-07-18, via live adversarial testing (curl against a locally
running instance in non-dev auth mode). **Fixed:** 2026-07-18, same day.

**Context.** Every route in this blueprint — `GET /api/scripts/<id>/analysis/status`,
`GET .../characters`, `GET .../characters/<name>`, `GET .../story-arc`, `POST
.../cancel` — was registered in `app.py` with no `@require_auth`. Confirmed live:
all returned data or succeeded with no Authorization header. This is separate
from the write-side analysis endpoints in `supabase_routes.py`
(`/api/scenes/<id>/analyze`, `/api/scripts/<id>/analyze/bulk`), which correctly
require both `@require_auth` and `@require_breakdown_entitlement`.

**Impact.** Any anonymous caller who knew or guessed a numeric `script_id`
could read that script's character breakdown and story-arc data, and cancel
another user's in-progress analysis job with no auth at all — a griefing
vector against a paying customer.

**Fix.** Every route in `backend/routes/analysis_routes.py` now has
`@require_auth`, plus a `_user_can_access_script` ownership/team-membership
check (imported from `supabase_routes.py`, the same helper already used by
the write-side endpoints) before touching any script-scoped data. The one
global, non-script-scoped route (`GET /api/analysis/status`) got
`@require_auth` only, matching the backlog's original scope.

**Verification.** `backend/tests/test_analysis_routes_auth.py` (new): every
route rejects anonymous callers (401) and non-members (403); an authorized
member still gets a 200. Full backend suite (399 tests) and app boot both
pass with no regressions.

**References.**
- `backend/routes/analysis_routes.py`
- `backend/routes/supabase_routes.py` — `_user_can_access_script`
- `backend/tests/test_analysis_routes_auth.py`

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

### `list_members` IDOR-shaped gap — RESOLVED, fixed

**Found:** Noted during Task 10 (team gating), 2026-07-18. **Fixed:**
2026-07-20, incidentally, by commit `90037b7` ("feat(teams): admin role
management with rank guardrails") while converting `list_members` and
`create_invite` to the `@require_script_role` decorator.

**Context.** The tier-2 gating check on `list_members` verified the
*caller's own* tier (`@require_team_tier`), not whether the caller belonged
to the *specific script* being queried. Any tier-2 user could list any
script's team roster by ID.

**Fix.** `backend/routes/invite_routes.py` — `list_members` now carries
`@require_script_role('viewer', resolver=from_script)` ahead of
`@require_team_tier`, so the caller must hold at least `viewer` on the
specific `script_id` in the URL (owner or a `script_members` row), not just
the tier check.

**Verification.** `backend/tests/test_route_enforcement.py::test_script_scoped_routes_enforced`
asserts every script-scoped route in this blueprint (including
`invite.list_members`) carries the `_authz_min_role` marker; passes.

**References.**
- `backend/routes/invite_routes.py` — `list_members`
- `backend/middleware/authorization.py` — `require_script_role`, `get_script_role`
- `backend/tests/test_route_enforcement.py`

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

## Script re-upload: detect and highlight what changed — PARTIALLY BUILT, entry corrected

**Status:** Open, but narrower than originally scoped. Found 2026-07-22
while checking the backlog for stale entries — the original premise
below ("re-uploading means a brand-new `script_id`... discarding all
prior breakdown work") is factually wrong; a substantial chunk of
Option 1 already shipped as a **Revision Import** feature, apparently
before this entry was written.

**What already exists (`git log`: `d36707c`, "Complete Phase 3 -
Revision Import").** `backend/services/revision_service.py` +
`/api/scripts/<id>/versions/import` (`supabase_routes.py`) let a user
upload a revised PDF **against the same `script_id`**: `diff_script_versions`
compares new-vs-old scenes and classifies each as added/modified/removed/
unchanged; `apply_revision_changes` inserts new scenes, updates only the
modified ones (bumping `revision_number`, writing a `scene_history` row),
marks removed scenes `is_omitted` instead of deleting them, and — the
core value prop this backlog item wanted — **leaves unchanged scenes,
and therefore their breakdown data, completely untouched**. `script_versions`
tracks version history per script. The frontend has a real entry point:
`RevisionImportWizard.jsx`, wired into `SceneManager.jsx`, not a dead
component. A preview mode (`apply_changes=false`) returns the diff
without writing anything, matching the "review before committing"
instinct in the original Option 1 sketch.

**What's actually still missing.**
- **PDF-only.** `import_revision` rejects anything not ending `.pdf`
  (`supabase_routes.py`) — no FDX revision-import path, unlike FDX's own
  upload/analysis flow.
- **No test coverage at all.** `grep` across `backend/tests/` for
  `revision_service`, `diff_script_versions`, `apply_revision_changes`,
  or `import_revision` returns nothing — this entire feature has never
  been exercised by an automated test.
- **Selective AI re-analysis unconfirmed.** The backlog's "only re-queue
  AI analysis for scenes that actually changed" isn't obviously wired
  up in `apply_revision_changes` as read — needs tracing through to
  confirm modified/added scenes actually get queued and unchanged ones
  don't get needlessly re-billed/re-run.
- **Discoverability.** This is a deliberate "Import Revision" action a
  user has to find inside `SceneManager`, not something that happens
  automatically when someone uses the normal top-level script upload
  flow — worth deciding whether that's the intended UX or whether the
  two paths should be unified.
- Option 2 (partial "pink pages" upload of only changed scenes) was
  never built and is still a legitimate future idea if wanted.

**References.**
- `backend/services/revision_service.py` — `diff_script_versions`,
  `apply_revision_changes`, `create_version_record`, `get_version_history`
- `backend/routes/supabase_routes.py` — `import_revision`,
  `get_version_diff`, `get_version_details`, `get_script_versions`
- `frontend/src/components/revisions/RevisionImportWizard.jsx`,
  `frontend/src/components/scenes/SceneManager.jsx`
- `script_versions`, `scene_history` tables

---

## Series / multi-episode analysis — Phase 1 + My-Scripts grouping + known-series picker RESOLVED, shipped; further UX/UI reassessment + Phase 2 + Board/Schedule/Report integration open

**Status:** Phase 1 (grouping/reporting layer) shipped 2026-07-22,
including a same-day reassignment-surface fix and a visual polish pass
(both also 2026-07-22). A first slice of the UX/UI reassessment —
nesting episodes under series/season directly in the My Scripts table,
plus an upload-flow deep link to skip the picker for the common
"add the next episode" case — shipped 2026-07-23. A second slice —
styling `SeriesPicker` and replacing its "pick from scratch" tabs with a
compact known-series view when arriving via that deep link — also
shipped 2026-07-23. Three follow-ups remain open: the rest of the UX/UI
reassessment (`SeriesAssignmentModal` still unstyled, the 3-level
`/series` click-through still exists), Phase 2 (cross-episode entity
continuity), and whether/how Series should integrate with
Board/Scheduling/Reporting (all three are strictly single-script-scoped
today — confirmed via investigation 2026-07-23, no
`season_id`/`episode_number` touches those code paths anywhere).

**What shipped (Phase 1).** Brainstormed, designed, planned, and
implemented via `superpowers:subagent-driven-development` across 8 tasks,
merged to `main`. A `series` → `seasons` → episode (`scripts.season_id`/
`episode_number`) hierarchy, assignable at upload time via a `SeriesPicker`
component, with `GET/POST /api/series`, `GET/POST /api/series/:id/seasons`,
`GET /api/seasons/:id/episodes`, `PATCH /api/scripts/:id/season`, and
`GET /api/seasons/:id/cast` (combined cast view, exact-name-grouped,
case-insensitive — explicitly not identity resolution). Access is
inherited per-episode from existing script roles, no new permission
system. Zero billing/entitlement impact by design. A same-day follow-up
fix added the missing reassignment surface (a "Series" action in the My
Scripts table, `SeriesAssignmentModal`) after live testing showed the
original design's "fix a mis-assigned episode later" requirement had
never actually been built.

Along the way, a real production bug was found and fixed: this repo's
`postgrest` library raises on a zero-row `.single()` call instead of
returning `None`, so every `if not result.data: return 404` built on
`.single()` was unreachable — fixed via a `fetch_single()` helper
(`backend/db/supabase_client.py`), retrofitted across `series_routes.py`
and ~21 pre-existing call sites in `invite_routes.py`.

**Done: style the Series/Season UI — RESOLVED, shipped 2026-07-22.**
Found during live manual testing (uploading two real "Die Testament"
episodes) — the three pages were functionally correct but visually
undressed (plain default `<ul>`/`<li>` lists, no CSS at all). Fixed via
`superpowers:brainstorming` (visual companion mockups chose row-list over
card-grid, and a styled table over character-cards for the cast view) →
new shared `frontend/src/pages/SeriesPages.css`, consistent full-page
loading/error handling across all three pages (previously two competing
conventions), and icon+heading+description empty states. Verified live
against real data. `SeriesAssignmentModal`/`SeriesPicker` (the
reassignment surface) were explicitly left unstyled — deferred, not
forgotten (browser-default form controls only).

**Done: nest episodes under series/season in My Scripts, add upload
deep-link — RESOLVED, shipped 2026-07-23.** Found via live use: assigning
a script's series was already inline at upload (`SeriesPicker` embedded
in `ScriptUpload.jsx`, not a separate page — contrary to the original
complaint that prompted this), but *browsing* the library by series
required leaving My Scripts for the `/series` pages, and there was no
fast path to "add the next episode to a season I'm already working in."
Brainstormed, designed, planned, and implemented via
`superpowers:subagent-driven-development` across 4 tasks. `GET
/api/scripts` now joins `season_id → seasons → series` and returns
`series_id`/`series_title`/`season_number`/`season_title` (batched
`in_()` queries, not N+1). `ScriptTable.jsx` groups scripts into
collapsible series → season → episode rows (localStorage-persisted
collapse state, collapsed by default; unassigned scripts still render
flat and sortable below, unchanged). Each series header links to
`/series/:id` ("View series" — the `/series` pages are kept, not
replaced, for the combined cast view and deeper series management);
each season header has an "Add episode" action that deep-links to
`/upload?seriesId=..&seasonId=..`. `SeriesPicker.jsx` gained optional
`initialSeriesId`/`initialSeasonId`/`initialEpisodeNumber` props (zero
behavior change when omitted — `SeriesAssignmentModal.jsx`'s usage is
unaffected) so `ScriptUpload.jsx` can pre-select that season and the
next sequential episode number from the deep link, still fully editable
before uploading. A real race condition in the prefill effect (a
series-switch before the season list finished loading could silently
apply the original prefill onto the newly selected series) was found in
task review, needed two fix rounds to close (a synchronous ref flip
alone was insufficient; the standard React effect-cancellation-flag
pattern closed it fully) — independently re-verified by tracing the
closure/cleanup semantics.

**Done: known-series picker view + `SeriesPicker` styling — RESOLVED,
shipped 2026-07-23.** Found via live use right after the My-Scripts
deep link shipped (above): `SeriesPicker.jsx` had no CSS at all
(raw browser-default controls floating on the dark page background),
and landing on `/upload` via a season's "Add episode" link still showed
the exact same "pick a series from scratch" 3-tab UI as a cold upload,
just with values pre-filled — nothing in the UI reflected that the
series was already known. Separately, the account owner flagged that
episodes are sometimes uploaded out of sequence (e.g. episode 5 before
episode 3) and the UI needed to make that as easy as accepting the
suggested next number. Brainstormed, designed, planned, and implemented
via `superpowers:subagent-driven-development` across 3 tasks.
`SeriesPicker.jsx` gained a derived `isKnownSeries` flag (true only when
both `initialSeriesId` and `initialSeasonId` are set) and an `overridden`
escape hatch: when known, it renders a compact view (series-name badge,
a live season `<select>`, an always-editable episode-number `<input>`
explicitly supporting out-of-sequence numbers, a "Not this series?"
button that reveals the classic tabs from a clean state) instead of the
3-tab picker. The "next episode number" suggestion moved from
`ScriptUpload.jsx` into `SeriesPicker` itself, recomputed via
`listEpisodes()` whenever the season dropdown changes (numbering is
per-season and the season is now live inside the picker) —
`ScriptUpload.jsx` simplified accordingly, now just forwarding
`seriesId`/`seasonId` from the URL. New `SeriesPicker.css` (first
stylesheet for this component) styles both render paths against the
same dark navy/amber tokens `ScriptTable.css` already uses. No backend
changes; `SeriesAssignmentModal.jsx`'s classic-tabs usage is unaffected
(it never passes `initialSeriesId`/`initialSeasonId`, so `isKnownSeries`
is always `false` there) — confirmed both in task review and the final
whole-branch review.

**In progress (started 2026-07-23, paused mid-verification): `/series`
3-level click-through collapsed to an accordion.** Brainstormed,
designed, planned, and implemented via `superpowers:subagent-driven-development`
in worktree branch `worktree-series-accordion` (not yet merged).
`SeriesDetailPage.jsx` (the pure season-picker page) is deleted;
`SeriesListPage.jsx` becomes an accordion — clicking a series expands
its seasons inline instead of navigating to a separate page. The old
`series/:seriesId` route now redirects to `/series?expand=<id>`
(pre-expanding that series), and `ScriptTable.jsx`'s "View series"
action links straight there. All 3 code tasks passed task review clean.

Live verification against real production data (2026-07-23) surfaced
four real issues the task reviews didn't catch, all fixed in a follow-up
commit on the same branch:
- The original lazy-fetch-on-expand design (a deliberate brainstorm
  decision) felt clunky in practice — a spinner on every first expand.
  Redesigned to batch-embed each series' seasons directly into
  `GET /api/series` (one extra batched query, not N+1) so expand is a
  pure instant UI toggle. New test coverage
  (`test_list_series_embeds_seasons_ordered_and_scoped`,
  `test_list_series_with_no_series_returns_empty_list`); 19/19 series
  tests and 445/445 full backend suite pass.
- Abrupt open/close snap replaced with a `max-height` transition (a
  `grid-template-rows: 0fr` approach was tried first but doesn't
  reliably collapse to a true zero height in practice — left a visible
  sliver of the child row peeking through when collapsed).
- The toggle `<button>` had unreset native browser chrome
  (`appearance`/`outline`), rendering a stray border artifact under the
  row — fixed.
- **Alignment bug fixed as part of this work** (see the entry below,
  now resolved): `.series-page` gained `margin: 0 auto`. While touching
  that CSS, also found and fixed a real `:first-of-type` scoping bug on
  `.series-section-title` — the pseudo-class is scoped per `<section>`
  parent, so on `SeasonPage.jsx` (each heading in its own `<section>`)
  it was zeroing the top margin on *every* section's heading instead of
  just the page's first, collapsing the gap above "Combined Cast" against
  the Episodes list above it. Spacing moved to the `<section>` boundary
  instead.

**Stopped here at user request, before finishing.** Two of the four live
fixes (the collapse-sliver fix and the Combined Cast spacing fix) were
made but not yet re-verified live in the browser — do that first on
resume. Then still needed: final whole-branch code review and
`superpowers:finishing-a-development-branch` (branch not yet merged to
`main`). Progress ledger:
`.claude/worktrees/series-accordion/.superpowers/sdd/progress.md` (that
worktree, not this checkout).

**Still open, unchanged by the above:** `SeriesAssignmentModal` remains
unstyled (browser-default form controls only — noted as in-scope back
when the visual polish pass shipped 2026-07-22, still not done; it
reuses `SeriesPicker`'s classic tabs, which are now styled, but the
modal's own chrome is not) — explicitly deferred out of this round's
scope per user decision during brainstorming.

**Open: Phase 2 — cross-episode entity continuity.** Character/location/
prop identity carrying across episodes (so "JOHN" in episode 3 resolves to
the same entity as "JOHN" in episode 1), rather than each episode's cast
being independently extracted with only exact-string-match grouping in the
combined cast view. Would extend `backend/services/entity_resolver.py`'s
existing duplicate-character merging logic across scripts within a season.
Higher value, meaningfully harder — needs a cross-script identity store and
a strategy for when episode 5 legitimately introduces a different "JOHN."
Also still open from the original brainstorm: whether identity matching is
AI-assisted (embedding/fuzzy match) or requires manual confirmation.

**Open: does/should Series integrate with Board, Scheduling, or
Reporting?** Raised by the account owner 2026-07-23 — now that a season's
episodes are easy to see grouped together, should scheduling or reporting
gain any season-level concept, or make cross-episode work easier? Confirmed
via investigation before scoping this session's brainstorm down to just the
My Scripts table (above): today all three are strictly single-script-scoped
with no exceptions — `shooting_schedules.script_id` is `NOT NULL REFERENCES
scripts(id)` (`030_shooting_schedules.sql`), every schedule/stripboard route
in `backend/routes/schedule_routes.py` and every call in
`ShootingSchedulePage.jsx`/`ScheduleKanban.jsx` is scoped to one `scriptId`;
`report_service.py`'s every method and `ReportStudio.jsx`'s every call
likewise take one `script_id`. No `season_id`/`episode_number` reference
exists anywhere in either code path. This is a genuinely undesigned
question, not a partially-built feature — needs its own
`superpowers:brainstorming` pass to decide whether a season-level rollup
(e.g. a combined report across a season's episodes, or a shared
stripboard spanning multiple episodes shot together) is worth the added
complexity, or whether per-episode scoping should simply stay as-is.

**Open (expanded scope, 2026-07-23): Board/Schedule a series with
numerous episodes.** Beyond the general integration question above, the
account owner specifically wants to brainstorm how an AD/Line Producer
would actually **Board and Schedule a whole series** (multiple episodes
shot together, as is typical in TV production), not just view episodes
grouped in a list. Open questions for that brainstorm: does a
season/series get its own stripboard spanning all its episodes' scenes
(cross-episode board), or does each episode keep its own board with a
season-level view layered on top; how strip/scene ordering and day
assignment should represent which episode a strip belongs to; whether
`shooting_schedules.script_id` needs to become nullable/multi-script (a
schema change) or a season-level board is a new, separate concept
alongside the existing per-script one; and how this interacts with the
existing single-`script_id` scoping confirmed above in
`schedule_routes.py`/`ShootingSchedulePage.jsx`/`ScheduleKanban.jsx`.

**Open (2026-07-23): key season-level metrics for the Series/Season
page.** Separately, after a season's episodes have all been analyzed,
what data points would an AD or Line Producer actually want to see when
looking at a Season (on `SeasonPage.jsx`, which today only shows the
combined cast table)? Needs a brainstorm to shortlist candidates before
building anything — starting candidates to validate: total scene count
and estimated total shoot days across the season; cast members ranked by
episode-count/total-scene-count across the season (which actors span the
most episodes); location reuse across episodes (which locations get
shot at repeatedly, useful for company-move planning); total estimated
runtime/page count across the season; and any per-episode breakdown
counts (props/wardrobe/vehicles/SFX) rolled up to a season total. None
of this is computed anywhere today — `get_season_cast`
(`backend/routes/series_routes.py`) is the only season-level aggregate
that currently exists.

**Bug (2026-07-23) — RESOLVED, fixed as part of the accordion work
above.** Series/Season pages were left-aligned, not centered:
`frontend/src/pages/SeriesPages.css:6-8` — `.series-page` set
`max-width: 900px` but no `margin: 0 auto`, so on wide screens
`SeriesListPage`/`SeasonPage` sat flush against the left edge instead of
centering, unlike `BillingPage`'s `.billing-content` (fixed for the same
complaint on 2026-07-21). Fixed as a one-line `margin: 0 auto;` addition
while already touching this CSS for the accordion work (see above) —
not yet merged to `main` (worktree branch `worktree-series-accordion`).
Bundling with the season-metrics brainstorm turned out unnecessary; the
metrics panel, whenever built, can adjust `.series-page`/`SeasonPage`
layout further at that point same as any other page change would.

**Done: document Series in `docs/SLATEONE_FEATURES.md` — RESOLVED, fixed
2026-07-28.** The feature had shipped across four merged rounds (Phase 1
grouping, My-Scripts nesting, known-series picker, accordion pages) but
was never added to the product capability doc — zero mentions of
"series" in `SLATEONE_FEATURES.md` despite being live in production.
Added as new "Currently Available" section 6, "Series & Multi-Episode
Management" (old section 6, Exporting & Reporting, renumbered to 7),
covering Series → Season → Episode grouping, the grouped My-Scripts
view, the Series/Season pages with combined cast view, and the
no-billing-impact guarantee. Deliberately left out the still-open items
above (unstyled `SeriesAssignmentModal`, Board/Schedule/Report
integration, Phase 2 identity resolution) since those aren't shipped —
add them to the Roadmap section instead if/when scoped.

**References.**
- Phase 1 design: `docs/superpowers/specs/2026-07-22-series-multi-episode-phase1-design.md`
- Phase 1 plan: `docs/superpowers/plans/2026-07-22-series-multi-episode-phase1.md`
- My-Scripts-grouping design: `docs/superpowers/specs/2026-07-23-series-nested-script-table-design.md`
- My-Scripts-grouping plan: `docs/superpowers/plans/2026-07-23-series-nested-script-table.md`
- Known-series-picker design: `docs/superpowers/specs/2026-07-23-upload-known-series-picker-design.md`
- Known-series-picker plan: `docs/superpowers/plans/2026-07-23-upload-known-series-picker.md`
- `backend/routes/series_routes.py`, `backend/db/migrations/045_series_seasons.sql`
- `backend/routes/supabase_routes.py` — `_attach_series_info` (the `GET /api/scripts` join)
- `frontend/src/pages/SeriesListPage.jsx`, `SeriesDetailPage.jsx`, `SeasonPage.jsx`, `SeriesPages.css`
- `frontend/src/components/series/SeriesPicker.jsx`, `SeriesPicker.css` (new) — known-series view + styling
- `frontend/src/components/series/SeriesAssignmentModal.jsx` (still unstyled — remaining reassessment scope)
- `frontend/src/components/scripts/ScriptTable.jsx` — grouped series/season rendering, "View series"/"Add episode" actions
- `frontend/src/components/script/ScriptUpload.jsx` — `?seriesId=&seasonId=` deep-link prefill
- Phase 2 starting point: `backend/services/entity_resolver.py`
- Board/Schedule/Report integration starting points: `backend/routes/schedule_routes.py`,
  `backend/db/migrations/030_shooting_schedules.sql`, `backend/services/report_service.py`,
  `frontend/src/components/schedule/`, `frontend/src/components/reports/ReportStudio.jsx`
- Season-level metrics starting point: `backend/routes/series_routes.py` — `get_season_cast`
  (only existing season-level aggregate); `frontend/src/pages/SeasonPage.jsx`
- Alignment bug: `frontend/src/pages/SeriesPages.css:6-8` (`.series-page`); prior fix pattern
  at `frontend/src/pages/BillingPage.css` (`.billing-content`)

---

## Billing page and payment success messages — misaligned (screen-left instead of centered) — RESOLVED, fixed

**Status:** Done. Brainstormed, designed, planned, and implemented 2026-07-21.

**What shipped.** `BillingPage.jsx`/`.css` — header, error message, and the
card stack are now wrapped in a `.billing-content` container
(`max-width: 640px; margin: 0 auto;`), centering the page's content instead
of leaving it flush against the left padding on wide screens.
`PaymentResultPage.jsx` gained a dedicated `PaymentResultPage.css` and is now
a centered, card-styled result screen (matching `.billing-card`'s token
palette) with a per-state `lucide-react` icon: green `CheckCircle` once
settled, gray `Clock` while confirming, red `XCircle` on cancel. No changes
to checkout logic, polling, or the seat-invite resume redirect.

**References.**
- Design: `docs/superpowers/specs/2026-07-21-billing-alignment-fix-design.md`
- Plan: `docs/superpowers/plans/2026-07-21-billing-alignment-fix.md`
- `frontend/src/pages/BillingPage.jsx`, `BillingPage.css`
- `frontend/src/pages/PaymentResultPage.jsx`, `PaymentResultPage.css` (new)

---

## Better layout for the Breakdown credits and Team seats cards — RESOLVED, shipped

**Status:** Done. Brainstormed (3 visual mockups compared), designed, planned,
and implemented 2026-07-21.

**What shipped.** The Breakdown Credits and Team Seats sections on
`/billing` are now one card (`.billing-purchase-card`) with each purchase
as a compact horizontal row — icon badge (reusing the existing `Wallet`/
`Users` lucide-react icons), title + subtitle, quantity stepper, running
total, and a buy button — separated by a divider when both rows are
present. On narrow screens each row wraps via CSS flexbox (icon+text on
one line, stepper+total+button on the next) with no separate mobile
markup. The Annual Team License upsell card (shown instead of the seats
row for non-team accounts) is unchanged — it's a distinct action
(subscribe vs. buy-more), not a peer row. No changes to checkout logic,
`PRICE_ZAR`, or any purchase state/handlers.

**References.**
- Design: `docs/superpowers/specs/2026-07-21-billing-purchase-cards-layout-design.md`
- Plan: `docs/superpowers/plans/2026-07-21-billing-purchase-cards-layout.md`
- `frontend/src/pages/BillingPage.jsx`, `BillingPage.css`

---

## Team seat price change: R150 → R250 per seat — RESOLVED, shipped

**Status:** Done. Implemented, tested, and deployed to production 2026-07-22.

**What shipped.** Both price sources updated from `150` to `250`:
`backend/services/payfast_service.py`'s `PRICES['tier_2_seats']` (the
server-side source of truth for the actual PayFast charge) and
`frontend/src/pages/BillingPage.jsx`'s `PRICE_ZAR.tier_2_seats`
(display-only). Updated the two tests asserting the old amount
(`test_payfast_checkout_fields.py::test_compute_amount_multiplies_by_quantity`,
`test_payfast_itn_route.py::test_seats_grant_uses_intent_quantity`) and
recomputed every ZAR 150 reference and worked example in
`docs/SPEC_Tiered_Business_Model.md` to ZAR 250.

**Verification.** Full backend suite (422 tests) and frontend
`npm run build` pass. Pushed to `main` (`b3d4d7c`) and confirmed live:
Vercel auto-deployed via the GitHub webhook (`dpl_8reuQw8tpqAb1UWav7BesV7T168b`,
aliased to `app.slateone.studio`) and Railway redeployed the backend
from the same push.

**References.**
- `backend/services/payfast_service.py` — `compute_amount`, `PRICES`
- `frontend/src/pages/BillingPage.jsx` — `PRICE_ZAR`
- `docs/SPEC_Tiered_Business_Model.md`
- `backend/tests/test_payfast_checkout_fields.py`,
  `backend/tests/test_payfast_itn_route.py`

---

## No way for a user to downgrade from Teams (annual) back to Solo

**Status:** Not started — feature gap, no design yet.

**Context.** There is no cancel/downgrade path anywhere in the billing code
today — grep of `entitlement_service.py`, `payfast_routes.py`, and
`BillingPage.jsx` turns up no `cancel`/`downgrade`/`unsubscribe` route or
button. The only way a `tier_2_license` account currently loses team access
is the passive failed-renewal path (see "Failed-renewal downgrade gap"
above), which isn't built yet either and isn't something a user can trigger
on purpose. A Teams subscriber who wants to drop to Solo (pay-per-breakdown)
has no self-serve action to take.

**Why it matters.** Renewal automation (also open, above) will charge the
stored PayFast token automatically before expiry unless something stops it —
so this gap isn't just "missing UI," it risks auto-charging a user for
another year with no opt-out once that job exists.

**Scope when picked up.** Brainstorm before implementing — open questions:
what "downgrade" means given PayFast tokenization isn't true recurring
billing (is it just "let the current annual term lapse and don't renew" vs.
an immediate switch with a refund/proration?); whether it needs to void/clear
`profiles.subscription_payfast_token` so the (future) renewal job skips it;
what happens to existing team members/seats already granted under the
annual term; and where the action surfaces in `BillingPage.jsx` (needs a
visible "Cancel"/"Downgrade to Solo" control — currently absent).

**References.**
- `backend/services/entitlement_service.py` — `get_entitlement`,
  `subscription_status` handling
- `backend/db/migrations/042_payfast_tokenization.sql` —
  `profiles.subscription_payfast_token`
- `frontend/src/pages/BillingPage.jsx`
- Related open items: "Renewal automation not built", "Failed-renewal
  downgrade gap" (above)

---

## Landing page copy — reword — V1 RESOLVED, shipped; FAQ page still open

**Status:** V1 done. Brainstormed and designed
(`docs/superpowers/specs/2026-07-28-landing-page-redesign-design.md`),
planned (`docs/superpowers/plans/2026-07-28-landing-page-redesign.md`),
and implemented in the separate `~/slateone` marketing-site repo (not
this repo — see below), merged via PR #2 ("landing-redesign") to that
repo's `main` 2026-07-28.

**What shipped.** Reskinned every section of the marketing site from its
charcoal/neon-green/Space-Grotesk identity to the same slate/amber/Inter
visual system as the actual product app (stock Tailwind `slate-*`/
`amber-*` utilities, exact hex matches for `ScripDown_AI/frontend/src/index.css`'s
`--gray-*`/`--primary-*` variables — no custom Tailwind theme needed).
Hero copy was rewritten; nav, footer, `IndustryReality`, `BuiltFor`,
`Pricing`, `TierSelectionModal`, `LegalDocument` were reskinned (copy
unchanged on most — only Hero got a copy rewrite); `SystemArchitecture`
was deleted and folded into `OperatingLayer`. A follow-up commit
(`f6b30d8`) also visually separated the license fee from the per-seat
fee in the pricing card/modal.

**Still open:** a FAQ page. `docs/landing-faq.md` — the old FAQ copy
referencing the deprecated flat "$49/month" model — was never reconciled
with the two-tier model; a design spec for a new FAQ page
(`~/slateone` commit `18022e5`, "docs: add FAQ page design spec") exists
but is not yet implemented. Track that as the remainder of this item.

**References.**
- `~/slateone` (separate repo, not `ScripDown_AI`) — PR #2 "landing-redesign",
  merged to `main`; commit `18022e5` has the pending FAQ page design spec
- `docs/superpowers/specs/2026-07-28-landing-page-redesign-design.md`,
  `docs/superpowers/plans/2026-07-28-landing-page-redesign.md` (this repo)
- `docs/landing-faq.md` — stale FAQ copy, still needs the two-tier rewrite
- `docs/SPEC_Tiered_Business_Model.md` — current tier names/positioning
  ("Tier 1 — Pay-Per-Breakdown", "Tier 2 — Annual Team License") that FAQ
  copy needs to reflect

---

## SOLO / TEAMS pricing — change pricing

**Status:** Not started — feature request. No new numbers decided yet.

**Context.** Current pricing per `docs/SPEC_Tiered_Business_Model.md`:
- **Tier 1 (Solo)** — ZAR 450 per AI breakdown/analysis, pay-per-use, no team
  features.
- **Tier 2 (Teams)** — ZAR 1,850/year + ZAR 250 per seat, annual license,
  full team collaboration.

Pricing for both tiers needs to change; new numbers not yet decided —
needs a brainstorming pass to pick them and work through downstream impact.

**Downstream impact when picked up.** Prices aren't just copy — they're
referenced in billing logic and tests, not only marketing pages:
- `backend/services/entitlement_service.py` — tier constants (`TIER_1`,
  `TIER_2`) and any hardcoded amounts used when creating PayFast payment
  requests
- `backend/routes/payfast_routes.py` — ITN handling, amount verification
  against what was charged
- Any frontend pricing display (`BillingPage.jsx`, invite/seat-purchase
  quantity picker) that shows per-seat or per-breakdown cost to the user
- `docs/landing-faq.md` / `docs/SPEC_Tiered_Business_Model.md` — copy and
  spec both currently state the old numbers and would go stale

**References.**
- `docs/SPEC_Tiered_Business_Model.md` — §3 (current price points), §8
  (billing mechanics per tier)
- `backend/services/entitlement_service.py`, `backend/routes/payfast_routes.py`
- `frontend/src/pages/BillingPage.jsx`

---

## Character merge: uppercase/lowercase name variants won't merge — RESOLVED, fixed

**Status:** Done. Reproduced with a test, root-caused, fixed, and verified —
the `character_analyses` hypothesis originally noted here was wrong; the real
bug was simpler and in a different place.

**Root cause (confirmed via test, not the original hypothesis).** Both
`merge_characters` and `merge_locations` (`backend/routes/supabase_routes.py`)
deduped the alias list by comparing the *uppercased* alias against the
*uppercased* canonical name/place, then dropped any alias that matched —
intending to strip an accidentally-reselected canonical. That comparison
can't distinguish "alias is literally already the canonical spelling" from
"alias is a genuine case-only variant" (`John` vs `JOHN`), so a real
case-only duplicate always normalized to "identical to canonical" and got
filtered out of the alias list entirely — backend responded `400 No valid
aliases to merge` even though `scenes.characters`/`scenes.setting` still held
the literal differently-cased string, unrewritten. The frontend's
`normalizeForMerge` guard (`ScriptSummary.jsx`) had the identical bug for
characters: it upcased before the no-op check, so the request never even
reached the backend — it was blocked client-side with a false "these already
share the same name" toast.

**Fix.**
- `backend/routes/supabase_routes.py::merge_characters` — alias-dedup filter
  now excludes an alias only if its *raw* (pre-uppercase) spelling exactly
  equals `canonical_name`, not its uppercased form. A case-only alias is kept
  and gets rewritten to the canonical spelling by the existing scene-matching
  loop.
- `backend/routes/supabase_routes.py::merge_locations` — same fix shape:
  compare raw alias text against `canonical_place` verbatim, not `.upper()`
  vs `.upper()`.
- `frontend/src/components/scenes/ScriptSummary.jsx::normalizeForMerge` —
  dropped the character-specific uppercase branch; both types now just
  trim/collapse whitespace, so the client-side no-op guard no longer blocks
  a genuine case-only merge before it's sent.

**Verification.** `backend/tests/test_character_merge_case.py` (new) covers:
a case-only character alias (`JOHN`/`John`) merges and rewrites the scene's
`characters` array to the canonical spelling; the same for locations
(`VILLA`/`villa`); a truly identical alias (verbatim match to canonical) is
still correctly rejected as a no-op. Full backend suite (396 tests) and
frontend `npm run build` pass with no regressions.

**References.**
- `backend/routes/supabase_routes.py` — `merge_characters`, `merge_locations`
- `frontend/src/components/scenes/ScriptSummary.jsx` — `normalizeForMerge`
- `backend/tests/test_character_merge_case.py`

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

---

## Billing page UI/placement — RESOLVED, shipped

**Status:** Done. Brainstormed, designed, planned, and implemented
2026-07-21 across two merged branches.

**What shipped.** `/billing` stays its own top-level route (decided against
nesting inside `ProfilePage`). Restyled to match `ProfilePage`'s card-based
design language (`PageHeader`, `Spinner` loading state, `.billing-card`
sections using the same gray-800/900/700 tokens), plus a new "current plan"
summary card (tier label, status badge, breakdown/seat usage) that didn't
exist before. A "Billing" entry was added to the TopBar user dropdown next
to "Profile" — previously `/billing` had no direct nav entry point at all,
only contextual upgrade prompts or a manual URL. Follow-up same day: both
quantity pickers (breakdown credits, team seats) were changed from
fixed-preset dropdowns (1/5/10 and 1/2/3/5/10) to a click-only `−`/`+`
stepper, so any exact positive integer quantity is reachable — matching the
backend's only real constraint (`quantity >= 1`, no upper bound, confirmed
in `payfast_service.py::compute_amount`).

**References.**
- Design: `docs/superpowers/specs/2026-07-21-billing-page-redesign-design.md`,
  `docs/superpowers/specs/2026-07-21-billing-quantity-stepper-design.md`
- Plan: `docs/superpowers/plans/2026-07-21-billing-page-redesign.md`,
  `docs/superpowers/plans/2026-07-21-billing-quantity-stepper.md`
- `frontend/src/pages/BillingPage.jsx`, `BillingPage.css` (new)
- `frontend/src/components/layout/TopBar.jsx`, `Breadcrumb.jsx`

---

## Vercel git integration silently stopped auto-deploying `main` — RESOLVED, no recurrence

**Found:** 2026-07-21, pushing commit `6653400` (billing purchase-row
layout fix). **Worked around same day** via a manual CLI deploy.
**Confirmed isolated, 2026-07-22:** checked the project's actual Vercel
deployment history (`list_deployments`) — the deploy for `6653400`
itself carries `"gitDirty": "1"` and is missing every GitHub-webhook
metadata field (`githubRepoOwnerType`, `githubCommitVerification`,
`repoPushedAt`, etc.), confirming it really was the manual `vercel
--prod` CLI workaround. Both the push immediately before it (`503b61e`)
and the push immediately after it (`8c4f37b`) show clean webhook
metadata and deployed automatically with no manual intervention — the
integration recovered on its own for the very next push, and every
deployment recorded since has the same healthy webhook pattern. No
repeat across 10+ subsequent pushes. Treating this as a one-off GitHub
App delivery glitch, not a systemic break — no fallback deploy hook
needed unless it recurs.

**Further confirmed 2026-07-22:** push `6ee161a` (bundling this entry's
own update plus the R150→R250 seat price change) auto-deployed cleanly
— `dpl_8reuQw8tpqAb1UWav7BesV7T168b` built and went `READY` via the
GitHub webhook with no manual intervention, aliased to
`app.slateone.studio`.

**Context.** Every earlier push to `main` today (`503b61e`, `006ffad`,
etc.) triggered an automatic Vercel production deployment within about a
minute, confirmed via `vercel_list_deployments`. Push `6653400` did not —
`vercel_get_project` kept reporting the previous commit (`006ffad`) as
`latestDeployment` for several minutes with no new deployment ever
appearing for `6653400`. Confirmed via `gh api
repos/.../commits/6653400.../status`: Railway posted two commit statuses
for this SHA (both `success`), but **no Vercel status was ever posted at
all** — the GitHub App integration never picked up the push, this wasn't
just slow webhook delivery.

**Workaround applied.** Ran `vercel --prod --yes` manually from the repo
root (not `frontend/` — running it from inside `frontend/` fails with
"path .../frontend/frontend does not exist", because the linked
project's Root Directory setting is `frontend` relative to the repo root
where `.vercel/project.json` lives one level up from the CLI's cwd
expectation). This built and deployed the correct commit and aliased it
to `app.slateone.studio` successfully.

**Why deferred.** Single occurrence so far — could be a transient GitHub
App delivery glitch, or something about repeated pushes in quick
succession (several pushes happened within ~30 minutes today) that the
integration doesn't handle well. Not enough data yet to root-cause.

**Scope when picked up.** Watch the next few pushes to `main` for a
repeat. If it recurs: check the Vercel dashboard's Git integration
settings (Project → Settings → Git) for a disconnected/reinstalled
GitHub App, check GitHub's org-level "Installed GitHub Apps" settings for
Vercel's access/permissions, and check Vercel's own status page for
incidents around the affected timestamps. If it's a recurring quick-
succession issue, consider whether a deploy hook or CI step that calls
`vercel --prod` explicitly (rather than relying solely on the GitHub App
webhook) is worth adding as a fallback.

**References.**
- `frontend/.vercel/project.json` — linked project id or Vercel CLI
- Vercel dashboard: Project → Settings → Git (integration config)
- `gh api repos/Manakin-Wraith/scripdown_ai/commits/<sha>/status` — how
  the missing Vercel status was confirmed
