# Phase 3 Stream C — Navigation & Layout Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every script page one consistent navigation shell (a single `SectionNav`) and one page-header/container standard, and bring `/profile` inside the app shell — resolving audit findings L1, L2, and the header/container half of L3.

**Architecture:** `MainLayout` centrally renders the chrome for every script page: TopBar → Breadcrumb → SectionNav → main. A new `SectionNav` derives `scriptId` and the active section from the URL. `ViewSwitcher` is retired; `ScriptHeader` loses its section buttons (keeps identity/Info/Team on the scene hub). A shared `PageHeader` + a single `.page-container` (1400px) replace five bespoke headers.

**Tech Stack:** React 18 + Vite (plain JSX, no TypeScript), react-router-dom v6, lucide-react, plain CSS with design tokens in `index.css`.

## Global Constraints

- **Chrome only.** No JSX business-logic, data-flow, or API changes. Only navigation/layout structure and CSS.
- **Tokens only** in new/edited CSS — no raw hex/rgb literals (respect Stream A). Use `--primary-*`, `--gray-*`, `--space-*`, `--radius-*`, `--text-*`, `--primary-alpha-*`, `--edge-padding`.
- **Container standard = 1400px**, via a new `--container-max: 1400px` token and a `.page-container` global class in `index.css`.
- **SectionNav derives everything from `location.pathname`**, never from `ScriptContext` — it must render correct tabs before script data loads. `MainLayout` owns the `deriveScriptId` helper and passes `scriptId` as a prop.
- **No test runner exists** in this repo and none is added. Per-task verification is `npm run build` green plus the manual smoke assertions listed in each task. Live click-through is browser-blocked and login-gated (same limitation documented for Stream A) — nav correctness is verified by reviewing the pathname-derivation logic against the route table.
- **Route table (authoritative):** Scenes `/scenes/:id` · Stripboard `/scripts/:id/stripboard` · Board `/scripts/:id/board` · Reports `/scripts/:id/reports` · Schedule `/scripts/:id/schedule`. A route is a "script route" iff `scriptId` derives from `/scenes/:id` or `/scripts/:id/:section`.
- Run all commands from `frontend/`.

---

### Task 1: `PageHeader` component + `.page-container` container standard

**Files:**
- Create: `frontend/src/components/layout/PageHeader.jsx`
- Create: `frontend/src/components/layout/PageHeader.css`
- Modify: `frontend/src/index.css` (add `--container-max` token + `.page-container` utility)

**Interfaces:**
- Produces: `PageHeader({ title: string, subtitle?: string, icon?: ReactNode, actions?: ReactNode })` — a presentational header block. Consumed by Tasks 4 and 5.
- Produces: `.page-container` global class + `--container-max` token. Consumed by Tasks 4 and 5.

- [ ] **Step 1: Create `PageHeader.jsx`**

```jsx
import React from 'react';
import './PageHeader.css';

const PageHeader = ({ title, subtitle, icon, actions }) => (
  <header className="page-header">
    <div className="page-header-text">
      <h1 className="page-header-title">
        {icon && <span className="page-header-icon">{icon}</span>}
        {title}
      </h1>
      {subtitle && <p className="page-header-subtitle">{subtitle}</p>}
    </div>
    {actions && <div className="page-header-actions">{actions}</div>}
  </header>
);

export default PageHeader;
```

- [ ] **Step 2: Create `PageHeader.css`**

```css
/* PageHeader — one shared page-title block (tokens only) */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.page-header-title {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-3xl);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.page-header-icon {
  display: inline-flex;
  color: var(--primary-500);
}

.page-header-subtitle {
  margin: var(--space-2) 0 0;
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.page-header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: var(--space-3);
  }
}
```

- [ ] **Step 3: Add container token + utility to `index.css`**

In the `:root` block, add alongside the existing `--edge-padding` / layout vars (after `--sidebar-width-viewer: 320px;`):

```css
  --container-max: 1400px;
```

After the `:root { … }` block closes (near the top-level element rules, e.g. after the `body { … }` rule), add the global utility. `.page-container` intentionally has **no padding** — the `.main-content` wrapper it lives inside already applies `var(--edge-padding)`:

```css
/* One contained-width standard for text/table pages (full-bleed pages skip it) */
.page-container {
  max-width: var(--container-max);
  margin: 0 auto;
  width: 100%;
}
```

- [ ] **Step 4: Build**

