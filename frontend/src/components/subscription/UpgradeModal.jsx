/**
 * UpgradeModal Component
 * Displays upgrade prompt with Yoco payment link.
 */

import React from 'react';
import { X, Sparkles, Check, CreditCard, Clock } from 'lucide-react';
import './UpgradeModal.css';

const YOCO_PAYMENT_LINK = 'https://pay.yoco.com/r/mEDpxp';

const UpgradeModal = ({ 
    isOpen, 
    onClose, 
    feature = null,
    title = 'Unlock Full Beta Access',
    message = null,
    daysRemaining = null,
    isExpired = false
}) => {
    if (!isOpen) return null;

    const handleUpgrade = () => {
        window.open(YOCO_PAYMENT_LINK, '_blank');
    };

    const getTitle = () => {
        if (isExpired) return 'Your Access Has Expired';
        if (daysRemaining !== null && daysRemaining <= 3) return `Only ${daysRemaining} Days Left!`;
        if (feature) return `Upgrade to Access ${formatFeature(feature)}`;
        return title;
    };

    const getMessage = () => {
        if (message) return message;
        if (isExpired) return 'Renew your subscription to continue using SlateOne and keep all your scripts.';
        if (feature) return `This feature requires an active subscription. Upgrade now to unlock ${formatFeature(feature)} and all other premium features.`;
        return 'Get 1 year of full access to SlateOne for a one-time payment of R249.';
    };

    const formatFeature = (feat) => {
        return feat.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    };

    return (
        <div className="upgrade-modal-overlay" onClick={onClose}>
            <div className="upgrade-modal" onClick={e => e.stopPropagation()}>
                <button className="upgrade-modal-close" onClick={onClose}>
                    <X size={20} />
                </button>

                <div className="upgrade-modal-header">
                    <div className="upgrade-modal-icon">
                        <Sparkles size={32} />
                    </div>
                    <h2>{getTitle()}</h2>
                    <p>{getMessage()}</p>
                </div>

                {daysRemaining !== null && daysRemaining > 0 && !isExpired && (
                    <div className="upgrade-modal-urgency">
                        <Clock size={16} />
                        <span>{daysRemaining} {daysRemaining === 1 ? 'day' : 'days'} remaining</span>
                    </div>
                )}

                <div className="upgrade-modal-features">
                    <h3>What you'll get:</h3>
                    <ul>
                        <li>
                            <Check size={16} />
                            <span>Unlimited script uploads</span>
                        </li>
                        <li>
                            <Check size={16} />
                            <span>Full AI-powered breakdown</span>
                        </li>
                        <li>
                            <Check size={16} />
                            <span>Team collaboration (up to 10 members)</span>
                        </li>
                        <li>
                            <Check size={16} />
                            <span>Reports & PDF exports</span>
                        </li>
                        <li>
                            <Check size={16} />
                            <span>Stripboard editing</span>
                        </li>
                        <li>
                            <Check size={16} />
                            <span>Department notes</span>
                        </li>
                    </ul>
                </div>

                <div className="upgrade-modal-pricing">
                    <div className="upgrade-modal-price">
                        <span className="price-amount">R249</span>
                        <span className="price-period">for 1 year</span>
                    </div>
                    <p className="price-note">One-time payment • No recurring charges</p>
                </div>

                <div className="upgrade-modal-actions">
                    <button className="upgrade-btn-primary" onClick={handleUpgrade}>
                        <CreditCard size={18} />
                        Pay & Upgrade Now
                    </button>
                    <button className="upgrade-btn-secondary" onClick={onClose}>
                        Maybe Later
                    </button>
                </div>

                <p className="upgrade-modal-footer">
                    Secure payment via Yoco. Your access will be activated immediately.
                </p>
            </div>
        </div>
    );
};

export default UpgradeModal;
