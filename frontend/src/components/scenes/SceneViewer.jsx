import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getScenes, getScriptMetadata, getScriptItems } from '../../services/apiService';
import SceneList from './SceneList';
import SceneDetail from './SceneDetail';
import ScriptHeader from '../metadata/ScriptHeader';
import ScriptSummary from './ScriptSummary';
import PdfViewerPanel from '../pdf/PdfViewerPanel';
import { AlertCircle, ChevronDown, ChevronUp, Zap, FileText, List, Loader, XCircle, BookOpen, CalendarDays } from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { useScript } from '../../context/ScriptContext';
import { useStoryDayListener } from '../../context/StoryDayContext';
import { analyzeBulkScenes, analyzeScene, getPageMapping, reorderScenes, omitScene } from '../../services/apiService';
import { useSubscription } from '../../hooks/useSubscription';
import { UpgradeModal } from '../subscription';
import './SceneViewer.css';

const SceneViewer = () => {
    const { scriptId } = useParams();
    const toast = useToast();
    const { setScript } = useScript();
    
    const [scenes, setScenes] = useState([]);
    const [metadata, setMetadata] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedScene, setSelectedScene] = useState(null);
    const [userItemsByScene, setUserItemsByScene] = useState({});
    const [showSummary, setShowSummary] = useState(false);
    const [analyzingScenes, setAnalyzingScenes] = useState(new Set());
    const [isBulkAnalyzing, setIsBulkAnalyzing] = useState(false);
    const [bulkAnalysisStartTime, setBulkAnalysisStartTime] = useState(null);
    const [pollIntervalId, setPollIntervalId] = useState(null);
    const [showPdfPanel, setShowPdfPanel] = useState(false);
    const [pageMapping, setPageMapping] = useState(null);
    const [currentPdfPage, setCurrentPdfPage] = useState(1);
    const [recentlyCompletedScenes, setRecentlyCompletedScenes] = useState(new Set());
    const [storyDayFilter, setStoryDayFilter] = useState(null);
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    const { status, daysRemaining } = useSubscription();
    const isPaidSubscriber = status === 'active';
    const selectedSceneRef = useRef(null);
    selectedSceneRef.current = selectedScene;

    // Fetch scenes data
    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                
                // Fetch scenes + user-added items in parallel
                const [sceneData, itemsData] = await Promise.all([
                    getScenes(scriptId),
                    getScriptItems(scriptId).catch(() => ({ items: [] }))
                ]);
                const fetchedScenes = sceneData.scenes || [];
                setScenes(fetchedScenes);
                
                // Index user items by scene_id → item_type
                const itemMap = {};
                (itemsData.items || []).forEach(item => {
                    if (!item.scene_id || item.status === 'removed') return;
                    if (!itemMap[item.scene_id]) itemMap[item.scene_id] = {};
                    if (!itemMap[item.scene_id][item.item_type]) itemMap[item.scene_id][item.item_type] = [];
                    itemMap[item.scene_id][item.item_type].push(item.item_name);
                });
                setUserItemsByScene(itemMap);
                
                // Auto-select first scene if available
                if (fetchedScenes.length > 0) {
                    setSelectedScene(fetchedScenes[0]);
                }
                
                // Fetch metadata
                try {
                    const metadataData = await getScriptMetadata(scriptId);
                    setMetadata(metadataData);
                    // Update script context for breadcrumbs
                    setScript({
                        id: scriptId,
                        title: metadataData?.title || metadataData?.script_name
                    });
                } catch (metaErr) {
                    console.warn('Failed to load metadata:', metaErr);
                }
                
                // Fetch page mapping for PDF sync
                try {
                    const mapping = await getPageMapping(scriptId);
                    setPageMapping(mapping);
                } catch (mapErr) {
                    console.warn('Failed to load page mapping:', mapErr);
                }
                
                setError(null);
            } catch (err) {
                setError(err.message || 'Failed to load scenes');
                console.error('Error fetching data:', err);
            } finally {
                setLoading(false);
            }
        };

        if (scriptId) {
            fetchData();
        }
    }, [scriptId]);

    // Reusable scene refresh (called after story day edits and other changes)
    const refreshScenes = useCallback(async () => {
        try {
            const [sceneData, itemsData] = await Promise.all([
                getScenes(scriptId),
                getScriptItems(scriptId).catch(() => ({ items: [] }))
            ]);
            const fetched = sceneData.scenes || [];
            setScenes(fetched);
            const itemMap = {};
            (itemsData.items || []).forEach(item => {
                if (!item.scene_id || item.status === 'removed') return;
                if (!itemMap[item.scene_id]) itemMap[item.scene_id] = {};
                if (!itemMap[item.scene_id][item.item_type]) itemMap[item.scene_id][item.item_type] = [];
                itemMap[item.scene_id][item.item_type].push(item.item_name);
            });
            setUserItemsByScene(itemMap);
            const current = selectedSceneRef.current;
            if (current) {
                const refreshed = fetched.find(s => s.id === current.id || s.scene_id === current.scene_id);
                if (refreshed) setSelectedScene(refreshed);
            }
        } catch (err) {
            console.error('Error refreshing scenes:', err);
        }
    }, [scriptId]);

    // Listen for story day changes from other views
    useStoryDayListener((changedScriptId) => {
        if (changedScriptId === scriptId) refreshScenes();
    });

    // Compute unique story days for filter dropdown
    const uniqueStoryDays = useMemo(() => {
        const days = new Map();
        scenes.forEach(scene => {
            if (scene.story_day) {
                if (!days.has(scene.story_day)) {
                    days.set(scene.story_day, {
                        day: scene.story_day,
                        label: scene.story_day_label || `Day ${scene.story_day}`,
                        timeline: scene.timeline_code || 'PRESENT',
                        count: 0
                    });
                }
                days.get(scene.story_day).count++;
            }
        });
        return Array.from(days.values()).sort((a, b) => a.day - b.day);
    }, [scenes]);

    // Filtered scenes based on story day filter
    const filteredScenes = useMemo(() => {
        if (!storyDayFilter) return scenes;
        return scenes.filter(s => s.story_day === storyDayFilter);
    }, [scenes, storyDayFilter]);

    // Clear selected scene if it's no longer in the filtered list
    useEffect(() => {
        if (storyDayFilter && selectedScene) {
            const stillVisible = filteredScenes.some(
                s => s.scene_id === selectedScene.scene_id
            );
            if (!stillVisible) {
                setSelectedScene(filteredScenes[0] || null);
            }
        }
    }, [storyDayFilter, filteredScenes]);

    // Aggregate data for summary panel (excludes omitted scenes)
    const summaryData = useMemo(() => {
        const chars = {};
        const locs = {};
        let analyzedCount = 0;
        const activeScenes = scenes.filter(s => !s.is_omitted);

        activeScenes.forEach(scene => {
            // Check if scene is analyzed using analysis_status
            const isAnalyzed = scene.analysis_status === 'complete';
            if (isAnalyzed) analyzedCount++;

            // Aggregate Characters (AI + user-added)
            const sceneId = scene.id || scene.scene_id;
            const sceneItems = userItemsByScene[sceneId] || {};
            const allChars = [...(scene.characters || []), ...(sceneItems.characters || [])];
            allChars.forEach(char => {
                if (!chars[char]) chars[char] = { count: 0, scenes: [] };
                chars[char].count++;
                chars[char].scenes.push(scene.scene_number);
            });

            // Aggregate Locations
            if (scene.setting) {
                if (!locs[scene.setting]) locs[scene.setting] = { count: 0, scenes: [] };
                locs[scene.setting].count++;
                locs[scene.setting].scenes.push(scene.scene_number);
            }
        });

        return {
            characters: chars,
            locations: locs,
            totalScenes: activeScenes.length,
            analyzedScenes: analyzedCount,
            pendingScenes: activeScenes.length - analyzedCount,
            omittedScenes: scenes.length - activeScenes.length
        };
    }, [scenes, userItemsByScene]);

    // Handle single scene analysis
    const handleAnalyzeScene = async (sceneId) => {
        // Subscription gate: block analysis for non-subscribers
        if (!isPaidSubscriber) {
            setShowUpgradeModal(true);
            return;
        }
        setAnalyzingScenes(prev => new Set([...prev, sceneId]));
        
        try {
            const result = await analyzeScene(sceneId);
            
            // Update scenes array with new analysis data
            setScenes(prevScenes => prevScenes.map(scene => {
                if (scene.id === sceneId || scene.scene_id === sceneId) {
                    const updatedScene = {
                        ...scene,
                        ...result.analysis,
                        analysis_status: 'complete'
                    };
                    // Also update selectedScene if this is the one being viewed
                    if (selectedScene && (selectedScene.id === sceneId || selectedScene.scene_id === sceneId)) {
                        setSelectedScene(updatedScene);
                    }
                    return updatedScene;
                }
                return scene;
            }));
            
            toast.success('Analysis Complete', 'Scene breakdown is ready!');
            
            // Track as recently completed for fade-out animation
            const sceneIdToTrack = sceneId;
            setRecentlyCompletedScenes(prev => new Set([...prev, sceneIdToTrack]));
            
            // Remove from recently completed after 1.5s (fade-out duration)
            setTimeout(() => {
                setRecentlyCompletedScenes(prev => {
                    const next = new Set(prev);
                    next.delete(sceneIdToTrack);
                    return next;
                });
            }, 1500);
            
        } catch (err) {
            toast.error('Analysis Failed', err.message || 'Could not analyze scene.');
        } finally {
            setAnalyzingScenes(prev => {
                const next = new Set(prev);
                next.delete(sceneId);
                return next;
            });
        }
    };

    // Handle bulk analysis - starts background job and polls for updates
    const handleBulkAnalyze = async () => {
        // Subscription gate: block analysis for non-subscribers
        if (!isPaidSubscriber) {
            setShowUpgradeModal(true);
            return;
        }
        setIsBulkAnalyzing(true);
        setBulkAnalysisStartTime(Date.now());
        
        try {
            const result = await analyzeBulkScenes(scriptId);
            toast.info(
                'Bulk Analysis Started', 
                `Processing ${result.total} scenes in the background.`
            );
            
            // Start polling for scene updates
            startPollingForUpdates();
            
        } catch (err) {
            toast.error('Bulk Analysis Failed', err.message || 'Could not start bulk analysis.');
            setIsBulkAnalyzing(false);
            setBulkAnalysisStartTime(null);
        }
    };
    
    // Cancel bulk analysis polling
    const handleCancelBulkAnalysis = () => {
        if (pollIntervalId) {
            clearInterval(pollIntervalId);
            setPollIntervalId(null);
        }
        setIsBulkAnalyzing(false);
        setBulkAnalysisStartTime(null);
        toast.info('Analysis Stopped', 'Bulk analysis polling stopped. Scenes already analyzed will remain.');
    };
    
    // Poll for scene updates during bulk analysis
    const startPollingForUpdates = () => {
        // Clear any existing interval
        if (pollIntervalId) {
            clearInterval(pollIntervalId);
        }
        
        const intervalId = setInterval(async () => {
            try {
                const sceneData = await getScenes(scriptId);
                const fetchedScenes = sceneData.scenes || [];
                setScenes(fetchedScenes);
                
                // Update selected scene if it was analyzed
                if (selectedScene) {
                    const updatedSelected = fetchedScenes.find(
                        s => s.id === selectedScene.id || s.scene_id === selectedScene.scene_id
                    );
                    if (updatedSelected) {
                        setSelectedScene(updatedSelected);
                    }
                }
                
                // Track newly completed scenes for fade-out animation
                const newlyCompleted = fetchedScenes.filter(s => {
                    const oldScene = scenes.find(os => os.id === s.id || os.scene_id === s.scene_id);
                    return s.analysis_status === 'complete' && 
                           oldScene && 
                           oldScene.analysis_status !== 'complete';
                });
                
                if (newlyCompleted.length > 0) {
                    const newIds = newlyCompleted.map(s => s.scene_id || s.id);
                    setRecentlyCompletedScenes(prev => new Set([...prev, ...newIds]));
                    
                    // Remove after fade-out duration
                    setTimeout(() => {
                        setRecentlyCompletedScenes(prev => {
                            const next = new Set(prev);
                            newIds.forEach(id => next.delete(id));
                            return next;
                        });
                    }, 1500);
                }
                
                // Check if all scenes are analyzed
                const pendingCount = fetchedScenes.filter(
                    s => s.analysis_status === 'pending' || s.analysis_status === 'analyzing'
                ).length;
                const errorCount = fetchedScenes.filter(
                    s => s.analysis_status === 'error'
                ).length;
                
                if (pendingCount === 0) {
                    clearInterval(intervalId);
                    setPollIntervalId(null);
                    setIsBulkAnalyzing(false);
                    setBulkAnalysisStartTime(null);
                    if (errorCount > 0) {
                        toast.error('Bulk Analysis Finished', `${errorCount} scene${errorCount > 1 ? 's' : ''} failed. Try re-analyzing individually.`);
                    } else {
                        toast.success('Bulk Analysis Complete', 'All scenes have been analyzed!');
                    }
                    // Final re-fetch after 2s to pick up story day recalculation
                    setTimeout(async () => {
                        try {
                            const freshData = await getScenes(scriptId);
                            const freshScenes = freshData.scenes || [];
                            setScenes(freshScenes);
                            if (selectedScene) {
                                const updated = freshScenes.find(
                                    s => s.id === selectedScene.id || s.scene_id === selectedScene.scene_id
                                );
                                if (updated) setSelectedScene(updated);
                            }
                        } catch (e) {
                            console.warn('Post-analysis refresh failed:', e);
                        }
                    }, 2000);
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        }, 3000); // Poll every 3 seconds
        
        setPollIntervalId(intervalId);
    };
    
    // Cleanup polling on unmount
    useEffect(() => {
        return () => {
            if (pollIntervalId) {
                clearInterval(pollIntervalId);
            }
        };
    }, [pollIntervalId]);
    
    // Calculate current analyzing scene (first pending/analyzing scene)
    const currentAnalyzingScene = useMemo(() => {
        if (!isBulkAnalyzing) return null;
        return scenes.find(s => s.analysis_status === 'analyzing' || s.analysis_status === 'pending');
    }, [scenes, isBulkAnalyzing]);
    
    // Calculate estimated time remaining
    const estimatedTimeRemaining = useMemo(() => {
        if (!isBulkAnalyzing || !bulkAnalysisStartTime) return null;
        
        const elapsed = (Date.now() - bulkAnalysisStartTime) / 1000; // seconds
        const completed = summaryData.analyzedScenes;
        const total = summaryData.totalScenes;
        const pending = summaryData.pendingScenes;
        
        if (completed === 0 || elapsed < 5) return 'Calculating...';
        
        // Average time per scene based on elapsed time
        const avgTimePerScene = elapsed / Math.max(1, completed - (total - pending - completed));
        const remainingSeconds = pending * avgTimePerScene;
        
        if (remainingSeconds < 60) return `~${Math.ceil(remainingSeconds)}s remaining`;
        if (remainingSeconds < 3600) return `~${Math.ceil(remainingSeconds / 60)} min remaining`;
        return `~${Math.ceil(remainingSeconds / 3600)} hr remaining`;
    }, [isBulkAnalyzing, bulkAnalysisStartTime, summaryData]);

    // Handle omit/restore scene from sidebar
    const handleOmitScene = useCallback(async (scene) => {
        const sceneId = scene.id || scene.scene_id;
        const newOmitState = !scene.is_omitted;

        // Optimistic update
        setScenes(prev => prev.map(s =>
            (s.id || s.scene_id) === sceneId ? { ...s, is_omitted: newOmitState } : s
        ));

        try {
            await omitScene(scriptId, sceneId, newOmitState);
            toast.success(
                newOmitState ? 'Scene Omitted' : 'Scene Restored',
                `Scene ${scene.scene_number || ''} ${newOmitState ? 'omitted' : 'restored'}`
            );
        } catch (err) {
            toast.error('Error', 'Failed to update scene');
            // Rollback
            setScenes(prev => prev.map(s =>
                (s.id || s.scene_id) === sceneId ? { ...s, is_omitted: !newOmitState } : s
            ));
        }
    }, [scriptId, toast]);

    // Handle drag reorder of scenes in sidebar
    const handleReorderScenes = useCallback(async (fromIndex, toIndex) => {
        const reordered = [...filteredScenes];
        const [moved] = reordered.splice(fromIndex, 1);
        reordered.splice(toIndex, 0, moved);

        // Optimistic update
        if (storyDayFilter) {
            const filteredIds = new Set(filteredScenes.map(s => s.scene_id));
            setScenes(prev => {
                const copy = prev.filter(s => !filteredIds.has(s.scene_id));
                // Insert reordered scenes back at the position of the first filtered scene
                const firstFilteredIdx = prev.findIndex(s => filteredIds.has(s.scene_id));
                copy.splice(firstFilteredIdx >= 0 ? firstFilteredIdx : copy.length, 0, ...reordered);
                return copy;
            });
        } else {
            setScenes(reordered);
        }

        // Build ordered scene_ids from the full (potentially reordered) scenes array
        const allSceneIds = storyDayFilter
            ? (() => {
                const filteredIds = new Set(filteredScenes.map(s => s.scene_id));
                const result = [];
                let reorderedIdx = 0;
                for (const s of scenes) {
                    if (filteredIds.has(s.scene_id)) {
                        result.push(reordered[reorderedIdx]?.scene_id || reordered[reorderedIdx]?.id);
                        reorderedIdx++;
                    } else {
                        result.push(s.scene_id || s.id);
                    }
                }
                return result;
            })()
            : reordered.map(s => s.scene_id || s.id);

        try {
            await reorderScenes(scriptId, allSceneIds);
            toast.success('Reordered', 'Scene order updated.');
        } catch (err) {
            toast.error('Reorder Failed', err.message || 'Could not reorder scenes.');
            // Rollback: re-fetch from server
            try {
                const sceneData = await getScenes(scriptId);
                setScenes(sceneData.scenes || []);
            } catch (fetchErr) {
                console.error('Failed to rollback scene order:', fetchErr);
            }
        }
    }, [filteredScenes, scenes, storyDayFilter, scriptId, toast]);

    // Handle PDF page change - sync scene selection (only called on user scroll)
    const handlePdfPageChange = (page) => {
        setCurrentPdfPage(page);
        
        // Only sync if we have page mapping
        if (!pageMapping) return;
        
        // Find scene(s) on this page
        const scenesOnPage = pageMapping.page_to_scenes?.[page];
        if (scenesOnPage && scenesOnPage.length > 0) {
            // Select the first scene on this page
            const sceneId = scenesOnPage[0].scene_id;
            const sceneToSelect = scenes.find(s => s.id === sceneId || s.scene_id === sceneId);
            
            if (sceneToSelect && sceneToSelect.id !== selectedScene?.id) {
                console.log(`[SceneViewer] Syncing to scene ${sceneToSelect.scene_number} from PDF page ${page}`);
                setSelectedScene(sceneToSelect);
            }
        }
    };

    // Get the page number for the selected scene
    const getScenePageNumber = (scene) => {
        if (!scene || !pageMapping) return 1;
        const sceneData = pageMapping.scene_pages?.[scene.id] || pageMapping.scene_pages?.[scene.scene_id];
        return sceneData?.page_start || 1;
    };

    if (loading) {
        return (
            <div className="scene-viewer-loading">
                <div className="spinner"></div>
                <p>Loading script...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="scene-viewer-error">
                <AlertCircle size={48} className="error-icon" />
                <h3>Error Loading Scenes</h3>
                <p>{error}</p>
                <Link to="/upload" className="btn-primary">
                    Upload New Script
                </Link>
            </div>
        );
    }

    return (
        <div className="scene-viewer-container">
            {/* Script Header */}
            <ScriptHeader metadata={metadata} sceneCount={scenes.length} />
            
            {/* Collapsible Script Summary */}
            <div className="summary-panel">
                <button 
                    className="summary-toggle"
                    onClick={() => setShowSummary(!showSummary)}
                >
                    <span className="summary-toggle-text">
                        <FileText size={16} />
                        Script Summary
                        <span className="summary-stats">
                            {Object.keys(summaryData.characters).length} Characters • {Object.keys(summaryData.locations).length} Locations
                        </span>
                    </span>
                    {showSummary ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </button>
                
                {showSummary && (
                    <ScriptSummary 
                        characters={summaryData.characters}
                        locations={summaryData.locations}
                        stats={{
                            total: summaryData.totalScenes,
                            analyzed: summaryData.analyzedScenes,
                            pending: summaryData.pendingScenes
                        }}
                        scriptId={scriptId}
                        onMergeComplete={async () => {
                            try {
                                const sceneData = await getScenes(scriptId);
                                const fetchedScenes = sceneData.scenes || [];
                                setScenes(fetchedScenes);
                                if (selectedScene) {
                                    const updated = fetchedScenes.find(
                                        s => s.id === selectedScene.id || s.scene_id === selectedScene.scene_id
                                    );
                                    if (updated) setSelectedScene(updated);
                                }
                            } catch (err) {
                                console.error('Failed to refresh scenes after merge:', err);
                            }
                        }}
                    />
                )}
            </div>
            
            {/* Enhanced Analysis Progress Bar */}
            {(summaryData.pendingScenes > 0 || isBulkAnalyzing) && (
                <div className={`analysis-progress-bar ${isBulkAnalyzing ? 'analyzing' : ''}`}>
                    <div className="progress-header">
                        <div className="progress-status">
                            {isBulkAnalyzing ? (
                                <>
                                    <Loader size={16} className="spin" />
                                    <span>Analyzing scenes...</span>
                                </>
                            ) : (
                                <span>{summaryData.analyzedScenes} of {summaryData.totalScenes} scenes analyzed</span>
                            )}
                        </div>
                        <div className="progress-actions">
                            {isBulkAnalyzing ? (
                                <>
                                    <span className="progress-eta">{estimatedTimeRemaining}</span>
                                    <button 
                                        className="cancel-btn"
                                        onClick={handleCancelBulkAnalysis}
                                        title="Stop watching progress"
                                    >
                                        <XCircle size={14} />
                                        Stop
                                    </button>
                                </>
                            ) : (
                                <button 
                                    className="bulk-analyze-btn"
                                    onClick={handleBulkAnalyze}
                                    disabled={isBulkAnalyzing}
                                    title="Analyze all pending scenes"
                                >
                                    <Zap size={14} />
                                    Analyze All
                                </button>
                            )}
                        </div>
                    </div>
                    
                    <div className="progress-track">
                        <div 
                            className={`progress-fill ${isBulkAnalyzing ? 'pulse' : ''}`}
                            style={{ width: `${(summaryData.analyzedScenes / summaryData.totalScenes) * 100}%` }}
                        />
                    </div>
                    
                    {/* Current scene being analyzed */}
                    {isBulkAnalyzing && currentAnalyzingScene && (
                        <div className="progress-current">
                            <span className="current-label">Currently:</span>
                            <span className="current-scene">
                                Scene {currentAnalyzingScene.scene_number} - {currentAnalyzingScene.setting}
                            </span>
                        </div>
                    )}
                    
                    {/* Progress count */}
                    <div className="progress-count">
                        <span className="count-analyzed">{summaryData.analyzedScenes}</span>
                        <span className="count-separator">/</span>
                        <span className="count-total">{summaryData.totalScenes}</span>
                        <span className="count-label">scenes</span>
                        <span className="count-percentage">
                            ({Math.round((summaryData.analyzedScenes / summaryData.totalScenes) * 100)}%)
                        </span>
                    </div>
                </div>
            )}
            
            <div className={`scene-viewer-layout ${showPdfPanel ? 'with-pdf-panel' : ''}`}>
                {/* Sidebar - Scene List Only */}
                <div className="viewer-sidebar">
                    <div className="sidebar-header">
                        <span>Scenes</span>
                        <div className="sidebar-header-actions">
                            {uniqueStoryDays.length > 0 && (
                                <select
                                    className={`story-day-filter-select ${storyDayFilter ? 'filter-active' : ''}`}
                                    value={storyDayFilter || ''}
                                    onChange={(e) => setStoryDayFilter(e.target.value ? parseInt(e.target.value, 10) : null)}
                                    title="Filter by story day"
                                >
                                    <option value="">All Days</option>
                                    {uniqueStoryDays.map(d => (
                                        <option key={d.day} value={d.day}>
                                            {d.label} ({d.count})
                                        </option>
                                    ))}
                                </select>
                            )}
                            <button 
                                className={`pdf-toggle-btn ${showPdfPanel ? 'active' : ''}`}
                                onClick={() => setShowPdfPanel(!showPdfPanel)}
                                title={showPdfPanel ? 'Hide PDF' : 'View Original PDF'}
                            >
                                <BookOpen size={16} />
                            </button>
                        </div>
                    </div>
                    <SceneList 
                        scenes={filteredScenes} 
                        selectedId={selectedScene?.scene_id} 
                        onSelect={setSelectedScene}
                        analyzingScenes={analyzingScenes}
                        recentlyCompletedScenes={recentlyCompletedScenes}
                        pageMapping={pageMapping}
                        userItemsByScene={userItemsByScene}
                        onReorder={handleReorderScenes}
                        onOmit={handleOmitScene}
                    />
                </div>

                {/* Main Detail Area */}
                <div className="viewer-main">
                    <SceneDetail 
                        scene={selectedScene}
                        scriptId={scriptId}
                        onAnalyze={handleAnalyzeScene}
                        isAnalyzing={selectedScene && analyzingScenes.has(selectedScene.scene_id)}
                        pageMapping={pageMapping}
                        onRefreshScene={refreshScenes}
                    />
                </div>

                {/* PDF Viewer Panel (Right Side) */}
                <PdfViewerPanel
                    scriptId={scriptId}
                    isOpen={showPdfPanel}
                    onClose={() => setShowPdfPanel(false)}
                    currentPage={getScenePageNumber(selectedScene)}
                    onPageChange={handlePdfPageChange}
                />
            </div>
            {/* Subscription upgrade modal */}
            <UpgradeModal
                isOpen={showUpgradeModal}
                onClose={() => setShowUpgradeModal(false)}
                feature="ai_analysis"
                daysRemaining={daysRemaining}
                isExpired={status === 'expired'}
            />
        </div>
    );
};

export default SceneViewer;
