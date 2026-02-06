import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
    Clapperboard,
    MapPin,
    Zap,
    Loader,
    Clock,
    MessageSquare,
    Activity,
    Heart,
    Camera,
    Sparkles,
    Info,
    ShieldCheck,
    ChevronRight,
    ChevronDown,
    Eye,
    EyeOff,
    Brain,
    ArrowLeftRight,
    Sun,
    Moon,
    Sunset
} from 'lucide-react';
import NoteDrawer from '../notes/NoteDrawer';
import { getScriptNotes, getSceneBreakdown } from '../../services/apiService';
import { getSceneEighthsDisplay } from '../../utils/sceneUtils';
import { SCENE_CATEGORIES, CATEGORY_DEPARTMENTS } from '../../config/extractionClassConfig';
import './SceneDetail.css';

// Tier thresholds
const HERO_THRESHOLD = 4; // ≥4 items → expanded by default

// Confidence dot color helper
const getConfidenceColor = (confidence) => {
    if (confidence >= 0.9) return 'var(--success, #22c55e)';
    if (confidence >= 0.7) return 'var(--warning, #eab308)';
    return 'var(--danger, #f97316)';
};

/**
 * SceneDetail - Tiered Accordion breakdown layout
 * Hero (≥4 items) → expanded by default
 * Summary (1-3 items) → collapsed, inline preview
 * Hidden (0 items) → tucked under disclosure toggle
 */
