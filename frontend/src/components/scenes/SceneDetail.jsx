import React, { useState, useEffect } from 'react';
import { 
    Users, 
    Package, 
    Sparkles, 
    Shirt, 
    Palette, 
    Car, 
    Clapperboard,
    MapPin,
    Zap,
    Loader,
    Clock,
    MessageSquare,
    Building2,
    Volume2,
    Dog,
    UserPlus,
    Flame,
    Activity,
    Heart,
    Camera,
    Mic2,
    Video,
    ChevronRight,
    ShieldCheck,
    ShieldAlert
} from 'lucide-react';
import BreakdownDrawer from '../breakdown/BreakdownDrawer';
import { getScriptNotes, getSceneItems } from '../../services/apiService';
import { getSceneEighthsDisplay } from '../../utils/sceneUtils';
import './SceneDetail.css';

// Category to department mapping for counting notes
const CATEGORY_DEPARTMENTS = {
    characters: ['director', 'casting', 'actor'],
    props: ['production_design', 'director'],
    wardrobe: ['costume', 'director'],
    makeup_hair: ['makeup_hair', 'director'],
    special_fx: ['vfx', 'director'],
    vehicles: ['locations', 'director', 'production_design'],
    locations: ['locations', 'production_design', 'director'],
    sound: ['sound', 'director', 'post_production'],
    animals: ['production_design', 'director'],
    extras: ['casting', 'director'],
    stunts: ['stunts', 'director', 'safety']
};

/**
 * SceneDetail - Shows scene breakdown with clickable cards for notes
 */
// Map category key to scene JSONB field name
const CATEGORY_FIELD_MAP = {
    characters: 'characters',
    props: 'props',
    wardrobe: 'wardrobe',
    makeup_hair: 'makeup_hair',
    special_fx: 'special_fx',
    vehicles: 'vehicles',
    locations: 'locations',
    sound: 'sound',
    animals: 'animals',
    extras: 'extras',
    stunts: 'stunts',
};

