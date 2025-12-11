/**
 * SubscriptionBanner Component
 * Shows trial/expiration warning banner at top of dashboard.
 */

import React, { useState } from 'react';
import { Clock, Sparkles, X } from 'lucide-react';
import { useSubscription } from '../../hooks/useSubscription';
import UpgradeModal from './UpgradeModal';
import './SubscriptionBanner.css';

const SubscriptionBanner = () => {
    const { status, daysRemaining, shouldShowUpgradePrompt, message } = useSubscription();
    const [dismissed, setDismissed] = useState(false);
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);

    if (dismissed || !shouldShowUpgradePrompt()) {
        return null;
    }

    const getBannerStyle = () => {
        if (status === 'expired') return 'banner-expired';
        if (daysRemaining <= 3) return 'banner-urgent';
        return 'banner-warning';
    };

    const getBannerMessage = () => {
        if (status === 'expired') {
            return 'Your access has expired. Upgrade now to continue using SlateOne.';
        }
        if (status === 'trial') {
            return `Your trial ends in ${daysRemaining} ${daysRemaining === 1 ? 'day' : 'days'}. Upgrade to keep your scripts.`;
        }
        if (status === 'active' && daysRemaining <= 14) {
            return `Your subscription expires in ${daysRemaining} days. Renew to continue.`;
        }
        return message;
    };

    return (
        <>
            <div className={`subscription-banner ${getBannerStyle()}`}>
                <div className="subscription-banner-content">
                    <Clock size={18} />
                    <span>{getBannerMessage()}</span>
                </div>
                <div className="subscription-banner-actions">
                    <button 
                        className="subscription-banner-upgrade"
                        onClick={() => setShowUpgradeModal(true)}
                    >
                        <Sparkles size={14} />
                        Upgrade Now
                    </button>
                    {status !== 'expired' && (
                        <button 
                            className="subscription-banner-dismiss"
                            onClick={() => setDismissed(true)}
                            aria-label="Dismiss"
                        >
                            <X size={16} />
                        </button>
                    )}
                </div>
            </div>

            <UpgradeModal
                isOpen={showUpgradeModal}
                onClose={() => setShowUpgradeModal(false)}
                daysRemaining={daysRemaining}
                isExpired={status === 'expired'}
            />
        </>
    );
};

export default SubscriptionBanner;
