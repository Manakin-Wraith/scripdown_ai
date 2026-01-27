/**
 * CreditPurchaseModal Component
 * Modal for selecting and purchasing credit packages
 */

import React, { useState, useEffect } from 'react';
import { X, Coins, Check, TrendingUp, Zap, Crown } from 'lucide-react';
import { useCredits } from '../../hooks/useCredits';
import './CreditPurchaseModal.css';

const YOCO_PAYLINKS = {
    single: 'https://pay.yoco.com/r/4aQyxM',
    pack_5: 'https://pay.yoco.com/r/4W9Vev',
    pack_10: 'https://pay.yoco.com/r/78j6rk',
    pack_25: 'https://pay.yoco.com/r/2Q1ZLN'
};

const PACKAGE_ICONS = {
    single: Coins,
    pack_5: TrendingUp,
    pack_10: Zap,
    pack_25: Crown
};

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
        
        // Create purchase record
        const result = await createPurchase(packageType);
        
        if (result.success) {
            // Redirect to Yoco payment link
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
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content credit-purchase-modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>Buy Script Credits</h2>
                    <button className="modal-close" onClick={onClose}>
                        <X size={24} />
                    </button>
                </div>

                <div className="modal-body">
                    <p className="credit-purchase-intro">
                        Choose a credit package to upload scripts. Each script requires 1 credit.
                        <strong> Bulk packages save you money!</strong>
                    </p>

                    {loading ? (
                        <div className="credit-purchase-loading">
                            <div className="spinner"></div>
                            <p>Loading packages...</p>
                        </div>
                    ) : (
                        <div className="credit-packages">
                            {packages && Object.entries(packages).map(([key, pkg]) => {
                                const Icon = PACKAGE_ICONS[key];
                                const isPopular = key === 'pack_10';
                                const isBestValue = key === 'pack_25';
                                
                                return (
                                    <div 
                                        key={key}
                                        className={`credit-package ${isPopular ? 'popular' : ''} ${isBestValue ? 'best-value' : ''}`}
                                        onClick={() => handlePurchase(key)}
                                    >
                                        {isPopular && <div className="package-badge popular-badge">Popular</div>}
                                        {isBestValue && <div className="package-badge best-value-badge">Best Value</div>}
                                        
                                        <div className="package-icon">
                                            <Icon size={32} />
                                        </div>
                                        
                                        <h3 className="package-name">{pkg.name}</h3>
                                        <p className="package-description">{pkg.description}</p>
                                        
                                        <div className="package-pricing">
                                            <div className="package-price">
                                                R{pkg.price.toFixed(2)}
                                            </div>
                                            <div className="package-per-script">
                                                R{pkg.per_script.toFixed(2)} per script
                                            </div>
                                        </div>
                                        
                                        {pkg.savings && (
                                            <div className="package-savings">
                                                <Check size={16} />
                                                Save {pkg.savings}
                                            </div>
                                        )}
                                        
                                        <button 
                                            className="package-button"
                                            disabled={selectedPackage === key}
                                        >
                                            {selectedPackage === key ? 'Redirecting...' : 'Buy Now'}
                                        </button>
                                    </div>
                                );
                            })}
                        </div>
                    )}

                    <div className="credit-purchase-footer">
                        <p>
                            <strong>Secure payment via Yoco.</strong> Credits never expire.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CreditPurchaseModal;
