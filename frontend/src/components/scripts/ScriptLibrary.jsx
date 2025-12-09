import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getScripts, deleteScript, reanalyzeScript } from '../../services/apiService';
import { useAnalysis } from '../../context/AnalysisContext';
import ScriptTable from './ScriptTable';
import EmptyLibrary from './EmptyLibrary';
import { Plus } from 'lucide-react';
import { useConfirmDialog } from '../../context/ConfirmDialogContext';
import { useToast } from '../../context/ToastContext';
import './ScriptLibrary.css';

const ScriptLibrary = () => {
    const [scripts, setScripts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [reanalyzing, setReanalyzing] = useState(null);
    const navigate = useNavigate();
    const { hasActiveAnalysis, globalStatus } = useAnalysis();
    const { confirm } = useConfirmDialog();
    const toast = useToast();

    const fetchScripts = useCallback(async (showLoading = true) => {
        try {
            if (showLoading) setLoading(true);
            const data = await getScripts();
            setScripts(data.scripts || []);
            setError('');
        } catch (err) {
            console.error('Fetch error:', err);
            setError('Failed to load scripts: ' + err.message);
        } finally {
            if (showLoading) setLoading(false);
        }
    }, []);

    // Initial fetch
    useEffect(() => {
        fetchScripts();
    }, [fetchScripts]);

    // Auto-refresh when there are active analyses (silent refresh - no loading spinner)
    useEffect(() => {
        if (!hasActiveAnalysis) return;
        
        // Poll every 3 seconds while analysis is active
        const interval = setInterval(() => {
            fetchScripts(false); // Silent refresh
        }, 3000);
        
        return () => clearInterval(interval);
    }, [hasActiveAnalysis, fetchScripts]);

    // Refresh when any analysis completes (silent refresh)
    useEffect(() => {
        // Check if any script just completed
        const completedScripts = Object.entries(globalStatus).filter(
            ([, status]) => status.status === 'complete'
        );
        
        if (completedScripts.length > 0) {
            fetchScripts(false); // Silent refresh
        }
    }, [globalStatus, fetchScripts]);

    const handleViewScenes = (scriptId) => {
        navigate(`/scenes/${scriptId}`);
    };

    const handleReanalyze = async (scriptId) => {
        const confirmed = await confirm({
            title: 'Re-analyze Script',
            message: 'This will delete existing scenes and run a fresh analysis. Continue?',
            variant: 'warning',
            confirmText: 'Re-analyze'
        });
        
        if (!confirmed) return;

        try {
            setReanalyzing(scriptId);
            await reanalyzeScript(scriptId);

            // Navigate to streaming analysis (could be better handled in-place, but sticking to proven flow)
            const eventSource = new EventSource(`http://localhost:5000/analyze_script_stream/${scriptId}`);

            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.done) {
                    eventSource.close();
                    setReanalyzing(null);
                    fetchScripts(); 
                    navigate(`/scenes/${scriptId}`);
                }

                if (data.error) {
                    eventSource.close();
                    setReanalyzing(null);
                    toast.error('Analysis Failed', data.error);
                }
            };

            eventSource.onerror = () => {
                eventSource.close();
                setReanalyzing(null);
                toast.error('Connection Failed', 'Could not connect to analysis server.');
            };

        } catch (err) {
            setReanalyzing(null);
            toast.error('Re-analyze Failed', err.message);
        }
    };

    const handleDelete = async (scriptId, scriptName) => {
        const confirmed = await confirm({
            title: 'Delete Script',
            message: `Delete "${scriptName}"? This cannot be undone.`,
            variant: 'danger',
            confirmText: 'Delete'
        });
        
        if (!confirmed) return;

        try {
            await deleteScript(scriptId);
            toast.success('Script Deleted', `"${scriptName}" has been removed.`);
            fetchScripts(); // Refresh the list
        } catch (err) {
            toast.error('Delete Failed', err.message);
        }
    };

    if (loading) {
        return (
            <div className="library-container loading-state">
                <div className="spinner"></div>
                <p>Loading library...</p>
            </div>
        );
    }

    return (
        <div className="library-container">
            <div className="library-header">
                <div>
                    <h1>My Scripts</h1>
                    <p className="library-subtitle">Manage your screenplays and breakdowns</p>
                </div>
                {scripts.length > 0 && (
                    <button
                        className="upload-new-btn"
                        onClick={() => navigate('/upload')}
                    >
                        <Plus size={18} />
                        Upload New
                    </button>
                )}
            </div>

            {error && <div className="error-banner">{error}</div>}

            {scripts.length === 0 ? (
                <EmptyLibrary />
            ) : (
                <ScriptTable 
                    scripts={scripts} 
                    onView={handleViewScenes} 
                    onReanalyze={handleReanalyze}
                    onDelete={handleDelete}
                    reanalyzingId={reanalyzing}
                />
            )}
        </div>
    );
};

export default ScriptLibrary;
