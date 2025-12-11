import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
    GripVertical, 
    Scissors, 
    RotateCcw, 
    Edit3, 
    ChevronLeft,
    Lock,
    Unlock,
    AlertCircle,
    CheckCircle,
    Clock,
    Loader,
    Save,
    X,
    MoreVertical,
    History,
    FileText,
    Plus,
    Merge,
    Upload
} from 'lucide-react';
import { 
    getScenesForManagement, 
    reorderScenes, 
    omitScene, 
    updateSceneHeader 
} from '../../services/apiService';
import { useToast } from '../../context/ToastContext';
import SceneSplitModal from './SceneSplitModal';
import SceneMergeModal from './SceneMergeModal';
import AddSceneModal from './AddSceneModal';
import MultiMergeModal from './MultiMergeModal';
import RevisionImportWizard from '../revisions/RevisionImportWizard';
import './SceneManager.css';

/**
 * SceneManager - Scene Management Component (Phase 1)
 * 
 * Features:
 * - Drag-and-drop scene reordering
 * - Omit/restore scenes
 * - Edit scene headers (INT/EXT, setting, time of day)
 * - View script lock status
 */
const SceneManager = () => {
    const { scriptId } = useParams();
    const navigate = useNavigate();
    const toast = useToast();
    
    // State
    const [script, setScript] = useState(null);
    const [scenes, setScenes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    
    // Drag state
    const [draggedIndex, setDraggedIndex] = useState(null);
    const [dragOverIndex, setDragOverIndex] = useState(null);
    
    // Edit state
    const [editingScene, setEditingScene] = useState(null);
    const [editForm, setEditForm] = useState({ int_ext: '', setting: '', time_of_day: '' });
    
    // Modal state (Phase 2)
    const [splitModalOpen, setSplitModalOpen] = useState(false);
    const [mergeModalOpen, setMergeModalOpen] = useState(false);
    const [addModalOpen, setAddModalOpen] = useState(false);
    const [multiMergeModalOpen, setMultiMergeModalOpen] = useState(false);
    const [selectedScene, setSelectedScene] = useState(null);
    const [mergeTargetScene, setMergeTargetScene] = useState(null);
    const [insertAfterScene, setInsertAfterScene] = useState(null);
    const [showInstructions, setShowInstructions] = useState(true);
    
    // Multi-select state
    const [selectedSceneIds, setSelectedSceneIds] = useState(new Set());
    
    // Revision import state (Phase 3)
    const [revisionImportOpen, setRevisionImportOpen] = useState(false);
    
    // Load data
    useEffect(() => {
        loadScenes();
    }, [scriptId]);
    
    const loadScenes = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await getScenesForManagement(scriptId);
            setScript(data.script);
            setScenes(data.scenes || []);
        } catch (err) {
            console.error('Error loading scenes:', err);
            setError('Failed to load scenes');
            toast.error('Error', 'Failed to load scenes for management');
        } finally {
            setLoading(false);
        }
    };
    
    // ============================================
    // Drag and Drop Handlers
    // ============================================
    
    const handleDragStart = (e, index) => {
        if (script?.is_locked) return;
        setDraggedIndex(index);
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', index);
        // Add dragging class after a small delay for visual feedback
        setTimeout(() => {
            e.target.classList.add('dragging');
        }, 0);
    };
    
    const handleDragEnd = (e) => {
        e.target.classList.remove('dragging');
        setDraggedIndex(null);
        setDragOverIndex(null);
    };
    
    const handleDragOver = (e, index) => {
        e.preventDefault();
        if (draggedIndex === null || draggedIndex === index) return;
        setDragOverIndex(index);
    };
    
    const handleDragLeave = () => {
        setDragOverIndex(null);
    };
    
    const handleDrop = async (e, dropIndex) => {
        e.preventDefault();
        
        if (draggedIndex === null || draggedIndex === dropIndex) {
            setDraggedIndex(null);
            setDragOverIndex(null);
            return;
        }
        
        // Reorder locally first for instant feedback
        const newScenes = [...scenes];
        const [draggedScene] = newScenes.splice(draggedIndex, 1);
        newScenes.splice(dropIndex, 0, draggedScene);
        setScenes(newScenes);
        
        setDraggedIndex(null);
        setDragOverIndex(null);
        
        // Save to backend
        try {
            setSaving(true);
            const sceneIds = newScenes.map(s => s.id);
            await reorderScenes(scriptId, sceneIds);
            toast.success('Reordered', 'Scene order updated');
        } catch (err) {
            console.error('Error reordering:', err);
            toast.error('Error', 'Failed to save new order');
            // Reload to get correct order
            loadScenes();
        } finally {
            setSaving(false);
        }
    };
    
    // ============================================
    // Omit/Restore Handlers
    // ============================================
    
    const handleOmitScene = async (scene) => {
        if (script?.is_locked) {
            toast.error('Locked', 'Cannot modify scenes in a locked script');
            return;
        }
        
        const newOmitState = !scene.is_omitted;
        
        // Optimistic update
        setScenes(prev => prev.map(s => 
            s.id === scene.id ? { ...s, is_omitted: newOmitState } : s
        ));
        
        try {
            await omitScene(scriptId, scene.id, newOmitState);
            toast.success(
                newOmitState ? 'Scene Omitted' : 'Scene Restored',
                `Scene ${scene.scene_number} has been ${newOmitState ? 'omitted' : 'restored'}`
            );
        } catch (err) {
            console.error('Error omitting scene:', err);
            toast.error('Error', 'Failed to update scene');
            // Revert
            setScenes(prev => prev.map(s => 
                s.id === scene.id ? { ...s, is_omitted: !newOmitState } : s
            ));
        }
    };
    
    // ============================================
    // Edit Header Handlers
    // ============================================
    
    const startEditing = (scene) => {
        if (script?.is_locked) {
            toast.error('Locked', 'Cannot modify scenes in a locked script');
            return;
        }
        setEditingScene(scene.id);
        setEditForm({
            int_ext: scene.int_ext || 'INT',
            setting: scene.setting || '',
            time_of_day: scene.time_of_day || 'DAY'
        });
    };
    
    const cancelEditing = () => {
        setEditingScene(null);
        setEditForm({ int_ext: '', setting: '', time_of_day: '' });
    };
    
    const saveEditing = async () => {
        if (!editingScene) return;
        
        try {
            setSaving(true);
            await updateSceneHeader(scriptId, editingScene, editForm);
            
            // Update local state
            setScenes(prev => prev.map(s => 
                s.id === editingScene ? { ...s, ...editForm } : s
            ));
            
            toast.success('Updated', 'Scene header updated');
            cancelEditing();
        } catch (err) {
            console.error('Error updating scene:', err);
            toast.error('Error', 'Failed to update scene header');
        } finally {
            setSaving(false);
        }
    };
    
    // ============================================
    // Phase 2: Split/Merge/Add Handlers
    // ============================================
    
    const openSplitModal = (scene) => {
        if (script?.is_locked) {
            toast.error('Locked', 'Cannot split scenes in a locked script');
            return;
        }
        setSelectedScene(scene);
        setSplitModalOpen(true);
    };
    
    const openMergeModal = (scene, index) => {
        if (script?.is_locked) {
            toast.error('Locked', 'Cannot merge scenes in a locked script');
            return;
        }
        // Find adjacent scene (next one)
        const nextScene = scenes[index + 1];
        if (!nextScene || nextScene.is_omitted) {
            toast.error('Cannot Merge', 'No adjacent scene to merge with');
            return;
        }
        setSelectedScene(scene);
        setMergeTargetScene(nextScene);
        setMergeModalOpen(true);
    };
    
    const openAddModal = (afterScene = null) => {
        if (script?.is_locked) {
            toast.error('Locked', 'Cannot add scenes to a locked script');
            return;
        }
        setInsertAfterScene(afterScene);
        setAddModalOpen(true);
    };
    
    const handleModalSuccess = () => {
        loadScenes(); // Reload scenes after any operation
        setSelectedSceneIds(new Set()); // Clear selection after operation
    };
    
    // ============================================
    // Multi-Select Handlers
    // ============================================
    
    const toggleSceneSelection = (sceneId) => {
        setSelectedSceneIds(prev => {
            const newSet = new Set(prev);
            if (newSet.has(sceneId)) {
                newSet.delete(sceneId);
            } else {
                newSet.add(sceneId);
            }
            return newSet;
        });
    };
    
    const clearSelection = () => {
        setSelectedSceneIds(new Set());
    };
    
    const getSelectedScenes = () => {
        return scenes.filter(s => selectedSceneIds.has(s.id));
    };
    
    const areSelectedScenesContiguous = () => {
        const selected = getSelectedScenes();
        if (selected.length < 2) return false;
        
        // Sort by scene_order
        const sorted = [...selected].sort((a, b) => (a.scene_order || 0) - (b.scene_order || 0));
        
        // Check if all are adjacent (allowing for omitted scenes in between)
        const activeScenes = scenes.filter(s => !s.is_omitted);
        const activeOrders = activeScenes.map(s => s.scene_order);
        
        for (let i = 0; i < sorted.length - 1; i++) {
            const currentOrder = sorted[i].scene_order;
            const nextOrder = sorted[i + 1].scene_order;
            
            // Check if there are any non-selected active scenes between them
            const scenesBetween = activeScenes.filter(
                s => s.scene_order > currentOrder && 
                     s.scene_order < nextOrder && 
                     !selectedSceneIds.has(s.id)
            );
            
            if (scenesBetween.length > 0) {
                return false;
            }
        }
        
        return true;
    };
    
    const openMultiMergeModal = () => {
        if (!areSelectedScenesContiguous()) {
            toast.error('Invalid Selection', 'Selected scenes must be adjacent to merge');
            return;
        }
        setMultiMergeModalOpen(true);
    };
    
    // ============================================
    // Render Helpers
    // ============================================
    
    const getStatusIcon = (scene) => {
        if (scene.analysis_status === 'complete') {
            return <CheckCircle size={16} className="status-icon complete" />;
        }
        if (scene.analysis_status === 'analyzing') {
            return <Loader size={16} className="status-icon analyzing spin" />;
        }
        return <Clock size={16} className="status-icon pending" />;
    };
    
    const formatSceneHeader = (scene) => {
        const parts = [scene.int_ext, scene.setting, scene.time_of_day].filter(Boolean);
        return parts.join(' - ') || 'Untitled Scene';
    };
    
    // ============================================
    // Render
    // ============================================
    
    if (loading) {
        return (
            <div className="scene-manager">
                <div className="scene-manager-loading">
                    <Loader size={32} className="spin" />
                    <p>Loading scenes...</p>
                </div>
            </div>
        );
    }
    
    if (error) {
        return (
            <div className="scene-manager">
                <div className="scene-manager-error">
                    <AlertCircle size={32} />
                    <p>{error}</p>
                    <button onClick={loadScenes} className="btn-retry">
                        Try Again
                    </button>
                </div>
            </div>
        );
    }
    
    return (
        <div className="scene-manager">
            {/* Header */}
            <div className="scene-manager-header">
                <div className="header-left">
                    <button 
                        className="btn-back" 
                        onClick={() => navigate(`/scenes/${scriptId}`)}
                    >
                        <ChevronLeft size={20} />
                        Back to Breakdown
                    </button>
                    <div className="header-title">
                        <h1>Scene Manager</h1>
                        <span className="script-title">{script?.title}</span>
                    </div>
                </div>
                
                <div className="header-right">
                    {/* Import Revision Button */}
                    {!script?.is_locked && (
                        <button 
                            className="btn-import-revision"
                            onClick={() => setRevisionImportOpen(true)}
                        >
                            <Upload size={16} />
                            <span>Import Revision</span>
                        </button>
                    )}
                    
                    {/* Add Scene Button */}
                    {!script?.is_locked && (
                        <button 
                            className="btn-add-scene"
                            onClick={() => openAddModal(null)}
                        >
                            <Plus size={16} />
                            <span>Add Scene</span>
                        </button>
                    )}
                    
                    {script?.is_locked ? (
                        <div className="lock-badge locked">
                            <Lock size={16} />
                            <span>Locked</span>
                        </div>
                    ) : (
                        <div className="lock-badge unlocked">
                            <Unlock size={16} />
                            <span>Working Draft</span>
                        </div>
                    )}
                    
                    {saving && (
                        <div className="saving-indicator">
                            <Loader size={16} className="spin" />
                            <span>Saving...</span>
                        </div>
                    )}
                </div>
            </div>
            
            {/* Instructions */}
            {showInstructions && (
                <div className="scene-manager-instructions">
                    <FileText size={16} />
                    <span className="instructions-text">
                        Use <Scissors size={14} className="inline-icon" /> to split, 
                        <Merge size={14} className="inline-icon" /> to merge, 
                        <Edit3 size={14} className="inline-icon" /> to edit headers, 
                        <Plus size={14} className="inline-icon" /> to add scenes.
                    </span>
                    <button 
                        className="instructions-close"
                        onClick={() => setShowInstructions(false)}
                        title="Dismiss"
                    >
                        <X size={16} />
                    </button>
                </div>
            )}
            
            {/* Stats Bar */}
            <div className="scene-manager-stats">
                <div className="stat">
                    <span className="stat-value">{scenes.length}</span>
                    <span className="stat-label">Total Scenes</span>
                </div>
                <div className="stat">
                    <span className="stat-value">
                        {scenes.filter(s => !s.is_omitted).length}
                    </span>
                    <span className="stat-label">Active</span>
                </div>
                <div className="stat">
                    <span className="stat-value">
                        {scenes.filter(s => s.is_omitted).length}
                    </span>
                    <span className="stat-label">Omitted</span>
                </div>
                <div className="stat">
                    <span className="stat-value">
                        {scenes.filter(s => s.analysis_status === 'complete').length}
                    </span>
                    <span className="stat-label">Analyzed</span>
                </div>
            </div>
            
            {/* Scene List */}
            <div className="scene-manager-list">
                {scenes.length === 0 ? (
                    <div className="empty-state">
                        <FileText size={48} />
                        <p>No scenes found</p>
                    </div>
                ) : (
                    scenes.map((scene, index) => (
                        <div
                            key={scene.id}
                            className={`scene-manager-item ${scene.is_omitted ? 'omitted' : ''} ${
                                draggedIndex === index ? 'dragging' : ''
                            } ${dragOverIndex === index ? 'drag-over' : ''} ${
                                selectedSceneIds.has(scene.id) ? 'selected' : ''
                            }`}
                            draggable={!script?.is_locked && editingScene !== scene.id && selectedSceneIds.size === 0}
                            onDragStart={(e) => handleDragStart(e, index)}
                            onDragEnd={handleDragEnd}
                            onDragOver={(e) => handleDragOver(e, index)}
                            onDragLeave={handleDragLeave}
                            onDrop={(e) => handleDrop(e, index)}
                        >
                            {/* Selection Checkbox */}
                            {!scene.is_omitted && !script?.is_locked && (
                                <label className="scene-checkbox">
                                    <input
                                        type="checkbox"
                                        checked={selectedSceneIds.has(scene.id)}
                                        onChange={() => toggleSceneSelection(scene.id)}
                                    />
                                    <span className="checkmark"></span>
                                </label>
                            )}
                            
                            {/* Drag Handle */}
                            <div className={`drag-handle ${script?.is_locked ? 'disabled' : ''}`}>
                                <GripVertical size={20} color="#94a3b8" />
                            </div>
                            
                            {/* Scene Number */}
                            <div className="scene-number-badge">
                                {scene.is_omitted ? (
                                    <span className="omitted-label">OMIT</span>
                                ) : (
                                    scene.scene_number || index + 1
                                )}
                            </div>
                            
                            {/* Analysis Status Icon */}
                            <div className="scene-status-indicator">
                                {getStatusIcon(scene)}
                            </div>
                            
                            {/* Scene Content */}
                            <div className="scene-content">
                                {editingScene === scene.id ? (
                                    // Edit Mode
                                    <div className="scene-edit-form">
                                        <select
                                            value={editForm.int_ext}
                                            onChange={(e) => setEditForm(prev => ({ ...prev, int_ext: e.target.value }))}
                                            className="edit-select"
                                        >
                                            <option value="INT">INT</option>
                                            <option value="EXT">EXT</option>
                                            <option value="INT/EXT">INT/EXT</option>
                                        </select>
                                        
                                        <input
                                            type="text"
                                            value={editForm.setting}
                                            onChange={(e) => setEditForm(prev => ({ ...prev, setting: e.target.value }))}
                                            placeholder="Location"
                                            className="edit-input"
                                        />
                                        
                                        <select
                                            value={editForm.time_of_day}
                                            onChange={(e) => setEditForm(prev => ({ ...prev, time_of_day: e.target.value }))}
                                            className="edit-select"
                                        >
                                            <option value="DAY">DAY</option>
                                            <option value="NIGHT">NIGHT</option>
                                            <option value="DAWN">DAWN</option>
                                            <option value="DUSK">DUSK</option>
                                            <option value="CONTINUOUS">CONTINUOUS</option>
                                            <option value="LATER">LATER</option>
                                            <option value="MOMENTS LATER">MOMENTS LATER</option>
                                        </select>
                                        
                                        <div className="edit-actions">
                                            <button 
                                                className="btn-save" 
                                                onClick={saveEditing}
                                                disabled={saving}
                                            >
                                                <Save size={14} />
                                            </button>
                                            <button 
                                                className="btn-cancel" 
                                                onClick={cancelEditing}
                                            >
                                                <X size={14} />
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    // View Mode
                                    <>
                                        <div className="scene-header-text">
                                            {formatSceneHeader(scene)}
                                        </div>
                                        <div className="scene-meta">
                                            {scene.page_start && (
                                                <span className="meta-badge page-badge">
                                                    p. {scene.page_start}
                                                    {scene.page_end && scene.page_end !== scene.page_start && 
                                                        `-${scene.page_end}`}
                                                </span>
                                            )}
                                            {scene.character_count > 0 && (
                                                <span className="meta-badge char-badge">
                                                    {scene.character_count} {scene.character_count === 1 ? 'char' : 'chars'}
                                                </span>
                                            )}
                                            {scene.prop_count > 0 && (
                                                <span className="meta-badge prop-badge">
                                                    {scene.prop_count} {scene.prop_count === 1 ? 'prop' : 'props'}
                                                </span>
                                            )}
                                        </div>
                                    </>
                                )}
                            </div>
                            
                            {/* Actions */}
                            {editingScene !== scene.id && (
                                <div className="scene-actions" style={{ display: 'flex', gap: '0.5rem' }}>
                                    {/* Split Scene */}
                                    {!scene.is_omitted && (
                                        <button
                                            className="action-btn split"
                                            onClick={() => openSplitModal(scene)}
                                            title="Split scene"
                                            disabled={script?.is_locked}
                                            style={{ background: '#334155', border: '1px solid #475569', borderRadius: '6px', padding: '6px', cursor: 'pointer' }}
                                        >
                                            <Scissors size={16} color="#cbd5e1" />
                                        </button>
                                    )}
                                    
                                    {/* Merge with Next */}
                                    {!scene.is_omitted && index < scenes.length - 1 && (
                                        <button
                                            className="action-btn merge"
                                            onClick={() => openMergeModal(scene, index)}
                                            title="Merge with next scene"
                                            disabled={script?.is_locked}
                                            style={{ background: '#334155', border: '1px solid #475569', borderRadius: '6px', padding: '6px', cursor: 'pointer' }}
                                        >
                                            <Merge size={16} color="#cbd5e1" />
                                        </button>
                                    )}
                                    
                                    {/* Omit/Restore */}
                                    <button
                                        className={`action-btn ${scene.is_omitted ? 'restore' : 'omit'}`}
                                        onClick={() => handleOmitScene(scene)}
                                        title={scene.is_omitted ? 'Restore scene' : 'Omit scene'}
                                        disabled={script?.is_locked}
                                        style={{ background: '#334155', border: '1px solid #475569', borderRadius: '6px', padding: '6px', cursor: 'pointer' }}
                                    >
                                        {scene.is_omitted ? <RotateCcw size={16} color="#cbd5e1" /> : <X size={16} color="#cbd5e1" />}
                                    </button>
                                    
                                    {/* Edit Header */}
                                    <button
                                        className="action-btn edit"
                                        onClick={() => startEditing(scene)}
                                        title="Edit scene header"
                                        disabled={script?.is_locked}
                                        style={{ background: '#334155', border: '1px solid #475569', borderRadius: '6px', padding: '6px', cursor: 'pointer' }}
                                    >
                                        <Edit3 size={16} color="#cbd5e1" />
                                    </button>
                                    
                                    {/* Add Scene After */}
                                    <button
                                        className="action-btn add"
                                        onClick={() => openAddModal(scene)}
                                        title="Add scene after this"
                                        disabled={script?.is_locked}
                                        style={{ background: '#334155', border: '1px solid #475569', borderRadius: '6px', padding: '6px', cursor: 'pointer' }}
                                    >
                                        <Plus size={16} color="#cbd5e1" />
                                    </button>
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
            
            {/* Modals */}
            <SceneSplitModal
                isOpen={splitModalOpen}
                onClose={() => setSplitModalOpen(false)}
                scene={selectedScene}
                scriptId={scriptId}
                onSuccess={handleModalSuccess}
            />
            
            <SceneMergeModal
                isOpen={mergeModalOpen}
                onClose={() => setMergeModalOpen(false)}
                scene={selectedScene}
                adjacentScene={mergeTargetScene}
                scriptId={scriptId}
                onSuccess={handleModalSuccess}
            />
            
            <AddSceneModal
                isOpen={addModalOpen}
                onClose={() => setAddModalOpen(false)}
                scriptId={scriptId}
                insertAfterScene={insertAfterScene}
                onSuccess={handleModalSuccess}
            />
            
            <MultiMergeModal
                isOpen={multiMergeModalOpen}
                onClose={() => setMultiMergeModalOpen(false)}
                scenes={getSelectedScenes()}
                scriptId={scriptId}
                onSuccess={handleModalSuccess}
            />
            
            {/* Revision Import Wizard (Phase 3) */}
            <RevisionImportWizard
                isOpen={revisionImportOpen}
                onClose={() => setRevisionImportOpen(false)}
                scriptId={scriptId}
                scriptTitle={script?.title}
                onImportComplete={() => {
                    loadScenes();
                    toast.success('Revision Imported', 'Script has been updated with the new revision');
                }}
            />
            
            {/* Floating Action Bar for Multi-Select */}
            {selectedSceneIds.size >= 2 && (
                <div className="floating-action-bar">
                    <span className="selection-count">
                        {selectedSceneIds.size} scenes selected
                    </span>
                    <div className="action-buttons">
                        <button 
                            className="btn-merge"
                            onClick={openMultiMergeModal}
                        >
                            <Merge size={16} />
                            Merge Selected
                        </button>
                        <button 
                            className="btn-clear"
                            onClick={clearSelection}
                        >
                            <X size={16} />
                            Clear
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SceneManager;
