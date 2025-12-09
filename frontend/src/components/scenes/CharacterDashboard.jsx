import React, { useMemo, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Clapperboard, Star, TrendingUp, ChevronRight, Sparkles, RefreshCw } from 'lucide-react';
import { analyzeCharacters } from '../../services/apiService';
import './Dashboard.css';

const CharacterDashboard = ({ characters, scenes, onSelectCharacter, scriptId }) => {
    const navigate = useNavigate();
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
                const result = await analyzeCharacters(scriptId);
                setAiAnalysis(result);
            } catch (err) {
                console.error('Failed to fetch character analysis:', err);
                setAnalysisError('AI analysis unavailable');
            } finally {
                setAnalysisLoading(false);
            }
        };

        fetchAnalysis();
    }, [scriptId]);

    // Get AI description for a character
    const getAiDescription = (charName) => {
        if (!aiAnalysis?.characters) return null;
        return aiAnalysis.characters[charName] || null;
    };

    // Calculate statistics
    const stats = useMemo(() => {
        const charNames = Object.keys(characters);
        const totalCharacters = charNames.length;
        
        // Sort by scene count to determine leads vs supporting
        const sortedByAppearances = charNames
            .map(name => ({
                name,
                sceneCount: characters[name].length
            }))
            .sort((a, b) => b.sceneCount - a.sceneCount);
        
        // Lead characters appear in more than 50% of scenes, or top 2
        const leadThreshold = Math.max(2, Math.ceil(scenes.length * 0.5));
        const leads = sortedByAppearances.filter(c => c.sceneCount >= leadThreshold).length || 
                      Math.min(2, sortedByAppearances.length);
        
        const supporting = totalCharacters - leads;
        
        // Average scenes per character
        const totalAppearances = sortedByAppearances.reduce((sum, c) => sum + c.sceneCount, 0);
        const avgScenes = totalCharacters > 0 ? (totalAppearances / totalCharacters).toFixed(1) : 0;
        
        return {
            total: totalCharacters,
            leads: Math.min(leads, totalCharacters),
            supporting: Math.max(0, supporting),
            avgScenes
        };
    }, [characters, scenes]);

    // Process character data for cards
    const characterCards = useMemo(() => {
        return Object.entries(characters)
            .map(([name, charScenes]) => {
                const sceneNumbers = charScenes.map(s => s.scene_number).sort((a, b) => a - b);
                const isLead = charScenes.length >= Math.ceil(scenes.length * 0.5) || 
                               charScenes.length >= 2;
                
                // Get co-appearing characters
                const coAppearing = new Set();
                charScenes.forEach(scene => {
                    if (scene.characters) {
                        scene.characters.forEach(c => {
                            if (c !== name) coAppearing.add(c);
                        });
                    }
                });

                return {
                    name,
                    sceneCount: charScenes.length,
                    sceneNumbers,
                    isLead,
                    coAppearing: Array.from(coAppearing).slice(0, 3),
                    scenes: charScenes
                };
            })
            .sort((a, b) => b.sceneCount - a.sceneCount);
    }, [characters, scenes]);

    if (Object.keys(characters).length === 0) {
        return (
            <div className="dashboard-empty">
                <Users size={48} className="empty-icon" />
                <h3>No Characters Found</h3>
                <p>Characters will appear here once the script is analyzed</p>
            </div>
        );
    }

    return (
        <div className="dashboard">
            {/* Header */}
            <div className="dashboard-header">
                <div className="dashboard-title">
                    <Users size={24} className="title-icon" />
                    <h2>Character Overview</h2>
                </div>
                <span className="dashboard-count">{stats.total} Characters</span>
            </div>

            {/* Stats Grid */}
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-icon-wrapper blue">
                        <Users size={20} />
                    </div>
                    <div className="stat-content">
                        <span className="stat-value">{stats.total}</span>
                        <span className="stat-label">Total Characters</span>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon-wrapper indigo">
                        <Star size={20} />
                    </div>
                    <div className="stat-content">
                        <span className="stat-value">{stats.leads}</span>
                        <span className="stat-label">Lead Roles</span>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon-wrapper purple">
                        <Users size={20} />
                    </div>
                    <div className="stat-content">
                        <span className="stat-value">{stats.supporting}</span>
                        <span className="stat-label">Supporting</span>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon-wrapper emerald">
                        <TrendingUp size={20} />
                    </div>
                    <div className="stat-content">
                        <span className="stat-value">{stats.avgScenes}</span>
                        <span className="stat-label">Avg Scenes</span>
                    </div>
                </div>
            </div>

            {/* AI Analysis Status */}
            {analysisLoading && (
                <div className="ai-status loading">
                    <RefreshCw size={16} className="spin" />
                    <span>Analyzing characters with AI...</span>
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
                        {aiAnalysis.insights.protagonist && (
                            <div className="insight-item">
                                <span className="insight-label">Protagonist:</span>
                                <span className="insight-value">{aiAnalysis.insights.protagonist}</span>
                            </div>
                        )}
                        {aiAnalysis.insights.antagonist && (
                            <div className="insight-item">
                                <span className="insight-label">Antagonist:</span>
                                <span className="insight-value">{aiAnalysis.insights.antagonist}</span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Story Arc */}
            {aiAnalysis?.story_arc && (
                <div className="story-arc-section">
                    <div className="arc-header">
                        <h3>Story Arc</h3>
                    </div>
                    <div className="arc-content">
                        {aiAnalysis.story_arc.theme && (
                            <div className="arc-item">
                                <span className="arc-label">Theme:</span>
                                <span className="arc-value">{aiAnalysis.story_arc.theme}</span>
                            </div>
                        )}
                        {aiAnalysis.story_arc.tone && (
                            <div className="arc-item">
                                <span className="arc-label">Tone:</span>
                                <span className="arc-value tone-tag">{aiAnalysis.story_arc.tone}</span>
                            </div>
                        )}
                        {aiAnalysis.story_arc.conflict_type && (
                            <div className="arc-item">
                                <span className="arc-label">Conflict:</span>
                                <span className="arc-value">{aiAnalysis.story_arc.conflict_type.replace(/_/g, ' ')}</span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Character Cards */}
            <div className="dashboard-section">
                <h3 className="section-title">All Characters</h3>
                <div className="cards-grid">
                    {characterCards.map((char) => {
                        const aiData = getAiDescription(char.name);
                        
                        // Navigate to character profile page
                        const handleCardClick = () => {
                            const encodedName = encodeURIComponent(char.name);
                            navigate(`/scripts/${scriptId}/characters/${encodedName}`);
                        };

                        return (
                            <div 
                                key={char.name} 
                                className="entity-card"
                                onClick={handleCardClick}
                            >
                                <div className="card-header">
                                    <div className="card-avatar">
                                        {char.name.charAt(0).toUpperCase()}
                                    </div>
                                    <div className="card-title-section">
                                        <h4 className="card-name">{char.name}</h4>
                                        <span className={`role-badge ${aiData?.role_type?.toLowerCase() === 'lead' || char.isLead ? 'lead' : 'supporting'}`}>
                                            {aiData?.role_type || (char.isLead ? 'Lead' : 'Supporting')}
                                        </span>
                                    </div>
                                    <ChevronRight size={18} className="card-arrow" />
                                </div>
                                
                                <div className="card-body">
                                    {/* AI Description */}
                                    {aiData?.description && (
                                        <div className="ai-description">
                                            <Sparkles size={12} className="ai-icon" />
                                            <p>{aiData.description}</p>
                                        </div>
                                    )}

                                    {/* Character Arc Summary */}
                                    {aiData?.arc_summary && (
                                        <div className="arc-summary">
                                            <span className="arc-label">Arc:</span>
                                            <span className="arc-text">{aiData.arc_summary}</span>
                                        </div>
                                    )}

                                    {/* Emotional Journey */}
                                    {aiData?.emotional_journey && Object.keys(aiData.emotional_journey).length > 0 && (
                                        <div className="emotional-journey">
                                            <span className="journey-label">Emotional Journey:</span>
                                            <div className="journey-timeline">
                                                {Object.entries(aiData.emotional_journey).map(([sceneNum, data]) => (
                                                    <div key={sceneNum} className="journey-point" title={data.description}>
                                                        <span className="scene-num">#{sceneNum}</span>
                                                        <span className={`emotion-tag intensity-${Math.min(10, Math.max(1, data.intensity || 5))}`}>
                                                            {data.emotion}
                                                        </span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Traits */}
                                    {aiData?.traits && aiData.traits.length > 0 && (
                                        <div className="traits-container">
                                            {aiData.traits.map((trait, idx) => (
                                                <span key={idx} className="trait-tag">{trait}</span>
                                            ))}
                                        </div>
                                    )}

                                    <div className="card-stat">
                                        <Clapperboard size={14} />
                                        <span>{char.sceneCount} {char.sceneCount === 1 ? 'Scene' : 'Scenes'}</span>
                                    </div>
                                    <div className="card-scenes">
                                        {char.sceneNumbers.map(num => (
                                            <span key={num} className="scene-pill">#{num}</span>
                                        ))}
                                    </div>
                                </div>

                            {char.coAppearing.length > 0 && (
                                <div className="card-footer">
                                    <span className="footer-label">Appears with:</span>
                                    <span className="footer-value">
                                        {char.coAppearing.join(', ')}
                                    </span>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    </div>
);
};

export default CharacterDashboard;
