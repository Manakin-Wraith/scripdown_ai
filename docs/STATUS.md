# ScripDown AI status

Living progress doc. Update it at the end of each work session: Current state, Next steps, the Backlog board and a dated Changelog line. Full detail for every backlog entry lives in `docs/BACKLOG.md` (the long-form file this was split from on 2026-11-18).

## Current state (2026-11-19)

- **Page-load fixes merged to `main` (2026-11-19).** Route-level code splitting, scoped `get_scenes` schedule query, gzip on API responses, gthread gunicorn, polling pauses on hidden tabs. Lighthouse (mobile, login page, median of 3, preview vs production before the merge): score 84 to 99, LCP 4.5 s to 2.0 s, FCP 1.2 s to 0.8 s, script transfer 629 KB to 145 KB. Logged-in pages and the API-side gains are not yet measured.
- **Checkout is live.** PayFast live credentials are set and outbound checkout is verified (2026-08-27). The inbound payment notification (ITN) has not been exercised on a real transaction yet. Renewals and cancellations are handled by hand while volume is low.
- **Production-first navigation, Phase 1, is on `main` and live on Vercel (2026-11-10).** Production tabs are URLs, the top bar is Productions, Scripts, Contacts and Locations, and the production Overview is a dashboard. Verified by tests and build only; never clicked through in a browser.
- **Cast tab now lives inside the production page (2026-11-10).** Cast is still stored per script, so the same actor on two scripts is two unrelated rows. Also verified by tests and build only.
- **Character rename shipped (2026-11-11).** Known gaps: no Rename in the Characters view, writes are not atomic, and merge may not repoint existing aliases.
- **Production data model is in place:** productions, crew and contacts, members with permissions, locations, call sheets with per-production templates, and production-level script access (all shipped Aug to Sept 2026).
- **Known problem:** pages are loading slower than usual (logged 2026-11-10). Fixes shipped; logged-in pages and API response times still need measuring.
- **Deploy:** frontend on Vercel, backend on Railway, both from `main`. The latest check on `main` (merge of `docs/character-rename`, 2026-11-11) passed on both.

## Next steps

1. **Finish slow page loads.** Measure `/api/scripts/:id/scenes` before and after (needs an auth token) and watch the gthread workers on Railway. Remaining from the audit: Supabase advisors and index review, `select('*')` trimming, `/api` caching headers, polling backoff.
2. **Click through navigation Phase 1 and the production Cast tab in a real browser.** Neither was ever run by hand.
3. **Navigation Phase 2 (~3 to 5 days, frontend):** production shell with a Prep / Plan / Output / Admin sidebar, a production switcher, nested routes under `/productions/:id/...`, and one place for team management.
4. **Character rename follow-ups:** repoint aliases on merge (unverified), make the writes atomic with a Postgres RPC, add Rename to the Characters view.

## Backlog board

Read by the Bridge board. Four columns, one line per item. The long-form entry for each is in `docs/BACKLOG.md`.

### Now

- **Slow page loads** (2026-11-18 to 2026-11-20) — main fixes shipped 2026-11-19; remaining: advisors and indexes, `select('*')`, caching headers, polling backoff
- **Browser click-through of nav Phase 1 and the production Cast tab** (by 2026-11-20) — never verified by hand
- **Navigation Phase 2** (2026-11-23 to 2026-12-01) — production shell, sidebar, switcher, nested routes
- **Character rename follow-ups** — merge alias repoint, atomic writes, rename in Characters view
- **First real PayFast payment check** — confirm the inbound ITN row goes `complete` and the grant lands

### Next

- **Call sheets, next slice** — multi-script shoot days, extras from `casting_groups`, live preview in the template builder, CSV template import (brainstorm paused 2026-09-23)
- **Auto AI scheduling, first pass** — cast availability is now a real constraint; brainstorm
- **Cast and Casting closeout** — DOOD conflict overlay (Task 13), icon consistency
- **Role-aware edit controls on script pages** — viewers still see write controls that return 403
- **CI gates** — make `backend-tests` required, add a frontend `npm run build` gate
- **Breakdown element CRUD** — drill-down editing, extras first
- **Separate Location from Sets** — production element versus creative element
- **Merged cast list across scripts** — shared actor identity within a production

