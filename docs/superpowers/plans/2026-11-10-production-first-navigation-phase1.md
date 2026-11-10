# Production-First Navigation — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give multi-script teams a navigation that always shows which production they are in, with real URLs for production tabs, a dashboard-style production Overview, and a top bar grouped by scope. Frontend only; no backend change.

**Architecture:** Put breadcrumb logic in one pure module (`breadcrumbTrail.js`, unit-tested with Node's built-in runner) and have `Breadcrumb.jsx` render it. Production tabs become a route param on the existing detail page. The top bar is regrouped and renamed, and the Overview tab is reshaped into script cards plus a summary strip.

**Tech Stack:** React 18, react-router-dom v6, Vite, plain JS/JSX, lucide-react. Tests: `node --test` on pure `.js` modules (no new dependency).

**Spec:** `docs/superpowers/specs/2026-11-10-production-first-navigation-design.md` (Phase 1, section 4)

## Global Constraints

- Frontend gate is `cd frontend && npm run build` plus `node --test src/**/*.test.js` (`npm run lint` is broken repo-wide; do not use it as a gate).
- No new npm dependencies. No backend changes. No per-feature axios instances; use `src/services/apiService.js`.
- Use existing design tokens (`var(--space-*)`, `var(--primary-500)`, etc.); no hard-coded colours.
- Do not rename routes, with the one exception in Task 3 (production tab URLs). Legacy URLs must keep working.
- Copy: "My Scripts" becomes **"Scripts"** everywhere it is user-visible (nav, breadcrumb, page title, mobile back link).
- Phase 1 does not gate nav by tier. That belongs to Phase 2.

## Review Focus

1. Production-linked script whose title or production metadata is still loading: the breadcrumb must not flash `Scripts › Script` then jump; show a neutral placeholder crumb until resolved.
2. Script the viewer does not own that has no production: breadcrumb falls back to `Scripts › {Script}` and does not error.
3. Unknown production tab in the URL (`/productions/:id/bogus`) or a tab the viewer isn't permitted to see: redirects to Overview, no blank page.
4. Legacy `/productions/:id?tab=crew` links (existing bookmarks, invite emails) still land on the Crew tab.
5. Production deleted or 403 while on a script page: breadcrumb degrades to the no-production form rather than a broken link.

---

## File Structure

| File | Responsibility |
|---|---|
| `frontend/src/components/layout/breadcrumbTrail.js` (new) | Pure `buildTrail` function: pathname + context → crumb list. |
| `frontend/src/components/layout/breadcrumbTrail.test.js` (new) | `node --test` cases for every route family. |
| `frontend/src/hooks/useScriptProduction.js` (new) | Resolves `{id,title}` of the production a script belongs to, cached per script. |
| `frontend/src/components/layout/Breadcrumb.jsx` (modify) | Renders `buildTrail`; mobile back link = previous crumb. |
| `frontend/src/components/layout/TopBar.jsx` (modify) | Regroup/rename nav; Admin into user menu. |
| `frontend/src/App.jsx` (modify) | Production tab route param; index redirect target unchanged. |
| `frontend/src/pages/ProductionDetailPage.jsx` (modify) | Tab from URL; tab buttons become links. |
| `frontend/src/components/productions/ProductionOverviewTab.jsx` (modify) | Summary strip + script cards above the settings form. |
| `frontend/src/components/scripts/ScriptTable.jsx`, `ScriptLibrary.jsx`, `pages/SeriesListPage.jsx` (modify) | Visible "via production" label; rename; Series entry point from Scripts. |

---

### Task 1: Breadcrumb trail builder (pure, tested)

**Files:**
- Create: `frontend/src/components/layout/breadcrumbTrail.js`
- Test: `frontend/src/components/layout/breadcrumbTrail.test.js`

**Interfaces:**
- Produces: `buildTrail({ pathname, search = '', script = null, production = null }) -> Crumb[]` where `Crumb = { label: string, to: string | null }` (`to: null` means the current page). `script` is `{ id, title } | null`; `production` is `{ id, title } | null` and is the production owning the script on script routes, or the production being viewed on `/productions/:id...`. Returns `[]` for root pages (`/scripts`, `/productions`, `/contacts`, `/locations`, `/series`, `/`) and unknown routes.
- Also exports `PRODUCTION_TAB_LABELS = { overview: 'Overview', crew: 'Crew', locations: 'Locations', callsheet: 'Call Sheet', members: 'Members' }` and `SCRIPT_SECTION_LABELS = { stripboard: 'Stripboard', board: 'Board', schedule: 'Schedule', cast: 'Cast', reports: 'Reports', manage: 'Revisions' }`.

- [ ] **Step 1: Write the failing tests** in `breadcrumbTrail.test.js` using `node:test` and `node:assert/strict`. Cases (labels exact):
  - `/scripts`, `/productions`, `/contacts`, `/locations`, `/series` → `[]`.
  - `/productions/p1` with production `{id:'p1',title:'Looped Feature'}` → `[{Productions,/productions},{Looped Feature,null}]`.
  - `/productions/p1/crew` → `Productions › Looped Feature (to /productions/p1) › Crew (null)`.
  - `/productions/p1/overview` behaves like `/productions/p1` (no extra Overview crumb).
  - `/scenes/s1` with script `{id:'s1',title:'Pilot'}` and production p1 → `Productions › Looped Feature › Pilot (null)`; without production → `Scripts › Pilot (null)`.
  - `/scripts/s1/stripboard` with production → `Productions › Looped Feature › Pilot (to /scenes/s1) › Stripboard (null)`; `/scripts/s1/manage` last crumb is `Revisions`.
  - Script not yet loaded (`script: null`) on `/scenes/s1` → last crumb label `Script`, not `undefined`.
  - `/upload` → `Scripts › Upload Script`; `/profile` → `[Profile]`; `/billing` → `[Billing]` (single crumb, `to:null`).
  - `/series/x` → `Scripts › Series (to /series) › Series`; `/series/x/seasons/y` → `Scripts › Series › Series (to /series/x) › Season`.
  - `/contacts/abc` → `Contacts (to /contacts) › Contact`; `/locations/abc` → `Locations › Location`.

- [ ] **Step 2: Run** `cd frontend && node --test src/components/layout/breadcrumbTrail.test.js` — Expected: FAIL (module not found).

- [ ] **Step 3: Implement `buildTrail`** in `breadcrumbTrail.js` as a plain ES module (no JSX, no CSS imports, no React). Match on pathname with anchored regexes; production routes use the optional `:tab` segment. Unknown tab segment is treated as Overview (Task 3 does the redirect; the builder just must not throw).

- [ ] **Step 4: Run the test file again** — Expected: all PASS.

- [ ] **Step 5: Commit** `feat(nav): pure breadcrumb trail builder with tests`

---

### Task 2: Breadcrumb component + production resolution

**Files:**
- Create: `frontend/src/hooks/useScriptProduction.js`
- Modify: `frontend/src/components/layout/Breadcrumb.jsx` (replace `ROUTE_CONFIG`/`matchRoute` with `buildTrail`)
- Modify: `frontend/src/components/layout/MainLayout.jsx` only if needed to pass nothing new (the breadcrumb derives everything itself).

**Interfaces:**
- Consumes: `buildTrail` from Task 1; `getScriptMetadata(scriptId)` from `apiService` (returns `production_id`, `production_title`, `title`; see `backend/routes/supabase_routes.py` `get_script_metadata`); `getProduction(id)` for `/productions/:id...` routes.
- Produces: `useScriptProduction(scriptId: string | null) -> { production: {id,title} | null, scriptTitle: string | null, loading: boolean }`. Module-level `Map` cache keyed by scriptId so switching between a script's sections does not refetch; failures resolve to `{ production: null }` (never throw).

- [ ] **Step 1: Implement `useScriptProduction`** per the interface. Prefer `currentScript.title` from `ScriptContext` for the script crumb when present and fall back to `scriptTitle` from metadata.
- [ ] **Step 2: Rewrite `Breadcrumb.jsx`** to: derive `scriptId` from the pathname, call the hook, derive production for `/productions/:id` routes from `getProduction` (reuse the title only; cache by id), call `buildTrail`, render `<ol>` as today (same CSS classes), return `null` when the trail is empty. While `loading` on a script route, render the first crumb as `Scripts` and a non-link placeholder crumb (`…`) in the production slot; do not render a `Scripts › Script` flash (Review Focus 1).
- [ ] **Step 3: Mobile back link** = the second-to-last crumb's `to` and label (`Back to {label}`); keep the existing `breadcrumb-back mobile-only` markup.
- [ ] **Step 4: Verify** `cd frontend && npm run build` succeeds. Manually (`npm run dev`) open a production-linked script's Stripboard and confirm `Productions › {Production} › {Script} › Stripboard`; open an unlinked script and confirm `Scripts › {Script} › …`; open `/productions/:id`, `/contacts/:id`, `/series/:id` and confirm breadcrumbs now appear.
- [ ] **Step 5: Commit** `feat(nav): production-aware breadcrumbs on all routes`

---

### Task 3: Production tabs as URLs

**Files:**
- Modify: `frontend/src/App.jsx:89-90` (replace the `productions/:productionId` route with `productions/:productionId/:tab?`)
- Modify: `frontend/src/pages/ProductionDetailPage.jsx` (tab state, tab buttons)

**Interfaces:**
- Consumes: `TAB_IDS` (already in the page file).
- Produces: URL contract `/productions/:productionId` (= Overview) and `/productions/:productionId/{overview|crew|locations|callsheet|members}`. `ProductionDetailPage` derives `activeTab` from `useParams().tab`; no tab `useState`.

- [ ] **Step 1: Route change** in `App.jsx`.
- [ ] **Step 2: Derive the tab from the URL** in `ProductionDetailPage.jsx`: `useParams().tab`; if it is not in `TAB_IDS`, or not in the viewer's permitted `tabs` list (existing `isMember` / `canManageMembers` logic, applied after load), `<Navigate to={`/productions/${productionId}`} replace />`. Replace the existing "force back to overview" `useEffect` with this.
- [ ] **Step 3: Legacy `?tab=`:** on mount, if `searchParams.get('tab')` is a valid id, `navigate(`/productions/${productionId}/${tab}`, { replace: true })`. Remove the `useState` initializer that read it.
- [ ] **Step 4: Tab buttons → `NavLink`s** keeping the existing `production-tab` / `active` classes (Overview links to `/productions/:id`, others to `/productions/:id/{id}`).
- [ ] **Step 5: Check other deep links** — `grep -rn "productions/\${" frontend/src` and `grep -rn "?tab=" frontend/src`; update any that target a tab to the new path form (invite emails are backend-generated: note any `?tab=` they use, which works through Step 3).
- [ ] **Step 6: Verify** build passes; manually: click each tab (URL changes), browser Back returns to the previous tab, `/productions/:id/bogus` and `/productions/:id?tab=crew` behave per Review Focus 3 and 4, and a non-member viewer on `/productions/:id/members` lands on Overview.
- [ ] **Step 7: Commit** `feat(production): URL-addressable production tabs`

---

### Task 4: Top bar regroup and "Scripts" rename

**Files:**
- Modify: `frontend/src/components/layout/TopBar.jsx`
- Modify: `frontend/src/components/scripts/ScriptLibrary.jsx` (PageHeader title/subtitle)
- Modify: `frontend/src/pages/SeriesListPage.jsx` (back-link/copy if it says "My Scripts")
- Modify: `frontend/src/components/scripts/EmptyLibrary.jsx` only if it says "My Scripts"

**Interfaces:** none new. Order and labels are fixed here: **Productions · Scripts · Contacts · Locations**. Icons unchanged except none shared (Cast's icon fix is Task 6).

- [ ] **Step 1: Reorder and rename nav** in `TopBar.jsx`: Productions (`/productions`), Scripts (`/scripts`), Contacts, Locations. Remove the top-level Series link.
- [ ] **Step 2: Move Admin** (superusers only) into the user dropdown as a `dropdown-item` above Profile, navigating to `/admin`, using the existing `Shield` icon. Remove it from `topbar-nav`.
- [ ] **Step 3: Series entry point** — in `ScriptLibrary.jsx` add a secondary header action "View series" (`navigate('/series')`) next to "Upload New", shown only when any listed script has a `series_id`. (`/series` stays routable and keeps working.)
- [ ] **Step 4: Rename copy:** `grep -rn "My Scripts" frontend/src` and change every user-visible occurrence to "Scripts". `ScriptLibrary` title `Scripts`, subtitle `All screenplays you own or have been shared on`.
- [ ] **Step 5: Verify** build; manually confirm the nav order, that a superuser sees Admin only in the avatar menu, and that a non-superuser sees no Admin.
- [ ] **Step 6: Commit** `feat(nav): regroup top bar, Admin to user menu, My Scripts → Scripts`

---

### Task 5: Visible "via production" label on shared scripts

**Files:**
- Modify: `frontend/src/components/scripts/ScriptTable.jsx:198-208` (the `shared-badge`)
- Modify: `frontend/src/components/scripts/ScriptLibrary.css` or the table's existing stylesheet for any overflow tweak

**Interfaces:** consumes existing `script.is_owner`, `script.membership.via_production`, `script.production_title`.

- [ ] **Step 1:** When `is_owner === false` and `membership.via_production` with a `production_title`, render the badge text as `Shared · {production_title}` (truncate with ellipsis at ~20ch via CSS; keep full text in `title`). Other shared cases keep the text `Shared`.
- [ ] **Step 2:** For owned scripts that have a `production_title`, render a muted `{production_title}` chip in the same row (new class `script-production-chip`) so everyone sees the production without hovering. Scripts with no production show nothing.
- [ ] **Step 3: Verify** build; manually load the library as an owner of a production-linked script and as a production member who doesn't own it.
- [ ] **Step 4: Commit** `feat(scripts): show production on script rows`

---

### Task 6: Production Overview as a dashboard

**Files:**
- Modify: `frontend/src/components/productions/ProductionOverviewTab.jsx`
- Modify: `frontend/src/pages/ProductionPages.css` (new classes below)
- Modify: `frontend/src/components/layout/SectionNav.jsx` (Cast icon only; swap `Contact` for `Users`, no other change)

**Interfaces:** consumes the existing props of `ProductionOverviewTab` plus data already on the `scripts` rows from `getProduction` (`id, title, analysis_status, total_pages, episode_number`). Scene counts are **not** on these rows, so do not display them in Phase 1. Member count is not fetched in Phase 1 either.

- [ ] **Step 1: Summary strip** at the top: status badge (reuse `status-{status}` classes from the list page), shoot dates as `{start} → {end}` (or "Dates not set"), and script count.
- [ ] **Step 2: Script cards** (replace the plain `<ul>` list) — a responsive grid; each card shows title (link to `/scenes/:id`), `analysis_status` as a badge (map unknown values to the raw string), `{total_pages} pp` when present, `Ep {episode_number}` when present, and quick links **Breakdown** (`/scenes/:id`), **Stripboard** (`/scripts/:id/stripboard`), **Schedule** (`/scripts/:id/schedule`). The existing remove button and the Add script button/picker keep their permission gates (`canDelete`).
- [ ] **Step 3: Needs attention line** under the strip: list scripts whose `analysis_status` is not complete as `N script(s) still analysing/failed` (use the same status values the library table already treats as "not complete"; read them from `ScriptTable.jsx` rather than inventing new ones).
- [ ] **Step 4: Move the settings form** below the dashboard, inside a collapsed `<details>` titled "Production settings" (open by default for owners only when title is empty). Behaviour of save/delete unchanged.
- [ ] **Step 5: Cast icon** in `SectionNav.jsx` per the file list.
- [ ] **Step 6: Verify** build; manually check an empty production, a one-script and a multi-script production, as owner and as read-only member (no add/remove/settings write controls for the latter, same as today).
- [ ] **Step 7: Commit** `feat(production): overview dashboard with script cards`

---

### Task 7: Final verification and docs

**Files:**
- Modify: `docs/superpowers/specs/2026-11-10-production-first-navigation-design.md` (status line: Phase 1 implemented)

- [ ] **Step 1:** Run `cd frontend && node --test src/components/layout/breadcrumbTrail.test.js && npm run build` — Expected: tests pass, build succeeds.
- [ ] **Step 2:** Walk the Looped scenario end-to-end in `npm run dev`: log in, land on Scripts, open a production, switch tabs and use Back, open a script from the production, use the breadcrumb to return to the production, open Contacts and use its breadcrumb.
- [ ] **Step 3:** Update the spec status line; commit `docs: mark navigation Phase 1 implemented`.

---

## Self-Review

- **Spec coverage (Phase 1 list):** top-bar regrouping and renames → Task 4; breadcrumb for all routes with production context → Tasks 1–2; URL-based production tabs → Task 3; Overview-as-dashboard → Task 6; visible "shared via production" → Task 5. Admin to the user menu and Series demotion → Task 4. Gaps, deliberately deferred to Phase 2: production switcher, sidebar, `ProductionContext`, merged team management, production-aware upload, solo-tier shell gating. Not in Phase 1 because they need the shell: the Team drawer on scripts stays as is.
- **My calls to review (not decided by you):** no new test dependency (Node's built-in runner on a pure module, so only the breadcrumb logic is unit-tested; the rest is build + manual checks); generic `Series` / `Season` / `Contact` / `Location` labels on detail-page crumbs rather than fetching titles; dashboard shows analysis status and pages only because scene counts aren't on the production payload; Series link appears in Scripts header only when the user has series; settings form collapsed under the dashboard.
- **Type consistency:** `buildTrail` signature and `useScriptProduction` return shape are used identically in Tasks 1–2; tab ids match `TAB_IDS`.
