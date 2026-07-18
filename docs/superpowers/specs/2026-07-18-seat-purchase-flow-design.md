# Seat purchase flow — design

**Date:** 2026-07-18
**Status:** Approved, ready for planning
**Branch context:** builds on `feat/two-tier-pricing` (`tier_2_seats` charge type,
already verified end-to-end against live PayFast sandbox transactions per
Task 14)

## Problem

`tier_2_seats` purchases already work at the payment/grant layer: checkout →
PayFast → ITN → `account_seats` row inserted. What's undefined is the
*product flow* around it — how an Owner actually gets from "I want to add a
team member" to "that person is on the team," and what the seat pool means
along the way. The backend already has more built than that gap implied:
`account_seats` is a fungible pool (not tied to a person at purchase time),
`create_invite` already gates on `seats_used >= seats_paid` and returns
`402 no_seats_available`, and a full invite/accept/revoke flow exists via
email token (`backend/routes/invite_routes.py`). Nothing on the frontend
reacts to that 402 yet, and the seat-counting query has a race that allows
overbooking.

## Current state (as found)

- `account_seats` (`backend/services/entitlement_service.py`): rows of
  `{owner_id, seats_granted, term_expires_at}`. Buying N seats is one row
  with `seats_granted=N` — there is no per-seat record and no link to any
  specific invite or person.
- `_fetch_seats_paid`: sums `seats_granted` across rows where
  `term_expires_at > now()`. Seats expire when the Owner's
  `subscription_expires_at` does (seats default to that term at grant time).
- `_fetch_seats_used`: counts **distinct `user_id`** in `script_members`
  where `invited_by = owner_id`, across *all* of the Owner's scripts (a
  person invited to 3 scripts by the same Owner consumes 1 seat, not 3).
  This only counts *accepted* memberships — pending invites are invisible to
  it today.
- `create_invite` (`backend/routes/invite_routes.py:69`): gated by
  `@require_team_tier`, then checks `seats_used >= seats_paid` and returns
  `402 {"error": ..., "code": "no_seats_available"}` if the pool is
  exhausted. Nothing on the frontend currently handles this response.
- `accept_invite`: flips `script_invites.status` to `'accepted'` and inserts
  the `script_members` row. No seat check happens here — by the time this
  runs, `create_invite` already let the invite through.
- Frontend: `BillingPage.jsx` + `useEntitlement.js` already support buying
  `tier_2_seats` via the standard checkout flow. No UI anywhere reacts to
  `no_seats_available`, and no draft-preservation exists across a checkout
  redirect.

## The overbooking race

Because `seats_used` only counts *accepted* memberships, several pending
invites can each individually pass the `seats_used < seats_paid` check
before any of them are accepted. If an Owner with 1 free seat sends 5
invites in parallel, all 5 pass the check; if several are then accepted,
`seats_used` ends up above `seats_paid` with nothing having rejected any of
it. This is the first thing this design fixes.

## Design

### 1. Seat model: fungible pool, not per-seat assignment

Seats remain a pool — purchasing seats is not purchasing N individually
trackable records, and no data model change is needed to tie "this seat" to
"this invite." The Owner manages purchasing and inviting as two separate,
loosely-coupled actions; the pool just needs to be counted correctly at
every point where an invite could reserve a slot.

### 2. Fix: `seats_used` counts pending + accepted, not accepted-only

`_fetch_seats_used` changes to count distinct people across:
- `script_invites` rows with `status = 'pending'`, `invited_by = owner_id`
  (matched by `email`), **and**
- `script_members` rows with `invited_by = owner_id` (matched by `user_id`).

Dedup across the two by resolving the pending invite's `email` against
`profiles.email` where possible, so a person who is pending on one script and
already accepted on another under the same Owner counts once.

**Lifecycle under the fix:**
- **Send an invite** → seat reserved immediately (counted via the pending
  half).
- **Accept** → person moves from the pending half to the accepted half of
  the same tally. Net seat count is unchanged — accepting is a no-op for
  capacity, not a new reservation.
- **Revoke or expire** → the invite drops out of `status = 'pending'`,
  automatically releasing the seat. No cleanup job needed — this falls out
  of the query filter.
- **Remove a team member** (`DELETE /api/scripts/<id>/members/<id>`) →
  deletes their `script_members` row, freeing the seat **immediately** for
  reuse. Per the multi-script note below, this only frees the seat once the
  person has no remaining accepted/pending relationship with that Owner
  across *any* script — removing them from one script while they're still a
  member of another (same Owner) does not free a seat, because the count is
  per-person, not per-membership-row. This matches the existing
  `_fetch_seats_used` docstring intent; no behavior change beyond fixing the
  pending-invite gap.

### 3. Entry points

Two entry points exist; Billing is primary, the invite screen deep-links
into it when blocked.

**Primary — Billing page (proactive).** Owner buys N seats via the existing
checkout flow (`POST /api/billing/checkout` with `charge_type=tier_2_seats`,
quantity picker) → PayFast → ITN → `grant_seats`. After payment, they land
back on `PaymentResultPage` and then Billing, with the seat count updated.
No auto-redirect into an invite form — buying and inviting stay deliberate,
separate actions. This path requires no new backend work; the checkout
flow already handles `tier_2_seats` (Task 13/14).