const SceneDetail = ({ scene, scriptId, onAnalyze, isAnalyzing = false, pageMapping = null, onRefreshScene = null }) => {
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [activeCategory, setActiveCategory] = useState(null);
    const [noteCounts, setNoteCounts] = useState({});
    const [itemCounts, setItemCounts] = useState({});
    const [userItems, setUserItems] = useState([]);  // Full items for card tag merging

    // Fetch notes, items (for badges + card tags)
    const refreshData = async () => {
        if (!scene || !scriptId) return;
        try {
            const sceneId = scene.id || scene.scene_id;
            const [notesRes, itemsRes] = await Promise.all([
                getScriptNotes(scriptId, { scene_id: sceneId }),
                getSceneItems(scriptId, sceneId)  // excludes removed by default
            ]);
            const notes = notesRes.notes || [];
            const items = itemsRes.items || [];
            
            const nCounts = {};
            const iCounts = {};
            Object.keys(CATEGORY_DEPARTMENTS).forEach(category => {
                nCounts[category] = notes.filter(n => n.note_type === category).length;
                iCounts[category] = items.filter(i => i.item_type === category).length;
            });
            
            setNoteCounts(nCounts);
            setItemCounts(iCounts);
            setUserItems(items);
        } catch (err) {
            console.error('Error fetching data:', err);
        }
    };

    useEffect(() => {
        refreshData();
    }, [scene, scriptId]);

    // Get active (non-removed) user items for a given category
    const getUserItemsForCategory = (categoryKey) => {
        return userItems.filter(i => i.item_type === categoryKey && i.status !== 'removed');
    };

    const openDrawer = (category, title) => {
        setActiveCategory({ key: category, title });
        setDrawerOpen(true);
    };

    const closeDrawer = () => {
        setDrawerOpen(false);
        setActiveCategory(null);
        // Refresh data after closing (items may have been added/removed)
        refreshData();
        if (onRefreshScene) onRefreshScene();
    };

    // Get AI items array for the active category from scene JSONB
    const getAiItems = (categoryKey) => {
        if (!scene || !categoryKey) return [];
        const field = CATEGORY_FIELD_MAP[categoryKey];
        return (field && scene[field]) || [];
    };

    // Render merged tags: AI items + user-added items for a card
    const renderMergedTags = (categoryKey, tagClass, emptyText) => {
        const aiItems = getAiItems(categoryKey);
        const addedItems = getUserItemsForCategory(categoryKey);
        const hasAny = aiItems.length > 0 || addedItems.length > 0;

        if (!hasAny) return <p className="empty-text">{emptyText}</p>;

        return (
            <div className="tag-container">
                {aiItems.map((item, idx) => (
                    <span key={`ai-${idx}`} className={`tag ${tagClass}`}>
                        {typeof item === 'string' ? item : item.name || JSON.stringify(item)}
                    </span>
                ))}
                {addedItems.map((item) => (
                    <span key={`user-${item.id}`} className={`tag ${tagClass} user-added-tag`}>
                        {item.item_name}
                    </span>
                ))}
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
                {/* Header */}
                <div className="detail-header">
                    <span className="scene-number-label">Scene {scene.scene_number_original || scene.scene_number}</span>
                    <h2 className="scene-title">
                        <MapPin size={24} className="inline-icon" />
                        {scene.int_ext && <span className="int-ext-label">{scene.int_ext}.</span>}
                        {scene.setting}
                    </h2>
                </div>

                {/* Analyze Prompt */}
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
                {/* Header */}
                <div className="detail-header">
                    <span className="scene-number-label">Scene {scene.scene_number_original || scene.scene_number}</span>
                    <h2 className="scene-title">
                        <MapPin size={24} className="inline-icon" />
                        {scene.int_ext && <span className="int-ext-label">{scene.int_ext}.</span>}
                        {scene.setting}
                    </h2>
                </div>

                {/* Analyzing State */}
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

    return (
        <div className="scene-detail">
            {/* Header */}
            <div className="detail-header">
                <div className="scene-header-row">
                    <span className="scene-number-label">Scene {scene.scene_number_original || scene.scene_number}</span>
                    {scene.shot_type && (
                        <span className="shot-type-badge">
                            <Video size={12} />
                            {scene.shot_type}
                        </span>
                    )}
                    {scene.parse_method && (
                        <span className={`parse-method-badge ${scene.parse_method === 'grammar' ? 'grammar' : 'regex'}`} title={`Parsed via ${scene.parse_method}`}>
                            {scene.parse_method === 'grammar' ? <ShieldCheck size={12} /> : <ShieldAlert size={12} />}
                            {scene.parse_method === 'grammar' ? 'ScreenPy' : 'Regex'}
                        </span>
                    )}
                </div>
                <h2 className="scene-title">
                    <MapPin size={24} className="inline-icon" />
                    {scene.int_ext && <span className="int-ext-label">{scene.int_ext}.</span>}
                    {scene.setting}
                </h2>
                {/* Location Hierarchy Breadcrumb */}
                {scene.location_hierarchy && scene.location_hierarchy.length > 1 && (
                    <div className="location-breadcrumb">
                        <Building2 size={14} className="breadcrumb-icon" />
                        {scene.location_hierarchy.map((loc, idx) => (
                            <span key={idx} className="breadcrumb-segment">
                                {idx > 0 && <ChevronRight size={12} className="breadcrumb-separator" />}
                                <span className={idx === scene.location_hierarchy.length - 1 ? 'breadcrumb-current' : 'breadcrumb-parent'}>{loc}</span>
                            </span>
                        ))}
                    </div>
                )}
                {scene.atmosphere && (
                    <div className="scene-atmosphere">
                        <span className="label">Atmosphere:</span>
                        <span className="value">{scene.atmosphere}</span>
                    </div>
                )}
                {scene.emotional_tone && (
                    <div className="scene-atmosphere">
                        <Heart size={16} className="inline-icon" />
                        <span className="label">Tone:</span>
                        <span className="value">{scene.emotional_tone}</span>
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

                {/* Breakdown Grid - Clickable Cards */}
                <div className="breakdown-grid">
                    {/* Characters */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('characters', 'Characters')}
                        title="Click to manage items & notes"
                    >
                        <div className="card-header">
                            <Users size={20} className="card-icon" />
                            <h3>Characters</h3>
                            {itemCounts.characters > 0 && (
                                <span className="item-badge">
                                    <Zap size={10} />
                                    {itemCounts.characters}
                                </span>
                            )}
                            {noteCounts.characters > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.characters}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {renderMergedTags('characters', 'character-tag', 'No characters detected')}
                        </div>
                    </div>

                    {/* Speakers (from ScreenPy grammar parsing) */}
                    {scene.speakers && scene.speakers.length > 0 && (
                        <div className="breakdown-card speakers-card">
                            <div className="card-header">
                                <Mic2 size={20} className="card-icon speakers-icon" />
                                <h3>Speakers</h3>
                                <span className="source-badge grammar-source">Dialogue</span>
                            </div>
                            <div className="card-content">
                                <div className="tag-container">
                                    {scene.speakers.map((speaker, idx) => (
                                        <span key={idx} className="tag speaker-tag">{speaker}</span>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Props */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('props', 'Props')}
                        title="Click to manage items & notes"
                    >
                        <div className="card-header">
                            <Package size={20} className="card-icon" />
                            <h3>Props</h3>
                            {itemCounts.props > 0 && (
                                <span className="item-badge">
                                    <Zap size={10} />
                                    {itemCounts.props}
                                </span>
                            )}
                            {noteCounts.props > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.props}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {renderMergedTags('props', 'prop-tag', 'No props detected')}
                        </div>
                    </div>

                    {/* Wardrobe */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('wardrobe', 'Wardrobe')}
                        title="Click to manage items & notes"
                    >
                        <div className="card-header">
                            <Shirt size={20} className="card-icon" />
                            <h3>Wardrobe</h3>
                            {itemCounts.wardrobe > 0 && (
                                <span className="item-badge">
                                    <Zap size={10} />
                                    {itemCounts.wardrobe}
                                </span>
                            )}
                            {noteCounts.wardrobe > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.wardrobe}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {renderMergedTags('wardrobe', 'wardrobe-tag', 'No wardrobe notes')}
                        </div>
                    </div>

                    {/* Makeup & Hair */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('makeup_hair', 'Makeup & Hair')}
                        title="Click to manage items & notes"
                    >
                        <div className="card-header">
                            <Palette size={20} className="card-icon" />
                            <h3>Makeup & Hair</h3>
                            {itemCounts.makeup_hair > 0 && (
                                <span className="item-badge">
                                    <Zap size={10} />
                                    {itemCounts.makeup_hair}
                                </span>
                            )}
                            {noteCounts.makeup_hair > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.makeup_hair}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {renderMergedTags('makeup_hair', 'makeup-tag', 'No makeup/hair notes')}
                        </div>
                    </div>

                    {/* Special FX */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('special_fx', 'Special FX')}
                        title="Click to manage items & notes"
                    >
                        <div className="card-header">
                            <Sparkles size={20} className="card-icon" />
                            <h3>Special FX</h3>
                            {itemCounts.special_fx > 0 && (
                                <span className="item-badge">
                                    <Zap size={10} />
                                    {itemCounts.special_fx}
                                </span>
                            )}
                            {noteCounts.special_fx > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.special_fx}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {renderMergedTags('special_fx', 'fx-tag', 'No special FX detected')}
                        </div>
                    </div>

                    {/* Vehicles */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('vehicles', 'Vehicles')}
                        title="Click to manage items & notes"
                    >
                        <div className="card-header">
                            <Car size={20} className="card-icon" />
                            <h3>Vehicles</h3>
                            {itemCounts.vehicles > 0 && (
                                <span className="item-badge">
                                    <Zap size={10} />
                                    {itemCounts.vehicles}
                                </span>
                            )}
                            {noteCounts.vehicles > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.vehicles}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {renderMergedTags('vehicles', 'vehicle-tag', 'No vehicles detected')}
                        </div>
                    </div>

                    {/* Locations */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('locations', 'Locations')}
                        title="Click to manage items & notes"
                    >
                        <div className="card-header">
                            <Building2 size={20} className="card-icon" />
                            <h3>Locations</h3>
                            {itemCounts.locations > 0 && (
                                <span className="item-badge">
                                    <Zap size={10} />
                                    {itemCounts.locations}
                                </span>
                            )}
                            {noteCounts.locations > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.locations}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {renderMergedTags('locations', 'location-tag', 'No sub-locations detected')}
                        </div>
                    </div>

                    {/* Sound */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('sound', 'Sound')}
                        title="Click to manage items & notes"
                    >
                        <div className="card-header">
                            <Volume2 size={20} className="card-icon" />
                            <h3>Sound</h3>
                            {itemCounts.sound > 0 && (
                                <span className="item-badge">
                                    <Zap size={10} />
                                    {itemCounts.sound}
                                </span>
                            )}
                            {noteCounts.sound > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.sound}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {renderMergedTags('sound', 'sound-tag', 'No sound cues detected')}
                        </div>
                    </div>

                    {/* Animals */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('animals', 'Animals')}
                        title="Click to manage items & notes"
                    >
                        <div className="card-header">
                            <Dog size={20} className="card-icon" />
                            <h3>Animals</h3>
                            {itemCounts.animals > 0 && (
                                <span className="item-badge">
                                    <Zap size={10} />
                                    {itemCounts.animals}
                                </span>
                            )}
                            {noteCounts.animals > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.animals}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {renderMergedTags('animals', 'animal-tag', 'No animals detected')}
                        </div>
                    </div>

                    {/* Extras */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('extras', 'Extras')}
                        title="Click to manage items & notes"
                    >
                        <div className="card-header">
                            <UserPlus size={20} className="card-icon" />
                            <h3>Extras</h3>
                            {itemCounts.extras > 0 && (
                                <span className="item-badge">
                                    <Zap size={10} />
                                    {itemCounts.extras}
                                </span>
                            )}
                            {noteCounts.extras > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.extras}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {renderMergedTags('extras', 'extra-tag', 'No extras detected')}
                        </div>
                    </div>

                    {/* Stunts */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('stunts', 'Stunts')}
                        title="Click to manage items & notes"
                    >
                        <div className="card-header">
                            <Flame size={20} className="card-icon" />
                            <h3>Stunts</h3>
                            {itemCounts.stunts > 0 && (
                                <span className="item-badge">
                                    <Zap size={10} />
                                    {itemCounts.stunts}
                                </span>
                            )}
                            {noteCounts.stunts > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.stunts}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {renderMergedTags('stunts', 'stunt-tag', 'No stunts detected')}
                        </div>
                    </div>
                </div>
            </div>

            {/* Breakdown Drawer (Items CRUD + Notes) */}
            <BreakdownDrawer
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
                aiItems={getAiItems(activeCategory?.key)}
                onAiItemRemoved={onRefreshScene}
                sceneText={scene.scene_text || ''}
            />
        </div>
    );
};

export default SceneDetail;
