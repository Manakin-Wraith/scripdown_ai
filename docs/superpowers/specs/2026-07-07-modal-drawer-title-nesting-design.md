# Modal/Drawer Title Nesting Fix — Design

**Date:** 2026-07-07
**Status:** Approved (design)
**Parent:** `docs/audits/2026-07-06-ui-consistency-audit.md` (Phase 2/3 — shared primitives). Deferred twice — from B3a (InviteModal) and B3b (TeamDrawer/StripDetailDrawer) — as "block-in-inline title nesting; renders fine; candidate for a later polish pass." This is that pass.
**Goal:** Eliminate invalid block-in-inline HTML in the `<Modal>` and `<Drawer>` title regions with a single primitive-level change, no visual change, no caller edits.

## Context

Both primitives wrap the `title` prop in an **inline `<span>`**:
- `components/ui/Modal.jsx`: `<span className="ui-modal-title">{title}</span>`
- `components/ui/Drawer.jsx`: `<span className="ui-drawer-title">{title}</span>`

`title` is typed `React.ReactNode`, and several callers pass **block** content into it, producing invalid block-in-inline markup (browsers render it, but it is not valid HTML):
- `components/team/InviteModal.jsx` (two `<Modal>` instances — locked + unlocked branches): `title={<div className="header-content"><Users/><div><h2>Invite Team Member</h2><p className="script-name">…</p></div></div>}` — `<div>`/`<h2>`/`<p>` inside a `<span>`.
- `components/board/StripDetailDrawer.jsx`: `title={<div className="sdd-header-content"><div className="drawer-title-row">…</div><div className="drawer-setting">…</div><div className="drawer-meta-row">…</div></div>}` — multiple `<div>`s inside a `<span>`.

Other callers pass inline-only content and are already valid: icon-fragment titles (`AddSceneModal`, `SceneSplitModal`, `SceneMergeModal`, `MultiMergeModal` — `<><Icon/> text</>`), and span-wrapped titles (`ShareModal` `<span className="share-modal-title">`, `TeamDrawer` `<span className="team-drawer-title">` — valid span-in-span). String titles (`SceneEditor`, `FilteredSceneList`, `UpgradeModal`) are trivially valid.

## Fix

Change the two title wrapper elements from `<span>` to `<div>`:
- `Modal.jsx`: `<span className="ui-modal-title">{title}</span>` → `<div className="ui-modal-title">{title}</div>`
- `Drawer.jsx`: `<span className="ui-drawer-title">{title}</span>` → `<div className="ui-drawer-title">{title}</div>`

A `<div>` legally contains both inline and block content, so **every caller becomes valid at once** — the block-content callers (InviteModal ×2, StripDetailDrawer) stop nesting block-in-inline, the span-wrapped callers become valid span-in-div, and the inline-fragment callers are unaffected.

## Why this is zero-visual-change

- `.ui-modal-title` and `.ui-drawer-title` set **no `display`** — only font size/weight/color. The wrapper's default display (span=inline vs div=block) is irrelevant because in both headers the title sits inside a flex container (`.ui-modal-header` is `display:flex`; `.ui-drawer-title` is a child of `.ui-drawer-title-group` which is `display:flex; flex-direction:column`), so the title is a **flex item** regardless of its own tag.
- Inline children of the title (icon `<svg>` + text in the fragment callers) flow identically inside a block `<div>` as inside an inline `<span>` (both establish an inline formatting context for their inline children).
- No CSS selector is element-qualified on the tag: `grep` confirms there is no `span.ui-modal-title` / `span.ui-drawer-title` / `span.ui-drawer-subtitle` selector anywhere. All rules are class-only, so the tag swap changes no styling.

## Scope

**In:** `components/ui/Modal.jsx`, `components/ui/Drawer.jsx` — one line each.

**Out:**
- All caller files — untouched (the primitive change covers them by construction).
- Drawer's `subtitle` wrapper stays `<span className="ui-drawer-subtitle">` — subtitle content is always inline text (e.g. `TeamDrawer` passes the `scriptTitle` string); no violation there.
- No CSS changes; no copy changes.

## Verification

- `npm run build` from `frontend/` succeeds.
- Invariants (from `frontend/src`):
  - `grep -n "ui-modal-title" components/ui/Modal.jsx` shows `<div className="ui-modal-title">` (not `<span`).
  - `grep -n "ui-drawer-title\"" components/ui/Drawer.jsx` shows `<div className="ui-drawer-title">` (not `<span`).
  - `grep -rn "<span className=\"ui-modal-title\|<span className=\"ui-drawer-title\"" components/ui` returns nothing.
- No test runner; live-drive login-gated. Visual parity rests on the CSS reasoning above (no `display` on the title classes; class-only selectors). Correctness rests on build + review + before/after that Modal and Drawer titles render identically for a string title, an icon-fragment title, and a block-content title (InviteModal / StripDetailDrawer).

## Execution

Lightweight — in-session, single build-verified, reviewed commit on a short branch. No multi-task SDD.

## Success criteria

- `<Modal>`/`<Drawer>` title wrappers are `<div>`; no `<span className="ui-modal-title">`/`<span className="ui-drawer-title">` remains.
- No caller edited; no CSS edited; build green.
- Titles render identically across string / icon-fragment / block-content cases (no visual regression).
