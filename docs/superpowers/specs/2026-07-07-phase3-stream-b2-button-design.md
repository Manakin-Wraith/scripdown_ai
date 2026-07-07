# Phase 3 · Stream B2 — Button Adoption — Design

**Date:** 2026-07-07
**Status:** Approved (design)
**Parent:** `docs/audits/2026-07-06-ui-consistency-audit.md` (Phase 2/3 — shared primitives). Stream B is decomposed by primitive: B1 Spinner (merged), **B2 Button (this)**, B3 Modal/Drawer, B4 Badge/EmptyState, B5 interaction rules. Streams A, C, D, B1 are merged.
**Goal:** Adopt the `<Button>` primitive for the app's generic `btn-primary`/`btn-secondary`/`btn-tertiary` buttons, and consolidate the scattered duplicate `.btn-*` CSS definitions into one canonical set — standardizing the primary button to a solid `--primary-600` look.

## Context

The `<Button>` primitive (`components/ui/Button.jsx`) is built and already live in the scenes-cluster modals + `ConfirmDialogContext`. API: `{ variant: 'primary'|'secondary'|'danger'|'ghost', size: 'sm'|'md', loading, disabled, icon, iconPosition, fullWidth, className, ...rest }` → renders `<button class="ui-btn ui-btn--{variant} ui-btn--{size}">`, shows a `<Spinner>` when `loading`, and passes `onClick`/`type`/`form`/`aria-*` through via `...rest`. `.ui-btn--primary` is **solid `--primary-600`**.

The generic `.btn-primary` class is defined in many files with **divergent** styling — ~7 use an amber `linear-gradient`, others a solid fill, with different paddings/radii — so buttons sharing the class name render inconsistently. Unlike B1 (Spinner), adopting `<Button>` is therefore a **deliberate visual standardization**, not a zero-change refactor: the ~7 gradient buttons become flat solid, and paddings/radii unify.

**Cascade constraint (important):** 13 out-of-scope files (admin, campaigns, auth, WIP pages) use generic `btn-*` classes in their JSX, and most do **not** define their own `.btn-*` CSS — they rely on an in-scope definition cascading globally. Deleting all in-scope `.btn-*` defs would strip their styling.

## Scope

**In:**
- **Convert generic-`btn-*` JSX to `<Button>`** in these 7 files: `components/reports/ExportOptionsModal.jsx`, `components/reports/ReportBuilder.jsx`, `components/revisions/RevisionImportWizard.jsx`, `components/scenes/SceneViewer.jsx`, `components/script/ScriptUpload.jsx`, `components/subscription/UpgradeModal.jsx`, `components/team/InviteModal.jsx`.
- **Consolidate `.btn-*` CSS** from these 8 files into one canonical global set in `index.css`, then delete the locals: `components/reports/ExportOptionsModal.css`, `components/reports/ReportBuilder.css`, `components/revisions/RevisionImportWizard.css`, `components/scenes/SceneEditor.css`, `components/scenes/SceneModals.css`, `components/scenes/SceneViewer.css`, `components/script/ScriptUpload.css`, `components/team/InviteModal.css`.

**Variant mapping:** `btn-primary` → `variant="primary"`, `btn-secondary` → `variant="secondary"`, `btn-tertiary` → `variant="ghost"` (closest fit for the 2 uses). Primary is solid `--primary-600` (primitive as-is).

**Out:**
- The ~200 bespoke buttons (toolbar icon buttons, pills, custom/gradient hero CTAs) — not generic `btn-*`, not in scope.
- All excluded areas' JSX (admin/campaigns/auth/WIP) — untouched; they keep using the canonical legacy `.btn-*` classes.
- The excluded areas' OWN `.btn-*` defs (`components/auth/SignupSuccess.css`, `components/campaigns/PersonalEmailModal.css`) — left as-is.
- Other primitives (B3–B5).

## Conversion rule (per button)

- `<button className="btn-primary" onClick={x} type="submit" disabled={d} title="…">Label</button>` → `<Button variant="primary" onClick={x} type="submit" disabled={d} title="…">Label</Button>`. All non-class attributes pass through the primitive's `...rest`.
- **Leading-icon buttons:** `<button className="btn-primary"><Plus size={16}/> Add</button>` → `<Button variant="primary" icon={Plus}>Add</Button>`. Buttons with a trailing icon use `iconPosition="right"`. Buttons with two icons or non-standard icon layout keep their children inside `<Button>` unchanged.
- **Loading buttons:** where a button swaps its label/icon for a spinner while busy, use `<Button variant="primary" loading={busy}>Save</Button>` (the primitive renders `<Spinner>` when `loading` and disables itself). Apply only where the existing pattern maps cleanly; otherwise pass children through and leave loading logic in place.
- **Extra classes preserved:** `className="btn-primary wide"` → `<Button variant="primary" className="wide">` (drop only the generic `btn-*` token; keep the rest).
- Add `import { Button } from '<rel>/ui';` (`components/<domain>/*` → `'../ui'`). Remove now-unused icon imports only if truly unused.

## CSS consolidation (cascade-safe)

1. Add ONE canonical set to `index.css`: `.btn-primary`, `.btn-secondary`, `.btn-tertiary` (plus their `:hover`/`:disabled` states), styled to **visually match** the primitive's `.ui-btn` base + `.ui-btn--primary`/`--secondary`/`--ghost` (solid `--primary-600` primary; `--gray-700`+border secondary; transparent ghost/tertiary). This is a legacy alias so the un-migrated excluded buttons render identically to `<Button>`.
2. Delete the `.btn-primary`/`.btn-secondary`/`.btn-tertiary` rule families (base + `:hover`/`:disabled`/descendant variants) from the 8 in-scope CSS files.

Result: the scattered duplicate defs collapse to one canonical global; migrated buttons use `<Button>`; excluded buttons use the single canonical legacy class and finally render consistently.

## Execution

Per-domain JSX batches convert buttons (each an independently reviewable commit). A final CSS task adds the canonical global set and deletes the 8 local def families — gated on "no in-scope generic-`btn-*` JSX remains" (so the deletions can't strip a still-live in-scope button).

## Verification

- Per batch: `npm run build` green.
- End-of-stream invariants (from `frontend/src`):
  - No in-scope generic-`btn-*` JSX remains: `grep -rE "className=\"[^\"]*\\bbtn-(primary|secondary|tertiary)\\b" --include=*.jsx` (excluding admin/campaigns/auth/WIP) returns nothing.
  - Exactly one `.btn-primary`/`.btn-secondary`/`.btn-tertiary` definition in `index.css` (plus the two untouched excluded-area defs).
  - Excluded-area buttons still resolve to the canonical global class.
- No test runner; live-drive blocked/login-gated (same as prior streams). Correctness rests on build + per-batch review + the invariants + before/after token equivalence (the canonical global matches the primitive; the only intended visual deltas are gradient→solid on ~7 buttons and unified padding/radius).

## Success criteria

- The ~41 in-scope generic-`btn-*` buttons across the 7 files render via `<Button variant=…>`; the primary look is solid `--primary-600` everywhere.
- The 8 scattered `.btn-*` def families are removed; one canonical global set in `index.css` serves all remaining (excluded-area) legacy buttons.
- Build green; work lands as per-domain reviewed commits plus one CSS-consolidation commit.
