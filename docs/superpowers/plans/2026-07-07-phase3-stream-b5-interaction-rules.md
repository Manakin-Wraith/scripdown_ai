# Phase 3 Stream B5 — Interaction Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route every in-scope destructive confirmation through the `useConfirmDialog` context and the one transient failure through `useToast`, eliminating native `window.confirm`/`alert()` and TeamDrawer's bespoke confirm modals.

**Architecture:** Pure call-site refactor — no new components, no primitive changes. Five `window.confirm` guards become `const ok = await confirm({...}); if (!ok) return;`; one `alert()` becomes `toast.error(...)`; TeamDrawer's two hand-rolled modals collapse onto `confirm(...)` handlers with their bespoke state/JSX/CSS deleted. Both context providers (`ConfirmDialogProvider`, `ToastProvider`) already wrap the app and are proven in `ScriptLibrary.jsx`/`SceneEditor.jsx` (confirm) and reports/schedule (toast).

**Tech Stack:** React 18 + Vite, plain JSX, plain CSS with design tokens. No TypeScript, no test runner.

## Global Constraints

- **No test runner exists.** Verification per task = `npm run build` from `frontend/` succeeds + the grep invariants in that task. Live-drive is login-gated and not available.
- **Staging discipline (CRITICAL):** stage ONLY the named files with explicit `git add <path> <path>`. NEVER `git add .`, `git add -A`, or `git commit -a` — there is an untracked `.claude/` directory that must never be committed.
- **Commit trailers (MUST append to every commit):**
  ```
  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN
  ```
- **`useConfirmDialog` API:** `const { confirm } = useConfirmDialog();` → `await confirm({ title, message, variant: 'danger'|'warning'|'info', confirmText?, cancelText? })` returns `Promise<boolean>`. `message` is a single string. Import path from `components/<domain>/File.jsx`: `'../../context/ConfirmDialogContext'`.
- **`useToast` API:** `const toast = useToast();` → `toast.error(title, message)` / `toast.success(title, message)`. Import path: `'../../context/ToastContext'`.
- **Excluded — do NOT touch:** native confirms in `components/campaigns/*`, `pages/Admin/*`, `components/admin/*`, auth pages, and the frozen WIP components (SceneManager, DepartmentWorkspace, ShootingScriptPreview, CharacterProfile, SettingsPage, ScriptEditorPage). Do NOT add new failure toasts to DayColumn/DepartmentNotesSection's existing error handling — B5 is a confirm/alert consolidation only.
- **Copy:** where a bespoke modal used a separate name/email line, fold it into the single `message` string; preserve wording in substance.

---

### Task 1: Native `window.confirm` → `useConfirmDialog` (5 sites)

**Files:**
- Modify: `frontend/src/components/schedule/ShootingSchedulePage.jsx` (~line 115)
- Modify: `frontend/src/components/schedule/DayColumn.jsx` (~line 55, + imports/hook)
- Modify: `frontend/src/components/notes/DepartmentNotesSection.jsx` (~line 140, + imports/hook)
- Modify: `frontend/src/components/reports/ReportBuilder.jsx` (~line 179)
- Modify: `frontend/src/components/reports/ShareModal.jsx` (~line 52)

**Interfaces:**
- Consumes: `useConfirmDialog` from `'../../context/ConfirmDialogContext'` (existing).
- Produces: nothing later tasks depend on.

- [ ] **Step 1: ShootingSchedulePage.jsx** — it already imports `useToast` and has `const toast = useToast();` at the top of the component. Add the confirm hook. After the existing `import { useToast } from '../../context/ToastContext';` (line 6) add:
```jsx
import { useConfirmDialog } from '../../context/ConfirmDialogContext';
```
After `const toast = useToast();` (line 18) add:
```jsx
    const { confirm } = useConfirmDialog();
```
Then replace this block (in `handleDeleteSchedule`):
```jsx
        const sched = schedules.find(s => s.id === schedId);
        if (!window.confirm(`Delete "${sched?.name || 'this schedule'}" and all its shooting days? This cannot be undone.`)) return;
```
with:
```jsx
        const sched = schedules.find(s => s.id === schedId);
        const ok = await confirm({
            title: 'Delete Schedule?',
            message: `"${sched?.name || 'This schedule'}" and all its shooting days will be permanently deleted.`,
            variant: 'danger'
        });
        if (!ok) return;
```

