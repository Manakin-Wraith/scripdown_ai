import { useState, useEffect, useCallback } from 'react';
import { getEntitlement } from '../services/apiService';

export const useEntitlement = () => {
    const [entitlement, setEntitlement] = useState(null);
    const [loading, setLoading] = useState(true);

    const refetch = useCallback(async () => {
        setLoading(true);
        try {
            setEntitlement(await getEntitlement());
        } catch {
            // Fail closed in the UI: no entitlement means show the paywall,
            // never accidentally reveal paid features on a network blip.
            setEntitlement({
                tier: 'none', status: 'none', breakdown_balance: 0,
                seats_paid: 0, seats_used: 0,
                can_run_breakdown: false, can_use_teams: false,
            });
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { refetch(); }, [refetch]);

    return { entitlement, loading, refetch };
};