### Later

- **Series page redesign and Series Phase 2** — finish or drop `worktree-series-accordion`
- **Report version control** — and a CSV export that matches industry format
- **Script re-upload change highlight** — partially built
- **Department workspaces** — and user workspace with department-specific access
- **Production budget** — not scoped, no dependencies
- **Crew detail for scheduling, call sheets and sides** — sides not built
- **Productions page as the owner's workspace** — brainstorm
- **UI passes** — production pages, Crew tab, Members tab (incl. the owner-missing-seat message), Locations tab, app-wide alignment
- **Settings theme toggle does nothing** — remove it or build a light theme
- **FAQ page** — and fix `landing-faq.md`, which still describes the old $49/month model
- **FDX Tagger ingestion** — blocked on a sample file; revision-import FDX path too
- **Daily Production Reporting** — spec complete, not started; waits on schedule and call sheet maturity
- **Narrative Intelligence Dashboard** — spec from 2026-02-24; reassess whether it fits the direction
- **Production analytics, offline mode, wrap reports** — downstream of DPR, no spec
- **Navigation Phase 3** — production-wide schedule and reports (needs backend)

### Deferred

- **Renewal automation** — deferred until scale (2026-08-27)
- **Failed-renewal downgrade** — blocked on renewal automation
- **Teams to Solo downgrade** — deferred until scale
- **Live PayFast ITN verification** — opportunistic, with the first real transaction

## Changelog

- **2026-11-19 (CORS extra origins):** `CORS_EXTRA_ORIGINS` env var (comma-separated exact origins) so a Vercel preview can call the API. Exact match only, not a pattern: a `*.vercel.app` regex could be matched by another Vercel account. Remove the Railway variable when not testing a preview.
- **2026-11-19 (page-load audit fixes):** lazy-loaded all routes except login and layout, vendor chunks for react and supabase, `get_scenes` schedule query scoped to the script (was reading every script's rows), Flask-Compress, gunicorn gthread x4 in Dockerfile and Procfile, polling skips hidden tabs and fetches in parallel, supabase preconnect, `profile_pic.png` 3 MB to 107 kB (kept, a live email links to it).
- **2026-11-11 (character rename):** Rename a character from the Cast drawer. Spec `docs/superpowers/specs/2026-11-11-character-rename-design.md`. Follow-ups are in the Now column.
- **2026-11-10 (cast tab in the production page):** New production Cast tab at `/productions/:id/cast` and `/productions/:id/cast/:scriptId`; the script-level Cast tab is hidden for scripts in a production. Merged to `main`.
- **2026-11-10 (navigation Phase 1):** Production-first navigation shipped and live on Vercel: breadcrumb, production tabs as URLs, new top bar, production dashboard, `scene_count` fields on `GET /api/productions/:id`. Gotcha: `scripts.analysis_status` is not maintained, so derive progress from scenes.
- **2026-09-23 (production script access):** Membership grants access to every script in a production through a per-member `script_access` level. Migration 056 applied. Series and season delete shipped the same day. Mapbox tokens set the same day as step 3.
- **2026-09-22 (call sheet customization):** Per-production templates, section order and visibility, custom columns, department calls, boilerplate blocks. Migration 055.
- **2026-09-21 (call sheets v1):** Functional call sheets with PDF render, wired into the shooting-schedule kanban. Migration 054. Sides not built.
- **2026-09-03 (locations and directory redesign):** Account-level locations directory with Mapbox geocoding (migration 053). Contacts and Locations rebuilt as centred split-pane pages.
- **2026-09-02 (production members):** Role and capability layer with invites (migration 052).
- **2026-08-31 (production spine and crew):** Production entity, crew and contacts directory (migrations 050, 051).
- **2026-08-29 (cast tab v2):** Multi-photo gallery, cast tiers, extras as groups, in-app conflict resolution.
- **2026-08-28 (cast and casting v1):** Cast contacts, headshots, availability, schedule conflict detection.
- **2026-08-27 (checkout live):** PayFast live credentials verified outbound. Pricing change dropped; current prices kept.
