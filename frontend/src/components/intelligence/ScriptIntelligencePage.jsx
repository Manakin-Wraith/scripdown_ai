import React, { useState, useEffect, useMemo } from 'react';
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
    Activity,
    Sun,
    Moon,
    Sunset,
    Loader,
    AlertCircle,
    ChevronRight,
    ExternalLink
} from 'lucide-react';
import { getScriptIntelligence, getScriptMetadata } from '../../services/apiService';
import SceneIntelligencePage from './SceneIntelligencePage';
import './ScriptIntelligencePage.css';

const ScriptIntelligencePage = () => {
    const { scriptId } = useParams();
    const [searchParams] = useSearchParams();
    const sceneId = searchParams.get('sceneId');
    const navigate = useNavigate();

    // If sceneId is present, render the scene-level page instead
    if (sceneId) {
        return <SceneIntelligencePage />;
    }

    return <ScriptIntelligenceOverview scriptId={scriptId} navigate={navigate} />;
};

const ScriptIntelligenceOverview = ({ scriptId, navigate }) => {
    const [data, setData] = useState(null);
    const [metadata, setMetadata] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            if (!scriptId) {
                setError('Missing script ID');
                setLoading(false);
                return;
            }
            try {
                setLoading(true);
                const [intelRes, metaRes] = await Promise.allSettled([
                    getScriptIntelligence(scriptId),
                    getScriptMetadata(scriptId)
                ]);
                if (intelRes.status === 'fulfilled') setData(intelRes.value);
                if (metaRes.status === 'fulfilled') setMetadata(metaRes.value);
                if (intelRes.status === 'rejected') throw intelRes.reason;
                setError(null);
            } catch (err) {
                setError(err.message || 'Failed to load script intelligence');
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [scriptId]);

    const totals = data?.totals || {};
    const characters = data?.characters || [];
    const relationships = data?.relationships || [];
    const scenes = data?.scenes || [];

    // Sort characters by dialogue count descending
    const sortedCharacters = useMemo(() =>
        [...characters].sort((a, b) => b.dialogue_count - a.dialogue_count),
        [characters]
    );

    // Find max dialogue count for bar width scaling
    const maxDialogue = useMemo(() =>
        Math.max(1, ...characters.map(c => c.dialogue_count)),
        [characters]
    );

    if (loading) {
        return (
            <div className="script-intel-loading">
                <Loader size={40} className="spin" />
                <p>Loading Script Intelligence...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="script-intel-error">
                <AlertCircle size={48} />
                <h3>Unable to Load Intelligence</h3>
                <p>{error}</p>
                <button className="btn-back" onClick={() => navigate(-1)}>
                    <ArrowLeft size={16} /> Go Back
                </button>
            </div>
        );
    }

    return (
        <div className="script-intel-page">
            {/* Top Bar */}
            <div className="script-intel-top-bar">
                <button className="btn-back" onClick={() => navigate(`/scenes/${scriptId}`)}>
                    <ArrowLeft size={18} />
                    <span>Back to Scenes</span>
                </button>
                <div className="script-intel-top-title">
                    <Brain size={20} className="script-intel-icon" />
                    <h1>Script Intelligence</h1>
                </div>
                <div className="script-intel-top-meta">
                    {metadata?.title && (
                        <span className="meta-script-title">{metadata.title}</span>
                    )}
                    <span className="meta-scene-count">{data?.total_scenes || 0} Scenes</span>
                </div>
            </div>

            {/* Aggregate Stats Chips */}
            <div className="script-intel-stats">
                <span className="stat-chip" style={{ '--chip-color': '#a78bfa', '--chip-bg': 'rgba(139,92,246,0.12)' }}>
                    <Users size={13} />
                    <span className="chip-label">Characters</span>
                    <span className="chip-count">{characters.length}</span>
                </span>
                {totals.emotions > 0 && (
                    <span className="stat-chip" style={{ '--chip-color': '#f472b6', '--chip-bg': 'rgba(219,39,119,0.12)' }}>
                        <Heart size={13} />
                        <span className="chip-label">Emotions</span>
                        <span className="chip-count">{totals.emotions}</span>
                    </span>
                )}
                {totals.dialogue > 0 && (
                    <span className="stat-chip" style={{ '--chip-color': '#5eead4', '--chip-bg': 'rgba(20,184,166,0.12)' }}>
                        <MessageSquare size={13} />
                        <span className="chip-label">Dialogue</span>
                        <span className="chip-count">{totals.dialogue}</span>
                    </span>
                )}
                {totals.actions > 0 && (
                    <span className="stat-chip" style={{ '--chip-color': '#f87171', '--chip-bg': 'rgba(220,38,38,0.12)' }}>
                        <Activity size={13} />
                        <span className="chip-label">Actions</span>
                        <span className="chip-count">{totals.actions}</span>
                    </span>
                )}
                {totals.relationships > 0 && (
                    <span className="stat-chip" style={{ '--chip-color': '#f472b6', '--chip-bg': 'rgba(236,72,153,0.12)' }}>
                        <ArrowLeftRight size={13} />
                        <span className="chip-label">Relations</span>
                        <span className="chip-count">{totals.relationships}</span>
                    </span>
                )}
                {totals.transitions > 0 && (
                    <span className="stat-chip" style={{ '--chip-color': '#fbbf24', '--chip-bg': 'rgba(245,158,11,0.12)' }}>
                        <Clock size={13} />
                        <span className="chip-label">Transitions</span>
                        <span className="chip-count">{totals.transitions}</span>
                    </span>
                )}
            </div>

            {/* Main Content */}
            <div className="script-intel-content">
                {/* Characters Dashboard */}
                <section className="script-intel-section">
                    <div className="section-title">
                        <Users size={18} style={{ color: '#a78bfa' }} />
                        <h2>Characters</h2>
                        <span className="section-subtitle">{characters.length} across {data?.total_scenes} scenes</span>
                    </div>
                    <div className="char-dashboard">
                        {sortedCharacters.map(char => (
                            <div key={char.name} className="char-row">
                                <div className="char-row-left">
                                    <span className="char-avatar-lg">{char.name[0]}</span>
                                    <div className="char-info">
                                        <span className="char-name-lg">{char.name}</span>
                                        <span className="char-scenes-list">
                                            Scenes: {char.scenes.join(', ')}
                                        </span>
                                    </div>
                                </div>
                                <div className="char-row-middle">
                                    <div className="char-bar-track">
                                        <div
                                            className="char-bar-fill dialogue"
                                            style={{ width: `${(char.dialogue_count / maxDialogue) * 100}%` }}
                                        />
                                    </div>
                                </div>
                                <div className="char-row-stats">
                                    <span className="char-stat" title="Dialogue lines">
                                        <MessageSquare size={12} style={{ color: '#14b8a6' }} />
                                        {char.dialogue_count}
                                    </span>
                                    <span className="char-stat" title="Emotions">
                                        <Heart size={12} style={{ color: '#db2777' }} />
                                        {char.emotion_count}
                                    </span>
                                    <span className="char-stat" title="Actions">
                                        <Activity size={12} style={{ color: '#dc2626' }} />
                                        {char.action_count}
                                    </span>
                                    <span className="char-stat" title="Scenes">
                                        <MapPin size={12} style={{ color: '#a78bfa' }} />
                                        {char.scene_count}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Relationships */}
                {relationships.length > 0 && (
                    <section className="script-intel-section">
                        <div className="section-title">
                            <ArrowLeftRight size={18} style={{ color: '#ec4899' }} />
                            <h2>Relationships</h2>
                            <span className="section-subtitle">{relationships.length} across the script</span>
                        </div>
                        <div className="rel-dashboard">
                            {relationships.map((r, idx) => {
                                const chars = r.attributes?.characters || r.text;
                                return (
                                    <div key={r.id || idx} className="rel-card-overview">
                                        <div className="rel-card-header">
                                            <ArrowLeftRight size={14} style={{ color: '#ec4899' }} />
                                            <span className="rel-chars-name">{chars}</span>
                                            <span className="rel-scene-badge">Scene {r.scene_number}</span>
                                        </div>
                                        <div className="rel-card-meta">
                                            {r.attributes?.type && (
                                                <span className="rel-type-pill">{r.attributes.type}</span>
                                            )}
                                            {r.attributes?.dynamic && (
                                                <span className="rel-dynamic-text">{r.attributes.dynamic}</span>
                                            )}
                                            {r.attributes?.development && (
                                                <span className="rel-dev-text">{r.attributes.development}</span>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </section>
                )}

                {/* Scene Cards Grid */}
                <section className="script-intel-section">
                    <div className="section-title">
                        <MapPin size={18} style={{ color: '#818cf8' }} />
                        <h2>Scenes</h2>
                        <span className="section-subtitle">Click a scene to explore its intelligence</span>
                    </div>
                    <div className="scene-cards-grid">
                        {scenes.map(s => {
                            const hasData = s.total_items > 0;
                            return (
                                <div
                                    key={s.scene_id}
                                    className={`scene-intel-card ${hasData ? 'has-data' : 'empty'}`}
                                    onClick={() => {
                                        if (hasData) {
                                            navigate(`/scenes/${scriptId}/intelligence?sceneId=${s.scene_id}`);
                                        }
                                    }}
                                    role={hasData ? 'button' : undefined}
                                    tabIndex={hasData ? 0 : undefined}
                                >
                                    <div className="scene-card-header">
                                        <span className="scene-card-number">Scene {s.scene_number}</span>
                                        {hasData && <ChevronRight size={14} className="scene-card-arrow" />}
                                    </div>
                                    <div className="scene-card-location">
                                        {s.int_ext && <span className="scene-card-ie">{s.int_ext}.</span>}
                                        <span>{s.setting}</span>
                                    </div>
                                    {s.time_of_day && (
                                        <span className={`scene-card-tod ${(s.time_of_day || '').toLowerCase().includes('night') ? 'night' : 'day'}`}>
                                            {(s.time_of_day || '').toLowerCase().includes('night')
                                                ? <Moon size={10} />
                                                : (s.time_of_day || '').toLowerCase().includes('sunset') || (s.time_of_day || '').toLowerCase().includes('dawn')
                                                    ? <Sunset size={10} />
                                                    : <Sun size={10} />}
                                            {s.time_of_day}
                                        </span>
                                    )}
                                    {hasData ? (
                                        <div className="scene-card-chips">
                                            {s.counts.dialogue > 0 && (
                                                <span className="scene-chip teal">
                                                    <MessageSquare size={10} /> {s.counts.dialogue}
                                                </span>
                                            )}
                                            {s.counts.emotions > 0 && (
                                                <span className="scene-chip pink">
                                                    <Heart size={10} /> {s.counts.emotions}
                                                </span>
                                            )}
                                            {s.counts.actions > 0 && (
                                                <span className="scene-chip red">
                                                    <Activity size={10} /> {s.counts.actions}
                                                </span>
                                            )}
                                            {s.counts.relationships > 0 && (
                                                <span className="scene-chip rose">
                                                    <ArrowLeftRight size={10} /> {s.counts.relationships}
                                                </span>
                                            )}
                                            {s.counts.transitions > 0 && (
                                                <span className="scene-chip amber">
                                                    <Clock size={10} /> {s.counts.transitions}
                                                </span>
                                            )}
                                        </div>
                                    ) : (
                                        <span className="scene-card-empty">No intelligence data</span>
                                    )}
                                    {s.emotional_tone && (
                                        <span className="scene-card-tone">{s.emotional_tone}</span>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </section>
            </div>
        </div>
    );
};

export default ScriptIntelligencePage;
