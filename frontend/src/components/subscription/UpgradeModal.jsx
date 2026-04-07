/**
 * UpgradeModal Component
 * Displays upgrade prompt with Wise payment link.
 */

import React from 'react';
import { X, Sparkles, Check, CreditCard, Clock } from 'lucide-react';
import './UpgradeModal.css';

const WISE_PAYMENT_LINK = 'https://wise.com/pay/r/8j9W0j5SUuPivxk';

const UpgradeModal = ({ 
    isOpen, 
    onClose, 
    feature = null,
    title = 'Unlock Unlimited Access',
    message = null,
    daysRemaining = null,
    isExpired = false
}) => {
    if (!isOpen) return null;

    const handleUpgrade = () => {
        window.open(WISE_PAYMENT_LINK, '_blank');
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
        if (feature) return `This feature requires an active subscription. Subscribe now to unlock ${formatFeature(feature)} and all other premium features.`;
        return 'Get unlimited access to SlateOne for $49/month.';
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
                        <span className="price-amount">$49</span>
                        <span className="price-period">/month</span>
                    </div>
                    <p className="price-note">Unlimited breakdowns • Full production infrastructure</p>
                </div>

                <div className="upgrade-modal-actions">
                    <button className="upgrade-btn-primary" onClick={handleUpgrade}>
                        <CreditCard size={18} />
                        Subscribe Now — $49/month
                    </button>
                    <button className="upgrade-btn-secondary" onClick={onClose}>
                        Maybe Later
                    </button>
                </div>

                <p className="upgrade-modal-footer">
                    Secure payment via Wise. Access activated after payment verification.
                </p>
            </div>
        </div>
    );
};

export default UpgradeModal;
