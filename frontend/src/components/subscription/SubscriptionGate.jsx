/**
 * SubscriptionGate Component
 * Wraps content that requires specific subscription features.
 * Shows blur preview with upgrade prompt for locked features.
 */

import React, { useState } from 'react';
import { Lock, Sparkles } from 'lucide-react';
import { useSubscription } from '../../hooks/useSubscription';
import UpgradeModal from './UpgradeModal';
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
    const { canAccess, status, daysRemaining } = useSubscription();
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);

    const hasAccess = canAccess(feature);

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
        if (status === 'expired') return 'Your subscription has expired';
        if (status === 'trial') return `Upgrade to access ${formatFeature(feature)}`;
        return 'This feature requires an active subscription';
    };

    return (
        <>
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
                        <button 
                            className="subscription-gate-btn"
                            onClick={() => setShowUpgradeModal(true)}
                        >
                            <Sparkles size={16} />
                            Upgrade Now
                        </button>
                    </div>
                </div>
            </div>

            <UpgradeModal
                isOpen={showUpgradeModal}
                onClose={() => setShowUpgradeModal(false)}
                feature={feature}
                daysRemaining={daysRemaining}
                isExpired={status === 'expired'}
            />
        </>
    );
};

export default SubscriptionGate;
