# Remove Feedback Feature — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completely remove the in-app feedback feature (user submit UI, admin review, backend routes/service/emails, notification type) and the email-solicitation infra, leaving the production `feedback` DB table and migration history intact.

**Architecture:** Two independent removal tasks — frontend (Task 1) then backend (Task 2). Each deletes a set of files and cleans a set of edit-sites, then verifies via a build/import check plus grep invariants. No behavior is added; the net effect is deletion.

**Tech Stack:** Frontend — React 18 + Vite (JSX). Backend — Flask (Python 3.13). No test runner covers this feature; verification is `npm run build` / `python -c "import app"` + grep invariants.

**Spec:** `docs/superpowers/specs/2026-07-07-remove-feedback-feature-design.md`

## Global Constraints

- **Leave the `feedback` DB table untouched** — no `DROP`, no migration.
- **Keep migration `.sql` history** — `db/migrations/018_feedback_system.sql`, `021_add_feedback_reply_tracking.sql`. Delete only the `apply_migration_018.py` / `apply_migration_021.py` runner scripts.
- **Keep the announcement system** — `email_templates/feature_announcement.py` (class + registration) and `services/email_service.py::send_feature_announcement_email`. Only strip the feedback *content* from the announcement template.
- **Keep incidental "feedback" keeps:** `feedback_confirmation` / `feedback_reply` / `admin_feedback_alert` email-type **label strings** in `TransactionalLogPanel.jsx` and `EmailCampaignsPage.jsx` (they label historical email-log rows); incidental "feedback" comments in `SceneManager.jsx` / `AuthContext.jsx`; "feedback" copy in waitlist/welcome email templates.
- **Keep `MessageSquare` import** wherever it retains another use after the feedback nav entry is removed.
- **Commit trailers** — every commit ends with:
  ```
  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN
  ```
- **Branch:** `chore/remove-feedback`. Two reviewed commits (one per task). Push only on explicit command.

---

### Task 1: Frontend removal

**Files:**
- Delete: `frontend/src/components/feedback/FeedbackButton.jsx`
- Delete: `frontend/src/components/feedback/FeedbackButton.css`
- Delete: `frontend/src/components/feedback/FeedbackDrawer.jsx`
- Delete: `frontend/src/components/feedback/FeedbackDrawer.css`
- Delete: `frontend/src/pages/Admin/FeedbackManagement.jsx`
- Delete: `frontend/src/pages/Admin/FeedbackManagement.css`
- Delete: `frontend/src/components/admin/FeedbackDetailModal.jsx`
- Delete: `frontend/src/components/admin/FeedbackDetailModal.css`
- Modify: `frontend/src/components/layout/TopBar.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/admin/AdminLayout.jsx`
- Modify: `frontend/src/services/apiService.js`
- Modify: `frontend/src/components/notifications/NotificationBell.jsx`

(The `frontend/src/components/feedback/` directory becomes empty after its 4 files are deleted — remove the empty directory.)

**Interfaces:**
- Produces: nothing consumed by Task 2 (frontend and backend are independent). No new exports.

- [ ] **Step 1: Delete the 8 feedback component/page files**

```bash
cd frontend
git rm src/components/feedback/FeedbackButton.jsx \
       src/components/feedback/FeedbackButton.css \
       src/components/feedback/FeedbackDrawer.jsx \
       src/components/feedback/FeedbackDrawer.css \
       src/pages/Admin/FeedbackManagement.jsx \
       src/pages/Admin/FeedbackManagement.css \
       src/components/admin/FeedbackDetailModal.jsx \
       src/components/admin/FeedbackDetailModal.css
```

- [ ] **Step 2: Clean `TopBar.jsx`**

Remove the import line:
```jsx
import FeedbackButton from '../feedback/FeedbackButton';
```
And remove the render block (comment + conditional). It currently reads:
```jsx
              {/* Feedback Button - only show when authenticated */}
              {isAuthenticated && <FeedbackButton />}
```
Delete both lines. Verify no other `FeedbackButton` reference remains in the file. Leave everything else (the `isAuthenticated` variable is used elsewhere — do not remove it).

- [ ] **Step 3: Clean `App.jsx`**

Remove the import:
```jsx
import FeedbackManagement from './pages/Admin/FeedbackManagement';
```
Remove both feedback routes (the `admin/feedback` index route and the `admin/feedback/:feedbackId` detail route). They render `<FeedbackManagement />`. Delete both `<Route ...>` elements in full. Leave all sibling admin routes intact.

