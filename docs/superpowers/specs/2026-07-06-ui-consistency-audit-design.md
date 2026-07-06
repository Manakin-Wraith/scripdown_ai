# UI/UX Consistency Audit — Design

**Date:** 2026-07-06
**Status:** Approved
**Goal:** Audit the SlateOne frontend for UI/UX inconsistency and produce a findings report plus a phased fix roadmap, to inform upcoming UI/UX changes.

## Context

The frontend grew organically: 119 JSX components, 102 hand-written CSS files (~37k lines), a dark "Slate & Amber" theme via CSS variables in `src/index.css`, no Tailwind or component library. The user wants a **consistency cleanup** — not a redesign and not a tooling migration. The styling architecture stays plain CSS + variables; the fix direction is consolidation into shared components and enforced tokens.

## Scope

**In:** everything a paying user touches.

- `frontend/src/pages/` excluding `Admin/`
- `frontend/src/components/` domains: dashboard, editor, scenes, script(s), breakdown, schedule, reports, team, workspace, notes, metadata, revisions, characters, board, pdf, layout, common, shared, subscription, notifications, feedback
- Global styles: `src/index.css`, `src/styles/forms.css`, `src/App.css`
- UI parts of contexts: Toast, ConfirmDialog

**Out:** Admin pages, campaigns components (superuser-only), auth/onboarding pages, backend, any styling-tooling migration (Tailwind, CSS Modules, component libraries).

## Audit lenses

1. **Token compliance** — hardcoded colors/spacing/fonts/shadows bypassing the CSS variables; the duplicate `:root` block in `components/layout/Layout.css`.
2. **Component duplication** — inventory of every button, modal, drawer, table, card, badge, empty-state, loading-state, and error-state implementation, clustered into "should be one shared component" groups.
3. **Interaction patterns** — same job done differently across features: modal vs drawer, inline edit vs form, toast vs alert, divergent confirm/loading/error flows.
4. **Layout & navigation** — page skeleton map (headers, toolbars, spacing rhythm) and how each feature is reached; inconsistencies between pages.

## Method — three phases

### Phase 1: Static sweep
Parallel read-only agents, one per lens above. Findings must carry `file:line` references.

### Phase 2: Live visual pass
Browse **production** (`app.slateone.studio`) in the user's Chrome session (user logged in, script with breakdown data loaded). Screenshot core screens: dashboard, script editor, scene manager/detail, breakdown drawer, stripboard/schedule, reports, team drawer, settings/profile. Screenshots anchor findings code reading can't show and serve as before-references.

**Fallback:** if production can't be reached or isn't logged in, affected screens get static-only findings, flagged "not visually verified".

### Phase 3: Synthesis
Merge static + visual findings into one report. Every finding gets:
- **Severity:** high (users notice / erodes trust) · medium (visible inconsistency) · low (code hygiene)
- File references and, where applicable, a screenshot reference

## Deliverables

One document committed to the repo: `docs/audits/2026-07-06-ui-consistency-audit.md`, containing:

1. **Findings** by lens, severity-ranked, with `file:line` refs and screenshots.
2. **Phased fix roadmap**, each phase independently shippable:
   - **Phase 1 — Foundation:** consolidate tokens into `index.css`, remove duplicate `:root`, define canonical shared-component list.
   - **Phase 2 — Shared component build-out:** Button, Modal, Drawer, Table, EmptyState, etc. in `components/common/` or `components/shared/`.
   - **Phase 3 — Domain-by-domain adoption:** migrate feature areas to shared components, ordered by user visibility.

## Success criteria

- Findings are specific enough to act on without re-investigating (file-level, severity-ranked).
- The roadmap phases are independently shippable and ordered by user impact.
- No recommendation requires abandoning the plain-CSS + variables architecture.
