# Backlog

Deferred work items with enough context to pick up later. Each entry states the
gap, current state, and options — not a committed design. Brainstorm before
implementing (see `superpowers:brainstorming`).

---

# CURRENT PRIORITY — path to real revenue

**Decided 2026-08-27.** Near-term goal was to get to a state where real
customers can be charged. **Reached** — checkout is live (step 1). The
remaining billing-lifecycle steps (renewal, downgrade) are deferred until
scale; at current volume the account owner handles renewals and
cancellations manually. Product-depth work has since started on the P2
cluster: **Cast & Casting v1 shipped 2026-08-28** and **Cast tab v2 shipped
2026-08-29** (see entries below for what shipped and verification). Both
implement cast production data: v1 has cast contacts, headshots, availability
tracking, and schedule conflict detection; v2 adds full-body/multi-photo
gallery, cast tiers (leads/supporting/featured/background), background groups
by headcount, and in-app conflict resolution. Still ahead in that cluster:
crew + call sheets + sides, auto-scheduling, department workspaces.

## Priority snapshot — 2026-08-31

Ranked view of everything open below. Billing lifecycle stays deferred by
the 2026-08-27 decision; the active thrust is production-management depth.

**Production data model — DIRECTION DECIDED 2026-08-31.** Umbrella
brainstorm complete → `docs/superpowers/specs/2026-08-31-production-data-model-design.md`:
a top-level `production` entity (independent axis from series/seasons),
account-level `contacts` + `locations` directories, additive
`production_members` permission layer, `units` now, production-level
schedule later (per-script rollup first).

- **Step 1 ("the spine")** shipped to `main` 2026-08-31 — `production` entity,
  `/productions` + detail page, script association, migration 050
  (`docs/superpowers/plans/2026-08-31-production-spine.md`).
- **Step 2a (crew + contacts)** shipped to `main` 2026-08-31, merge `8e03750`
  — account-level `contacts` directory (`/contacts`), `production_crew`
  assignments + Crew tab, CSV crew import, all owner-only. Migrations 051 +
  updated 013 applied to Supabase. Spec `2026-08-31-crew-contacts-design.md`,
  plan `2026-08-31-crew-contacts.md`.

