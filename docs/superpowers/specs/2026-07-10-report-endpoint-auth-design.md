# Report Endpoint Auth Hardening — Design

**Date:** 2026-07-10
**Status:** Design approved, pending spec review
**Components:** `backend/routes/report_routes.py`, new `backend/utils/report_access.py`, `frontend/src/services/apiService.js`, `frontend/src/components/reports/ReportStudio.jsx`

## Problem

The report blueprint (`report_bp`, mounted at `/api/reports`) accesses the database with the Supabase **service-role key**, which bypasses Row-Level Security. Most of its data endpoints have **no authentication and no ownership check** — they are keyed only on a `script_id` or `report_id` (UUIDs). Anyone who knows or guesses an id can list, generate, preview, download, delete, or share another user's reports. This was flagged in the Report Studio final review as a pre-existing, blueprint-wide exposure.

The public sharing endpoints (`/shared/<token>/*`) are intentionally public — the unguessable share token is the capability — and must remain so.

## Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Access model | **Owner OR team member** — `scripts.user_id == user_id` OR a row in `script_members(script_id, user_id)` (any role) |
| Print/PDF (currently `window.open`, no JWT) | **Uniform authenticated fetch** — frontend fetches print/PDF via axios (JWT) as a blob, so every report endpoint can require auth uniformly |
| Public share links | Unchanged — stay public |
| Static metadata routes | Unchanged — stay public |

## Access model

Mirrors the owner-or-member check the invite routes already perform inline (`invite_routes.py:113-116`), extracted into one reusable, testable unit.

### New module: `backend/utils/report_access.py`

```
script_access(client, script_id, user_id) -> "ok" | "forbidden" | "not_found"
    - "not_found" if no scripts row with id == script_id
    - "ok" if scripts.user_id == user_id
    - "ok" if a script_members row exists for (script_id, user_id)
    - "forbidden" otherwise

report_script_id(client, report_id) -> script_id (str) | None
    - returns the report's script_id, or None if the report doesn't exist
```

`client` is the Supabase admin (service-role) client the report routes already use. The three-state return lets callers map cleanly to 404 vs 403.

(`invite_routes` can adopt `script_access` later to replace its inline check — out of scope for this change.)

## Endpoint treatment

All endpoints below already receive a JWT from the frontend axios instance (interceptor attaches `Authorization: Bearer` to every request), except print/PDF which are addressed in the Frontend section.

### Gate: `@require_auth` + script-keyed access check
Resolve `user_id = get_user_id()`, then `script_access(client, script_id, user_id)`; return 404 on `not_found`, 403 on `forbidden`, proceed on `ok`.

- `GET  /scripts/<script_id>/filter-options`
- `GET  /scripts/<script_id>/filter-presets` (upgrade from `@optional_auth`)
- `POST /scripts/<script_id>/filter-presets` (upgrade from `@optional_auth`)
- `GET  /scripts/<script_id>/reports`
- `POST /scripts/<script_id>/reports/generate`
- `POST /scripts/<script_id>/reports/preview`
- `POST /scripts/<script_id>/reports/preview-html`

### Gate: `@require_auth` + report-keyed access check
Resolve `script_id = report_script_id(client, report_id)`; 404 if `None`; else `script_access(client, script_id, user_id)` → 404/403/ok.

- `GET    /reports/<report_id>`
- `DELETE /reports/<report_id>`
- `GET    /reports/<report_id>/pdf`
- `GET    /reports/<report_id>/print`
- `POST   /reports/<report_id>/share`
- `DELETE /reports/<report_id>/share`

### Gate: `@require_auth` only (already user-scoped)
- `DELETE /filter-presets/<preset_id>` — the service method already filters the delete by `user_id`; add `@require_auth` (upgrade from `@optional_auth`) so an anonymous caller can't reach it.

### Unchanged — remain public
- `GET /shared/<share_token>`, `GET /shared/<share_token>/pdf`, `GET /shared/<share_token>/print` — public by design (token is the capability).
- `GET /templates`, `GET /templates/<template_id>`, `GET /report-types`, `GET /report-presets` — static metadata, no user data.

### Error semantics
- 401 — missing/invalid JWT (produced by `@require_auth`).
- 403 — authenticated but not owner/member (`{'success': False, 'error': 'Not authorized'}`).
- 404 — script or report does not exist.

## Frontend changes

The Download and Print buttons currently call `window.open(getReportPrintUrl(report.id))` — a browser navigation that sends no JWT. Once `/reports/<id>/print` requires auth, that breaks. Fix by fetching with the authenticated axios instance.

### `apiService.js`
- Add `openReportPrint(reportId)`: `api.get('/api/reports/reports/<id>/print', { responseType: 'blob' })` → `URL.createObjectURL(blob)` → `window.open(objectUrl, '_blank')`. Returns `{ success }` (or throws) so the caller can toast on failure. Revoke the object URL after a short delay.
- **Popup-blocker nuance:** `window.open()` called *after* an `await` is no longer inside the click gesture and browsers may block it. Mitigation: open the tab **synchronously** at the top of the click handler (`const win = window.open('', '_blank')`), then after the blob resolves set `win.location = objectUrl` (and `win.close()` + toast on failure). The helper therefore accepts a pre-opened window handle, or the component opens the window and the helper only fetches the blob + returns the object URL. The plan picks one; the requirement is that the print tab is opened in the user gesture, not after the await.
- Leave the existing `getReportPrintUrl` / `getReportPdfUrl` URL builders in place (still used to compute the path inside the helper / for any shared-route usage), but they are no longer opened directly for authenticated reports.

### `ReportStudio.jsx`
- `handleDownload` / `handlePrint` open the print tab synchronously in the click handler, then use `openReportPrint(report.id)` to fetch the blob and point the tab at it (both keep opening the printable HTML, as today); show a toast error and close the blank tab on failure.
- `SharedReportView.jsx` is **not** touched — it uses the public `/shared/<token>/*` routes.

## Testing

### Backend (pytest, monkeypatched module-level `report_service` / admin client, no real DB)
- `report_access.script_access`: owner → "ok"; member → "ok"; unrelated user → "forbidden"; unknown script → "not_found".
- `report_access.report_script_id`: returns the script_id for an existing report; `None` for a missing one.
- Route gating (representative): a non-owner/non-member gets **403** and the owner gets **200** on one script-keyed route (`GET /scripts/<id>/reports`) and one report-keyed route (`GET /reports/<id>/print`); an anonymous request (no auth) gets **401**.
- Regression: `GET /shared/<token>` still returns 200 with **no** auth header (public route unaffected).

### Frontend
- `npm run build` succeeds (`npm run lint` is pre-broken repo-wide — not a gate).
- Manual: while logged in, Download and Print still open the report; a logged-out/again-scoped attempt is rejected.

## Out of scope
- Migrating `invite_routes` to use the shared `script_access` helper.
- Making "Download" produce a real PDF instead of printable HTML (separate deferred item).
- Rate limiting / audit logging on report endpoints.
- Adding RLS policies (the service-role key bypasses RLS by design; app-layer checks are the mechanism here).
