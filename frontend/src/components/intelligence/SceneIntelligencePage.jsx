import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
    ArrowLeft,
    Brain,
    Heart,
    MessageSquare,
    ArrowLeftRight,
    Zap,
    Clock,
    Users,
    MapPin,
    Filter,
    X,
    ChevronDown,
    ChevronRight,
    Activity,
    Sun,
    Moon,
    Sunset,
    Loader,
    AlertCircle,
    Eye
} from 'lucide-react';
import { getSceneBreakdown, getScenes, getScriptMetadata } from '../../services/apiService';
import './SceneIntelligencePage.css';

// Confidence dot color helper
const getConfidenceColor = (confidence) => {
    if (confidence >= 0.9) return 'var(--success, #22c55e)';
    if (confidence >= 0.7) return 'var(--warning, #eab308)';
    return 'var(--danger, #f97316)';
};

// Intensity to percentage
const intensityToPercent = (intensity) => {
    const val = (intensity || '').toLowerCase();
    if (val === 'high' || val === 'intense') return 100;
    if (val === 'medium' || val === 'moderate') return 60;
    if (val === 'low' || val === 'subtle') return 30;
    return 50;
};

const SceneIntelligencePage = () => {
    const { scriptId } = useParams();
    const [searchParams] = useSearchParams();
    const sceneId = searchParams.get('sceneId');
    const navigate = useNavigate();

    // Data state
    const [scene, setScene] = useState(null);
    const [enrichment, setEnrichment] = useState(null);
    const [metadata, setMetadata] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // UI state
    const [activeCharFilter, setActiveCharFilter] = useState(null); // null = all
    const [expandedSections, setExpandedSections] = useState({
        emotions: true,
        dialogue: true,
        actions: true,
        relationships: true,
        transitions: true
    });

    // Fetch scene + enrichment data
    useEffect(() => {
        const fetchData = async () => {
            if (!scriptId || !sceneId) {
                setError('Missing script or scene ID');
                setLoading(false);
                return;
            }

            try {
                setLoading(true);

                // Fetch in parallel
                const [scenesRes, breakdownRes, metadataRes] = await Promise.allSettled([
                    getScenes(scriptId),
                    getSceneBreakdown(scriptId, sceneId),
                    getScriptMetadata(scriptId)
                ]);

                // Find the specific scene
                if (scenesRes.status === 'fulfilled') {
                    const scenes = scenesRes.value.scenes || [];
                    const found = scenes.find(s => s.id === sceneId || s.scene_id === sceneId);
                    setScene(found || null);
                }

                // Set enrichment
                if (breakdownRes.status === 'fulfilled') {
                    setEnrichment(breakdownRes.value.enrichment || {});
                }

                // Set metadata
                if (metadataRes.status === 'fulfilled') {
                    setMetadata(metadataRes.value);
                }

                setError(null);
            } catch (err) {
                setError(err.message || 'Failed to load intelligence data');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [scriptId, sceneId]);

    // Extract all unique characters from enrichment data (case-insensitive)
    // Prefers UPPERCASE form (screenplay convention), then Title Case
    const allCharacters = useMemo(() => {
        if (!enrichment) return [];
        // Map: lowercased name → best display form
        const charMap = new Map();

        const addChar = (name) => {
            if (!name || typeof name !== 'string') return;
            const trimmed = name.trim();
            if (!trimmed) return;
            const norm = trimmed.toLowerCase();
            const existing = charMap.get(norm);
            if (!existing) {
                charMap.set(norm, trimmed);
            } else {
                // Prefer UPPERCASE (screenplay standard), then Title Case
                if (trimmed.toUpperCase() === trimmed && existing.toUpperCase() !== existing) {
                    charMap.set(norm, trimmed);
                }
            }
        };

        (enrichment.emotion || []).forEach(e => addChar(e.attributes?.character));
        (enrichment.dialogue || []).forEach(d => addChar(d.attributes?.character));
        (enrichment.action || []).forEach(a => {
            const chars = a.attributes?.characters;
            if (chars) {
                if (typeof chars === 'string') {
                    chars.split(/[,&]/).forEach(c => addChar(c));
                } else if (Array.isArray(chars)) {
                    chars.forEach(c => addChar(c));
                }
            }
        });
        (enrichment.relationship || []).forEach(r => {
            const chars = r.attributes?.characters || r.text;
            if (typeof chars === 'string') {
                chars.split(/[,&]/).forEach(c => addChar(c));
            }
        });

        return Array.from(charMap.values()).sort();
    }, [enrichment]);

    // Filter enrichment by character
    const filtered = useMemo(() => {
        if (!enrichment) return {};
        if (!activeCharFilter) return enrichment;

        const charLower = activeCharFilter.toLowerCase();
        const matchesChar = (item) => {
            const char = item.attributes?.character;
            const chars = item.attributes?.characters;
            const text = item.text || '';

            if (char && char.toLowerCase() === charLower) return true;
            if (typeof chars === 'string' && chars.toLowerCase().includes(charLower)) return true;
            if (Array.isArray(chars) && chars.some(c => c.toLowerCase() === charLower)) return true;
            if (text.toLowerCase().includes(charLower)) return true;
            return false;
        };

        return {
            emotion: (enrichment.emotion || []).filter(matchesChar),
            dialogue: (enrichment.dialogue || []).filter(matchesChar),
            action: (enrichment.action || []).filter(matchesChar),
            relationship: (enrichment.relationship || []).filter(matchesChar),
            transition: enrichment.transition || [] // transitions don't filter by character
        };
    }, [enrichment, activeCharFilter]);

    const toggleSection = useCallback((section) => {
        setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
    }, []);

    // Section counts
    const sectionCounts = useMemo(() => ({
        emotions: (filtered.emotion || []).length,
        dialogue: (filtered.dialogue || []).length,
        actions: (filtered.action || []).length,
        relationships: (filtered.relationship || []).length,
        transitions: (filtered.transition || []).length
    }), [filtered]);

    const totalItems = Object.values(sectionCounts).reduce((a, b) => a + b, 0);

    // Group dialogue by character (case-insensitive, prefer UPPERCASE)
    const dialogueGrouped = useMemo(() => {
        const grouped = {};
        (filtered.dialogue || []).forEach(d => {
            const rawChar = d.attributes?.character || 'Unknown';
            const char = rawChar.trim().toUpperCase();
            if (!grouped[char]) grouped[char] = [];
            grouped[char].push(d);
        });
        return grouped;
    }, [filtered.dialogue]);

    if (loading) {
        return (
            <div className="intel-page-loading">
                <Loader size={40} className="spin" />
                <p>Loading Scene Intelligence...</p>
            </div>
        );
    }

    if (error || !scene) {
        return (
            <div className="intel-page-error">
                <AlertCircle size={48} />
                <h3>Unable to Load Intelligence</h3>
                <p>{error || 'Scene not found'}</p>
                <button className="btn-back" onClick={() => navigate(-1)}>
                    <ArrowLeft size={16} /> Go Back
                </button>
            </div>
        );
    }

    return (
        <div className="intel-page">
            {/* Top Bar */}
            <div className="intel-top-bar">
                <button className="btn-back" onClick={() => navigate(`/scenes/${scriptId}`)}>
                    <ArrowLeft size={18} />
                    <span>Back to Scenes</span>
                </button>
                <div className="intel-top-title">
                    <Brain size={20} className="intel-top-icon" />
                    <h1>Scene Intelligence</h1>
                </div>
                <div className="intel-top-meta">
                    <span className="meta-badge scene-badge">
                        Scene {scene.scene_number_original || scene.scene_number}
                    </span>
                    {metadata?.title && (
                        <span className="meta-script-name">{metadata.title}</span>
                    )}
                </div>
            </div>

            {/* Scene Context Header */}
            <div className="intel-scene-header">
                <div className="scene-header-left">
                    <h2 className="scene-heading">
                        <MapPin size={20} />
                        {scene.int_ext && <span className="int-ext">{scene.int_ext}.</span>}
                        {scene.setting}
                    </h2>
                    <div className="scene-header-badges">
                        {scene.time_of_day && (
                            <span className={`tod-badge ${(scene.time_of_day || '').toLowerCase().includes('night') ? 'night' : 'day'}`}>
                                {(scene.time_of_day || '').toLowerCase().includes('night')
                                    ? <Moon size={12} />
                                    : (scene.time_of_day || '').toLowerCase().includes('sunset') || (scene.time_of_day || '').toLowerCase().includes('dawn')
                                        ? <Sunset size={12} />
                                        : <Sun size={12} />}
                                {scene.time_of_day}
                            </span>
                        )}
                        {scene.emotional_tone && (
                            <span className="tone-header-badge">
                                <Heart size={12} /> {scene.emotional_tone}
                            </span>
                        )}
                    </div>
                    {scene.description && (
                        <p className="scene-description-text">{scene.description}</p>
                    )}
                </div>
                <div className="scene-header-chips">
                    <span className="stat-chip" style={{ '--chip-color': '#a78bfa', '--chip-bg': 'rgba(139,92,246,0.12)' }}>
                        <Users size={13} />
                        <span className="chip-label">Characters</span>
                        <span className="chip-count">{allCharacters.length}</span>
                    </span>
                    {sectionCounts.emotions > 0 && (
                        <span className="stat-chip" style={{ '--chip-color': '#f472b6', '--chip-bg': 'rgba(219,39,119,0.12)' }}>
                            <Heart size={13} />
                            <span className="chip-label">Emotions</span>
                            <span className="chip-count">{sectionCounts.emotions}</span>
                        </span>
                    )}
                    {sectionCounts.dialogue > 0 && (
                        <span className="stat-chip" style={{ '--chip-color': '#5eead4', '--chip-bg': 'rgba(20,184,166,0.12)' }}>
                            <MessageSquare size={13} />
                            <span className="chip-label">Dialogue</span>
                            <span className="chip-count">{sectionCounts.dialogue}</span>
                        </span>
                    )}
                    {sectionCounts.actions > 0 && (
                        <span className="stat-chip" style={{ '--chip-color': '#f87171', '--chip-bg': 'rgba(220,38,38,0.12)' }}>
                            <Activity size={13} />
                            <span className="chip-label">Actions</span>
                            <span className="chip-count">{sectionCounts.actions}</span>
                        </span>
                    )}
                    {sectionCounts.relationships > 0 && (
                        <span className="stat-chip" style={{ '--chip-color': '#f472b6', '--chip-bg': 'rgba(236,72,153,0.12)' }}>
                            <ArrowLeftRight size={13} />
                            <span className="chip-label">Relations</span>
                            <span className="chip-count">{sectionCounts.relationships}</span>
                        </span>
                    )}
                    {sectionCounts.transitions > 0 && (
                        <span className="stat-chip" style={{ '--chip-color': '#fbbf24', '--chip-bg': 'rgba(245,158,11,0.12)' }}>
                            <Clock size={13} />
                            <span className="chip-label">Transitions</span>
                            <span className="chip-count">{sectionCounts.transitions}</span>
                        </span>
                    )}
                </div>
            </div>

            {/* Main Content: Sidebar + Sections */}
            <div className="intel-layout">
                {/* Character Filter Sidebar */}
                <aside className="intel-sidebar">
                    <div className="sidebar-title">
                        <Filter size={16} />
                        <span>Character Lens</span>
                    </div>

                    <button
                        className={`char-filter-btn ${!activeCharFilter ? 'active' : ''}`}
                        onClick={() => setActiveCharFilter(null)}
                    >
                        <Users size={14} />
                        <span>All Characters</span>
                        <span className="char-count">{allCharacters.length}</span>
                    </button>

                    {allCharacters.map(char => (
                        <button
                            key={char}
                            className={`char-filter-btn ${activeCharFilter === char ? 'active' : ''}`}
                            onClick={() => setActiveCharFilter(activeCharFilter === char ? null : char)}
                        >
                            <span className="char-avatar">{char[0]}</span>
                            <span className="char-name">{char}</span>
                        </button>
                    ))}

                    {activeCharFilter && (
                        <button
                            className="clear-filter-btn"
                            onClick={() => setActiveCharFilter(null)}
                        >
                            <X size={14} />
                            Clear Filter
                        </button>
                    )}
                </aside>

                {/* Intelligence Sections */}
                <main className="intel-main">
                    {/* Active filter indicator */}
                    {activeCharFilter && (
                        <div className="active-filter-banner">
                            <Eye size={16} />
                            <span>Viewing through <strong>{activeCharFilter}</strong>'s lens</span>
                            <button onClick={() => setActiveCharFilter(null)}>
                                <X size={14} /> Clear
                            </button>
                        </div>
                    )}

                    {/* ─── EMOTIONS ─── */}
                    <section className="intel-section">
                        <div
                            className="section-header"
                            onClick={() => toggleSection('emotions')}
                            role="button"
                            tabIndex={0}
                        >
                            <span className="section-chevron">
                                {expandedSections.emotions ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                            </span>
                            <Heart size={20} className="section-icon" style={{ color: '#db2777' }} />
                            <h3>Emotions</h3>
                            <span className="section-count" style={{ background: 'rgba(219,39,119,0.15)', color: '#db2777' }}>
                                {sectionCounts.emotions}
                            </span>
                        </div>
                        {expandedSections.emotions && (
                            <div className="section-body">
                                {sectionCounts.emotions === 0 ? (
                                    <p className="empty-section">No emotions extracted for this scene.</p>
                                ) : (
                                    <div className="emotion-grid">
                                        {(filtered.emotion || []).map((e, idx) => {
                                            const intensity = (e.attributes?.intensity || '').toLowerCase();
                                            const barWidth = intensityToPercent(intensity);
                                            return (
                                                <div key={e.id || idx} className="emotion-card">
                                                    <div className="emotion-card-top">
                                                        <span className="emotion-name">{e.text}</span>
                                                        {typeof e.confidence === 'number' && (
                                                            <span
                                                                className="confidence-dot"
                                                                style={{ background: getConfidenceColor(e.confidence) }}
                                                                title={`AI Confidence: ${Math.round(e.confidence * 100)}%`}
                                                            />
                                                        )}
                                                    </div>
                                                    <div className="emotion-bar-track">
                                                        <div className="emotion-bar-fill" style={{ width: `${barWidth}%` }} />
                                                    </div>
                                                    {intensity && (
                                                        <span className="emotion-intensity">{intensity}</span>
                                                    )}
                                                    {/* Drill-down attributes */}
                                                    <div className="emotion-details">
                                                        {e.attributes?.character && (
                                                            <div className="detail-row">
                                                                <span className="detail-label">Character</span>
                                                                <span className="detail-value">{e.attributes.character}</span>
                                                            </div>
                                                        )}
                                                        {e.attributes?.trigger && (
                                                            <div className="detail-row">
                                                                <span className="detail-label">Trigger</span>
                                                                <span className="detail-value">{e.attributes.trigger}</span>
                                                            </div>
                                                        )}
                                                        {e.attributes?.manifestation && (
                                                            <div className="detail-row">
                                                                <span className="detail-label">Manifestation</span>
                                                                <span className="detail-value">{e.attributes.manifestation}</span>
                                                            </div>
                                                        )}
                                                        {e.attributes?.emotion_type && (
                                                            <div className="detail-row">
                                                                <span className="detail-label">Type</span>
                                                                <span className="detail-value chip">{e.attributes.emotion_type}</span>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        )}
                    </section>

                    {/* ─── DIALOGUE ─── */}
                    <section className="intel-section">
                        <div
                            className="section-header"
                            onClick={() => toggleSection('dialogue')}
                            role="button"
                            tabIndex={0}
                        >
                            <span className="section-chevron">
                                {expandedSections.dialogue ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                            </span>
                            <MessageSquare size={20} className="section-icon" style={{ color: '#14b8a6' }} />
                            <h3>Dialogue</h3>
                            <span className="section-count" style={{ background: 'rgba(20,184,166,0.15)', color: '#14b8a6' }}>
                                {sectionCounts.dialogue}
                            </span>
                        </div>
                        {expandedSections.dialogue && (
                            <div className="section-body">
                                {sectionCounts.dialogue === 0 ? (
                                    <p className="empty-section">No dialogue extracted for this scene.</p>
                                ) : (
                                    <div className="dialogue-full-list">
                                        {Object.entries(dialogueGrouped).map(([character, lines]) => (
                                            <div key={character} className="dialogue-char-block">
                                                <div className="dialogue-char-header">
                                                    <span className="dialogue-char-avatar">{character[0]}</span>
                                                    <span className="dialogue-char-name">{character}</span>
                                                    <span className="dialogue-line-count">{lines.length} line{lines.length !== 1 ? 's' : ''}</span>
                                                </div>
                                                <div className="dialogue-lines">
                                                    {lines.map((d, idx) => (
                                                        <div key={d.id || idx} className="dialogue-line-card">
                                                            <div className="dialogue-line-top">
                                                                <span className="dialogue-quote">"{d.text}"</span>
                                                                {typeof d.confidence === 'number' && (
                                                                    <span
                                                                        className="confidence-dot"
                                                                        style={{ background: getConfidenceColor(d.confidence) }}
                                                                        title={`AI Confidence: ${Math.round(d.confidence * 100)}%`}
                                                                    />
                                                                )}
                                                            </div>
                                                            <div className="dialogue-line-meta">
                                                                {d.attributes?.tone && (
                                                                    <span className="dl-tone-badge">{d.attributes.tone}</span>
                                                                )}
                                                                {d.attributes?.parenthetical && (
                                                                    <span className="dl-parenthetical">({d.attributes.parenthetical})</span>
                                                                )}
                                                                {d.attributes?.subtext && (
                                                                    <span className="dl-subtext" title="Subtext">
                                                                        <em>Subtext: {d.attributes.subtext}</em>
                                                                    </span>
                                                                )}
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </section>

                    {/* ─── ACTION BEATS ─── */}
                    <section className="intel-section">
                        <div
                            className="section-header"
                            onClick={() => toggleSection('actions')}
                            role="button"
                            tabIndex={0}
                        >
                            <span className="section-chevron">
                                {expandedSections.actions ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                            </span>
                            <Activity size={20} className="section-icon" style={{ color: '#dc2626' }} />
                            <h3>Action Beats</h3>
                            <span className="section-count" style={{ background: 'rgba(220,38,38,0.15)', color: '#dc2626' }}>
                                {sectionCounts.actions}
                            </span>
                        </div>
                        {expandedSections.actions && (
                            <div className="section-body">
                                {sectionCounts.actions === 0 ? (
                                    <p className="empty-section">No action beats extracted for this scene.</p>
                                ) : (
                                    <div className="action-list">
                                        {(filtered.action || []).map((a, idx) => {
                                            const intensity = (a.attributes?.intensity || '').toLowerCase();
                                            return (
                                                <div key={a.id || idx} className={`action-card intensity-${intensity || 'medium'}`}>
                                                    <div className="action-card-top">
                                                        <Zap size={14} className="action-zap" />
                                                        <span className="action-text">{a.text}</span>
                                                        {typeof a.confidence === 'number' && (
                                                            <span
                                                                className="confidence-dot"
                                                                style={{ background: getConfidenceColor(a.confidence) }}
                                                                title={`AI Confidence: ${Math.round(a.confidence * 100)}%`}
                                                            />
                                                        )}
                                                    </div>
                                                    <div className="action-details">
                                                        {a.attributes?.type && (
                                                            <span className="action-type-badge">{a.attributes.type}</span>
                                                        )}
                                                        {intensity && (
                                                            <span className={`action-intensity-badge ${intensity}`}>{intensity}</span>
                                                        )}
                                                        {a.attributes?.importance && (
                                                            <span className="action-importance">{a.attributes.importance.replace(/_/g, ' ')}</span>
                                                        )}
                                                        {a.attributes?.characters && (
                                                            <span className="action-chars">
                                                                <Users size={12} />
                                                                {typeof a.attributes.characters === 'string'
                                                                    ? a.attributes.characters
                                                                    : a.attributes.characters.join(', ')}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        )}
                    </section>

                    {/* ─── RELATIONSHIPS ─── */}
                    <section className="intel-section">
                        <div
                            className="section-header"
                            onClick={() => toggleSection('relationships')}
                            role="button"
                            tabIndex={0}
                        >
                            <span className="section-chevron">
                                {expandedSections.relationships ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                            </span>
                            <ArrowLeftRight size={20} className="section-icon" style={{ color: '#ec4899' }} />
                            <h3>Relationships</h3>
                            <span className="section-count" style={{ background: 'rgba(236,72,153,0.15)', color: '#ec4899' }}>
                                {sectionCounts.relationships}
                            </span>
                        </div>
                        {expandedSections.relationships && (
                            <div className="section-body">
                                {sectionCounts.relationships === 0 ? (
                                    <p className="empty-section">No relationships extracted for this scene.</p>
                                ) : (
                                    <div className="relationship-list">
                                        {(filtered.relationship || []).map((r, idx) => {
                                            const chars = r.attributes?.characters || r.text;
                                            const dynamic = r.attributes?.dynamic;
                                            const relType = r.attributes?.type;
                                            const development = r.attributes?.development;
                                            return (
                                                <div key={r.id || idx} className="relationship-card">
                                                    <div className="rel-card-top">
                                                        <ArrowLeftRight size={14} className="rel-icon" />
                                                        <span className="rel-chars">{chars}</span>
                                                        {typeof r.confidence === 'number' && (
                                                            <span
                                                                className="confidence-dot"
                                                                style={{ background: getConfidenceColor(r.confidence) }}
                                                                title={`AI Confidence: ${Math.round(r.confidence * 100)}%`}
                                                            />
                                                        )}
                                                    </div>
                                                    <div className="rel-details">
                                                        {relType && <span className="rel-type-badge">{relType}</span>}
                                                        {dynamic && <span className="rel-dynamic">{dynamic}</span>}
                                                        {development && (
                                                            <span className="rel-development">{development}</span>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        )}
                    </section>

                    {/* ─── TRANSITIONS ─── */}
                    <section className="intel-section">
                        <div
                            className="section-header"
                            onClick={() => toggleSection('transitions')}
                            role="button"
                            tabIndex={0}
                        >
                            <span className="section-chevron">
                                {expandedSections.transitions ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                            </span>
                            <Clock size={20} className="section-icon" style={{ color: '#f59e0b' }} />
                            <h3>Transitions</h3>
                            <span className="section-count" style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b' }}>
                                {sectionCounts.transitions}
                            </span>
                        </div>
                        {expandedSections.transitions && (
                            <div className="section-body">
                                {sectionCounts.transitions === 0 ? (
                                    <p className="empty-section">No transitions extracted for this scene.</p>
                                ) : (
                                    <div className="transition-list">
                                        {(filtered.transition || []).map((t, idx) => (
                                            <div key={t.id || idx} className="transition-card">
                                                <div className="trans-card-top">
                                                    <Clock size={14} />
                                                    <span className="trans-text">{t.text}</span>
                                                </div>
                                                <div className="trans-details">
                                                    {t.attributes?.type && (
                                                        <span className="trans-type-badge">{t.attributes.type}</span>
                                                    )}
                                                    {t.attributes?.timing && (
                                                        <span className="trans-timing">{t.attributes.timing}</span>
                                                    )}
                                                    {t.attributes?.time_jump && (
                                                        <span className="trans-jump">{t.attributes.time_jump}</span>
                                                    )}
                                                    {t.attributes?.purpose && (
                                                        <span className="trans-purpose">{t.attributes.purpose}</span>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </section>
                </main>
            </div>
        </div>
    );
};

export default SceneIntelligencePage;