- [ ] **Step 2: DayColumn.jsx** — add the import and hook. After the lucide import (line 2) add:
```jsx
import { useConfirmDialog } from '../../context/ConfirmDialogContext';
```
Inside the component, after `const dateInputRef = useRef(null);` (line 12) add:
```jsx
    const { confirm } = useConfirmDialog();
```
Then replace (in `handleDeleteDay`):
```jsx
        if (!window.confirm(`Delete Day ${day.day_number} and unschedule all its scenes?`)) return;
```
with:
```jsx
        const ok = await confirm({
            title: 'Delete Day?',
            message: `Day ${day.day_number} will be deleted and all its scenes unscheduled.`,
            variant: 'danger'
        });
        if (!ok) return;
```

- [ ] **Step 3: DepartmentNotesSection.jsx** — add the import and hook. After `import { Spinner } from '../ui';` (line 28) add:
```jsx
import { useConfirmDialog } from '../../context/ConfirmDialogContext';
```
Inside the component, after `const [submitting, setSubmitting] = useState(false);` (line 60) add:
```jsx
    const { confirm } = useConfirmDialog();
```
Then replace (in `handleDeleteNote`):
```jsx
        if (!window.confirm('Delete this note?')) return;
        
```
with:
```jsx
        const ok = await confirm({
            title: 'Delete Note?',
            message: 'This note will be permanently deleted.',
            variant: 'danger'
        });
        if (!ok) return;

```

- [ ] **Step 4: ReportBuilder.jsx** — it already imports `useToast` and has `const toast = useToast();`. After `import { useToast } from '../../context/ToastContext';` (line 10) add:
```jsx
import { useConfirmDialog } from '../../context/ConfirmDialogContext';
```
Inside the component, immediately after `const toast = useToast();` (line 50) add:
```jsx
    const { confirm } = useConfirmDialog();
```
Then replace (in `handleDelete`):
```jsx
        if (!window.confirm('Delete this report?')) return;
        
```
with:
```jsx
        const ok = await confirm({
            title: 'Delete Report?',
            message: 'This report will be permanently deleted.',
            variant: 'danger'
        });
        if (!ok) return;

```

- [ ] **Step 5: ShareModal.jsx** — it already imports `useToast` and has `const toast = useToast();` (line 17). After `import { useToast } from '../../context/ToastContext';` (line 7) add:
```jsx
import { useConfirmDialog } from '../../context/ConfirmDialogContext';
```
Inside the component, immediately after `const toast = useToast();` (line 17) add:
```jsx
    const { confirm } = useConfirmDialog();
```
Then replace (in `handleRevokeLink`):
```jsx
        if (!window.confirm('Revoke this share link? Anyone with the link will lose access.')) return;
        
```
with:
```jsx
        const ok = await confirm({
            title: 'Revoke Share Link?',
            message: 'Anyone with the link will lose access.',
            variant: 'warning',
            confirmText: 'Revoke'
        });
        if (!ok) return;

```

- [ ] **Step 6: Verify** — from `frontend/`:
```bash
grep -n "window.confirm" src/components/schedule/ShootingSchedulePage.jsx src/components/schedule/DayColumn.jsx src/components/notes/DepartmentNotesSection.jsx src/components/reports/ReportBuilder.jsx src/components/reports/ShareModal.jsx
```
Expected: no output.
```bash
grep -c "useConfirmDialog" src/components/schedule/ShootingSchedulePage.jsx src/components/schedule/DayColumn.jsx src/components/notes/DepartmentNotesSection.jsx src/components/reports/ReportBuilder.jsx src/components/reports/ShareModal.jsx
```
Expected: each file reports `2` (import + hook call).
```bash
npm run build
```
Expected: succeeds (pre-existing chunk-size + apiService dynamic-import warnings are unrelated and OK).

