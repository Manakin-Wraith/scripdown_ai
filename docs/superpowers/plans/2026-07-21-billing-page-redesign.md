# Billing Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `/billing` a real visual design pass matching `ProfilePage`'s card-based look, add a "current plan" summary card, and add a TopBar nav entry point so the page is reachable without a contextual upgrade prompt or a manual URL.

**Architecture:** Pure frontend change — no backend, API, or entitlement-logic changes. One nav-wiring change in `TopBar.jsx` (+ a breadcrumb config entry for consistency with `/profile`), one new `BillingPage.css` stylesheet reusing existing design tokens from `ProfilePage.css`, and a JSX-only restructure of `BillingPage.jsx` (all existing state/handlers untouched).

**Tech Stack:** React 18 + Vite (plain JS/JSX), `lucide-react` icons, existing `Spinner` UI component. No test framework exists in `frontend/` (no vitest/jest) — verification is `npm run build` plus manual browser check, per project memory that `npm run lint` is broken repo-wide.

## Global Constraints

- No backend/API/entitlement-logic changes — this is markup + CSS only (spec: "Out of scope").
- Reuse existing CSS custom properties only (`--gray-900/800/700/600/500/300/100`, `--primary-400/500/600`, `--primary-alpha-15/30`, `--space-*`, `--text-*`) — no new tokens invented (spec: "Architecture").
- `/billing` stays its own top-level route; do not nest inside `ProfilePage` (spec: "Decisions").
- Nav entry point goes in the TopBar user dropdown next to "Profile", not the sidebar (spec: "Decisions").
- Tier enum values: `entitlement.tier` is one of `'none'`, `'tier_1_pay_per_breakdown'`, `'tier_2_annual_team'` (confirmed against `backend/services/entitlement_service.py` `TIER_1`/`TIER_2` constants) — do not confuse with PayFast charge types (`'tier_1_credits'`, `'tier_2_license'`, `'tier_2_seats'`), which are a separate value space used only when calling `createCheckout`.
- Gate on `npm run build`, not `npm run lint` (repo-wide lint breakage, unrelated to this work).

---

### Task 1: Add Billing nav entry point

**Files:**
- Modify: `frontend/src/components/layout/TopBar.jsx:1-12` (imports), `:126-132` (dropdown items)
- Modify: `frontend/src/components/layout/Breadcrumb.jsx:11-20` (route config)

**Interfaces:**
- Consumes: existing `navigate` (from `useNavigate()`, already in scope in `TopBar.jsx`), existing `setUserMenuOpen` state setter.
- Produces: nothing consumed by later tasks — this task is nav-only and independent of Tasks 2-3.

- [ ] **Step 1: Add the `CreditCard` icon import**

In `frontend/src/components/layout/TopBar.jsx`, change the `lucide-react` import block:

```jsx
import {
  Library,
  Settings,
  LogOut,
  ChevronDown,
  User,
  CreditCard,
  Film,
  LogIn,
  Shield
} from 'lucide-react';
```

- [ ] **Step 2: Add the Billing dropdown button**

In the same file, find the existing "Profile" dropdown button (currently around line 126-132):

```jsx
                <button 
                  className="dropdown-item"
                  onClick={() => { navigate('/profile'); setUserMenuOpen(false); }}
                >
                  <User size={16} />
                  <span>Profile</span>
                </button>
```

Add a new button immediately after it, before the commented-out Settings block:

```jsx
                <button 
                  className="dropdown-item"
                  onClick={() => { navigate('/profile'); setUserMenuOpen(false); }}
                >
                  <User size={16} />
                  <span>Profile</span>
                </button>
                <button 
                  className="dropdown-item"
                  onClick={() => { navigate('/billing'); setUserMenuOpen(false); }}
                >
                  <CreditCard size={16} />
                  <span>Billing</span>
                </button>
```

- [ ] **Step 3: Add `/billing` to the breadcrumb route config**

In `frontend/src/components/layout/Breadcrumb.jsx`, the `ROUTE_CONFIG` object currently has:

```jsx
const ROUTE_CONFIG = {
    '/scripts': { label: 'My Scripts', parent: null },
    '/scenes/:scriptId': { label: 'Scene Breakdown', parent: '/scripts' },
    '/scripts/:scriptId/stripboard': { label: 'Stripboard', parent: '/scripts' },
    '/scripts/:scriptId/board': { label: 'Board', parent: '/scripts' },
    '/scripts/:scriptId/reports': { label: 'Reports', parent: '/scripts' },
    '/scripts/:scriptId/schedule': { label: 'Schedule', parent: '/scripts' },
    '/upload': { label: 'Upload Script', parent: '/scripts' },
    '/profile': { label: 'Profile', parent: null },
};
```

