# Analyze-Redirect Signup-Intent Toast Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A user who clicks Analyze with no entitlement sees a toast explaining why they're being sent to `/billing`, worded differently for a never-subscribed Team-License signup vs. everyone else — using the exact same trigger condition as the existing `/billing` nudge, not a re-derived copy of it.

**Architecture:** Extract the existing inline condition from `BillingPage.jsx` into a tiny shared utility function, then use it in both `BillingPage.jsx` (replacing the inline version, same behavior) and `SceneViewer.jsx` (new — a toast before the existing redirect).

**Tech Stack:** React 18 + Vite, `frontend/src/context/ToastContext.jsx`'s existing `toast.info(title, message)` API.

## Global Constraints

- Frontend gate: `npm run build` from `frontend/` (never `npm run lint` — broken repo-wide, per project memory).
- No backend changes in this plan.
- No new dedicated test file for `billingIntent.js` — per the spec, this codebase doesn't unit-test small frontend utilities in isolation; verification is `npm run build` plus a manual toast check.

---

### Task 1: Extract the shared condition into `billingIntent.js`

**Files:**
- Create: `frontend/src/utils/billingIntent.js`
- Modify: `frontend/src/pages/BillingPage.jsx:1-6` (imports), `:83-86` (derived flags)

**Interfaces:**
- Produces: `isNeverSubscribedTeamIntent(entitlement)` — takes the object returned by `useEntitlement()`'s `entitlement` field (or `null`/`undefined`), returns `boolean`. Used by both this task's `BillingPage.jsx` update and Task 2's `SceneViewer.jsx` change.

- [ ] **Step 1: Create the utility**

```javascript
// frontend/src/utils/billingIntent.js

// Shared between BillingPage.jsx's Team-License-first nudge and
// SceneViewer.jsx's analyze-redirect toast — both must use the exact
// same condition so they can't drift out of sync with each other.
export const isNeverSubscribedTeamIntent = (entitlement) => {
    if (!entitlement) return false;
    return entitlement.signup_plan === 'tier_2_annual_team'
        && entitlement.tier === 'none'
        && entitlement.status === 'none';
};
```

- [ ] **Step 2: Update `BillingPage.jsx` to use it**

In `frontend/src/pages/BillingPage.jsx`, add the import alongside the existing ones at the top:

```javascript
import { isNeverSubscribedTeamIntent } from '../utils/billingIntent';
```

Then find these three lines (currently right after `isActiveTeam`/`tierLabel`):

```javascript
    const neverSubscribed = entitlement.tier === 'none' && entitlement.status === 'none';
    const isTeamIntent = entitlement.signup_plan === 'tier_2_annual_team';
    const hideBreakdownDefault = isTeamIntent && neverSubscribed && !isActiveTeam;
```

Replace them with:

```javascript
    const hideBreakdownDefault = isNeverSubscribedTeamIntent(entitlement) && !isActiveTeam;
```

Nothing else in the file changes — `hideBreakdownDefault` is used identically everywhere else in the component (the badge, the card ordering, the escape hatch).

- [ ] **Step 3: Verify the build**

```bash
cd frontend
npm run build
```
Expected: builds clean, same pre-existing chunk-size warning as before, no new errors or warnings.

- [ ] **Step 4: Manual sanity check**

Run `npm run dev` and confirm `/billing` still behaves identically to before this change for at least one account state (e.g. a normal tier_1 account still shows Breakdown Credits first, unaffected). This is a pure refactor — behavior must be unchanged.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/billingIntent.js frontend/src/pages/BillingPage.jsx
git commit -m "$(cat <<'EOF'
refactor(billing): extract signup-intent condition to shared utility

BillingPage.jsx's "never-subscribed tier_2 signup" check is about to be
needed in SceneViewer.jsx too (the analyze-redirect toast). Pulled it
out to frontend/src/utils/billingIntent.js so both nudges use the exact
same condition instead of two copies that could drift apart. No
behavior change to BillingPage.jsx itself.
EOF
)"
```

---

### Task 2: Toast before the analyze-redirect in `SceneViewer.jsx`

**Files:**
- Modify: `frontend/src/components/scenes/SceneViewer.jsx:16` (import), `:239-244` (`handleAnalyzeScene`), `:309-314` (`handleBulkAnalyze`)

**Interfaces:**
- Consumes: `isNeverSubscribedTeamIntent(entitlement)` from Task 1 (`frontend/src/utils/billingIntent.js`); `entitlement` and `toast` are already in scope in this component (`useEntitlement()` at line 52, `useToast()` at line 21).

- [ ] **Step 1: Add the import**

In `frontend/src/components/scenes/SceneViewer.jsx`, add alongside the existing `useEntitlement` import (line 16):

```javascript
import { isNeverSubscribedTeamIntent } from '../../utils/billingIntent';
```

- [ ] **Step 2: Update `handleAnalyzeScene`'s gate**

Find (around line 239-244):

```javascript
        // Breakdown entitlement gate: block analysis with no credits/plan
        if (!canRunBreakdown) {
            navigate('/billing');
            return;
        }
```

Replace with:

```javascript
        // Breakdown entitlement gate: block analysis with no credits/plan
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

- [ ] **Step 3: Update `handleBulkAnalyze`'s gate**

Find (around line 309-314) — the identical shape, in the bulk-analyze handler:

```javascript
        // Breakdown entitlement gate: block analysis with no credits/plan
        if (!canRunBreakdown) {
            navigate('/billing');
            return;
        }
```

Replace with the same change as Step 2:

```javascript
        // Breakdown entitlement gate: block analysis with no credits/plan
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

(This duplicates the same four lines between the two handlers — consistent with the file's existing style, where the original one-line gate was already copy-pasted between both handlers rather than factored into a shared function.)

- [ ] **Step 4: Verify the build**

```bash
cd frontend
npm run build
```
Expected: builds clean, no new errors or warnings.

- [ ] **Step 5: Manual verification**

Using `npm run dev`, trigger both gates (single-scene Analyze and "Analyze All") as:
1. A never-subscribed account with `signup_plan: 'tier_2_annual_team'` → confirm the "Subscribe to continue" toast appears, then the page navigates to `/billing`.
2. A never-subscribed account with `signup_plan: 'tier_1_pay_per_breakdown'` (or any other entitlement state that fails `canRunBreakdown`, e.g. zero balance) → confirm "Buy breakdown credits" appears instead.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/scenes/SceneViewer.jsx
git commit -m "$(cat <<'EOF'
feat(billing): explain the analyze-redirect to /billing with a toast

Clicking Analyze (single scene or "Analyze All") with no entitlement
silently navigated to /billing with zero context — the exact moment
the original signup-intent test case in this session hit. Now shows a
toast first: the same "Subscribe to your Team License" nudge as
BillingPage.jsx for never-subscribed tier_2 signups (via the shared
isNeverSubscribedTeamIntent utility), or a generic "Buy breakdown
credits" toast for everyone else. See
docs/superpowers/specs/2026-07-31-analyze-redirect-nudge-design.md.
EOF
)"
```

---

## Self-Review Notes

- **Spec coverage:** Shared-utility extraction (Task 1), toast copy for both branches (Task 2 Steps 2-3), both gate call sites covered (single-scene and bulk) — all present. Out-of-scope items from the spec (no other entitlement gate touched, no toast-library change) — neither task touches those.
- **Placeholder scan:** No TBD/TODO; every step has literal code.
- **Type consistency:** `isNeverSubscribedTeamIntent` takes one argument (`entitlement`) and returns `boolean` everywhere it's defined and called, across both tasks.
