# Billing Page Redesign — Design Spec

**Date:** 2026-07-21
**Status:** Approved, ready for planning.

## Problem

`frontend/src/pages/BillingPage.jsx` (88 lines) is functionally complete
(quantity-picker credit purchase, seat purchase, annual license upsell, all
wired to `createCheckout`/PayFast) but visually unstyled — plain `<div>`s and
`<section>`s with no card treatment, no `PageHeader`, no design-system
classes. This is the last major page in the app without a design pass.

Separately, there is currently **no direct navigation entry point** to
`/billing` at all. It's only reachable via contextual upgrade prompts
(`SubscriptionBanner`, `SubscriptionGate`, `InviteModal`'s "buy seats" link)
or a manual URL — not from the primary TopBar user dropdown, which only has
"Profile" and "Log out".

## Decisions (from brainstorming)

- **Placement:** `/billing` stays its own top-level route (not nested inside
  `ProfilePage`).
- **Nav entry:** add a "Billing" item to the TopBar user dropdown, next to
  the existing "Profile" item.
- **Visual language:** restyle to match `ProfilePage.jsx` / `ProfilePage.css`
  — same card idiom (`--gray-800` background, `--gray-700` border, 16px
  radius), same primary-gradient button style, same `Spinner` loading state,
  same `PageHeader` component.
- **New content:** add a "current plan" summary card above the existing
  purchase actions, so the page answers "what am I on" before offering
  upgrade/purchase actions. This is new UI, not present today.
- **Scope:** frontend markup/CSS + one nav wire-up only. No backend, API,
  pricing, or entitlement-logic changes. No visual companion / mockups were
  used — this spec's structure descriptions are the source of truth for
  layout.

## Architecture

Three files touched:

1. `frontend/src/components/layout/TopBar.jsx` — add one more
   `dropdown-item` button, immediately after the existing "Profile" button
   (~line 128-132), following the identical pattern:
   ```jsx
   <button
     className="dropdown-item"
     onClick={() => { navigate('/billing'); setUserMenuOpen(false); }}
   >
     <CreditCard size={16} />
     <span>Billing</span>
   </button>
   ```
   `CreditCard` imported from `lucide-react` (already a project dependency —
   see other icons imported in `TopBar.jsx`/`ProfilePage.jsx`).

2. `frontend/src/pages/BillingPage.jsx` — restructured markup only. All
   existing state/handlers (`useEntitlement`, `useState` for quantity/seat
   quantity/busy/error, `buy()`, `postToPayFast()`, the
   `PRICE_ZAR` display constants) are unchanged. The JSX returned changes
   from bare divs to the structure in "Page structure" below.

3. `frontend/src/pages/BillingPage.css` (new file) — styled using the same
   CSS custom properties already defined and used by `ProfilePage.css`
   (`--gray-900`, `--gray-800`, `--gray-700`, `--gray-600`, `--gray-500`,
   `--gray-300`, `--gray-100`, `--primary-400/500/600`, `--primary-alpha-15`,
   `--primary-alpha-30`). No new tokens introduced.

No changes to `services/apiService.js`, `hooks/useEntitlement.js`, or any
backend route/service.

## Page structure

Top to bottom:

1. **`PageHeader`** — `title="Billing"`. No subtitle or actions needed (no
   equivalent of Profile's avatar/save-button pairing at the header level).

2. **Plan summary card** (new, `.billing-card` class, same visual treatment
   as `.profile-card`):
   - Tier label — one of:
     - "No active plan" (`entitlement.tier === 'none'`)
     - "Pay-per-breakdown" (`entitlement.tier === 'tier_1_pay_per_breakdown'`
       — confirmed against `backend/services/entitlement_service.py`'s
       `TIER_1` constant; distinct from `tier_1_credits`, which is a
       PayFast *charge type*, not an entitlement tier)
     - "Annual Team License" (`entitlement.tier === 'tier_2_annual_team'`
       — `TIER_2` constant, same file)
   - Status badge — reflects `entitlement.status` (e.g. "active", "none"),
     styled as a small pill (reuse the color logic pattern from
     `.profile-message.success` / `.error` — green for active, neutral gray
     otherwise — but as a compact badge, not a full alert banner).
   - Usage line — `entitlement.breakdown_balance` remaining always shown;
     additionally `entitlement.seats_used` / `entitlement.seats_paid` shown
     only when the team branch applies (mirrors the existing conditional in
     the seats section today).

3. **Buy breakdown credits card** — same content as today's first
   `<section>` (quantity select, total, buy button), restyled as a
   `.billing-card` with an `<h2>` heading (icon + "Breakdown credits", same
   heading pattern as `.profile-card h2`).

4. **Team seats card** *or* **Annual License upsell card** — same
   conditional as today
   (`entitlement.tier === 'tier_2_annual_team' && entitlement.status === 'active'`
   picks seats; else the license upsell), restyled as a `.billing-card`.

5. **Loading state** — replaces the current bare `Loading…` text with the
   same `Spinner` component `ProfilePage.jsx` uses (`import { Spinner } from
   '../components/ui'`), centered, matching `.profile-loading`'s layout
   pattern (new equivalent class in `BillingPage.css`).

6. **Error state** — `error && <div className="billing-message error">...`
   using the same visual treatment as `.profile-message.error` (icon +
   text, red-tinted background/border), not reusing the literal CSS class
   name since it lives in a separate stylesheet, but matching the same
   colors/spacing.

## Data flow

Unchanged. `useEntitlement()` still drives all conditional rendering;
`createCheckout` + `postToPayFast` still perform the actual purchase
round-trip to PayFast. This spec only changes what wraps that existing data
and those existing handlers in the DOM/CSS.

## Error handling

No new error paths. The existing `try/catch` around `buy()` and its
`setError('Could not start checkout. Please try again.')` message are
unchanged in behavior — only in visual presentation (see "Error state"
above).

## Testing / verification

- `npm run build` (per project memory, `npm run lint` is broken repo-wide —
  gate on build, not lint).
- Manual browser check of `/billing` reachable via the new TopBar dropdown
  entry, and visual review of the page in whatever real entitlement state(s)
  are available to the logged-in test account. Cannot fabricate all three
  entitlement states (none / credits / active team) without backend/data
  setup, so only the reachable state(s) get a live visual check; the other
  branches get a code-level review against the existing (already-working)
  conditional logic, which is not being changed — only restyled.

## Out of scope

- Any change to pricing, entitlement logic, or PayFast integration.
- Nesting Billing inside `ProfilePage` (explicitly decided against).
- Sidebar nav placement (explicitly decided against in favor of TopBar
  dropdown).
- Renewal automation / failed-renewal downgrade (separate open backlog
  items, unrelated to this page's visual design).
