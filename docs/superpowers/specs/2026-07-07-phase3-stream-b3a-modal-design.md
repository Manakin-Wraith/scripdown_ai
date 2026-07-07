# Phase 3 · Stream B3a — Modal Adoption — Design

**Date:** 2026-07-07
**Status:** Approved (design)
**Parent:** `docs/audits/2026-07-06-ui-consistency-audit.md` (Phase 2/3 — shared primitives). Stream B is decomposed by primitive: B1 Spinner (merged), B2 Button (merged), **B3 Modal/Drawer (this)**, B4 Badge/EmptyState, B5 interaction rules. Streams A, C, D, B1, B2 are merged.
**Goal:** Adopt the `<Modal>` primitive for the app's live bespoke modal components, and delete the dead modal components discovered during scoping. Drawer adoption is deferred to a separate sub-stream (B3b).

## Context

B3 targets the overlay primitives (`components/ui/Modal.jsx`, `components/ui/Drawer.jsx`, backed by `components/ui/useOverlay.js`). These are the most logic-entangled primitives — portal to `document.body`, Escape-to-close, body scroll-lock, and focus-restore all live in `useOverlay`. Because of that entanglement, B3 splits into two sub-streams:

- **B3a — Modal adoption (this spec).** The `<Modal>` primitive is well-proven: it already backs the scenes-cluster modals (AddSceneModal, MultiMergeModal, SceneMergeModal, SceneSplitModal, SceneEditor) and `ConfirmDialogContext`. Converting the remaining bespoke modals is low-risk.
- **B3b — Drawer adoption (deferred).** The `<Drawer>` primitive is not yet used anywhere (unproven). The 5 bespoke drawers (StripDetailDrawer, BreakdownDrawer, FeedbackDrawer, NoteDrawer, TeamDrawer) convert in B3b. B3a runs first, in part because `TeamDrawer` renders `InviteModal` — converting the modal first keeps the two changes independent.

### Reachability finding (drives scope)

A reference sweep of the 7 in-scope `*Modal.jsx` components found **4 are dead code** — imported and rendered by nobody:

| Dead component | Files |
| --- | --- |
| `components/common/AnalysisProgressModal.jsx` | + `.css` |
| `components/reports/ExportOptionsModal.jsx` | + `.css` |
| `components/scripts/LockScriptModal.jsx` | + `.css` |
| `components/credits/CreditPurchaseModal.jsx` | + `.css`, re-exported by `components/credits/index.js` |

`CreditPurchaseModal` belongs to the deprecated credit system. Its barrel (`components/credits/index.js`) is imported nowhere, and the barrel's only sibling, `CreditBalance` (`.jsx` + `.css`), is also unreferenced — so the **entire `components/credits/` directory is dead**.

The **3 live modals** are:

| Live modal | Rendered by |
| --- | --- |
| `components/reports/ShareModal.jsx` | `ReportBuilder.jsx` (conditionally mounted) |
| `components/subscription/UpgradeModal.jsx` | `SceneViewer`, `SubscriptionBanner`, `SubscriptionGate`, `ScriptUpload`, `InviteModal` (5 renderers) |
| `components/team/InviteModal.jsx` | `TeamDrawer.jsx` |

## `<Modal>` primitive API (target)

`Modal({ isOpen, onClose, title, size='md', footer, showClose=true, closeOnOverlay=true, closeOnEscape=true, overlayClassName='', children })` → `createPortal` to `document.body`; renders `.ui-modal-overlay` (click-to-close when `closeOnOverlay`), a `.ui-modal--{size}` dialog (`sm`/`md`/`lg`) with an optional `.ui-modal-header` (title + X close), a `.ui-modal-body` for `children`, and an optional `.ui-modal-footer` for `footer`. `useOverlay` supplies Escape-to-close, scroll-lock, and focus-restore. `title` accepts a ReactNode, so rich headers (icon + text + subtitle) pass through as a node.

## Scope

**In:**
- **Convert the 3 live modals** to `<Modal>`: `ShareModal`, `UpgradeModal`, `InviteModal`.
- **Delete the dead modal code:** `AnalysisProgressModal` (`.jsx`+`.css`), `ExportOptionsModal` (`.jsx`+`.css`), `LockScriptModal` (`.jsx`+`.css`), and the entire `components/credits/` directory (`CreditPurchaseModal.jsx`+`.css`, `CreditBalance.jsx`+`.css`, `index.js`).

**Out:**
- The 5 bespoke drawers — deferred to **B3b**.
- The scenes-cluster modals and `ConfirmDialogContext` — already on `<Modal>`.
- Other primitives (B4 Badge/EmptyState, B5 interaction rules). In particular, `window.confirm` inside `ShareModal.handleRevokeLink` is **left as-is** — routing native confirms through `useConfirmDialog` is B5's job.
- Bespoke non-generic CTAs inside these modals (e.g. `.upgrade-btn-primary/-secondary` gradient buttons) — kept as `children`; not `<Button>` targets (per B2 scope).
- All excluded areas (admin, campaigns, auth, WIP components).

## Conversion approach (per modal)

The primitive supplies the overlay chrome (backdrop, positioning, Escape, scroll-lock, focus-restore, X close). Each modal's **content** moves into `children`; its bespoke overlay/backdrop/card-wrapper/header-chrome CSS is pruned; its **content-specific** CSS is kept.

