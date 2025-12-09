import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
    Plus, 
    Trash2, 
    Save, 
    X, 
    Scissors, 
    Type,
    Sun,
    Moon,
    Home,
    Trees,
    ChevronLeft,
    ChevronRight,
    Check,
    AlertCircle
} from 'lucide-react';
import { getScenes, createScene, deleteSceneById } from '../../services/apiService';
import { useToast } from '../../context/ToastContext';
import { useConfirmDialog } from '../../context/ConfirmDialogContext';
import './SceneEditor.css';

/**
 * SceneEditor - Manual Scene Labeling Component (Option A)
 * 
 * Allows users to:
 * - View full script text
 * - Highlight text to mark as a scene
 * - Edit scene metadata (INT/EXT, setting, time of day)
 * - Delete scenes
 * - See existing scenes highlighted in the text
 */
const SceneEditor = ({ scriptId, fullText, onScenesUpdated }) => {
    const [scenes, setScenes] = useState([]);
    const [selection, setSelection] = useState(null);
    const [showSceneForm, setShowSceneForm] = useState(false);
    const [newSceneData, setNewSceneData] = useState({
        int_ext: 'INT',
        setting: '',
        time_of_day: 'DAY'
    });
    const [loading, setLoading] = useState(false);
    const [highlightedSceneId, setHighlightedSceneId] = useState(null);
    
    const textContainerRef = useRef(null);
    const toast = useToast();
    const { confirm } = useConfirmDialog();

    // Load existing scenes
    useEffect(() => {
        loadScenes();
    }, [scriptId]);

    const loadScenes = async () => {
        try {
            const response = await getScenes(scriptId);
            const scenesData = response.scenes || [];
            setScenes(scenesData);
            if (onScenesUpdated) onScenesUpdated(scenesData);
        } catch (error) {
            console.error('Error loading scenes:', error);
            toast.error('Error', 'Failed to load scenes');
        }
    };

    // Handle text selection
    const handleTextSelection = useCallback(() => {
        const sel = window.getSelection();
        if (!sel || sel.isCollapsed) {
            return;
        }

        const selectedText = sel.toString().trim();
        if (selectedText.length < 10) {
            return; // Minimum selection length
        }

        // Get selection range relative to the full text
        const container = textContainerRef.current;
        if (!container) return;

        const range = sel.getRangeAt(0);
        
        // Calculate start position in full text
        const preRange = document.createRange();
        preRange.selectNodeContents(container);
        preRange.setEnd(range.startContainer, range.startOffset);
        const start = preRange.toString().length;
        const end = start + selectedText.length;

        setSelection({
            text: selectedText,
            start,
            end
        });
        setShowSceneForm(true);
        
        // Pre-fill setting from first line if it looks like a scene header
        const firstLine = selectedText.split('\n')[0].trim();
        if (firstLine.length < 100) {
            setNewSceneData(prev => ({
                ...prev,
                setting: firstLine
            }));
        }
    }, []);

    // Create scene from selection
    const handleCreateScene = async () => {
        if (!selection) return;

        setLoading(true);
        try {
            await createScene({
                script_id: scriptId,
                ...newSceneData,
                scene_text: selection.text,
                text_start: selection.start,
                text_end: selection.end
            });

            toast.success('Scene Created', `Scene "${newSceneData.setting}" has been added.`);
            
            // Reset form
            setSelection(null);
            setShowSceneForm(false);
            setNewSceneData({
                int_ext: 'INT',
                setting: '',
                time_of_day: 'DAY'
            });
            
            // Reload scenes
            await loadScenes();
            
            // Clear text selection
            window.getSelection()?.removeAllRanges();
            
        } catch (err) {
            toast.error('Error', err.message || 'Failed to create scene');
        } finally {
            setLoading(false);
        }
    };

    // Delete a scene
    const handleDeleteScene = async (sceneId) => {
        const confirmed = await confirm({
            title: 'Delete Scene',
            message: 'Are you sure you want to delete this scene?',
            variant: 'danger',
            confirmText: 'Delete'
        });
        
        if (!confirmed) return;

        try {
            await deleteSceneById(sceneId);
            toast.success('Scene Deleted', 'The scene has been removed.');
            await loadScenes();
        } catch (err) {
            toast.error('Error', err.message || 'Failed to delete scene');
        }
    };

    // Render text with scene highlights
    const renderHighlightedText = () => {
        if (!fullText) return null;

        // Sort scenes by start position
        const sortedScenes = [...scenes]
            .filter(s => s.text_start !== null && s.text_end !== null)
            .sort((a, b) => a.text_start - b.text_start);

        if (sortedScenes.length === 0) {
            return <pre className="script-text">{fullText}</pre>;
        }

        const segments = [];
        let lastEnd = 0;

        sortedScenes.forEach((scene, index) => {
            // Add unhighlighted text before this scene
            if (scene.text_start > lastEnd) {
                segments.push(
                    <span key={`text-${index}`} className="unhighlighted-text">
                        {fullText.slice(lastEnd, scene.text_start)}
                    </span>
                );
            }

            // Add highlighted scene text
            const isHighlighted = highlightedSceneId === scene.id;
            segments.push(
                <span 
                    key={`scene-${scene.id}`}
                    className={`scene-highlight ${isHighlighted ? 'active' : ''}`}
                    data-scene-id={scene.id}
                    onClick={() => setHighlightedSceneId(scene.id)}
                    title={`Scene ${scene.scene_number}: ${scene.setting}`}
                >
                    <span className="scene-marker">
                        Scene {scene.scene_number}
                    </span>
                    {fullText.slice(scene.text_start, scene.text_end)}
                </span>
            );

            lastEnd = scene.text_end;
        });

        // Add remaining text after last scene
        if (lastEnd < fullText.length) {
            segments.push(
                <span key="text-end" className="unhighlighted-text">
                    {fullText.slice(lastEnd)}
                </span>
            );
        }

        return <pre className="script-text">{segments}</pre>;
    };

    // Cancel scene creation
    const handleCancel = () => {
        setSelection(null);
        setShowSceneForm(false);
        setNewSceneData({
            int_ext: 'INT',
            setting: '',
            time_of_day: 'DAY'
        });
        window.getSelection()?.removeAllRanges();
    };

    return (
        <div className="scene-editor">
            {/* Instructions */}
            <div className="editor-instructions">
                <AlertCircle size={18} />
                <p>
                    <strong>Manual Scene Labeling:</strong> Select text in the script below to mark it as a scene. 
                    Existing scenes are highlighted in color.
                </p>
            </div>

            {/* Scene Form Modal */}
            {showSceneForm && selection && (
                <div className="scene-form-overlay">
                    <div className="scene-form-modal">
                        <div className="modal-header">
                            <h3>Create New Scene</h3>
                            <button className="close-btn" onClick={handleCancel}>
                                <X size={20} />
                            </button>
                        </div>

                        <div className="modal-body">
                            {/* Selected text preview */}
                            <div className="selection-preview">
                                <label>Selected Text:</label>
                                <div className="preview-text">
                                    {selection.text.slice(0, 200)}
                                    {selection.text.length > 200 && '...'}
                                </div>
                                <span className="char-count">
                                    {selection.text.length} characters selected
                                </span>
                            </div>

                            {/* INT/EXT selector */}
                            <div className="form-group">
                                <label>Interior/Exterior</label>
                                <div className="toggle-group">
                                    <button
                                        className={`toggle-btn ${newSceneData.int_ext === 'INT' ? 'active' : ''}`}
                                        onClick={() => setNewSceneData(prev => ({ ...prev, int_ext: 'INT' }))}
                                    >
                                        <Home size={16} />
                                        INT
                                    </button>
                                    <button
                                        className={`toggle-btn ${newSceneData.int_ext === 'EXT' ? 'active' : ''}`}
                                        onClick={() => setNewSceneData(prev => ({ ...prev, int_ext: 'EXT' }))}
                                    >
                                        <Trees size={16} />
                                        EXT
                                    </button>
                                    <button
                                        className={`toggle-btn ${newSceneData.int_ext === 'INT/EXT' ? 'active' : ''}`}
                                        onClick={() => setNewSceneData(prev => ({ ...prev, int_ext: 'INT/EXT' }))}
                                    >
                                        INT/EXT
                                    </button>
                                </div>
                            </div>

                            {/* Setting/Location */}
                            <div className="form-group">
                                <label>Setting / Location</label>
                                <input
                                    type="text"
                                    value={newSceneData.setting}
                                    onChange={(e) => setNewSceneData(prev => ({ ...prev, setting: e.target.value }))}
                                    placeholder="e.g., COFFEE SHOP, JOHN'S APARTMENT"
                                />
                            </div>

                            {/* Time of Day */}
                            <div className="form-group">
                                <label>Time of Day</label>
                                <div className="toggle-group">
                                    <button
                                        className={`toggle-btn ${newSceneData.time_of_day === 'DAY' ? 'active' : ''}`}
                                        onClick={() => setNewSceneData(prev => ({ ...prev, time_of_day: 'DAY' }))}
                                    >
                                        <Sun size={16} />
                                        DAY
                                    </button>
                                    <button
                                        className={`toggle-btn ${newSceneData.time_of_day === 'NIGHT' ? 'active' : ''}`}
                                        onClick={() => setNewSceneData(prev => ({ ...prev, time_of_day: 'NIGHT' }))}
                                    >
                                        <Moon size={16} />
                                        NIGHT
                                    </button>
                                    <button
                                        className={`toggle-btn ${newSceneData.time_of_day === 'DAWN' ? 'active' : ''}`}
                                        onClick={() => setNewSceneData(prev => ({ ...prev, time_of_day: 'DAWN' }))}
                                    >
                                        DAWN
                                    </button>
                                    <button
                                        className={`toggle-btn ${newSceneData.time_of_day === 'DUSK' ? 'active' : ''}`}
                                        onClick={() => setNewSceneData(prev => ({ ...prev, time_of_day: 'DUSK' }))}
                                    >
                                        DUSK
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div className="modal-footer">
                            <button className="btn-secondary" onClick={handleCancel}>
                                Cancel
                            </button>
                            <button 
                                className="btn-primary" 
                                onClick={handleCreateScene}
                                disabled={loading || !newSceneData.setting}
                            >
                                {loading ? 'Creating...' : 'Create Scene'}
                                <Check size={16} />
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Main Content */}
            <div className="editor-layout">
                {/* Script Text Panel */}
                <div 
                    className="script-panel"
                    ref={textContainerRef}
                    onMouseUp={handleTextSelection}
                >
                    {renderHighlightedText()}
                </div>

                {/* Scenes Sidebar */}
                <div className="scenes-sidebar">
                    <div className="sidebar-header">
                        <h3>Scenes ({scenes.length})</h3>
                    </div>
                    
                    {scenes.length === 0 ? (
                        <div className="no-scenes">
                            <Scissors size={32} />
                            <p>No scenes yet</p>
                            <span>Select text in the script to create scenes</span>
                        </div>
                    ) : (
                        <div className="scenes-list">
                            {scenes.map((scene) => (
                                <div 
                                    key={scene.id}
                                    className={`scene-card ${highlightedSceneId === scene.id ? 'active' : ''}`}
                                    onClick={() => setHighlightedSceneId(scene.id)}
                                >
                                    <div className="scene-card-header">
                                        <span className="scene-number">Scene {scene.scene_number}</span>
                                        <span className={`int-ext-badge ${scene.int_ext?.toLowerCase()}`}>
                                            {scene.int_ext}
                                        </span>
                                    </div>
                                    <div className="scene-card-body">
                                        <p className="scene-setting">{scene.setting}</p>
                                        <span className="scene-time">{scene.time_of_day}</span>
                                    </div>
                                    <div className="scene-card-actions">
                                        <button 
                                            className="delete-btn"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleDeleteScene(scene.id);
                                            }}
                                            title="Delete scene"
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SceneEditor;
