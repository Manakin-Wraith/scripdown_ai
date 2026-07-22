# Teams & Access-Control Hardening — Design

**Date:** 2026-07-08
**Status:** Approved — ready for implementation plan
**Author:** Brainstormed with Claude

## Problem

The app has **no server-side authorization**. Authentication (verifying *who* a user is) works via Supabase JWT, but authorization (verifying *what* a user may touch) is effectively absent:

- 56 `@optional_auth` endpoints vs 54 `@require_auth` across `backend/routes/`. Many of the optional-auth endpoints are script-scoped data routes (scenes, notes, schedule, reports) that perform **no ownership or membership check**. Access is effectively "know the script UUID."
- The backend uses the Supabase **service-role key**, which bypasses Postgres RLS entirely — so the database enforces nothing. Enforcement must live in app code.
- No ownership/membership helper exists; the few checks that exist are ad-hoc and inconsistent (e.g. `remove_member` inline-checks owner; `create_note` uses membership only to guess a department and **silently falls back to the "production" department for non-members**, still writing the row).

This is a **data-isolation vulnerability affecting solo users today**, not just a Teams gap: any authenticated user can read and write any other user's script.

Separately, the **Teams feature is demoable but not sellable**. Verified end-to-end state:

- Invites are never emailed — the owner must manually copy/paste a link (`create_invite` never calls any send function; no `send_invite` exists in `email_service.py`).
- The invite link is an **unbound bearer token** — the email-match check in `accept_invite` is commented out (`invite_routes.py:317-319`), so any logged-in account holding the link can accept.
- Roles (admin/member/viewer) are **cosmetic** — no write endpoint enforces them.
- No role management exists after invite (role is immutable; no endpoint or UI).

## Goals

1. Close the authorization hole across **all** script-scoped endpoints in one coherent pass.
2. Introduce a single, testable authorization primitive with a clear role hierarchy.
3. Make Teams genuinely safe to sell: real invite emails, links bound to the invited email, enforced roles, and role management.
4. Land the first real backend authorization tests.

## Non-Goals

- Postgres RLS / per-request user-scoped Supabase clients. Considered and deferred — a large, risky rewrite of the 180KB data layer. Recorded as a future **defense-in-depth** layer, not this phase.
- Department-scoped write permissions. Permissions are **global by role** this phase; department remains a label/default. (May become an optional per-script flag later; the helper should not preclude it, but no work is done for it now.)
- Lighting up the disabled department-workspace / threads UI (Bucket 2/3 items from the audit). Out of scope.

## Decisions (locked)

- **Mechanism:** Centralized app-layer authorization — one helper + one decorator, applied everywhere. (Not RLS, not ad-hoc inline patches.)
- **Permission model:** Global role hierarchy. Department is a label only.
- **Sweep scope:** All-in-one-pass — convert every script-scoped endpoint across `supabase_routes.py`, `schedule_routes.py`, and `report_routes.py` in a single effort. No partial rollout that leaves the hole half-open.

## Architecture

### New module: `backend/middleware/authorization.py`

Kept separate from `auth.py`, which stays authentication-only.

**Role ladder**

```python
ROLE_RANK = {'viewer': 1, 'member': 2, 'admin': 3, 'owner': 4}
```

**`get_script_role(script_id, user_id) -> str | None`**

- Returns `'owner'` if `scripts.user_id == user_id`.
- Else returns the `script_members.role` for `(script_id, user_id)`.
- Else returns `None` (no access).
- One DB round-trip; single source of truth. Owner is implicit — never stored as a `script_members` row.

**`@require_script_role(min_role)` decorator**

- Stacked **after** `@require_auth` (which guarantees `g.current_user`).
- Extracts `script_id` from the route's kwargs.
- Calls `get_script_role(script_id, user_id)`.
- If the script does not exist → **404** (avoids leaking existence to strangers).
- If the user's role rank `< min_role` rank (or `None`) → **403**.
- On success, sets `g.script_role` so the handler can make finer decisions without re-querying, and proceeds.

### Permission matrix

| Capability | Min role |
|---|---|
| Read scenes / reports / notes / schedule / members | **viewer** |
| Create/edit/delete scenes, notes, schedule; run AI analysis; manage story days | **member** |
| Invite / remove members, change roles, revoke invites | **admin** |
| Delete script, lock/unlock script | **owner** |

Ranks are **inclusive**: a higher rank has every capability of the ranks below it. So owner and admin can run AI analysis, edit scenes, etc., exactly as a member can — `min_role` is a floor, not an exact match. (Transfer ownership is intentionally out of scope this phase — no endpoint exists and none is added.)