- [ ] **Step 7: Commit**
```bash
git add frontend/src/components/schedule/ShootingSchedulePage.jsx frontend/src/components/schedule/DayColumn.jsx frontend/src/components/notes/DepartmentNotesSection.jsx frontend/src/components/reports/ReportBuilder.jsx frontend/src/components/reports/ShareModal.jsx
git commit -m "refactor(ui): route destructive confirms through useConfirmDialog

Replace 5 native window.confirm guards (schedule delete/day, note delete,
report delete, share-link revoke) with the themed useConfirmDialog context.
Part of Phase 3 Stream B5 (interaction rules).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

### Task 2: `alert()` → `useToast` (ScriptSummary)

**Files:**
- Modify: `frontend/src/components/scenes/ScriptSummary.jsx` (~line 136, + imports/hook)

**Interfaces:**
- Consumes: `useToast` from `'../../context/ToastContext'` (existing).
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Add the toast import** — after `import { Badge } from '../ui';` (line 3) add:
```jsx
import { useToast } from '../../context/ToastContext';
```

- [ ] **Step 2: Add the hook** — inside the component, after `const [mergeSuccess, setMergeSuccess] = useState(null);` (line 61) add:
```jsx
    const toast = useToast();
```

- [ ] **Step 3: Replace the alert** — in the merge `catch` block, replace:
```jsx
            console.error('Merge failed:', err);
            alert('Merge failed: ' + (err.response?.data?.error || err.message));
```
with:
```jsx
            console.error('Merge failed:', err);
            toast.error('Merge Failed', err.response?.data?.error || err.message);
```

- [ ] **Step 4: Verify** — from `frontend/`:
```bash
grep -n "alert(" src/components/scenes/ScriptSummary.jsx
```
Expected: no output.
```bash
grep -c "useToast" src/components/scenes/ScriptSummary.jsx
```
Expected: `2` (import + hook call).
```bash
npm run build
```
Expected: succeeds.

- [ ] **Step 5: Commit**
```bash
git add frontend/src/components/scenes/ScriptSummary.jsx
git commit -m "refactor(scenes): replace merge-failure alert() with toast.error

ScriptSummary's character-merge failure now surfaces via the useToast
channel instead of a native alert(). Part of Phase 3 Stream B5.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

### Task 3: TeamDrawer bespoke confirms → `useConfirmDialog`

**Files:**
- Modify: `frontend/src/components/team/TeamDrawer.jsx`
- Modify: `frontend/src/components/team/TeamDrawer.css`

**Interfaces:**
- Consumes: `useConfirmDialog` from `'../../context/ConfirmDialogContext'` (existing).
- Produces: nothing later tasks depend on.

**Context the diff can't show:** `Spinner` (line 245, drawer loading state), `UserX` (line 333, remove trigger), and `LinkIcon` (line 373, revoke trigger) are ALL still used after the modals are deleted — keep those imports. `Trash2` is used ONLY inside the two deleted modals (lines 439, 462) — after deletion it is unused and must be removed from the lucide import. In `TeamDrawer.css`, the `@keyframes fadeIn` (used at line 367) and `@keyframes scaleIn` (used at line 383) are referenced ONLY by the confirm rules, so they are deleted along with the block.

- [ ] **Step 1: Add the confirm hook** — after `import { useToast } from '../../context/ToastContext';` (line 25) add:
```jsx
import { useConfirmDialog } from '../../context/ConfirmDialogContext';
```
Inside the component, immediately after `const toast = useToast();` (line 39) add:
```jsx
    const { confirm } = useConfirmDialog();
```

