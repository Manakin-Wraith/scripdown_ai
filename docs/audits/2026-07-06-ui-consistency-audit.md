# UI/UX Consistency Audit — SlateOne Frontend

**Date:** 2026-07-06
**Scope:** Core user-facing app (per `docs/superpowers/specs/2026-07-06-ui-consistency-audit-design.md`). Excludes Admin, campaigns, auth pages.
**Method:** Static sweep of `frontend/src` (4 parallel lens audits) + live visual pass on production (app.slateone.studio, script "Script_Powerlessness", 194 scenes). Visual findings were verified live in-browser; screenshots were reviewed during the session but are not embedded in this document.

**Severity key:** 🔴 High = users notice / erodes trust · 🟡 Medium = visible inconsistency · ⚪ Low = code hygiene.

---

## Executive summary

The app has a real design system on paper (slate & amber tokens in `index.css`) but almost nothing enforces it: **1,988 hardcoded color literals across 71 of 73 in-scope CSS files**, two leftover palettes from earlier design eras (Tailwind cool-gray, ~239 uses; pre-rebrand indigo/blue, ~130 uses — visibly live on the scene-breakdown cards), and **no shared UI primitives at all** — no Button, Modal, Drawer, Spinner, EmptyState, Badge, or Table component exists. Every feature re-implements them: `.btn-primary` is redefined in 17 files, `@keyframes spin` in 47, `.modal-overlay` in 5, and there are two competing ConfirmDialogs. Interaction patterns fragment the same way: confirming a destructive action happens three different ways, and user feedback ranges from toasts to `alert()` to silence depending on the feature. Navigation between a script's sections relies on three disagreeing mechanisms, and `/profile` renders outside the app shell entirely (no top bar — confirmed live).

The good news: the token palette itself is coherent, the drawer-based UX is a solid pattern, most rogue colors map 1:1 onto existing tokens, and roughly a quarter of the duplication (dead sidebar CSS, orphaned pages, unused routes) can simply be deleted.

---

## Lens 1 — Token compliance

### 🔴 T1. Hardcoded colors bypass the token system almost everywhere
1,988 hex/rgb(a) literals across 71 of 73 in-scope CSS files. `box-shadow`: 161 of 163 declarations hardcode values; the `--shadow-*` tokens are used twice in total. Worst files: `schedule/ShootingSchedule.css` (151), `scenes/SceneDetail.css` (124), `reports/Stripboard.css` (101), `notes/NoteDrawer.css` (81), `scenes/SceneManager.css` (75).

Most recurring rogue values map directly onto existing tokens — this is mechanical cleanup:
`#94a3b8`→`--gray-400` (78×), `#ef4444`→`--danger` (67×), `#334155`→`--gray-700` (67×), `#f59e0b`→`--primary-500` (61×), `#f1f5f9`→`--gray-100` (48×), `#22c55e`→`--success` (37×), plus exact-match literals for `--danger-bg`, `--success-bg`, and `--shadow-sm` that ignore their own tokens.

### 🔴 T2. Two foreign palettes still live in the product
- **Tailwind cool-gray** (~239 occurrences: `#374151`, `#9ca3af`, `#1f2937`, `#e5e7eb`, `#6b7280`, `#f3f4f6`, `#111827`, `#4b5563`) runs parallel to the slate `--gray-*` scale — near-duplicate hues that make surfaces subtly mismatch. Many are wrong-palette *fallbacks inside token refs*, e.g. `var(--gray-800, #1F2937)` (`auth/AuthModal.css:69`).
- **Legacy indigo/blue brand** (~130 occurrences: `#6366f1`, `#818cf8`, `#4f46e5`, `#3b82f6`, `#60a5fa`) survives in Board, Schedule popovers, and BreakdownDrawer — including indigo fallbacks wired to amber tokens: `var(--primary-400, #818cf8)` (`board/BoardCanvas.css:19`), `var(--primary-600, #4f46e5)` (`board/BoardToolbar.css:57`). **Visually confirmed live:** the scene-breakdown category cards (Characters, Props, Wardrobe…) render with blue/indigo icons and blue chips inside the amber-branded app.

### 🟡 T3. No size/spacing/radius scale exists
`index.css` defines only colors, two layout dims, and shadows. Sampling the 10 largest files: **36 distinct font-sizes** (mixed rem/px/pt), **19 distinct border-radius values** including malformed shorthands (`6px6px00`, `12px12px00`, `0012px12px` — visible bugs). Six near-duplicate small font sizes (0.65–0.68rem) exist with no rationale.

