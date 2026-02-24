import React, { useState, useRef, useCallback } from 'react';
import { Users, ChevronRight, CheckCircle, Clock, Loader, FileText, ArrowDownUp, CalendarDays, GripVertical, EyeOff, Eye } from 'lucide-react';
import { getSceneEighthsDisplay } from '../../utils/sceneUtils';
import './SceneList.css';

/**
 * SceneList - Displays scenes with analysis status badges
 * 
 * Status indicators:
 * - ✅ Complete (green) - Scene has been analyzed
 * - ⏳ Pending (gray) - Scene awaiting analysis
 * - 🔄 Analyzing (blue spinner) - Currently being analyzed
 * 
 * Page info from pageMapping shows which PDF pages each scene spans
 */
const SceneList = ({ scenes, selectedId, onSelect, analyzingScenes = new Set(), recentlyCompletedScenes = new Set(), pageMapping = null, userItemsByScene = {}, onReorder = null, onOmit = null }) => {
    const [dragIndex, setDragIndex] = useState(null);
    const [overIndex, setOverIndex] = useState(null);
    const dragNodeRef = useRef(null);
    const listRef = useRef(null);
    const startYRef = useRef(0);

    const handleDragStart = useCallback((e, index) => {
        e.stopPropagation();
        setDragIndex(index);
        startYRef.current = e.clientY;
        dragNodeRef.current = e.currentTarget.closest('.scene-item');

        const handlePointerMove = (moveEvt) => {
            moveEvt.preventDefault();
            if (!listRef.current) return;
            const items = listRef.current.querySelectorAll('.scene-item');
            let closestIdx = index;
            let closestDist = Infinity;
            items.forEach((item, i) => {
                const rect = item.getBoundingClientRect();
                const midY = rect.top + rect.height / 2;
                const dist = Math.abs(moveEvt.clientY - midY);
                if (dist < closestDist) {
                    closestDist = dist;
                    closestIdx = i;
                }
            });
            setOverIndex(closestIdx);
        };

        const handlePointerUp = () => {
            document.removeEventListener('pointermove', handlePointerMove);
            document.removeEventListener('pointerup', handlePointerUp);
            setDragIndex((prevDragIdx) => {
                setOverIndex((prevOverIdx) => {
                    if (prevDragIdx !== null && prevOverIdx !== null && prevDragIdx !== prevOverIdx && onReorder) {
                        onReorder(prevDragIdx, prevOverIdx);
                    }
                    return null;
                });
                return null;
            });
        };

        document.addEventListener('pointermove', handlePointerMove);
        document.addEventListener('pointerup', handlePointerUp);
    }, [onReorder]);
    if (!scenes || scenes.length === 0) {
        return (
            <div className="list-empty">
                <FileText size={32} className="empty-icon-small" />
                <p>No scenes found</p>
            </div>
        );
    }

    // Determine analysis status for a scene
    const getAnalysisStatus = (scene) => {
        if (analyzingScenes.has(scene.scene_id) || scene.analysis_status === 'analyzing') {
            return 'analyzing';
        }
        // Use analysis_status field from database
        return scene.analysis_status === 'complete' ? 'complete' : 'pending';
    };

    // Extract the last transition from a scene's transitions array
    const getLastTransition = (scene) => {
        if (!scene.transitions || scene.transitions.length === 0) return null;
        const last = scene.transitions[scene.transitions.length - 1];
        // Handle both string and object formats
        if (typeof last === 'string') return last;
        if (last.type) return last.type;
        if (last.transition) return last.transition;
        return null;
    };

    return (
        <div className="scene-list" ref={listRef}>
            {scenes.map((scene, index) => {
                const sceneId = scene.id || scene.scene_id;
                const sceneUserItems = userItemsByScene[sceneId] || {};
                const charCount = (scene.characters?.length || 0) + (sceneUserItems.characters?.length || 0);
                const propCount = (scene.props?.length || 0) + (sceneUserItems.props?.length || 0);
                const status = getAnalysisStatus(scene);
                
                // Build meta text
                const metaParts = [];
                if (charCount > 0) metaParts.push(`${charCount} char${charCount > 1 ? 's' : ''}`);
                if (propCount > 0) metaParts.push(`${propCount} prop${propCount > 1 ? 's' : ''}`);
                const metaText = metaParts.join(', ');

                // Use original scene number if available, otherwise fall back to sequential
                const displaySceneNum = scene.scene_number_original || scene.scene_number;

                // Check if this scene just completed (for fade-out animation)
                const isRecentlyCompleted = recentlyCompletedScenes.has(scene.scene_id) || 
                                            recentlyCompletedScenes.has(scene.id);

                // Get transition from previous scene to this one
                const prevScene = index > 0 ? scenes[index - 1] : null;
                const transitionLabel = prevScene ? getLastTransition(prevScene) : null;

                // Story day separator: show when story_day changes from previous scene
                const prevStoryDay = prevScene ? prevScene.story_day : null;
                const showDaySeparator = scene.story_day && prevStoryDay && scene.story_day !== prevStoryDay;

                return (
                    <React.Fragment key={scene.scene_id}>
                        {/* Story Day separator */}
                        {showDaySeparator && (
                            <div className="story-day-divider">
                                <span className="story-day-divider-line" />
                                <span className={`story-day-divider-label timeline-${(scene.timeline_code || 'PRESENT').toLowerCase()}`}>
                                    <CalendarDays size={10} />
                                    {scene.story_day_label || `Day ${scene.story_day}`}
                                </span>
                                <span className="story-day-divider-line" />
                            </div>
                        )}

                        {/* Transition divider between scenes */}
                        {transitionLabel && (
                            <div className="transition-divider">
                                <span className="transition-line" />
                                <span className="transition-label">
                                    <ArrowDownUp size={10} />
                                    {transitionLabel}
                                </span>
                                <span className="transition-line" />
                            </div>
                        )}

                        {/* Drop indicator above */}
                        {dragIndex !== null && overIndex === index && dragIndex > index && (
                            <div className="scene-drop-indicator" />
                        )}

                        <div 
                            className={`scene-item scene-item-card ${selectedId === scene.scene_id ? 'selected' : ''} status-${status} ${dragIndex === index ? 'dragging' : ''} ${scene.is_omitted ? 'omitted' : ''}`}
                            onClick={() => onSelect(scene)}
                        >
                            {/* Drag Handle */}
                            {onReorder && (
                                <button
                                    className="scene-drag-handle"
                                    onPointerDown={(e) => handleDragStart(e, index)}
                                    onClick={(e) => e.stopPropagation()}
                                    title="Drag to reorder"
                                >
                                    <GripVertical size={14} />
                                </button>
                            )}
                            {/* Scene Number - Top Left */}
                            <span className="scene-number">
                                {scene.is_omitted && <span className="omitted-badge">OMIT</span>}
                                {displaySceneNum}
                            </span>
                            
                            {/* Status Indicator - fades out for completed scenes */}
                            <div className={`status-indicator status-${status} ${isRecentlyCompleted ? 'fade-out' : ''} ${status === 'complete' && !isRecentlyCompleted ? 'hidden' : ''}`}>
                                {status === 'complete' && <CheckCircle size={14} />}
                                {status === 'pending' && <Clock size={14} />}
                                {status === 'analyzing' && <Loader size={14} className="spin" />}
                            </div>
                            
                            <div className="scene-item-content">
                                <div className="entity-header">
                                    <div className="entity-name" title={scene.setting}>
                                        {scene.int_ext && <span className="int-ext-badge">{scene.int_ext}</span>}
                                        {scene.setting}
                                    </div>
                                    <div className="entity-header-right">
                                        {scene.story_day && (
                                            <span className={`story-day-pill timeline-${(scene.timeline_code || 'PRESENT').toLowerCase()}`}>
                                                D{scene.story_day}
                                            </span>
                                        )}
                                        <span className="entity-count">{scene.time_of_day || 'DAY'}</span>
                                    </div>
                                </div>
                                
                                <div className="entity-meta-row">
                                    {status === 'complete' && metaText && (
                                        <div className="entity-meta">
                                            <Users size={12} className="meta-icon" />
                                            <span className="meta-value">{metaText}</span>
                                        </div>
                                    )}
                                    {status === 'pending' && (
                                        <div className="entity-meta pending-label">
                                            <span className="meta-value">Click to analyze</span>
                                        </div>
                                    )}
                                    {status === 'analyzing' && (
                                        <div className="entity-meta analyzing-label">
                                            <span className="meta-value">Analyzing...</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                            
                            {/* Omit/Restore Toggle */}
                            {onOmit && (
                                <button
                                    className={`scene-omit-btn ${scene.is_omitted ? 'is-omitted' : ''}`}
                                    onClick={(e) => { e.stopPropagation(); onOmit(scene); }}
                                    title={scene.is_omitted ? 'Restore scene' : 'Omit scene'}
                                >
                                    {scene.is_omitted ? <Eye size={14} /> : <EyeOff size={14} />}
                                </button>
                            )}
                            <ChevronRight size={16} className="arrow-icon" />
                        </div>

                        {/* Drop indicator below */}
                        {dragIndex !== null && overIndex === index && dragIndex < index && (
                            <div className="scene-drop-indicator" />
                        )}
                    </React.Fragment>
                );
            })}
        </div>
    );
};

export default SceneList;
