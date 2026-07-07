# Phase 3 · Stream B5 — Interaction Rules — Design

**Date:** 2026-07-07
**Status:** Approved (design)
**Parent:** `docs/audits/2026-07-06-ui-consistency-audit.md` (Lens 3 — Interaction patterns; I1 "all confirms via `useConfirmDialog`; all transient feedback via `useToast`; kill `alert()`"). Final sub-stream of Phase 3 Stream B (B1 Spinner, B2 Button, B3a Modal, B3b Drawer, B4a EmptyState, B4b Badge — all merged). B5 closes Stream B.
**Goal:** Route every destructive confirmation through the existing `useConfirmDialog` context and every transient failure through `useToast`, eliminating native `window.confirm`/`alert()` and the one remaining bespoke confirm-modal pattern (TeamDrawer), so the app has a single themed confirm system and a single feedback channel.

## Context

The audit's Lens 3 found destructive actions confirmed **three different ways** — native `window.confirm`, the shared `useConfirmDialog` context, and TeamDrawer's hand-rolled `.confirm-overlay`/`.confirm-modal` — and user feedback ranging from toasts to `alert()` to silence. The infrastructure to unify already exists and is proven in the app: `useConfirmDialog` (`context/ConfirmDialogContext.jsx`, `confirm({title, message, variant, confirmText, cancelText}) → Promise<boolean>`, already used by `ScriptLibrary.jsx` and `SceneEditor.jsx`) and `useToast` (`context/ToastContext.jsx`, `toast.success(title, message)` / `toast.error(title, message)`, used across reports/schedule). Both providers wrap the app. B5 migrates the remaining in-scope offenders onto them.

## Confirm / Toast context APIs (target)

- `const { confirm } = useConfirmDialog();` → `const ok = await confirm({ title, message, variant: 'danger'|'warning'|'info', confirmText?, cancelText? }); if (!ok) return;`. Variant supplies icon + accent + a default confirm label (`danger`→"Delete", `warning`→"Continue", `info`→"Confirm"); pass `confirmText` to override. `message` is a single string.
- `const toast = useToast();` → `toast.error(title, message)` / `toast.success(title, message)`.

## Scope

**In — 3 groups:**

### A. Native `window.confirm` → `useConfirmDialog` (5 sites)

| File:line | Action | `confirm({...})` |
| --- | --- | --- |
| `components/schedule/ShootingSchedulePage.jsx:115` | delete schedule | `variant:'danger'`, `title:'Delete Schedule?'`, `message:` `` `"${sched?.name || 'This schedule'}" and all its shooting days will be permanently deleted.` `` |
| `components/schedule/DayColumn.jsx:55` | delete day | `variant:'danger'`, `title:'Delete Day?'`, `message:` `` `Day ${day.day_number} will be deleted and all its scenes unscheduled.` `` |
| `components/notes/DepartmentNotesSection.jsx:140` | delete note | `variant:'danger'`, `title:'Delete Note?'`, `message:'This note will be permanently deleted.'` |
| `components/reports/ReportBuilder.jsx:179` | delete report | `variant:'danger'`, `title:'Delete Report?'`, `message:'This report will be permanently deleted.'` |
| `components/reports/ShareModal.jsx:52` | revoke share link | `variant:'warning'`, `confirmText:'Revoke'`, `title:'Revoke Share Link?'`, `message:'Anyone with the link will lose access.'` |

Each replaces `if (!window.confirm(...)) return;` with `const ok = await confirm({...}); if (!ok) return;`. The surrounding `try/catch` (and existing toasts, where present) is unchanged. `ShootingSchedulePage`, `ReportBuilder`, `ShareModal` already import from context (they use `useToast`); `DayColumn` and `DepartmentNotesSection` gain `import { useConfirmDialog } from '../../context/ConfirmDialogContext';` + `const { confirm } = useConfirmDialog();`.

### B. Native `alert()` → `useToast` (1 site)

`components/scenes/ScriptSummary.jsx:136` — `alert('Merge failed: ' + (err.response?.data?.error || err.message))` → `toast.error('Merge Failed', err.response?.data?.error || err.message)`. Adds `import { useToast } from '../../context/ToastContext';` + `const toast = useToast();`.

### C. TeamDrawer bespoke confirms → `useConfirmDialog` (2 modals)

`components/team/TeamDrawer.jsx` hand-rolls two confirm modals (Remove member, Revoke invite) as `.confirm-overlay`/`.confirm-modal` markup driven by `removeConfirm`/`revokeConfirm` state, with an in-dialog `<Spinner>` gated on `actionLoading === id`. Consolidate onto `useConfirmDialog`:

- Add `import { useConfirmDialog } from '../../context/ConfirmDialogContext';` + `const { confirm } = useConfirmDialog();`.
- **Remove-member trigger** (currently `onClick={() => setRemoveConfirm({id, name})}`) → `onClick={() => handleRemoveClick(member)}` where:
  ```js
  const handleRemoveClick = async (member) => {
      const ok = await confirm({
          title: 'Remove Team Member?',
          message: `${member.name} will lose access to this script. Their notes will remain.`,
          variant: 'danger',
          confirmText: 'Remove'
      });
      if (!ok) return;
      await handleRemoveMember(member.id, member.name);
  };
  ```
- **Revoke-invite trigger** (`onClick={() => setRevokeConfirm({id, email})}`) → `onClick={() => handleRevokeClick(invite)}` where:
  ```js
  const handleRevokeClick = async (invite) => {
      const ok = await confirm({
          title: 'Revoke Invite?',
          message: `The invite to ${invite.email} will no longer work.`,
          variant: 'warning',
          confirmText: 'Revoke'
      });
      if (!ok) return;
      await handleRevokeInvite(invite.id, invite.email);
  };
  ```