### 🟡 T4. Duplicate `:root` and undefined variables
`components/layout/Layout.css:2-7` declares a second `:root` (`--edge-padding`, `--sidebar-width-viewer`, redundant `--header-height`). `Layout.css:58` consumes `--sidebar-width-collapsed`, which is **defined nowhere**.

### ⚪ T5. No typography tokens for the mono/serif stacks
`'Courier New'` screenplay stacks hardcoded in 7+ places (`SceneModals.css`, `SceneEditor.css:56`, `SceneDetail.css:294`…), `SF Mono` stacks in 4, with no `--font-mono`/`--font-screenplay` token.

---

## Lens 2 — Component duplication

What exists today as "shared": `ToastContext`, `ConfirmDialogContext`, one nav pill (`shared/ViewSwitcher`), and element-level `styles/forms.css`. **No generic Button, Modal, Drawer, Spinner, EmptyState, Badge, Tooltip, Dropdown, or Table component exists.** Ranked by consolidation value:

### 🔴 C1. Buttons — 17 independent `.btn-primary` definitions
No shared Button. `.btn-primary` is redefined in 17 CSS files (ConfirmDialog, ExportOptionsModal, ReportBuilder, RevisionImportWizard, SceneEditor, SceneModals, SceneViewer, ScriptUpload, InviteModal, CharacterProfile, SettingsPage…), plus whole bespoke button namespaces that skip `.btn-*` entirely (`.bm-*`, `.cdp-*`, `.sa-*`, `.ss-*`, `.chip-btn`, `.vs-pill`). Padding/radius/hover drift freely.

### 🔴 C2. Spinners — `@keyframes spin` copy-pasted in 47 files
Eight named spinner classes (`.spinner`, `.spinner-sm`, `.spinner-small`, `.upload-spinner`, `.bm-spinner`…). One `Spinner` component + one keyframe replaces all of it. No skeleton system exists anywhere.

### 🔴 C3. Modals — ~13 independent implementations, 2 ConfirmDialogs
Each modal ships its own overlay/container/close markup; the generic class name `.modal-overlay` is independently redefined in 5 CSS files. Two ConfirmDialog copies exist — `components/common/ConfirmDialog.jsx` and `context/ConfirmDialogContext.jsx` — with duplicated CSS and **different z-index** (10000 vs 9999). The scenes cluster (`SceneModals.css` shared by 4 modals) is the one good internal example.

### 🟡 C4. Drawers — 5 implementations, 4 copy-pasting the same classes
`NoteDrawer` and `TeamDrawer` near-duplicate identical `.drawer-header`/`.drawer-title-group` markup+CSS; `FeedbackDrawer` diverges entirely; `BreakdownDrawer` nests its own confirm overlay inside.

### 🟡 C5. Empty states — ~25 ad-hoc versions; Badges — ~30 classes
`.empty-state` plus feature-prefixed reinventions (`.bd-empty`, `.board-empty-state`, `.drawer-empty`, `.stripboard-empty`…). **Confirmed live:** breakdown cards mix copy patterns ("No wardrobe notes" vs "No special FX detected"). Badges: ~30 classes; `.cdp-status-*` has a full 6-color status system other features partially duplicate.

### 🟡 C6. Form classes — used in JSX, defined nowhere central
`styles/forms.css` styles bare elements only. `.form-group` (used 50×) is independently defined in **9 files**; 26 in-scope CSS files locally restyle `input`/`select`/`textarea`.

### ⚪ C7. Tooltips (4 systems), dropdown menus (5 systems), tables (4 — genuinely different use cases; lowest priority).

---

## Lens 3 — Interaction patterns

### 🔴 I1. Destructive-action confirms happen three different ways
- Canonical `useConfirmDialog()`: scenes (`SceneEditor.jsx:148`), script library.
- Raw `window.confirm`: schedule (`DayColumn.jsx:55`, `ShootingSchedulePage.jsx:115`), notes (`DepartmentNotesSection.jsx:140`), reports (`ReportBuilder.jsx:177`, `ShareModal.jsx:51`) — browser-native dialog that ignores the app's theme.
- Hand-rolled inline confirm overlays: `TeamDrawer.jsx:411,448`, `NoteDrawer.jsx:456`, `BreakdownDrawer.jsx:874,892` — with different class systems (`confirm-*` vs `bd-confirm-*`).
Deleting a note alone is done three ways depending on where you do it. **Standardize on `useConfirmDialog`.**

