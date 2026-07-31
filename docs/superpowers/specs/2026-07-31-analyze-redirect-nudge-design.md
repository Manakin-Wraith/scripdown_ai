# Analyze-trigger redirect: explain why the user landed on /billing

**Date:** 2026-07-31
**Status:** Approved, not yet implemented

## Background

This extends the signup-intent nudge shipped in
`2026-07-31-billing-signup-intent-design.md`, which was explicitly scoped
to `/billing` itself. This spec covers the redirect *into* `/billing` —
the actual moment a user clicked Analyze.

## Problem

`frontend/src/components/scenes/SceneViewer.jsx` has two entitlement
gates, `handleAnalyzeScene` (single scene) and `handleBulkAnalyze` ("Analyze
All"), both doing the same thing:

```js
if (!canRunBreakdown) {
    navigate('/billing');
    return;
}
```

No toast, no message — the user clicks Analyze and is silently
teleported to `/billing` with zero explanation of why. This is the exact
moment the original test case in this session hit: click Analyze, get
redirected, land on a page with purchase options and no context for why
you're there.

## Design

### Shared condition, extracted

`BillingPage.jsx` currently inlines the "never-subscribed tier_2-intent"
check:

```js
const neverSubscribed = entitlement.tier === 'none' && entitlement.status === 'none';
const isTeamIntent = entitlement.signup_plan === 'tier_2_annual_team';
const hideBreakdownDefault = isTeamIntent && neverSubscribed && !isActiveTeam;
```

This condition is now needed in a second place. Extract the
`isTeamIntent && neverSubscribed` part (the `!isActiveTeam` clause stays
local to `BillingPage.jsx` — it's not relevant at the redirect point,
since `canRunBreakdown` already gates on entitlement, not team status) to
a new tiny utility:

**New file:** `frontend/src/utils/billingIntent.js`

```js
// Shared with BillingPage.jsx's Team-License-first nudge — keep both
// nudges using the exact same condition so they can't drift out of sync.
export const isNeverSubscribedTeamIntent = (entitlement) => {
    if (!entitlement) return false;
    return entitlement.signup_plan === 'tier_2_annual_team'
        && entitlement.tier === 'none'
        && entitlement.status === 'none';
};
```

`BillingPage.jsx` is updated to import and use this instead of its
inline `neverSubscribed`/`isTeamIntent` locals:

```js
const hideBreakdownDefault = isNeverSubscribedTeamIntent(entitlement) && !isActiveTeam;
```

### Toast at the redirect point

`SceneViewer.jsx` already has `toast` (`useToast()`) and `entitlement`
(`useEntitlement()`) in scope. Both gates become:

```js
if (!canRunBreakdown) {
    if (isNeverSubscribedTeamIntent(entitlement)) {
        toast.info('Subscribe to continue', 'You signed up for the Team License — subscribe to run unlimited breakdowns.');
    } else {
        toast.info('Buy breakdown credits', 'Purchase breakdown credits to continue analyzing this script.');
    }
    navigate('/billing');
    return;
}
```

Both `handleAnalyzeScene` and `handleBulkAnalyze` get the identical
change — the gate logic is copy-pasted between them today already (same
`if (!canRunBreakdown) { navigate('/billing'); return; }` shape appears
twice), so this plan keeps that existing duplication pattern rather than
introducing a new shared helper function for it, consistent with the
file's current style.

## What doesn't change

- `canRunBreakdown` itself, the entitlement fetch, the redirect
  destination — all unchanged.
- No new toast variant/type — `toast.info` already exists and is used
  elsewhere in this exact file (e.g. the "Analysis Started" toast).
- `BillingPage.jsx`'s own rendering logic (Task 2 of the prior plan) is
  unchanged in behavior — only its internal derivation of
  `neverSubscribed`/`isTeamIntent` moves into the shared utility.

## Testing

- No existing automated test coverage for `SceneViewer.jsx` or
  `BillingPage.jsx` (both are pure frontend components with none today,
  confirmed in the prior spec) — verified via `npm run build` plus a
  manual check: trigger the gate as a never-subscribed tier_2-intent
  account and confirm the "Subscribe to continue" toast appears before
  the redirect; trigger it as a tier_1-intent or lapsed-tier_2 account
  and confirm "Buy breakdown credits" appears instead.
- `billingIntent.js` is trivial (single boolean expression) — no
  dedicated unit test file is being added for it, consistent with this
  codebase's existing pattern of not unit-testing small frontend
  utilities in isolation from the components that use them.

## Out of scope

- Changing the toast library/component itself.
- Any change to `canRunBreakdown`'s computation or the entitlement fetch.
- Any other entitlement gate in the codebase besides these two in
  `SceneViewer.jsx` (e.g. `SubscriptionGate.jsx`, `InviteModal.jsx`) —
  those already show their own contextual messaging in place, unlike
  this silent redirect.
