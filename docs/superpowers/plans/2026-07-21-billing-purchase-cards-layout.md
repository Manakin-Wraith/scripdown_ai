# Billing Purchase Cards Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Combine the Breakdown Credits and Team Seats sections on `/billing` into a single card with compact horizontal rows (icon, title/subtitle, stepper, total, buy button), replacing the current two plain stacked sections.

**Architecture:** One presentation-only change to `frontend/src/pages/BillingPage.jsx` (JSX restructure) and `frontend/src/pages/BillingPage.css` (new row rules, removal of now-dead `.billing-form-group` rules). No changes to checkout logic, state, or handlers. The Annual Team License upsell card is untouched.

**Tech Stack:** React 18 (plain JSX, no TypeScript), Vite, `lucide-react` icons (`Wallet`, `Users` — already imported), plain CSS with existing design tokens (`--gray-100/400/700`, `--primary-400`, `--primary-alpha-15`).

## Global Constraints

- Presentation-only: `buy()`, `PRICE_ZAR`, `quantity`/`setQuantity`, `seatQuantity`/`setSeatQuantity`, `busy`/`error` state, and the `isActiveTeam` conditional must not change behavior — only the JSX/CSS around them.
- Frontend gate is `npm run build`, not `npm run lint` (lint is broken repo-wide — known project issue).
- The Annual Team License upsell card (rendered when `!isActiveTeam`) keeps its exact current markup and styling — it is not part of the new row card.
- Rows must wrap on narrow viewports via CSS flex-wrap — no separate mobile markup or JS breakpoint logic.
- Reuse existing `Wallet`/`Users` lucide-react icons already imported at the top of `BillingPage.jsx` — no new icon imports.

---

### Task 1: Combine Breakdown Credits and Team Seats into one row-based card

**Files:**
- Modify: `frontend/src/pages/BillingPage.jsx:102-166`
- Modify: `frontend/src/pages/BillingPage.css:102-155` (remove dead `.billing-form-group` rules, add new row rules)

**Interfaces:**
- Consumes: existing `entitlement`, `quantity`/`setQuantity`, `seatQuantity`/`setSeatQuantity`, `busy`, `buy`, `PRICE_ZAR`, `isActiveTeam` — no signature changes.
- Produces: nothing consumed by other tasks (this task is self-contained).

- [ ] **Step 1: Replace the two card sections in `BillingPage.jsx` with the combined row card**

In `frontend/src/pages/BillingPage.jsx`, replace lines 102-166 (the `<section className="billing-card">` for Breakdown credits through the closing `)}` of the `isActiveTeam ? ... : ...` block, but keep the Annual Team License `<section>` in the `else` branch unchanged) with:

```jsx
                    <section className="billing-card billing-purchase-card">
                        <div className="purchase-row">
                            <div className="purchase-row-icon"><Wallet size={20} /></div>
                            <div className="purchase-row-text">
                                <h3>Breakdown credits</h3>
                                <p>{entitlement.breakdown_balance} remaining · R{PRICE_ZAR.tier_1_credits} each</p>
                            </div>
                            <div className="quantity-stepper">
                                <button
                                    type="button"
                                    className="stepper-btn"
                                    onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                                    disabled={quantity <= 1}
                                    aria-label="Decrease breakdown credit quantity"
                                >−</button>
                                <span className="stepper-value">{quantity}</span>
                                <button
                                    type="button"
                                    className="stepper-btn"
                                    onClick={() => setQuantity((q) => q + 1)}
                                    aria-label="Increase breakdown credit quantity"
                                >+</button>
                            </div>
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
                                <div className="quantity-stepper">
                                    <button
                                        type="button"
                                        className="stepper-btn"
                                        onClick={() => setSeatQuantity((q) => Math.max(1, q - 1))}
                                        disabled={seatQuantity <= 1}
                                        aria-label="Decrease team seat quantity"
                                    >−</button>
                                    <span className="stepper-value">{seatQuantity}</span>
                                    <button
                                        type="button"
                                        className="stepper-btn"
                                        onClick={() => setSeatQuantity((q) => q + 1)}
                                        aria-label="Increase team seat quantity"
                                    >+</button>
                                </div>
                                <p className="purchase-row-total">R{PRICE_ZAR.tier_2_seats * seatQuantity}/yr</p>
                                <button className="billing-buy-btn" disabled={busy} onClick={() => buy('tier_2_seats', seatQuantity)}>
                                    Add
                                </button>
                            </div>
                        )}
                    </section>

                    {!isActiveTeam && (
                        <section className="billing-card">
                            <h2><Crown size={20} /> Annual Team License</h2>
                            <p>R{PRICE_ZAR.tier_2_license}/yr — unlimited breakdowns for you and your team.</p>
                            <button className="billing-buy-btn" disabled={busy} onClick={() => buy('tier_2_license', 1)}>
                                Subscribe
                            </button>
                        </section>
                    )}
```