Add a `/billing` entry matching the existing `/profile` shape:

```jsx
const ROUTE_CONFIG = {
    '/scripts': { label: 'My Scripts', parent: null },
    '/scenes/:scriptId': { label: 'Scene Breakdown', parent: '/scripts' },
    '/scripts/:scriptId/stripboard': { label: 'Stripboard', parent: '/scripts' },
    '/scripts/:scriptId/board': { label: 'Board', parent: '/scripts' },
    '/scripts/:scriptId/reports': { label: 'Reports', parent: '/scripts' },
    '/scripts/:scriptId/schedule': { label: 'Schedule', parent: '/scripts' },
    '/upload': { label: 'Upload Script', parent: '/scripts' },
    '/profile': { label: 'Profile', parent: null },
    '/billing': { label: 'Billing', parent: null },
};
```

- [ ] **Step 4: Build to verify no syntax/import errors**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors (warnings about unrelated existing code, if any, are fine — only new errors matter).

- [ ] **Step 5: Manual check**

Run: `cd frontend && npm run dev`, log in, open the TopBar user dropdown menu. Confirm a "Billing" item with a credit-card icon appears below "Profile", and clicking it navigates to `/billing`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/layout/TopBar.jsx frontend/src/components/layout/Breadcrumb.jsx
git commit -m "feat(nav): add Billing entry to TopBar user dropdown

Billing was previously only reachable via contextual upgrade prompts
or a manual URL. Adds a direct nav entry next to Profile, plus a
breadcrumb config entry matching /profile's."
```

---

### Task 2: Create `BillingPage.css`

**Files:**
- Create: `frontend/src/pages/BillingPage.css`

**Interfaces:**
- Consumes: existing CSS custom properties already defined and used by `frontend/src/pages/ProfilePage.css` (`--gray-900`, `--gray-800`, `--gray-700`, `--gray-600`, `--gray-500`, `--gray-300`, `--gray-100`, `--primary-400`, `--primary-500`, `--primary-600`, `--primary-alpha-15`, `--primary-alpha-30`).
- Produces: class names consumed by Task 3's JSX: `.billing-page`, `.billing-loading`, `.billing-message` (`.error` modifier), `.billing-card`, `.billing-card h2`, `.billing-card h2 svg`, `.plan-summary-card`, `.plan-summary-row`, `.plan-status-badge` (`.active` / `.inactive` modifiers), `.billing-form-group`, `.billing-buy-btn`.

- [ ] **Step 1: Write the stylesheet**

Create `frontend/src/pages/BillingPage.css`:

```css
/* Billing Page Styles */

.billing-page {
    min-height: 100vh;
    background: var(--gray-900);
    padding: 2rem;
}

/* Loading State */
.billing-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 60vh;
    gap: 1rem;
    color: var(--gray-400);
}

/* Error Message */
.billing-message {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.875rem 1rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
    font-size: 0.875rem;
}

.billing-message.error {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #FCA5A5;
}

/* Card layout */
.billing-cards {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    max-width: 640px;
}

.billing-card {
    background: var(--gray-800);
    border: 1px solid var(--gray-700);
    border-radius: 16px;
    padding: 1.5rem;
}

.billing-card h2 {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 0 0 1.5rem;
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--gray-100);
}

.billing-card h2 svg {
    color: var(--primary-400);
}

/* Plan summary card */
.plan-summary-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.5rem 0;
    color: var(--gray-300);
    font-size: 0.95rem;
}

.plan-summary-row + .plan-summary-row {
    border-top: 1px solid var(--gray-700);
}

.plan-status-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.02em;
}

.plan-status-badge.active {
    background: rgba(34, 197, 94, 0.15);
    color: #86EFAC;
}

.plan-status-badge.inactive {
    background: var(--gray-700);
    color: var(--gray-400);
}

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

.billing-form-group select {
    padding: 0.75rem 1rem;
    background: var(--gray-900);
    border: 1px solid var(--gray-600);
    border-radius: 8px;
    color: var(--gray-100);
    font-size: 0.95rem;
    font-family: inherit;
    width: fit-content;
}

.billing-form-group select:focus {
    outline: none;
    border-color: var(--primary-500);
    box-shadow: 0 0 0 3px var(--primary-alpha-15);
}

.billing-total {
    color: var(--gray-100);
    font-weight: 600;
    margin: 0.75rem 0;
}

