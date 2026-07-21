# Billing page and payment result page — alignment/styling fix

**Date:** 2026-07-21
**Status:** Approved, ready for planning

## Problem

Two related presentation bugs reported by the user:

1. **Billing page (`frontend/src/pages/BillingPage.jsx`, `BillingPage.css`)**
   renders its content aligned to the left edge of the viewport rather than
   centered. Root cause: `.billing-cards` has `max-width: 640px` but no
   `margin: 0 auto`, so on any screen wider than ~700px the narrow card
   column sits flush against `.billing-page`'s left padding instead of
   centered in the available space. `PageHeader` and the error message
   (`.billing-message`) aren't width-constrained at all, so even if the
   cards were centered they wouldn't line up with the header/message above
   them.

2. **Payment result page (`frontend/src/pages/PaymentResultPage.jsx`)** has
   no CSS file at all — it's plain unstyled `<div>`/`<h1>`/`<p>` markup,
   rendered top-left with browser-default typography and no card styling,
   completely inconsistent with the rest of the app's design system.

## Goals

- Center the Billing page's content (header, error message, card stack) as
  a single column, matching the page's existing narrow-column design intent
  — no layout redesign, just fix the alignment.
- Give the payment result page (success / cancel / pending-confirmation
  states) real styling consistent with the app's existing card design
  language (`gray-800/900/700` tokens, 16px radius, card padding), centered
  in the viewport.
- Presentation-only change: no changes to billing logic, polling behavior,
  or the seat-invite resume redirect in `PaymentResultPage.jsx`.

## Design

### Billing page

Wrap `PageHeader`, the error message block, and `.billing-cards` in a new
`.billing-content` container:

```jsx
<div className="billing-page">
  <div className="billing-content">
    <PageHeader title="Billing" />
    {error && <div className="billing-message error" role="alert">...</div>}
    <div className="billing-cards">...</div>
  </div>
</div>
```

CSS addition:

```css
.billing-content {
    max-width: 640px;
    margin: 0 auto;
}
```

`.billing-cards` keeps its existing `max-width: 640px` (now redundant but
harmless — leave it for now rather than risk an unrelated cleanup) and its
`flex-direction: column; gap: 1.5rem`. The loading state (`.billing-loading`)
already centers itself via `min-height: 60vh; align-items/justify-content:
center` and needs no change.

### Payment result page

New `frontend/src/pages/PaymentResultPage.css`, imported by
`PaymentResultPage.jsx`. Structure becomes:

```jsx
<div className="payment-result-page">
  <div className="payment-result-card">
    <StatusIcon size={40} className="payment-result-icon" />
    <h1>...</h1>
    <p>...</p>
    <Link to="..." className="payment-result-link">...</Link>
  </div>
</div>
```

CSS:

```css
.payment-result-page {
    min-height: 100vh;
    background: var(--gray-900);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
}

.payment-result-card {
    background: var(--gray-800);
    border: 1px solid var(--gray-700);
    border-radius: 16px;
    padding: 2.5rem;
    max-width: 420px;
    width: 100%;
    text-align: center;
}

.payment-result-icon {
    margin-bottom: 1rem;
}
```

Three states, each with a `lucide-react` icon colored to match existing
status-color usage elsewhere in the app:

| State | Condition | Icon | Color |
|---|---|---|---|
| Success (settled) | `outcome === 'success' && settled` | `CheckCircle` | `#86EFAC` (matches `.plan-status-badge.active`) |
| Pending confirmation | `outcome === 'success' && !settled` | `Clock` | `var(--gray-400)` (neutral) |
| Cancelled | `outcome === 'cancel'` | `XCircle` | `#FCA5A5` (matches `.billing-message.error`) |

Heading/body copy stays as it is today (`Thank you` / `Payment cancelled` /
existing paragraph text) — this is a styling pass, not a copy pass.

All existing behavior is preserved unchanged:
- The 5-attempt, 2-second polling `useEffect` for `refetch()`.
- The seat-invite resume redirect `useEffect` (`tier_2_seats` + draft +
  `seats_paid` baseline comparison).
- The `settled` derivation (`can_run_breakdown || can_use_teams`).
- Both `Link` destinations (`/billing` on cancel, `/` on success).

## Non-goals

- No change to `BillingPage.jsx`'s business logic, checkout flow, or
  quantity steppers.
- No change to `PaymentResultPage.jsx`'s polling/redirect logic.
- No wide-screen multi-column layout for Billing (deferred per user
  decision — fixed narrow column only).
- No new shared component between `BillingPage.css` and
  `PaymentResultPage.css` — each keeps its own stylesheet even though the
  visual language (tokens, radius, padding) matches.

## Testing

- `frontend/npm run build` (lint is broken repo-wide — gate on build, per
  existing project convention).
- Manual verification in browser: `/billing` at a wide viewport (e.g.
  1440px) shows the content centered, not left-hugging; `/payment/success`
  and `/payment/cancel` (or whatever routes `App.jsx` wires
  `PaymentResultPage` to) show a centered, card-styled result with the
  correct icon per state.

## References

- `frontend/src/pages/BillingPage.jsx`, `BillingPage.css`
- `frontend/src/pages/PaymentResultPage.jsx` (new `PaymentResultPage.css`)
- `frontend/src/App.jsx` — routes wiring `PaymentResultPage`
- Backlog item: "Billing page and payment success messages — misaligned"
  in `docs/BACKLOG.md`
