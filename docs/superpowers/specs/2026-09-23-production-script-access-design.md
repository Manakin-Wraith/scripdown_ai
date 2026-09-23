# Production Script Access — Design

**Date:** 2026-09-23
**Status:** Design approved — spec reviewed against code 2026-09-23 (D1–D3 resolved)
**Type:** Architectural
**Parent:** `docs/superpowers/specs/2026-08-31-production-data-model-design.md`
**Amends:** `docs/superpowers/specs/2026-09-01-production-members-design.md`
(step 2b — reverses its "axes stay independent" decision)

## Purpose

Today SlateOne has two unrelated membership systems:

| | Script team (`script_members`) | Production members (`production_members`) |
|---|---|---|
| Added via | Script → Team Members drawer (`TeamDrawer.jsx`) | Production → Members tab |
| Grants | One script: breakdown, scenes, schedule, reports, notes | Production surfaces: Overview, Crew, Locations, Call Sheets |
| Roles | viewer / member / admin | viewer / coordinator / admin + capability flags |
| Checked by | `get_script_role` (`middleware/authorization.py`) | `production_authz` |

Step 2b deliberately gave production members **zero** script access. In
practice that is wrong: an owner who creates a production, attaches a script
and adds a line producer expects that person to get the breakdown and reports
too — not a 403 until they are invited a second time per script.

This design makes **the production the team**: production membership grants
access to every script attached to the production, controlled by one new
per-member setting. The per-script Team drawer remains only for scripts that
are **not** in a production (Solo users, one-off shares).

## Decisions (from brainstorm)

- **Production is the team; script team only for standalone scripts.**
  Scripts attached to a production are shared exclusively through the
  production's Members tab.
- **Per-member `script_access` level**, role-preset default, overridable per
  member — same "roles are presets, not cages" pattern as the existing
  capability flags.
- **Levels: `none` / `view` / `edit`.** No `manage` level: the only thing
  script `admin` adds over `member` is managing the script Team drawer, which
  no longer applies to production scripts. Delete / lock / unlock stay
  `owner`-only.
- **Resolved at check time, not synced.** `get_script_role` derives the role
  from `scripts.production_id` → `production_members.script_access`. No
  shadow `script_members` rows, so nothing can drift.
- **Attaching a script with existing team members prompts the owner** to move
  them into the production or drop them. Server-enforced.
- **Detaching lets the owner keep chosen members** on the script's own team.
- **Moving members bypasses the seat and Team-tier gates** (spec review D3).
  It relocates the same people; the seat count is unchanged, and a lapsed
  Team owner's script members already keep access today (`get_script_role`
  never checks entitlement).
- **`department_code` is not carried over** on a move (spec review D2).
  Moved members' notes fall back to the default `production` department
  like any other production-derived member. Department handling belongs to
  umbrella step 7.
- **Script pages hide edit controls for viewers** (spec review D1). Today
  the frontend never checks the script role (only `isOwner` in
  `ScriptHeader`), so viewers see edit buttons that 403. This feature puts
  many more people at View, so role-aware controls are in scope.

## Scope

**In:**

- Migration `056_production_script_access.sql`.
- `get_script_role` production-derived branch.
- `_user_can_access_script` and the other direct `script_members` queries
  listed under "Direct-query call sites".
- `script_access` in production member / invite create, update, accept, rank
  guardrail, and the member list payload.
- Attach (`members_action`) and detach (`keep_user_ids`) flow changes on
  `production_bp`, backed by `production_service`.
- Script invite routes refuse production scripts.
- Frontend: Members tab dropdown, attach/detach/delete-production dialogs,
  Team drawer replacement notice, My Scripts production badge, role-aware
  edit controls on script pages.
- Docstrings in `middleware/production_authz.py` and
  `services/production_member_service.py` that state production members get
  "zero script access" are rewritten.

**Out (deferred):**

- Department-scoped script access (makeup HOD sees only makeup) — umbrella
  step 7 / its own brainstorm.
- Per-script access within one production (member sees episode 1 but not 2).
- Script attach by non-owner production admins (attach stays owner-only; the
  script must be owned by the caller).
- Atomic attach+move via a Postgres RPC (idempotent Python steps chosen
  instead — see "Attach").

## Data model

Migration `backend/db/migrations/056_production_script_access.sql` (manual
apply, like 050–055):

