/**
 * CreditBalance Component
 * Displays user's current credit balance in header/sidebar
 */

import React from 'react';
import { Coins, TrendingUp } from 'lucide-react';
import { useCredits } from '../../hooks/useCredits';
import './CreditBalance.css';

const CreditBalance = ({ onClick, compact = false }) => {
    const { credits, isLegacyBeta, loading } = useCredits();

    if (loading) {
        return (
            <div className={`credit-balance ${compact ? 'compact' : ''}`}>
                <div className="credit-balance-loading">
                    <div className="spinner-small"></div>
                </div>
            </div>
        );
    }

    const isLow = credits <= 2 && credits > 0;
    const isEmpty = credits === 0;

    return (
        <div 
            className={`credit-balance ${compact ? 'compact' : ''} ${isLow ? 'low' : ''} ${isEmpty ? 'empty' : ''}`}
            onClick={onClick}
            role={onClick ? 'button' : undefined}
            tabIndex={onClick ? 0 : undefined}
        >
            <div className="credit-balance-icon">
                <Coins size={compact ? 18 : 20} />
            </div>
            <div className="credit-balance-content">
                <div className="credit-balance-amount">
                    {credits}
                    <span className="credit-label">breakdown{credits !== 1 ? 's' : ''} remaining</span>
                </div>
                {!compact && isEmpty && (
                    <div className="credit-balance-cta">
                        Click to buy breakdowns
                    </div>
                )}
            </div>
        </div>
    );
};

export default CreditBalance;
