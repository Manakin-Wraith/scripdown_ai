# Phase 3 · Stream D — Dead-CSS Deletion — Design

**Date:** 2026-07-07
**Status:** Approved (design)
**Parent:** `docs/audits/2026-07-06-ui-consistency-audit.md` (finding L4; roadmap Phase 1 item 3 / Phase 3 Stream D). Phase 3 streams: A (color tokens, merged), B (primitive adoption), C (nav/layout, merged), D (this — dead-CSS deletion).
**Goal:** Remove provably-dead CSS left over after Phase 1 pruning and the Stream A/C refactors — one orphaned file plus seven orphaned rule-families — with zero rendering change and nothing live touched.

## Scope

This is a **small, targeted janitorial pass**, not the large deletion the audit's L4 originally implied. Re-verification against the current `main` shows most of L4's targets are already handled or actually live:
- Phase 1 already pruned the large dead-sidebar block from `Layout.css`.
- The remaining "sidebar" classes are LIVE: `.logo-icon` (4 JSX uses), `.logo-text` (5), `.sidebar-header` (3), `.user-avatar` (3), `.coming-soon-badge` (1), `no-sidebar` (1) — all consumed by the TopBar/live layout.
- `--sidebar-width-viewer` is consumed by `SceneViewer.css` (not unused).
- `.back-btn` has 4 live JSX uses; `.header-action-btn` and its `.primary` modifier are still used by ScriptHeader's Info trigger and Team button.
- The six commented-out route components (`SettingsPage`, `ScriptEditorPage`, `SceneManager`, `DepartmentWorkspace`, `ShootingScriptPreview`, `CharacterProfile`) are substantial disabled WIP — **kept** per the Phase 1 "delete orphans only, keep WIP" decision.
- `ScriptHero.jsx` and `dashboard/Dashboard.jsx` are already deleted; only `dashboard/Dashboard.css` remains as an orphan.

**In (delete — all verified zero JSX usage):**

1. **Whole file:** `frontend/src/components/dashboard/Dashboard.css` — its `.jsx` sibling is gone and no JSX imports it.
2. **Orphaned rule-families** left behind when Stream C swapped bespoke page headers for the shared `PageHeader`. Delete each rule together with its descendant selectors (`.x h1`, `.x p`, …) and any media-query overrides:
   - `.profile-header`, `.profile-container` — `frontend/src/pages/ProfilePage.css`
   - `.library-header`, `.library-subtitle` — `frontend/src/components/scripts/ScriptLibrary.css`
   - `.upload-header` — `frontend/src/components/script/ScriptUpload.css`
   - `.stripboard-header` — `frontend/src/components/reports/Stripboard.css`
   - `.report-builder-header` — `frontend/src/components/reports/ReportBuilder.css`

**Out (explicitly not touched):**
- The six WIP route components and their CSS, and the commented `App.jsx` imports/routes.
- All verified-live classes/tokens listed above (`.back-btn`, `.header-action-btn`/`.primary`, `.sidebar-*`, `.logo-*`, `.user-avatar`, `no-sidebar`, `--sidebar-width-viewer`).
- `pages/Admin/**`, `components/admin/**`, `components/campaigns/**`, auth — out of the whole effort's scope.
- No exhaustive unused-selector sweep (rejected as risky: dynamically-built classNames and global-cascade sharing produce false positives). Only the enumerated, individually-verified targets.
- No JSX changes at all — this stream removes CSS only.

## Verification method (the safety story)

Each deletion is gated on one proof: **the selector's class token appears in zero `.jsx` files across `frontend/src`.** Grep the bare token (e.g. `grep -rn "profile-header" --include="*.jsx" frontend/src`), not just `className="…"`, so dynamically-constructed class strings (template literals like `` `${x}-header` ``) are also caught. A class token that appears nowhere in any JSX cannot be applied to any element, so deleting its CSS rule cannot change what renders — that is the equivalence argument that stands in for a live click-through (the browser tooling can't load localhost and the app is login-gated, the same limitation documented for Streams A and C).

Per step: confirm the 0-usage grep, delete the rule/file, then `npm run build` stays green. No test runner exists in the repo; this stream adds none.

Re-run the whole-file orphan check with a **path-aware** grep (match the import path suffix, not the bare basename) — `dashboard/Dashboard.css` shares a basename with `scenes/Dashboard.css`, so a basename-only search gives a false "imported" result.

## Success criteria

- `components/dashboard/Dashboard.css` deleted; the seven orphaned rule-families (`.profile-header`, `.profile-container`, `.library-header`, `.library-subtitle`, `.upload-header`, `.stripboard-header`, `.report-builder-header`) removed with their descendant/media-query variants.
- Every deleted selector proven unreferenced (0 JSX usages) at deletion time.
- Nothing on the keep list touched; no JSX changed.
- Build green; the work lands as one or two reviewed commits.
