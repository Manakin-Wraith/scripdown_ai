/**
 * useSubscription Hook
 * Manages subscription status, feature access, and upgrade prompts.
 */

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

// Phase 1: Everyone gets active status (no subscription enforcement)
// Set to false to enable subscription checks in Phase 4
const PHASE1_FREE_ACCESS = true;

// Trial configuration (must match backend)
const TRIAL_DURATION_DAYS = 14;
const TRIAL_SCRIPT_LIMIT = 1;

// Feature definitions
const TRIAL_FEATURES = [
    'view_scripts',
    'view_scenes',
    'basic_analysis',
];

const ACTIVE_FEATURES = [
    'view_scripts',
    'view_scenes',
    'basic_analysis',
    'upload_scripts',
    'unlimited_scripts',
    'full_analysis',
    'team_collaboration',
    'invite_members',
    'reports',
    'export_pdf',
    'stripboard_edit',
    'department_notes',
];

const YOCO_PAYMENT_LINK = 'https://pay.yoco.com/r/2JB0rQ';

export function useSubscription() {
    const { user, profile } = useAuth();
    const [subscriptionStatus, setSubscriptionStatus] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Phase 1: Return active status immediately without API call
    const getPhase1Status = useCallback(() => ({
        status: 'active',
        is_active: true,
        days_remaining: null,
        expires_at: null,
        trial_ends_at: null,
        can_upload_script: true,
        script_count: 0,
        script_limit: null,
        features: ACTIVE_FEATURES,
        message: null
    }), []);

    // Fetch subscription status from backend
    const fetchSubscriptionStatus = useCallback(async () => {
        // Phase 1: Skip API call, everyone gets active status
        if (PHASE1_FREE_ACCESS) {
            setSubscriptionStatus(getPhase1Status());
            setLoading(false);
            return;
        }

        if (!user?.id) {
            setSubscriptionStatus(null);
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            const response = await fetch(`${API_BASE_URL}/api/auth/subscription-status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: user.id })
            });

            if (!response.ok) {
                throw new Error('Failed to fetch subscription status');
            }

            const data = await response.json();
            setSubscriptionStatus(data);
            setError(null);
        } catch (err) {
            console.error('Error fetching subscription status:', err);
            setError(err.message);
            // Fallback to local calculation
            setSubscriptionStatus(calculateLocalStatus());
        } finally {
            setLoading(false);
        }
    }, [user?.id, getPhase1Status]);

    // Calculate status locally as fallback
    const calculateLocalStatus = useCallback(() => {
        if (!profile) return null;

        const status = profile.subscription_status || 'trial';
        const createdAt = profile.created_at ? new Date(profile.created_at) : new Date();
        const now = new Date();
        
        if (status === 'trial') {
            const trialEndsAt = new Date(createdAt);
            trialEndsAt.setDate(trialEndsAt.getDate() + TRIAL_DURATION_DAYS);
            const daysRemaining = Math.max(0, Math.ceil((trialEndsAt - now) / (1000 * 60 * 60 * 24)));
            const isExpired = now > trialEndsAt;

            return {
                status: isExpired ? 'expired' : 'trial',
                is_active: !isExpired,
                days_remaining: daysRemaining,
                trial_ends_at: trialEndsAt.toISOString(),
                script_limit: TRIAL_SCRIPT_LIMIT,
                features: isExpired ? [] : TRIAL_FEATURES,
                message: daysRemaining <= 7 ? `${daysRemaining} days left in your trial` : null
            };
        }

        if (status === 'active') {
            const expiresAt = profile.subscription_expires_at ? new Date(profile.subscription_expires_at) : null;
            const daysRemaining = expiresAt ? Math.max(0, Math.ceil((expiresAt - now) / (1000 * 60 * 60 * 24))) : null;
            const isExpired = expiresAt && now > expiresAt;

            return {
                status: isExpired ? 'expired' : 'active',
                is_active: !isExpired,
                days_remaining: daysRemaining,
                expires_at: expiresAt?.toISOString(),
                script_limit: null,
                features: isExpired ? [] : ACTIVE_FEATURES,
                message: daysRemaining && daysRemaining <= 14 ? `${daysRemaining} days until renewal` : null
            };
        }

        return {
            status: status,
            is_active: false,
            days_remaining: 0,
            features: [],
            message: 'Your subscription is inactive.'
        };
    }, [profile]);

    // Refresh status on mount and when user changes
    useEffect(() => {
        fetchSubscriptionStatus();
    }, [fetchSubscriptionStatus]);

    // Check if user can access a specific feature
    const canAccess = useCallback((feature) => {
        if (!subscriptionStatus) return false;
        return subscriptionStatus.features?.includes(feature) || false;
    }, [subscriptionStatus]);

    // Check if user can upload a script
    const canUploadScript = useCallback(async () => {
        if (!user?.id) return { canUpload: false, message: 'Please sign in' };

        try {
            const response = await fetch(`${API_BASE_URL}/api/auth/can-upload-script`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: user.id })
            });

            const data = await response.json();
            return {
                canUpload: data.can_upload,
                message: data.message,
                upgradeUrl: data.upgrade_url
            };
        } catch (err) {
            console.error('Error checking upload permission:', err);
            // Fallback: allow if active, block if trial with scripts
            if (subscriptionStatus?.status === 'active') {
                return { canUpload: true };
            }
            return { 
                canUpload: false, 
                message: 'Unable to verify upload permission',
                upgradeUrl: YOCO_PAYMENT_LINK
            };
        }
    }, [user?.id, subscriptionStatus]);

    // Get upgrade URL
    const getUpgradeUrl = useCallback(() => YOCO_PAYMENT_LINK, []);

    // Check if should show upgrade prompt
    const shouldShowUpgradePrompt = useCallback(() => {
        if (!subscriptionStatus) return false;
        
        // Show if trial with <= 7 days remaining
        if (subscriptionStatus.status === 'trial' && subscriptionStatus.days_remaining <= 7) {
            return true;
        }
        
        // Show if expired
        if (subscriptionStatus.status === 'expired') {
            return true;
        }
        
        // Show if active with <= 14 days remaining
        if (subscriptionStatus.status === 'active' && subscriptionStatus.days_remaining <= 14) {
            return true;
        }
        
        return false;
    }, [subscriptionStatus]);

    // Get status badge info
    const getStatusBadge = useCallback(() => {
        if (!subscriptionStatus) return null;

        switch (subscriptionStatus.status) {
            case 'trial':
                return {
                    label: `Trial - ${subscriptionStatus.days_remaining} days left`,
                    color: subscriptionStatus.days_remaining <= 3 ? 'red' : 'amber',
                    icon: '⏰'
                };
            case 'active':
                return {
                    label: 'Beta Access',
                    color: 'green',
                    icon: '✓'
                };
            case 'expired':
                return {
                    label: 'Expired',
                    color: 'red',
                    icon: '⚠️'
                };
            case 'cancelled':
                return {
                    label: 'Cancelled',
                    color: 'gray',
                    icon: '✕'
                };
            default:
                return null;
        }
    }, [subscriptionStatus]);

    return {
        // Status
        status: subscriptionStatus?.status || 'trial',
        isActive: subscriptionStatus?.is_active || false,
        isLoading: loading,
        error,
        
        // Details
        daysRemaining: subscriptionStatus?.days_remaining,
        scriptLimit: subscriptionStatus?.script_limit,
        scriptCount: subscriptionStatus?.script_count,
        message: subscriptionStatus?.message,
        features: subscriptionStatus?.features || [],
        
        // Methods
        canAccess,
        canUploadScript,
        getUpgradeUrl,
        shouldShowUpgradePrompt,
        getStatusBadge,
        refresh: fetchSubscriptionStatus,
        
        // Constants
        YOCO_PAYMENT_LINK,
        TRIAL_DURATION_DAYS,
        TRIAL_SCRIPT_LIMIT,
    };
}

export default useSubscription;