```sql
ALTER TABLE production_members
  ADD COLUMN IF NOT EXISTS script_access text NOT NULL DEFAULT 'none'
  CHECK (script_access IN ('none','view','edit'));

ALTER TABLE production_invites
  ADD COLUMN IF NOT EXISTS script_access text NOT NULL DEFAULT 'none'
  CHECK (script_access IN ('none','view','edit'));

-- Backfill from role presets
UPDATE production_members SET script_access = 'edit'
  WHERE role IN ('admin','coordinator');
UPDATE production_members SET script_access = 'view'
  WHERE role = 'viewer';
UPDATE production_invites SET script_access = 'edit'
  WHERE role IN ('admin','coordinator') AND status = 'pending';
UPDATE production_invites SET script_access = 'view'
  WHERE role = 'viewer' AND status = 'pending';
```

`script_access` is a **level**, not a boolean, so it is **not** added to the
`CAPABILITIES` tuple in `production_authz.py`. It is handled alongside it.

### Role presets

| Role | `script_access` default |
|---|---|
| admin | `edit` |
| coordinator | `edit` |
| viewer | `view` |

### Level ↔ script role mapping

```python
SCRIPT_ACCESS_RANK = {'none': 0, 'view': 1, 'edit': 2}
SCRIPT_ACCESS_TO_ROLE = {'view': 'viewer', 'edit': 'member'}   # none → no access
SCRIPT_ROLE_TO_ACCESS = {'viewer': 'view', 'member': 'edit', 'admin': 'edit'}
```

Both live in `middleware/production_authz.py` (the production-axis module)
and are imported by `authorization.py` and the services.

## Authorization

### `get_script_role(script_id, user_id)`

Resolution order:

1. Script missing → `SCRIPT_NOT_FOUND`.
2. `scripts.user_id == user_id` → `'owner'`.
3. Direct role = `script_members.role` for `(script_id, user_id)` (if any).
4. If `scripts.production_id` is set: production role =
   `SCRIPT_ACCESS_TO_ROLE[production_members.script_access]` for
   `(production_id, user_id)` (if a row exists and access ≠ `none`).
5. Return the **higher-ranked** of direct and production role (by
   `ROLE_RANK`), or `None` if neither.

The existing `scripts` lookup extends its select to `user_id, production_id`,
so the production branch costs one extra query only when the caller is neither
owner nor (for a standalone script) a direct member. A production owner who is
not the script owner cannot occur: attach requires `scripts.user_id ==
productions.owner_id`.

`require_script_role` and every route using it pick this up with no change.

### Direct-query call sites

These bypass `get_script_role` and query `script_members` directly. Each must
also include production-derived access:

| Location | What it does | Change |
|---|---|---|
| `routes/supabase_routes.py:169` (`GET /api/scripts`) | "Shared with me" scripts | Also include scripts whose `production_id` is in the caller's `production_members` rows with `script_access <> 'none'`. Reuse the existing payload shape (`is_owner: false`, `membership: {...}`, which `ScriptTable` already renders as a "Shared" badge): `membership` gets `role` = the mapped script role plus `via_production: {id, title}`; `department_code` is null. |
| `routes/supabase_routes.py:4923` `_user_can_access_script` | Access check for routes at 5060/5129/5175/5198 | Replace the inline owner/member logic with `get_script_role(...) not in (None, SCRIPT_NOT_FOUND)`; keep the legacy-null-owner and superuser branches. |
| `routes/supabase_routes.py:5582` (`/api/scripts/locations/health-counts`) | Collects the caller's accessible script ids | Same production-derived union as `GET /api/scripts`. |

Put the union in one helper — `accessible_script_ids(user_id)` in
`middleware/authorization.py` — returning `{script_id: source}` for owned,
direct-member, and production-derived scripts, and use it at 169 and 5582.

Also not changed: `GET /api/scripts/<id>/my-membership`
(`invite_routes.py:737`) reads `script_members` directly and will report
`membership: null` for production-derived members. No frontend code calls
it; leave it and note it in its docstring.

Not changed: `entitlement_service` seat counting (already a unified
person-count across both tables; moving someone from `script_members` to
`production_members` leaves the count unchanged); `analytics_service`; the
department auto-detect in notes (production-derived members have no
`department_code` and fall back to the existing default).

### Script invite routes

`POST /api/scripts/<script_id>/invites` (`create_invite`, the only way to
add a script member) returns **409**
`{error: 'Access to this script is managed by its production', code:
'managed_by_production', production_id}` when `scripts.production_id` is set.
Listing, role change and removal keep working so any leftover direct rows
stay manageable. Production-derived roles top out at `member`, so they can
never pass `create_invite`'s `require_script_role('admin')` anyway — only the
owner reaches the new 409.

### Rank guardrail

`production_member_service.rank_ok` gains one rule: a non-owner actor may
not assign a `script_access` whose rank exceeds their own `script_access`.
Applies to add, update and invite.