- [ ] **Step 4: Clean `AdminLayout.jsx`**

Remove the nav entry:
```jsx
    { path: '/admin/feedback', label: 'Feedback', icon: MessageSquare },
```
`MessageSquare` currently appears on exactly 2 lines: the lucide-react import and this nav entry. After removing the nav entry, `MessageSquare` is unused — **remove it from the lucide-react import** as well. (If, contrary to this, a build or grep shows `MessageSquare` used elsewhere, keep the import — verify with `grep -n "MessageSquare" src/components/admin/AdminLayout.jsx` after the edit: it must return nothing.)

- [ ] **Step 5: Clean `apiService.js`**

Remove the entire "Feedback API" section — from the banner comment:
```js
// ==================== Feedback API ====================
```
through the last feedback export in that section, stopping immediately before the next banner:
```js
// ==================== Email Campaigns API ====================
```
The section contains `submitFeedback`, `getUserFeedback`, `getFeedbackById` (and any admin feedback functions in that block). Delete the banner and every function between it and the Email Campaigns banner. Leave the Email Campaigns banner and everything after it untouched.

- [ ] **Step 6: Clean `NotificationBell.jsx`**

Two edits, both leaving every other notification type intact:
1. In the click handler, remove the `feedback_submitted` navigation branch. It currently reads (a leading `if`/`else if` chain):
```jsx
    if (notification.type === 'feedback_submitted' && notification.data?.feedback_id) {
      navigate(`/admin/feedback/${notification.data.feedback_id}`);
      setIsOpen(false);
    } else if (notification.data?.script_id) {
```
Convert this so the `script_id` branch becomes the leading `if` (drop the feedback branch, keep the `script_id` branch and any subsequent `else`/`else if` branches exactly as they are).
2. In the icon `switch`, remove:
```jsx
      case 'feedback_submitted':
        return <Bell size={16} />;
```
The `default` case already returns `<Bell size={16} />`, so removing this case leaves behavior unchanged for any stray historical `feedback_submitted` notification. Keep all other `case` branches and the `Bell` import (still used by `default`).

- [ ] **Step 7: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds. A dangling import to any deleted file would fail the build with a resolve error.

- [ ] **Step 8: Grep invariant**

Run: `grep -rn "feedback\|Feedback" frontend/src --include="*.jsx" --include="*.js"`
Expected: only the intentional keeps remain — incidental comments in `SceneManager.jsx` / `AuthContext.jsx`, and the `feedback_confirmation` / `feedback_reply` / `admin_feedback_alert` **label strings** in `TransactionalLogPanel.jsx` / `EmailCampaignsPage.jsx`. **No** reference to `FeedbackButton`, `FeedbackDrawer`, `FeedbackManagement`, `FeedbackDetailModal`, `submitFeedback`, `getUserFeedback`, `getFeedbackById`, `/admin/feedback`, or `feedback_submitted` remains. If any appears, fix it before committing.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "chore(feedback): remove frontend feedback feature (UI, admin, API, notification)

Delete FeedbackButton/FeedbackDrawer, FeedbackManagement page,
FeedbackDetailModal, the Feedback API section, and the
feedback_submitted notification handling. Feedback table untouched.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

### Task 2: Backend removal

**Files:**
- Delete: `backend/routes/feedback_routes.py`
- Delete: `backend/services/feedback_service.py`
- Delete: `backend/db/apply_migration_018.py`
- Delete: `backend/db/apply_migration_021.py`
- Delete: `backend/scripts/send_feedback_request.py`
- Delete: `backend/scripts/send_feedback_request_manual.py`
- Delete: `backend/email_templates/components/feedback_section.py`
- Modify: `backend/app.py`
- Modify: `backend/services/email_service.py`
- Modify: `backend/email_templates/components/__init__.py`
- Modify: `backend/email_templates/feature_announcement.py`

**Interfaces:**
- Consumes: nothing from Task 1 (independent).
- Produces: nothing consumed downstream.

- [ ] **Step 1: Delete the 7 backend files**

```bash
cd backend
git rm routes/feedback_routes.py \
       services/feedback_service.py \
       db/apply_migration_018.py \
       db/apply_migration_021.py \
       scripts/send_feedback_request.py \
       scripts/send_feedback_request_manual.py \
       email_templates/components/feedback_section.py
```

- [ ] **Step 2: Clean `app.py`**

