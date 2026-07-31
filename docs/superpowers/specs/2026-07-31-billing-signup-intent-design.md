# Billing page: honor signup intent for never-subscribed Team License signups

**Date:** 2026-07-31
**Status:** Approved, not yet implemented

## Problem

A user who signs up choosing the Team License plan (`signup_plan =
'tier_2_annual_team'`, recorded at signup via `POST /api/auth/set-plan` —
see `backend/routes/auth_routes.py`) has no active entitlement yet, since
setting a plan at signup records intent only; it grants nothing (per that
route's own docstring: "Setting a plan grants nothing... only a confirmed
PayFast payment grants access").

When that user then tries to run their first analysis and hits the
entitlement gate, they land on `/billing`
(`frontend/src/pages/BillingPage.jsx`). Today that page always shows the
**Breakdown Credits** purchase card first, with the **Team License**
subscribe card below it. A user who explicitly told us at signup they
wanted the team license sees the one-off breakdown purchase as the first,
most prominent option — and, confirmed via live testing, will buy that
instead of subscribing to the plan they actually said they wanted.

## Goal

When a user's stated signup intent was the Team License and they have
never actually subscribed to anything, steer them toward subscribing
instead of defaulting them into a one-off breakdown purchase — without
removing their ability to try a single breakdown if they genuinely want
to.

## Trigger condition

Show the "Team License first, no breakdown by default" view only when
**all** of the following are true, evaluated from the entitlement
response:

- `signup_plan === 'tier_2_annual_team'`
- `tier === 'none'` (i.e. `profiles.subscription_plan` is `'none'`)
- `status === 'none'` (i.e. `profiles.subscription_status` is `'none'`)

The `tier`/`status` check is what makes this automatically self-limiting
to "never subscribed": the moment a real PayFast payment activates a
license, `subscription_plan`/`subscription_status` move off `'none'`
permanently for that account (activation always writes
`subscription_plan = 'tier_2_annual_team'`, `subscription_status =
'active'` — see `entitlement_service.activate_license` and the
`payfast_claim_and_grant` Postgres function). If the license later lapses
or is cancelled, `subscription_status` becomes `'expired'`/`'cancelled'`
— never back to `'none'` — so this condition goes false on its own and
the account reverts to the ordinary billing page layout, including the
Breakdown Credits card. No extra "has ever subscribed" bookkeeping is
needed; the existing status vocabulary already encodes it.

Everything else (tier_1-intent signups, already-active tier_2 accounts,
lapsed tier_2 accounts) sees today's layout exactly as it is now.

## Behavior when triggered

1. The **Team License** card renders first, above the purchase-card
   section, with a small badge reading "Your selected plan".
2. The **Breakdown Credits** purchase row is not rendered.
3. Below the Team License card, a small, low-emphasis text link reads:
   *"Just want to try one breakdown instead?"* Clicking it reveals the
   Breakdown Credits card in place (no navigation, no reload) — this is
   local UI state only, not persisted, so it resets if the page is
   reloaded.

The Team Seats purchase row (only relevant once `isActiveTeam` is true)
is unaffected by any of this — it's mutually exclusive with the trigger
condition anyway, since an active team account already has
`status !== 'none'`.

## Changes required

### Backend — `services/entitlement_service.py`

- `_fetch_profile` already selects `subscription_plan`,
  `subscription_status`, `subscription_expires_at`,
  `subscription_billing_cycle`. Add `signup_plan` to that select list.
- `get_entitlement()` return dict gains a `signup_plan` key (the raw
  value from the profile row, `None` if never set — the "unknown user"
  early-return branch also gains `signup_plan: None` for shape
  consistency).

No other backend changes. This is a pure additive read — no new routes,
no schema changes, no changes to any grant/charge logic.

### Frontend — `frontend/src/pages/BillingPage.jsx`

- Derive `neverSubscribed = entitlement.tier === 'none' && entitlement.status === 'none'`.
- Derive `isTeamIntent = entitlement.signup_plan === 'tier_2_annual_team'`.
- Derive `hideBreakdownDefault = isTeamIntent && neverSubscribed && !isActiveTeam`.
- New local state: `showBreakdownAnyway` (boolean, default `false`).
- `showBreakdownCard = !hideBreakdownDefault || showBreakdownAnyway`.
- When `hideBreakdownDefault` is true: render the Team License card
  before the purchase-card section (instead of after), add the "Your
  selected plan" badge, and render the escape-hatch link beneath it when
  `showBreakdownCard` is still false.
- The purchase-card section (currently always rendered, holding the
  Breakdown Credits row and conditionally the Team Seats row) becomes
  conditionally rendered: skip entirely when `!showBreakdownCard` and
  seats aren't applicable (they aren't, since `isActiveTeam` is false in
  this state) — i.e. render it only when `showBreakdownCard` is true.

No changes to `apiService.js`, no changes to checkout/purchase logic
itself — this only touches what's visible and in what order.

## Testing

- Backend: extend `tests/test_entitlement_service.py` with a case
  asserting `get_entitlement()` includes `signup_plan` sourced from the
  profile row, and the "unknown user" branch returns `signup_plan: None`.
- Frontend: no existing automated test coverage for `BillingPage.jsx`
  (none exists today for this page) — verify manually via `npm run
  build` plus a live check: a fresh account with `signup_plan =
  'tier_2_annual_team'` and no purchases shows Team License first with no
  Breakdown card, the escape-hatch link reveals it, and an existing
  tier_1-intent or already-active account is unaffected.

## Out of scope

- Anything about the actual checkout/purchase flow, pricing, or PayFast
  integration — unchanged.
- Persisting `showBreakdownAnyway` across reloads — deliberately
  ephemeral, matches how transient this nudge is meant to be.
- The equivalent nudge on any other page (e.g. the analyze-trigger point
  itself, before the redirect to `/billing`) — out of scope for this
  round; `/billing` is the single place this entitlement gate lands
  today.
