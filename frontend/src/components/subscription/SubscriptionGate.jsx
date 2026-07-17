/**
 * SubscriptionGate Component
 * Wraps content that requires specific subscription features.
 * Shows blur preview with upgrade prompt for locked features.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { Lock, Sparkles } from 'lucide-react';
import { useEntitlement } from '../../hooks/useEntitlement';
import './SubscriptionGate.css';

const SubscriptionGate = ({
    feature,
    children,
    fallback = null,
    showBlur = true,
    blurAmount = 8,
    showLockIcon = true,
    customMessage = null
}) => {
    const { entitlement } = useEntitlement();

    const hasAccess = entitlement?.can_run_breakdown ?? false;

    if (hasAccess) {
        return <>{children}</>;
    }

    // If fallback provided and no blur, show fallback
    if (fallback && !showBlur) {
        return <>{fallback}</>;
    }

    const formatFeature = (feat) => {
        return feat.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    };

    const getMessage = () => {
        if (customMessage) return customMessage;
        return `Buy breakdown credits to unlock ${formatFeature(feature)}`;
    };

    return (
        <div className="subscription-gate">
            {/* Blurred content preview */}
            {showBlur && (
                <div
                    className="subscription-gate-blur"
                    style={{ filter: `blur(${blurAmount}px)` }}
                >
                    {children}
                </div>
            )}

            {/* Lock overlay */}
            <div className="subscription-gate-overlay">
                <div className="subscription-gate-content">
                    {showLockIcon && (
                        <div className="subscription-gate-icon">
                            <Lock size={24} />
                        </div>
                    )}
                    <p className="subscription-gate-message">{getMessage()}</p>
                    <Link to="/billing" className="subscription-gate-btn">
                        <Sparkles size={16} />
                        Go to Billing
                    </Link>
                </div>
            </div>
        </div>
    );
};

export default SubscriptionGate;