Remove the import (currently line 18):
```python
from routes.feedback_routes import feedback_bp
```
Remove the registration (currently line 53):
```python
app.register_blueprint(feedback_bp)  # Feedback routes at /api/feedback/*
```
Leave all other blueprint imports and registrations (admin, campaign, webhook — note `webhook_bp` must still register before `campaign_bp`) untouched.

- [ ] **Step 3: Clean `email_service.py`**

Remove three functions in their entirety — they are the last three functions in the file (nothing follows `send_admin_feedback_alert_email`), so delete from the blank line before `def send_feedback_confirmation_email(` (~line 1399) through end-of-file:
- `send_feedback_confirmation_email(...)` (starts ~line 1401)
- `send_feedback_reply_email(...)` (starts ~line 1539)
- `send_admin_feedback_alert_email(...)` (starts ~line 1676)

The function immediately before them, `send_password_reset_email`, ends with `return result` (~line 1398) — that function and everything above it stay. Do **not** touch `send_feature_announcement_email` or any waitlist/welcome function. After the edit the file should end at `send_password_reset_email`'s `return result` (plus any trailing module code that was below 1676 — there is none between these fns and EOF, so EOF follows the last kept function).

- [ ] **Step 4: Clean `email_templates/components/__init__.py`**

Remove the import line:
```python
from .feedback_section import FeedbackSection
```
Remove `'FeedbackSection'` from `__all__`, leaving:
```python
__all__ = ['JourneyBox', 'CTABox', 'ProfileReminder']
```

- [ ] **Step 5: Clean `feature_announcement.py`**

Two edits; keep the template class and its registration:
1. Remove the `<!-- Feedback Request -->` HTML block — the entire `<div style="...">…</div>` containing "💬 We'd Love Your Feedback!" and the "Your input helps us build better tools…" paragraph (currently ~lines 61–70, between the CTA `</div>` and the "Thanks for being part of…" closing paragraph). Delete the block and its surrounding blank lines; keep the CTA block above it and the "Thanks for being part of…" paragraph below it.
2. In `_get_default_features`, remove the "Feedback System" feature dict:
```python
            {
                'icon': '💬',
                'title': 'Feedback System',
                'description': 'Share your thoughts and suggestions directly in the app. We read every piece of feedback!'
            },
```
Keep the remaining feature dicts (e.g. "Enhanced Reports") and the list/return structure intact.

- [ ] **Step 6: Import check**

Run: `cd backend && python -c "import app"` (with the app's env vars available; if env-gating blocks a full import, fall back to `python -c "import ast, pathlib; [ast.parse(pathlib.Path(p).read_text()) for p in ['app.py','services/email_service.py','email_templates/components/__init__.py','email_templates/feature_announcement.py']]"` to confirm no syntax error, plus `python -c "import email_templates.components"` and `python -c "import email_templates.feature_announcement"`).
Expected: no `ImportError` / `NameError` referencing `feedback_bp`, `feedback_routes`, `feedback_service`, `FeedbackSection`, or the removed email functions.

- [ ] **Step 7: Grep invariants**

Run (exclude `__pycache__`):
```bash
grep -rn "feedback_bp\|feedback_service\|feedback_routes\|FeedbackSection\|send_feedback_confirmation_email\|send_feedback_reply_email\|send_admin_feedback_alert_email" backend --include="*.py"
grep -rn "send_feedback_request" backend --include="*.py"
```
Expected: both return nothing. (`.pyc` files under `__pycache__` are ignored — regenerated.) The `feedback` table references in migration `.sql` files are out of scope and not matched by `--include="*.py"`.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "chore(feedback): remove backend feedback routes, service, emails, solicitation

Delete feedback_routes/feedback_service, the 3 feedback email
functions, the FeedbackSection email component, migration runner
scripts, and feedback-request scripts. Strip feedback content from
the announcement template. Feedback table + migration SQL kept.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01P9WZ2xHfDmLMtK81G7V4FN"
```

---

## Self-Review notes

- **Spec coverage:** All 13 deletes (8 FE + 7 BE... note: 8 FE files, but spec counts 13 total across both — 6 BE non-`__init__` + ... ) — reconciled: Task 1 deletes 8 files; Task 2 deletes 7 files; 9 edit-sites (5 FE + 4 BE) all have steps. The `feedback` table, migration SQL, announcement/waitlist systems are explicit keeps (Global Constraints).
- **Verification:** each task ends with a build/import check + grep invariant matching the spec's Verification section.
- **No placeholders:** every edit step shows the exact code to remove.