### 🔴 I2. User feedback: toast vs `alert()` vs inline vs silence
Toast is the majority pattern (scenes, schedule, board, team, reports), but: `alert()` survives in `ScriptSummary.jsx:135` and `CreditPurchaseModal.jsx:47,50`; the **entire notes feature succeeds silently** (`NoteDrawer.jsx`, `DepartmentNotesSection.jsx` — inline error string only, no success feedback); breakdown funnels everything to an inline banner (`BreakdownDrawer.jsx:471`); several paths swallow errors (`ReportBuilder.jsx:100,116,125` console.warn and continue; `Stripboard.jsx:81,122` `.catch(() => ({items:[]}))`). `TeamDrawer` is inconsistent with itself (inline error for load, toast for mutations).

### 🟡 I3. Overlay dismissal is per-component roulette
Most modals close on overlay-click but **not Escape**; drawers close on backdrop-click but not Escape; the nested confirm overlays (I1) close on **neither**; `SceneEditor`'s form modal only via its close button. Only `ConfirmDialogContext` and `StripDetailDrawer` do both. This is the direct cost of having no shared Modal/Drawer primitive (C3/C4).

### 🟡 I4. Async-action loading is mostly consistent, with gaps
Dominant, good pattern: disabled button + inline `Loader` spin. Gaps: `NoteDrawer` delete/toggle give no in-flight feedback; `SceneDetail` inline saves disable without spinner.

### ⚪ I5. Edit-pattern rule is implicit and drifting
Detail = drawer, create = modal mostly holds, but notes can't be edited at all while breakdown items edit inline, and `InviteModal` opens a modal from inside a drawer. Document the rule when building the shared primitives.

---

## Lens 4 — Layout & navigation

### 🔴 L1. `/profile` renders outside the app shell
Deliberately mounted outside `MainLayout` (`App.jsx:83-88`): no TopBar, no breadcrumb, just a floating "Back" button. **Confirmed live** — it reads as a different product.

### 🔴 L2. Three disagreeing mechanisms for in-script navigation
- `ScriptHeader` buttons on the scene hub → all 4 sections (Stripboard/Board/Reports/Schedule).
- `ViewSwitcher` pills → knows only Board + Schedule.
- `Breadcrumb` → its `ROUTE_CONFIG` (`Breadcrumb.jsx:11-20`) lists routes that don't exist and **omits `/board` and `/schedule`**, so those pages get no breadcrumb.
Net effect (confirmed live): from Stripboard or Reports there is **no lateral navigation** to sibling sections — you go back through the scene hub. Board/Schedule swap to an entirely different chrome (canvas toolbar, no breadcrumb). The script toolbar itself scrolls away contextually on the scene hub while the section pages lose it altogether.

### 🟡 L3. Nine bespoke page headers, five different max-widths
Every screen invents its own `*-header` class (`library-header`, `upload-header`, `stripboard-header`, `report-builder-header`, `schedule-header`, `profile-header`…). Container max-widths: 800 (upload) / 1000 (profile) / 1200 (library) / 1400 (reports, stripboard) / none (scene hub, board, schedule); padding 2rem vs 1.5rem. `Layout.css` ships a `--main-content--contained` (1600px) helper **no page uses**. Confirmed live: Upload uses a centered hero title; every other page is left-aligned.

### 🟡 L4. Significant dead layout code and orphaned pages
- ~285 lines of sidebar CSS (`Layout.css:41-327`) for a `.sidebar` no component renders (the real shell is a TopBar); `--sidebar-width` token consumed by nothing.
- Dead routes/components: `SettingsPage`, `ScriptEditorPage`, `SceneManager`, `DepartmentWorkspace`, `ShootingScriptPreview`, `CharacterProfile` (commented imports, `App.jsx:37-42,73-80`); `dashboard/Dashboard.jsx` and `metadata/ScriptHero.jsx` imported by zero files. Note: several appear in this audit's duplication counts — deleting them shrinks the problem for free (decide resurrect-vs-delete first).

### 🟡 L5. Z-index escalation war
No scale: modals cluster at hardcoded 1000 (16 files), then 1100 (drawer confirms), 9000/9001, a 9999 tier (`Toast`, context `ConfirmDialog`, `ScriptHeader.css:435` — an in-page header element at overlay altitude), topped by common `ConfirmDialog` at 10000.

### 🟡 L6. Responsive coverage is patchy
`768px` is the de-facto standard (39 uses) but 8+ ad-hoc breakpoints exist; the **entire Board feature ships zero responsive rules**, as do `ScriptTable` (the landing-page table), `SceneDetail`, `BreakdownDrawer`, and Upload.

### ⚪ L7. No spacing scale; rem- and px-based files coexist (header paddings range `0.5rem 1.5rem` → `1.25rem 1.5rem` → `10px 20px` in the same app).

---

