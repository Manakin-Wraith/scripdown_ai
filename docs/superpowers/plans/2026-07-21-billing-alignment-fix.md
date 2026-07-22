# Billing Alignment Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Center the Billing page's content and give the payment result page (`/payment/success`, `/payment/cancel`) real, centered, card-styled markup consistent with the app's design system.

**Architecture:** Two independent, presentation-only changes in `frontend/src/pages/`: (1) wrap Billing page's header/message/cards in a centered container via one new CSS class; (2) build out `PaymentResultPage.jsx` with a new dedicated stylesheet and per-state `lucide-react` status icons. No business logic, routing, or backend changes in either task.

**Tech Stack:** React 18 (plain JSX, no TypeScript), Vite, `lucide-react` icons, plain CSS with existing design tokens (`--gray-800`, `--gray-900`, `--gray-700`, `--primary-400/500/600`).

## Global Constraints

- Presentation-only: no changes to `BillingPage.jsx`'s checkout/quantity logic, or to `PaymentResultPage.jsx`'s polling `useEffect` or seat-invite redirect `useEffect`.
- Frontend gate is `npm run build`, not `npm run lint` (lint is broken repo-wide — known project issue, not something to fix here).
- Billing page stays a fixed narrow column (max 640px), centered — no multi-column wide-screen layout.
- `PaymentResultPage.css` is its own new file, not a shared import from `BillingPage.css` (kept independently editable per design decision).
- Icon color tokens must match existing usage: success `#86EFAC`, error/cancel `#FCA5A5`, neutral `var(--gray-400)`.

---

### Task 1: Center the Billing page content

**Files:**
- Modify: `frontend/src/pages/BillingPage.jsx:66-168` (wrap return JSX)
- Modify: `frontend/src/pages/BillingPage.css:37-43` (add new class)

**Interfaces:**
- Consumes: existing `PageHeader`, `error` state, `entitlement`/`isActiveTeam`/`tierLabel` — no signature changes.
- Produces: nothing consumed by other tasks (this task is self-contained).

- [ ] **Step 1: Add the `.billing-content` wrapper CSS**

In `frontend/src/pages/BillingPage.css`, insert a new rule immediately before the existing `/* Card layout */` comment (currently at line 37):

```css
/* Centered content column */
.billing-content {
    max-width: 640px;
    margin: 0 auto;
}

/* Card layout */
.billing-cards {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    max-width: 640px;
}
```

(This replaces the existing `/* Card layout */` block header line — the `.billing-cards` rule body itself is unchanged, just now preceded by the new `.billing-content` rule.)

- [ ] **Step 2: Wrap the page's JSX in `.billing-content`**

In `frontend/src/pages/BillingPage.jsx`, change the main return block (lines 66-168) from:

```jsx
    return (
        <div className="billing-page">
            <PageHeader title="Billing" />

            {error && (
                <div className="billing-message error" role="alert">
                    <span>{error}</span>
                </div>
            )}

            <div className="billing-cards">
```

to:

```jsx
    return (
        <div className="billing-page">
            <div className="billing-content">
                <PageHeader title="Billing" />

                {error && (
                    <div className="billing-message error" role="alert">
                        <span>{error}</span>
                    </div>
                )}

                <div className="billing-cards">
```

And change the closing tags at the end of the same return block from:

```jsx
                )}
            </div>
        </div>
    );
}
```

to:

```jsx
                )}
                </div>
            </div>
        </div>
    );
}
```

Re-indent the JSX between the wrapper's opening and closing tags (the `<section className="billing-card ...">` blocks) one level deeper to match — this is a pure indentation change, no logic changes to any `section` block's contents.

- [ ] **Step 3: Build and manually verify**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors.

