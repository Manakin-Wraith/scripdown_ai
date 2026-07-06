# Phase 3 · Stream C — Navigation & Layout Consistency — Design

**Date:** 2026-07-06
**Status:** Approved (design)
**Parent:** `docs/audits/2026-07-06-ui-consistency-audit.md` (Phase 3, Lens 4). Phase 3 streams: A (color tokens, merged), B (primitive adoption), C (this — navigation/layout), D (dead-CSS deletion).
**Goal:** Give every script page one consistent navigation shell and one page-header/container standard, and bring `/profile` inside the app shell — resolving audit findings L1, L2, and the header/container half of L3, with no change to page content or business logic.

## Scope

**In:**
- A single canonical `SectionNav` for in-script lateral navigation, rendered centrally by `MainLayout`.
- Retiring `ViewSwitcher`; slimming `ScriptHeader` (drop its section-nav buttons only).
- Fixing the `Breadcrumb` route table (add `/board` + `/schedule`, remove dead routes).
- Moving the `/profile` route inside `MainLayout`.
- A shared `PageHeader` component + one `.page-container` width standard (1400px), adopted on Library, Upload, Profile, Stripboard, Reports.

**Out (explicitly deferred):**
- Relocating the Info popover / Team drawer out of `ScriptHeader` (they stay on the scene hub).
- Board/Schedule canvas internals; responsive work (L6); the z-index ladder (L5); dead-component/route deletion (L4 / Stream D); deep-domain headers (drawers, cards, admin, campaigns, auth).
- Any JSX business-logic change, data flow, or API change. This stream is chrome only.

## Current state (the problem)

Three disagreeing in-script nav mechanisms (audit L2):
- `ScriptHeader` (`components/metadata/ScriptHeader.jsx`, mounted only by `SceneViewer` on the scene hub) has buttons to all four sections (Stripboard/Board/Reports/Schedule).
- `ViewSwitcher` (`components/shared/ViewSwitcher.jsx`, mounted by `BoardToolbar` and `ShootingSchedulePage`) knows only Board + Schedule + a back-to-script button.
- `Breadcrumb` (`components/layout/Breadcrumb.jsx`, rendered globally by `MainLayout`) has a `ROUTE_CONFIG` that omits `/board` and `/schedule` and lists routes that don't exist (`/edit`, `/manage`, `/characters`).

Net effect: from Stripboard or Reports there is no lateral navigation to sibling sections. `/profile` is mounted outside `MainLayout` (`App.jsx`), so it has no TopBar/breadcrumb (L1). Nine bespoke `*-header` classes and five container max-widths (800/1000/1200/1400/none) coexist (L3).

## Routes (authoritative list)

Script-scoped section routes and their SectionNav identity:

| Section | Route pattern | Active-match |
|---|---|---|
| Scenes (hub) | `/scenes/:scriptId` | pathname === `/scenes/:id` |
| Stripboard | `/scripts/:scriptId/stripboard` | endsWith `/stripboard` |
| Board | `/scripts/:scriptId/board` | endsWith `/board` |
| Reports | `/scripts/:scriptId/reports` | endsWith `/reports` |
| Schedule | `/scripts/:scriptId/schedule` | endsWith `/schedule` |

A route is a "script route" (SectionNav renders) iff `scriptId` can be derived from it, i.e. it matches `/scenes/:id` or `/scripts/:id/:section`. Non-script routes (`/scripts`, `/upload`, `/profile`) render no SectionNav.

## Components

### `SectionNav` (new — `components/layout/SectionNav.jsx` + `.css`)

- **Responsibility:** the one lateral-navigation control between a script's five sections. Presentational tab bar; owns no data.
- **How it's used:** rendered once by `MainLayout` for any script route. Derives `scriptId` and the active section from `location.pathname` (via `useLocation`), mirroring the existing parse pattern in `ViewSwitcher`/`Breadcrumb`. No props required (it self-derives), but accepts an optional `scriptId` override for testability.
- **Depends on:** `react-router-dom` (`useLocation`, `Link`/`useNavigate`), `lucide-react` icons. No context beyond the router.
- **Markup:** a `<nav>` with five tab `<Link>`s (or buttons calling `navigate`), each with icon + label; the active tab gets an `.active` class. Uses design tokens only (amber `--primary-*` for active, slate for rest) — no raw color literals (respects Stream A).
- **Icons:** Scenes = `List`, Stripboard = `ClipboardList`, Board = `LayoutGrid`, Reports = `FileText`, Schedule = `CalendarDays` (reuse the lucide icons already imported in ScriptHeader/ViewSwitcher for visual continuity).

### `MainLayout` (modify — `components/layout/MainLayout.jsx`)

- Adds a helper `deriveScriptId(pathname)` returning the id or `null`.
- Renders `{scriptId && <SectionNav />}` between `<Breadcrumb />` and `<main>`. Order: TopBar → Breadcrumb → SectionNav → main. SectionNav sits in the chrome, so it works for both contained pages and `main-content--full-bleed` (board/schedule).
- No change to the existing `FULL_BLEED_PATTERNS` logic.

### `Breadcrumb` (modify — `components/layout/Breadcrumb.jsx`)

- `ROUTE_CONFIG`: **remove** `/scripts/:scriptId/edit`, `/scripts/:scriptId/manage`, `/scripts/:scriptId/characters/:characterName` (dead routes). **Add** `/scripts/:scriptId/board` → `{ label: 'Board', parent: '/scripts' }` and `/scripts/:scriptId/schedule` → `{ label: 'Schedule', parent: '/scripts' }`. **Add** `/profile` → `{ label: 'Profile', parent: null }`.
- No structural/rendering change; the trail-building logic already handles any matched route.

