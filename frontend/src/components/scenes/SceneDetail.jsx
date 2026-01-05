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
    Volume2
} from 'lucide-react';
import NoteDrawer from '../notes/NoteDrawer';
import { getScriptNotes } from '../../services/apiService';
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
    sound: ['sound', 'director', 'post_production']
};

/**
 * SceneDetail - Shows scene breakdown with clickable cards for notes
 */
const SceneDetail = ({ scene, scriptId, onAnalyze, isAnalyzing = false, pageMapping = null }) => {
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [activeCategory, setActiveCategory] = useState(null);
    const [noteCounts, setNoteCounts] = useState({});

    // Fetch note counts for badges
    useEffect(() => {
        const fetchNoteCounts = async () => {
            if (!scene || !scriptId) return;
            
            try {
                const sceneId = scene.id || scene.scene_id;
                const response = await getScriptNotes(scriptId, { scene_id: sceneId });
                const notes = response.notes || [];
                
                // Count notes per category using note_type field
                const counts = {};
                Object.keys(CATEGORY_DEPARTMENTS).forEach(category => {
                    // Filter by note_type (category) - this is the correct way
                    counts[category] = notes.filter(n => n.note_type === category).length;
                });
                
                setNoteCounts(counts);
            } catch (err) {
                console.error('Error fetching note counts:', err);
            }
        };
        
        fetchNoteCounts();
    }, [scene, scriptId]);

    const openDrawer = (category, title) => {
        setActiveCategory({ key: category, title });
        setDrawerOpen(true);
    };

    const closeDrawer = () => {
        setDrawerOpen(false);
        setActiveCategory(null);
        // Refresh note counts after closing
        if (scene && scriptId) {
            const sceneId = scene.id || scene.scene_id;
            getScriptNotes(scriptId, { scene_id: sceneId }).then(response => {
                const notes = response.notes || [];
                const counts = {};
                Object.keys(CATEGORY_DEPARTMENTS).forEach(category => {
                    // Filter by note_type (category)
                    counts[category] = notes.filter(n => n.note_type === category).length;
                });
                setNoteCounts(counts);
            }).catch(console.error);
        }
    };
    // Calculate scene length in eighths
    const eighthsDisplay = scene ? getSceneEighthsDisplay(scene) : null;
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
                    {eighthsDisplay && <span className="scene-eighths-badge" title="Scene length in eighths of a page">{eighthsDisplay}</span>}
                </div>
                <h2 className="scene-title">
                    <MapPin size={24} className="inline-icon" />
                    {scene.int_ext && <span className="int-ext-label">{scene.int_ext}.</span>}
                    {scene.setting}
                </h2>
                {scene.atmosphere && (
                    <div className="scene-atmosphere">
                        <span className="label">Atmosphere:</span>
                        <span className="value">{scene.atmosphere}</span>
                    </div>
                )}
            </div>

            <div className="detail-content">
                {/* Description Box */}
                <div className="detail-section description-section">
                    <p className="scene-description">{scene.description}</p>
                </div>

                {/* Breakdown Grid - Clickable Cards */}
                <div className="breakdown-grid">
                    {/* Characters */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('characters', 'Characters')}
                        title="Click to add notes"
                    >
                        <div className="card-header">
                            <Users size={20} className="card-icon" />
                            <h3>Characters</h3>
                            {noteCounts.characters > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.characters}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {scene.characters && scene.characters.length > 0 ? (
                                <div className="tag-container">
                                    {scene.characters.map((char, idx) => (
                                        <span key={idx} className="tag character-tag">{char}</span>
                                    ))}
                                </div>
                            ) : (
                                <p className="empty-text">No characters detected</p>
                            )}
                        </div>
                    </div>

                    {/* Props */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('props', 'Props')}
                        title="Click to add notes"
                    >
                        <div className="card-header">
                            <Package size={20} className="card-icon" />
                            <h3>Props</h3>
                            {noteCounts.props > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.props}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {scene.props && scene.props.length > 0 ? (
                                <div className="tag-container">
                                    {scene.props.map((prop, idx) => (
                                        <span key={idx} className="tag prop-tag">{prop}</span>
                                    ))}
                                </div>
                            ) : (
                                <p className="empty-text">No props detected</p>
                            )}
                        </div>
                    </div>

                    {/* Wardrobe */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('wardrobe', 'Wardrobe')}
                        title="Click to add notes"
                    >
                        <div className="card-header">
                            <Shirt size={20} className="card-icon" />
                            <h3>Wardrobe</h3>
                            {noteCounts.wardrobe > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.wardrobe}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {scene.wardrobe && scene.wardrobe.length > 0 ? (
                                <ul className="detail-list">
                                    {scene.wardrobe.map((item, idx) => (
                                        <li key={idx}>{item}</li>
                                    ))}
                                </ul>
                            ) : (
                                <p className="empty-text">No wardrobe notes</p>
                            )}
                        </div>
                    </div>

                    {/* Makeup & Hair */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('makeup_hair', 'Makeup & Hair')}
                        title="Click to add notes"
                    >
                        <div className="card-header">
                            <Palette size={20} className="card-icon" />
                            <h3>Makeup & Hair</h3>
                            {noteCounts.makeup_hair > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.makeup_hair}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {scene.makeup_hair && scene.makeup_hair.length > 0 ? (
                                <ul className="detail-list">
                                    {scene.makeup_hair.map((item, idx) => (
                                        <li key={idx}>{item}</li>
                                    ))}
                                </ul>
                            ) : (
                                <p className="empty-text">No makeup/hair notes</p>
                            )}
                        </div>
                    </div>

                    {/* Special FX */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('special_fx', 'Special FX')}
                        title="Click to add notes"
                    >
                        <div className="card-header">
                            <Sparkles size={20} className="card-icon" />
                            <h3>Special FX</h3>
                            {noteCounts.special_fx > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.special_fx}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {scene.special_fx && scene.special_fx.length > 0 ? (
                                <div className="tag-container">
                                    {scene.special_fx.map((fx, idx) => (
                                        <span key={idx} className="tag fx-tag">{fx}</span>
                                    ))}
                                </div>
                            ) : (
                                <p className="empty-text">No special FX detected</p>
                            )}
                        </div>
                    </div>

                    {/* Vehicles */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('vehicles', 'Vehicles')}
                        title="Click to add notes"
                    >
                        <div className="card-header">
                            <Car size={20} className="card-icon" />
                            <h3>Vehicles</h3>
                            {noteCounts.vehicles > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.vehicles}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {scene.vehicles && scene.vehicles.length > 0 ? (
                                <div className="tag-container">
                                    {scene.vehicles.map((v, idx) => (
                                        <span key={idx} className="tag vehicle-tag">{v}</span>
                                    ))}
                                </div>
                            ) : (
                                <p className="empty-text">No vehicles detected</p>
                            )}
                        </div>
                    </div>

                    {/* Locations */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('locations', 'Locations')}
                        title="Click to add notes"
                    >
                        <div className="card-header">
                            <Building2 size={20} className="card-icon" />
                            <h3>Locations</h3>
                            {noteCounts.locations > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.locations}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {scene.locations && scene.locations.length > 0 ? (
                                <div className="tag-container">
                                    {scene.locations.map((loc, idx) => (
                                        <span key={idx} className="tag location-tag">{loc}</span>
                                    ))}
                                </div>
                            ) : (
                                <p className="empty-text">No sub-locations detected</p>
                            )}
                        </div>
                    </div>

                    {/* Sound */}
                    <div 
                        className="breakdown-card clickable"
                        onClick={() => openDrawer('sound', 'Sound')}
                        title="Click to add notes"
                    >
                        <div className="card-header">
                            <Volume2 size={20} className="card-icon" />
                            <h3>Sound</h3>
                            {noteCounts.sound > 0 && (
                                <span className="note-badge">
                                    <MessageSquare size={12} />
                                    {noteCounts.sound}
                                </span>
                            )}
                        </div>
                        <div className="card-content">
                            {scene.sound && scene.sound.length > 0 ? (
                                <div className="tag-container">
                                    {scene.sound.map((s, idx) => (
                                        <span key={idx} className="tag sound-tag">{s}</span>
                                    ))}
                                </div>
                            ) : (
                                <p className="empty-text">No sound cues detected</p>
                            )}
                        </div>
                    </div>
                </div>
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
