# Billing page: combined purchase-row layout for Breakdown Credits / Team Seats

**Date:** 2026-07-21
**Status:** Approved, ready for planning

## Problem

On `/billing`, the "Breakdown credits" card and the "Team seats" card
(`frontend/src/pages/BillingPage.jsx:101-165`) are each a plain stacked
section — heading, one line of body text, a quantity stepper, a total, and
a buy button. User feedback: too plain/utilitarian, doesn't read as a
considered pricing UI.

Explored three directions visually (side-by-side pricing-tier cards,
compact horizontal rows in one shared card, a unified card with a
tab toggle). User selected **compact horizontal rows sharing one card**.

## Goals

- Combine the Breakdown Credits purchase and the Team Seats purchase into
  one card, each as a horizontal row (icon badge, title/subtitle, quantity
  stepper, running total, buy button), separated by a divider.
- Reuse the app's existing lucide-react icons already imported in
  `BillingPage.jsx` (`Wallet` for credits, `Users` for seats) — no new
  icon set or emoji.
- Adapt gracefully on narrow/mobile screens without a second layout to
  maintain.
- Presentation-only: no changes to checkout logic, `PRICE_ZAR`, state, or
  handlers (`buy`, `quantity`/`setQuantity`, `seatQuantity`/`setSeatQuantity`).

## Design

### Card structure

Replace the current two separate `.billing-card` sections for breakdown
credits and team seats with a single new `.billing-purchase-card`
containing two `.purchase-row` children:

```jsx
<section className="billing-card billing-purchase-card">
    <div className="purchase-row">
        <div className="purchase-row-icon"><Wallet size={20} /></div>
        <div className="purchase-row-text">
            <h3>Breakdown credits</h3>
            <p>{entitlement.breakdown_balance} remaining · R{PRICE_ZAR.tier_1_credits} each</p>
        </div>
        <div className="quantity-stepper">{/* unchanged stepper markup */}</div>
        <p className="purchase-row-total">R{PRICE_ZAR.tier_1_credits * quantity}</p>
        <button className="billing-buy-btn" disabled={busy} onClick={() => buy('tier_1_credits', quantity)}>
            Buy
        </button>
    </div>

    {isActiveTeam && (
        <div className="purchase-row">
            <div className="purchase-row-icon"><Users size={20} /></div>
            <div className="purchase-row-text">
                <h3>Team seats</h3>
                <p>{entitlement.seats_used} of {entitlement.seats_paid} in use · R{PRICE_ZAR.tier_2_seats}/seat/yr</p>
            </div>
            <div className="quantity-stepper">{/* unchanged stepper markup */}</div>
            <p className="purchase-row-total">R{PRICE_ZAR.tier_2_seats * seatQuantity}/yr</p>
            <button className="billing-buy-btn" disabled={busy} onClick={() => buy('tier_2_seats', seatQuantity)}>
                Add
            </button>
        </div>
    )}
</section>
```

- The two rows always render inside the same card when `isActiveTeam` is
  true; when it's false, only the credits row renders in this card (the
  seats row's `isActiveTeam &&` guard already handles that — matching
  today's conditional).
- `<h2>` card-level headings ("Wallet — Breakdown credits", "Users — Team
  seats") are removed since each row now carries its own icon + title.
- The existing `.billing-total` paragraph copy ("Total: R…") is shortened
  to just the number (`.purchase-row-total`) since the row's icon+label
  already establishes context — avoids repeating "Total:" twice when both
  rows are visible at once.
- "Buy breakdowns" / "Add N seat(s) — R150/yr each" button copy is
  shortened to "Buy" / "Add" — the row's own text already states what's
  being bought and at what price, so the button doesn't need to repeat it.

### Annual Team License upsell (non-active-team state)

Stays exactly as it is today — its own separate `.billing-card` (`h2` with
`Crown` icon, price line, `Subscribe` button), unchanged markup and CSS,
rendered below `.billing-purchase-card` in the same `{isActiveTeam ? ... : ...}`
position it already occupies in the card list. It's a different action
(subscribing vs. buying more of something already owned), not a peer row.

### CSS

New rules in `BillingPage.css`, alongside the existing `.billing-card`
block:

```css
.billing-purchase-card {
    display: flex;
    flex-direction: column;
}

.purchase-row {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem 0;
    flex-wrap: wrap;
}

.purchase-row + .purchase-row {
    border-top: 1px solid var(--gray-700);
}

.purchase-row-icon {
    width: 40px;
    height: 40px;
    flex-shrink: 0;
    background: var(--primary-alpha-15);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--primary-400);
}

.purchase-row-text {
    flex: 1 1 180px;
    min-width: 0;
}

.purchase-row-text h3 {
    margin: 0 0 0.15rem;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--gray-100);
}

.purchase-row-text p {
    margin: 0;
    font-size: 0.8rem;
    color: var(--gray-400);
}

.purchase-row-total {
    font-weight: 700;
    color: var(--gray-100);
    font-size: 0.9rem;
    white-space: nowrap;
}
```

`.quantity-stepper` and `.billing-buy-btn` keep their existing rules
(`BillingPage.css:116-188`) unchanged — they're reused as-is inside each
row.

### Mobile behavior

No separate mobile markup or breakpoint-specific component. `.purchase-row`
uses `flex-wrap: wrap` — on narrow viewports, `.purchase-row-icon` +
`.purchase-row-text` (which has `flex: 1 1 180px`, so it takes the full
line once nothing else fits beside it) wrap onto their own line, and the
stepper/total/button group wraps to the line below within the same row
block. No JS/breakpoint logic needed; this is pure flexbox reflow.

## Non-goals

- No change to `buy()`, `PRICE_ZAR`, quantity/seatQuantity state, or any
  handler.
- No change to the Annual Team License upsell card's markup or styling.
- No change to the plan-summary card above these two sections.
- No new icon library or custom icon assets — reuses `Wallet`/`Users`
  already imported from `lucide-react` in `BillingPage.jsx`.

## Testing

- `frontend/npm run build` (project convention: lint is broken repo-wide,
  gate on build).
- Manual verification in browser: `/billing` at both a wide viewport and a
  narrow (mobile-width) viewport, for both an active-team account (seats
  row visible) and a non-team account (Annual Team License upsell card
  visible instead) — confirm rows render correctly, wrap sanely on mobile,
  and the divider only appears between two rows (not after a single row
  when the seats row is absent).

## References

- `frontend/src/pages/BillingPage.jsx` — current card sections (lines 101-165)
- `frontend/src/pages/BillingPage.css` — `.billing-card`, `.quantity-stepper`,
  `.billing-buy-btn` (reused unchanged)
- Backlog item: "Better layout for the Breakdown credits and Team seats
  cards" in `docs/BACKLOG.md`
