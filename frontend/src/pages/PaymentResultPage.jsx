import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useEntitlement } from '../hooks/useEntitlement';
import { readPendingSeatInviteDraft } from '../utils/pendingSeatInviteDraft';

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
    useEffect(() => {
        if (outcome !== 'success' || params.get('type') !== 'tier_2_seats' || !settled) return;
        const draft = readPendingSeatInviteDraft();
        if (draft?.scriptId) {
            navigate(`/scenes/${draft.scriptId}?resume_invite=1`, { replace: true });
        }
    }, [outcome, params, settled, navigate]);

    if (outcome === 'cancel') {
        return (
            <div>
                <h1>Payment cancelled</h1>
                <p>You have not been charged.</p>
                <Link to="/billing">Back to billing</Link>
            </div>
        );
    }

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