Run: `npm run build`
Expected: builds green (the new component is defined but not yet imported — that is fine, no error).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/PageHeader.jsx frontend/src/components/layout/PageHeader.css frontend/src/index.css
git commit -m "feat(layout): add shared PageHeader component + .page-container 1400px standard"
```

---

### Task 2: `SectionNav` + `MainLayout` wiring + `Breadcrumb` route fix

**Files:**
- Create: `frontend/src/components/layout/SectionNav.jsx`
- Create: `frontend/src/components/layout/SectionNav.css`
- Modify: `frontend/src/components/layout/MainLayout.jsx`
- Modify: `frontend/src/components/layout/Breadcrumb.jsx:11-20` (`ROUTE_CONFIG`)

**Interfaces:**
- Produces: `SectionNav({ scriptId: string })` — presentational tab bar; active tab derived from `useLocation()`. Rendered only by `MainLayout`.
- Consumes: nothing from earlier tasks.

- [ ] **Step 1: Create `SectionNav.jsx`**

```jsx
import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { List, ClipboardList, LayoutGrid, FileText, CalendarDays } from 'lucide-react';
import './SectionNav.css';

const SECTIONS = [
  { key: 'scenes', label: 'Scenes', icon: List, to: (id) => `/scenes/${id}` },
  { key: 'stripboard', label: 'Stripboard', icon: ClipboardList, to: (id) => `/scripts/${id}/stripboard` },
  { key: 'board', label: 'Board', icon: LayoutGrid, to: (id) => `/scripts/${id}/board` },
  { key: 'reports', label: 'Reports', icon: FileText, to: (id) => `/scripts/${id}/reports` },
  { key: 'schedule', label: 'Schedule', icon: CalendarDays, to: (id) => `/scripts/${id}/schedule` },
];

// Active section derived from the URL only (not from ScriptContext).
const activeKey = (pathname) => {
  if (/^\/scenes\/[^/]+$/.test(pathname)) return 'scenes';
  const m = pathname.match(/^\/scripts\/[^/]+\/(stripboard|board|reports|schedule)/);
  return m ? m[1] : null;
};

