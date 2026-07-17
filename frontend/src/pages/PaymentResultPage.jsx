import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useEntitlement } from '../hooks/useEntitlement';

export default function PaymentResultPage({ outcome }) {
    const [params] = useSearchParams();
    const { entitlement, refetch } = useEntitlement();
    const [waited, setWaited] = useState(0);

    // The ITN is a separate server-to-server call and may land after the
    // browser gets back here, so poll briefly rather than claim failure.
    useEffect(() => {
        if (outcome !== 'success' || waited >= 5) return;
        const t = setTimeout(() => { refetch(); setWaited((w) => w + 1); }, 2000);
        return () => clearTimeout(t);
    }, [outcome, waited, refetch]);

    if (outcome === 'cancel') {
        return (
            <div>
                <h1>Payment cancelled</h1>
                <p>You have not been charged.</p>
                <Link to="/billing">Back to billing</Link>
            </div>
        );
    }

    const settled = entitlement?.can_run_breakdown || entitlement?.can_use_teams;

    return (
        <div>
            <h1>Thank you</h1>
            {settled ? (
                <p>Your purchase is active. Type: {params.get('type')}</p>
            ) : (
                <p>Payment received — confirming with our payment provider. This
                   usually takes a few seconds.</p>
            )}
            <Link to="/">Continue</Link>
        </div>
    );
}