## Live visual pass — screen notes

| Screen | State | Notes |
|---|---|---|
| Script library | ✅ solid | Clean table; header pattern is the best candidate baseline |
| Scene hub (breakdown) | ⚠️ | Indigo/blue card icons & chips vs amber brand (T2); mixed empty-state copy (C5); three stacked header bars; app header scrolls away while toolbar sticks |
| Breakdown drawer | ✅ good UX | Script-text highlight + chips work well; inline-banner errors only (I2) |
| Stripboard | ⚠️ | Good stats bar; no lateral nav to siblings (L2); NIGHT badge purple vs DAY amber vs day-number teal — three badge systems in one row |
| Board | ⚠️ | Different chrome entirely; indigo accents; zero responsive (L6) |
| Reports | ✅ solid | Consistent with stripboard pattern; window.confirm on delete/revoke (I1) |
| Schedule | ⚠️ | Third chrome variant; schedule tabs pattern appears nowhere else |
| Team drawer | ✅ good | Best drawer example; nested custom confirms (I1); InviteModal-inside-drawer (I5) |
| Profile | 🔴 | No TopBar/breadcrumb (L1) |
| Upload | ⚠️ | Centered hero header unlike all other pages (L3) |
| Settings / script editor | — | Dead routes (L4) — unreachable in production |

---

## Fix roadmap

Constraint honored: plain CSS + variables stays; consolidation, not migration. Each phase is independently shippable.

### Phase 1 — Foundation (small, high leverage)
1. **Merge tokens:** fold `Layout.css` `:root` into `index.css`; define or delete `--sidebar-width-collapsed`; fix malformed border-radius values (T4, T3).
2. **Extend the scale:** add `--space-*` (4px grid), `--radius-*` (3 sizes), `--text-*` font-size scale, `--font-mono`/`--font-screenplay`, amber-alpha tokens (`rgba(245,158,11,…)` × 134 uses), and a `--z-*` ladder (dropdown < sticky < drawer < modal < confirm < toast) (T3, T5, L5).
3. **Kill the dead code:** delete orphaned sidebar CSS, `Dashboard.jsx`, `ScriptHero.jsx`, and the six dead-route components — or explicitly decide which come back (L4). This alone removes a chunk of the duplication counts.
4. **Retire the foreign palettes decision-first:** map cool-gray → slate 1:1; decide whether Board/Schedule's indigo becomes amber or a sanctioned secondary accent token (T2). Do the actual replacement per-domain in Phase 3.

### Phase 2 — Shared primitives (`components/ui/`)
Build once, in this order (highest duplication × visibility first):
1. `Button` (primary/secondary/danger/ghost + loading state) — kills 17 `.btn-primary` defs and absorbs I4's pattern.
2. `Spinner` (+ one global keyframe) — kills 47 duplicates.
3. `Modal` + `Drawer` shells (portal, backdrop, Escape + overlay-click, focus trap, z-tokens) — kills 13 modal implementations, unifies dismissal (I3); delete `components/common/ConfirmDialog.jsx` in favor of the context version rebuilt on `Modal` (C3).
4. `EmptyState`, `Badge` (variant-driven status colors, adopting the `.cdp-*` 6-color system), `Spinner`-based table/list loading.
5. Promote `.form-group`/`.form-row`/`.form-actions` into `styles/forms.css`; delete the 9 local copies (C6).
6. **Interaction rules, enforced by the primitives:** all confirms via `useConfirmDialog`; all transient feedback via `useToast` (kill `alert()`, silent successes, swallowed errors); inline banners reserved for full-view load failures. Document detail=drawer / create=modal (I1, I2, I5).

### Phase 3 — Domain-by-domain adoption (ordered by user visibility)
For each domain: swap primitives in, codemod color literals → tokens, remove local CSS. Suggested order:
1. **Scene hub + breakdown** (daily-driver screens; also resolves the indigo cards, T2).
2. **Stripboard + Reports + navigation fix:** persistent section nav (extend `ViewSwitcher` to all 4 sections and mount it on every script page), breadcrumb entries for `/board`/`/schedule` (L2).
3. **Board + Schedule:** palette alignment + minimum responsive pass (L6).
4. **Team/notes/feedback drawers** onto shared `Drawer` (C4, I1, I2).
5. **Library, Upload, Profile:** standard `PageHeader` + container (L3); move `/profile` inside `MainLayout` (L1).

**Definition of done per domain:** zero hex/rgb literals outside `index.css`, zero local `@keyframes spin`, zero `window.confirm`/`alert()`, overlays via shared shells, breakpoints from the standard set (768/480/1024).