**Reactive — invite screen (blocked path).** Owner is on a script's team
page filling in an invite (email, department, role). Submitting hits the
`402 no_seats_available` response. Instead of a dead end:

1. Show the block message with a "Buy seats" CTA that opens the same
   checkout flow as Billing, including the quantity picker (not fixed to 1
   — an Owner who expects to hit this repeatedly can buy several at once).
2. Before navigating to PayFast (which is a full-page redirect, off-origin),
   stash the draft invite in `sessionStorage` under a fixed key (e.g.
   `pending_seat_invite_draft`): `{script_id, email, department_code,
   role}`. This has to be `sessionStorage`, not React state — the redirect
   to PayFast and back leaves and re-enters the SPA.
3. On return, `PaymentResultPage` checks for that stashed draft when
   `type=tier_2_seats` and the purchase has settled (reusing its existing
   ITN-arrival poll — see "Confirmation timing" below). If present, it
   routes to that script's team page instead of the generic landing, with a
   flag telling the team page to read and clear the `sessionStorage` draft
   on mount.
4. The team page pre-fills the invite form from the restored draft. The
   Owner reviews and clicks send, which re-runs the normal `create_invite`
   call — now passing the seat check because the purchase granted a seat
   and nothing else claimed it in between.

Nothing server-side ties a specific `account_seats` row to a specific
invite draft — the `sessionStorage` draft is pure UX convenience so the
Owner doesn't retype the email after the purchase interruption, not a data
link.

### 4. Confirmation timing

`PaymentResultPage` already polls `refetch()` on the entitlement hook up to
5 times over ~10 seconds waiting for the ITN to land, since it's a separate
server-to-server call that can arrive after the browser returns. The
reactive flow reuses this poll unchanged, but the "restore draft and route
to the team page" step cannot use the page's generic settle-check
(`can_run_breakdown || can_use_teams`): a `tier_2_seats` purchase is only
ever made by a tier-2-active owner who already has both flags true
*before* paying, since seat count doesn't gate them (see
`entitlement_service.py`). That check would be true on the very first
render, firing the redirect before the ITN has granted the seat. Instead,
the draft stashed before the PayFast redirect also carries
`seatsPaidBaseline` (the owner's `seats_paid` at purchase time), and the
redirect only fires once `entitlement.seats_paid > seatsPaidBaseline` —
i.e. once the seat pool has actually grown — so the Owner doesn't land
back on the invite form only to immediately re-hit the 402.

### 5. Known residual race (not fixed here)

Two simultaneous `create_invite` calls (e.g. an Owner double-clicking submit,
or two admins on the same script inviting at once) can both read
`seats_used < seats_paid` as true before either write commits, both
succeeding when only one seat was actually free — the same class of race the
PayFast ITN handler solves with `_claim_intent`'s conditional UPDATE. Not
fixing this now: it requires either a DB-level constraint/lock or a claim
pattern on `script_invites` insert, which is a bigger change than this
design's scope. Flagging it for whoever picks up the implementation plan to
decide whether it's in scope or a fast-follow.

### 6. Interaction with the failed-renewal downgrade gap (existing backlog item)

`account_seats.term_expires_at` defaults to the Owner's
`subscription_expires_at`, and `_fetch_seats_paid` only counts seats where
`term_expires_at > now()`. This means the backlog's "Failed-renewal downgrade
gap" (nothing writes `status = 'expired'` on a renewal failure) has a second
consequence beyond losing `can_use_teams`: if the license term lapses,
*seats* also silently stop counting once `term_expires_at` passes, even
before any explicit downgrade logic runs. No fix proposed here — this design
and the renewal-automation/downgrade work are coupled, and whoever
implements the renewal job should re-read this spec.

## Out of scope

- Per-seat assignment/tracking (a `seats` table with individual seat rows
  explicitly tied to one invite each). Considered and rejected in favor of
  the fungible pool — see "Seat model" above.
- Fixing the concurrent double-invite race (section 5).
- Renewal automation and the failed-renewal downgrade fix themselves —
  tracked separately in `docs/BACKLOG.md`.
- New notification types — the seat purchase itself reuses the existing
  `PaymentResultPage` confirmation; invite send/accept reuses the existing
  `send_team_invite` / accepted-notification email machinery unchanged.

## Implementation touchpoints (for the plan)

- `backend/services/entitlement_service.py` — `_fetch_seats_used`: change
  query to count pending `script_invites` + accepted `script_members`,
  deduped by email/user_id.
- `backend/routes/invite_routes.py` — no gating logic change needed (the
  402 check stays the same comparison); confirm `revoke_invite` and invite
  expiry naturally exclude from the new pending-count query (they should,
  via `status` filtering).
- Frontend: invite/team page component — handle `402 no_seats_available`
  with a "Buy seats" CTA + quantity picker, `sessionStorage` draft stash
  before redirecting to checkout.
- `frontend/src/pages/PaymentResultPage.jsx` — branch on
  `type=tier_2_seats` + presence of a stashed draft to route back to the
  script's team page instead of the generic landing, and signal the team
  page to restore + clear the draft.
- Tests: seat-count query (pending+accepted dedup), revoke/expire releasing
  a reserved seat, removal freeing a seat only when no other
  script-membership remains under the same Owner.