.billing-buy-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.875rem 1.5rem;
    background: linear-gradient(135deg, var(--primary-500), var(--primary-600));
    border: none;
    border-radius: 10px;
    color: var(--gray-900);
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
}

.billing-buy-btn:hover:not(:disabled) {
    background: linear-gradient(135deg, var(--primary-400), var(--primary-500));
    transform: translateY(-1px);
    box-shadow: 0 4px 12px var(--primary-alpha-30);
}

.billing-buy-btn:disabled {
    opacity: 0.7;
    cursor: not-allowed;
}
```

- [ ] **Step 2: Build to verify the CSS file has no parse errors**

Run: `cd frontend && npm run build`
Expected: build succeeds (the CSS file is not yet imported anywhere, so this mainly confirms no other regressions — the real check happens in Task 3 once it's imported).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/BillingPage.css
git commit -m "style(billing): add BillingPage stylesheet matching ProfilePage tokens"
```

---

### Task 3: Restructure `BillingPage.jsx`

**Files:**
- Modify: `frontend/src/pages/BillingPage.jsx` (full file rewrite of the JSX return + imports; all handlers/state unchanged)

**Interfaces:**
- Consumes: `.billing-page`, `.billing-loading`, `.billing-message`, `.billing-card`, `.plan-summary-card`, `.plan-summary-row`, `.plan-status-badge`, `.billing-form-group`, `.billing-total`, `.billing-buy-btn` (all from Task 2's `BillingPage.css`); `PageHeader` from `frontend/src/components/layout/PageHeader.jsx`; `Spinner` from `frontend/src/components/ui`; `entitlement.tier` values `'none'` / `'tier_1_pay_per_breakdown'` / `'tier_2_annual_team'` and `entitlement.status` (existing shape from `useEntitlement`, unchanged).
- Produces: nothing consumed by other tasks — this is the last task.

- [ ] **Step 1: Rewrite the file**

Replace the full contents of `frontend/src/pages/BillingPage.jsx`:

```jsx
import { useState } from 'react';
import { CreditCard, Wallet, Users, Crown } from 'lucide-react';
import { createCheckout } from '../services/apiService';
import { useEntitlement } from '../hooks/useEntitlement';
import PageHeader from '../components/layout/PageHeader';
import { Spinner } from '../components/ui';
import './BillingPage.css';

// Display only. The server is the authority on price.
const PRICE_ZAR = { tier_1_credits: 450, tier_2_license: 1850, tier_2_seats: 150 };

const TIER_LABELS = {
    none: 'No active plan',
    tier_1_pay_per_breakdown: 'Pay-per-breakdown',
    tier_2_annual_team: 'Annual Team License',
};

const postToPayFast = ({ process_url, fields }) => {
    // PayFast requires a real form POST, not fetch.
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = process_url;
    Object.entries(fields).forEach(([name, value]) => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = name;
        input.value = value;
        form.appendChild(input);
    });
    document.body.appendChild(form);
    form.submit();
};

export default function BillingPage() {
    const { entitlement, loading } = useEntitlement();
    const [quantity, setQuantity] = useState(1);
    const [seatQuantity, setSeatQuantity] = useState(1);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);

    const buy = async (chargeType, qty) => {
        setBusy(true);
        setError(null);
        try {
            postToPayFast(await createCheckout(chargeType, qty));
        } catch {
            setError('Could not start checkout. Please try again.');
            setBusy(false);
        }
    };

    if (loading || !entitlement) {
        return (
            <div className="billing-page">
                <div className="billing-loading">
                    <Spinner size={32} />
                    <p>Loading billing…</p>
                </div>
            </div>
        );
    }

    const isActiveTeam = entitlement.tier === 'tier_2_annual_team' && entitlement.status === 'active';
    const tierLabel = TIER_LABELS[entitlement.tier] || TIER_LABELS.none;

    return (
        <div className="billing-page">
            <PageHeader title="Billing" />

            {error && (
                <div className="billing-message error" role="alert">
                    <span>{error}</span>
                </div>
            )}

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
                        <div className="plan-summary-row">
                            <span>Team seats</span>
                            <span>{entitlement.seats_used} of {entitlement.seats_paid} in use</span>
                        </div>
                    )}
                </section>

                <section className="billing-card">
                    <h2><Wallet size={20} /> Breakdown credits</h2>
                    <p>{entitlement.breakdown_balance} remaining · R{PRICE_ZAR.tier_1_credits} each (incl. VAT)</p>
                    <div className="billing-form-group">
                        <label htmlFor="qty">Quantity</label>
                        <select id="qty" value={quantity}
                                onChange={(e) => setQuantity(Number(e.target.value))}>
                            {[1, 5, 10].map((n) => <option key={n} value={n}>{n}</option>)}
                        </select>
                    </div>
                    <p className="billing-total">Total: R{PRICE_ZAR.tier_1_credits * quantity}</p>
                    <button className="billing-buy-btn" disabled={busy} onClick={() => buy('tier_1_credits', quantity)}>
                        Buy breakdowns
                    </button>
                </section>

                {isActiveTeam ? (
                    <section className="billing-card">
                        <h2><Users size={20} /> Team seats</h2>
                        <p>{entitlement.seats_used} of {entitlement.seats_paid} seats in use</p>
                        <div className="billing-form-group">
                            <label htmlFor="seat-qty">Quantity</label>
                            <select id="seat-qty" value={seatQuantity}
                                    onChange={(e) => setSeatQuantity(Number(e.target.value))}>
                                {[1, 2, 3, 5, 10].map((n) => <option key={n} value={n}>{n}</option>)}
                            </select>
                        </div>
                        <p className="billing-total">Total: R{PRICE_ZAR.tier_2_seats * seatQuantity}/yr</p>
                        <button className="billing-buy-btn" disabled={busy} onClick={() => buy('tier_2_seats', seatQuantity)}>
                            Add {seatQuantity} seat{seatQuantity > 1 ? 's' : ''} — R{PRICE_ZAR.tier_2_seats}/yr each
                        </button>
                    </section>
                ) : (
                    <section className="billing-card">
                        <h2><Crown size={20} /> Annual Team License</h2>
                        <p>R{PRICE_ZAR.tier_2_license}/yr — unlimited breakdowns for you and your team.</p>
                        <button className="billing-buy-btn" disabled={busy} onClick={() => buy('tier_2_license', 1)}>
                            Subscribe
                        </button>
                    </section>
                )}
            </div>
        </div>
    );
}
```

- [ ] **Step 2: Build to verify no syntax/import errors**

Run: `cd frontend && npm run build`
Expected: build succeeds with no new errors.

- [ ] **Step 3: Manual verification in browser**

Run: `cd frontend && npm run dev`, log in, navigate to `/billing` (via the new TopBar dropdown entry from Task 1). Confirm:
- `PageHeader` renders "Billing" as the title.
- A "Current plan" card shows plan label, a status badge, and breakdown credits remaining.
- The "Breakdown credits" card renders with the quantity selector and buy button, styled as a card (gray background, border, rounded corners) rather than plain text.
- Depending on the logged-in account's entitlement state, either the "Team seats" or "Annual Team License" card renders below it — confirm whichever one applies to the test account looks correct; the other branch's correctness is verified by code review since the underlying conditional is unchanged from the original file (only restyled).
- Trigger the error path if possible (e.g. by blocking the network request in devtools) and confirm the error message renders in the new `.billing-message.error` style.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/BillingPage.jsx
git commit -m "feat(billing): redesign BillingPage with card layout and plan summary

Restyles BillingPage to match ProfilePage's card-based design language
(PageHeader, Spinner loading state, styled cards) and adds a new
current-plan summary card. No changes to purchase logic, entitlement
handling, or PayFast integration -- markup/CSS only."
```

---

## Self-Review Notes

- **Spec coverage:** TopBar nav entry ✓ Task 1. Breadcrumb consistency (minor addition beyond spec text but directly supports the "reachable via nav" goal) ✓ Task 1 Step 3. `PageHeader` ✓ Task 3. Card styling matching `ProfilePage` tokens ✓ Task 2. Plan summary card (tier label, status badge, breakdown balance, seat usage when team) ✓ Task 3. Existing three purchase sections restyled, conditional logic unchanged ✓ Task 3. `Spinner` loading state ✓ Task 3. Error state restyled ✓ Task 2 + Task 3. No backend/entitlement changes ✓ no task touches `backend/`.
- **Placeholder scan:** none — every step has literal, complete code.
- **Type/name consistency:** `TIER_LABELS` keys (`none`, `tier_1_pay_per_breakdown`, `tier_2_annual_team`) match the constraint section's confirmed enum values. CSS class names produced by Task 2 (`.billing-page`, `.billing-loading`, `.billing-message`, `.billing-card`, `.plan-summary-card`, `.plan-summary-row`, `.plan-status-badge`, `.billing-form-group`, `.billing-total`, `.billing-buy-btn`) are exactly the set consumed by Task 3's JSX — cross-checked, no mismatches.
