import { useState } from 'react';
import { CreditCard, Wallet, Users, Crown } from 'lucide-react';
import { createCheckout } from '../services/apiService';
import { useEntitlement } from '../hooks/useEntitlement';
import { isNeverSubscribedTeamIntent } from '../utils/billingIntent';
import PageHeader from '../components/layout/PageHeader';
import { Spinner } from '../components/ui';
import './BillingPage.css';

// Display only. The server is the authority on price. Longer cadences are
// a discounted prepay of the same license, not a separate product. Extra
// seats beyond the cadence's included count are always a flat R250/month.
const PRICE_ZAR = {
    tier_1_credits: 2250,
    tier_2_license: { monthly: 1850, '3month': 5500, '6month': 9500, annual: 18500 },
    tier_2_seats: { monthly: 250, '3month': 750, '6month': 1500, annual: 3000 },
};

// Seats bundled free with each cadence (entitlement_service.INCLUDED_SEATS).
const INCLUDED_SEATS = { monthly: 0, '3month': 1, '6month': 2, annual: 3 };

const CYCLE_LABELS = { monthly: 'Monthly', '3month': '3-Month', '6month': '6-Month', annual: 'Annual' };
const CYCLE_UNITS = { monthly: '/mo', '3month': '/3mo', '6month': '/6mo', annual: '/yr' };
const CYCLE_SEAT_UNITS = { monthly: '/seat/mo', '3month': '/seat (3mo)', '6month': '/seat (6mo)', annual: '/seat/yr' };
// Savings vs. the monthly baseline, on a true monthly-equivalent basis.
// 3-month's equivalent (~R1,833/mo) isn't a meaningful discount, so no badge.
const CYCLE_BADGES = { '6month': 'Save ~14%', annual: 'Save ~17%' };

const TIER_LABELS = {
    none: 'No active plan',
    tier_1_pay_per_breakdown: 'Pay-per-breakdown',
    tier_2_annual_team: 'Team License',
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
    // Cadence for a NEW license purchase. An existing seat purchase always
    // follows the account's already-active cycle (entitlement.billing_cycle)
    // — seats share the license's term, they don't pick their own.
    const [licenseCycle, setLicenseCycle] = useState('annual');
    const [showBreakdownAnyway, setShowBreakdownAnyway] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);

    const buy = async (chargeType, qty, billingCycle = 'annual') => {
        setBusy(true);
        setError(null);
        try {
            postToPayFast(await createCheckout(chargeType, qty, billingCycle));
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

    // A user who told us at signup they wanted the Team License, and has
    // never actually subscribed to anything (tier/status still 'none' —
    // not lapsed, not active), should see that plan first instead of
    // defaulting into a one-off breakdown purchase. The moment they ever
    // subscribe, subscription_plan/status move off 'none' permanently
    // (see entitlement_service.activate_license), so this self-clears —
    // no separate "has ever subscribed" bookkeeping needed.
    const hideBreakdownDefault = isNeverSubscribedTeamIntent(entitlement) && !isActiveTeam;
    const showBreakdownCard = !hideBreakdownDefault || showBreakdownAnyway;

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
                // Seats always follow the license's own cycle — they
                // share its term, they don't pick a separate one.
                const seatCycle = entitlement.billing_cycle in PRICE_ZAR.tier_2_seats
                    ? entitlement.billing_cycle : 'annual';
                const seatPrice = PRICE_ZAR.tier_2_seats[seatCycle];
                const seatUnit = CYCLE_SEAT_UNITS[seatCycle];
                const included = INCLUDED_SEATS[seatCycle];
                return (
                    <div className="purchase-row">
                        <div className="purchase-row-icon"><Users size={20} /></div>
                        <div className="purchase-row-text">
                            <h3>Team seats</h3>
                            <p>
                                {entitlement.seats_used} of {entitlement.seats_paid} in use
                                {included > 0 && ` (${included} included)`} · R{seatPrice}{seatUnit} extra
                            </p>
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

    const teamLicenseSection = (
        <section className="billing-card" key="team-license">
            <h2><Crown size={20} /> Team License</h2>
            {hideBreakdownDefault && <span className="billing-recommended-badge">Your selected plan</span>}
            <div className="billing-cycle-toggle" role="group" aria-label="Billing cycle">
                {Object.keys(CYCLE_LABELS).map((cycle) => (
                    <button
                        key={cycle}
                        type="button"
                        className={licenseCycle === cycle ? 'cycle-btn active' : 'cycle-btn'}
                        onClick={() => setLicenseCycle(cycle)}
                    >
                        {CYCLE_LABELS[cycle]}
                        {CYCLE_BADGES[cycle] && <span className="cycle-badge">{CYCLE_BADGES[cycle]}</span>}
                    </button>
                ))}
            </div>
            {(() => {
                const included = INCLUDED_SEATS[licenseCycle];
                const seatsCopy = included > 0
                    ? `includes ${included} seat${included > 1 ? 's' : ''}`
                    : 'no seats included';
                return (
                    <p>
                        R{PRICE_ZAR.tier_2_license[licenseCycle]}{CYCLE_UNITS[licenseCycle]} — {seatsCopy}, unlimited breakdowns.
                        {' '}Extra seats R{PRICE_ZAR.tier_2_seats[licenseCycle]}{CYCLE_SEAT_UNITS[licenseCycle]}.
                    </p>
                );
            })()}
            <button className="billing-buy-btn" disabled={busy} onClick={() => buy('tier_2_license', 1, licenseCycle)}>
                Subscribe
            </button>
        </section>
    );

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
                                    <span>{CYCLE_LABELS[entitlement.billing_cycle] || 'Annual'}</span>
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
            </div>
        </div>
    );
}
