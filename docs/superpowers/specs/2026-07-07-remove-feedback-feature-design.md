# Remove Feedback Feature — Design

**Date:** 2026-07-07
**Status:** Approved (design)
**Goal:** Completely remove the in-app feedback feature (user submission UI, admin review, backend routes/service/emails) and the email-based feedback-solicitation infra, while leaving the production `feedback` DB table and migration history intact.

## Context

The feedback feature spans both apps: a user-facing submit flow (`FeedbackButton` in TopBar → `FeedbackDrawer` form → `POST /api/feedback` → `feedback` table), an admin review flow (`FeedbackManagement` page + `FeedbackDetailModal` → GET/PATCH/reply/delete/stats endpoints), transactional emails (confirmation / reply / admin-alert), a `feedback_submitted` notification type, and a separate email-solicitation mechanism (scripts that email beta users asking for feedback, plus a reusable `FeedbackSection` email component).

Two things named "feedback" are **not** part of this and are kept: (1) `feature_announcement.py` + `send_feature_announcement_email` — the general feature-announcement email system (admin-triggered via `auth_routes`), which merely *contains* a feedback blurb; (2) incidental "feedback" wording in unrelated waitlist/welcome email copy and code comments.

**Verified dependency facts:** the 3 feedback email functions are called only by `feedback_service.py`; `feedback_service.py` is imported only by `feedback_routes.py`; `FeedbackSection` is referenced only by its own file and the `components/__init__.py` export; `send_feedback_request*.py` are standalone scripts. So all deletions are dangling-free once their edit-sites are cleaned.

## User decisions (locked)

- **Remove the email-solicitation infra too** (broader removal), not just the in-app feature.
- **Leave the production `feedback` DB table** untouched (orphaned; no drop).
- **Keep the historical migration `.sql` files** (`018`, `021`); delete only the one-off `apply_migration_*.py` runner scripts.

## Scope

### Task 1 — Frontend removal

**Delete files:**
- `frontend/src/components/feedback/FeedbackButton.jsx`, `FeedbackButton.css`
- `frontend/src/components/feedback/FeedbackDrawer.jsx`, `FeedbackDrawer.css`
- `frontend/src/pages/Admin/FeedbackManagement.jsx`, `FeedbackManagement.css`
- `frontend/src/components/admin/FeedbackDetailModal.jsx`, `FeedbackDetailModal.css`
(The `components/feedback/` directory becomes empty and is removed.)

**Edit files:**
- `components/layout/TopBar.jsx` — remove `import FeedbackButton …` (line 17) and the `{isAuthenticated && <FeedbackButton />}` render (lines ~102–103), plus its comment.
- `App.jsx` — remove `import FeedbackManagement …` (line 27) and both routes `admin/feedback` and `admin/feedback/:feedbackId` (lines ~110–118).
- `components/admin/AdminLayout.jsx` — remove the `{ path: '/admin/feedback', label: 'Feedback', icon: MessageSquare }` nav entry (line ~23). Remove the `MessageSquare` lucide import only if it becomes unused after this.
- `services/apiService.js` — remove the entire "Feedback API" section (from the `// ==================== Feedback API ====================` banner, line ~1700, through the last feedback export): `submitFeedback`, `getUserFeedback`, `getFeedbackById`, and the admin feedback functions (list/status/reply/delete/stats) in that section.
- `components/notifications/NotificationBell.jsx` — remove the `feedback_submitted` handling: the navigation branch (`if (notification.type === 'feedback_submitted' …) navigate('/admin/feedback/…')`, lines ~188–189) and the `case 'feedback_submitted':` label branch (line ~205). Leave all other notification types intact.

**Verification:** `npm run build` from `frontend/` succeeds (a dangling import to any deleted file would fail the build). `grep -rn "feedback\|Feedback" frontend/src --include="*.jsx" --include="*.js"` returns only the intentional keeps: incidental comments in `SceneManager.jsx`/`AuthContext.jsx` and the `feedback_confirmation` label strings in `TransactionalLogPanel.jsx`/`EmailCampaignsPage.jsx`. No reference to any deleted component/route/API function remains.

