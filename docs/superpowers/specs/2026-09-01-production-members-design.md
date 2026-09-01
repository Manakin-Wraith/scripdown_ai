# Production Members — Build-Sequence Step 2b Design

**Date:** 2026-09-01
**Status:** Design approved — ready for implementation plan
**Type:** Architectural
**Parent:** `docs/superpowers/specs/2026-08-31-production-data-model-design.md`
(umbrella direction spec — build-sequence step 2, second half)
**Sibling:** `docs/superpowers/specs/2026-08-31-crew-contacts-design.md`
(step 2a — shipped the data half, owner-only)

## Purpose

Step 2a shipped `contacts` + `production_crew` + CSV import as an
**owner-only** slice: sensitive fields (phone, rates) are stored but
ungated because the owner is the only viewer, the Crew tab is hidden for
non-owner viewers, and `/contacts` is absent from their nav.

Step 2b makes a production **shareable**. It introduces the additive
`production_members` permission layer the umbrella spec reserved: a line
producer, coordinator, or department-lead viewer can be added to a
production, open its workspace, and (per their role and per-member
permission toggles) read or edit the crew roster — without gaining any
access to the underlying scripts' breakdowns, scenes, or reports.

This is the first surface worth gating, and the layer every later
production surface (locations, call sheets, production-level schedule,
DPR) will build against.

## Scope

**In:**

- Migration `052_production_members.sql` (manual apply — `run_migration.py`
  is dead): `production_members`, `production_invites`.
- New `backend/middleware/production_authz.py` — the production-axis
  authorization primitive (`get_production_role`, `get_production_access`,
  `require_production_role`, resolvers).
- Member + invite lifecycle routes on the existing `production_bp`, backed
  by a new `services/production_member_service.py`.
- Server-side redaction of sensitive fields in the crew payload for
  members without `can_view_sensitive`.
- `_fetch_seats_used` extended to count production members + pending
  production invites (unified person-count across both membership
  systems).
- Crew routes re-gated from the 2a `_user_owns_production` guard to
  `require_production_role`.
- `GET /api/productions/:id` gains `production_access`; `list_productions`
  and `get_production_for_viewer` include productions the caller is a
  **member** of.
- Frontend: Crew tab visible to all members (write controls gated); new
  **Members** tab; production-invite accept page; `apiService.js`
  additions.
- Email templates + notification types for member-added / invited /
  accepted, mirroring `invite_routes.py`.

**Out (named, deferred):**

