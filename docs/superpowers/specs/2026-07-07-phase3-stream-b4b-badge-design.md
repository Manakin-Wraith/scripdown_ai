# Phase 3 · Stream B4b — Badge Adoption — Design

**Date:** 2026-07-07
**Status:** Approved (design)
**Parent:** `docs/audits/2026-07-06-ui-consistency-audit.md` (Phase 2/3 — shared primitives; C5 "Badges — ~30 classes; `.cdp-status-*` 6-color status system"). Stream B by primitive: B1 Spinner, B2 Button, B3a Modal, B3b Drawer, B4a EmptyState (all merged); **B4 Badge/EmptyState** — B4a EmptyState merged, **B4b Badge (this)** closes B4. Then B5 interaction rules.
**Goal:** Adopt the shared `<Badge>` primitive for the app's genuine status-state pills that map cleanly to its fixed variants, keeping copy verbatim and colors unchanged.

## Context

The audit flagged ~30 badge classes and a `.cdp-status-*` 6-color status system to consolidate onto a `<Badge>` primitive. On inspection, the convertible surface is small: the canonical `.cdp-status-*` system lives in `components/campaigns/` (an excluded area), the main in-scope status widget (`AnalysisStatusBadge`) is an interactive component rather than a pill, and the large majority of `*-badge` classes encode meaning through color/data that the primitive's fixed variants would flatten. B4b therefore takes a **tight, high-confidence** scope: convert only the pills that unambiguously map to a variant with no color or behavior change. The `<Badge>` primitive (`components/ui/Badge.jsx`) is already proven in `SceneList.jsx` (`<Badge variant="danger">OMIT</Badge>`).

## `<Badge>` primitive API (target)

Current: `Badge({ variant='neutral'|'primary'|'success'|'warning'|'danger'|'info', size='sm'|'md', dot=false, icon, children })` → `<span class="ui-badge ui-badge--{variant} ui-badge--{size}">` with an optional dot, an optional lucide `icon` (rendered at 11px for `sm`, 13px for `md`), and `children`.

**Enhancement (this stream):** add `...rest` passthrough so the primitive forwards arbitrary span attributes (`title`, `aria-*`, `onClick`, etc.) onto its `<span>`, with the computed `className` still winning. This is additive — existing `<Badge>` calls pass no extra props, so their output is unchanged — and it lets attributed pills (e.g. a badge with a tooltip) convert without losing behavior.

## Scope

**In:**
- **Enhance `<Badge>`** to forward `...rest` onto the span.
- **Convert 4 status-pill types** to `<Badge>`, copy verbatim, color unchanged:

| Bespoke class | File(s) | Mapping |
| --- | --- | --- |
| `status-badge kept` / `status-badge omitted` | `components/scenes/MultiMergeModal.jsx` ("KEEP"/"OMIT"), `components/scenes/SceneMergeModal.jsx` ("KEPT"/"OMITTED") | kept → `variant="success"`, omitted → `variant="danger"` |
| `shared-badge` | `components/reports/ReportBuilder.jsx` | green → `variant="success"`, `icon={Share2}`, text "Shared" |
| `merge-recommended-badge` | `components/scenes/ScriptSummary.jsx` | green → `variant="success"`, text "Recommended" |
| `strip-scheduled-badge` | `components/board/StripCard.jsx` | green → `variant="success"`, `icon={CalendarCheck}`, text `{label || 'Sched'}`, `title` preserved via `...rest` |

- **Prune** each converted bespoke class's CSS family (cascade-safe: grep before delete; leave classes still used by an un-converted sibling).

