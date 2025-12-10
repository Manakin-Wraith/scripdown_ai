import React from 'react';
import { Users, ChevronRight, CheckCircle, Clock, Loader, FileText } from 'lucide-react';
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
const SceneList = ({ scenes, selectedId, onSelect, analyzingScenes = new Set(), recentlyCompletedScenes = new Set(), pageMapping = null }) => {
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

    return (
        <div className="scene-list">
            {scenes.map((scene) => {
                const charCount = scene.characters?.length || 0;
                const propCount = scene.props?.length || 0;
                const status = getAnalysisStatus(scene);
                
                // Build meta text
                const metaParts = [];
                if (charCount > 0) metaParts.push(`${charCount} char${charCount > 1 ? 's' : ''}`);
                if (propCount > 0) metaParts.push(`${propCount} prop${propCount > 1 ? 's' : ''}`);
                const metaText = metaParts.join(', ');

                // Use original scene number if available, otherwise fall back to sequential
                const displaySceneNum = scene.scene_number_original || scene.scene_number;
                
                // Build page info from pageMapping or scene data
                const getPageInfo = () => {
                    // First try pageMapping (most accurate)
                    if (pageMapping?.scene_pages) {
                        const scenePageData = pageMapping.scene_pages[scene.id] || pageMapping.scene_pages[scene.scene_id];
                        if (scenePageData) {
                            const { page_start, page_end } = scenePageData;
                            if (page_start && page_end && page_end !== page_start) {
                                return `pp. ${page_start}-${page_end}`;
                            } else if (page_start) {
                                return `p. ${page_start}`;
                            }
                        }
                    }
                    // Fallback to scene data
                    if (scene.page_start) {
                        return scene.page_end && scene.page_end !== scene.page_start 
                            ? `pp. ${scene.page_start}-${scene.page_end}` 
                            : `p. ${scene.page_start}`;
                    }
                    return null;
                };
                const pageInfo = getPageInfo();

                // Check if this scene just completed (for fade-out animation)
                const isRecentlyCompleted = recentlyCompletedScenes.has(scene.scene_id) || 
                                            recentlyCompletedScenes.has(scene.id);

                return (
                    <div 
                        key={scene.scene_id} 
                        className={`scene-item scene-item-card ${selectedId === scene.scene_id ? 'selected' : ''} status-${status}`}
                        onClick={() => onSelect(scene)}
                    >
                        {/* Scene Number - Top Left */}
                        <span className="scene-number">{displaySceneNum}</span>
                        
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
                                <span className="entity-count">{scene.time_of_day || 'DAY'}</span>
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
                                {pageInfo && (
                                    <div className="entity-meta page-info" title={`PDF ${pageInfo}`}>
                                        <span className="meta-value">{pageInfo}</span>
                                    </div>
                                )}
                            </div>
                        </div>
                        
                        <ChevronRight size={16} className="arrow-icon" />
                    </div>
                );
            })}
        </div>
    );
};

export default SceneList;