## Member lifecycle changes

In `services/production_member_service.py`:

- `ROLE_PRESETS` gains `script_access` per role; `apply_role_preset` applies
  an overriding `script_access` if supplied and valid (else 400).
- `add_member` and invite creation persist `script_access`.
- `update_member` follows the existing flag behaviour: on a role change it
  keeps the member's current `script_access` unless one is explicitly sent
  (presets are re-applied by the frontend form, not the server).
- `accept_invite` copies `script_access` from the invite to the member row.
- `_member_view` / `_invite_view` include `script_access`.
- `get_production_access` returns `script_access` alongside the capability
  flags (owner → `'edit'`).

## Attach

`POST /api/productions/<production_id>/scripts` — owner only (unchanged).
Body: `{script_id, members_action?: 'move' | 'drop'}`.

"Live pending invite" below means `status = 'pending' AND expires_at >
now()`; expired pending invites are ignored by the check and revoked
silently in both branches.

1. Load the script's `script_members` and live pending `script_invites`.
2. If either is non-empty and `members_action` is absent → **409**
   `{code: 'script_has_members', members: [{user_id, name, email, role}],
   invites: [{email, role}]}`. Nothing is written.
3. Run the existing single conditional attach
   (`UPDATE scripts SET production_id = :pid WHERE id = :sid AND user_id =
   :caller AND production_id IS NULL`). Zero rows → existing **409**
   'Script already belongs to a production' — before any member is touched.
4. **Re-read** the script's `script_members` and live pending invites. An
   invite created between steps 1 and 3 is then moved or dropped like the
   rest instead of being silently deleted; from step 3 on, `create_invite`
   refuses new ones.
5. `members_action == 'move'` — done by a dedicated service function
   (`move_script_team_to_production`), **not** through `add_member`: it
   bypasses the `can_use_teams` and `seats_used >= seats_paid` gates (see
   D3) because it relocates people already counted.
   - For each script member:
     - Not yet a production member → upsert `production_members` with role
       `viewer`, viewer capability preset, `script_access =
       SCRIPT_ROLE_TO_ACCESS[role]`, `invited_by = caller`. Fire the
       existing member-added notification + email.
     - Already a production member → raise `script_access` to
       `max(existing, mapped)`; never lower it; production role untouched.
   - For each live pending script invite: create a `production_invites` row
     (viewer, mapped `script_access`, new token, 14-day expiry) unless a
     pending production invite for that email already exists (then raise its
     `script_access` the same way); send the production invite email; set
     the script invite to `revoked` **directly** (not via
     `invite_routes.revoke_invite`, which emails "your invitation was
     withdrawn" — contradicting the new invite sent the same moment).
   - Delete the script's `script_members` rows **last**.
6. `members_action == 'drop'`: delete the script's `script_members` rows and
   revoke its live pending `script_invites` **with** the existing
   withdrawn-invite email (`send_invite_revoked`), since those people really
   are losing access.

**Failure handling.** supabase-py has no transactions. Every step in 5 is
idempotent (upsert on `(production_id, user_id)`, pending-invite unique index,
raise-only updates), and deletes run last, so a retry after a partial failure
converges. The worst intermediate state is a leftover direct row, which is
harmless: `get_script_role` takes the higher role. Errors are logged and
surfaced as 500 with the script already attached; the frontend offers
"Retry moving members", which re-sends the same request. `add_script`
currently returns `'conflict'` for both "in another production" and "already
in this one"; it gains a third outcome `'already_attached'` (re-read
`scripts.production_id == :pid` after a zero-row update), which the route
treats as success and continues to step 4.

Response: `{success: true, moved_members: n, moved_invites: n}` (extends the
current `{success: true}`).

## Detach

`DELETE /api/productions/<production_id>/scripts/<script_id>` — owner only.
Optional body `{keep_user_ids: [uuid]}`.

1. Existing conditional clear of `scripts.production_id`.
2. For each id in `keep_user_ids` that is a production member with
   `script_access <> 'none'`: upsert a `script_members` row with role
   `SCRIPT_ACCESS_TO_ROLE[script_access]`. Ids that don't qualify are ignored.

Everyone else loses access immediately (derived access simply stops
resolving).

**Delete production:** unchanged mechanics (`ON DELETE SET NULL` on scripts,
member rows cascade). No keep-prompt; the confirmation copy warns.

## Frontend

All calls through `services/apiService.js`.

- **`ProductionMembersTab`** — "Script access" select (None / View / Edit) on
  each member row and in the add/invite form; populated from the role preset
  when the role changes; options above the actor's own level disabled for
  non-owners. Helper line: "Script access applies to all scripts in this
  production (N)."
