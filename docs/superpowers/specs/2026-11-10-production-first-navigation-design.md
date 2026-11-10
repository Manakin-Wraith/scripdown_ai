# Production-First Navigation — UX Audit & Redesign Proposal

**Date:** 2026-11-10
**Status:** Proposal, not approved. Nothing built.
**Trigger:** Looped Pictures (multi-script production company, working with a team) reports clumsy navigation.
**Basis:** Code audit of `frontend/src` (routes, `TopBar`, `SectionNav`, `Breadcrumb`, production/series/script pages). The app was **not** run live, and Looped's specific complaints were not collected, so the pain points below are inferred from the code. Check them against what Looped actually says.

## 1. The core problem

The product has grown from a script tool into a production suite, but the navigation still treats the **script** as the root of everything. The data model already says otherwise: `production` is the top-level container, and scripts, crew, locations, call sheets and (soon) schedules hang off it (`2026-08-31-production-data-model-design.md`). The UI hasn't caught up, so a team working across several scripts keeps leaving the context they're working in.

## 2. Findings

**Structure**
1. **Wrong root.** `/` redirects to `/scripts` and the first nav item is "My Scripts". Productions is one of five peer links. A team member who joined via a production sees a library titled "My Scripts" that isn't theirs (the "shared via production" hint is a hover tooltip only, `ScriptTable.jsx:201`).
2. **Two competing grouping systems, both in the top bar.** Series (narrative grouping) and Productions (physical shoot grouping) each group scripts and each have their own list/detail pages. The data model makes them independent axes on purpose, but users see two parallel "folders" with no explanation.
3. **Mixed scopes in one bar.** `My Scripts · Series · Productions` are project-level. `Contacts · Locations` are company-level directories. `Admin` is platform-level. They are all rendered as equal peers.
4. **No "current production" context.** Opening a script from a production drops you into `/scenes/:id` with breadcrumb `My Scripts › Script`. You can't tell which production you're in, and "back" goes to the wrong place. Switching between two scripts in the same production means going back up to the production page and down again.

**Navigation mechanics**
5. **Breadcrumb has no config for productions, series, contacts or locations.** `Breadcrumb.jsx` returns nothing for those routes, and for script routes it always starts at `My Scripts`.
6. **Production tabs live in `useState`** (`ProductionDetailPage.jsx`). The `?tab=` param is only read on first load, so tabs have no real URLs: no deep links, and the browser back button leaves the production instead of the tab.
7. **Script sub-nav has 7 tabs with unclear boundaries.** Scenes, Revisions (route is `/manage`), Cast, Stripboard, Board, Schedule, Reports. Three planning views (Stripboard / Board / Schedule) sit next to each other. "Cast" uses the Contact icon, the same as the Contacts nav item.

**Production-as-a-suite gaps**
8. **Production page is a settings form with a script list underneath.** The Overview tab opens on Title/Status/Dates/Notes, with scripts as a plain link list at the bottom. There's no progress (scenes broken down, pages, shoot days) and no "what needs attention".
9. **Production has no breakdown, schedule, cast or reports.** Those exist only per script. A production holding a TV block or feature plus reshoot script can't see or schedule across scripts. (`shooting_schedules.production_id` is documented as the target model but isn't surfaced in the UI.)
10. **Team is managed in two places.** A per-script "Team" drawer in `ScriptHeader` and the production's Members tab. Which one grants access, and why, isn't obvious to the person doing the inviting.
11. **Upload isn't production-aware.** `/upload` knows `seriesId`/`seasonId` but not production. Attaching a script to a production is a separate "pick an existing script" step afterwards.

## 3. Proposal: production-first shell

### 3.1 Three navigation levels, each with its own chrome

| Level | What it is | Chrome |
|---|---|---|
| **Company** | Everything the account owns | Top bar: **Productions** (home) · **Scripts** · **Contacts** · **Locations**. Admin moves into the user menu. "My Scripts" becomes "Scripts". |
| **Production** | One shoot | Production switcher in the top bar (current production name, dropdown to switch or create). Left sidebar with grouped sections (below). |
| **Script** | One script/episode within a production | Script switcher at the top of the production sidebar's "Script" group, plus the existing per-script tabs, slimmed down. |

### 3.2 Production sidebar (grouped by workflow, not by feature age)

```
Overview            dashboard: progress, shoot dates, what needs attention
Scripts             list + series/season grouping, add/upload here
 ── Prep ──────
Breakdown           scenes, elements, revisions   (script-scoped, with script switcher)
Cast & Crew         cast, crew, contacts picked from the directory
Locations           production locations
 ── Plan ──────
Schedule            stripboard, board, calendar    (script-scoped now, production-wide later)
Call Sheets         template + generated sheets
 ── Output ────
Reports
 ── Admin ─────
Members & Access    the single place for team and permissions
Settings            title, status, dates, notes, delete
```

### 3.3 URL and state
- Nested routes under `/productions/:productionId/...` for every section, so tabs have real URLs, deep links work and back works.
- Script-scoped sections take `?script=:id` or a nested `/scripts/:scriptId` segment (builder's call). Old routes (`/scenes/:id`, `/scripts/:id/...`) redirect into the owning production, or stay as-is for unfiled scripts.
- A `ProductionContext` (like `ScriptContext`) supplies production name, role and access to the shell, breadcrumb and switcher.
- Breadcrumb becomes `Productions › {Production} › {Section} › {Script}` and is generated from the same route config.

### 3.4 Smaller fixes that go with it
- **Overview becomes a dashboard**: script cards with scene counts and analysis status, shoot dates, member count, and the settings form moves to Settings.
- **One place for team**: the per-script Team drawer becomes a shortcut that opens the production's Members & Access, or shows read-only access when the script is unfiled.
- **Series** is demoted from top-level nav to a grouping inside Scripts (and a filter). `/series` stays reachable from Scripts.
- **Upload** takes `productionId`, with "Upload script" available inside the production's Scripts section.
- Rename the `Revisions` / `/manage` mismatch; give Cast a distinct icon from Contacts.
- Replace `window.confirm` on production delete with the shared confirm dialog.

### 3.5 Solo tier
Tier 1 (Pay-Per-Breakdown, no team features) shouldn't see production chrome. Keep today's simple script-library shell for solo accounts and switch to the production-first shell when the account has a Team License or has any production. Scripts not in a production remain valid, shown under Company → Scripts.

## 4. Phasing

1. **Phase 1, no backend change (about 1 to 2 days):** top-bar regrouping and renames, breadcrumb support for all routes with production context, URL-based production tabs, Overview-as-dashboard, "shared via production" label shown visibly in the script table.
2. **Phase 2, frontend routing (about 3 to 5 days):** production shell with sidebar and switcher, nested routes with redirects, `ProductionContext`, merged team management, production-aware upload.
3. **Phase 3, needs backend (separate spec):** production-wide schedule and stripboard across scripts (`shooting_schedules.production_id`), production-level reports and cast.

Phases 1 and 2 are independent of Phase 3 and already fix most of what a multi-script team will feel day to day.

## 5. Decisions for the product owner (my recommendations in bold)
1. Demote Series from top-level nav into Scripts? **Yes.**
2. Show the production-first shell to solo-tier accounts? **No, keep the simple shell until they have a production.**
3. Long-term, can a script exist outside any production? **Yes, as "unfiled" under Scripts, with a nudge to attach it.**
4. Ship Phase 1 to Looped now as a quick win, then Phase 2? **Yes.**

## 6. Non-goals
- Redesigning individual screens (stripboard, scene detail, report studio).
- Changing permissions or the data model.
- Visual rebrand. The existing design primitives and tokens stay.