- **Step 2b (`production_members` permission layer)** shipped to `main`
  2026-09-02, merge `8477e82` — all 18 tasks done. Migration 052
  (`production_members` + `production_invites`) applied to Supabase;
  `production_authz` (`get_production_role` / `get_production_access` /
  `ROLE_RANK` / `CAPABILITIES`) + `require_production_role` decorator;
  crew routes re-gated with server-side redaction of `job_rate` / `phone` /
  `standard_rate`; `production_member_service` (role presets
  admin/coordinator/viewer + four override toggles, rank guardrails);
  member CRUD + email-based invite lifecycle (immediate for existing
  accounts, pending token invite otherwise; revoke / public token lookup /
  accept; auto-accept on login); `_fetch_seats_used` now unions the
  production axis deduped per person; `production_access` on GET-one +
  member-visible `list_productions`; route-enforcement regression test.
  Frontend: Members tab (roster, role/capability edits, invites,
  add-member modal), crew-tab write gating on `can_edit_crew`, public
  `ProductionInviteAccept` page, joined-productions role badge in the list.
  Spec `2026-09-01-production-members-design.md`, plan
  `2026-09-01-production-members.md`. Entitlement gate is keyed to the
  production OWNER (a coordinator adding a member can be blocked by the
  owner's missing seat — see item 9e for the messaging follow-up).
  Department-scoped script/report access for HODs stayed OUT of scope →
  its own brainstorm / umbrella step 7.

**Umbrella step 3: account-level `locations` directory — SHIPPED and
MERGED to `main` 2026-09-03 (13 tasks + a whole-branch review pass).**
Migration `053_locations.sql`
(`locations` + `production_locations` + `location_photos`) applied
manually to the Supabase project; `geocode_service` (Mapbox v6, degrades
to `None`); owner-scoped `location_service` (directory CRUD +
geocode-on-write + photos) and `locations_bp` (`/api/locations/*`);
`production_location_service` + `from_production_location_id` resolver +
4 link routes on `production_bp` gated by `can_edit_production`;
`MAPBOX_SECRET_TOKEN` added to `RECOMMENDED_VARS`. Frontend: `/locations`
directory page + nav link, `LocationFormModal` / `LocationDetailDrawer` /
`StaticMap`, `ProductionLocationsTab` + `LocationPickerModal` wired into
`ProductionDetailPage`. Backend suite 726 passed / 1 skipped; frontend
`npm run build` green. Review pass fixed 4 findings (no re-geocode on
unchanged address, search needle strips `()`, no half-populated
lat/lng, `update_link` verifies the link's production). `MAPBOX_SECRET_TOKEN`
(Railway) + `VITE_MAPBOX_PUBLIC_TOKEN` (Vercel, public `pk.` token, Prod +
Preview) set 2026-09-03 — a frontend redeploy bakes the Vite var in.
Migration 053 applied manually to slateone (the only environment). `main`
pushed 2026-09-03.

**START HERE — umbrella step 4: call sheets / sides.** Brainstorm first;
no spec/plan yet. The spine (step 1), crew + contacts (2a), the
`production_members` permission layer (2b), and the locations directory
(step 3) precede it.

**Step 3 deferred (not built):** scene-`setting`→location creative
mapping (own brainstorm), contact photos, CSV import for locations, AI
call-sheet parse.

**Step 3 follow-ups (small, non-blocking — fold into a hygiene pass):**
- Same parenthesis-in-search bug fixed in `location_service` still lives in
  `contact_service.py:42` — apply the identical `()` strip.
- `LocationFormModal` UI/UX pass (item 9f) — shipped functional, no design
  pass.

**2b follow-ups (small, non-blocking — fold into step 3 or a hygiene pass):**
- Members tab never had a design pass — see item 9e (esp. the
  owner-missing-seat error surface when a coordinator adds a member).
- A background commit-security-review's 3 findings (all adjudicated
  non-blocking: 2 defense-in-depth DB-scoping / payload-trim nits, 1 = the
  already-deferred Teams→Solo downgrade class) — revisit opportunistically.

**2a follow-ups (small, non-blocking — fold into 2b or a hygiene pass):**
- Verify `department=camera` in `frontend/public/crew-import-template.csv` is a
  real `departments` code/name (else the template's first example row is
  skipped on a user's first import).
- CSV import: no explicit >2,000-row cap (1 MB byte cap only); import is
  non-transactional so a huge file is a slow partial write.
- Crew tab uses `window.confirm` instead of the repo's `ConfirmDialogContext`.
- `GET /api/contacts?kind=<invalid>` returns `[]` instead of 400 (POST/PATCH
  validate the enum; GET doesn't).
- `update_crew`: a single-field PATCH (e.g. only `end_date`) that violates the
  date-order CHECK against an existing opposite bound surfaces as a clean 500
  via try/except, not a 400.

**Do next (unblocks the most):**
1. **Umbrella step 4: call sheets / sides** (see START HERE above) — the
   headline next slice, now that step 3 (locations) has shipped to `main`.
   Brainstorm first; no spec/plan yet.
2. **Cast & Casting v1 closeout** (cheap, ~1 session): `TriangleAlert`→`AlertTriangle`
   icon consistency (cosmetic). Task 13 (DOOD conflict overlay) remains open
   but not blocking v1. Docs entry now complete via Cast tab v2
   SLATEONE_FEATURES.md section.
3. **Auto AI scheduling (first pass) — brainstorm.** Cast availability now
   exists as a real constraint; biggest "breakdown tool → scheduling
   tool" jump. Consumes the production/units/crew model.

**Solid, no hard dependency (pick up between the above):**
6. Breakdown element CRUD drill-down (+ extras CRUD as the first concrete
   type) — recurring need to correct AI output.
7. Separate Location (production) from Sets (creative).
8. Series page redesign + finish-or-drop `worktree-series-accordion`,
   style `SeriesAssignmentModal`.
9. Report version control; CSV export industry-standard audit.
9a. Cast drawer (`CastingDetailPanel`) UI/UX layout pass — cosmetic,
    brainstorm-then-build; drawer grew organically across Cast v1/v2.
9b. Production pages UI/UX pass — `/productions` list + `ProductionDetailPage`
    (Overview/Crew tabs, script picker, crew roster, CSV import modal).
    Shipped functional across the spine + step 2a; never had a design pass.
    Brainstorm-then-build, cosmetic.
9c. Contacts page UI/UX pass — the new `/contacts` account-level directory
    (list, add/edit contact, kind filter, sensitive-field display) shipped
    functional in step 2a but never had a design pass. Brainstorm-then-build,
    cosmetic.
9d. Crew tab UI/UX pass — the new Crew tab on `ProductionDetailPage`
    (crew roster, department grouping, add-from-contacts, CSV import modal,
    job/rate fields) shipped functional in step 2a but never had a design
    pass. Brainstorm-then-build, cosmetic.
9e. Members tab UI/UX pass — the Members tab on `ProductionDetailPage`
    (roster, role/capability edits, invites, add-member modal) shipped
    functional in slice 2b but never had a design pass. Brainstorm-then-build.
    Specifically review the alerts/messaging when adding a member while the
    owner has not yet bought a seat — the entitlement gate is keyed to the
    production OWNER, so a coordinator adding a member can be blocked by the
    owner's missing seat; the current error surface for that case needs a
    clear, actionable message (who needs to buy a seat, and where).
9f. Locations pages UI/UX pass — the `/locations` directory, the detail
    drawer (fields + map + photo grid), and the `ProductionLocationsTab`
    (linked-locations table + inline notes + picker modal) all shipped
    functional in step 3, modelled on the contacts/crew chrome, with no
    design pass. Brainstorm-then-build, cosmetic.

**Infra / hygiene:**
10. Flip `backend-tests` CI check to required; add a frontend
    `npm run build` gate.
11. FAQ page (in the `~/slateone` repo — spec already written).
12. Revision-import: FDX path + test coverage + confirm selective
    re-analysis. FDX Tagger ingestion stays blocked on a sample file.

**Deferred by decision — revisit at scale:** renewal automation,
failed-renewal downgrade, Teams→Solo downgrade, live PayFast ITN inbound
verification (opportunistic, with the first real transaction).

**Untracked big rocks (specs exist, not yet on this list):** see
"Roadmap specs — status" at the bottom of this file (DPR, Narrative
Intelligence Dashboard, Production Analytics, On-Set Offline, Wrap
Reports).

---

**1. PayFast: sandbox → live credentials. — DONE (outbound verified 2026-08-27).**
Live merchant creds set in Railway, `PAYFAST_SANDBOX` effectively off. Verified
outbound: a real checkout POSTs to `https://payment.payfast.io/eng/process`
(live, not sandbox) and live PayFast returns `302` (merchant ID / key /
passphrase mutually valid). *Residual:* the inbound ITN → grant path has not
been exercised on live — close it opportunistically with the first real
completed transaction (check `payfast_transactions` row goes `complete` with a
real `pf_payment_id`, `reject_reason` null, grant lands).

**2. SOLO / TEAMS pricing change. — DROPPED 2026-08-27.** Current prices
(Solo R2,250/breakdown; Team License R1,850 / R5,500 / R9,500 / R18,500 per
cadence with 0/1/2/3 seats; extra seat flat R250/mo) are being kept as-is.
The "SOLO / TEAMS pricing — change pricing" entry below is stale (references
old R450 / R1,850-per-year numbers) — retained for history only, not
actionable.

**3. Renewal automation. — DEFERRED until scale 2026-08-27.** Brainstorm
started and stopped: the account owner will handle Team License renewals
manually (charge the stored PayFast token via the dashboard / adhoc API by
hand) while volume is low. Pick this up when manual renewal tracking
becomes a burden. Full context in "Renewal automation not built" below.

**4. Failed-renewal downgrade. — DEFERRED (blocked on step 3).** No
automated renewal means no automated failure to react to. Manual for now.
See "Failed-renewal downgrade gap".

**5. Teams → Solo downgrade path. — DEFERRED until scale 2026-08-27.** With
manual renewals, a customer who wants out is simply not re-charged; no
self-serve control needed yet. Revisit alongside step 3. See "No way for a
user to downgrade from Teams (annual) back to Solo".

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

## Report Studio: CSV export — RESOLVED, shipped

**Status:** Done. Brainstormed and implemented 2026-08-13.

**What shipped.** `ReportService.generate_csv(report_id)`
(`backend/services/report_service.py`) reads a saved report's existing
`data_snapshot` — the exact same aggregate the PDF/preview render from — and
dispatches to a per-type row builder for the 7 tabular report types
(`scene_breakdown`, `one_liner`, `shooting_schedule`, `day_out_of_days`,
`location`, `props`, `wardrobe`); `full_breakdown` is excluded (narrative
document, not a table) and raises `ValueError`. New route
`GET /api/reports/reports/<report_id>/csv`, mirroring the existing `/pdf`
route's auth/ownership checks (`@require_auth` +
`@require_script_role('viewer', resolver=from_report)`), plus a matching
public `GET /api/reports/shared/<share_token>/csv` for share links. Frontend
`downloadReportCsv(reportId, title)` (`apiService.js`) follows the existing
`downloadStripboardPdf` blob-download pattern. A "Download CSV" button sits
next to the existing PDF download in both `ReportStudio.jsx`'s toolbar and
`ReportLibraryDrawer.jsx`'s per-report row actions, disabled/hidden for
`full_breakdown`.

**Verification.** `backend/tests/test_report_csv.py` (new, 17 tests): route
auth/forbidden/ok/404/400 cases (mirroring `test_report_auth.py`'s pattern),
shared-link CSV, and header/row-shape assertions for every exportable report
type including both the schedule-based and scene-fallback branches of
`one_liner`/`day_out_of_days`. Full backend suite (467 tests) and frontend
`npm run build` pass.

**References.**
- `backend/services/report_service.py` — `generate_csv`,
  `_csv_rows_for_report`, `_csv_*` per-type builders
- `backend/routes/report_routes.py` — `download_csv`, `download_shared_csv`
- `backend/tests/test_report_csv.py`
- `frontend/src/services/apiService.js` — `downloadReportCsv`
- `frontend/src/components/reports/ReportStudio.jsx`,
  `ReportLibraryDrawer.jsx`

---

## Department-specific reporting — RESOLVED, shipped

**Status:** Done. Brainstormed and implemented 2026-08-13/14.

**What shipped.** All six previously-unreachable renderers
(`makeup`, `sfx`, `stunts`, `vehicles`, `animals`, `extras`) are now
real, generatable report types: added to `REPORT_TYPES`
(`backend/services/report_service.py`), each with a matching
`_csv_*_department` builder registered in `_csv_rows_for_report` (so
`CSV_EXPORTABLE_TYPES`, which derives from `REPORT_TYPES`, picks them
up automatically). `aggregate_scene_data`'s six per-category loops
gained `story_days` tracking (matching props/wardrobe) so their CSV
exports have the same "Story Days" column. `reportIcons.js` gained
real icons for `makeup`/`vehicles`/`animals` (`sfx`/`stunts`/`extras`
already had icons). No route or `ReportRail.jsx` changes were needed —
both already render/validate off `REPORT_TYPES`'s keys, so the six new
entries "fell out for free" once added.

**Verification.** 12 new tests in `backend/tests/test_report_csv.py`
(CSV header/row shape per type, plus a combined valid-type/renders-HTML
check). Full backend suite (474/474) and `npm run build` pass.

**Original context (kept for history).** Found 2026-08-13 while implementing CSV export.
`ReportService._render_report_html` (`backend/services/report_service.py`)
dispatches on six department report types beyond `wardrobe` —
`makeup`, `sfx`/`special_effects`, `stunts`, `vehicles`, `animals`,
`extras` — each with its own `_render_*_department` renderer (item name,
associated character(s) where relevant, scene count, scene numbers). But
`REPORT_TYPES` (the dict `generate_report`/`generate_report`'s route
validation actually checks against — `backend/routes/report_routes.py:240`)
only contains 8 keys: `scene_breakdown`, `day_out_of_days`, `location`,
`props`, `wardrobe`, `one_liner`, `shooting_schedule`, `full_breakdown`.
`wardrobe` is reachable as a real report type; the other six are not — a
request for `report_type: "makeup"` (etc.) is rejected with 400 by the route
before `generate_report` ever runs, so those renderers are currently dead
code, unreachable from the UI or API. `ReportRail.jsx`'s type picker only
ever offers whatever `GET /report-types` returns, which is sourced from the
same 8-key `REPORT_TYPES` dict.

**Why it matters.** Wardrobe already gets its own dedicated department
report (item → character(s) → scenes); makeup, SFX, stunts, vehicles,
animals, and extras data is all aggregated the same way in
`aggregate_scene_data` (`data['makeup']`, `data['special_effects']`,
`data['stunts']`, `data['vehicles']`, `data['animals']`, `data['extras']` —
same `{count, scenes, ...}` shape as wardrobe/props) and the render code to
turn it into a report already exists — it's just not wired up to be
generatable. A production AD/department head would plausibly want a
standalone SFX or stunts breakdown the same way they'd want a props or
wardrobe one.

**Scope when picked up.** Brainstorm before implementing (see
`superpowers:brainstorming`) — open questions: is exposing the six existing
renderers as real, generatable report types the right scope, or does each
department warrant a different shape than what's already written (the
existing renderers were written speculatively and never validated against
real production use); whether `REPORT_TYPES` should just gain the six
missing keys (cheap) plus corresponding CSV builders
(`ReportService._csv_rows_for_report`, which currently only covers the 7
CSV-exportable types) if CSV export should cover them too; and whether
`ReportRail.jsx`'s UI needs any department-specific grouping/iconography
beyond just listing six more options.

**References.**
- `backend/services/report_service.py` — `REPORT_TYPES` (reachable types),
  `ReportConfig.VALID_REPORT_TYPES` (broader list, includes the six),
  `_render_makeup_department`, `_render_sfx_department`,
  `_render_stunts_department`, `_render_vehicles_department`,
  `_render_animals_department`, `_render_extras_department` (existing but
  unreachable renderers), `aggregate_scene_data` (already aggregates all six)
- `backend/routes/report_routes.py:240` — route-level validation against
  `REPORT_TYPES`, the actual gate
- `frontend/src/components/reports/ReportRail.jsx` — report type picker
- `backend/tests/test_report_csv.py` — new coverage for the six shipped types
- `frontend/src/components/reports/reportIcons.js` — makeup/vehicles/animals icons

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

---

## Separate Location (production element) from Sets (creative element)

**Status:** Not started — feature request, needs brainstorming. Related:
the production data model spec
(`docs/superpowers/specs/2026-08-31-production-data-model-design.md`)
defines an account-level `locations` directory (real places: address,
contacts, permits, photos) but **explicitly defers the scene-`setting`
→ real-`location` mapping mechanism to this brainstorm.** Pick this up
after the `locations` directory ships (build-sequence step 3); this
item is then the mapping layer on top of it.

**Context.** The breakdown currently conflates two distinct concepts under
one "location" idea: the physical shooting **Location** (a production/
logistics concern — where the crew actually goes, used for scheduling and
company moves) and the **Set** (a creative/story concern — the fictional
place a scene is set, e.g. "INT. KITCHEN" vs. the real house that kitchen is
shot in). Today's extraction and breakdown UI treat these as one field.

**Scope when picked up.** Brainstorm before implementing — open questions:
whether this needs a schema change (a `sets` table separate from
`locations`/`scenes.setting`) or just a UI/labeling split over existing data;
how AI extraction should populate both (a scene heading gives the Set
directly, but Location requires either user input or an AI guess); and how
this interacts with location-based scheduling/stripboard grouping, which
currently keys off the single conflated field.

**References.**
- `backend/services/entity_resolver.py` — existing location dedup/merge logic
- `backend/routes/supabase_routes.py` — `merge_locations`
- Scene extraction pipeline: `backend/services/extraction_pipeline.py`

---

## Breakdown UI/UX drill-down (CRUD) for elements

**Status:** Not started — feature request, needs brainstorming.

**Context.** Today's breakdown view surfaces AI-extracted elements
(characters, props, wardrobe, etc.) largely as read-only lists tied to
scenes. There's no dedicated drill-down surface for a single element (e.g.
a character) showing all its appearances, notes, or metadata in one place,
and no direct create/edit/delete affordance for individual elements outside
scene-level editing.

**Scope when picked up.** Brainstorm before implementing — open questions:
which element types get drill-down first (characters/props are likely
highest value); whether CRUD operates on the element identity itself
(rename/merge, already partially covered by `merge_characters`/
`merge_locations`) vs. per-scene appearance data; and where this surfaces in
the UI (a dedicated detail panel/modal vs. an expanded row in the existing
breakdown table).

**References.**
- `frontend/src/components/breakdown/` — existing breakdown UI components
- `backend/routes/supabase_routes.py` — `merge_characters`, `merge_locations`
  (existing identity-level CRUD to build on)

---

## Extras / background artists — needs CRUD editing

**Status:** Not started — needs brainstorming.

**Context.** Found 2026-08-14 while shipping department-specific reporting.
Extras/background-artist entries are AI-extracted per scene
(`scene.get('extras')`, aggregated into `data['extras']` by
`aggregate_scene_data` in `backend/services/report_service.py`) and are now
reportable (see "Department-specific reporting" above), but there's no
user-facing way to create, edit, rename, split, or delete an extras entry —
same read-only-list gap as the general breakdown CRUD item above, but
extras/background artists specifically haven't been scoped at all yet.

**Why it matters.** AI extraction of background/extras counts and
descriptions is inherently approximate (e.g. "bar patrons" vs. "3 bar
patrons" vs. "background diners") — a production AD needs to correct,
consolidate, or add entries by hand, the same way props/wardrobe/cast
already need occasional manual correction elsewhere in the breakdown UI.

**Scope when picked up.** Brainstorm before implementing (see
`superpowers:brainstorming`) — open questions: does this ride on the
general "Breakdown UI/UX drill-down (CRUD) for elements" item above (same
mechanism, extras as the first/a concrete element type) or get its own
surface; whether edits apply at the identity level (rename/merge an extras
group across all its scenes) vs. per-scene appearance edits; whether a
count/quantity field belongs on each entry (distinct from most other
breakdown categories, which are just item + scenes); and how edits should
interact with re-analysis (does a manual edit survive an AI re-run on that
scene, or an FDX/PDF revision import).

**References.**
- `backend/services/report_service.py` — `aggregate_scene_data`'s `extras`
  loop, `_render_extras_department`, `_csv_extras_department`
- Related, broader-scoped item: "Breakdown UI/UX drill-down (CRUD) for
  elements" (above) — likely the mechanism this should build on
- `frontend/src/components/breakdown/` — existing breakdown UI components

---

## CSV export format isn't industry-standard

**Status:** Not started — needs brainstorming.

**Context.** Found 2026-08-20. The CSV export shipped in "Report Studio:
CSV export" (above) writes each report type's own ad hoc column set
straight from `data_snapshot` — it was designed to mirror the PDF/preview
layout, not to match what production software (Movie Magic Scheduling,
Gorilla, StudioBinder, etc.) or a line producer/1st AD expects when they
import a stripboard/schedule/breakdown CSV into their own tooling. No
audit has been done yet of where today's columns/headers/ordering/date
formats diverge from what's actually treated as "standard" in the
industry.

**Scope when picked up.** Brainstorm before implementing (see
`superpowers:brainstorming`) — open questions: what "industry standard"
concretely means per report type (there may be no single standard —
Movie Magic and Gorilla export formats differ from each other); whether
to match an existing tool's column schema for interop (so a CSV round-trips
into that tool) or just clean up general CSV hygiene (consistent scene
numbering, INT/EXT and D/N codes, page-eighths formatting, UTF-8 BOM for
Excel, date formats); whether this varies per report type (`scene_breakdown`
vs `shooting_schedule` vs `day_out_of_days` likely need different
conventions) or is one global format pass; and whether it's worth an actual
interview/reference pull from a working AD/scheduler on what they currently
import CSVs into.

**References.**
- `backend/services/report_service.py` — `generate_csv`,
  `_csv_rows_for_report`, per-type `_csv_*` builders (current formats to
  audit against)
- `backend/tests/test_report_csv.py` — current header/row-shape assertions,
  will need updating alongside any format change
- "Report Studio: CSV export — RESOLVED, shipped" (above) — what shipped
  and why, for context on the current column choices

---

## Cast & Casting v1 (cast contacts, headshots, availability + conflicts) — SHIPPED, verified in production; Task 13 + polish open

**Status:** v1 shipped and verified end-to-end in production 2026-08-28.
Brainstormed → designed → planned → built via
`superpowers:subagent-driven-development` across 12 tasks (Tasks 1–7
backend, 8–12 frontend), plus a whole-branch review and four follow-up
fixes/features the same day. This is the **cast slice** of the broader
"Add CREW, CAST and production detail…" backlog entry below — crew, call
sheets, sides, and per-shoot-day production detail are still unbuilt.

**Context (kept for history).** Raised 2026-08-20. Before this, the
breakdown/schedule carried only AI-extracted *script* data — no way to
attach who's cast, contact details, a headshot, or blackout dates, so a
1st AD couldn't catch a scheduling conflict inside the app.

**What shipped.**
- **Schema** (`migration 048`): `casting` (one row per script × character
  — `actor_name`, `status` ∈ wishlist/offer/booked/declined/released,
  contact phone/email/agent, `headshot_path`, `notes`) and
  `casting_unavailability` (`casting_id`, `start_date`, `end_date`,
  `reason`).
- **Backend** (`services/casting_service.py`, `routes/casting_routes.py`):
  CRUD at `GET/POST /api/scripts/:id/casting`,
  `PATCH/DELETE /api/casting/:id`, unavailability add/remove, headshot
  upload (`POST /api/casting/:id/headshot` → Supabase `scripts` bucket at
  `casting/<script_id>/<casting_id>.<ext>`, 1h signed URLs, type/size
  validated server-side), and `GET /api/scripts/:id/casting/conflicts`.
  Auth via `@require_script_role` (viewer to read, admin to edit). A merge
  hook carries casting rows to the canonical name when characters merge.
- **Conflict engine** (`casting_service.compute_conflicts`): a conflict is
  a `booked`/`offer` casting whose unavailability range overlaps a **dated**
  shoot day that contains a scene featuring that character (alias-resolved
  via the same `character_aliases` map). Each conflict row carries
  `scene_ids` so the UI can pinpoint the exact cards.
- **Frontend**: Cast section (`/scripts/:id/cast`, `CastPage` + `CastRow` +
  `StatusBadge`), a detail drawer (`CastingDetailPanel` + autosave on blur
  + `UnavailabilityEditor`), 8 `apiService.js` methods, and schedule
  integration — `ConflictPanel` banner, red day-header dots
  (`DayColumn`), and per-scene-card danger rings + "⚠ <actor> unavailable"
  notes (`ScheduleSceneCard`). Conflicts **re-check automatically** on any
  schedule composition change (scene moved between days, shoot date
  changed, day added/removed) with an "updating…" indicator; stale rings
  hold until the fresh backend result lands (no wrong-way flash).

**Follow-up commits (all 2026-08-28, on `main`).**
- `e2388d1` — review fix: detail drawer unmounted on every autosave
  (`onChanged` reused the loading-toggling `load`); split into a silent
  `refresh`, added `onCreated` + an in-flight create guard.
- `180247a` — conflicted scene-card highlighting (the `scene_ids`
  addition + rings/notes) + 3 backend tests.
- `a003324` — unavailability list wasn't updating after add:
  `CastPage.refresh` swallowed refetch errors and had ~1.5s latency;
  `UnavailabilityEditor` now renders from optimistic local state
  (append on add, remove-with-restore, "Adding…" state).
- `3d21b9c` — Cast page had no breadcrumb / section tabs: the
  `/scripts/:id/cast` route was never added to `MainLayout.deriveScriptId`
  or `Breadcrumb.ROUTE_CONFIG`.
- `9e56770` — the schedule conflict re-check + "updating…" indicator.

**Verification.** Backend `pytest tests/` green (511+). Frontend `npm run
build` green. Live in production against a real script: casting CRUD,
status change, headshot upload, unavailability add (appears instantly),
and the full conflict flow — banner + day dots + scene-card rings all
propagate correctly when a scene is dragged between days or a shoot date
changes.

**Still open.**
- **Task 13 (optional, never built): Day Out of Days conflict overlay.**
  Full step-by-step spec is in the plan (`Task 13`) — thread
  `compute_conflicts` output into `_render_day_out_of_days` /
  `_render_day_out_of_days_from_scenes` and ring the conflicted
  `(character, day)` work-mark cell in the DOOD PDF/preview, plus a
  footnote. Deferred because the Schedule panel is the primary surface.
- **Review Important #3 (minor):** `CastingDetailPanel`'s text fields use
  uncontrolled `defaultValue`, so a server-side normalized value isn't
  reflected until the drawer remounts. Low impact (editable fields are
  free text).
- **Minor:** new casting code uses `TriangleAlert` / `Contact` icons; the
  rest of the repo uses `AlertTriangle`. Cosmetic.
- **Phase 2 ideas** (from the specs, not scoped): bulk status actions,
  richer filtering, cast rollup on reports, and extending the same
  pattern to crew.
- **Cast tab v2** (new, 2026-08-29): full-body/additional photos, cast
  tiers (leads/supporting/background), extras as groups not one row
  each, and a conflict-resolution workflow (act on a flagged scheduled
  scene instead of only surfacing it). Own brainstorm entry below.
- **Docs:** not yet in `docs/SLATEONE_FEATURES.md` (the product
  capability overview) — add a "Cast & Casting" section the way Series
  was added after it shipped.

**References.**
- Plan: `docs/superpowers/plans/2026-08-27-cast-casting-v1.md`
- Specs: `docs/superpowers/specs/2026-08-27-cast-casting-v1-design.md`,
  `…-cast-casting-v1-ui-ux.md`
- SDD ledger: `.superpowers/sdd/2026-08-27-cast-casting-v1/progress.md`
  (Tasks 1–7 + the 2026-08-28 follow-ups)
- `backend/db/migrations/048_*.sql`, `backend/services/casting_service.py`,
  `backend/routes/casting_routes.py`, `backend/tests/test_casting_*.py`
- `frontend/src/components/cast/`, `frontend/src/components/schedule/`
  (`ConflictPanel`, `DayColumn`, `ScheduleKanban`, `ScheduleSceneCard`,
  `ShootingSchedulePage`), `frontend/src/services/apiService.js`
- `backend/services/report_service.py` — Day Out of Days, the Task 13
  target

---

## Cast tab v2 — full-body photo, cast tiers, extras as groups, conflict resolution — SHIPPED, verified

**Status:** v2 shipped and verified 2026-08-29. Brainstormed → designed → planned
→ built via `superpowers:subagent-driven-development` across 14 tasks (Tasks
1–14 distributed backend/frontend/db), all merged to `main`. Builds directly on
the shipped "Cast & Casting v1" entry (the `casting` / `casting_unavailability`
tables, `casting_service`, `CastPage`, and the schedule conflict engine);
extends and reshapes the Cast tab and backend services with four integrated
threads (photos, tiers, groups, conflict resolution).

**What shipped.**
- **Schema** (`migration 049`): `casting.tier` enum (lead/supporting/featured/
  background, default supporting; all 48+ existing rows backfilled); new
  `casting_photos` table (casting_id, path, kind ∈ headshot/full_body/other,
  created_at, ordering); `casting_groups` table (script_id, label, headcount,
  status, day_rate, notes); `casting_group_scenes` junction table (group_id,
  scene_id); `shooting_day_scenes.conflict_ack`, `conflict_ack_reason`,
  `conflict_ack_at`, `conflict_ack_by`; plus a database trigger clearing the
  ack when a day's `shoot_date` changes.
- **Backend** (`services/casting_service.py`, `routes/casting_routes.py`):
  `tier` added to cast record and updatable `PATCH /api/casting/:id` fields;
  `serialize` includes `tier`, `photos` array (with `from_casting_photo`
  resolver). Multi-photo routes: `POST /api/casting/:id/photos?kind=<kind>`
  (store to Supabase `scripts` bucket), `GET /api/casting/:id/photos`,
  `DELETE /api/casting/photos/:id`. New `casting_group_service`: `list_groups`,
  `create_group`, `update_group`, `delete_group`, `set_group_scenes`; five
  routes (`GET/POST /api/scripts/:id/casting-groups`, `PATCH/DELETE
  /api/casting-groups/:id`, `PUT /api/casting-groups/:id/scenes`) + 
  `from_casting_group` resolver.
- **Conflict engine** (`casting_service.compute_conflicts`): tier-filtered to
  lead/supporting/featured booked/offer cast only (background groups excluded);
  skips acknowledged (shooting_day_id, character_name) rows; returns them under
  `acknowledged` key; computes `suggested_day` (earliest dated day with no
  conflict for that scene's featured principals). New endpoint `PATCH
  /api/shooting-days/:day/scenes/:scene/conflict-ack` (member+ role) to
  record ack + reason + timestamp.
- **Frontend**: Cast page restructured into Principals / Background sub-tabs.
  Principals = 4 collapsible tier sections (Leads, Supporting, Featured,
  Uncast); collapse state persisted per-script in localStorage. Background =
  individual background-tier rows + "Groups" list (label × headcount · N scenes
  · status) + "New group" button + empty states. `TierBadge` component chips
  on every cast row. Casting drawer: tier + status on one row, all text fields
  controlled (no uncontrolled `defaultValue`); multi-photo gallery (primary
  headshot + "N more" expander + kind-tagged thumbnails + add button);
  Availability editor hidden for background tier. New `CastingGroupPanel`
  drawer (label, headcount, status, day-rate input with R prefix, scene
  checkbox multi-select with debounced save, notes, delete; read-only for
  non-admin). Schedule Kanban: conflicted scene cards get a "Resolve" button;
  `ConflictPanel` expandable conflict rows each with **Move to Day N**
  (suggested; disabled "No conflict-free day" when unavailable) / **Unassign**
  / **Acknowledge** (with reason modal); collapsed "Acknowledged (N)" section
  with **Un-acknowledge** action.
- **Testing & verification:** Backend suite 553 passed / 1 skipped
  (`backend/tests/` — the skipped test is the database trigger, covered via
  manual verification). Frontend `npm run build` green. Live manual verification
  of UI flows pending (user batch test).

**Still open.**
- **Task 13 (optional, never built): Day Out of Days conflict overlay.**
  Thread `compute_conflicts` output into `_render_day_out_of_days` and ring
  conflicted `(character, day)` cells in the DOOD PDF/preview, plus a footnote.
  Deferred because the Schedule panel is the primary conflict surface.
- **Call sheets / sides:** Crew + production detail (call times, location
  addresses, contacts, shoot parameters) remains unbuilt; call sheet/sides
  generation is blocked on that scope, the "Production data model" brainstorm,
  and the "Crew" item below.
- **Groups in reports / extras seeding:** Background groups don't yet appear
  in production reports; groups aren't pre-seeded from the AI `scenes.extras`
  breakdown. Deferred.
- **v1 visual polish — cosmetic:** New casting code uses `TriangleAlert` /
  `Contact` icons while the rest of the repo uses `AlertTriangle`. Purely
  cosmetic, no impact on functionality.

**Follow-up — non-blocking minors (from final review, 2026-08-29).** None
block the ship; batch them into a cleanup session.
- `casting_group_service.set_group_scenes` isn't transactional — a mid-loop
  failure leaves the scene set half-updated (delete-then-insert with no
  rollback).
- `delete_casting_photo` returns 200 for a non-existent id (no existence
  check → silent no-op looks like success).
- `store_photo` orphans the uploaded blob in Storage if the row insert
  fails afterward. Pre-existing pattern (v1 headshot upload does the same).
- `ConflictPanel` shares one reason-input value across all conflict rows —
  typing a reason for one row shows it under every row until submit.
- `CastPage.jsx` is ~430 lines — split out the sub-tab / tier-section
  rendering.
- Photo gallery has no "Remove" for the primary photo (matches v1 behaviour;
  only added photos are removable).
- `backend/tests/test_route_enforcement.py` doesn't cover the `casting.`
  blueprint — add `"casting."` to `BLUEPRINT_PREFIXES` plus the new route arg
  names. Would also retro-cover the v1 casting routes.

**Verification evidence.**
- Backend: `pytest tests/` = 553 passed, 1 skipped (DB trigger, manually verified)
- Frontend: `npm run build` green
- Migration 049: applied manually to development database
- Live manual testing: casting CRUD, status/tier change, multi-photo gallery,
  background groups, conflict detection, and conflict resolution (move/unassign/
  acknowledge) all verified working. User batch verification pending.

**References.**
- Design: `docs/superpowers/specs/2026-08-28-cast-tab-v2-design.md` (schema,
  workflow, tier/group model)
- Plan: `docs/superpowers/plans/2026-08-29-cast-tab-v2.md` (14-task breakdown)
- SDD ledger: `.superpowers/sdd/2026-08-29-cast-tab-v2/progress.md` (Tasks 1–14)
- `backend/db/migrations/049_*.sql` (tier, photos, groups, conflict ack)
- `backend/services/casting_service.py` (serialize, tier filtering, conflict engine)
- `backend/services/casting_group_service.py` (new, groups CRUD)
- `backend/routes/casting_routes.py` (photo/group endpoints), `schedule_routes.py`
  (conflict-ack endpoint)
- `backend/tests/test_casting_*.py` (passing), `test_casting_groups_*.py` (passing)
- `frontend/src/components/cast/` (CastPage, Principals/Background tabs, TierBadge,
  CastingDetailPanel multi-photo gallery, CastingGroupPanel)
- `frontend/src/components/schedule/` (ConflictPanel conflict resolution UI,
  ScheduleSceneCard Resolve button, conflict visualization)
- Cast & Casting v1 (above) — built on top of v1's schema, service, conflict engine

---

## Cast drawer (CastingDetailPanel) UI/UX — needs a layout pass — brainstorm

**Status:** Not started — needs brainstorming. Cosmetic/UX only; the drawer
is functionally complete and verified (see "Cast tab v2" above).

**Context.** `frontend/src/components/cast/CastingDetailPanel.jsx` grew
organically across Cast v1 and v2 — it now carries contact fields, tier +
status on one row, the multi-photo gallery (primary headshot + "N more"
expander + kind-tagged thumbnails + add button), the availability editor,
and notes. The layout was never designed as a whole; fields and controls
were appended as each thread shipped. It reads as a stack of unrelated
sections rather than a considered form.

**What to look at when picked up.** Brainstorm before implementing (see
`superpowers:brainstorming`) — open questions:
- Overall information hierarchy: what a user needs first (identity, photo,
  tier/status) vs. secondary (contact detail, availability, notes), and
  grouping/sectioning to match.
- Photo gallery placement and sizing — it's the most visually prominent
  element but currently sits mid-stack.
- Field grouping and alignment (contact block, casting block, scheduling
  block), consistent spacing, and whether a two-column layout helps on
  wider drawers.
- Consistency with the other drawer in this area, `CastingGroupPanel.jsx`,
  and with the app's existing panel/drawer chrome.
- Whether any of this overlaps with the pending `CastPage.jsx` split-out
  noted in the Cast tab v2 follow-ups.

**References.**
- `frontend/src/components/cast/CastingDetailPanel.jsx`, `CastingDetailPanel.css`
- `frontend/src/components/cast/PhotoGallery.jsx`, `UnavailabilityEditor.jsx`,
  `TierBadge.jsx`, `StatusBadge.jsx`
- `frontend/src/components/cast/CastingGroupPanel.jsx` — sibling drawer
- "Cast tab v2" (above) — what the drawer currently contains and why

---

## Redesign the Series page UI/UX — brainstorm

**Status:** Not started — needs brainstorming.

**Context.** The Series/Season surface has grown by accretion across four
merged rounds (Phase 1 grouping, My-Scripts nesting, known-series picker,
the paused accordion branch) plus a visual polish pass — see "Series /
multi-episode analysis" above for the full history. The result is a set of
pages (`SeriesListPage.jsx`, `SeasonPage.jsx`, the deleted-but-not-merged
`SeriesDetailPage.jsx`) that were each styled in isolation rather than
designed as one coherent workspace. `SeasonPage.jsx` today shows only the
combined cast table; there is no series/season dashboard, no at-a-glance
sense of episode status, and `SeriesAssignmentModal` is still unstyled.

**Why it matters.** As soon as a user has more than a couple of episodes,
the Series page is where they'll live to navigate and manage the season —
but it currently offers less than the grouped My Scripts table does. It
needs to be a real destination, not a thin index.

**Scope when picked up.** Brainstorm before implementing (see
`superpowers:brainstorming`) — open questions: what the Series page's job
actually is (navigation hub vs. season dashboard vs. both); what belongs on
a Season view beyond the cast table (ties directly into "key season-level
metrics" below); whether the paused `worktree-series-accordion` branch
should be finished/merged first or folded into this redesign; how episode
status (uploaded / analyzing / analyzed / scheduled) should be surfaced;
navigation model (accordion vs. dedicated pages vs. nested in My Scripts);
and finishing `SeriesAssignmentModal`/`SeriesPicker` styling as part of the
same visual system.

**References.**
- "Series / multi-episode analysis" (above) — full feature history, open
  sub-items (Phase 2, Board/Schedule integration, season metrics, unstyled
  modal), and the paused `worktree-series-accordion` branch
- `frontend/src/pages/SeriesListPage.jsx`, `SeasonPage.jsx`, `SeriesPages.css`
- `frontend/src/components/series/SeriesPicker.jsx`, `SeriesAssignmentModal.jsx`
- `frontend/src/components/scripts/ScriptTable.jsx` — the grouped My-Scripts view

---

## Department Workspaces — brainstorm

**Status:** Not started — needs brainstorming. Build-sequence step 7 in
`docs/superpowers/specs/2026-08-31-production-data-model-design.md` —
re-scope department workspaces to production-level, building on
`production_crew` + the existing `departments` list. Depends on the
production spine (step 1) and crew (step 2).

**Context.** Breakdown data is aggregated by department (props, wardrobe,
makeup, SFX, stunts, vehicles, animals, extras, cast, locations) and each
now has a reportable/CSV-exportable view — see "Department-specific
reporting" above. But there is no per-department *working surface*: a place
where (e.g.) the props master sees only props, across all scenes, with the
notes/status/CRUD they need, separate from the full breakdown view. Today
every department shares the one scene-centric breakdown UI.

**Why it matters.** On a real production each department head works their
own slice. A dedicated workspace per department is the natural home for the
element CRUD gap ("Breakdown UI/UX drill-down (CRUD) for elements" and
"Extras / background artists" above), per-element status tracking, and
department-scoped permissions.

**Scope when picked up.** Brainstorm before implementing (see
`superpowers:brainstorming`) — open questions: which departments get a
workspace first (props/wardrobe likely highest value); what a workspace
contains beyond a filtered element list (status, notes, quantities,
sourcing, attachments/photos); how it relates to the department *reports*
that already exist (is the report just an export of the workspace?);
whether workspaces need their own permission scope tied to Team License
seats (a props coordinator who can only see/edit props); and how this
overlaps with the general element-CRUD backlog item — likely the same
mechanism, workspaces as the container.

**References.**
- "Department-specific reporting — RESOLVED, shipped" (above) — the six
  department renderers + `aggregate_scene_data` per-category aggregation
- "Breakdown UI/UX drill-down (CRUD) for elements" (above) — the CRUD
  mechanism this would build on
- "Extras / background artists — needs CRUD editing" (above)
- `backend/services/report_service.py` — `aggregate_scene_data`
- `frontend/src/components/breakdown/` — existing breakdown UI

---

## "Auto" AI scheduling (first pass) — brainstorm

**Status:** Not started — needs brainstorming. Consumes the production
data model (`docs/superpowers/specs/2026-08-31-production-data-model-design.md`)
— shoot dates on `productions`, `units`, cast availability, and later the
production-level cross-script schedule. Where target shoot-days/hours-per-day
get entered is answered by that spec (production/unit level).

**Context.** Scheduling today is entirely manual: the user builds a
stripboard / shooting schedule by hand in `ScheduleKanban.jsx` /
`ShootingSchedulePage.jsx`, assigning scenes to shoot days themselves. All
the inputs a scheduler uses are already computed — scene INT/EXT and D/N,
location/setting, cast per scene, page-eighths (`utils/scene_calculations.py`),
and Day Out of Days (`report_service.py`). Nothing yet proposes a draft
day-by-day schedule from those inputs.

**Why it matters.** An AI-generated first-pass schedule (group by location,
cluster INT/EXT, respect D/N, balance page count per day, minimise company
moves and cast hold days) that the user then hand-adjusts would be a major
step from "breakdown tool" toward "scheduling tool" — and pairs directly
with cast availability data (below) once that exists.

**Scope when picked up.** Brainstorm before implementing (see
`superpowers:brainstorming`) — open questions: rules/heuristics engine vs.
LLM vs. hybrid for the first pass; what constraints v1 respects (location
grouping, D/N, page-count-per-day target, cast availability if present) and
which are deferred; how the draft is presented (fills an empty stripboard
the user then edits vs. a side-by-side suggestion); whether it re-runs
incrementally as the user locks days; how it scopes (single script now;
whole-series scheduling is its own open item above); and where the target
shoot-days/hours-per-day and other production parameters get entered.

**References.**
- `frontend/src/components/schedule/` — `ScheduleKanban.jsx`,
  `ShootingSchedulePage.jsx` (manual stripboard today)
- `backend/routes/schedule_routes.py`, `backend/db/migrations/030_shooting_schedules.sql`
- `backend/utils/scene_calculations.py` — page-eighths / scene math
- `backend/services/report_service.py` — Day Out of Days, `aggregate_scene_data`
- Related open items: "Cast & Casting v1" (above — cast availability now
  exists and can be consumed as a scheduling constraint) and the
  "Add CREW and production detail…" item below; "Board/Schedule a series
  with numerous episodes" (above)

---

## Add CREW and production detail for scheduling + call sheets / sides — brainstorm

**Status:** Not started — needs brainstorming. Data model now set by
`docs/superpowers/specs/2026-08-31-production-data-model-design.md`:
build-sequence step 2 (`contacts` directory + `production_crew`
assignments + CSV import), step 3 (`locations` directory), step 4 (call
sheets — `shooting_day_details`, fields designed in that brainstorm,
generation via the WeasyPrint pipeline). Depends on the production spine
(step 1). The **cast** slice (actor, contact, agent, headshot,
availability + schedule conflict detection) shipped 2026-08-28 — see
"Cast & Casting v1" above — and stays a separate system per the spec.

**Context.** The app now carries cast production data (via Cast & Casting
v1) but still lacks the rest of what a call sheet or scene sides need:
the crew list (name, role/department, contact, call time) and shoot-day
production detail (unit/base camp, location addresses and parking,
weather/sunrise-sunset, hospital, general crew call, meal times, key
personnel).

**Why it matters.** Call sheets and sides are the daily deliverable of a
1st AD — generating them from data already in the app (schedule, scene
breakdown, cast/scene mapping) plus this production layer would be a
headline feature. Cast availability is also the missing constraint for
"Auto" AI scheduling (above) and the only way to catch a booking conflict
inside the app.

**Scope when picked up.** Brainstorm before implementing (see
`superpowers:brainstorming`) — open questions: data model (`crew_members`;
per-shoot-day production-detail fields on `shooting_schedules`/shoot
days); whether crew attaches to a `production`/`season` or per-script;
call-sheet and sides generation (reuse the WeasyPrint report pipeline in
`report_service.py`? industry call-sheet layout — pull cast/scene data
from the schedule + the new `casting` table); the still-open Task 13
(Day Out of Days conflict overlay) from Cast & Casting v1; and Team
License seat/permission rules for who can enter/edit sensitive contact
details.

**References.**
- "Cast & Casting v1" (above) — the shipped cast slice; the `casting` /
  `casting_unavailability` tables and `casting_service` are the pattern
  crew data should follow
- "Auto AI scheduling (first pass)" (above) — cast availability (now
  present) is a key constraint it can use
- `backend/db/migrations/030_shooting_schedules.sql` — shoot-day schema
- `backend/services/report_service.py` — WeasyPrint pipeline (call sheet /
  sides generation), Day Out of Days
- `backend/routes/supabase_routes.py` — `merge_characters` (character
  identity system casting would key off)
- `frontend/src/components/schedule/` — stripboard / schedule UI

---

## Production data model — what a production needs, and how it's uploaded/managed — DIRECTION DECIDED

**Status:** Umbrella brainstorm complete 2026-08-31 →
`docs/superpowers/specs/2026-08-31-production-data-model-design.md`
(direction + data-model only; no implementation plan). Decision:
introduce a top-level `production` entity as an independent axis from
`series → seasons`; account-level `contacts` + `locations` reusable
directories; per-production `production_crew` assignments; additive
`production_members` permission layer with a `can_view_sensitive` gate;
`units` defined now (unblocks DPR); `shooting_schedules.production_id`
in the target model with a per-script rollup as the first slice; cast
(`casting`) and `script_members` left untouched. Ingestion: manual
forms baseline, CSV fast-follow for crew/contacts, AI-parse deferred.
Placement: `/productions` list + per-production tabbed workspace.

**Next:** each build-sequence step in the spec is its own brainstorm →
spec → plan cycle. Step 1 is "the spine" — `productions` entity +
`/productions` + workspace shell + script↔production association +
`production_members`. Steps 2–7: crew, locations, call sheets,
production-level schedule, DPR, department workspaces.

**Original context (kept for history):** Umbrella item; the
scheduling/call-sheet, crew, and department-workspace entries above are
slices of this. The **cast** slice shipped 2026-08-28 as an independent
feature ("Cast & Casting v1" above) — the spec keeps it separate rather
than folding it into the new `contacts` directory.

**Context.** Everything the app holds today is derived from the script (AI
extraction) or generated from it (breakdown, schedule, reports) — plus,
now, cast production data (`casting` / `casting_unavailability`). A real
production also runs on a large body of *other* production data that has
no home in the app: company/project setup (production company, title,
format, shoot dates, unit(s), budget tier), crew by department with
contacts and rates, locations as real places (addresses, contacts,
permits, parking, load-in, restrictions, photos), logistics
(equipment/vehicle/kit lists, catering, accommodation, travel), and
per-shoot-day operational detail (call times, weather, sunrise/sunset,
hospital, map links). None of that is modelled, and there's no ingestion
path.

**Why it matters.** This is the connective tissue between the breakdown
tool and an actual production-management product — call sheets, sides,
realistic scheduling, DOOD conflict-checking, and department workspaces all
depend on some subset of it. Deciding the data model and the
upload/management UX once, up front, avoids each downstream feature
inventing its own half-schema.

**Scope when picked up.** Brainstorm before implementing (see
`superpowers:brainstorming`) — open questions:
- **Inventory.** Enumerate the full set of production data categories and,
  per category, which fields are v1 vs. later. Reference real call-sheet /
  production-book templates and (ideally) a working line producer / 1st AD.
- **Data model.** New tables (`productions`/`project_settings`,
  `cast_members`, `crew_members`, `contacts`, real-`locations`,
  per-shoot-day detail) and how they attach — to a `script`, a `season`,
  or a new top-level `production` entity that scripts belong to. How this
  reconciles with the existing `series`→`seasons`→`scripts` hierarchy.
- **Identity links.** Cast → `characters` identity (surviving
  `merge_characters` alias merges); real-location → `scenes.setting` /
  the location-manager entities; crew → departments (ties to Department
  Workspaces above).
- **Upload / management UX.** Manual entry forms vs. bulk import (CSV/XLSX
  crew & cast lists are how this data actually circulates on set) vs.
  parsing an uploaded call sheet / production book PDF with AI. Which of
  those is v1. Where it lives in the app (a "Production" settings area, per
  script vs. per production).
- **Storage & permissions.** Headshots/location photos/documents —
  confirm the app's existing object-storage pattern and reuse it. Team
  License seat/role rules for who can see/edit contact details, rates, and
  other sensitive fields.
- **Sequencing.** Which downstream feature (call sheets, auto-scheduling,
  DOOD conflicts, department workspaces) drives the first concrete slice,
  so the model is built against a real consumer rather than speculatively.

**References.**
- "Cast & Casting v1" (above) — the shipped cast slice; its `casting` /
  `casting_unavailability` tables + `casting_service` are the pattern
  the rest of this data should follow
- "Add CREW and production detail for scheduling + call sheets / sides —
  brainstorm" (above) — the scheduling-driven slice of this
- "Department Workspaces — brainstorm" (above) — crew-by-department consumer
- "Auto AI scheduling (first pass) — brainstorm" (above) — needs shoot
  dates, cast availability, day parameters
- "Series / multi-episode analysis" (above) — the `series`→`seasons`→
  `scripts` hierarchy a `production` entity has to fit alongside
- `backend/db/migrations/030_shooting_schedules.sql`,
  `045_series_seasons.sql` — existing schema to extend
- `backend/routes/supabase_routes.py` — `merge_characters`,
  `merge_locations` (identity systems to key off)
- `backend/services/report_service.py` — WeasyPrint pipeline (call sheets /
  sides / production reports)

---

## Roadmap specs — status (added 2026-08-28)

Large features with written specs that were never tracked as backlog
entries. Listed here so the priority snapshot at the top accounts for
them. None are started.

### Daily Production Reporting (DPR)
**Status:** Spec complete, not started. `docs/SPEC_Daily_Production_Reporting.md`
(Rev 4 — 120+ FRs, 11 entities, 25 edge cases), full task breakdown in
`docs/TASKS_Daily_Production_Reporting.md` + `docs/dpr-plan/`. Feature
branch `feature/daily-production-reporting` was never created (T000a
unchecked). New deps required: `qrcode[pil]` (backend), `recharts`
(frontend), Supabase Storage bucket `dpr-attachments`.
**Why not now:** very large; depends on schedule/call-sheet maturity to
have a "planned baseline" to report actuals against. Sequence it *after*
call sheets exist. Roadmap item #1 in `SLATEONE_FEATURES.md`. Build-sequence
step 6 in `docs/superpowers/specs/2026-08-31-production-data-model-design.md`
— its "per production" config and Unit entity are accommodated by that
spec (`productions`, `units` defined up front); DPR internals stay as
specced here.

### Narrative Intelligence Dashboard
**Status:** Spec complete 2026-02-24
(`docs/SPEC_Narrative_Intelligence.md`, "Ready for Implementation"),
zero implementation — no route, service, or component exists. Full-page
AI story analysis at `/scripts/:scriptId/narrative` (theme, tone, plot
structure detection, character arcs, pacing, emotional flow).
**Why not now:** orthogonal to the production-management thrust —
director/writer-facing, not AD/producer-facing. Reassess whether it still
fits the product direction before committing; the spec predates the
two-tier pricing model and the whole production-data push.

### Production Analytics Dashboard / On-Set Offline Mode / Wrap Reports
**Status:** Roadmap bullets only (`SLATEONE_FEATURES.md` §2, §4, §5), no
spec. All three are downstream of DPR — analytics charts DPR data,
offline mode syncs DPR/department logs, wrap reports compile DPRs. Don't
scope until DPR is real.

### Docs debt
`docs/SLATEONE_FEATURES.md` is missing a "Cast & Casting" section (Cast &
Casting v1 shipped 2026-08-28) — add it the way Series was added after it
shipped. `docs/landing-faq.md` still describes the deprecated flat
"$49/month" model.
