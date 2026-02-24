import React, { useState, useEffect, useMemo } from 'react';
import { 
    Video, 
    Camera, 
    Clapperboard, 
    MapPin, 
    ChevronRight, 
    Loader,
    Filter,
    BarChart3
} from 'lucide-react';
import { getScenes } from '../../services/apiService';
import './CameraDeptView.css';

/**
 * CameraDeptView - Camera Department workspace view
 * 
 * Shows shot types aggregated across all scenes, grouped by type.
 * Useful for DOP/Camera Dept prep — see all CLOSE ON, WIDE, POV scenes at a glance.
 */
const CameraDeptView = ({ scriptId }) => {
    const [scenes, setScenes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedShotType, setSelectedShotType] = useState(null);
    const [filterType, setFilterType] = useState('all');

    useEffect(() => {
        const fetchScenes = async () => {
            if (!scriptId) return;
            setLoading(true);
            try {
                const data = await getScenes(scriptId);
                setScenes(data.scenes || []);
            } catch (err) {
                console.error('Error fetching scenes for camera view:', err);
            } finally {
                setLoading(false);
            }
        };
        fetchScenes();
    }, [scriptId]);

    // Aggregate scenes by shot type (exclude omitted)
    const activeScenes = useMemo(() => scenes.filter(s => !s.is_omitted), [scenes]);

    const shotTypeGroups = useMemo(() => {
        const groups = {};
        activeScenes.forEach(scene => {
            const shotType = scene.shot_type || 'STANDARD';
            if (!groups[shotType]) {
                groups[shotType] = {
                    type: shotType,
                    scenes: [],
                    intExtBreakdown: { INT: 0, EXT: 0 }
                };
            }
            groups[shotType].scenes.push(scene);
            const ie = (scene.int_ext || 'INT').toUpperCase();
            if (ie.includes('EXT')) {
                groups[shotType].intExtBreakdown.EXT++;
            } else {
                groups[shotType].intExtBreakdown.INT++;
            }
        });

        // Sort by scene count descending
        return Object.values(groups).sort((a, b) => b.scenes.length - a.scenes.length);
    }, [activeScenes]);

    // Scenes with shot types vs without
    const scenesWithShotType = useMemo(() => 
        activeScenes.filter(s => s.shot_type && s.shot_type !== 'STANDARD').length,
    [activeScenes]);

    // Filter groups
    const filteredGroups = useMemo(() => {
        if (filterType === 'all') return shotTypeGroups;
        if (filterType === 'with_shot') return shotTypeGroups.filter(g => g.type !== 'STANDARD');
        return shotTypeGroups;
    }, [shotTypeGroups, filterType]);

    // Selected group scenes
    const selectedScenes = useMemo(() => {
        if (!selectedShotType) return [];
        const group = shotTypeGroups.find(g => g.type === selectedShotType);
        return group ? group.scenes : [];
    }, [selectedShotType, shotTypeGroups]);

    if (loading) {
        return (
            <div className="camera-loading">
                <Loader size={24} className="spin" />
                <span>Loading shot data...</span>
            </div>
        );
    }

    return (
        <div className="camera-dept-view">
            {/* Summary Stats */}
            <div className="camera-stats">
                <div className="camera-stat-card">
                    <Clapperboard size={20} />
                    <div className="stat-info">
                        <span className="stat-value">{activeScenes.length}</span>
                        <span className="stat-label">Total Scenes</span>
                    </div>
                </div>
                <div className="camera-stat-card">
                    <Video size={20} />
                    <div className="stat-info">
                        <span className="stat-value">{shotTypeGroups.length}</span>
                        <span className="stat-label">Shot Types</span>
                    </div>
                </div>
                <div className="camera-stat-card">
                    <Camera size={20} />
                    <div className="stat-info">
                        <span className="stat-value">{scenesWithShotType}</span>
                        <span className="stat-label">Scenes with Shot Type</span>
                    </div>
                </div>
            </div>

            {/* Filter */}
            <div className="camera-toolbar">
                <h3>
                    <BarChart3 size={18} />
                    Shot List by Type
                </h3>
                <div className="camera-filter">
                    <Filter size={14} />
                    <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
                        <option value="all">All Scenes</option>
                        <option value="with_shot">With Shot Type Only</option>
                    </select>
                </div>
            </div>

            <div className="camera-layout">
                {/* Shot Type Groups */}
                <div className="shot-type-list">
                    {filteredGroups.length === 0 ? (
                        <div className="camera-empty">
                            <Camera size={40} />
                            <p>No shot type data available.</p>
                            <span>Upload and analyze scenes to see shot types.</span>
                        </div>
                    ) : (
                        filteredGroups.map(group => (
                            <div 
                                key={group.type}
                                className={`shot-type-card ${selectedShotType === group.type ? 'selected' : ''}`}
                                onClick={() => setSelectedShotType(selectedShotType === group.type ? null : group.type)}
                            >
                                <div className="shot-type-header">
                                    <span className="shot-type-name">
                                        <Video size={16} />
                                        {group.type}
                                    </span>
                                    <span className="shot-type-count">{group.scenes.length}</span>
                                </div>
                                <div className="shot-type-meta">
                                    <span className="int-count">INT: {group.intExtBreakdown.INT}</span>
                                    <span className="ext-count">EXT: {group.intExtBreakdown.EXT}</span>
                                </div>
                                {/* Mini bar chart */}
                                <div className="shot-type-bar">
                                    <div 
                                        className="bar-fill"
                                        style={{ width: `${(group.scenes.length / activeScenes.length) * 100}%` }}
                                    />
                                </div>
                            </div>
                        ))
                    )}
                </div>

                {/* Selected Shot Type Detail */}
                {selectedShotType && selectedScenes.length > 0 && (
                    <div className="shot-detail-panel">
                        <h4>
                            <Video size={16} />
                            {selectedShotType}
                            <span className="detail-count">{selectedScenes.length} scenes</span>
                        </h4>
                        <div className="shot-scene-list">
                            {selectedScenes.map(scene => (
                                <div key={scene.id || scene.scene_id} className="shot-scene-item">
                                    <span className="shot-scene-number">
                                        {scene.scene_number_original || scene.scene_number}
                                    </span>
                                    <div className="shot-scene-info">
                                        <span className="shot-scene-setting">
                                            {scene.int_ext && <span className="shot-int-ext">{scene.int_ext}</span>}
                                            {scene.setting}
                                        </span>
                                        <span className="shot-scene-tod">{scene.time_of_day || 'DAY'}</span>
                                    </div>
                                    {scene.location_hierarchy && scene.location_hierarchy.length > 1 && (
                                        <div className="shot-scene-location">
                                            <MapPin size={10} />
                                            {scene.location_hierarchy.join(' > ')}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default CameraDeptView;