- **Delete** the two `{removeConfirm && (...)}` / `{revokeConfirm && (...)}` JSX modal blocks, the `removeConfirm`/`revokeConfirm`/`actionLoading` `useState` declarations, and the `setActionLoading(...)` / `setRemoveConfirm(null)` / `setRevokeConfirm(null)` lines inside `handleRemoveMember`/`handleRevokeInvite` (those handlers keep their fetch + toast + `console.error`, losing only the removed-state bookkeeping).
- **Behavior change (intended):** the dialog now closes immediately on confirm; the existing `toast.success`/`toast.error` in `handleRemoveMember`/`handleRevokeInvite` reports the outcome — identical to how the other five sites behave. The in-dialog spinner is dropped.
- **Prune CSS:** remove TeamDrawer.css's own `.confirm-overlay`/`.confirm-modal`/`.confirm-icon`/`.confirm-name`/`.confirm-warning`/`.confirm-actions`/`.confirm-cancel`/`.confirm-delete` rule family (grep-confirm no remaining TeamDrawer refs). BreakdownDrawer.css, `context/ConfirmDialog.css`, and admin/FeedbackDetailModal.css keep their **own** scoped copies — do not touch them.
- **Imports:** remove `Spinner` from the `../ui` import **only if** it is no longer used elsewhere in TeamDrawer (verify — the drawer's loading state may still use it). Remove `UserX`/`Trash2` lucide imports only if their sole remaining use was the deleted modals (the trigger buttons still use `UserX`/`LinkIcon`, so `UserX` stays; verify `Trash2`).

**Out (documented exclusions):**
- **Excluded areas** (native confirms left untouched): `components/campaigns/TemplateEditorModal.jsx`, `components/campaigns/CampaignDetailPanel.jsx` (×2), `pages/Admin/EmailCampaignsPage.jsx` (already uses `confirm()`), and all `components/admin/*` / `pages/Admin/*` / `components/campaigns/*`, auth pages, and the frozen WIP components (SceneManager, DepartmentWorkspace, ShootingScriptPreview, CharacterProfile, SettingsPage, ScriptEditorPage).
- **Swallowed-error feedback:** B5 does **not** add new failure toasts to `DayColumn` (`console.error` only) or `DepartmentNotesSection` (already sets an inline `error` banner). Migrating their confirm is in scope; wiring new toast feedback is a separable "swallowed errors" concern deferred to a later pass.
- **Carried polish deferred:** BoardCanvas emoji-icon empty states (→ EmptyState, a B4 concern) and the Modal/Drawer title block-in-inline nesting (InviteModal `<div>` / TeamDrawer inside the primitive's `<span>`) — both deferred, tracked in the ledger.

## Conversion approach

Per confirm site: swap the native guard for `const ok = await confirm({...}); if (!ok) return;`, keeping the handler `async` (all five are already `async`) and the try/catch intact. Per alert site: swap for `toast.error(title, message)`. Add the context hook import + call where the file lacks it. For TeamDrawer, additionally delete the bespoke state/JSX/CSS as above. Copy is folded into the single `message` string where the bespoke modal previously used a separate name/email line; wording is preserved in substance (this is a system consolidation, not a copy-freeze).

## Execution

Three independently reviewable tasks:
1. **Native `window.confirm` → `useConfirmDialog`** — the 5 sites (schedule×2, notes, reports×2). Uniform mechanical swap; two files gain the import.
2. **`alert()` → `useToast`** — `ScriptSummary.jsx` (adds `useToast`).
3. **TeamDrawer consolidation** — triggers → `await confirm(...)` handlers, delete bespoke state/JSX, prune `.confirm-*` CSS.

## Verification

- Per task: `npm run build` green.
- Invariants (from `frontend/src`):
  - Task 1: `grep -n "window.confirm" components/schedule/ShootingSchedulePage.jsx components/schedule/DayColumn.jsx components/notes/DepartmentNotesSection.jsx components/reports/ReportBuilder.jsx components/reports/ShareModal.jsx` → nothing. Each of the five imports and calls `confirm` from `useConfirmDialog`.
  - Task 2: `grep -n "alert(" components/scenes/ScriptSummary.jsx` → nothing; file imports/uses `useToast`.
  - Task 3: `grep -n "removeConfirm\|revokeConfirm\|actionLoading\|confirm-overlay\|confirm-modal" components/team/TeamDrawer.jsx` → nothing; `confirm` from `useConfirmDialog` used by the two trigger handlers; `grep -n "confirm-overlay\|confirm-modal\|confirm-icon\|confirm-name\|confirm-warning\|confirm-actions\|confirm-cancel\|confirm-delete" components/team/TeamDrawer.css` → nothing.
- End-of-stream: `grep -rn "window.confirm\|[^a-zA-Z.]alert(" --include="*.jsx" components pages | grep -v "campaigns/\|Admin/"` returns nothing (only the excluded campaigns/admin native confirms remain in the whole in-scope tree).
- No test runner exists; live-drive is login-gated (as in prior streams). Correctness rests on build + per-task review + the invariants + before/after that each confirm still guards its destructive action, each toast still fires on failure, and TeamDrawer's remove/revoke still complete and report via toast.

## Success criteria

- Zero `window.confirm`/`alert()` in the in-scope tree; the only native confirms left are in the excluded campaigns/admin areas.
- Every destructive confirmation in scope routes through `useConfirmDialog`; TeamDrawer's bespoke confirm markup and its `.confirm-*` CSS family are gone.
- The merge-failure `alert()` is now a `toast.error`.
- Build green; work lands as three reviewed commits. Stream B is complete.