- **Department-scoped access for *script* members** (the "makeup HOD sees
  only makeup reports" case). This is a change to the existing
  `script_members` system — `script_members.department_code` is captured
  today but gates nothing — and belongs to umbrella **step 7 (Department
  Workspaces)** or its own brainstorm. `script_members`,
  `get_script_role`, and every report/breakdown route are **untouched** in
  2b.
- **Permission inheritance between axes.** A production member gets **zero**
  script access; a script member gets no production write access (the
  spine's existing script-member read-through to production Overview is
  unchanged). `get_script_role` is not modified.
- `locations` / `production_locations` and their member gating → step 3
  (they add their own capability columns to `production_members` then).
- Production-level schedule / call sheets / DPR gating → steps 4–6 (same:
  new capability columns as they ship).
- Non-owner access to the global `/contacts` directory page → never (see
  "Directory scope").
- AI-parse of uploaded call sheets → deferred (umbrella spec).

## Decisions carried from the brainstorm

- **Membership mechanism:** one unified email-based "Add member" flow.
  If the email matches a `profiles` row the person becomes a member
  immediately (notification + email); otherwise a pending
  `production_invites` row is created with a token that resolves on
  signup / next login. Reuses the `script_invites` infrastructure
  patterns (token, expiry, accept, auto-accept, email, notifications).
- **Axes stay independent** — production membership governs
  production-level surfaces only.
- **Seats:** unified person-count. One person who is both a script member
  and a production member on the same account consumes **one** seat.
- **Directory scope:** a non-owner member sees contact details **only**
  through crew assignments on productions they belong to (embedded in the
  crew payload). The `/contacts` page stays owner-only and never appears
  in a member's nav.
- **Permission model:** roles are **presets** that fill in a bundle of
  boolean capability flags; the owner or a member with `can_manage_members`
  can then override individual flags per member. Roles are a starting
  point, not a cage.
- **Redaction is server-side** — the API omits sensitive fields entirely
  for members without `can_view_sensitive`; it is not a UI-only hide.
- **Member management** is available to the owner **and** to members with
  `can_manage_members` (an `admin` by default), with rank guardrails
  mirroring the script-side `update_member_role`.

## Roles and capabilities

Three roles on production-level surfaces: **`admin`** (line producer),
**`coordinator`**, **`viewer`**. `owner` is not a stored role — it is
`productions.owner_id` and short-circuits every check to all-true.

`ROLE_RANK = {'viewer': 1, 'coordinator': 2, 'admin': 3, 'owner': 4}`.

Four capability flags, each a real boolean column on `production_members`.
Role presets set the defaults; each is independently overridable:

| Capability | Gates | admin | coordinator | viewer |
|---|---|---|---|---|
| `can_view_sensitive` | `contacts.phone`, `contacts.standard_rate`, `production_crew.job_rate` in the crew payload | `true` | `false` | `false` |
| `can_edit_crew` | add / edit / remove crew assignments, CSV import | `true` | `true` | `false` |
| `can_manage_members` | add / remove / re-role members, revoke invites | `true` | `false` | `false` |
| `can_edit_production` | edit Overview (title, dates, status), add / remove scripts | `true` | `false` | `false` |

Every role can **view** the Crew tab and the production Overview.

**Rank guardrail:** a member with `can_manage_members` may not create or
edit a member whose `role` outranks their own, may not grant a capability
flag they do not themselves hold, and may not modify or remove a member
ranked greater than or equal to themselves (mirrors
`invite_routes.update_member_role`). The `owner` is never a
`production_members` row and cannot be targeted.

**Later production surfaces** (locations, schedule, call sheets, DPR) add
their own capability columns to `production_members` as they ship — the
column-per-flag shape is chosen so that additions are additive migrations,
not a JSONB reshape.

## Data model

Migration `backend/db/migrations/052_production_members.sql`. Mirrors the
`050` / `051` conventions: `gen_random_uuid()` pks, manual apply,
`update_shooting_updated_at()` trigger reuse (migration 030), owner-only
RLS as a direct-client backstop only. Real enforcement is Python +
service-role key.

### `production_members`

| Column | Type | Notes |
|---|---|---|
| `id` | uuid pk | `default gen_random_uuid()` |
| `production_id` | uuid not null | `REFERENCES productions(id) ON DELETE CASCADE` |
| `user_id` | uuid not null | `REFERENCES auth.users(id) ON DELETE CASCADE` |
| `role` | text not null | `CHECK (role IN ('admin','coordinator','viewer'))` |
| `can_view_sensitive` | boolean not null | `default false` |
| `can_edit_crew` | boolean not null | `default false` |
| `can_manage_members` | boolean not null | `default false` |
| `can_edit_production` | boolean not null | `default false` |
| `invited_by` | uuid null | `REFERENCES auth.users(id) ON DELETE SET NULL` |
| `created_at` | timestamptz not null | `default now()` |
| `updated_at` | timestamptz not null | `default now()`; `BEFORE UPDATE` trigger reusing `update_shooting_updated_at()` |

Constraints / indexes:
- `UNIQUE (production_id, user_id)` — one membership row per person per
  production.
- `idx_production_members_production ON production_members(production_id)`
- `idx_production_members_user ON production_members(user_id)` — the seat
  count and "productions I belong to" both filter on `user_id`.

Capability defaults are **not** enforced by the DB against `role` — the
service layer applies presets on insert; the columns default `false` so a
bare insert is safe.

### `production_invites`

Mirrors `script_invites` (`email`-keyed, token, expiry, status). Stores
the resolved capability flags so an owner's per-invite customization
survives acceptance.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid pk | `default gen_random_uuid()` |
| `production_id` | uuid not null | `REFERENCES productions(id) ON DELETE CASCADE` |
| `email` | text not null | stored lowercased / trimmed |
| `role` | text not null | `CHECK (role IN ('admin','coordinator','viewer'))` |
| `can_view_sensitive` | boolean not null | `default false` |
| `can_edit_crew` | boolean not null | `default false` |
| `can_manage_members` | boolean not null | `default false` |
| `can_edit_production` | boolean not null | `default false` |
| `token` | text not null | `UNIQUE`; `generate_invite_token()` reuse |
| `status` | text not null | `default 'pending'`, `CHECK (status IN ('pending','accepted','revoked'))` |
| `invited_by` | uuid null | `REFERENCES auth.users(id) ON DELETE SET NULL` |
| `expires_at` | timestamptz not null | 14 days out |
| `created_at` | timestamptz not null | `default now()` |

Constraints / indexes:
- `idx_production_invites_token ON production_invites(token)`
- `idx_production_invites_production_status ON production_invites(production_id, status)`
- `idx_production_invites_email ON production_invites(lower(email))` — seat
  count over pending invites.
- Partial unique guard on one *pending* invite per (production, email):
  `CREATE UNIQUE INDEX uq_production_invites_pending ON production_invites(production_id, lower(email)) WHERE status = 'pending';`
  A second POST for the same pending email → 409 (route-level friendly
  message; the index is the backstop).

### RLS

```sql
ALTER TABLE production_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE production_invites ENABLE ROW LEVEL SECURITY;

CREATE POLICY "owner manages production members"
    ON production_members FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = production_members.production_id
                  AND p.owner_id = auth.uid())
    );

CREATE POLICY "member reads own membership row"
    ON production_members FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "owner manages production invites"
    ON production_invites FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = production_invites.production_id
                  AND p.owner_id = auth.uid())
    );
```

Backstop only — the backend uses the service-role key.

### User deletion

`013_delete_user_safely.sql` deletes `scripts` then `profiles`, with
`productions.owner_id ON DELETE CASCADE` clearing the deleted owner's
productions (and, via `production_id ON DELETE CASCADE`,
`production_members` / `production_invites` / `production_crew`).
Separately, a deleted user who was a **member** of *someone else's*
production is cleared by `production_members.user_id ON DELETE CASCADE`
and `invited_by ON DELETE SET NULL`. No FK error in either direction.
Migration 052 carries a comment stating this.

## Authorization layer

**New `backend/middleware/production_authz.py`** — parallel to
`middleware/authorization.py`, deliberately not merged into it (the
production axis is independent; keeping the modules separate keeps each
readable).

```python
ROLE_RANK = {'viewer': 1, 'coordinator': 2, 'admin': 3, 'owner': 4}
PRODUCTION_NOT_FOUND = object()   # 404 vs 403 sentinel

def get_production_role(production_id, user_id):
    """'owner' | 'admin' | 'coordinator' | 'viewer' | None | PRODUCTION_NOT_FOUND"""

def get_production_access(production_id, user_id):
    """{'role', 'can_view_sensitive', 'can_edit_crew',
        'can_manage_members', 'can_edit_production'}
       — owner short-circuits to all-true; a member returns its row's flags;
         non-member returns None; missing production returns PRODUCTION_NOT_FOUND."""
```

**Decorator** `require_production_role(min_role=None, capability=None,
resolver=from_production_id)` — stack below `@require_auth`:

1. `user_id = get_user_id()` — 401 if absent.
2. `production_id = resolver(kwargs)` — 404 if `None`.
3. `access = get_production_access(production_id, user_id)`.
   - `PRODUCTION_NOT_FOUND` → 404.
   - `None` → 403.
4. If `min_role` given and `ROLE_RANK[access['role']] < ROLE_RANK[min_role]`
   → 403.
5. If `capability` given and `access[capability]` is not `True` → 403.
6. `g.production_access = access`; `g.resolved_production_id = production_id`.
7. Sets `wrapper._authz_capability` / `_authz_min_role` introspection
   markers (mirrors the script decorator's `_authz_min_role`, for the
   route-enforcement test).

**Resolvers** (in `production_authz.py`):
- `from_production_id(kwargs)` → `kwargs.get('production_id')` (URL is
  `/api/productions/<production_id>/...`).
- `from_crew_id(kwargs)` → `production_crew.production_id` for
  `kwargs['crew_id']` (one hop).
- `from_member_id(kwargs)` → `production_members.production_id` for
  `kwargs['member_id']`.
- `from_production_invite_id(kwargs)` → `production_invites.production_id`
  for `kwargs['invite_id']`.

### Crew routes — re-gated

The 2a crew routes currently call `production_service._user_owns_production`
inline. They move to the decorator:

| Route | 2a guard | 2b guard |
|---|---|---|
| `GET /api/productions/:id/crew` | owner-only | `require_production_role('viewer')` |
| `POST /api/productions/:id/crew` | owner-only | `require_production_role(capability='can_edit_crew')` |
| `PATCH /api/productions/:id/crew/:crewId` | owner-only | `require_production_role(capability='can_edit_crew', resolver=from_crew_id)` |
| `DELETE /api/productions/:id/crew/:crewId` | owner-only | `require_production_role(capability='can_edit_crew', resolver=from_crew_id)` |
| `POST /api/productions/:id/crew/import` | owner-only | `require_production_role(capability='can_edit_crew')` |

`_user_owns_production` stays for the spine's own owner-only routes
(create / delete / list-owned).

### Redaction

`production_crew_service.list_crew(production_id, *, can_view_sensitive)`
gains the keyword. When `False`, each returned row is stripped of:
- `job_rate` (the assignment's rate)
- `contact.phone`
- `contact.standard_rate`

`job_rate_unit` / `rate_unit` are **kept** (a unit with no number leaks
nothing). The `GET .../crew` route passes
`g.production_access['can_view_sensitive']`.

`add_crew` / `update_crew`: when the caller's
`g.production_access['can_view_sensitive']` is `False`, the service
**drops** `job_rate` from the incoming payload before the write (a
coordinator who cannot see the rate must not blank or overwrite it).
`POST /api/contacts` is unreachable for non-owners, so contact-side
sensitive writes need no extra guard.

## Seat accounting

`entitlement_service._fetch_seats_used(owner_id)` today unions:
- accepted `script_members.user_id` where `invited_by == owner_id`
- pending `script_invites.email` where `invited_by == owner_id`, unexpired

It gains two sources, folded into the **same** `accepted_ids` /
`pending_emails` sets before the existing email↔user_id dedup runs:

- **Accepted production members:** `production_members.user_id` for every
  `production_members` row whose `production_id` belongs to a production
  with `owner_id == owner_id`. Implemented as: fetch this owner's
  `productions.id` list, then `production_members.select('user_id').in_('production_id', ids)`.
  Add to `accepted_ids`.
- **Pending production invites:** `production_invites.email` (status
  `pending`, `expires_at > now`) for those same production ids. Add to
  `pending_emails`.

Result: a person who is a script member **and** a production member on the
same account is one entry in `accepted_ids` → **one seat**. A pending
production invite to an email that is already an accepted member anywhere
under this owner → **zero** additional seats (existing `new_pending`
subtraction).

`_fetch_seats_paid` is unchanged.

### Invite / add gate

Adding a member or creating a production invite must check the **production
owner's** entitlement — *not* the caller's (a production `admin` doing the
add may not be the account owner and may not personally hold Tier 2).

`production_member_service.add_member(...)`:
1. Resolve `owner_id = productions.owner_id` for the target production.
2. `ent = get_entitlement(owner_id)`.
   - `not ent['can_use_teams']` → 403 `{code: 'tier_2_required'}`
     (owner's license lapsed / absent).
   - `ent['seats_used'] >= ent['seats_paid']` → 402
     `{code: 'no_seats_available'}` (mirrors `invite_routes` line 69–72).
3. Proceed with the immediate-add or pending-invite branch.

This mirrors the script path's `require_team_tier` + inline seat check,
but keyed to the owner.

## Backend API

All routes on the existing `production_bp` (no new blueprint — members are
a facet of a production, like crew). Backed by
`backend/services/production_member_service.py`.

| Method / path | Guard | Behavior |
|---|---|---|
| `GET /api/productions/:id/members` | `require_production_role('viewer')` | `{members: [{id, user_id, name, email, role, can_view_sensitive, can_edit_crew, can_manage_members, can_edit_production, created_at}], invites: [{id, email, role, ...flags, expires_at, created_at}]}`. Invites list only `status='pending'`. |
| `POST /api/productions/:id/members` | `require_production_role(capability='can_manage_members')` + owner-entitlement gate | Body `{email, role, can_view_sensitive?, can_edit_crew?, can_manage_members?, can_edit_production?}`. `email` required, lowercased/trimmed. `role` in the CHECK set → else 400. Omitted flags filled from the role preset. **Rank guardrail** against `g.production_access`. Then: **match `profiles` by `lower(email)`** → if found, insert `production_members` (409 if `UNIQUE` hit → "already a member"), fire notification + `production_member_added` email, return `201 {member}`. **Else** insert `production_invites` (409 on the pending partial-unique index), send `production_invite` email, return `201 {invite}`. |
| `PATCH /api/productions/:id/members/:memberId` | `require_production_role(capability='can_manage_members', resolver=from_member_id)` | Body: any of `role` + the four flags. Rank guardrail: target's current role and the *new* role must both be `< ` caller's rank (owner unrestricted); a flag may only be set that the caller holds. 404 if the row isn't on this production. `200 {member}`. |
| `DELETE /api/productions/:id/members/:memberId` | same | Rank guardrail (can't remove a peer/superior). Deletes the row; frees the seat on the next `get_entitlement`. No-match → `200` no-op (mirrors `remove_script`). |
| `DELETE /api/production-invites/:inviteId` | `require_production_role(capability='can_manage_members', resolver=from_production_invite_id)` | Sets `status='revoked'`. `200`. |
| `GET /api/production-invites/token/:token` | public (no auth) | `{production_title, inviter_name, role, email, expired: bool, status}` for the accept screen. Unknown token → 404. |
| `POST /api/production-invites/token/:token/accept` | `@require_auth` | Validates: token exists, `status='pending'`, not expired, and `auth.users` email == invite email (case-insensitive) → else 403 `{code}`. Inserts `production_members` with the invite's stored role + flags; marks invite `accepted`. Already a member (UNIQUE) → still mark accepted, return `200 {member, already_member: true}`. Fires an `invite_accepted`-style notification to `invited_by`. |

**Auto-accept:** extend the existing `/api/invites/auto-accept`
(`invite_routes.auto_accept_pending_invites`) — or add a parallel block in
the same handler — to also apply pending `production_invites` matching the
caller's email on first login. Same shape as the script branch.

`services/production_member_service.py`:
`list_members_and_invites(production_id)`,
`add_member(production_id, actor_access, fields)` →
`{'member': ...}` | `{'invite': ...}` | `('error', code, status)`,
`update_member(production_id, member_id, actor_access, fields)`,
`remove_member(production_id, member_id, actor_access)`,
`revoke_invite(invite_id)`,
`get_invite_by_token(token)`,
`accept_invite(token, user_id, user_email)`,
`_apply_role_preset(role, overrides) -> dict` (the four-flag bundle),
`_rank_ok(actor_access, target_role, new_flags) -> bool`.

### `GET /api/productions/:id` — additive field

Adds `production_access: {role, can_view_sensitive, can_edit_crew,
can_manage_members, can_edit_production}` next to the existing `is_owner`
(added in 2a). Owner → all-`true` with `role: 'owner'`. A non-member with
only the script read-through → `role: null`, all flags `false`
(`is_owner: false`), matching today's Overview-only view. The frontend
drives tab visibility and control enablement off this object;
`is_owner` is retained (some 2a call sites still read it) but new code
should prefer `production_access`.

### `list_productions` / `get_production_for_viewer`

- `list_productions(user_id)` (spine, `production_service`): currently
  `productions WHERE owner_id = user_id`. Extend to **union** productions
  where the user has a `production_members` row. Owned rows carry
  `is_owner: true`; member rows carry the member's `role`. One extra query
  (`production_members.select('production_id, role').eq('user_id', ...)`,
  then `productions.in_('id', ids)`), merged and de-duplicated.
- `get_production_for_viewer(production_id, user_id)`: the "exists but
  caller has no way in" branch (returns `None` today when not owner and no
  visible scripts) now also admits a `production_members` row. Order of
  checks: owner → member → script read-through → `None`.

## Frontend

### `services/apiService.js`

Through the single axios instance:
`listProductionMembers(prodId)`, `addProductionMember(prodId, payload)`,
`updateProductionMember(prodId, memberId, payload)`,
`removeProductionMember(prodId, memberId)`,
`revokeProductionInvite(inviteId)`,
`getProductionInvite(token)`, `acceptProductionInvite(token)`.

### `ProductionDetailPage.jsx`

- Reads `production_access` from the `GET /api/productions/:id` payload
  into page state.
- Tab strip (from 2a: **Overview | Crew**) gains **Members**, shown when
  `production_access.can_manage_members || production_access.role === 'owner'`.
  (Locations / Schedule / Call Sheets still appear as their slices ship.)
- Overview edit controls: gate on `production_access.can_edit_production`
  (2a gated on `is_owner`; switch to the flag).
- Opens for a production **member** now, not just owner + script
  read-through (backend change above makes the payload return).

### `components/productions/ProductionCrewTab.jsx`

- No longer owner-hidden — rendered for every role.
- "Add crew" / "Import CSV" / row edit + remove controls render only when
  `production_access.can_edit_crew`.
- Rate / phone columns: simply render whatever the payload contains —
  absent for a redacted viewer, so no conditional needed beyond
  null-safety. A short "— (hidden)" placeholder where a value would be, so
  the omission is legible rather than looking like missing data.

### `components/productions/ProductionMembersTab.jsx` (new)

- Members table: name, email, role `<select>`, four capability checkboxes
  inline, remove button. Editing role/flags → `PATCH`; disabled for rows
  ranked ≥ the current user (guardrail mirrored client-side for UX; server
  is the enforcement).
- Pending-invites list: email, role, sent date, "Revoke".
- "Add member" modal: email input, role `<select>`, an "Advanced
  permissions" disclosure with the four checkboxes (pre-checked from the
  role preset, live-updating when role changes until the user touches
  one). Submit → `addProductionMember`; on `no_seats_available` /
  `tier_2_required` show the same messaging the script `TeamManagement`
  flow uses.
- Mirrors the existing script `TeamDrawer.jsx` / `InviteModal.jsx`
  component structure and `ProductionPages.css` tokens.

### `ProductionInviteAccept.jsx` (new)

- Route `/production-invites/:token` (public shell; prompts login if
  needed, mirroring the script `InvitePage.jsx` accept page).
- Calls `getProductionInvite(token)` for the summary card (production
  title, inviter, role), `acceptProductionInvite(token)` on confirm, then
  redirects to `/productions/:id`.
- Handles expired / revoked / wrong-email / already-member states with the
  same copy patterns as the script accept page.

### Nav

No new top-level nav item. `/productions` already lists productions; it
now also lists productions the user is a member of (backend change). The
list row shows a small role badge for non-owned productions.

## Error handling

- **404 vs 403:** `PRODUCTION_NOT_FOUND` sentinel → 404; a real production
  the caller can't touch → 403. Never leak production existence to a
  non-member beyond what the spine already does.
- **Seat exhaustion mid-flow:** the owner-entitlement gate is checked at
  add time; a race between two concurrent adds is bounded the same way the
  script side is (pending rows reserve seats immediately — the
  `production_invites` pending row and the `production_members` row both
  count in `_fetch_seats_used` the moment they're written).
- **Rank-guardrail violation:** 403 with a clear message
  (`"You cannot assign a role above your own"` /
  `"You cannot modify a member at or above your access level"`).
- **Redaction is fail-closed:** `get_production_access` returns all-`false`
  for `None`; `list_crew` defaults `can_view_sensitive=False` if the kwarg
  is somehow omitted.
- **Accept mismatches:** expired → 410-style `{code: 'invite_expired'}`;
  revoked → `{code: 'invite_revoked'}`; email mismatch →
  `{code: 'email_mismatch'}`; all 403 with a distinguishing `code` for the
  accept page.
- **Owner deletes production:** cascades members + invites + crew; no
  orphan rows (see "User deletion").

## Testing

### Backend — new test files

`backend/tests/test_production_authz.py`:
- `get_production_role`: owner, each member role, non-member (`None`),
  missing production (`PRODUCTION_NOT_FOUND`).
- `get_production_access`: owner all-true; a `coordinator` row returns its
  stored flags; a per-member override (coordinator + `can_view_sensitive`)
  is reflected.
- `require_production_role`: `min_role` gate (viewer route rejects a
  non-member, accepts a viewer); `capability` gate (a `can_edit_crew`
  route rejects a viewer, accepts a coordinator, accepts a viewer whose
  flag was overridden on); 401 anon; 404 missing; introspection markers
  set.
- Resolvers: `from_crew_id`, `from_member_id`, `from_production_invite_id`
  each resolve the right `production_id`; unknown id → `None` → 404.

`backend/tests/test_production_member_routes.py`:
- **Access matrix:** anon → 401 every route; a script-member-only user
  (read-through) → 403 on `GET /members`; a `viewer` → 200 on `GET`, 403
  on `POST`/`PATCH`/`DELETE`; a `coordinator` → 403 on member management;
  an `admin` → 200; owner → 200.
- **Add — immediate:** email matching a `profiles` row inserts a
  `production_members` row with preset flags; a notification + email are
  attempted (mock asserts); a second add of the same user → 409.
- **Add — pending invite:** unknown email inserts `production_invites`;
  second POST same email → 409; email send attempted.
- **Overrides:** `POST` with `role: 'coordinator', can_view_sensitive: true`
  persists the override; omitted flags take the preset.
- **Rank guardrail:** an `admin` (rank 3) cannot create/patch a member to
  `admin` or grant `can_manage_members` if they lack it; cannot
  delete/patch another `admin`; the owner can do all of it.
- **Entitlement gate:** production whose **owner** is not Tier 2 active →
  403 `tier_2_required` even when the caller (an admin) personally is;
  `seats_used >= seats_paid` → 402 `no_seats_available`.
- **Accept:** valid token + matching email → `production_members` row with
  the invite's flags, invite → `accepted`; expired / revoked /
  wrong-email → 403 with the right `code`; already-a-member → 200
  `already_member`.
- **Cascade:** deleting the production removes its `production_members` +
  `production_invites` (assert) and leaves `contacts` / other productions
  intact.

`backend/tests/test_production_crew_routes.py` (extend the 2a file):
- Crew routes now accept a `coordinator` (with `can_edit_crew`) and reject
  a `viewer`; `GET .../crew` serves a `viewer`.
- **Redaction:** `GET .../crew` as a viewer without `can_view_sensitive`
  omits `job_rate`, `contact.phone`, `contact.standard_rate`; keeps
  `job_rate_unit`. As an admin, all present.
- `PATCH .../crew/:id` from a coordinator without `can_view_sensitive`
  with `job_rate` in the body → the write ignores `job_rate` (assert the
  stored value is unchanged), other fields update.
- The 2a owner-only assertions are updated (owner still passes; the new
  roles are additive).

`backend/tests/test_entitlement_service.py` (extend — the existing seat tests live here):
- One person as a script member + a production member on the same owner →
  `seats_used` counts them once.
- A pending production invite → `seats_used` +1; accepting it → no change.
- A pending production invite to an email that's already an accepted
  script member → no additional seat.
- Production members under a *different* owner don't affect this owner's
  count.

`backend/tests/test_route_enforcement.py`:
- Extend `test_script_scoped_routes_enforced`'s sibling (or add
  `test_production_scoped_routes_enforced`) to assert every
  production-member / crew route carries an `_authz_min_role` or
  `_authz_capability` marker.

Full suite (`pytest tests/`) stays green.

### Frontend

- `npm run build` green (repo lint is broken — build is the gate).
- Manual:
  1. As owner, open a production → **Members** tab → add a teammate who
     already has an account as `coordinator` → they appear immediately.
  2. Add an unknown email as `viewer` → pending invite shows; accept it in
     a second browser/session → member appears, invite clears.
  3. As the `coordinator`, open the production → Crew tab visible, "Add
     crew" available, **rates and phone hidden**.
  4. As owner, flip the coordinator's `can_view_sensitive` on → they now
     see rates.
  5. As the `viewer`, Crew tab is read-only (no add/edit/remove).
  6. As an `admin` member, try to promote someone to `admin` → blocked
     with the guardrail message; the owner can.
  7. Remove a member → seat freed (check `/billing` seat count).
  8. Delete the production → members/invites vanish, `/contacts` and other
     productions intact.

## Reconciliation with existing systems

| System | Change |
|---|---|
| `productions` / `units` / spine routes | `production_bp` gains member + invite routes + `production_member_service`. `GET /api/productions/:id` gains `production_access`. `list_productions` / `get_production_for_viewer` admit member rows. Crew routes re-gated to `require_production_role`. |
| `production_crew` (2a) | No schema change. `list_crew` gains a `can_view_sensitive` kwarg (redaction); `add_crew` / `update_crew` drop `job_rate` from a non-sensitive caller's payload. Route guards change from `_user_owns_production` to the decorator. |
| `contacts` (2a) | None. Still owner-only; non-owners only ever see contact fields embedded (and redacted) in the crew payload. |
| `script_members` / `script_invites` / `get_script_role` / `require_script_role` | **None.** The script axis is untouched. Department-scoped script access is explicitly out of scope. |
| `series` / `seasons` | None. |
| `casting` / `casting_unavailability` | None. |
| `shooting_schedules` / reports | None. |
| `entitlement_service` | `_fetch_seats_used` gains two sources (production members + pending production invites), folded into the existing dedup. `_fetch_seats_paid`, `get_entitlement`, `require_team_tier` unchanged. |
| Email / notifications | New `production_invite` / `production_member_added` templates in `email_templates/`; new `notifications.type` values. Reuses `email_service` + the `notifications` table. |
| `/api/invites/auto-accept` | Extended (or paralleled) to also apply pending `production_invites` on login. |
| `013_delete_user_safely.sql` | No edit — cascades are clean both directions. Migration 052 carries the comment. |
| `app.py` | No new blueprint registration (routes are on `production_bp`). |
| Frontend `App.jsx` | One new public route `/production-invites/:token`. |

## Open questions resolved in the brainstorm

- **How does someone become a member?** → One unified email-based add:
  immediate for existing accounts, pending token invite for unknown
  emails. Reuses `script_invites` infrastructure.
- **Permission inheritance between axes?** → None. Independent axes;
  `get_script_role` untouched.
- **Seat model?** → Unified person-count. Script member + production
  member = one seat. `_fetch_seats_used` unions four sources.
- **Non-owner directory scope?** → Assigned subset only. `/contacts` stays
  owner-only and out of a member's nav.
- **Roles vs. granular permissions?** → Hybrid. Roles
  (`admin`/`coordinator`/`viewer`) are presets for four boolean capability
  flags; owner / `can_manage_members` override per member.
- **Which capabilities?** → `can_view_sensitive`, `can_edit_crew`,
  `can_manage_members`, `can_edit_production`. Later surfaces add columns.
- **Who manages members?** → Owner + `can_manage_members` holders, with
  rank guardrails mirroring the script side.
- **Sensitive-field gate?** → Server-side redaction in the crew payload;
  non-sensitive callers also can't write `job_rate`.
- **Crew tab for non-owners?** → Visible to every member; write controls
  gated on `can_edit_crew`; viewer is read-only.
- **Department-scoped script/report access (HODs)?** → Out of scope.
  Separate brainstorm / umbrella step 7. `script_members.department_code`
  stays a label.
- **Entitlement check keyed to whom?** → The production **owner**, not the
  acting admin.

## References

- `docs/superpowers/specs/2026-08-31-production-data-model-design.md` —
  umbrella (permissions direction, `production_members` reservation, seat
  policy)
- `docs/superpowers/specs/2026-08-31-production-spine-design.md` — step 1;
  `production_bp` / `production_service` / `_user_owns_production` /
  `get_production_for_viewer` / the tab-strip `ProductionDetailPage`
- `docs/superpowers/specs/2026-08-31-crew-contacts-design.md` — step 2a;
  the crew routes and `production_crew_service` this re-gates, the
  sensitive fields it redacts, `is_owner` on `GET /api/productions/:id`
- `backend/middleware/authorization.py` — `get_script_role`,
  `require_script_role`, `ROLE_RANK`, resolver + `_authz_min_role` marker
  pattern that `production_authz.py` mirrors
- `backend/routes/invite_routes.py` — `create_invite` (tier + seat gate,
  409-on-pending), `update_member_role` (rank guardrails), `accept_invite`,
  `auto_accept_pending_invites`, notification + email wiring
- `backend/services/entitlement_service.py` — `_fetch_seats_used`
  (the dedup this extends), `_fetch_seats_paid`, `require_team_tier`
- `backend/db/migrations/050_productions.sql`,
  `051_contacts_crew.sql` — migration conventions, `owner_id → profiles`
  cascade + delete-user comment pattern, RLS-as-backstop
- `frontend/src/pages/ProductionDetailPage.jsx`,
  `frontend/src/components/productions/`,
  `frontend/src/pages/ProductionPages.css` — page + tab + token patterns
- `frontend/src/components/team/TeamDrawer.jsx`,
  `frontend/src/components/team/InviteModal.jsx`,
  `frontend/src/pages/InvitePage.jsx` — the script-side member UI +
  accept page this mirrors