**Out (documented exclusions):**
- **Guarded** `timeline-*` day badges: `strip-day-badge`, `drawer-day-badge`, `sb-day-badge`, `story-day-badge`, `story-day-badge-sm` (Stream A guard — never touch `timeline-` rules).
- **Semantic two-state** badges: IE (`int-ext-badge`, `ie-badge`, `strip-ie-badge`, `drawer-ie-badge`), time-of-day (`time-badge` day/night), location type (`type-badge` interior/exterior).
- **Dynamic-data color** badges: `bd-dept-badge`, `dept-badge`, `role-badge`, `entity-badge`/`char-badge`/`loc-badge`, category chips (`badge-character`/`-prop`/`-fx`/`-vehicle`), inline-colored priority (`bd-priority-badge`, `priority-badge`).
- **Count / number chips:** `scene-count-badge`, `filter-count-badge`, `filter-badge`, `notification-badge`, `scene-number-badge`, `item-badge`, `note-badge`.
- **Interactive / non-pill:** `AnalysisStatusBadge` (clickable start/retry, progress bar, action icons, a `partial`/purple state with no variant home) — a component, not a pill; excluded.
- **Borderline decorative/positional** labels intentionally left (not clean status): `owner-badge` (gradient), `parse-method-badge`, `source-badge`, `preview-badge`, `sp-badge`, `diff-badge`, `revision-badge`.
- **Excluded areas / frozen WIP:** `components/admin/*`, `pages/Admin/*`, `components/campaigns/*` (incl. `.cdp-status-*`), auth pages (Login/Invite/Profile), and the frozen WIP components (SceneManager, DepartmentWorkspace, ShootingScriptPreview, CharacterProfile, SettingsPage, ScriptEditorPage).

## Conversion approach

Per pill:
- Replace the bespoke `<span className="…-badge …">…</span>` with `<Badge variant="…" [icon={…}] [title={…}]>text</Badge>`, keeping the text exactly and choosing the variant per the mapping table. Icons that were inline (`Share2 size={10}`, `CalendarCheck size={9}`) move to the `icon` prop (the primitive renders them at 11px for the default `sm` size — a minor, intended size normalization).
- Add `import { Badge } from '<rel>/ui';` (or extend an existing `../ui` import). Remove a now-unused lucide icon import only if the icon is truly unused after the move.
- For the conditional `status-badge kept/omitted`, keep the surrounding `keep… ? … : …` conditional; only the two `<span>`s become `<Badge>`s.
- Prune the bespoke CSS family (`.status-badge`+`.kept`/`.omitted`, `.shared-badge`, `.merge-recommended-badge`, `.strip-scheduled-badge`) once its class is unused; grep first for stray users.

## Execution

Three independently reviewable tasks:
1. **Enhance `<Badge>`** — add `...rest` passthrough to `components/ui/Badge.jsx`; verify existing `<Badge>` output is unchanged.
2. **scenes** — MultiMergeModal + SceneMergeModal (`status-badge`), ScriptSummary (`merge-recommended-badge`).
3. **reports + board** — ReportBuilder (`shared-badge`), StripCard (`strip-scheduled-badge`, using `icon` + `title`).

## Verification

- Per task: `npm run build` green.
- Task 1 invariant: existing `<Badge>` usages (e.g. `SceneList.jsx`) still render the same `ui-badge` classes; `...rest` is spread such that the computed `className` is not overridden.
- Conversion invariants (from `frontend/src`): each converted file imports `Badge` from the `ui` barrel and renders `<Badge`; the converted bespoke class no longer appears in that file's JSX; its CSS family is removed (or documented as still used by a sibling).
- No test runner exists; live-drive is login-gated (as in prior streams). Correctness rests on build + per-task review + the invariants + before/after that every badge's text is verbatim, its variant preserves the original color intent, and `strip-scheduled-badge`'s tooltip survives. Intended change: unified badge chrome (padding, radius, icon size) across the converted pills.

## Success criteria

- The 4 status-pill types render via `<Badge variant=…>` with verbatim text and equivalent color; the `strip-scheduled` tooltip is preserved.
- `<Badge>` forwards `...rest`; existing usages are unchanged.
- The converted bespoke CSS families are removed; no orphaned rules remain in the converted files.
- All excluded badge categories are untouched.
- Build green; work lands as three reviewed commits. B4 (EmptyState + Badge) is complete.
