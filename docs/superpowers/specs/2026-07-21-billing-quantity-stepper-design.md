# Billing Quantity Stepper — Design Spec

**Date:** 2026-07-21
**Status:** Approved, ready for planning.

## Problem

`BillingPage.jsx`'s two quantity pickers (breakdown credits: `[1, 5, 10]`,
team seats: `[1, 2, 3, 5, 10]`) are `<select>` dropdowns limited to a fixed
set of preset values. A user who wants, say, 7 breakdown credits or 4 seats
has no way to select that exact quantity — they must round up to the
nearest preset and overpay, or round down and buy again later.

## Decisions (from brainstorming)

- **Scope:** applies to both quantity pickers — breakdown credits AND team
  seats — since they are visually identical controls today and should stay
  consistent.
- **Control:** a stepper (`−` / number display / `+`), not a free-text
  input. Click-only — no direct typing into the number field.
- **Bounds:** minimum 1 (the `−` button disables at 1); no maximum — this
  matches the backend's only real constraint. Confirmed in
  `backend/services/payfast_service.py::compute_amount`:
  ```python
  if quantity < 1:
      raise ValueError(f"quantity must be >= 1, got {quantity}")
  ```
  There is no upper bound enforced anywhere server-side for `tier_1_credits`
  or `tier_2_seats`, so the UI introduces no artificial cap either.
- **Step size:** 1, for both pickers.

## Architecture

Single file touched: `frontend/src/pages/BillingPage.jsx`. A new small
inline stepper markup pattern (no new component file — two instances of a
few lines of JSX each, not complex enough to justify extracting a shared
component per YAGNI) replaces the two `<select>` elements. New CSS rules
added to the existing `frontend/src/pages/BillingPage.css` for the stepper
buttons, reusing existing tokens.

No backend changes — `buy(chargeType, qty)` and `createCheckout` already
accept an arbitrary integer quantity; only the UI control that produces
`quantity` / `seatQuantity` changes.

## Component structure

Replace, in the "Breakdown credits" card:

```jsx
<div className="billing-form-group">
    <label>Quantity</label>
    <div className="quantity-stepper">
        <button
            type="button"
            className="stepper-btn"
            onClick={() => setQuantity((q) => Math.max(1, q - 1))}
            disabled={quantity <= 1}
            aria-label="Decrease quantity"
        >−</button>
        <span className="stepper-value">{quantity}</span>
        <button
            type="button"
            className="stepper-btn"
            onClick={() => setQuantity((q) => q + 1)}
            aria-label="Increase quantity"
        >+</button>
    </div>
</div>
```

And the identical pattern in the "Team seats" card, driving `seatQuantity` /
`setSeatQuantity` instead. The `id`/`htmlFor` pairing the old `<select>` had
is dropped since there's no longer a single focusable form control to label
that way — `aria-label` on each button covers accessibility instead.

The `<option>` arrays (`[1, 5, 10]` and `[1, 2, 3, 5, 10]`) are deleted
entirely — the stepper has no preset list.

## Data flow

Unchanged. `quantity` and `seatQuantity` remain the same `useState<number>`
values already read by the total-price calculation
(`PRICE_ZAR.tier_1_credits * quantity`, `PRICE_ZAR.tier_2_seats *
seatQuantity`) and passed into `buy('tier_1_credits', quantity)` /
`buy('tier_2_seats', seatQuantity)`. Only the control that mutates them
changes, from `onChange={(e) => setQuantity(Number(e.target.value))}` to
the two button `onClick` handlers above.

## Error handling

None new. Because the stepper can only ever produce integers `>= 1` (the
`−` button is disabled at the floor, `+` has no ceiling to overflow in any
problematic way for a display integer), there is no invalid-state case to
guard against — unlike a free-text input, this control cannot produce
empty, negative, decimal, or non-numeric values. `disabled={busy}` on the
buy button (unchanged) still prevents double-submission during checkout.

## Testing / verification

- `npm run build` (per project memory, gate on build not lint).
- Manual browser check: click `+`/`−` on both steppers, confirm the number
  and total price update live, confirm `−` disables exactly at 1, confirm
  clicking "Buy breakdowns" / "Add N seats" passes the current stepper
  value through unchanged (same `buy()` call as before, only the value it
  receives changes source).

## Out of scope

- Any backend/entitlement/pricing change.
- A maximum quantity cap (explicitly decided against — no backend
  constraint exists to justify one).
- Direct typing into the quantity field (explicitly decided against in
  favor of click-only).
- Extracting a shared `<QuantityStepper>` component — two small inline
  instances are simple enough that a shared abstraction isn't warranted
  yet (YAGNI); revisit if a third quantity picker appears elsewhere.