## Endpoint classification & conversion

Every script-scoped endpoint is sorted into exactly one bucket. The implementation plan will contain the **complete endpoint → bucket table**; the rules:

- **Public (stays `@optional_auth`) — explicit whitelist:** the share-link routes (`/shared/<token>`, `/shared/<token>/pdf`, `/shared/<token>/print`). These are intentionally auth-free and MUST remain so. Whitelisted in the spec so they are never accidentally locked.
- **Read → `@require_auth` + `@require_script_role('viewer')`**
- **Write → `@require_auth` + `@require_script_role('member')`**
- **Manage → `@require_auth` + `@require_script_role('admin')` or `('owner')`** per the matrix.

Files in scope: `backend/routes/supabase_routes.py`, `backend/routes/schedule_routes.py` (currently all `@optional_auth`), `backend/routes/report_routes.py`, `backend/routes/invite_routes.py`.

**Specific fixes that fall out of the sweep:**

- **`create_note` silent fallback** (`supabase_routes.py:3792-3809`): non-members currently fall back to the "production" department and still write. This becomes a hard **403** via `@require_script_role('member')`. Department auto-detection remains only as a convenience for actual members.
- **`schedule_routes.py`**: entirely `@optional_auth` today (any caller can PATCH/DELETE any schedule/day/scene assignment). Gets member-level enforcement across every mutating route and viewer-level on reads.
- **`create_invite`**: currently checks ownership inline — replace with `@require_script_role('admin')` for consistency.

## Teams Phase 2 (rides on the new primitive)

- **Invite email:** add `send_invite()` to `email_service.py` with a new template under `email_templates/`. `create_invite` calls it with the invite URL after creating the invite. The copy-link flow remains as a fallback in the UI.
- **Bind invite to invitee:** re-enable the email-match check in `accept_invite` (`invite_routes.py:317-319`) so a link only works for the addressed email. The existing `auto_accept_pending_invites` path (already keyed on email) is unaffected.
- **Role management:** new `PATCH /api/scripts/<script_id>/members/<member_id>` guarded by `@require_script_role('admin')`, updating `script_members.role`. Guardrails: cannot change the owner; cannot elevate above the actor's own rank. Add a role-picker to `TeamDrawer.jsx`.

## Error handling

- **401** — no/invalid JWT (from `@require_auth`).
- **403** — authenticated but insufficient role.
- **404** — script does not exist (existence not leaked).
- Consistent JSON error shape: `{ "error": "<message>" }`, matching existing route conventions.
- `DEV_MODE` bypass in `require_auth` is preserved; `get_script_role` still runs in dev, but dev requests resolve to `DEV_USER_ID` — dev seed data should make that user an owner of test scripts.

## Rollout safety

Flipping `optional_auth → require_auth` breaks any endpoint the frontend calls **without** a JWT. Mitigations, included as plan steps:

1. `frontend/src/services/apiService.js` already attaches the cached Supabase JWT to every request — so risk is low by design.
2. Before flipping, grep all frontend callsites for the converted endpoints and confirm each goes through `apiService`.
3. Smoke-test the running app (owner happy path + a member happy path) after conversion.
4. Preserve the public share-link whitelist and add a regression test that these routes remain reachable without auth.

## Testing

First real backend authorization tests (`backend/tests/`):

- **Unit — `get_script_role`:** owner, member, viewer, non-member, and missing-script cases.
- **Decorator — `require_script_role`:** each rank boundary (e.g. viewer → write route = 403; member → read route = 200; non-member → 404/403; admin → manage = 200; member → manage = 403).
- **Regression:** share-link routes remain public (no auth → 200).
- **Teams Phase 2:** `accept_invite` rejects an email mismatch; role-change endpoint enforces admin + guardrails (cannot change owner, cannot elevate above self).

## Implementation phases

1. **Phase 1 — Access control:** build `authorization.py` (helper + decorator + role ladder), produce the full endpoint→bucket table, convert all script-scoped endpoints across the four route files, preserve the share-link whitelist, add authz tests, verify frontend callsites + smoke test.
2. **Phase 2 — Teams hardening:** invite email + template, invite-to-email binding, role-management endpoint + `TeamDrawer` role picker, Teams tests.

Phase 1 is a prerequisite for Phase 2 (Phase 2's endpoints use the new decorator).

## Open risks / notes

- `apply_revision_changes` re-extracts scenes via a simpler pipeline than main ingest (audit note) — out of scope here but flagged.
- Bulk AI analysis runs in an in-process daemon thread (not durable) — out of scope here; noted for a future reliability phase.
