import React, { useMemo, useState, useEffect } from 'react';
import { MapPin, Home, TreePine, Sun, Moon, Sunrise, Clapperboard, ChevronRight, Users, Sparkles, RefreshCw } from 'lucide-react';
import { analyzeLocations } from '../../services/apiService';
import './Dashboard.css';

const LocationDashboard = ({ locations, scenes, onSelectLocation, scriptId }) => {
    // AI Analysis state
    const [aiAnalysis, setAiAnalysis] = useState(null);
    const [analysisLoading, setAnalysisLoading] = useState(false);
    const [analysisError, setAnalysisError] = useState(null);

    // Fetch AI analysis on mount
    useEffect(() => {
        const fetchAnalysis = async () => {
            if (!scriptId) return;
            
            setAnalysisLoading(true);
            setAnalysisError(null);
            
            try {
                const result = await analyzeLocations(scriptId);
                setAiAnalysis(result);
            } catch (err) {
                console.error('Failed to fetch location analysis:', err);
                setAnalysisError('AI analysis unavailable');
            } finally {
                setAnalysisLoading(false);
            }
        };

        fetchAnalysis();
    }, [scriptId]);

    // Get AI description for a location
    const getAiDescription = (locName) => {
        if (!aiAnalysis?.locations) return null;
        return aiAnalysis.locations[locName] || null;
    };
    // Parse location data and categorize
    const locationData = useMemo(() => {
        const parsed = Object.entries(locations).map(([setting, locScenes]) => {
            // Parse INT/EXT from setting name
            const settingUpper = setting.toUpperCase();
            let type = 'other';
            if (settingUpper.startsWith('INT.') || settingUpper.startsWith('INT ')) {
                type = 'interior';
            } else if (settingUpper.startsWith('EXT.') || settingUpper.startsWith('EXT ')) {
                type = 'exterior';
            }

            // Parse time of day
            let timeOfDay = 'day';
            if (settingUpper.includes('NIGHT')) {
                timeOfDay = 'night';
            } else if (settingUpper.includes('DAWN') || settingUpper.includes('SUNRISE')) {
                timeOfDay = 'dawn';
            } else if (settingUpper.includes('DUSK') || settingUpper.includes('SUNSET')) {
                timeOfDay = 'dusk';
            } else if (settingUpper.includes('DAY')) {
                timeOfDay = 'day';
            }

            // Get characters at this location
            const charactersAtLocation = new Set();
            locScenes.forEach(scene => {
                if (scene.characters) {
                    scene.characters.forEach(c => charactersAtLocation.add(c));
                }
            });

            // Clean location name for display
            let displayName = setting;
            // Remove INT./EXT. prefix for cleaner display
            displayName = displayName.replace(/^(INT\.|EXT\.|INT |EXT )\s*/i, '');

            return {
                setting,
                displayName,
                type,
                timeOfDay,
                sceneCount: locScenes.length,
                sceneNumbers: locScenes.map(s => s.scene_number).sort((a, b) => a - b),
                characters: Array.from(charactersAtLocation),
                scenes: locScenes
            };
        });

        return parsed.sort((a, b) => b.sceneCount - a.sceneCount);
    }, [locations]);

    // Calculate statistics
    const stats = useMemo(() => {
        const interior = locationData.filter(l => l.type === 'interior').length;
        const exterior = locationData.filter(l => l.type === 'exterior').length;
        
        const dayScenes = locationData.filter(l => l.timeOfDay === 'day').length;
        const nightScenes = locationData.filter(l => l.timeOfDay === 'night').length;
        const otherTime = locationData.length - dayScenes - nightScenes;

        return {
            total: locationData.length,
            interior,
            exterior,
            day: dayScenes,
            night: nightScenes,
            other: otherTime
        };
    }, [locationData]);

    // Group by type for display
    const interiorLocations = locationData.filter(l => l.type === 'interior');
    const exteriorLocations = locationData.filter(l => l.type === 'exterior');

    if (Object.keys(locations).length === 0) {
        return (
            <div className="dashboard-empty">
                <MapPin size={48} className="empty-icon" />
                <h3>No Locations Found</h3>
                <p>Locations will appear here once the script is analyzed</p>
            </div>
        );
    }

    const getTimeIcon = (time) => {
        switch (time) {
            case 'night': return <Moon size={14} />;
            case 'dawn':
            case 'dusk': return <Sunrise size={14} />;
            default: return <Sun size={14} />;
        }
    };

    return (
        <div className="dashboard">
            {/* Header */}
            <div className="dashboard-header">
                <div className="dashboard-title">
                    <MapPin size={24} className="title-icon" />
                    <h2>Location Overview</h2>
                </div>
                <span className="dashboard-count">{stats.total} Locations</span>
            </div>

            {/* Stats Grid */}
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-icon-wrapper blue">
                        <MapPin size={20} />
                    </div>
                    <div className="stat-content">
                        <span className="stat-value">{stats.total}</span>
                        <span className="stat-label">Total Locations</span>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon-wrapper indigo">
                        <Home size={20} />
                    </div>
                    <div className="stat-content">
                        <span className="stat-value">{stats.interior}</span>
                        <span className="stat-label">Interior</span>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon-wrapper emerald">
                        <TreePine size={20} />
                    </div>
                    <div className="stat-content">
                        <span className="stat-value">{stats.exterior}</span>
                        <span className="stat-label">Exterior</span>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon-wrapper amber">
                        <Sun size={20} />
                    </div>
                    <div className="stat-content">
                        <span className="stat-value">{stats.day}</span>
                        <span className="stat-label">Day Scenes</span>
                    </div>
                </div>
            </div>

            {/* AI Analysis Status */}
            {analysisLoading && (
                <div className="ai-status loading">
                    <RefreshCw size={16} className="spin" />
                    <span>Analyzing locations with AI...</span>
                </div>
            )}

            {/* AI Insights */}
            {aiAnalysis?.insights && (
                <div className="ai-insights">
                    <div className="insights-header">
                        <Sparkles size={18} className="sparkle-icon" />
                        <h3>AI Insights</h3>
                    </div>
                    <div className="insights-content">
                        {aiAnalysis.insights.primary_location && (
                            <div className="insight-item">
                                <span className="insight-label">Primary Location:</span>
                                <span className="insight-value">{aiAnalysis.insights.primary_location}</span>
                            </div>
                        )}
                        {aiAnalysis.insights.production_notes && (
                            <div className="insight-item">
                                <span className="insight-label">Production Notes:</span>
                                <span className="insight-value">{aiAnalysis.insights.production_notes}</span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Interior Locations */}
            {interiorLocations.length > 0 && (
                <div className="dashboard-section">
                    <h3 className="section-title">
                        <Home size={18} />
                        Interior Locations
                        <span className="section-count">{interiorLocations.length}</span>
                    </h3>
                    <div className="cards-grid">
                        {interiorLocations.map((loc) => {
                            const aiData = getAiDescription(loc.setting);
                            
                            return (
                                <div 
                                    key={loc.setting} 
                                    className="entity-card location-card"
                                    onClick={() => onSelectLocation(loc.setting)}
                                >
                                    <div className="card-header">
                                        <div className="card-avatar location-avatar">
                                            <Home size={18} />
                                        </div>
                                        <div className="card-title-section">
                                            <h4 className="card-name">{loc.displayName}</h4>
                                            <div className="location-badges">
                                                <span className="type-badge interior">INT</span>
                                                <span className="time-badge">
                                                    {getTimeIcon(loc.timeOfDay)}
                                                    {loc.timeOfDay.charAt(0).toUpperCase() + loc.timeOfDay.slice(1)}
                                                </span>
                                            </div>
                                        </div>
                                        <ChevronRight size={18} className="card-arrow" />
                                    </div>
                                    
                                    <div className="card-body">
                                        {/* AI Atmosphere Description */}
                                        {aiData?.atmosphere && (
                                            <div className="ai-description">
                                                <Sparkles size={12} className="ai-icon" />
                                                <p>{aiData.atmosphere}</p>
                                            </div>
                                        )}

                                        {/* Mood Tag */}
                                        {aiData?.mood && (
                                            <div className="mood-tag">
                                                <span>{aiData.mood}</span>
                                            </div>
                                        )}

                                        <div className="card-stat">
                                            <Clapperboard size={14} />
                                            <span>{loc.sceneCount} {loc.sceneCount === 1 ? 'Scene' : 'Scenes'}</span>
                                        </div>
                                        <div className="card-scenes">
                                            {loc.sceneNumbers.map(num => (
                                                <span key={num} className="scene-pill">#{num}</span>
                                            ))}
                                        </div>
                                    </div>

                                    {loc.characters.length > 0 && (
                                        <div className="card-footer">
                                            <Users size={14} className="footer-icon" />
                                            <span className="footer-value">
                                                {loc.characters.slice(0, 3).join(', ')}
                                                {loc.characters.length > 3 && ` +${loc.characters.length - 3}`}
                                            </span>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Exterior Locations */}
            {exteriorLocations.length > 0 && (
                <div className="dashboard-section">
                    <h3 className="section-title">
                        <TreePine size={18} />
                        Exterior Locations
                        <span className="section-count">{exteriorLocations.length}</span>
                    </h3>
                    <div className="cards-grid">
                        {exteriorLocations.map((loc) => {
                            const aiData = getAiDescription(loc.setting);
                            
                            return (
                                <div 
                                    key={loc.setting} 
                                    className="entity-card location-card"
                                    onClick={() => onSelectLocation(loc.setting)}
                                >
                                    <div className="card-header">
                                        <div className="card-avatar location-avatar exterior">
                                            <TreePine size={18} />
                                        </div>
                                        <div className="card-title-section">
                                            <h4 className="card-name">{loc.displayName}</h4>
                                            <div className="location-badges">
                                                <span className="type-badge exterior">EXT</span>
                                                <span className="time-badge">
                                                    {getTimeIcon(loc.timeOfDay)}
                                                    {loc.timeOfDay.charAt(0).toUpperCase() + loc.timeOfDay.slice(1)}
                                                </span>
                                            </div>
                                        </div>
                                        <ChevronRight size={18} className="card-arrow" />
                                    </div>
                                    
                                    <div className="card-body">
                                        {/* AI Atmosphere Description */}
                                        {aiData?.atmosphere && (
                                            <div className="ai-description">
                                                <Sparkles size={12} className="ai-icon" />
                                                <p>{aiData.atmosphere}</p>
                                            </div>
                                        )}

                                        {/* Mood Tag */}
                                        {aiData?.mood && (
                                            <div className="mood-tag">
                                                <span>{aiData.mood}</span>
                                            </div>
                                        )}

                                        <div className="card-stat">
                                            <Clapperboard size={14} />
                                            <span>{loc.sceneCount} {loc.sceneCount === 1 ? 'Scene' : 'Scenes'}</span>
                                        </div>
                                        <div className="card-scenes">
                                            {loc.sceneNumbers.map(num => (
                                                <span key={num} className="scene-pill">#{num}</span>
                                            ))}
                                        </div>
                                    </div>

                                    {loc.characters.length > 0 && (
                                        <div className="card-footer">
                                            <Users size={14} className="footer-icon" />
                                            <span className="footer-value">
                                                {loc.characters.slice(0, 3).join(', ')}
                                                {loc.characters.length > 3 && ` +${loc.characters.length - 3}`}
                                            </span>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
};

export default LocationDashboard;