Note the Annual Team License section changed from the `else` branch of a ternary to its own `{!isActiveTeam && (...)}` block, since it's no longer paired with the seats row in a single ternary — the seats row is now an independent `{isActiveTeam && (...)}` inside the purchase card above. This is a structural change only; the rendered condition (`!isActiveTeam` shows the license card, `isActiveTeam` shows the seats row) is identical to today's behavior.

- [ ] **Step 2: Remove the now-dead `.billing-form-group` CSS rules and add the new row rules**

In `frontend/src/pages/BillingPage.css`, delete this block (the `/* Purchase form controls */` comment and the two rules under it — `.billing-form-group` and `.billing-form-group label` are no longer referenced anywhere after Step 1):

```css
/* Purchase form controls */
.billing-form-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 1rem;
}

.billing-form-group label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--gray-300);
}
```

In its place, insert:

```css
/* Combined purchase card (Breakdown credits / Team seats rows) */
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
    margin: 0;
}
```

Leave `.quantity-stepper`, `.stepper-btn`, and `.stepper-value` rules exactly as they are — still used by both rows in the new card.

- [ ] **Step 3: Remove the now-dead `.billing-total` CSS rule**

After Step 1's JSX replacement, no markup anywhere in `BillingPage.jsx` uses `className="billing-total"` any more — both purchase rows now use `purchase-row-total`, and the Annual Team License card never used `.billing-total` (it only ever had a price line and a Subscribe button). Confirm with:

Run: `grep -n "billing-total" frontend/src/pages/BillingPage.jsx`
Expected: no output (no matches).

Then delete this now-dead rule from `BillingPage.css`:

```css
.billing-total {
    color: var(--gray-100);
    font-weight: 600;
    margin: 0.75rem 0;
}
```

- [ ] **Step 4: Build and manually verify**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors.

Then run `npm run dev` and check `/billing` in a browser:
- With an active-team test account (or by temporarily inspecting the entitlement data if a real one isn't available): both rows (Breakdown credits, Team seats) appear in one card with a divider between them; steppers and buy buttons work as before.
- With a non-team account: only the Breakdown credits row appears in the purchase card, and the Annual Team License card appears below it as its own card, unchanged from before.
- Resize the browser to a narrow/mobile width: each row's icon+text wraps to its own line above the stepper+total+button group, without any content getting cut off or overlapping.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/BillingPage.jsx frontend/src/pages/BillingPage.css
git commit -m "feat(billing): combine credits/seats purchases into one row-based card"
```

---

### Task 2: Update BACKLOG.md to mark this item resolved

**Files:**
- Modify: `docs/BACKLOG.md` (the "Better layout for the Breakdown credits and Team seats cards" entry)

**Interfaces:**
- Consumes: nothing (doc-only task).
- Produces: nothing.

- [ ] **Step 1: Mark the backlog entry resolved**

In `docs/BACKLOG.md`, find the entry titled `## Better layout for the Breakdown credits and Team seats cards` and replace its `**Status:**` line and body with:

```markdown
## Better layout for the Breakdown credits and Team seats cards — RESOLVED, shipped

**Status:** Done. Brainstormed (3 visual mockups compared), designed, planned,
and implemented 2026-07-21.

**What shipped.** The Breakdown Credits and Team Seats sections on
`/billing` are now one card (`.billing-purchase-card`) with each purchase
as a compact horizontal row — icon badge (reusing the existing `Wallet`/
`Users` lucide-react icons), title + subtitle, quantity stepper, running
total, and a buy button — separated by a divider when both rows are
present. On narrow screens each row wraps via CSS flexbox (icon+text on
one line, stepper+total+button on the next) with no separate mobile
markup. The Annual Team License upsell card (shown instead of the seats
row for non-team accounts) is unchanged — it's a distinct action
(subscribe vs. buy-more), not a peer row. No changes to checkout logic,
`PRICE_ZAR`, or any purchase state/handlers.

**References.**
- Design: `docs/superpowers/specs/2026-07-21-billing-purchase-cards-layout-design.md`
- Plan: `docs/superpowers/plans/2026-07-21-billing-purchase-cards-layout.md`
- `frontend/src/pages/BillingPage.jsx`, `BillingPage.css`
```

- [ ] **Step 2: Commit**

```bash
git add docs/BACKLOG.md
git commit -m "docs: mark billing purchase cards layout backlog item resolved"
```
