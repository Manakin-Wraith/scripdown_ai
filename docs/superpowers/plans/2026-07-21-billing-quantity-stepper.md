# Billing Quantity Stepper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two fixed-preset `<select>` quantity pickers on `BillingPage.jsx` (breakdown credits: 1/5/10, team seats: 1/2/3/5/10) with a click-only `−`/`+` stepper so a user can reach any exact positive integer quantity.

**Architecture:** Single-file JSX change (`frontend/src/pages/BillingPage.jsx`) plus new CSS rules appended to the existing `frontend/src/pages/BillingPage.css`. No new component file, no backend change — `quantity`/`seatQuantity` state and the `buy()` call are unchanged; only the control that mutates that state changes.

**Tech Stack:** React 18 + Vite (plain JS/JSX). No frontend test framework exists (no vitest/jest) — verification is `npm run build` + manual browser check.

## Global Constraints

- Minimum quantity is 1 for both pickers — the `−` button disables at `<= 1`, matching the backend floor confirmed in `backend/services/payfast_service.py::compute_amount` (`if quantity < 1: raise ValueError(...)`).
- No maximum — do not add a UI cap; none exists server-side for `tier_1_credits` or `tier_2_seats`.
- Step size is 1 for both pickers.
- Click-only — no direct typing into the quantity value (explicitly decided against in the spec).
- No shared `<QuantityStepper>` component — two small inline instances, per YAGNI (spec: "Out of scope").
- Gate on `npm run build`, not `npm run lint` (repo-wide lint breakage, unrelated).

---

### Task 1: Replace both quantity `<select>`s with a stepper control

**Files:**
- Modify: `frontend/src/pages/BillingPage.jsx:104-110` (breakdown credits quantity), `:121-127` (team seats quantity)
- Modify: `frontend/src/pages/BillingPage.css` (append new stepper rules after `.billing-form-group select:focus`, i.e. after line 131)

**Interfaces:**
- Consumes: existing `quantity`/`setQuantity` and `seatQuantity`/`setSeatQuantity` state (`frontend/src/pages/BillingPage.jsx:36-37`, unchanged); existing `.billing-form-group` wrapper class (unchanged).
- Produces: new CSS classes `.quantity-stepper`, `.stepper-btn`, `.stepper-btn:disabled`, `.stepper-value` — used only within this same file, nothing downstream depends on them.

- [ ] **Step 1: Add the stepper CSS rules**

In `frontend/src/pages/BillingPage.css`, after the existing `.billing-form-group select:focus` block (currently lines 127-131) and before `.billing-total` (currently line 133), insert:

```css
.quantity-stepper {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.stepper-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.25rem;
    height: 2.25rem;
    background: var(--gray-900);
    border: 1px solid var(--gray-600);
    border-radius: 8px;
    color: var(--gray-100);
    font-size: 1.125rem;
    font-weight: 600;
    line-height: 1;
    cursor: pointer;
    transition: all 0.15s ease;
}

.stepper-btn:hover:not(:disabled) {
    border-color: var(--primary-500);
    color: var(--primary-400);
}

.stepper-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}

.stepper-value {
    min-width: 2rem;
    text-align: center;
    font-size: 1rem;
    font-weight: 600;
    color: var(--gray-100);
}
```

Also delete the now-unused `.billing-form-group select` and `.billing-form-group select:focus` rules (currently lines 116-131), since Step 2 removes the only two `<select>` elements that used them.

- [ ] **Step 2: Replace the breakdown-credits `<select>` with the stepper**

In `frontend/src/pages/BillingPage.jsx`, find (currently lines 104-110):

```jsx
                    <div className="billing-form-group">
                        <label htmlFor="qty">Quantity</label>
                        <select id="qty" value={quantity}
                                onChange={(e) => setQuantity(Number(e.target.value))}>
                            {[1, 5, 10].map((n) => <option key={n} value={n}>{n}</option>)}
                        </select>
                    </div>
```

Replace with:

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

- [ ] **Step 3: Replace the team-seats `<select>` with the stepper**

In the same file, find (currently lines 121-127):

```jsx
                        <div className="billing-form-group">
                            <label htmlFor="seat-qty">Quantity</label>
                            <select id="seat-qty" value={seatQuantity}
                                    onChange={(e) => setSeatQuantity(Number(e.target.value))}>
                                {[1, 2, 3, 5, 10].map((n) => <option key={n} value={n}>{n}</option>)}
                            </select>
                        </div>
```

Replace with:

```jsx
                        <div className="billing-form-group">
                            <label>Quantity</label>
                            <div className="quantity-stepper">
                                <button
                                    type="button"
                                    className="stepper-btn"
                                    onClick={() => setSeatQuantity((q) => Math.max(1, q - 1))}
                                    disabled={seatQuantity <= 1}
                                    aria-label="Decrease quantity"
                                >−</button>
                                <span className="stepper-value">{seatQuantity}</span>
                                <button
                                    type="button"
                                    className="stepper-btn"
                                    onClick={() => setSeatQuantity((q) => q + 1)}
                                    aria-label="Increase quantity"
                                >+</button>
                            </div>
                        </div>
```

- [ ] **Step 4: Build to verify no syntax/import errors**

Run: `cd frontend && npm run build`
Expected: build succeeds with no new errors (pre-existing chunk-size and `pdf.js` eval warnings are unrelated and fine).

- [ ] **Step 5: Manual verification in browser**

Run: `cd frontend && npm run dev`, log in, navigate to `/billing`. Confirm:
- Both quantity steppers render with `−`, a number, and `+`.
- Clicking `+` increments the displayed number and the total price line below it updates live, for both the credits and seats cards (seats card only visible if the logged-in account is on an active `tier_2_annual_team` plan — otherwise the Annual Team License upsell card renders instead, unaffected by this change).
- Clicking `−` decrements the same way, and disables (visibly dimmed, unclickable) once the value reaches 1.
- Clicking "Buy breakdowns" / "Add N seats" still calls `buy()` with the current stepper value (check via browser devtools network tab that the `createCheckout` request body's `quantity` matches what's displayed, or trust the unchanged `buy(chargeType, qty)` call signature read from the code).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/BillingPage.jsx frontend/src/pages/BillingPage.css
git commit -m "feat(billing): replace preset quantity dropdowns with a stepper

Both the breakdown-credits and team-seats quantity pickers were
limited to a fixed preset list (1/5/10 and 1/2/3/5/10). Replaces both
with a click-only -/+ stepper so any exact positive integer quantity
is reachable, matching the backend's only real constraint
(quantity >= 1, no upper bound, per payfast_service.py). No change to
purchase logic -- quantity/seatQuantity state and the buy() call are
unchanged."
```

---

## Self-Review Notes

- **Spec coverage:** stepper replaces both dropdowns ✓ Steps 2-3. Min 1 enforced via `disabled` ✓ both steps. No max ✓ `+` handler has no ceiling. Step size 1 ✓ `q - 1`/`q + 1`. Click-only, no typing ✓ no `<input>` element used, `<span>` display only. No shared component, two inline instances ✓ Steps 2 and 3 are separate, not extracted. Dead CSS removed ✓ Step 1 deletes the now-unused `select` rules.
- **Placeholder scan:** none — every step has literal, complete code.
- **Type/name consistency:** `quantity-stepper`/`stepper-btn`/`stepper-value` class names are identical between the CSS (Step 1) and both JSX instances (Steps 2-3); `setQuantity`/`setSeatQuantity` functional-update form (`(q) => ...`) matches the existing `useState` declarations at `BillingPage.jsx:36-37`, unchanged from the current file.