const SceneDetail = ({ scene, scriptId, onAnalyze, isAnalyzing = false, pageMapping = null }) => {
    const navigate = useNavigate();
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [activeCategory, setActiveCategory] = useState(null);
    const [noteCounts, setNoteCounts] = useState({});
    const [richBreakdown, setRichBreakdown] = useState(null);
    const [enrichment, setEnrichment] = useState(null);
    const [breakdownLoading, setBreakdownLoading] = useState(false);
    const [expandedCategories, setExpandedCategories] = useState({});
    const [showEmptyCategories, setShowEmptyCategories] = useState(false);
    const [intelligenceOpen, setIntelligenceOpen] = useState(true);

    // Fetch rich breakdown data from extraction_metadata
    useEffect(() => {
        const fetchBreakdown = async () => {
            if (!scene || !scriptId) return;
            const sceneId = scene.id || scene.scene_id;
            if (!sceneId) return;

            setBreakdownLoading(true);
            try {
                const data = await getSceneBreakdown(scriptId, sceneId);
                setRichBreakdown(data.breakdown || null);
                setEnrichment(data.enrichment || null);
            } catch (err) {
                console.warn('Rich breakdown unavailable, using flat scene data:', err.message);
                setRichBreakdown(null);
                setEnrichment(null);
            } finally {
                setBreakdownLoading(false);
            }
        };

        fetchBreakdown();
    }, [scene, scriptId]);

    // Fetch note counts for badges
    useEffect(() => {
        const fetchNoteCounts = async () => {
            if (!scene || !scriptId) return;
            
            try {
                const sceneId = scene.id || scene.scene_id;
                const response = await getScriptNotes(scriptId, { scene_id: sceneId });
                const notes = response.notes || [];
                
                const counts = {};
                Object.keys(CATEGORY_DEPARTMENTS).forEach(category => {
                    counts[category] = notes.filter(n => n.note_type === category).length;
                });
                
                setNoteCounts(counts);
            } catch (err) {
                console.error('Error fetching note counts:', err);
            }
        };
        
        fetchNoteCounts();
    }, [scene, scriptId]);

    /**
     * Get items for a category: prefer rich extraction data, fall back to flat scene arrays.
     * Rich items have { text, attributes, confidence }, flat items are strings.
     */
    const getCategoryItems = useCallback((categoryKey) => {
        if (richBreakdown && richBreakdown[categoryKey] && richBreakdown[categoryKey].length > 0) {
            // Deduplicate rich items case-insensitively (safety net — backend should already dedup)
            const seen = new Map();
            for (const item of richBreakdown[categoryKey]) {
                const norm = (item.text || '').trim().toLowerCase();
                if (!norm) continue;
                const existing = seen.get(norm);
                if (!existing || (item.confidence || 0) > (existing.confidence || 0)) {
                    seen.set(norm, item);
                }
            }
            return { items: Array.from(seen.values()), isRich: true };
        }
        // Deduplicate flat items case-insensitively
        const flatItems = scene[categoryKey] || [];
        const seen = new Set();
        const deduped = flatItems.filter(item => {
            const text = (typeof item === 'string' ? item : item?.name || String(item)).trim().toLowerCase();
            if (seen.has(text)) return false;
            seen.add(text);
            return true;
        });
        return { items: deduped, isRich: false };
    }, [richBreakdown, scene]);

    /**
     * Sort categories by item count descending, split into tiers.
     */
    const { heroCategories, summaryCategories, emptyCategories } = useMemo(() => {
        const sorted = Object.entries(SCENE_CATEGORIES)
            .map(([key, config]) => {
                const { items, isRich } = getCategoryItems(key);
                return { key, config, items, isRich, count: items.length };
            })
            .sort((a, b) => b.count - a.count);

        return {
            heroCategories: sorted.filter(c => c.count >= HERO_THRESHOLD),
            summaryCategories: sorted.filter(c => c.count > 0 && c.count < HERO_THRESHOLD),
            emptyCategories: sorted.filter(c => c.count === 0)
        };
    }, [getCategoryItems]);


    // Reset expanded state when scene changes; auto-expand hero categories
    useEffect(() => {
        const initial = {};
        heroCategories.forEach(c => { initial[c.key] = true; });
        setExpandedCategories(initial);
        setShowEmptyCategories(false);
    }, [scene?.id, scene?.scene_id]); // eslint-disable-line react-hooks/exhaustive-deps

    const toggleCategory = (categoryKey) => {
        setExpandedCategories(prev => ({
            ...prev,
            [categoryKey]: !prev[categoryKey]
        }));
    };

    const openDrawer = (category, title) => {
        setActiveCategory({ key: category, title });
        setDrawerOpen(true);
    };

    const closeDrawer = () => {
        setDrawerOpen(false);
        setActiveCategory(null);
        if (scene && scriptId) {
            const sceneId = scene.id || scene.scene_id;
            getScriptNotes(scriptId, { scene_id: sceneId }).then(response => {
                const notes = response.notes || [];
                const counts = {};
                Object.keys(CATEGORY_DEPARTMENTS).forEach(category => {
                    counts[category] = notes.filter(n => n.note_type === category).length;
                });
                setNoteCounts(counts);
            }).catch(console.error);
        }
    };

    /** Render a single accordion row */
    const renderAccordionRow = ({ key, config, items, isRich, count }) => {
        const Icon = config.icon;
        const isExpanded = !!expandedCategories[key];
        const noteCount = noteCounts[key] || 0;

        return (
            <div key={key} className={`accordion-row ${isExpanded ? 'expanded' : ''}`}>
                <div
                    className="accordion-header"
                    role="button"
                    tabIndex={0}
                    aria-expanded={isExpanded}
                    aria-controls={`accordion-panel-${key}`}
                    onClick={() => toggleCategory(key)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            toggleCategory(key);
                        }
                    }}
                    style={{ '--accent-color': config.color }}
                >
                    <span className="accordion-chevron">
                        {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </span>
                    <Icon size={18} className="accordion-icon" style={{ color: config.color }} />
                    <span className="accordion-label">{config.label}</span>
                    <span className="accordion-count" style={{ 
                        background: `${config.color}22`,
                        color: config.color 
                    }}>
                        {count}
                    </span>
                    {isRich && (
                        <span className="rich-badge" title="Rich extraction data">
                            <ShieldCheck size={12} />
                        </span>
                    )}
                    {noteCount > 0 && (
                        <button
                            className="note-badge"
                            onClick={(e) => { e.stopPropagation(); openDrawer(key, config.label); }}
                            title={`${noteCount} note${noteCount > 1 ? 's' : ''} — click to view`}
                        >
                            <MessageSquare size={12} />
                            {noteCount}
                        </button>
                    )}
                    <button
                        className="accordion-note-btn"
                        onClick={(e) => { e.stopPropagation(); openDrawer(key, config.label); }}
                        title="Add note"
                    >
                        <MessageSquare size={14} />
                    </button>
                    {/* Inline summary when collapsed and has items */}
                    {!isExpanded && count > 0 && (
                        <span className="accordion-inline-summary">
                            {items.slice(0, 3).map((item, idx) => (
                                <span key={idx} className={`inline-tag ${config.tagClass}`}>
                                    {isRich ? item.text : (typeof item === 'string' ? item : item?.name || String(item))}
                                </span>
                            ))}
                            {count > 3 && <span className="inline-more">+{count - 3}</span>}
                        </span>
                    )}
                </div>

                {/* Expandable panel */}
                <div
                    id={`accordion-panel-${key}`}
                    className="accordion-panel"
                    role="region"
                >
                    {isExpanded && (
                        <div className="accordion-content">
                            {isRich ? (
                                <div className="rich-item-list">
                                    {items.map((item, idx) => {
                                        const attrs = item.attributes || {};
                                        const displayAttrs = Object.entries(attrs)
                                            .filter(([, v]) => v && v !== '' && v !== 'unknown')
                                            .slice(0, 3);
                                        const conf = item.confidence;
                                        return (
                                            <div key={item.id || idx} className="rich-item">
                                                <div className="rich-item-header">
                                                    <span className={`tag ${config.tagClass}`}>{item.text}</span>
                                                    {typeof conf === 'number' && (
                                                        <span
                                                            className="confidence-dot"
                                                            style={{ background: getConfidenceColor(conf) }}
                                                            title={`AI Confidence: ${Math.round(conf * 100)}%`}
                                                        />
                                                    )}
                                                </div>
                                                {displayAttrs.length > 0 && (
                                                    <div className="rich-attrs">
                                                        {displayAttrs.map(([attrKey, value]) => (
                                                            <span key={attrKey} className="attr-pill">
                                                                {attrKey.replace(/_/g, ' ')}: {String(value)}
                                                            </span>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            ) : (
                                <div className="tag-container">
                                    {items.map((item, idx) => (
                                        <span key={idx} className={`tag ${config.tagClass}`}>
                                            {typeof item === 'string' ? item : item?.name || String(item)}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        );
    };
    
    if (!scene) {
        return (
            <div className="scene-detail-empty">
                <div className="empty-content">
                    <Clapperboard size={64} className="empty-icon" />
                    <h3>Select a scene</h3>
                    <p>Choose a scene from the list to view its full breakdown</p>
                </div>
            </div>
        );
    }

    // Check if scene needs analysis using analysis_status field
    const needsAnalysis = scene.analysis_status !== 'complete';

    // Render analyze prompt for pending scenes
    if (needsAnalysis && !isAnalyzing) {
        return (
            <div className="scene-detail">
                <div className="detail-header">
                    <span className="scene-number-label">Scene {scene.scene_number_original || scene.scene_number}</span>
                    <h2 className="scene-title">
                        <MapPin size={24} className="inline-icon" />
                        {scene.int_ext && <span className="int-ext-label">{scene.int_ext}.</span>}
                        {scene.setting}
                    </h2>
                </div>

                <div className="analyze-prompt">
                    <div className="prompt-icon">
                        <Clock size={48} />
                    </div>
                    <h3>Scene Not Analyzed</h3>
                    <p>This scene hasn't been analyzed yet. Click below to extract characters, props, wardrobe, and other breakdown details.</p>
                    <button 
                        className="analyze-btn"
                        onClick={() => onAnalyze(scene.scene_id)}
                    >
                        <Zap size={18} />
                        Analyze This Scene
                    </button>
                </div>
            </div>
        );
    }

    // Render analyzing state
    if (isAnalyzing) {
        return (
            <div className="scene-detail">
                <div className="detail-header">
                    <span className="scene-number-label">Scene {scene.scene_number_original || scene.scene_number}</span>
                    <h2 className="scene-title">
                        <MapPin size={24} className="inline-icon" />
                        {scene.int_ext && <span className="int-ext-label">{scene.int_ext}.</span>}
                        {scene.setting}
                    </h2>
                </div>

                <div className="analyze-prompt analyzing">
                    <div className="prompt-icon">
                        <Loader size={48} className="spin" />
                    </div>
                    <h3>Analyzing Scene...</h3>
                    <p>AI is extracting breakdown details. This usually takes 10-30 seconds.</p>
                </div>
            </div>
        );
    }

    const totalPopulated = heroCategories.length + summaryCategories.length;

    return (
        <div className="scene-detail">
            {/* Header */}
            <div className="detail-header">
                <div className="header-top-row">
                    <span className="scene-number-label">Scene {scene.scene_number_original || scene.scene_number}</span>
                    <div className="header-badges">
                        {scene.time_of_day && (
                            <span className={`time-of-day-badge ${(scene.time_of_day || '').toLowerCase().includes('night') ? 'night' : (scene.time_of_day || '').toLowerCase().includes('sunset') || (scene.time_of_day || '').toLowerCase().includes('dawn') || (scene.time_of_day || '').toLowerCase().includes('dusk') ? 'twilight' : 'day'}`}>
                                {(scene.time_of_day || '').toLowerCase().includes('night')
                                    ? <Moon size={12} />
                                    : (scene.time_of_day || '').toLowerCase().includes('sunset') || (scene.time_of_day || '').toLowerCase().includes('dawn') || (scene.time_of_day || '').toLowerCase().includes('dusk')
                                        ? <Sunset size={12} />
                                        : <Sun size={12} />}
                                {scene.time_of_day}
                            </span>
                        )}
                        <span className="page-length-badge">
                            {getSceneEighthsDisplay(scene)} pg
                        </span>
                    </div>
                </div>
                <h2 className="scene-title">
                    <MapPin size={24} className="inline-icon" />
                    {scene.int_ext && <span className="int-ext-label">{scene.int_ext}.</span>}
                    {scene.setting}
                </h2>
                {(scene.atmosphere || scene.emotional_tone) && (
                    <div className="header-meta-row">
                        {scene.atmosphere && (
                            <div className="scene-atmosphere">
                                <span className="label">Atmosphere:</span>
                                <span className="value">{scene.atmosphere}</span>
                            </div>
                        )}
                        {scene.emotional_tone && (
                            <div className="scene-atmosphere">
                                <Heart size={14} className="inline-icon" />
                                <span className="label">Tone:</span>
                                <span className="value">{scene.emotional_tone}</span>
                            </div>
                        )}
                    </div>
                )}
            </div>

            <div className="detail-content">
                {/* Description Box */}
                <div className="detail-section description-section">
                    <p className="scene-description">{scene.description}</p>
                    {scene.action_description && (
                        <div className="scene-action-description">
                            <Activity size={16} className="inline-icon" />
                            <span className="label">Action:</span>
                            <span className="value">{scene.action_description}</span>
                        </div>
                    )}
                    {scene.technical_notes && (
                        <div className="scene-technical-notes">
                            <Camera size={16} className="inline-icon" />
                            <span className="label">Technical:</span>
                            <span className="value">{scene.technical_notes}</span>
                        </div>
                    )}
                </div>

                {/* Loading skeleton */}
                {breakdownLoading && (
                    <div className="accordion-skeleton">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="skeleton-row" />
                        ))}
                    </div>
                )}

                {/* Tiered Accordion Breakdown */}
                {!breakdownLoading && totalPopulated > 0 && (
                    <div className="accordion-breakdown">
                        {/* Hero tier — expanded by default */}
                        {heroCategories.map(renderAccordionRow)}

                        {/* Summary tier — collapsed by default */}
                        {summaryCategories.map(renderAccordionRow)}

                        {/* Empty categories disclosure */}
                        {emptyCategories.length > 0 && (
                            <button
                                className="empty-disclosure-toggle"
                                onClick={() => setShowEmptyCategories(prev => !prev)}
                                aria-expanded={showEmptyCategories}
                            >
                                {showEmptyCategories ? <EyeOff size={14} /> : <Eye size={14} />}
                                {showEmptyCategories
                                    ? 'Hide empty categories'
                                    : `+${emptyCategories.length} empty categor${emptyCategories.length === 1 ? 'y' : 'ies'}`
                                }
                            </button>
                        )}

                        {/* Revealed empty categories */}
                        {showEmptyCategories && emptyCategories.map(({ key, config }) => {
                            const Icon = config.icon;
                            const noteCount = noteCounts[key] || 0;
                            return (
                                <div key={key} className="accordion-row empty-row">
                                    <div
                                        className="accordion-header empty-header"
                                        role="button"
                                        tabIndex={0}
                                        onClick={() => openDrawer(key, config.label)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' || e.key === ' ') {
                                                e.preventDefault();
                                                openDrawer(key, config.label);
                                            }
                                        }}
                                        style={{ '--accent-color': config.color }}
                                    >
                                        <Icon size={18} className="accordion-icon" style={{ color: config.color, opacity: 0.5 }} />
                                        <span className="accordion-label" style={{ opacity: 0.5 }}>{config.label}</span>
                                        <span className="accordion-count empty-count">0</span>
                                        {noteCount > 0 && (
                                            <span className="note-badge">
                                                <MessageSquare size={12} />
                                                {noteCount}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* No extraction data at all */}
                {!breakdownLoading && totalPopulated === 0 && !needsAnalysis && (
                    <div className="no-extraction-message">
                        <Info size={20} />
                        <span>No extraction data found for this scene</span>
                    </div>
                )}

                {/* Scene Intelligence — elevated enrichment panel */}
                {enrichment && Object.keys(enrichment).length > 0 && (
                    <div className="intelligence-section">
                        <div
                            className="intelligence-header"
                            role="button"
                            tabIndex={0}
                            aria-expanded={intelligenceOpen}
                            aria-controls="intelligence-panel"
                            onClick={() => setIntelligenceOpen(prev => !prev)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                    e.preventDefault();
                                    setIntelligenceOpen(prev => !prev);
                                }
                            }}
                        >
                            <Brain size={18} className="intelligence-icon" />
                            <span className="intelligence-title">Scene Intelligence</span>
                            <button
                                className="intel-deep-dive-btn"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    navigate(`/scenes/${scriptId}/intelligence`);
                                }}
                                title="Open Script Intelligence overview"
                            >
                                <Brain size={14} />
                                Deep Dive
                            </button>
                            <span className="intelligence-chevron">
                                {intelligenceOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                            </span>
                        </div>

                        {intelligenceOpen && (
                            <div id="intelligence-panel" className="intelligence-body" role="region">
                                {/* Emotions — intensity bars */}
                                {enrichment.emotion && enrichment.emotion.length > 0 && (
                                    <div className="intel-card">
                                        <div className="intel-card-header">
                                            <Heart size={16} style={{ color: '#db2777' }} />
                                            <span>Emotions ({enrichment.emotion.length})</span>
                                        </div>
                                        <div className="intel-card-body">
                                            {enrichment.emotion.map((e, idx) => {
                                                const intensity = (e.attributes?.intensity || '').toLowerCase();
                                                const barWidth = intensity === 'high' || intensity === 'intense' ? 100
                                                    : intensity === 'medium' || intensity === 'moderate' ? 60
                                                    : intensity === 'low' || intensity === 'subtle' ? 30
                                                    : 50;
                                                return (
                                                    <div key={e.id || idx} className="emotion-row">
                                                        <div className="emotion-info">
                                                            <span className="emotion-label">{e.text}</span>
                                                            {typeof e.confidence === 'number' && (
                                                                <span
                                                                    className="confidence-dot"
                                                                    style={{ background: getConfidenceColor(e.confidence) }}
                                                                    title={`AI Confidence: ${Math.round(e.confidence * 100)}%`}
                                                                />
                                                            )}
                                                        </div>
                                                        <div className="emotion-bar-track">
                                                            <div
                                                                className="emotion-bar-fill"
                                                                style={{ width: `${barWidth}%` }}
                                                            />
                                                        </div>
                                                        {intensity && (
                                                            <span className="emotion-intensity-label">{intensity}</span>
                                                        )}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}

                                {/* Dialogue — grouped by character */}
                                {enrichment.dialogue && enrichment.dialogue.length > 0 && (() => {
                                    const grouped = {};
                                    enrichment.dialogue.forEach(d => {
                                        const rawChar = d.attributes?.character || 'Unknown';
                                        const char = rawChar.trim().toUpperCase();
                                        if (!grouped[char]) grouped[char] = [];
                                        grouped[char].push(d);
                                    });
                                    const totalLines = enrichment.dialogue.length;
                                    let shownCount = 0;
                                    const maxLines = 5;

                                    return (
                                        <div className="intel-card">
                                            <div className="intel-card-header">
                                                <MessageSquare size={16} style={{ color: '#14b8a6' }} />
                                                <span>Dialogue ({totalLines})</span>
                                            </div>
                                            <div className="intel-card-body">
                                                {Object.entries(grouped).map(([character, lines]) => (
                                                    <div key={character} className="dialogue-group">
                                                        <span className="dialogue-character">{character}</span>
                                                        {lines.map((d, idx) => {
                                                            shownCount++;
                                                            if (shownCount > maxLines) return null;
                                                            return (
                                                                <div key={d.id || idx} className="dialogue-line">
                                                                    <span className="dialogue-text">"{d.text}"</span>
                                                                    {d.attributes?.tone && (
                                                                        <span className="tone-badge">{d.attributes.tone}</span>
                                                                    )}
                                                                    {typeof d.confidence === 'number' && (
                                                                        <span
                                                                            className="confidence-dot"
                                                                            style={{ background: getConfidenceColor(d.confidence) }}
                                                                            title={`AI Confidence: ${Math.round(d.confidence * 100)}%`}
                                                                        />
                                                                    )}
                                                                </div>
                                                            );
                                                        })}
                                                    </div>
                                                ))}
                                                {totalLines > maxLines && (
                                                    <p className="intel-more">+{totalLines - maxLines} more lines</p>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })()}

                                {/* Relationships — pairs with dynamic */}
                                {enrichment.relationship && enrichment.relationship.length > 0 && (
                                    <div className="intel-card">
                                        <div className="intel-card-header">
                                            <ArrowLeftRight size={16} style={{ color: '#ec4899' }} />
                                            <span>Relationships ({enrichment.relationship.length})</span>
                                        </div>
                                        <div className="intel-card-body">
                                            {enrichment.relationship.map((r, idx) => {
                                                const chars = r.attributes?.characters || r.text;
                                                const dynamic = r.attributes?.dynamic;
                                                const relType = r.attributes?.type;
                                                return (
                                                    <div key={r.id || idx} className="relationship-row">
                                                        <div className="relationship-pair">
                                                            <span className="relationship-chars">{chars}</span>
                                                            {typeof r.confidence === 'number' && (
                                                                <span
                                                                    className="confidence-dot"
                                                                    style={{ background: getConfidenceColor(r.confidence) }}
                                                                    title={`AI Confidence: ${Math.round(r.confidence * 100)}%`}
                                                                />
                                                            )}
                                                        </div>
                                                        <div className="relationship-meta">
                                                            {dynamic && <span className="relationship-dynamic">{dynamic}</span>}
                                                            {relType && <span className="attr-pill">{relType}</span>}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Note Drawer */}
            <NoteDrawer
                isOpen={drawerOpen}
                onClose={closeDrawer}
                category={activeCategory?.key}
                categoryTitle={activeCategory?.title}
                sceneId={scene.id || scene.scene_id}
                scriptId={scriptId}
                sceneNumber={scene.scene_number}
                sceneSetting={scene.setting || `${scene.int_ext || ''} ${scene.location || ''}`.trim()}
                pageStart={pageMapping?.scene_pages?.[scene.id || scene.scene_id]?.page_start || scene.page_start}
                pageEnd={pageMapping?.scene_pages?.[scene.id || scene.scene_id]?.page_end || scene.page_end}
            />
        </div>
    );
};

export default SceneDetail;
