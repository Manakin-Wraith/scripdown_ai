# Phase 3 · Stream A — Color-Token Codemod — Design

**Date:** 2026-07-06
**Status:** Approved (design)
**Parent:** `docs/audits/2026-07-06-ui-consistency-audit.md` (Phase 3). Phase 3 is decomposed into streams A (this), B (primitive adoption), C (navigation/layout), D (dead-CSS deletion). This spec covers **Stream A only**.
**Goal:** Replace the ~1,900 raw color literals in the in-scope CSS with design tokens, unify legacy brand indigo/blue → amber, and tokenize the semantic timeline palette — via an allowlist codemod applied and reviewed per-domain, with zero unintended visual change.

## Scope

**In:** all `frontend/src/**/*.css` EXCEPT `pages/Admin/**`, `components/admin/**`, `components/campaigns/**`, the auth pages (`LoginPage`, `ConfirmEmailPage`, `AuthCallbackPage`, `ResetPasswordPage`, `InvitePage`, `PaymentSuccessPage`), and `components/ui/**` (already token-pure). `index.css` gains new semantic tokens.

**Out:** primitive adoption (Stream B), navigation/layout (C), dead-CSS deletion (D), JSX changes. This stream touches CSS values and `index.css` only — no component logic.

## The four literal categories

The codemod is an **allowlist**: a script applies an explicit `literal → replacement` table and touches only mapped literals. Every literal not in the table is left untouched and reported for manual triage. This is what protects semantic and ambiguous colors.

1. **Dead token-fallbacks** — `var(--token, #legacy)` where `--token` is defined in `index.css` (so the fallback never applies). Rewrite to `var(--token)`. **Zero visual change.** e.g. `var(--primary-500, #6366f1)` → `var(--primary-500)` (≈25 occurrences, mostly `ScriptSummary.css`, `board/BoardCanvas.css`, `board/BoardToolbar.css`).

2. **Neutral / status / amber literals** matching an existing token — the mechanical bulk. Includes the cool-gray→slate consolidation (accepted in the audit as a near-identical hue shift). Mapping table below.

3. **Legacy brand indigo/blue accents** used as the old primary (active-tab borders, accent icons, the scene-breakdown category-card icons/chips) → amber `--primary-*`. This is the intended visual unification. e.g. `BreakdownDrawer.css:1028` active-tab `#6366f1` → `var(--primary-500)`; blue category-card icons in `SceneList.css`/`SceneManager.css`/`SceneDetail.css`.

4. **Semantic palette — preserved, then tokenized (not amberified).** The timeline codes are a deliberate color system. Define tokens in `index.css` and repoint the (duplicated) literals at them:
   - `--timeline-dream: #3b82f6` (+ existing `.15` bg)
   - `--timeline-fantasy: #ec4899`
   - `--timeline-flashback: #a855f7`
   - `--timeline-montage` → **reuse** `--primary-500` (`#f59e0b`, already identical)
   - `--timeline-title-card` → **reuse** `--gray-400` (`#94a3b8`, already identical)
   These appear duplicated in `board/StripCard.css` and `board/StripDetailDrawer.css` (and any SceneList/SceneDetail timeline pills); all point at the tokens. Revision colors: the industry revision palette appears to be applied via JS/inline, not a CSS class set — the implementation will confirm; if a CSS revision-color set exists it is tokenized the same way, otherwise it is out of this stream.

## Ambiguity guard (do NOT auto-map)

Color-**named** modifier classes that form a deliberate multi-color set — e.g. `.stat-icon-wrapper.blue` / `.indigo` on the Character/Location dashboards (`Dashboard.css`), with distinct per-variant background tints — are NOT the breakdown "category cards" and must not be blindly amberified (a class named `.blue` rendering amber is a bug). These are left untouched by the codemod and reported; a human/reviewer decides per case (tokenize as a semantic set, or unify) in a follow-up, out of this stream's automatic path.

## Mapping table (canonical — the plan enumerates the full list)

Neutrals (slate, exact + cool-gray consolidation):
`#f8fafc→--gray-50` · `#f1f5f9`,`#f3f4f6→--gray-100` · `#e2e8f0`,`#e5e7eb→--gray-200` · `#cbd5e1→--gray-300` · `#94a3b8`,`#9ca3af→--gray-400` · `#64748b`,`#6b7280→--gray-500` · `#475569`,`#4b5563→--gray-600` · `#334155`,`#374151→--gray-700` · `#1e293b`,`#1f2937→--gray-800` · `#0f172a`,`#111827→--gray-900` · `#020617→--gray-950`

Brand (amber) + legacy indigo→amber:
`#fffbeb→--primary-50` · `#fef3c7→--primary-100` · `#fde68a→--primary-200` · `#fcd34d→--primary-300` · `#fbbf24→--primary-400` · `#f59e0b→--primary-500` · `#d97706→--primary-600` · `#b45309→--primary-700` · legacy `#6366f1`,`#4f46e5→--primary-500/600` · `#818cf8→--primary-400` · `#4338ca→--primary-700` · brand blues `#3b82f6`/`#60a5fa` **only where they are accent usage** → `--primary-500`/`--primary-400` (NOT where they are `.timeline-dream`, which maps to `--timeline-dream`)

Status + alpha (exact rgba matches):
`#22c55e→--success` · `#ef4444→--danger` · `#f59e0b→--warning` (context-dependent vs --primary-500) · `rgba(34,197,94,0.1)→--success-bg` · `rgba(239,68,68,0.1)→--danger-bg` · `rgba(245,158,11,0.1)→--primary-alpha-10` · `rgba(245,158,11,0.15)→--primary-alpha-15` · `rgba(245,158,11,0.05/0.2/0.3/0.4)→--primary-alpha-05/20/30/40`

Context-sensitive entries (`#f59e0b` = `--primary-500` vs `--warning`; blue = accent vs `--timeline-dream`) are resolved per-occurrence in the plan, not by a naive global swap — another reason the table is applied as a reviewed allowlist, not sed-all.

## Codemod mechanics

- A Node script (`scripts/ui/color-codemod.mjs`, committed) holds the mapping table and, given a list of files, replaces only exact mapped literals (case-insensitive hex; normalized rgba whitespace), writing changes in place and printing a per-file report of (a) replacements made and (b) **unmapped literals left behind**.
- Run it **per domain** (scenes, breakdown, board, schedule, reports, team, notes, revisions, subscription, workspace, layout, common, shared, metadata, characters), committing each domain separately so each batch is independently reviewable and revertible.
- The script never deletes rules and never touches JSX. Rules destined for Stream D deletion may still be converted (harmless); no effort is spent avoiding them.

## Verification

- Per domain: `npm run build` green; the script's unmapped-literal report reviewed (should contain only semantic/ambiguous/out-of-palette values, never a plain gray/amber that should have mapped).
- End of stream: re-run the in-scope literal count — remaining literals are only the intentionally-preserved semantic/ambiguous set, and every occurrence of that set is accounted for.
- **Live-drive limitation:** the browser tooling can't load localhost and the app is login-gated, so visual confirmation is by careful before/after token equivalence (cases 1–2 are visually identical; case 3 indigo→amber and case-4 tokenization are the only intended visual deltas) plus per-domain review, not a live click-through. Stated, not hidden.
- No test runner exists; this stream adds none.

## Success criteria

- In-scope CSS contains no raw color literal except the explicitly-preserved semantic/ambiguous set.
- New `--timeline-*` tokens defined once in `index.css`; timeline pills reference them (duplication gone).
- Legacy indigo/blue brand accents render amber; no class named for a color renders a different color.
- Build green; each domain landed as its own reviewed commit.