Then run `npm run dev`, open `/billing` in a browser at a wide viewport (e.g. resize to 1440px wide), and confirm the header, any error banner, and the card stack all sit centered as one column rather than hugging the left edge.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/BillingPage.jsx frontend/src/pages/BillingPage.css
git commit -m "fix(billing): center Billing page content instead of left-aligned"
```

---

### Task 2: Style the payment result page with centered, card-based layout and status icons

**Files:**
- Create: `frontend/src/pages/PaymentResultPage.css`
- Modify: `frontend/src/pages/PaymentResultPage.jsx` (full file rewrite of the render section, lines 1-69)

**Interfaces:**
- Consumes: existing `outcome` prop (`'success'` | `'cancel'`, passed from `App.jsx` routes `payment/success` / `payment/cancel`), existing `settled` derivation, existing `params`, existing `readPendingSeatInviteDraft` import — no signature changes.
- Produces: nothing consumed by other tasks (this task is self-contained).

- [ ] **Step 1: Create `PaymentResultPage.css`**

```css
/* Payment Result Page Styles */

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

.payment-result-icon.success {
    color: #86EFAC;
}

.payment-result-icon.pending {
    color: var(--gray-400);
}

.payment-result-icon.cancel {
    color: #FCA5A5;
}

.payment-result-card h1 {
    margin: 0 0 0.75rem;
    font-size: 1.375rem;
    font-weight: 600;
    color: var(--gray-100);
}

.payment-result-card p {
    margin: 0 0 1.5rem;
    color: var(--gray-300);
    font-size: 0.95rem;
    line-height: 1.5;
}

.payment-result-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.75rem 1.5rem;
    background: linear-gradient(135deg, var(--primary-500), var(--primary-600));
    border-radius: 10px;
    color: var(--gray-900);
    font-size: 0.95rem;
    font-weight: 600;
    text-decoration: none;
    transition: all 0.2s ease;
}

.payment-result-link:hover {
    background: linear-gradient(135deg, var(--primary-400), var(--primary-500));
    transform: translateY(-1px);
    box-shadow: 0 4px 12px var(--primary-alpha-30);
}
```

- [ ] **Step 2: Run build to confirm the new CSS file alone doesn't break anything**

Run: `cd frontend && npm run build`
Expected: build succeeds (CSS file isn't imported yet, so this just confirms no syntax errors are picked up by any glob).

- [ ] **Step 3: Rewrite `PaymentResultPage.jsx` to use the new styles and icons**

Replace the full file contents with:

```jsx
import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { CheckCircle, Clock, XCircle } from 'lucide-react';
import { useEntitlement } from '../hooks/useEntitlement';
import { readPendingSeatInviteDraft } from '../utils/pendingSeatInviteDraft';
import './PaymentResultPage.css';