### `ScriptHeader` (modify — `components/metadata/ScriptHeader.jsx` + `.css`)

- **Remove** the four section-nav buttons in `.header-right` (Stripboard, Board, Reports, Schedule) and any now-unused icon imports (`List`, `ClipboardList`, `LayoutGrid`, `CalendarDays`) — keep icons still used by Info/Team.
- **Keep** everything else: script name, writer, scene-count badge, Info popover, Team drawer trigger. This is the scene hub's script-identity header; SectionNav does not replace it.
- Remove the corresponding now-dead CSS for the removed buttons if it is button-specific and unshared (verify no other file consumes the class before deleting; when in doubt, leave the rule).

### `ViewSwitcher` (delete — `components/shared/ViewSwitcher.jsx` + `.css`)

- Delete the component and its CSS.
- Remove its import + usage in `components/board/BoardToolbar.jsx` and `components/schedule/ShootingSchedulePage.jsx`. The global SectionNav now provides that navigation. Verify no other file imports it before deleting.

### `PageHeader` (new — `components/layout/PageHeader.jsx` + `.css`)

- **Responsibility:** one consistent page-title header block.
- **Props:** `{ title: string, subtitle?: string, icon?: ReactNode, actions?: ReactNode }`. `actions` renders right-aligned (buttons/links the page supplies). Presentational; no data, no router.
- **Markup:** `<header class="page-header">` with an optional icon, a title (`<h1>`), optional subtitle, and an `actions` slot. Tokens only; left-aligned (not the centered-hero style Upload currently uses).

### `.page-container` (new utility — a global class in `index.css`)

- One contained-width standard, defined as a global utility class in `index.css` (alongside the token below): `max-width: 1400px; margin: 0 auto; width: 100%;` plus the standard edge padding. Contained pages wrap their content in `.page-container`; full-bleed pages (board/schedule) do not use it.
- Introduce `--container-max: 1400px` in `index.css` and reference it, so the width has a single source of truth. (The unused `--main-content--contained` 1600px helper in `Layout.css` may be left or removed; removing it is a harmless bonus, not required.)

## Adoption map (deliverable 3)

| Page | File | Change |
|---|---|---|
| Library | `components/scripts/ScriptLibrary.jsx` | replace `library-header` with `PageHeader`; wrap in `.page-container` |
| Upload | `components/script/ScriptUpload.jsx` | replace centered `upload-header` with left-aligned `PageHeader`; `.page-container` |
| Profile | `pages/ProfilePage.jsx` | drop floating Back button; `PageHeader` + `.page-container` |
| Stripboard | `components/reports/Stripboard.jsx` | replace `stripboard-header` with `PageHeader`; `.page-container` |
| Reports | `components/reports/ReportBuilder.jsx` | replace `report-builder-header` with `PageHeader`; `.page-container` |

Scene hub keeps `ScriptHeader`. Board/Schedule keep full-bleed chrome. All other bespoke headers are out of scope.

## `/profile` into the shell (deliverable 2)

- `App.jsx`: move `<Route path="profile" …>` from its standalone position into the children of `<Route path="/" element={<ProtectedRoute><MainLayout/></ProtectedRoute>}>`. It remains protected (inherits the parent `ProtectedRoute`). Result path is unchanged (`/profile`).
- `ProfilePage.jsx`: remove the floating "Back" button and its handler; the breadcrumb ("My Scripts › Profile") now provides upward navigation. Adopt `PageHeader` + `.page-container`.

## Error handling & edge cases

- **SectionNav with no `currentScript` loaded yet:** the nav derives everything from the URL, not from `ScriptContext`, so it renders correctly even before script data loads. Tab labels are static.
- **Unknown script sub-route:** if a script route has no matching section (shouldn't happen given the route table), no tab is marked active — the bar still renders with all tabs clickable.
- **Deep-linking to a section:** SectionNav highlights the active tab purely from `pathname`, so a hard refresh on `/scripts/:id/board` shows Board active. No effect from navigation history.
- **`/profile` breadcrumb:** parent `null` → breadcrumb shows just "My Scripts › Profile" via the existing top-level logic.

## Verification

- Per task: `npm run build` green.
- Nav correctness is verified by reviewing the pathname-derivation logic (scriptId extraction + active-section match) against the authoritative route table above, plus the build. **Live-drive limitation:** the browser tooling can't load localhost and the app is login-gated, so there is no automated click-through; this is stated, not hidden — same constraint documented for Stream A.
- No test runner exists in the repo; this stream adds none.
- Manual smoke checklist (for whoever runs it locally, documented in the plan): from each of the five sections the other four are reachable in one click; breadcrumb shows the right trail on board/schedule; `/profile` shows TopBar + breadcrumb and no floating Back button; the five adopted pages share one header look and 1400px width.

## Success criteria

- One `SectionNav` is the only in-script lateral nav; `ViewSwitcher` is deleted and `ScriptHeader` no longer carries section buttons. From any of the five sections, the other four are one click away.
- `Breadcrumb` renders a correct trail on all five sections (including board/schedule) and on `/profile`; no dead routes remain in `ROUTE_CONFIG`.
- `/profile` renders inside `MainLayout` (TopBar + breadcrumb), with no floating Back button.
- Library, Upload, Profile, Stripboard, and Reports use `PageHeader` and the single 1400px `.page-container`; Upload is no longer a centered-hero outlier.
- Build green; no color-literal regressions (SectionNav/PageHeader use tokens only); each deliverable lands as its own reviewed commit.
