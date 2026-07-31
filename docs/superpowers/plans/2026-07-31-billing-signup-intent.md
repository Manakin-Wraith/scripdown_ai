# Billing Signup-Intent Nudge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A user who signed up choosing the Team License but has never actually subscribed to anything sees the Team License option first on `/billing`, not the one-off Breakdown Credits purchase — with an escape hatch to still buy one breakdown if they want.

**Architecture:** One additive backend field (`signup_plan` on the entitlement response) drives one frontend component's conditional rendering (`BillingPage.jsx`). No new routes, no schema changes, no changes to checkout/purchase logic.

**Tech Stack:** Flask + supabase-py (backend), React 18 + Vite (frontend), pytest, `npm run build` as the frontend gate (lint is broken repo-wide).

## Global Constraints

- Server is the sole authority on price — this plan touches display/ordering logic only, never amounts.
- Backend gate: `pytest tests/` from `backend/`, using `SUPABASE_URL=https://test.supabase.co SUPABASE_ANON_KEY=test SUPABASE_SERVICE_KEY=test RESEND_API_KEY=test FLASK_ENV=development` env vars (matches this repo's existing test invocation pattern).
- Frontend gate: `npm run build` from `frontend/` (never `npm run lint` — broken repo-wide, per project memory).
- Trigger condition (exact, from the spec): `signup_plan === 'tier_2_annual_team' && tier === 'none' && status === 'none'`.

---

### Task 1: Backend — expose `signup_plan` on the entitlement response

**Files:**
- Modify: `backend/services/entitlement_service.py:40-44` (`_fetch_profile`), `:129-155` (`get_entitlement`)
- Test: `backend/tests/test_entitlement_service.py`

**Interfaces:**
- Produces: `get_entitlement(user_id)` return dict gains a `signup_plan` key (`str | None`) — every other existing key (`tier`, `status`, `breakdown_balance`, `seats_paid`, `seats_used`, `billing_cycle`, `can_run_breakdown`, `can_use_teams`) is unchanged.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_entitlement_service.py`. First, extend the existing `_profile` helper (near the top of the file) to accept an optional `signup_plan`:

```python
def _profile(plan='tier_1_pay_per_breakdown', status='active', signup_plan=None):
    return {'subscription_plan': plan, 'subscription_status': status,
            'subscription_expires_at': '2099-01-01T00:00:00Z',
            'signup_plan': signup_plan}
```

Then add two new test functions anywhere after the existing tests:

```python
def test_get_entitlement_includes_signup_plan(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile",
                         lambda uid: _profile('none', 'none', signup_plan='tier_2_annual_team'))
    monkeypatch.setattr(es, "_fetch_balance", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_paid", lambda uid: 0)
    monkeypatch.setattr(es, "_fetch_seats_used", lambda uid: 0)
    ent = es.get_entitlement('u1')
    assert ent['signup_plan'] == 'tier_2_annual_team'


def test_unknown_user_signup_plan_is_none(monkeypatch):
    monkeypatch.setattr(es, "_fetch_profile", lambda uid: None)
    ent = es.get_entitlement('ghost')
    assert ent['signup_plan'] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `backend/`:
```bash
source venv/bin/activate
SUPABASE_URL=https://test.supabase.co SUPABASE_ANON_KEY=test SUPABASE_SERVICE_KEY=test RESEND_API_KEY=test FLASK_ENV=development pytest tests/test_entitlement_service.py -k signup_plan -v
```
Expected: both FAIL with `KeyError: 'signup_plan'`.

- [ ] **Step 3: Implement**

In `backend/services/entitlement_service.py`, update `_fetch_profile` (currently selects `'subscription_plan, subscription_status, subscription_expires_at, subscription_billing_cycle'`) to also select `signup_plan`:

```python
def _fetch_profile(user_id: str):
    resp = get_supabase_admin().table('profiles').select(
        'subscription_plan, subscription_status, subscription_expires_at, '
        'subscription_billing_cycle, signup_plan'
    ).eq('id', user_id).limit(1).execute()
    return resp.data[0] if resp.data else None
```

Then update `get_entitlement`'s two return points. The "unknown user" early return:

```python
    if not profile:
        # Unknown user: deny everything.
        return {'tier': 'none', 'status': 'none', 'breakdown_balance': 0,
                'seats_paid': 0, 'seats_used': 0, 'billing_cycle': None,
                'signup_plan': None,
                'can_run_breakdown': False, 'can_use_teams': False}
```

And the normal return:

```python
    return {
        'tier': tier,
        'status': status,
        'breakdown_balance': balance,
        'seats_paid': seats_paid,
        'seats_used': seats_used,
        'billing_cycle': profile.get('subscription_billing_cycle'),
        'signup_plan': profile.get('signup_plan'),
        # Tier 2 active is unlimited; everyone else needs credits.
        'can_run_breakdown': tier2_active or balance > 0,
        # Expired tier 2 loses team writes (failed renewal => downgrade).
        'can_use_teams': tier2_active,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
SUPABASE_URL=https://test.supabase.co SUPABASE_ANON_KEY=test SUPABASE_SERVICE_KEY=test RESEND_API_KEY=test FLASK_ENV=development pytest tests/test_entitlement_service.py -v
```
Expected: all tests in this file PASS (17 previously + 2 new = 19).

- [ ] **Step 5: Run the full backend suite to confirm no regressions**

```bash
SUPABASE_URL=https://test.supabase.co SUPABASE_ANON_KEY=test SUPABASE_SERVICE_KEY=test RESEND_API_KEY=test FLASK_ENV=development pytest tests/ -q
```
Expected: all tests pass (448 previously + 2 new = 450).

- [ ] **Step 6: Commit**

```bash
git add backend/services/entitlement_service.py backend/tests/test_entitlement_service.py
git commit -m "$(cat <<'EOF'
feat(billing): expose signup_plan on the entitlement response

Lets the frontend tell a never-subscribed tier_2-signup user apart from
everyone else, so BillingPage can steer them toward the license they
already said they wanted instead of defaulting them into a one-off
breakdown purchase (see docs/superpowers/specs/2026-07-31-billing-signup-intent-design.md).
EOF
)"
```

---

### Task 2: Frontend — reorder/hide billing cards for never-subscribed tier_2 signups

**Files:**
- Modify: `frontend/src/pages/BillingPage.jsx` (whole file restructure — see below)
- Modify: `frontend/src/pages/BillingPage.css` (new styles, additive)

**Interfaces:**
- Consumes: `entitlement.signup_plan` (from Task 1), `entitlement.tier`, `entitlement.status` — all already available via `useEntitlement()`.
- No new exports — this is a leaf page component with no other consumers.

There's no existing automated test coverage for `BillingPage.jsx` (confirmed in the spec) — this task is verified via `npm run build` plus the manual check in Step 5. Do not invent a test file that doesn't fit the codebase's existing pattern.

- [ ] **Step 1: Add the derived flags and escape-hatch state**

`useState` calls must stay unconditional and in the same order every
render, so the new `showBreakdownAnyway` state goes alongside the
existing four `useState` calls at the top of the component, before the
`loading` early return — not after it. The derived `const` flags (which
depend on `entitlement`, only available after that early return) go
after the existing `isActiveTeam`/`tierLabel` lines, as normal.

In `frontend/src/pages/BillingPage.jsx`, update the top of the component:

```javascript
export default function BillingPage() {
    const { entitlement, loading } = useEntitlement();
    const [quantity, setQuantity] = useState(1);
    const [seatQuantity, setSeatQuantity] = useState(1);
    const [licenseCycle, setLicenseCycle] = useState('annual');
    const [showBreakdownAnyway, setShowBreakdownAnyway] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
```

Then, immediately after the existing `isActiveTeam`/`tierLabel` lines (right after the early-return loading block):

```javascript
    const isActiveTeam = entitlement.tier === 'tier_2_annual_team' && entitlement.status === 'active';
    const tierLabel = TIER_LABELS[entitlement.tier] || TIER_LABELS.none;

    // A user who told us at signup they wanted the Team License, and has
    // never actually subscribed to anything (tier/status still 'none' —
    // not lapsed, not active), should see that plan first instead of
    // defaulting into a one-off breakdown purchase. The moment they ever
    // subscribe, subscription_plan/status move off 'none' permanently
    // (see entitlement_service.activate_license), so this self-clears —
    // no separate "has ever subscribed" bookkeeping needed.
    const neverSubscribed = entitlement.tier === 'none' && entitlement.status === 'none';
    const isTeamIntent = entitlement.signup_plan === 'tier_2_annual_team';
    const hideBreakdownDefault = isTeamIntent && neverSubscribed && !isActiveTeam;
    const showBreakdownCard = !hideBreakdownDefault || showBreakdownAnyway;
```

- [ ] **Step 2: Restructure the two purchase sections into variables**

Currently the JSX has, in order: `plan-summary-card` section, `billing-purchase-card` section (Breakdown Credits row + conditional Team Seats row), then the Team License `section` (only when `!isActiveTeam`). Replace the return statement's card-rendering body (everything inside `<div className="billing-cards">` after the `plan-summary-card` section closes) with:

```jsx
                <div className="billing-cards">
                    <section className="billing-card plan-summary-card">
                        <h2><CreditCard size={20} /> Current plan</h2>
                        <div className="plan-summary-row">
                            <span>Plan</span>
                            <span>{tierLabel}</span>
                        </div>
                        <div className="plan-summary-row">
                            <span>Status</span>
                            <span className={`plan-status-badge ${entitlement.status === 'active' ? 'active' : 'inactive'}`}>
                                {entitlement.status}
                            </span>
                        </div>
                        <div className="plan-summary-row">
                            <span>Breakdown credits</span>
                            <span>{entitlement.breakdown_balance} remaining</span>
                        </div>
                        {isActiveTeam && (
                            <>
                                <div className="plan-summary-row">
                                    <span>Billing cycle</span>
                                    <span>{entitlement.billing_cycle === 'monthly' ? 'Monthly' : 'Annual'}</span>
                                </div>
                                <div className="plan-summary-row">
                                    <span>Team seats</span>
                                    <span>{entitlement.seats_used} of {entitlement.seats_paid} in use</span>
                                </div>
                            </>
                        )}
                    </section>

                    {hideBreakdownDefault ? (
                        <>
                            {teamLicenseSection}
                            {showBreakdownCard ? purchaseCardSection : (
                                <button
                                    type="button"
                                    className="billing-try-breakdown-link"
                                    onClick={() => setShowBreakdownAnyway(true)}
                                >
                                    Just want to try one breakdown instead?
                                </button>
                            )}
                        </>
                    ) : (
                        <>
                            {showBreakdownCard && purchaseCardSection}
                            {!isActiveTeam && teamLicenseSection}
                        </>
                    )}
                </div>
```

This references two JSX variables, `purchaseCardSection` and `teamLicenseSection`, which don't exist yet — define them next.

- [ ] **Step 3: Define `purchaseCardSection`**

Immediately before the `return (` statement (i.e. after the `isActiveTeam`/`tierLabel`/derived-flags block from Step 1), add:

```javascript
    const purchaseCardSection = (
        <section className="billing-card billing-purchase-card" key="purchase-card">
            <div className="purchase-row">
                <div className="purchase-row-icon"><Wallet size={20} /></div>
                <div className="purchase-row-text">
                    <h3>Breakdown credits</h3>
                    <p>{entitlement.breakdown_balance} remaining · R{PRICE_ZAR.tier_1_credits} each (incl. VAT)</p>
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

            {isActiveTeam && (() => {
                const seatCycle = entitlement.billing_cycle === 'monthly' ? 'monthly' : 'annual';
                const seatPrice = PRICE_ZAR.tier_2_seats[seatCycle];
                const seatUnit = seatCycle === 'monthly' ? '/seat/mo' : '/seat/yr';
                return (
                    <div className="purchase-row">
                        <div className="purchase-row-icon"><Users size={20} /></div>
                        <div className="purchase-row-text">
                            <h3>Team seats</h3>
                            <p>{entitlement.seats_used} of {entitlement.seats_paid} in use · R{seatPrice}{seatUnit}</p>
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
                        <p className="purchase-row-total">R{seatPrice * seatQuantity}{seatUnit}</p>
                        <button className="billing-buy-btn" disabled={busy} onClick={() => buy('tier_2_seats', seatQuantity, seatCycle)}>
                            Add
                        </button>
                    </div>
                );
            })()}
        </section>
    );
```

This is byte-for-byte the same JSX as the current `billing-purchase-card` section — only wrapped in a variable so it can be placed in either position, with `key="purchase-card"` added since it's now used inside a fragment.

- [ ] **Step 4: Define `teamLicenseSection`**

Immediately after `purchaseCardSection` (still before `return (`), add:

```javascript
    const teamLicenseSection = (
        <section className="billing-card" key="team-license">
            <h2><Crown size={20} /> Team License</h2>
            {hideBreakdownDefault && <span className="billing-recommended-badge">Your selected plan</span>}
            <div className="billing-cycle-toggle" role="group" aria-label="Billing cycle">
                <button
                    type="button"
                    className={licenseCycle === 'monthly' ? 'cycle-btn active' : 'cycle-btn'}
                    onClick={() => setLicenseCycle('monthly')}
                >
                    Monthly
                </button>
                <button
                    type="button"
                    className={licenseCycle === 'annual' ? 'cycle-btn active' : 'cycle-btn'}
                    onClick={() => setLicenseCycle('annual')}
                >
                    Annual <span className="cycle-badge">Save ~17%</span>
                </button>
            </div>
            {licenseCycle === 'annual' ? (
                <p>R{PRICE_ZAR.tier_2_license.annual}/yr + R{PRICE_ZAR.tier_2_seats.annual}/seat/yr — unlimited breakdowns for you and your team.</p>
            ) : (
                <p>R{PRICE_ZAR.tier_2_license.monthly}/mo + R{PRICE_ZAR.tier_2_seats.monthly}/seat/mo — unlimited breakdowns for you and your team.</p>
            )}
            <button className="billing-buy-btn" disabled={busy} onClick={() => buy('tier_2_license', 1, licenseCycle)}>
                Subscribe
            </button>
        </section>
    );
```

This is the same as the current Team License section, plus the conditional "Your selected plan" badge. Note this section is only ever rendered when `!isActiveTeam` is already true in both branches of Step 2's JSX (the `hideBreakdownDefault` branch implies `!isActiveTeam` per its own definition; the else branch explicitly checks `!isActiveTeam` before rendering it) — so no extra guard is needed inside `teamLicenseSection` itself.

- [ ] **Step 5: Verify with `npm run build`, then manually**

```bash
cd frontend
npm run build
```
Expected: builds clean, same pre-existing chunk-size warning as before (unrelated to this change), no new errors.

Then manually verify against a real dev server (`npm run dev`) with three account states, using the browser or `curl`-driven Supabase test data if you have it, or by temporarily monkey-patching `useEntitlement`'s return value in a scratch branch to check each case:
1. `signup_plan: 'tier_2_annual_team'`, `tier: 'none'`, `status: 'none'` → Team License card renders first with "Your selected plan" badge, no Breakdown Credits card, and the "Just want to try one breakdown instead?" link is visible. Clicking it reveals the Breakdown Credits card in place.
2. `signup_plan: 'tier_1_pay_per_breakdown'`, `tier: 'none'`, `status: 'none'` → unchanged from before this change: Breakdown Credits card first, Team License card below it, no badge.
3. `signup_plan: 'tier_2_annual_team'`, `tier: 'tier_2_annual_team'`, `status: 'expired'` → Breakdown Credits card first (lapsed account, not "never subscribed"), Team License card below, no badge — same as case 2's layout.

- [ ] **Step 6: Add CSS for the new badge and escape-hatch link**

In `frontend/src/pages/BillingPage.css`, add (near the existing `.billing-cycle-toggle`/`.cycle-btn` rules added for the pricing-cadence work):

```css
.billing-recommended-badge {
    display: inline-block;
    margin: -0.5rem 0 1rem;
    padding: 2px 10px;
    border-radius: 10px;
    background: var(--primary-alpha-15);
    color: var(--primary-400);
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.02em;
}

.billing-try-breakdown-link {
    display: block;
    margin: 0.5rem auto 0;
    padding: 0.5rem;
    background: none;
    border: none;
    color: var(--gray-400);
    font-size: 0.85rem;
    text-decoration: underline;
    cursor: pointer;
    text-align: center;
}

.billing-try-breakdown-link:hover {
    color: var(--gray-200);
}
```

- [ ] **Step 7: Re-run `npm run build` to confirm the CSS compiles**

```bash
cd frontend
npm run build
```
Expected: builds clean.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/BillingPage.jsx frontend/src/pages/BillingPage.css
git commit -m "$(cat <<'EOF'
feat(billing): steer never-subscribed tier_2 signups to the license they picked

BillingPage now shows the Team License card first with a "Your selected
plan" badge, and hides the one-off Breakdown Credits card by default,
for any account whose signup_plan was tier_2_annual_team and has never
actually subscribed to anything (tier/status still 'none'). A low-key
escape-hatch link still lets them buy a single breakdown if they want.
Everyone else's layout is unchanged. See
docs/superpowers/specs/2026-07-31-billing-signup-intent-design.md.
EOF
)"
```

---

## Self-Review Notes

- **Spec coverage:** Trigger condition (Task 2 Step 1), hide/reorder behavior (Task 2 Steps 2-4), escape hatch (Task 2 Steps 2 + 6), backend `signup_plan` field (Task 1) — all covered. Testing section of the spec (backend test + manual frontend check) — covered by Task 1 Step 1 and Task 2 Step 5. Out-of-scope items (checkout/pricing untouched, no persistence of the escape hatch, no change to the analyze-trigger redirect point) — none of the tasks touch those, consistent with the spec.
- **Placeholder scan:** No TBD/TODO; every step has literal code, not descriptions.
- **Type consistency:** `entitlement.signup_plan` (Task 1's new key) is consumed by name in Task 2 exactly as produced. `hideBreakdownDefault`, `showBreakdownCard`, `showBreakdownAnyway`, `purchaseCardSection`, `teamLicenseSection` are each defined once and referenced by the same name everywhere they're used.