### ShareModal (`components/reports/ShareModal.jsx`)
- Currently `({ report, onClose, onUpdate })` with no `isOpen` prop — `ReportBuilder` conditionally mounts it (`{shareModalReport && <ShareModal … />}`). Keep that mount gate; inside ShareModal wrap the content in `<Modal isOpen onClose={onClose} title={<><Link2 size={20}/> Share Report</>} size="sm">`. `isOpen` is always `true` while mounted; overlay-click/Escape/X all call `onClose`, which unmounts via the parent. `ReportBuilder` is otherwise unchanged.
- Move `.share-modal-content` markup into `children`. No `footer` (actions are inline in the content).
- Prune from `ShareModal.css`: `.share-modal-overlay`, `.share-modal`, `.share-modal-header`, `.close-btn`. Keep: `.share-modal-content`, `.report-info`, `.share-link-*`, `.link-meta`, `.share-actions`, `.action-btn`, `.revoke-btn`, `.create-*`, `.expiry-selector`, `.share-note`, etc.

### UpgradeModal (`components/subscription/UpgradeModal.jsx`)
- Already `({ isOpen, onClose, … })` returning `null` when `!isOpen` — pass both straight to `<Modal isOpen={isOpen} onClose={onClose} showClose size="sm">` and drop the manual `if (!isOpen) return null` (the primitive handles it). This modal has no title bar — omit `title` so the header renders just the X (matching today's top-right close button).
- Move the icon header / urgency / features / pricing / actions / footer markup into `children`. The `.upgrade-btn-primary`/`.upgrade-btn-secondary` bespoke CTAs stay as-is inside `children`.
- Prune from `UpgradeModal.css`: `.upgrade-modal-overlay`, `.upgrade-modal` (card wrapper), `.upgrade-modal-close`. Keep the content styles (`.upgrade-modal-header`, `-icon`, `-urgency`, `-features`, `-pricing`, `-actions`, `-footer`, `.upgrade-btn-*`).

### InviteModal (`components/team/InviteModal.jsx`)
- Already `({ isOpen, onClose, scriptId, scriptTitle })` returning `null` when `!isOpen`. Both the locked-state branch and the form branch wrap their content in `<Modal isOpen={isOpen} onClose={onClose} title={<rich header: Users icon + "Invite Team Member" + scriptTitle subtitle>} size="md">`. Drop the manual `if (!isOpen) return null`.
- The nested `<UpgradeModal>` (locked branch, gated by `showUpgradeModal`) stays — once UpgradeModal is itself a `<Modal>`, this is a Modal-over-Modal, both portaled to `document.body`; the stacking matches today's stacked overlays. No regression.
- InviteModal is rendered *inside* `TeamDrawer` (a still-bespoke drawer in B3b). Portaling to `document.body` moves it out of the drawer's DOM subtree — an improvement for z-index/stacking, and independent of B3b.
- Move both branches' body markup into `children`; keep the `<form>`, submit button, success view, and `<Button>` actions as-is. No `footer` (actions are inline).
- Prune from `InviteModal.css`: `.invite-modal-overlay`, `.invite-modal`, `.invite-modal-header`, `.header-content`, `.close-btn`. Keep the body/content styles (`.invite-modal-body`, `.invite-locked`, `.locked-*`, `.form-group`, `.department-*`, `.role-*`, `.submit-btn`, `.invite-success`, `.invite-link-box`, etc.).

## Execution

Four independently reviewable tasks:

1. **Delete dead modal code** — remove the 3 dead standalone modals (`.jsx`+`.css`) and the whole `components/credits/` dir. Verified zero references. (Quick, de-risks: e.g. removes `ExportOptionsModal`, so any prior B2 button work there is moot.)
2. **Convert ShareModal** to `<Modal>` + prune its CSS.
3. **Convert UpgradeModal** to `<Modal>` + prune its CSS.
4. **Convert InviteModal** to `<Modal>` + prune its CSS.

Each conversion is one commit. Deletion is one commit.

## Verification

- Per task: `npm run build` green.
- Deletion invariant (from `frontend/src`): `grep -rn "AnalysisProgressModal\|ExportOptionsModal\|LockScriptModal\|CreditPurchaseModal\|CreditBalance\|components/credits" --include="*.jsx" --include="*.js" .` returns nothing.
- Conversion invariants: the 3 live modals import `Modal` from `../ui` and render exactly one `<Modal>` (InviteModal renders two — one per branch — plus the nested `<UpgradeModal>`); their bespoke `.*-modal-overlay` classes no longer appear in the pruned CSS.
- Behavior preserved: open, close via overlay-click / Escape / X, form submit, nested content, the UpgradeModal-inside-InviteModal locked path. Escape + scroll-lock + focus-restore are *newly gained* (the bespoke modals lacked them) — an intended improvement, not a regression.
- No test runner exists; live-drive is blocked/login-gated (as in prior streams). Correctness rests on build + per-task review + the invariants + careful before/after of each modal's open/close wiring.

## Success criteria

- The 3 live modals render via `<Modal>`; backdrop, Escape, scroll-lock, focus-restore, and the X close are unified across them.
- The 4 dead modals and the dead `components/credits/` directory are removed; the deletion invariant passes.
- Build green; work lands as one deletion commit + three conversion commits.
- Drawer adoption (B3b) is cleanly separable and unblocked.
