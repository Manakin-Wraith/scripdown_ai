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
