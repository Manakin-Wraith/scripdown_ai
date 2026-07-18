import { useState } from 'react';
import { createCheckout } from '../services/apiService';
import { useEntitlement } from '../hooks/useEntitlement';

// Display only. The server is the authority on price.
const PRICE_ZAR = { tier_1_credits: 450, tier_2_license: 1850, tier_2_seats: 150 };

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

    if (loading || !entitlement) return <div>Loading…</div>;

    return (
        <div className="billing-page">
            <h1>Billing</h1>
            {error && <p role="alert">{error}</p>}

            <section>
                <h2>Breakdown credits</h2>
                <p>{entitlement.breakdown_balance} remaining · R{PRICE_ZAR.tier_1_credits} each (incl. VAT)</p>
                <label htmlFor="qty">Quantity</label>
                <select id="qty" value={quantity}
                        onChange={(e) => setQuantity(Number(e.target.value))}>
                    {[1, 5, 10].map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
                <p>Total: R{PRICE_ZAR.tier_1_credits * quantity}</p>
                <button disabled={busy} onClick={() => buy('tier_1_credits', quantity)}>
                    Buy breakdowns
                </button>
            </section>

            {entitlement.tier === 'tier_2_annual_team' && entitlement.status === 'active' ? (
                <section>
                    <h2>Team seats</h2>
                    <p>{entitlement.seats_used} of {entitlement.seats_paid} seats in use</p>
                    <label htmlFor="seat-qty">Quantity</label>
                    <select id="seat-qty" value={seatQuantity}
                            onChange={(e) => setSeatQuantity(Number(e.target.value))}>
                        {[1, 2, 3, 5, 10].map((n) => <option key={n} value={n}>{n}</option>)}
                    </select>
                    <p>Total: R{PRICE_ZAR.tier_2_seats * seatQuantity}/yr</p>
                    <button disabled={busy} onClick={() => buy('tier_2_seats', seatQuantity)}>
                        Add {seatQuantity} seat{seatQuantity > 1 ? 's' : ''} — R{PRICE_ZAR.tier_2_seats}/yr each
                    </button>
                </section>
            ) : (
                <section>
                    <h2>Annual Team License</h2>
                    <p>R{PRICE_ZAR.tier_2_license}/yr — unlimited breakdowns for you and your team.</p>
                    <button disabled={busy} onClick={() => buy('tier_2_license', 1)}>
                        Subscribe
                    </button>
                </section>
            )}
        </div>
    );
}
