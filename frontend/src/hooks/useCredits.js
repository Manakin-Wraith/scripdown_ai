/**
 * useCredits Hook
 * Manages script credit state and operations
 */

import { useState, useEffect, useCallback } from 'react';
import { supabase } from '../lib/supabase';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export const useCredits = () => {
    const [credits, setCredits] = useState(0);
    const [totalPurchased, setTotalPurchased] = useState(0);
    const [scriptsUploaded, setScriptsUploaded] = useState(0);
    const [isLegacyBeta, setIsLegacyBeta] = useState(false);
    const [usageHistory, setUsageHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchBalance = useCallback(async () => {
        console.log('useCredits: fetchBalance called');
        try {
            setLoading(true);
            setError(null);

            const { data: { session } } = await supabase.auth.getSession();
            console.log('useCredits: session check', { hasSession: !!session });
            if (!session) {
                console.log('useCredits: No session, skipping fetch');
                setLoading(false);
                return;
            }

            console.log('useCredits: Calling API', `${API_BASE_URL}/api/credits/balance`);
            const response = await axios.get(`${API_BASE_URL}/api/credits/balance`, {
                headers: {
                    'Authorization': `Bearer ${session.access_token}`
                }
            });

            console.log('useCredits: API response', response.data);
            if (response.data.success) {
                const balance = response.data.balance;
                setCredits(balance.credits);
                setTotalPurchased(balance.total_purchased);
                setScriptsUploaded(balance.scripts_uploaded);
                setIsLegacyBeta(balance.is_legacy_beta);
                setUsageHistory(balance.usage_history);
            }
        } catch (err) {
            console.error('Error fetching credit balance:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, []);

    const canUpload = useCallback(async () => {
        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) {
                return { canUpload: false, message: 'Please log in' };
            }

            const response = await axios.get(`${API_BASE_URL}/api/credits/can-upload`, {
                headers: {
                    'Authorization': `Bearer ${session.access_token}`
                }
            });

            if (response.data.success) {
                return {
                    canUpload: response.data.can_upload,
                    message: response.data.message
                };
            }

            return { canUpload: false, message: 'Unable to check upload permission' };
        } catch (err) {
            console.error('Error checking upload permission:', err);
            return { canUpload: false, message: err.message };
        }
    }, []);

    const deductCredit = useCallback(async (scriptId, scriptName) => {
        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) {
                throw new Error('Not authenticated');
            }

            const response = await axios.post(
                `${API_BASE_URL}/api/credits/deduct`,
                { script_id: scriptId, script_name: scriptName },
                {
                    headers: {
                        'Authorization': `Bearer ${session.access_token}`,
                        'Content-Type': 'application/json'
                    }
                }
            );

            if (response.data.success) {
                setCredits(response.data.remaining_credits);
                await fetchBalance(); // Refresh full balance
                return { success: true, remaining: response.data.remaining_credits };
            }

            return { success: false, error: 'Failed to deduct credit' };
        } catch (err) {
            console.error('Error deducting credit:', err);
            return { success: false, error: err.message };
        }
    }, [fetchBalance]);

    const getPackages = useCallback(async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/api/credits/packages`);
            if (response.data.success) {
                return response.data.packages;
            }
            return null;
        } catch (err) {
            console.error('Error fetching packages:', err);
            return null;
        }
    }, []);

    const createPurchase = useCallback(async (packageType) => {
        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) {
                throw new Error('Not authenticated');
            }

            const response = await axios.post(
                `${API_BASE_URL}/api/credits/purchase/create`,
                { package_type: packageType },
                {
                    headers: {
                        'Authorization': `Bearer ${session.access_token}`,
                        'Content-Type': 'application/json'
                    }
                }
            );

            if (response.data.success) {
                return { success: true, purchaseId: response.data.purchase_id };
            }

            return { success: false, error: 'Failed to create purchase' };
        } catch (err) {
            console.error('Error creating purchase:', err);
            return { success: false, error: err.message };
        }
    }, []);

    // Fetch balance on mount
    useEffect(() => {
        console.log('useCredits: Hook mounted, calling fetchBalance');
        fetchBalance();
    }, [fetchBalance]);

    return {
        credits,
        totalPurchased,
        scriptsUploaded,
        isLegacyBeta,
        usageHistory,
        loading,
        error,
        fetchBalance,
        canUpload,
        deductCredit,
        getPackages,
        createPurchase
    };
};
