/**
 * Analysis Context - Global state management for AI analysis status
 * 
 * Provides:
 * - Real-time analysis status for all scripts
 * - Functions to start/retry analysis
 * - Polling for progress updates
 */

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import {
    getGlobalAnalysisStatus,
    getScriptAnalysisStatus,
    startScriptAnalysis,
    retryScriptAnalysis
} from '../services/apiService';
import { useToast } from './ToastContext';

const AnalysisContext = createContext(null);

// Polling interval in milliseconds
const POLL_INTERVAL = 3000;

export const AnalysisProvider = ({ children }) => {
    const toast = useToast();
    
    // Global status for all scripts
    const [globalStatus, setGlobalStatus] = useState({});
    
    // Detailed status for specific scripts (when viewing)
    const [detailedStatus, setDetailedStatus] = useState({});
    
    // Loading states
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    
    // Track if any analysis is in progress
    const [hasActiveAnalysis, setHasActiveAnalysis] = useState(false);
    
    // Track previous status to detect completions
    const prevStatusRef = useRef({});
    
    // Polling ref
    const pollingRef = useRef(null);

    /**
     * Fetch global analysis status for all scripts
     */
    const fetchGlobalStatus = useCallback(async () => {
        try {
            const response = await getGlobalAnalysisStatus();
            if (response.success) {
                const newStatus = response.data;
                
                // Check for newly completed analyses
                Object.entries(newStatus).forEach(([scriptId, status]) => {
                    const prevStatus = prevStatusRef.current[scriptId];
                    
                    // If was in_progress and now complete
                    if (prevStatus?.status === 'in_progress' && status.status === 'complete') {
                        toast?.success(
                            'Analysis Complete!',
                            `${status.name || 'Script'} is ready to view.`,
                            {
                                action: {
                                    label: 'View',
                                    onClick: () => {
                                        window.location.href = `/scenes/${scriptId}`;
                                    }
                                }
                            }
                        );
                    }
                    
                    // If was in_progress and now failed
                    if (prevStatus?.status === 'in_progress' && status.status === 'failed') {
                        toast?.error(
                            'Analysis Failed',
                            `${status.name || 'Script'} analysis encountered an error.`,
                            {
                                action: {
                                    label: 'Retry',
                                    onClick: () => {
                                        retryScriptAnalysis(scriptId);
                                    }
                                }
                            }
                        );
                    }
                });
                
                // Update refs
                prevStatusRef.current = newStatus;
                setGlobalStatus(newStatus);
                
                // Check if any analysis is active
                const hasActive = Object.values(newStatus).some(
                    s => s.status === 'in_progress' || s.status === 'queued'
                );
                setHasActiveAnalysis(hasActive);
            }
        } catch (err) {
            console.error('Failed to fetch global analysis status:', err);
        }
    }, [toast]);

    /**
     * Fetch detailed status for a specific script
     */
    const fetchScriptStatus = useCallback(async (scriptId) => {
        try {
            const response = await getScriptAnalysisStatus(scriptId);
            if (response.success) {
                setDetailedStatus(prev => ({
                    ...prev,
                    [scriptId]: response.data
                }));
                return response.data;
            }
        } catch (err) {
            console.error(`Failed to fetch status for script ${scriptId}:`, err);
        }
        return null;
    }, []);

    /**
     * Start analysis for a script
     */
    const startAnalysis = useCallback(async (scriptId, priority = 5) => {
        setIsLoading(true);
        setError(null);
        
        try {
            const response = await startScriptAnalysis(scriptId, priority);
            if (response.success) {
                // Immediately update local state
                setGlobalStatus(prev => ({
                    ...prev,
                    [scriptId]: {
                        ...prev[scriptId],
                        status: 'queued',
                        progress: 0
                    }
                }));
                setHasActiveAnalysis(true);
                
                // Start polling if not already
                startPolling();
                
                return response.data;
            } else {
                setError(response.error);
            }
        } catch (err) {
            setError(err.message);
            console.error('Failed to start analysis:', err);
        } finally {
            setIsLoading(false);
        }
        return null;
    }, []);

    /**
     * Retry failed analysis for a script
     */
    const retryAnalysis = useCallback(async (scriptId) => {
        setIsLoading(true);
        setError(null);
        
        try {
            const response = await retryScriptAnalysis(scriptId);
            if (response.success) {
                // Refresh status
                await fetchScriptStatus(scriptId);
                setHasActiveAnalysis(true);
                startPolling();
                return true;
            } else {
                setError(response.error);
            }
        } catch (err) {
            setError(err.message);
            console.error('Failed to retry analysis:', err);
        } finally {
            setIsLoading(false);
        }
        return false;
    }, [fetchScriptStatus]);

    /**
     * Get status for a specific script
     */
    const getStatus = useCallback((scriptId) => {
        // Return detailed status if available, otherwise global
        return detailedStatus[scriptId] || globalStatus[scriptId] || {
            status: 'pending',
            progress: 0
        };
    }, [globalStatus, detailedStatus]);

    /**
     * Check if a script has completed analysis
     */
    const isAnalysisComplete = useCallback((scriptId) => {
        const status = getStatus(scriptId);
        return status.status === 'complete';
    }, [getStatus]);

    /**
     * Check if a script is currently being analyzed
     */
    const isAnalyzing = useCallback((scriptId) => {
        const status = getStatus(scriptId);
        return status.status === 'in_progress' || status.status === 'queued';
    }, [getStatus]);

    /**
     * Start polling for updates
     */
    const startPolling = useCallback(() => {
        if (pollingRef.current) return; // Already polling
        
        pollingRef.current = setInterval(async () => {
            await fetchGlobalStatus();
            
            // Also refresh detailed status for scripts we're tracking
            for (const scriptId of Object.keys(detailedStatus)) {
                await fetchScriptStatus(scriptId);
            }
        }, POLL_INTERVAL);
    }, [fetchGlobalStatus, fetchScriptStatus, detailedStatus]);

    /**
     * Stop polling
     */
    const stopPolling = useCallback(() => {
        if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
        }
    }, []);

    // Initial fetch on mount
    useEffect(() => {
        fetchGlobalStatus();
    }, [fetchGlobalStatus]);

    // Start/stop polling based on active analysis
    useEffect(() => {
        if (hasActiveAnalysis) {
            startPolling();
        } else {
            stopPolling();
        }
        
        return () => stopPolling();
    }, [hasActiveAnalysis, startPolling, stopPolling]);

    const value = {
        // State
        globalStatus,
        detailedStatus,
        isLoading,
        error,
        hasActiveAnalysis,
        
        // Actions
        fetchGlobalStatus,
        fetchScriptStatus,
        startAnalysis,
        retryAnalysis,
        
        // Helpers
        getStatus,
        isAnalysisComplete,
        isAnalyzing
    };

    return (
        <AnalysisContext.Provider value={value}>
            {children}
        </AnalysisContext.Provider>
    );
};

/**
 * Hook to use analysis context
 * Returns a safe default if context is not available (prevents crashes during HMR)
 */
export const useAnalysis = () => {
    const context = useContext(AnalysisContext);
    if (!context) {
        // Return safe defaults instead of throwing during development/HMR
        console.warn('useAnalysis called outside AnalysisProvider - returning defaults');
        return {
            globalStatus: {},
            hasActiveAnalysis: false,
            scriptStatuses: {},
            startAnalysis: () => Promise.resolve(),
            retryAnalysis: () => Promise.resolve(),
            cancelAnalysis: () => Promise.resolve(),
            refreshStatus: () => Promise.resolve(),
            getScriptStatus: () => null
        };
    }
    return context;
};

export default AnalysisContext;
