/**
 * CreditPurchaseModal Component
 * Clean pricing modal for purchasing screenplay breakdown credits
 */

import React, { useState, useEffect } from 'react';
import { X, Shield } from 'lucide-react';
import { useCredits } from '../../hooks/useCredits';
import './CreditPurchaseModal.css';

const YOCO_PAYLINKS = {
    single: 'https://pay.yoco.com/celebration-house-entertainment?amount=500.00&reference=single_breakdown',
    pack_5: 'https://pay.yoco.com/celebration-house-entertainment?amount=2000.00&reference=pack_5_breakdowns',
    pack_10: 'https://pay.yoco.com/celebration-house-entertainment?amount=3500.00&reference=pack_10_breakdowns',
    pack_25: 'https://pay.yoco.com/celebration-house-entertainment?amount=7500.00&reference=pack_25_breakdowns'
};

const DISPLAY_ORDER = ['single', 'pack_5', 'pack_10', 'pack_25'];

const CreditPurchaseModal = ({ isOpen, onClose }) => {
    const [packages, setPackages] = useState(null);
    const [selectedPackage, setSelectedPackage] = useState(null);
    const [loading, setLoading] = useState(true);
    const { getPackages, createPurchase } = useCredits();

    useEffect(() => {
        if (isOpen) {
            loadPackages();
        }
    }, [isOpen]);

    const loadPackages = async () => {
        setLoading(true);
        const pkgs = await getPackages();
        setPackages(pkgs);
        setLoading(false);
    };

    const handlePurchase = async (packageType) => {
        setSelectedPackage(packageType);
        const result = await createPurchase(packageType);
        if (result.success) {
            const paylink = YOCO_PAYLINKS[packageType];
            if (paylink) {
                window.location.href = paylink;
            } else {
                alert('Payment link not configured for this package');
            }
        } else {
            alert('Failed to create purchase: ' + result.error);
            setSelectedPackage(null);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="bm-overlay" onClick={onClose}>
            <div className="bm-modal" onClick={(e) => e.stopPropagation()}>

                {/* Header */}
                <div className="bm-header">
                    <div>
                        <h2 className="bm-title">Choose Your Plan</h2>
                    </div>
                    <button className="bm-close" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                {/* Pricing rows */}
                <div className="bm-body">
                    {loading ? (
                        <div className="bm-loading">
                            <div className="bm-spinner" />
                            <span>Loading plans...</span>
                        </div>
                    ) : (
                        <div className="bm-plans">
                            {packages && DISPLAY_ORDER
                                .filter(key => packages[key])
                                .map(key => {
                                    const pkg = packages[key];
                                    const best = key === 'pack_10';
                                    const isProcessing = selectedPackage === key;

                                    return (
                                        <div key={key} className={`bm-row ${best ? 'bm-row--best' : ''}`}>

                                            {best && <span className="bm-badge">Best Value</span>}

                                            {/* Left: plan info */}
                                            <div className="bm-row-info">
                                                <span className="bm-row-name">{pkg.name}</span>
                                                <span className="bm-row-meta">
                                                    R{pkg.per_breakdown.toFixed(0)}/breakdown
                                                </span>
                                            </div>

                                            {/* Center: savings */}
                                            {pkg.savings && (
                                                <span className="bm-row-save">-{pkg.savings}</span>
                                            )}

                                            {/* Right: price + CTA */}
                                            <div className="bm-row-action">
                                                <span className="bm-row-price">
                                                    R{pkg.price.toLocaleString('en-ZA')}
                                                </span>
                                                <button
                                                    className={`bm-btn ${best ? 'bm-btn--best' : ''}`}
                                                    disabled={isProcessing}
                                                    onClick={() => handlePurchase(key)}
                                                >
                                                    {isProcessing ? 'Processing...' : 'Select'}
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="bm-footer">
                    <Shield size={14} />
                    <span>Secure payment via Yoco</span>
                </div>
            </div>
        </div>
    );
};

export default CreditPurchaseModal;
