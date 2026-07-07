# Phase 3 · Stream B1 — Canonical Spinner — Design

**Date:** 2026-07-07
**Status:** Approved (design)
**Parent:** `docs/audits/2026-07-06-ui-consistency-audit.md` (Phase 2/3 — shared primitives). Stream B (primitive adoption) is decomposed **by primitive** into B1 Spinner (this), B2 Button, B3 Modal/Drawer, B4 Badge/EmptyState, B5 interaction rules. Streams A (color tokens), C (nav/layout), D (dead CSS) are merged.
**Goal:** Make the Phase 2 `<Spinner>` primitive the one loading spinner across the app and collapse the 58 duplicate `@keyframes spin` into a single global keyframe — no visual change except a deliberate standardization of spin speed to 1s.

## Context

The six `components/ui/` primitives exist (built and proven in the scenes cluster in Phase 2) but adoption stopped there. The rest of the app duplicates loading spinners: 58 files define a local `@keyframes spin`, and ~86 JSX elements carry a `spin` class on a lucide icon. Breakdown of the spinning icons: ~67 `<Loader>`, 4 `<Loader2>`, 15 `<RefreshCw>`; classNames are mostly the plain `"spin"` with a handful of multi-class cases (`status-icon processing spin`, `status-icon analyzing spin`, `spin upload-spinner`, `sp-spin`).

The `<Spinner>` primitive (`components/ui/Spinner.jsx`) renders `<span class="ui-spinner" role="status" aria-label>` wrapping lucide `Loader2`, animated by its own scoped `@keyframes ui-spin` (in `Spinner.css`). Props: `{ size = 16, label = 'Loading', className = '' }`.

## Scope

**In:**
1. **One global source in `index.css`:** a single `@keyframes spin` (0°→360°) and a single `.spin` utility class (`animation: spin 1s linear infinite`).
2. **Convert plain loading spinners to `<Spinner>`:** every `<Loader className="spin">` / `<Loader2 className="spin">` becomes `<Spinner size={N} />` (carry the original `size`). Multi-class loaders keep their positioning/color classes but drop the `spin` token (the primitive self-animates): `<Loader className="status-icon processing spin">` → `<Spinner className="status-icon processing" />`; `<Loader className="spin upload-spinner">` → `<Spinner className="upload-spinner" />`.
3. **Keep semantic `<RefreshCw className="spin">`** (15 sites) as the refresh-arrows icon; it resolves to the new global `.spin` + `@keyframes spin`.
4. **Delete every local duplicate:** all 58 local `@keyframes spin` and every now-redundant local `.spin` rule. After a file's loaders convert, its local spin CSS is dead; any remaining `.spin` user (RefreshCw) falls through to the global rule.

The primitive keeps its scoped `ui-spin` keyframe unchanged. Net keyframe count: **59 → 2** (`spin` global + `ui-spin` scoped).

**Execution:** per-domain batches (as Stream A's codemod ran), each an independently reviewable commit, so the ~58-file sweep is not one giant diff.

**Out:**
- The other primitives (B2 Button, B3 Modal/Drawer, B4 Badge/EmptyState, B5 interaction rules).
- Changing the RefreshCw icon or any non-spinner animation.
- `pages/Admin/**`, `components/admin/**`, `components/campaigns/**`, auth — out of the whole effort's scope.
- The already-migrated scenes cluster (Phase 2) — only touched if it still contains a local `@keyframes spin` to remove.

## Edge cases & decisions

- **`sp-spin`** (2 uses, board domain): a differently-named spin class. The implementation inspects its definition; if it wraps a plain loader, convert to `<Spinner>` and remove the class, otherwise leave the icon and repoint its keyframe at the global one. Resolved per-occurrence during implementation, not by blind replace.
- **Non-1s durations** (~4 files use `0.6s`/`0.8s`/`2s`): converting to `<Spinner>` standardizes them to 1s. This is an accepted, deliberate consistency change to spin speed — flagged, not hidden. (User-approved.)
- **Wrapper shape:** `<Spinner>` wraps `Loader2` in an `inline-flex` span with `role="status"`. Loaders that sat inline in buttons/status rows render equivalently; the ARIA role is an accessibility gain. Where a converted loader had layout-critical classes, they are preserved via the `className` prop (which lands on the span).
- **Color:** `.ui-spinner` uses `color: currentColor`, so a converted spinner inherits its parent's text color — matching how the bare `<Loader>` icons rendered.

## Verification

- Per batch: `npm run build` green.
- End of stream (grep invariants):
  - `grep -rn "@keyframes spin" frontend/src` returns exactly one match (in `index.css`), plus the primitive's `ui-spin` in `Spinner.css`.
  - No plain-loader spinner JSX remains: `grep -rE "<Loader2?[^>]*className=\"[^\"]*\bspin\b" frontend/src --include=*.jsx` returns nothing.
  - Remaining `spin`-class JSX is only `<RefreshCw>` (and any deliberately-kept semantic icon), all resolving to the single global rule.
- No test runner exists in the repo; the live-drive path is browser-blocked and login-gated (same limitation documented for Streams A/C/D). Correctness rests on build + per-batch review + the grep invariants + the zero-visual-change argument (converted loaders render the same spinning icon; only the wrapper element and, for ~4 sites, the speed change).

## Success criteria

- `<Spinner>` is the only loading-spinner component; all plain `<Loader>`/`<Loader2>` spin sites converted.
- Exactly one global `@keyframes spin` (+ the primitive's `ui-spin`); all 58 local duplicates and dead `.spin` rules removed.
- Semantic `<RefreshCw>` spins preserved and still animate via the global rule.
- Build green; work landed as per-domain reviewed commits.