const SectionNav = ({ scriptId }) => {
  const { pathname } = useLocation();
  if (!scriptId) return null;
  const active = activeKey(pathname);

  return (
    <nav className="section-nav" aria-label="Script sections">
      {SECTIONS.map(({ key, label, icon: Icon, to }) => (
        <NavLink
          key={key}
          to={to(scriptId)}
          className={`section-nav-tab${active === key ? ' active' : ''}`}
        >
          <Icon size={16} />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
};

export default SectionNav;
```

- [ ] **Step 2: Create `SectionNav.css`** (mirrors the `.topbar-nav-item` active pattern already in `Layout.css`)

```css
/* SectionNav — persistent lateral nav between a script's five sections */
.section-nav {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--edge-padding);
  background: var(--gray-800);
  border-bottom: 1px solid var(--border-color);
  overflow-x: auto;
}

.section-nav-tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: 500;
  white-space: nowrap;
  text-decoration: none;
  transition: all 0.15s ease;
}

.section-nav-tab:hover {
  color: var(--text-primary);
  background: var(--gray-700);
}

.section-nav-tab.active {
  color: var(--primary-500);
  background: var(--primary-alpha-15);
  font-weight: 600;
}

@media (max-width: 480px) {
  .section-nav-tab span { display: none; }
}
```

- [ ] **Step 3: Wire `SectionNav` into `MainLayout.jsx`**

Replace the entire file with:

```jsx
import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import TopBar from './TopBar';
import Breadcrumb from './Breadcrumb';
import SectionNav from './SectionNav';
import './Layout.css';

const FULL_BLEED_PATTERNS = [/\/board$/, /\/schedule$/];

// Script routes are /scenes/:id and /scripts/:id/:section — SectionNav renders for these only.
const deriveScriptId = (pathname) => {
  const scenes = pathname.match(/^\/scenes\/([^/]+)$/);
  if (scenes) return scenes[1];
  const section = pathname.match(/^\/scripts\/([^/]+)\/(?:stripboard|board|reports|schedule)/);
  return section ? section[1] : null;
};

const MainLayout = () => {
  const location = useLocation();
  const isFullBleed = FULL_BLEED_PATTERNS.some(p => p.test(location.pathname));
  const scriptId = deriveScriptId(location.pathname);

  return (
    <div className="main-layout no-sidebar">
      <TopBar />
      <Breadcrumb />
      {scriptId && <SectionNav scriptId={scriptId} />}
      <main className={`main-content${isFullBleed ? ' main-content--full-bleed' : ''}`}>
        <Outlet />
      </main>
    </div>
  );
};

export default MainLayout;
```

- [ ] **Step 4: Fix `Breadcrumb.jsx` `ROUTE_CONFIG`**

Replace the `ROUTE_CONFIG` object (`Breadcrumb.jsx:11-20`) with — adds `/board`, `/schedule`, `/profile`; removes dead `/edit`, `/manage`, `/characters`:

```js
const ROUTE_CONFIG = {
    '/scripts': { label: 'My Scripts', parent: null },
    '/scenes/:scriptId': { label: 'Scene Breakdown', parent: '/scripts' },
    '/scripts/:scriptId/stripboard': { label: 'Stripboard', parent: '/scripts' },
    '/scripts/:scriptId/board': { label: 'Board', parent: '/scripts' },
    '/scripts/:scriptId/reports': { label: 'Reports', parent: '/scripts' },
    '/scripts/:scriptId/schedule': { label: 'Schedule', parent: '/scripts' },
    '/upload': { label: 'Upload Script', parent: '/scripts' },
    '/profile': { label: 'Profile', parent: null },
};
```

- [ ] **Step 5: Build**

Run: `npm run build`
Expected: builds green.

- [ ] **Step 6: Manual smoke assertions** (review-level; live-drive is blocked)

Confirm by reading the code: `deriveScriptId` returns the id for `/scenes/x`, `/scripts/x/stripboard|board|reports|schedule`, and `null` for `/scripts`, `/upload`, `/profile`, `/`. `activeKey` marks the matching tab for each of the five section routes. `Breadcrumb` now matches `/scripts/:id/board` and `/scripts/:id/schedule`.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/layout/SectionNav.jsx frontend/src/components/layout/SectionNav.css frontend/src/components/layout/MainLayout.jsx frontend/src/components/layout/Breadcrumb.jsx
git commit -m "feat(nav): add persistent SectionNav in MainLayout; fix Breadcrumb routes (board/schedule/profile)"
```

---

### Task 3: Retire `ViewSwitcher`; slim `ScriptHeader`

**Files:**
- Delete: `frontend/src/components/shared/ViewSwitcher.jsx`
- Delete: `frontend/src/components/shared/ViewSwitcher.css`
- Modify: `frontend/src/components/board/BoardToolbar.jsx` (remove import + usage)
- Modify: `frontend/src/components/schedule/ShootingSchedulePage.jsx` (remove import + usage)
- Modify: `frontend/src/components/metadata/ScriptHeader.jsx` (remove four section buttons + now-unused icon imports)

**Interfaces:**
- Consumes: SectionNav from Task 2 now provides the navigation these removed controls used to.

- [ ] **Step 1: Confirm no other consumers of `ViewSwitcher`**

Run: `grep -rn "ViewSwitcher" frontend/src`
Expected: only `BoardToolbar.jsx`, `ShootingSchedulePage.jsx`, and the `ViewSwitcher.*` files themselves. If any other file imports it, stop and report.

- [ ] **Step 2: Remove `ViewSwitcher` from `BoardToolbar.jsx`**

Delete the import line `import ViewSwitcher from '../shared/ViewSwitcher';` (line 5) and the usage `<ViewSwitcher scriptId={scriptId} />` (inside `.toolbar-section`, ~line 21). Leave the surrounding `.toolbar-section` div and everything else intact.

- [ ] **Step 3: Remove `ViewSwitcher` from `ShootingSchedulePage.jsx`**

Delete the import line `import ViewSwitcher from '../shared/ViewSwitcher';` (line 5) and the usage `<ViewSwitcher scriptId={scriptId} />` (~line 172, inside `.schedule-header-left`). Leave the `.schedule-header-left` / `.schedule-title-group` markup (the script-name label) intact.

- [ ] **Step 4: Delete the `ViewSwitcher` files**

```bash
git rm frontend/src/components/shared/ViewSwitcher.jsx frontend/src/components/shared/ViewSwitcher.css
```

- [ ] **Step 5: Remove the four section buttons from `ScriptHeader.jsx`**

In `.header-right`, delete the four `<button className="header-action-btn primary">` blocks whose labels are **Stripboard**, **Board**, **Reports**, and **Schedule** (they call `navigate('/scripts/${scriptId}/stripboard|board|reports|schedule')`). **Keep** the **Team** button (`title="Team Members"`, `onClick={() => setTeamDrawerOpen(true)}`, `<Users>`), the Info popover block above them, and the `<TeamDrawer>` element below.

Then update the icon import (`ScriptHeader.jsx:1-16`) to drop the now-unused `List`, `ClipboardList`, `LayoutGrid`, `CalendarDays` (they were only used by the deleted buttons). **Keep** `User`, `Mail`, `Phone`, `Info`, `Copy`, `Check`, `FileText` (Info popover), and `Users` (Team). Resulting import:

```jsx
import {
    User,
    Mail,
    Phone,
    Info,
    Copy,
    Check,
    FileText,
    Users
} from 'lucide-react';
```

- [ ] **Step 6: Build**

Run: `npm run build`
Expected: builds green, no unused-import or undefined-component errors.

- [ ] **Step 7: Verify no orphaned references**

Run: `grep -rn "ViewSwitcher" frontend/src` → expect no matches.
Run: `grep -rn "header-action-btn" frontend/src/components/metadata/ScriptHeader.jsx` → expect only the Info trigger + Team button remain.

- [ ] **Step 8: Commit**

```bash
git add -A frontend/src
git commit -m "refactor(nav): retire ViewSwitcher and remove ScriptHeader section buttons (SectionNav replaces them)"
```

---

### Task 4: Move `/profile` into `MainLayout`; adopt `PageHeader`

**Files:**
- Modify: `frontend/src/App.jsx` (move the `profile` route inside the `MainLayout` parent)
- Modify: `frontend/src/pages/ProfilePage.jsx` (drop Back button; adopt `PageHeader` + `.page-container`)

**Interfaces:**
- Consumes: `PageHeader` + `.page-container` (Task 1); the `/profile` breadcrumb entry (Task 2).

- [ ] **Step 1: Move the route in `App.jsx`**

Inside `<Route path="/" element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>`, add a child route after the `schedule` route:

```jsx
                    <Route path="profile" element={<ProfilePage />} />
```

Then delete the standalone block that currently sits after the parent route closes:

```jsx
                  {/* Protected routes outside MainLayout */}
                  <Route path="profile" element={
                    <ProtectedRoute>
                      <ProfilePage />
                    </ProtectedRoute>
                  } />
```

(The child inherits the parent `ProtectedRoute`, so `/profile` stays protected; the resulting URL is unchanged.)

- [ ] **Step 2: Update `ProfilePage.jsx` header**

Add the import near the other imports:

```jsx
import PageHeader from '../components/layout/PageHeader';
```

Replace the header + container markup:

```jsx
    return (
        <div className="profile-page">
            <div className="profile-container">
                {/* Header */}
                <div className="profile-header">
                    <button className="back-btn" onClick={() => navigate(-1)}>
                        <ArrowLeft size={20} />
                        <span>Back</span>
                    </button>
                    <h1>My Profile</h1>
                </div>
```

with:

```jsx
    return (
        <div className="profile-page">
            <div className="page-container">
                <PageHeader title="My Profile" />
```

- [ ] **Step 3: Drop the now-unused `ArrowLeft` import**

In the lucide-react import in `ProfilePage.jsx`, remove `ArrowLeft,` (its only use was the deleted Back button — confirm with `grep -n "ArrowLeft" frontend/src/pages/ProfilePage.jsx` showing no remaining usage after the edit).

- [ ] **Step 4: Build**

Run: `npm run build`
Expected: builds green.

- [ ] **Step 5: Manual smoke assertions**

Read-confirm: `/profile` is now a child of the `MainLayout` route → it renders TopBar + Breadcrumb ("My Scripts › Profile") + `.main-content`; `deriveScriptId('/profile')` is `null` so no SectionNav; ProfilePage shows `PageHeader` with no floating Back button; content is centered at 1400px via `.page-container`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.jsx frontend/src/pages/ProfilePage.jsx
git commit -m "feat(layout): move /profile into MainLayout shell; adopt PageHeader + .page-container"
```

---

### Task 5: Adopt `PageHeader` + `.page-container` on Library, Upload, Stripboard, Reports

**Files:**
- Modify: `frontend/src/components/scripts/ScriptLibrary.jsx`
- Modify: `frontend/src/components/script/ScriptUpload.jsx`
- Modify: `frontend/src/components/reports/Stripboard.jsx`
- Modify: `frontend/src/components/reports/ReportBuilder.jsx`

**Interfaces:**
- Consumes: `PageHeader` + `.page-container` (Task 1).

Import depth for all four files (each is one level under `components/`): use `import PageHeader from '../layout/PageHeader';`.

- [ ] **Step 1: `ScriptLibrary.jsx`** — keep the "Upload New" button as `actions`

Add import: `import PageHeader from '../layout/PageHeader';`

Replace:

```jsx
            <div className="library-header">
                <div>
                    <h1>My Scripts</h1>
                    <p className="library-subtitle">Manage your screenplays and breakdowns</p>
                </div>
                {scripts.length > 0 && (
                    <button
                        className="upload-new-btn"
                        onClick={() => navigate('/upload')}
                    >
                        <Plus size={18} />
                        Upload New
                    </button>
                )}
            </div>
```

with:

```jsx
            <PageHeader
                title="My Scripts"
                subtitle="Manage your screenplays and breakdowns"
                actions={scripts.length > 0 && (
                    <button className="upload-new-btn" onClick={() => navigate('/upload')}>
                        <Plus size={18} />
                        Upload New
                    </button>
                )}
            />
```

Then change the outer wrapper `<div className="library-container">` to `<div className="library-container page-container">` (keep the existing class so its non-width styles survive; `.page-container` supplies the 1400px width + centering).

- [ ] **Step 2: `ScriptUpload.jsx`** — de-hero the header

Add import: `import PageHeader from '../layout/PageHeader';`

Replace:

```jsx
            <div className="upload-header">
                <h1>Upload New Script</h1>
                <p>Upload your screenplay and we'll detect all scenes. You can then analyze each scene for breakdown details.</p>
            </div>
```

with:

```jsx
            <PageHeader
                title="Upload New Script"
                subtitle="Upload your screenplay and we'll detect all scenes. You can then analyze each scene for breakdown details."
            />
```

Change the outer wrapper `<div className="upload-page">` to `<div className="upload-page page-container">`.

- [ ] **Step 3: `Stripboard.jsx`**

Add import: `import PageHeader from '../layout/PageHeader';`

Replace:

```jsx
            <div className="stripboard-header">
                <h1>
                    <List size={24} />
                    One-Liner / Stripboard
                </h1>
            </div>
```

with:

```jsx
            <PageHeader icon={<List size={24} />} title="One-Liner / Stripboard" />
```

Change the outer wrapper `<div className="stripboard">` to `<div className="stripboard page-container">`. (`List` is still imported/used here — keep it.)

- [ ] **Step 4: `ReportBuilder.jsx`**

Add import: `import PageHeader from '../layout/PageHeader';`

Replace:

```jsx
                <div className="report-builder-header">
                    <h1>
                        <FileText size={24} />
                        Generate Reports
                    </h1>
                </div>
```

with:

```jsx
                <PageHeader icon={<FileText size={24} />} title="Generate Reports" />
```

Change the outer wrapper `<div className="report-builder">` to `<div className="report-builder page-container">`. (`FileText` is still used elsewhere — keep it.)

- [ ] **Step 5: Build**

Run: `npm run build`
Expected: builds green.

- [ ] **Step 6: Manual smoke assertions**

Read-confirm all four pages now render `<PageHeader>` (one consistent title block, left-aligned) inside a `.page-container` (1400px, centered). Upload is no longer a centered hero. The Library "Upload New" button still appears (as header actions) only when `scripts.length > 0`.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/scripts/ScriptLibrary.jsx frontend/src/components/script/ScriptUpload.jsx frontend/src/components/reports/Stripboard.jsx frontend/src/components/reports/ReportBuilder.jsx
git commit -m "refactor(layout): adopt PageHeader + .page-container on Library, Upload, Stripboard, Reports"
```

---

## Post-Task: Final whole-branch review

After Task 5, dispatch the final whole-branch code review (most capable model) per subagent-driven-development, then use superpowers:finishing-a-development-branch. Review focus: no stray `ViewSwitcher`/removed-button references; SectionNav/Breadcrumb pathname logic matches the route table; no color-literal regressions in new CSS; the five adopted pages share one header + 1400px container; `/profile` renders in-shell.

## Self-Review notes (author)

- **Spec coverage:** SectionNav + MainLayout + Breadcrumb (L2) → Tasks 2–3; `/profile` in shell (L1) → Task 4; PageHeader + 1400px container (L3) → Tasks 1, 4, 5. All spec deliverables mapped.
- **Type/name consistency:** `PageHeader` props (`title/subtitle/icon/actions`) identical across Tasks 1, 4, 5. `deriveScriptId`/`activeKey` regexes both use the same five-section set. `.page-container` and `--container-max` defined once (Task 1), consumed by 4/5.
- **Import depth:** PageHeader consumers in `components/{scripts,script,reports}/` use `../layout/PageHeader`; ProfilePage in `pages/` uses `../components/layout/PageHeader`.
