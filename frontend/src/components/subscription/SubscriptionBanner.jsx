/**
 * SubscriptionBanner Component
 * Shows trial/expiration warning banner at top of dashboard.
 */

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Clock, Sparkles, X } from 'lucide-react';
import { useEntitlement } from '../../hooks/useEntitlement';
import './SubscriptionBanner.css';

const TIER_1 = 'tier_1_pay_per_breakdown';

const SubscriptionBanner = () => {
    const { entitlement } = useEntitlement();
    const [dismissed, setDismissed] = useState(false);

    // Only tier 1 (pay-per-breakdown) runs out — tier 2 active is unlimited.
    const outOfCredits = entitlement?.tier === TIER_1 && !entitlement?.can_run_breakdown;

    if (dismissed || !outOfCredits) {
        return null;
    }

    return (
        <div className="subscription-banner banner-warning">
            <div className="subscription-banner-content">
                <Clock size={18} />
                <span>You're out of breakdown credits. Buy more to keep analyzing scenes.</span>
            </div>
            <div className="subscription-banner-actions">
                <Link to="/billing" className="subscription-banner-upgrade">
                    <Sparkles size={14} />
                    Buy Credits
                </Link>
                <button
                    className="subscription-banner-dismiss"
                    onClick={() => setDismissed(true)}
                    aria-label="Dismiss"
                >
                    <X size={16} />
                </button>
            </div>
        </div>
    );
};

export default SubscriptionBanner;