- **`ProductionScriptPicker`** — on 409 `script_has_members`, a confirm step
  listing members and pending invites with **Move to production** (primary)
  and **Remove their access**; re-submits with `members_action`. On 500 after
  attach, show "Retry moving members".
- **Detach confirm** (production Overview) — lists members with script
  access, each with an unticked "Keep on script" checkbox; sends
  `keep_user_ids`.
- **Delete production confirm** — adds "N members will lose access to M
  scripts."
- **Production Overview scripts list** — members see the attached scripts
  they can open. Members with `none` see **no** scripts: `_accessible_scripts`
  (`production_service.py:84`) already drops scripts the caller has no role
  on, and that stays as is. If a `none` member has no scripts, the list shows
  "No scripts shared with you in this production."
- **`ProductionDetailPage`** — read an optional `?tab=` query param on load
  (validated against the tabs visible to the caller, falling back to
  `overview`) so the Team drawer notice can deep-link to Members. Today the
  page ignores the query string.
- **`TeamDrawer`** — when the script has `production_id`, render a notice
  instead of the member list: "Access for this script is managed in
  **{production title} → Members**", linking to
  `/productions/:id?tab=members` for owners and members who can manage
  members, plain text otherwise. The notice renders **before** the existing
  `hasTeamAccess` "Team Collaboration Locked" gate (that gate reads the
  *viewer's* own entitlement, which a production member usually lacks). The
  `resume_invite` seat-purchase flow in `ScriptHeader` skips reopening the
  invite modal for production scripts.
- **Script metadata** — `GET /api/scripts/<id>/metadata` adds `production_id`,
  `production_title` (null when standalone) and `my_role` (from
  `g.script_role`, which `require_script_role` already sets). `TeamDrawer`
  and the role-aware controls read these.
- **My Scripts (`ScriptTable`)** — production-derived scripts reuse the
  existing "Shared" badge; the tooltip reads "Shared via {production title} —
  role: {role}" when `membership.via_production` is present.
- **Role-aware edit controls (D1)** — new `useScriptRole()` hook (reads
  `my_role` from the script metadata; exposes `canEdit = rank >= member`).
  Viewers get read-only versions of the script pages: edit, add, delete,
  drag-to-reorder and "run analysis" controls are hidden or disabled with a
  "View only" hint. The implementation plan enumerates the exact components
  by grepping the script-page write calls in `apiService.js` back to their
  callers (breakdown/scene editing, stripboard/schedule, story days, notes,
  report config save). Owner-only controls keep their existing `isOwner`
  checks. The backend `require_script_role` checks stay the real
  enforcement; this is UX only.

## Testing

Backend (`pytest tests/`), new `tests/test_production_script_access.py` plus
additions to existing production member / invite tests:

- `get_script_role`: owner; direct member; production `edit` → `member`;
  `view` → `viewer`; `none` → `None`; direct + production → higher wins;
  standalone script ignores production rows; member removed → `None`;
  script detached → `None`; missing script → `SCRIPT_NOT_FOUND`.
- Attach: 409 `script_has_members` without action (nothing written);
  expired pending invites don't trigger it; move — new person inserted as
  viewer with mapped access; existing member's access raised, never lowered,
  role untouched; pending invites converted + production invite email sent +
  script invite revoked **without** a withdrawn email; script rows deleted;
  move succeeds when `seats_used == seats_paid` and when the owner lacks
  `can_use_teams`; drop — rows deleted, invites revoked **with** withdrawn
  email; attach to a script already in another production → 409 before
  member changes; retry after partial failure → `already_attached` treated
  as success and converges.
- Detach: without `keep_user_ids` everyone loses access; with it, kept users
  get the mapped direct role; ineligible ids ignored.
- Script invite create on a production script → 409.
- Rank guardrail: non-owner cannot grant higher `script_access` than own.
- Invite accept copies `script_access`.
- `GET /api/scripts` and location health counts include production-derived
  scripts (with `membership.via_production`); `_user_can_access_script`
  routes allow a production `view` member.
- Script metadata returns `my_role`, `production_id`, `production_title`.
- `update_member` role change without `script_access` keeps the current
  value.
- Migration backfill mapping (assert via service defaults on fixtures; the
  SQL itself is applied manually).

Frontend: `npm run build` (lint is broken repo-wide).

Manual: owner creates a production, attaches a script with one existing team
member → move prompt → member appears in Members tab with Edit; invites Jane
as viewer → Jane opens the breakdown and reports with edit controls hidden;
owner sets Jane to None → 403 on the script; detach with Jane kept → Jane's
access returns via the script Team drawer.