- [ ] **Step 2: Delete the bespoke confirm state** — remove these three `useState` lines (currently lines 49–51):
```jsx
    const [removeConfirm, setRemoveConfirm] = useState(null);
    const [revokeConfirm, setRevokeConfirm] = useState(null);
    const [actionLoading, setActionLoading] = useState(null);
```

- [ ] **Step 3: Clean the two handlers** — in `handleRemoveMember`, remove the `setActionLoading(memberId);` line at the top and the `setRemoveConfirm(null);` line (currently after the `setMembers(...)` filter), and remove the `finally { setActionLoading(null); }` block. The result:
```jsx
    const handleRemoveMember = async (memberId, memberName) => {
        try {
            const { supabase } = await import('../../lib/supabase');
            const { data: { session } } = await supabase.auth.getSession();

            const response = await fetch(
                `${API_BASE_URL}/api/scripts/${scriptId}/members/${memberId}`,
                {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${session?.access_token || ''}`
                    }
                }
            );

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Failed to remove member');
            }

            // Update local state
            setMembers(prev => prev.filter(m => m.id !== memberId));
            toast.success('Member Removed', `${memberName} has been removed from the team`);

        } catch (err) {
            console.error('Error removing member:', err);
            toast.error('Error', err.message);
        }
    };
```
Apply the equivalent edit to `handleRevokeInvite` (remove `setActionLoading(inviteId);`, `setRevokeConfirm(null);`, and the `finally { setActionLoading(null); }`):
```jsx
    const handleRevokeInvite = async (inviteId, email) => {
        try {
            const { supabase } = await import('../../lib/supabase');
            const { data: { session } } = await supabase.auth.getSession();

            const response = await fetch(
                `${API_BASE_URL}/api/invites/${inviteId}`,
                {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${session?.access_token || ''}`
                    }
                }
            );

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Failed to revoke invite');
            }

            // Update local state
            setInvites(prev => prev.filter(i => i.id !== inviteId));
            toast.success('Invite Revoked', `Invite to ${email} has been revoked`);

        } catch (err) {
            console.error('Error revoking invite:', err);
            toast.error('Error', err.message);
        }
    };
```

- [ ] **Step 4: Add the two confirm-trigger handlers** — immediately after `handleRevokeInvite` (and before the render/return), add:
```jsx
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

- [ ] **Step 5: Rewire the trigger buttons** — replace the remove button's handler:
```jsx
                                                    <button 
                                                        className="remove-btn"
                                                        onClick={() => setRemoveConfirm({
                                                            id: member.id,
                                                            name: member.name
                                                        })}
                                                        title="Remove member"
                                                    >
                                                        <UserX size={16} />
                                                    </button>
```
with:
```jsx
                                                    <button 
                                                        className="remove-btn"
                                                        onClick={() => handleRemoveClick(member)}
                                                        title="Remove member"
                                                    >
                                                        <UserX size={16} />
                                                    </button>
```
and the revoke button's handler:
```jsx
                                                    <button 
                                                        className="revoke-btn"
                                                        onClick={() => setRevokeConfirm({
                                                            id: invite.id,
                                                            email: invite.email
                                                        })}
                                                        title="Revoke invite"
                                                    >
                                                        <LinkIcon size={14} />
                                                    </button>
```
with:
```jsx
                                                    <button 
                                                        className="revoke-btn"
                                                        onClick={() => handleRevokeClick(invite)}
                                                        title="Revoke invite"
                                                    >
                                                        <LinkIcon size={14} />
                                                    </button>
```

- [ ] **Step 6: Delete the two bespoke modal JSX blocks** — remove the entire `{/* Remove Member Confirmation Modal */}` block (`{removeConfirm && ( ... )}`) and the entire `{/* Revoke Invite Confirmation Modal */}` block (`{revokeConfirm && ( ... )}`). These are the two sibling blocks that follow the closing `</Drawer>` tag.

- [ ] **Step 7: Remove the now-unused `Trash2` import** — in the lucide import block (lines 12–24), delete the `Trash2` line. The line above it (`ChevronUp`) already ends the list without a trailing comma issue only if `Trash2` was last; `Trash2` IS the last entry, so remove both `Trash2` and the trailing comma after `ChevronDown`/`ChevronUp` as needed to keep valid syntax. Concretely, the import currently ends:
```jsx
    ChevronDown,
    ChevronUp,
    Trash2
} from 'lucide-react';
```
Change it to:
```jsx
    ChevronDown,
    ChevronUp
} from 'lucide-react';
```

- [ ] **Step 8: Prune the confirm CSS** — in `TeamDrawer.css`, delete the entire "Confirmation Modal Overrides" section: the comment header
```css
/* ============================================ */
/* Confirmation Modal Overrides */
/* ============================================ */
```
through the end of the `.confirm-cancel:disabled, .confirm-delete:disabled { ... }` rule. This spans every rule whose selector contains `confirm-` (`.confirm-overlay`, `.confirm-modal`, `.confirm-icon`, `.confirm-name`, `.confirm-warning`, `.confirm-actions`, `.confirm-cancel`, `.confirm-delete` and their modifier/descendant variants) PLUS the `@keyframes fadeIn` and `@keyframes scaleIn` that sit inside that section (both are used only by the confirm rules). Do NOT delete anything after it — the `.team-drawer-title`, `.team-drawer-body`, and `.drawer-loading`/`.drawer-error` rules that follow must stay.

- [ ] **Step 9: Verify** — from `frontend/`:
```bash
grep -n "removeConfirm\|revokeConfirm\|actionLoading" src/components/team/TeamDrawer.jsx
```
Expected: no output.
```bash
grep -n "confirm-overlay\|confirm-modal\|confirm-icon\|confirm-name\|confirm-warning\|confirm-actions\|confirm-cancel\|confirm-delete" src/components/team/TeamDrawer.css
```
Expected: no output.
```bash
grep -n "Trash2\|fadeIn\|scaleIn" src/components/team/TeamDrawer.jsx src/components/team/TeamDrawer.css
```
Expected: no output.
```bash
grep -c "useConfirmDialog\|handleRemoveClick\|handleRevokeClick" src/components/team/TeamDrawer.jsx
```
Expected: `useConfirmDialog` and both handlers present (≥1 each; the grep -c counts total matching lines).
```bash
grep -n "Spinner\|UserX\|LinkIcon" src/components/team/TeamDrawer.jsx
```
Expected: still present (Spinner at the loading state; UserX/LinkIcon on the trigger buttons).
```bash
npm run build
```
Expected: succeeds.

- [ ] **Step 10: Commit**
```bash
git add frontend/src/components/team/TeamDrawer.jsx frontend/src/components/team/TeamDrawer.css
git commit -m "refactor(team): consolidate TeamDrawer confirms onto useConfirmDialog

Replace the two hand-rolled remove-member / revoke-invite confirm modals
with the shared useConfirmDialog context. Deletes removeConfirm/revokeConfirm/
actionLoading state, the bespoke modal JSX, the unused Trash2 import, and the
.confirm-* CSS family (with its fadeIn/scaleIn keyframes). Dialog now closes on
confirm and the existing toast reports the outcome — matching the rest of the
app. Closes Phase 3 Stream B5 / Stream B.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

## End-of-stream verification

After all 3 tasks, from `frontend/src`:
```bash
grep -rn "window.confirm" --include="*.jsx" components pages | grep -v "campaigns/\|Admin/\|admin/"
```
Returns nothing (only the excluded campaigns/admin native confirms remain).
```bash
grep -rn "[^a-zA-Z._]alert(" --include="*.jsx" components pages | grep -v "campaigns/\|Admin/\|admin/"
```
Returns nothing.
- `npm run build` green.
- No test runner; live-drive login-gated. Correctness rests on build + per-task review + these invariants + before/after that each confirm still guards its destructive action, the merge toast fires on failure, and TeamDrawer remove/revoke still complete and report via toast.
