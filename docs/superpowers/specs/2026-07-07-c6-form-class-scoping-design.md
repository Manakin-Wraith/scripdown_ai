# C6 — Form-Class Scoping — Design

**Date:** 2026-07-07
**Status:** Approved (design)
**Parent:** `docs/audits/2026-07-06-ui-consistency-audit.md` (Phase 2.5, C6 — "promote `.form-group`/`.form-row`/`.form-actions` into `styles/forms.css`; delete the 9 local copies"). Surfaced by the full backlog check (2026-07-07) as the one partial Phase-2 item.
**Goal:** Stop the global `.form-group`/`.form-row`/`.form-actions` base rules from leaking across components by scoping each file's rules under that component's existing container — removing a latent CSS-cascade fragility without a shared canonical class.

## Context

The backlog check found the local `.form-*` definitions are **divergent per-domain variants, not duplicates**: `.form-group` base is `margin-bottom: 1rem` (SceneModals), `1.25rem` (SceneEditor), `20px` (FeedbackDrawer), `1.5rem` (InviteModal), and `display:flex; flex-direction:column; gap:0.5rem` (RevisionImportWizard, ProfilePage) — two different box models. Because all component CSS is bundled globally and every bare `.form-group { … }` has identical specificity (0,1,0), each form currently renders with whichever file's base rule lands **last in the Vite bundle**, not its own. This is a latent bug: a form may be styled by a foreign component's rule.

The audit's literal C6 (one shared canonical class, delete locals) would **visually unify all forms** — a design migration, not a safe consolidation. This spec takes the **scoping** approach instead: isolate each file's rules under its own container so every form renders per its **own authored CSS**. A shared `forms.css` canonical class is explicitly **not** created here (true unification is deferred).

Because scoping restores each form to its authored styling — which may differ from the currently-leaked rendering — the change **requires visual verification**. The forms are login-gated; the user will verify on a Vercel preview / production.

## Scope

Six CSS files, one 1-line JSX change. For each file, prefix its `.form-group`, `.form-group label`, `.form-group input`/`select`/`textarea` (and their `:focus`/`:disabled`/`::placeholder` variants), `.form-row`, `.form-row .form-group`, `.form-actions`, and any responsive `@media` variants of these, with the component's anchor selector:

| File | Anchor prefix | JSX change |
| --- | --- | --- |
| `components/scenes/SceneEditor.css` | `.scene-editor` (root `<div className="scene-editor">`) | none |
| `components/feedback/FeedbackDrawer.css` | `.feedback-drawer` (root; wraps `.feedback-form`) | none |
| `pages/ProfilePage.css` | `.profile-card` (wraps the `<form>`) | none |
| `components/revisions/RevisionImportWizard.css` | `.revision-wizard` (root) | none |
| `components/scenes/SceneModals.css` | `#add-scene-form` (existing id; **AddSceneModal is the only one of the 4 SceneModals consumers that renders `.form-group`/`.form-row`** — SceneSplit/SceneMerge/MultiMerge render neither) | none |
| `components/team/InviteModal.css` | `.invite-form` | **add `className="invite-form"`** to InviteModal's `<form onSubmit={handleSubmit}>` (the non-locked branch) |

Scoped selectors gain specificity (`.scene-editor .form-group` = 0,2,0; `#add-scene-form .form-group` = 1,1,0), so each beats any residual bare `.form-group` (0,1,0) global — guaranteeing each form renders per its own file.

**Out:**
- `styles/forms.css` — **not touched**; no canonical `.form-*` class added (true unification deferred).
- `DepartmentNotesSection.css` — already scopes `.add-note-form .form-row`; left as-is.
- Excluded areas (admin/campaigns/auth pages) and frozen WIP — untouched.
- No change to any form's authored values (margins, label/input styling) — only the selector prefix. Any before/after visual delta is a form reverting from a leaked foreign rule to its own authored rule; the user verifies this is acceptable.

## Verification

- `npm run build` from `frontend/` green.
- Grep invariants (from `frontend/src`): in each of the 6 files, no bare `.form-group {` / `.form-row {` / `.form-actions {` remains at column 0 (every occurrence is prefixed by its anchor). `grep -n "^\.form-group\|^\.form-row\|^\.form-actions\|^  \.form-" <file>` — the base selectors now start with the anchor.
- InviteModal's `<form>` carries `className="invite-form"`.
- **Visual verification (binding, user-performed):** on a Vercel preview or production, the six forms render correctly and unchanged in intent — **Add Scene** modal, **Scene Editor**, **Feedback** popover (TopBar button), **Invite** modal (Team drawer), **Revision Import** wizard, **Profile** page. Any form that shifts is a form that was previously mis-styled by a leaked rule; confirm the scoped (authored) rendering is correct.
- No test runner; correctness rests on build + grep + the user's visual pass.

## Execution

Lightweight — in-session, a single build-verified, reviewed commit on a short branch (`chore/c6-form-scoping`). Before merging to `main`/production, push the branch for a **Vercel preview URL** so the user can verify the six forms; merge only after the visual pass.

## Success criteria

- The six files' `.form-group`/`.form-row`/`.form-actions` rules are scoped under their component anchors; no bare global base rules remain in them.
- Each in-scope form renders per its own authored CSS (cross-component leakage eliminated), confirmed by the user's visual pass.
- `styles/forms.css` untouched; true unification remains a documented follow-up.
- Build green; one reviewed commit.
