import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
    ChevronLeft, 
    Download, 
    Printer, 
    Lock, 
    FileText,
    Loader,
    AlertCircle
} from 'lucide-react';
import { getShootingScriptData, getScriptItems } from '../../services/apiService';
import { useToast } from '../../context/ToastContext';
import './ShootingScriptPreview.css';

/**
 * ShootingScriptPreview - Preview and export shooting script
 * 
 * Shows all scenes with locked numbers, including OMITTED scenes
 */
const ShootingScriptPreview = () => {
    const { scriptId } = useParams();
    const navigate = useNavigate();
    const toast = useToast();
    
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [data, setData] = useState(null);
    const [userItemsByScene, setUserItemsByScene] = useState({});
    
    useEffect(() => {
        loadShootingScript();
    }, [scriptId]);
    
    const loadShootingScript = async () => {
        try {
            setLoading(true);
            setError(null);
            const [result, itemsData] = await Promise.all([
                getShootingScriptData(scriptId),
                getScriptItems(scriptId).catch(() => ({ items: [] }))
            ]);
            setData(result);
            // Index user items by scene_id → item_type
            const itemMap = {};
            (itemsData.items || []).forEach(item => {
                if (!item.scene_id || item.status === 'removed') return;
                if (!itemMap[item.scene_id]) itemMap[item.scene_id] = {};
                if (!itemMap[item.scene_id][item.item_type]) itemMap[item.scene_id][item.item_type] = [];
                itemMap[item.scene_id][item.item_type].push(item.item_name);
            });
            setUserItemsByScene(itemMap);
        } catch (err) {
            console.error('Error loading shooting script:', err);
            setError('Failed to load shooting script data');
            toast.error('Error', 'Failed to load shooting script');
        } finally {
            setLoading(false);
        }
    };
    
    const handlePrint = () => {
        window.print();
    };
    
    const formatSceneHeader = (scene) => {
        return `${scene.int_ext}. ${scene.setting} - ${scene.time_of_day}`;
    };
    
    // Get color for revision
    const getRevisionColor = (colorName) => {
        const colors = {
            'WHITE': '#ffffff',
            'BLUE': '#93c5fd',
            'PINK': '#f9a8d4',
            'YELLOW': '#fde047',
            'GREEN': '#86efac',
            'GOLDENROD': '#fbbf24',
            'BUFF': '#fcd34d',
            'SALMON': '#fca5a5',
            'CHERRY': '#f87171',
            'TAN': '#d4a574'
        };
        return colors[colorName] || '#ffffff';
    };
    
    if (loading) {
        return (
            <div className="shooting-script-preview">
                <div className="loading-state">
                    <Loader size={32} className="spin" />
                    <p>Loading shooting script...</p>
                </div>
            </div>
        );
    }
    
    if (error) {
        return (
            <div className="shooting-script-preview">
                <div className="error-state">
                    <AlertCircle size={32} />
                    <p>{error}</p>
                    <button onClick={() => navigate(-1)}>Go Back</button>
                </div>
            </div>
        );
    }
    
    const { script, scenes, total_scenes, omitted_scenes } = data || {};
    
    return (
        <div className="shooting-script-preview">
            {/* Header */}
            <div className="preview-header no-print">
                <div className="header-left">
                    <button className="back-btn" onClick={() => navigate(-1)}>
                        <ChevronLeft size={20} />
                        Back
                    </button>
                    <div className="header-title">
                        <h1>Shooting Script</h1>
                        <span className="script-title">{script?.title}</span>
                    </div>
                </div>
                
                <div className="header-right">
                    {script?.is_locked && (
                        <div 
                            className="revision-badge"
                            style={{ backgroundColor: getRevisionColor(script.revision_color) }}
                        >
                            <Lock size={14} />
                            {script.revision_color} REVISION
                        </div>
                    )}
                    
                    <div className="header-actions">
                        <button className="action-btn" onClick={handlePrint}>
                            <Printer size={18} />
                            Print
                        </button>
                    </div>
                </div>
            </div>
            
            {/* Stats */}
            <div className="preview-stats no-print">
                <div className="stat">
                    <span className="stat-value">{total_scenes}</span>
                    <span className="stat-label">Active Scenes</span>
                </div>
                <div className="stat">
                    <span className="stat-value">{omitted_scenes}</span>
                    <span className="stat-label">Omitted</span>
                </div>
            </div>
            
            {/* Shooting Script Content */}
            <div className="shooting-script-content">
                {/* Title Page */}
                <div className="title-page print-only">
                    <h1>{script?.title}</h1>
                    {script?.writer_name && <p className="writer">Written by {script.writer_name}</p>}
                    <div className="revision-info">
                        <span 
                            className="revision-color-block"
                            style={{ backgroundColor: getRevisionColor(script?.revision_color) }}
                        />
                        <span>{script?.revision_color || 'WHITE'} REVISION</span>
                    </div>
                </div>
                
                {/* Scene List */}
                <div className="scene-list">
                    {scenes?.map((scene, index) => (
                        <div 
                            key={scene.id}
                            className={`shooting-scene ${scene.is_omitted ? 'omitted' : ''}`}
                        >
                            <div className="scene-number-col">
                                <span className="scene-number">{scene.scene_number}</span>
                            </div>
                            
                            <div className="scene-content-col">
                                {scene.is_omitted ? (
                                    <div className="omitted-marker">OMITTED</div>
                                ) : (
                                    <>
                                        <div className="scene-header">
                                            {formatSceneHeader(scene)}
                                        </div>
                                        {(() => {
                                            const sceneId = scene.id || scene.scene_id;
                                            const userChars = (userItemsByScene[sceneId] || {}).characters || [];
                                            const allChars = [...(scene.characters || []), ...userChars];
                                            return allChars.length > 0 ? (
                                                <div className="scene-characters">
                                                    {allChars.join(', ')}
                                                </div>
                                            ) : null;
                                        })()}
                                    </>
                                )}
                            </div>
                            
                            <div className="scene-page-col">
                                {scene.page_start && !scene.is_omitted && (
                                    <span className="page-number">
                                        {scene.page_start}
                                        {scene.page_end && scene.page_end !== scene.page_start && 
                                            `-${scene.page_end}`}
                                    </span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default ShootingScriptPreview;
