# Phase 3 · Stream B3a — Modal Adoption — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the 3 live bespoke modals (ShareModal, UpgradeModal, InviteModal) to the shared `<Modal>` primitive, and delete the 4 dead modal components plus the dead `components/credits/` directory.

**Architecture:** Each live modal drops its hand-rolled overlay/backdrop/card-wrapper/header-chrome (markup + CSS) and moves its content into `<Modal>`'s `children`, passing a rich header via the `title` prop where needed. The primitive (`components/ui/Modal.jsx`) supplies the portal, backdrop, `.ui-modal` card, header/body/footer layout, X-close, and — via `useOverlay` — Escape-to-close, body scroll-lock, and focus-restore (all newly gained; the bespoke modals lacked them). Content-specific CSS is kept; only the overlay/card/header-chrome rules are pruned.

**Tech Stack:** React 18 + Vite (plain JSX, no TypeScript), lucide-react icons, plain CSS with design tokens in `frontend/src/index.css`.

## Global Constraints

- No test runner exists and live-drive is login-gated. Verification per task = `npm run build` green (run from `frontend/`) + the task's grep invariant. There are no unit tests to write.
- `<Modal>` API (from `frontend/src/components/ui/Modal.jsx`, do not change it): `Modal({ isOpen, onClose, title, size='md', footer, showClose=true, closeOnOverlay=true, closeOnEscape=true, overlayClassName='', children })`. `title` accepts a ReactNode and is wrapped in `<span className="ui-modal-title">`. `size` maps to max-width: `sm`=420px, `md`=560px, `lg`=820px. The header renders when `title` OR `showClose` is truthy; `.ui-modal-body` provides its own padding (`var(--space-6)`, ≈1.5rem) and `overflow-y: auto`; `.ui-modal` provides `background: var(--bg-card)`, border, radius, shadow, and `max-height`.
- Import the primitive from the `ui` barrel: `import { Modal } from '../ui';` (all three modals live at `components/<domain>/*`, so `'../ui'` is correct).
- Do NOT convert bespoke non-generic CTAs inside these modals (`.upgrade-btn-primary/-secondary`, `.submit-btn`, `.create-btn`, `.upgrade-btn`, `.copy-btn`, `.action-btn`, `.revoke-btn`) to `<Button>` — out of scope for B3a; keep them as-is in `children`.
- Do NOT touch the `window.confirm` in `ShareModal.handleRevokeLink` — routing native confirms through `useConfirmDialog` is Stream B5's job.
- Minor padding deltas from unifying on `.ui-modal-body` (e.g. UpgradeModal's card padding 2rem → body 1.5rem) are acceptable intended consequences, not regressions.

---

### Task 1: Delete dead modal code

Removes 4 dead components (verified imported/rendered nowhere) plus the dead credit-system directory. No live code references any of these.

**Files:**
- Delete: `frontend/src/components/common/AnalysisProgressModal.jsx`, `frontend/src/components/common/AnalysisProgressModal.css`
- Delete: `frontend/src/components/reports/ExportOptionsModal.jsx`, `frontend/src/components/reports/ExportOptionsModal.css`
- Delete: `frontend/src/components/scripts/LockScriptModal.jsx`, `frontend/src/components/scripts/LockScriptModal.css`
- Delete (whole dir): `frontend/src/components/credits/` (`CreditPurchaseModal.jsx`+`.css`, `CreditBalance.jsx`+`.css`, `index.js`)

- [ ] **Step 1: Delete the files**

```bash
cd frontend
git rm src/components/common/AnalysisProgressModal.jsx src/components/common/AnalysisProgressModal.css
git rm src/components/reports/ExportOptionsModal.jsx src/components/reports/ExportOptionsModal.css
git rm src/components/scripts/LockScriptModal.jsx src/components/scripts/LockScriptModal.css
git rm -r src/components/credits
```

- [ ] **Step 2: Verify no references remain**

Run:
```bash
grep -rn "AnalysisProgressModal\|ExportOptionsModal\|LockScriptModal\|CreditPurchaseModal\|CreditBalance\|components/credits" src --include="*.jsx" --include="*.js"
```
Expected: no output (exit code 1). If anything prints, a live reference exists — stop and report; do not proceed.

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: build succeeds (no "failed to resolve import" errors for the deleted files).

- [ ] **Step 4: Commit**

```bash
git commit -m "refactor(ui): delete dead modal components and credits directory

Remove AnalysisProgressModal, ExportOptionsModal, LockScriptModal, and the
entire components/credits directory (CreditPurchaseModal + unused CreditBalance
+ barrel) — all verified imported/rendered nowhere. Part of Phase 3 Stream B3a.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

### Task 2: Convert ShareModal to `<Modal>`

`ShareModal` is conditionally mounted by `ReportBuilder` (`{shareModalReport && <ShareModal … />}`) and has no `isOpen` prop of its own. Keep that mount gate unchanged; inside ShareModal pass `isOpen` (always true while mounted) to `<Modal>`.

**Files:**
- Modify: `frontend/src/components/reports/ShareModal.jsx`
- Modify: `frontend/src/components/reports/ShareModal.css`

**Interfaces:**
- Consumes: `Modal` from `frontend/src/components/ui` (barrel).
- Produces: no exported-interface change — `ShareModal({ report, onClose, onUpdate })` keeps the same props; `ReportBuilder.jsx` is untouched.

- [ ] **Step 1: Swap imports (drop `X`, add `Modal`)**

In `ShareModal.jsx`, replace the lucide import + ui import (currently lines 2–6):
```jsx
import { 
    Copy, Check, Link2, Clock, Printer, 
    Download, ExternalLink, AlertCircle
} from 'lucide-react';
import { Spinner, Modal } from '../ui';
```
(`X` is removed — the primitive supplies the close button. All other icons stay.)

- [ ] **Step 2: Replace the overlay/header wrapper with `<Modal>`**

Replace the entire `return ( … )` block (currently lines 96–225) with the following. The inner conditional content (`.share-link-section` and `.create-link-section` branches) is **unchanged** — only the outer wrapper and the header are replaced, and the `.share-modal-content` wrapper div is dropped (the primitive's `.ui-modal-body` provides padding). The `.report-info` block is kept as the first child.

```jsx
    return (
        <Modal
            isOpen
            onClose={onClose}
            size="sm"
            title={
                <span className="share-modal-title">
                    <Link2 size={20} />
                    Share Report
                </span>
            }
        >
            <div className="report-info">
                <span className="report-name">{report.title}</span>
            </div>

            {report.share_token ? (
                /* Existing Share Link */
                <div className="share-link-section">
                    <label>Share Link</label>
                    <div className="share-link-input">
                        <input type="text" value={shareUrl} readOnly />
                        <button className="copy-btn" onClick={handleCopy}>
                            {copied ? <Check size={16} /> : <Copy size={16} />}
                        </button>
                    </div>

                    <div className="link-meta">
                        <span className="expires">
                            <Clock size={12} />
                            Expires: {expiresAt}
                        </span>
                    </div>

                    <div className="share-actions">
                        <button className="action-btn" onClick={handleOpenPrint}>
                            <Printer size={16} />
                            Print View
                        </button>
                        <button className="action-btn" onClick={handleOpenPdf}>
                            <Download size={16} />
                            Download PDF
                        </button>
                        <button className="action-btn" onClick={() => window.open(shareUrl, '_blank')}>
                            <ExternalLink size={16} />
                            Open Link
                        </button>
                    </div>

                    <button className="revoke-btn" onClick={handleRevokeLink} disabled={isRevoking}>
                        {isRevoking ? (
                            <>
                                <Spinner size={14} />
                                Revoking...
                            </>
                        ) : (
                            'Revoke Share Link'
                        )}
                    </button>
                </div>
            ) : (
                /* Create New Link */
                <div className="create-link-section">
                    <p className="create-info">
                        Create a shareable link that anyone can use to view this report.
                    </p>

                    <div className="expiry-selector">
                        <label>Link expires in:</label>
                        <select value={expiresInDays} onChange={(e) => setExpiresInDays(Number(e.target.value))}>
                            <option value={1}>1 day</option>
                            <option value={7}>7 days</option>
                            <option value={14}>14 days</option>
                            <option value={30}>30 days</option>
                            <option value={90}>90 days</option>
                        </select>
                    </div>

                    <button className="create-btn" onClick={handleCreateLink} disabled={isCreating}>
                        {isCreating ? (
                            <>
                                <Spinner size={16} />
                                Creating...
                            </>
                        ) : (
                            <>
                                <Link2 size={16} />
                                Create Share Link
                            </>
                        )}
                    </button>

                    <div className="share-note">
                        <AlertCircle size={14} />
                        <span>Anyone with the link can view and print this report</span>
                    </div>
                </div>
            )}
        </Modal>
    );
```

- [ ] **Step 3: Prune ShareModal.css**

In `ShareModal.css`, **delete** these rule blocks (chrome now supplied by the primitive): `.share-modal-overlay`, `.share-modal`, `.share-modal-header`, `.share-modal-header h2`, `.close-btn`, `.close-btn:hover`, `.share-modal-content`.

Then **add** this rule (replaces the old `.share-modal-header h2` flex layout, now applied to the title node; `.ui-modal-title` already provides font size/weight/color):
```css
.share-modal-title {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}
```
Keep every other rule (`.report-info`, `.report-name`, `.share-link-section`, `.share-link-input`, `.copy-btn`, `.link-meta`, `.share-actions`, `.action-btn`, `.revoke-btn`, `.create-link-section`, `.create-info`, `.expiry-selector`, `.create-btn`, `.share-note`).

- [ ] **Step 4: Verify chrome classes are gone and build passes**

Run:
```bash
grep -n "share-modal-overlay\|share-modal-header\|share-modal-content\|\.close-btn" src/components/reports/ShareModal.css
```
Expected: no output.

Run: `npm run build`
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git commit -am "refactor(reports): adopt <Modal> primitive in ShareModal

Move ShareModal content into <Modal>; drop the bespoke overlay/header/close
CSS. Gains Escape-to-close, scroll-lock, and focus-restore. Part of B3a.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

### Task 3: Convert UpgradeModal to `<Modal>`

`UpgradeModal` already takes `{ isOpen, onClose, … }` and returns `null` when `!isOpen`. It has no title bar — the primitive's default header (empty title + X close) replaces the original absolute-positioned close button.

**Files:**
- Modify: `frontend/src/components/subscription/UpgradeModal.jsx`
- Modify: `frontend/src/components/subscription/UpgradeModal.css`

**Interfaces:**
- Consumes: `Modal` from `frontend/src/components/ui`.
- Produces: no prop change — `UpgradeModal({ isOpen, onClose, feature, title, message, daysRemaining, isExpired })` unchanged. Its 5 renderers (`SceneViewer`, `SubscriptionBanner`, `SubscriptionGate`, `ScriptUpload`, `InviteModal`) are untouched.

- [ ] **Step 1: Swap imports (drop `X`, add `Modal`)**

In `UpgradeModal.jsx`, replace the import section (currently lines 6–8):
```jsx
import React from 'react';
import { Sparkles, Check, CreditCard, Clock } from 'lucide-react';
import { Modal } from '../ui';
import './UpgradeModal.css';
```
(`X` removed; `WISE_PAYMENT_LINK` const below stays.)

- [ ] **Step 2: Remove the manual open-guard**

Delete this line (currently line 21) — the primitive handles `isOpen`:
```jsx
    if (!isOpen) return null;
```
Keep the `handleUpgrade`, `getTitle`, `getMessage`, `formatFeature` helpers unchanged.

- [ ] **Step 3: Replace the overlay/close wrapper with `<Modal>`**

Replace the entire `return ( … )` block (currently lines 45–119) with the following. The inner header/urgency/features/pricing/actions/footer markup is **unchanged** — only the outer `.upgrade-modal-overlay` / `.upgrade-modal` / `.upgrade-modal-close` wrapper is removed.

```jsx
    return (
        <Modal isOpen={isOpen} onClose={onClose} size="sm">
            <div className="upgrade-modal-header">
                <div className="upgrade-modal-icon">
                    <Sparkles size={32} />
                </div>
                <h2>{getTitle()}</h2>
                <p>{getMessage()}</p>
            </div>

            {daysRemaining !== null && daysRemaining > 0 && !isExpired && (
                <div className="upgrade-modal-urgency">
                    <Clock size={16} />
                    <span>{daysRemaining} {daysRemaining === 1 ? 'day' : 'days'} remaining</span>
                </div>
            )}

            <div className="upgrade-modal-features">
                <h3>What you'll get:</h3>
                <ul>
                    <li><Check size={16} /><span>Unlimited script uploads</span></li>
                    <li><Check size={16} /><span>Full AI-powered breakdown</span></li>
                    <li><Check size={16} /><span>Team collaboration (up to 10 members)</span></li>
                    <li><Check size={16} /><span>Reports & PDF exports</span></li>
                    <li><Check size={16} /><span>Stripboard editing</span></li>
                    <li><Check size={16} /><span>Department notes</span></li>
                </ul>
            </div>

            <div className="upgrade-modal-pricing">
                <div className="upgrade-modal-price">
                    <span className="price-amount">$49</span>
                    <span className="price-period">/month</span>
                </div>
                <p className="price-note">Unlimited breakdowns • Full production infrastructure</p>
            </div>

            <div className="upgrade-modal-actions">
                <button className="upgrade-btn-primary" onClick={handleUpgrade}>
                    <CreditCard size={18} />
                    Subscribe Now — $49/month
                </button>
                <button className="upgrade-btn-secondary" onClick={onClose}>
                    Maybe Later
                </button>
            </div>

            <p className="upgrade-modal-footer">
                Secure payment via Wise. Access activated after payment verification.
            </p>
        </Modal>
    );
```

- [ ] **Step 4: Prune UpgradeModal.css**

In `UpgradeModal.css`, **delete**: `.upgrade-modal-overlay`, `.upgrade-modal` (the card wrapper), the `@keyframes modalSlideIn` block (used only by `.upgrade-modal`), `.upgrade-modal-close`, `.upgrade-modal-close:hover`, and — inside the `@media (max-width: 480px)` block — the `.upgrade-modal { padding: 1.5rem; }` rule only (keep the `.upgrade-modal-features ul` and `.price-amount` rules in that media block).

Keep all content rules (`.upgrade-modal-header` and its `h2`/`p`, `.upgrade-modal-icon`, `.upgrade-modal-urgency`, `.upgrade-modal-features` + descendants, `.upgrade-modal-pricing`, `.upgrade-modal-price`, `.price-*`, `.upgrade-modal-actions`, `.upgrade-btn-primary`/`-secondary` + hovers, `.upgrade-modal-footer`).

- [ ] **Step 5: Verify chrome classes are gone and build passes**

Run:
```bash
grep -n "upgrade-modal-overlay\|upgrade-modal-close\|modalSlideIn" src/components/subscription/UpgradeModal.css
```
Expected: no output.

Run: `npm run build`
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git commit -am "refactor(subscription): adopt <Modal> primitive in UpgradeModal

Move UpgradeModal content into <Modal>; drop the bespoke overlay/card/close
CSS. Gains Escape-to-close, scroll-lock, and focus-restore. Part of B3a.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

### Task 4: Convert InviteModal to `<Modal>`

`InviteModal` takes `{ isOpen, onClose, scriptId, scriptTitle }`, returns `null` when `!isOpen`, and has **two** render branches (locked-state and form-state), each currently wrapped in its own `.invite-modal-overlay`. Both branches convert to `<Modal>` with the same rich `title`. The nested `<UpgradeModal>` in the locked branch stays as-is (now a Modal-over-Modal, both portaled to `document.body` — matches today's stacked overlays). InviteModal is rendered inside `TeamDrawer`; portaling to `document.body` moves it out of the drawer subtree (an improvement), independent of the deferred B3b drawer work.

**Files:**
- Modify: `frontend/src/components/team/InviteModal.jsx`
- Modify: `frontend/src/components/team/InviteModal.css`

**Interfaces:**
- Consumes: `Modal` from `frontend/src/components/ui` (alongside existing `Spinner`, `Button`).
- Produces: no prop change — `InviteModal({ isOpen, onClose, scriptId, scriptTitle })` unchanged; `TeamDrawer.jsx` untouched.

- [ ] **Step 1: Swap imports (drop `X`, add `Modal`)**

In `InviteModal.jsx`, update the lucide import (currently lines 9–19) to remove `X`:
```jsx
import { 
    Mail, 
    Users, 
    Copy,
    Check,
    Send,
    Link as LinkIcon,
    Lock,
    Sparkles
} from 'lucide-react';
```
And update the ui import (currently line 23):
```jsx
import { Spinner, Button, Modal } from '../ui';
```

- [ ] **Step 2: Remove the manual open-guard**

Delete this line (currently line 142) — both branches now pass `isOpen` to `<Modal>`:
```jsx
    if (!isOpen) return null;
```

- [ ] **Step 3: Convert the locked-state branch**

Replace the locked-state `return ( … )` block (currently lines 145–190) with:
```jsx
    if (!hasTeamAccess) {
        return (
            <>
                <Modal
                    isOpen={isOpen}
                    onClose={onClose}
                    size="md"
                    title={
                        <div className="header-content">
                            <Users size={24} />
                            <div>
                                <h2>Invite Team Member</h2>
                                <p className="script-name">{scriptTitle}</p>
                            </div>
                        </div>
                    }
                >
                    <div className="invite-locked">
                        <div className="locked-content">
                            <div className="locked-icon">
                                <Lock size={32} />
                            </div>
                            <h3>Team Collaboration Locked</h3>
                            <p>Upgrade to invite team members and collaborate on your scripts.</p>
                            <button className="upgrade-btn" onClick={() => setShowUpgradeModal(true)}>
                                <Sparkles size={18} />
                                Subscribe — $49/month
                            </button>
                        </div>
                    </div>
                </Modal>
                <UpgradeModal
                    isOpen={showUpgradeModal}
                    onClose={() => setShowUpgradeModal(false)}
                    feature="team_collaboration"
                    daysRemaining={daysRemaining}
                    isExpired={status === 'expired'}
                />
            </>
        );
    }
```

- [ ] **Step 4: Convert the form-state branch**

Replace the main `return ( … )` block (currently lines 192–347) so the outer `.invite-modal-overlay` / `.invite-modal` / `.invite-modal-header` / `.invite-modal-body` wrapper becomes `<Modal>`. The inner `<form>` and `.invite-success` markup is **unchanged**; only the wrapper is replaced:
```jsx
    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            size="md"
            title={
                <div className="header-content">
                    <Users size={24} />
                    <div>
                        <h2>Invite Team Member</h2>
                        <p className="script-name">{scriptTitle}</p>
                    </div>
                </div>
            }
        >
            {!inviteResult ? (
                <form onSubmit={handleSubmit}>
                    {/* Email Input */}
                    <div className="form-group">
                        <label>
                            <Mail size={16} />
                            Email Address
                        </label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="teammate@example.com"
                            required
                        />
                    </div>

                    {/* Department Selection */}
                    <div className="form-group">
                        <label>
                            <Users size={16} />
                            Department
                        </label>
                        <div className="department-grid">
                            {departments.map(dept => (
                                <button
                                    key={dept.code}
                                    type="button"
                                    className={`department-option ${department === dept.code ? 'selected' : ''}`}
                                    onClick={() => setDepartment(dept.code)}
                                    style={{
                                        '--dept-color': dept.color,
                                        borderColor: department === dept.code ? dept.color : undefined
                                    }}
                                >
                                    <span className="dept-dot" style={{ backgroundColor: dept.color }} />
                                    {dept.name}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Role Selection */}
                    <div className="form-group">
                        <label>Role</label>
                        <div className="role-options">
                            {ROLES.map(r => (
                                <label key={r.value} className={`role-option ${role === r.value ? 'selected' : ''}`}>
                                    <input
                                        type="radio"
                                        name="role"
                                        value={r.value}
                                        checked={role === r.value}
                                        onChange={(e) => setRole(e.target.value)}
                                    />
                                    <div className="role-content">
                                        <span className="role-name">{r.label}</span>
                                        <span className="role-desc">{r.description}</span>
                                    </div>
                                </label>
                            ))}
                        </div>
                    </div>

                    {/* Submit Button */}
                    <button type="submit" className="submit-btn" disabled={loading || !email || !department}>
                        {loading ? (
                            <>
                                <Spinner size={18} />
                                Creating Invite...
                            </>
                        ) : (
                            <>
                                <Send size={18} />
                                Create Invite Link
                            </>
                        )}
                    </button>
                </form>
            ) : (
                <div className="invite-success">
                    <div className="success-icon">
                        <Check size={32} />
                    </div>
                    <h3>Invite Created!</h3>
                    <p>
                        Share this link with <strong>{inviteResult.email}</strong> to invite them 
                        as <strong>{inviteResult.department}</strong>
                    </p>

                    <div className="invite-link-box">
                        <LinkIcon size={16} />
                        <input type="text" value={inviteResult.invite_url} readOnly />
                        <button className="copy-btn" onClick={copyInviteLink}>
                            {copied ? <Check size={16} /> : <Copy size={16} />}
                            {copied ? 'Copied!' : 'Copy'}
                        </button>
                    </div>

                    <p className="expires-note">
                        This link expires in 7 days
                    </p>

                    <div className="success-actions">
                        <Button variant="secondary" onClick={sendAnotherInvite}>
                            Invite Another
                        </Button>
                        <Button variant="primary" onClick={onClose}>
                            Done
                        </Button>
                    </div>
                </div>
            )}
        </Modal>
    );
```

- [ ] **Step 5: Prune InviteModal.css**

In `InviteModal.css`, **delete**: `.invite-modal-overlay`, `.invite-modal`, the `@keyframes modalSlideIn` block (used only by `.invite-modal`), `.invite-modal-header`, `.close-btn`, `.close-btn:hover`, `.invite-modal-body`, and — inside the `@media (max-width: 600px)` block — the `.invite-modal { max-height: 100vh; border-radius: 0; }` rule only (keep the `.department-grid` and `.success-actions` rules in that media block).

**Change** the locked-state padding so it composes with the body's padding instead of the old body wrapper (currently `.invite-locked { padding: 3rem 2rem; }`):
```css
.invite-locked {
    padding: 1.5rem 0.5rem;
}
```

Keep all other rules, including `.header-content` and its descendants (`.header-content svg`, `.header-content h2`, `.header-content .script-name`) — they now style the `title` node — plus `.form-group`, `.department-*`, `.dept-dot`, `.role-*`, `.role-content`, `.role-name`, `.role-desc`, `.submit-btn`, `.invite-success`, `.success-icon`, `.invite-link-box`, `.copy-btn`, `.expires-note`, `.success-actions`, `.locked-content`, `.locked-icon`, `.invite-locked .upgrade-btn`.

- [ ] **Step 6: Verify chrome classes are gone and build passes**

Run:
```bash
grep -n "invite-modal-overlay\|invite-modal-header\|invite-modal-body\|modalSlideIn\|\.close-btn" src/components/team/InviteModal.css
```
Expected: no output.

Run:
```bash
grep -c "<Modal" src/components/team/InviteModal.jsx
```
Expected: `2` (one per branch).

Run: `npm run build`
Expected: build succeeds.

- [ ] **Step 7: Commit**

```bash
git commit -am "refactor(team): adopt <Modal> primitive in InviteModal

Convert both InviteModal branches (locked + form) to <Modal>; drop the bespoke
overlay/header/body chrome. Nested UpgradeModal now portals independently.
Gains Escape-to-close, scroll-lock, and focus-restore. Part of B3a.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

## End-of-stream verification

After all 4 tasks, from `frontend/src`:

- Deletion invariant (empty):
  ```bash
  grep -rn "AnalysisProgressModal\|ExportOptionsModal\|LockScriptModal\|CreditPurchaseModal\|CreditBalance\|components/credits" . --include="*.jsx" --include="*.js"
  ```
- Each live modal imports and renders the primitive:
  ```bash
  grep -l "import { .*Modal.* } from '../ui'" components/reports/ShareModal.jsx components/subscription/UpgradeModal.jsx components/team/InviteModal.jsx
  grep -rn "share-modal-overlay\|upgrade-modal-overlay\|invite-modal-overlay" . --include="*.css"
  ```
  First returns all three files; second returns nothing.
- `npm run build` green.
- No test runner; live-drive login-gated. Correctness rests on build + per-task review + these invariants + before/after of each modal's open/close wiring.