### Task 2 — Backend removal

**Delete files:**
- `backend/routes/feedback_routes.py`
- `backend/services/feedback_service.py`
- `backend/db/apply_migration_018.py`, `backend/db/apply_migration_021.py`
- `backend/scripts/send_feedback_request.py`, `backend/scripts/send_feedback_request_manual.py`
- `backend/email_templates/components/feedback_section.py`

**Edit files:**
- `backend/app.py` — remove `from routes.feedback_routes import feedback_bp` (line 18) and `app.register_blueprint(feedback_bp) …` (line 53).
- `backend/services/email_service.py` — remove the 3 feedback functions and their bodies: `send_feedback_confirmation_email` (~1401), `send_feedback_reply_email` (~1539), `send_admin_feedback_alert_email` (~1676). Leave everything else (incl. `send_feature_announcement_email`, waitlist/welcome templates and their "feedback" copy) untouched.
- `backend/email_templates/components/__init__.py` — remove `from .feedback_section import FeedbackSection` and the `'FeedbackSection'` entry in `__all__`.
- `backend/email_templates/feature_announcement.py` — strip the feedback-request content: the `<!-- Feedback Request -->` HTML block (~lines 62–68) and the "Feedback System" feature dict entry in the default features list (~lines 103–104). Keep the template class, its registration, and all other content.

**Verification:** the backend imports cleanly with the feedback code gone — `python -c "import app"` (run from `backend/`, with the app's env available or via a syntax/import check) succeeds with no `ImportError`/`NameError` from the removed blueprint, service, or email functions. `grep -rn "feedback_bp\|feedback_service\|feedback_routes\|FeedbackSection\|send_feedback_confirmation_email\|send_feedback_reply_email\|send_admin_feedback_alert_email" backend --include="*.py"` (excluding `__pycache__`) returns nothing. `grep -rn "send_feedback_request" backend --include="*.py"` returns nothing.

## Out of scope / explicit keeps

- The `feedback` DB table — untouched (per decision). No `DROP` migration.
- Migration files `db/migrations/018_feedback_system.sql`, `021_add_feedback_reply_tracking.sql` — kept as schema history.
- `feature_announcement.py` + `send_feature_announcement_email` + the `auth_routes` announcement endpoint — kept (general announcement system).
- Waitlist/welcome scripts (`send_early_access_reminder.py`, `send_waitlist_reminder.py`, `send_waitlist_confirmation_manual.py`, `send_welcome_credits_manual.py`) and their "feedback" copy — kept.
- `feedback_confirmation` / `feedback_reply` / `admin_feedback_alert` email-type *label* strings in `TransactionalLogPanel.jsx` and `EmailCampaignsPage.jsx` — kept (they label historical email-log rows; removing them would show raw keys).
- Incidental "feedback" comments in `SceneManager.jsx` / `AuthContext.jsx` — kept.
- The `.pyc` files under `__pycache__` — ignored (regenerated; not tracked meaningfully).

## Verification (overall)

- Task 1: `npm run build` green + the frontend grep invariant.
- Task 2: backend import check clean + the backend grep invariants.
- No test runner covers the feedback feature; correctness rests on the build/import checks + grep invariants + per-task review + final whole-branch review. Live-drive is login-gated. Runtime confirmation (feedback button gone from TopBar, `/admin/feedback` 404, no console errors) is a post-deploy user check.

## Execution

Full subagent-driven-development on branch `chore/remove-feedback`. Two tasks (frontend removal → backend removal), each with its own build/import verification and review, then a final whole-branch review, then merge (push on command).

## Success criteria

- All 13 feedback files deleted; all 9 edit-sites cleaned; frontend builds; backend imports cleanly.
- No dangling reference to any removed component, route, API function, blueprint, service, or email function anywhere in `frontend/src` or `backend` (excluding the intentional keeps above).
- The `feedback` table, migration history, and the announcement/waitlist systems are untouched.
- Work lands as two reviewed commits.