export default function PaymentResultPage({ outcome }) {
    const [params] = useSearchParams();
    const navigate = useNavigate();
    const { entitlement, refetch } = useEntitlement();
    const [waited, setWaited] = useState(0);

    // The ITN is a separate server-to-server call and may land after the
    // browser gets back here, so poll briefly rather than claim failure.
    useEffect(() => {
        if (outcome !== 'success' || waited >= 5) return;
        const t = setTimeout(() => { refetch(); setWaited((w) => w + 1); }, 2000);
        return () => clearTimeout(t);
    }, [outcome, waited, refetch]);

    const settled = entitlement?.can_run_breakdown || entitlement?.can_use_teams;

    // A seat purchase started from the invite modal's "buy seats" panel
    // stashes a draft before redirecting to PayFast — once the purchase
    // settles, send the Owner back to finish that invite instead of the
    // generic landing. The draft itself (email/department/role) is left
    // in sessionStorage for TeamDrawer (Task 7) to read and clear — this
    // page only needs scriptId to know where to route.
    //
    // This can't reuse the generic `settled` flag above: a tier_2_seats
    // purchase is only ever made by an owner who already has
    // can_use_teams/can_run_breakdown true *before* paying (seat count
    // doesn't gate those flags — see entitlement_service.py), so `settled`
    // is already true on the very first render and would fire the redirect
    // before the ITN has actually granted the seat. Instead, compare
    // entitlement.seats_paid against the pre-purchase baseline captured in
    // the draft, and only redirect once the pool has actually grown.
    useEffect(() => {
        if (outcome !== 'success' || params.get('type') !== 'tier_2_seats' || !entitlement) return;
        const draft = readPendingSeatInviteDraft();
        if (!draft?.scriptId) return;
        const baseline = draft.seatsPaidBaseline ?? 0;
        if (entitlement.seats_paid > baseline) {
            navigate(`/scenes/${draft.scriptId}?resume_invite=1`, { replace: true });
        }
    }, [outcome, params, entitlement, navigate]);

    if (outcome === 'cancel') {
        return (
            <div className="payment-result-page">
                <div className="payment-result-card">
                    <XCircle size={40} className="payment-result-icon cancel" />
                    <h1>Payment cancelled</h1>
                    <p>You have not been charged.</p>
                    <Link to="/billing" className="payment-result-link">Back to billing</Link>
                </div>
            </div>
        );
    }

    return (
        <div className="payment-result-page">
            <div className="payment-result-card">
                {settled ? (
                    <>
                        <CheckCircle size={40} className="payment-result-icon success" />
                        <h1>Thank you</h1>
                        <p>Your purchase is active. Type: {params.get('type')}</p>
                    </>
                ) : (
                    <>
                        <Clock size={40} className="payment-result-icon pending" />
                        <h1>Thank you</h1>
                        <p>Payment received — confirming with our payment provider. This
                           usually takes a few seconds.</p>
                    </>
                )}
                <Link to="/" className="payment-result-link">Continue</Link>
            </div>
        </div>
    );
}
```

- [ ] **Step 4: Build and manually verify all three states**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors.

Then run `npm run dev` and check in a browser:
- `/payment/cancel` — centered card, red `XCircle` icon, "Payment cancelled" heading, "Back to billing" button.
- `/payment/success?type=tier_1_credits` — centered card; if entitlement isn't yet settled you'll see the gray `Clock` icon and "confirming" copy, then (once entitlement refetches as active) the green `CheckCircle` icon and "Your purchase is active" copy.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/PaymentResultPage.jsx frontend/src/pages/PaymentResultPage.css
git commit -m "feat(billing): style payment result page with centered card and status icons"
```

---

### Task 3: Update BACKLOG.md to mark this item resolved

**Files:**
- Modify: `docs/BACKLOG.md` (the "Billing page and payment success messages — misaligned" entry)

**Interfaces:**
- Consumes: nothing (doc-only task).
- Produces: nothing.

- [ ] **Step 1: Mark the backlog entry resolved**

In `docs/BACKLOG.md`, find the entry titled `## Billing page and payment success messages — misaligned (screen-left instead of centered)` and replace its `**Status:**` line and body with:

```markdown
## Billing page and payment success messages — misaligned (screen-left instead of centered) — RESOLVED, fixed

**Status:** Done. Brainstormed, designed, planned, and implemented 2026-07-21.

**What shipped.** `BillingPage.jsx`/`.css` — header, error message, and the
card stack are now wrapped in a `.billing-content` container
(`max-width: 640px; margin: 0 auto;`), centering the page's content instead
of leaving it flush against the left padding on wide screens.
`PaymentResultPage.jsx` gained a dedicated `PaymentResultPage.css` and is now
a centered, card-styled result screen (matching `.billing-card`'s token
palette) with a per-state `lucide-react` icon: green `CheckCircle` once
settled, gray `Clock` while confirming, red `XCircle` on cancel. No changes
to checkout logic, polling, or the seat-invite resume redirect.

**References.**
- Design: `docs/superpowers/specs/2026-07-21-billing-alignment-fix-design.md`
- Plan: `docs/superpowers/plans/2026-07-21-billing-alignment-fix.md`
- `frontend/src/pages/BillingPage.jsx`, `BillingPage.css`
- `frontend/src/pages/PaymentResultPage.jsx`, `PaymentResultPage.css` (new)
```

- [ ] **Step 2: Commit**

```bash
git add docs/BACKLOG.md
git commit -m "docs: mark billing alignment backlog item resolved"
```
