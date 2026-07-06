import React, { useState, useMemo } from 'react';
import { Merge, AlertCircle } from 'lucide-react';
import { mergeMultipleScenes } from '../../services/apiService';
import { useToast } from '../../context/ToastContext';
import { Modal, Button } from '../ui';
import './SceneModals.css';

/**
 * MultiMergeModal - Modal for merging multiple scenes at once
 * 
 * Industry standard: One scene number is kept, all others become OMITTED
 */
const MultiMergeModal = ({ isOpen, onClose, scenes, scriptId, onSuccess }) => {
    const toast = useToast();
    const [loading, setLoading] = useState(false);
    const [keepSceneId, setKeepSceneId] = useState(null);
    
    // Sort scenes by order
    const sortedScenes = useMemo(() => {
        if (!scenes || scenes.length === 0) return [];
        return [...scenes].sort((a, b) => (a.scene_order || 0) - (b.scene_order || 0));
    }, [scenes]);
    
    // Set default keep scene to first one
    React.useEffect(() => {
        if (sortedScenes.length > 0 && !keepSceneId) {
            setKeepSceneId(sortedScenes[0].id);
        }
    }, [sortedScenes, keepSceneId]);
    
    if (!isOpen || !scenes || scenes.length < 2) return null;
    
    const keptScene = sortedScenes.find(s => s.id === keepSceneId);
    const omittedScenes = sortedScenes.filter(s => s.id !== keepSceneId);
    
    const formatSceneHeader = (s) => {
        return `${s.int_ext || 'INT'}. ${s.setting || 'LOCATION'} - ${s.time_of_day || 'DAY'}`;
    };
    
    const handleMerge = async () => {
        if (!keepSceneId) {
            toast.error('Required', 'Please select which scene number to keep');
            return;
        }
        
        try {
            setLoading(true);
            
            const sceneIds = sortedScenes.map(s => s.id);
            await mergeMultipleScenes(scriptId, sceneIds, keepSceneId);
            
            toast.success(
                'Scenes Merged', 
                `${scenes.length} scenes merged. Scene ${keptScene?.scene_number} kept.`
            );
            onSuccess?.();
            onClose();
            setKeepSceneId(null);
        } catch (error) {
            console.error('Error merging scenes:', error);
            toast.error('Error', error.response?.data?.error || 'Failed to merge scenes');
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={<><Merge size={20} /> Merge {scenes.length} Scenes</>}
            footer={
                <>
                    <Button variant="secondary" onClick={onClose} disabled={loading}>
                        Cancel
                    </Button>
                    <Button variant="primary" onClick={handleMerge} loading={loading} icon={Merge}>
                        {loading ? 'Merging…' : `Merge ${scenes.length} Scenes`}
                    </Button>
                </>
            }
        >
                    {/* Info Banner */}
                    <div className="info-banner warning">
                        <AlertCircle size={16} />
                        <span>
                            {omittedScenes.length} scene{omittedScenes.length > 1 ? 's' : ''} will be marked as OMITTED
                        </span>
                    </div>
                    
                    {/* Scenes to Merge */}
                    <div className="multi-merge-list">
                        <label className="section-label">Scenes to merge:</label>
                        {sortedScenes.map((scene, index) => (
                            <div 
                                key={scene.id}
                                className={`merge-scene-item ${keepSceneId === scene.id ? 'kept' : 'omitted'}`}
                            >
                                <label className="radio-wrapper">
                                    <input
                                        type="radio"
                                        name="keepScene"
                                        value={scene.id}
                                        checked={keepSceneId === scene.id}
                                        onChange={() => setKeepSceneId(scene.id)}
                                    />
                                    <div className="scene-info">
                                        <span className="scene-badge">{scene.scene_number}</span>
                                        <span className="scene-header">{formatSceneHeader(scene)}</span>
                                    </div>
                                    {keepSceneId === scene.id ? (
                                        <span className="status-badge kept">KEEP</span>
                                    ) : (
                                        <span className="status-badge omitted">OMIT</span>
                                    )}
                                </label>
                            </div>
                        ))}
                    </div>
                    
                    {/* Result Preview */}
                    <div className="result-preview">
                        <h4>Result</h4>
                        <p>
                            All content will be combined into scene{' '}
                            <strong>{keptScene?.scene_number}</strong>.
                            {omittedScenes.length > 0 && (
                                <> Scene{omittedScenes.length > 1 ? 's' : ''}{' '}
                                <strong>
                                    {omittedScenes.map(s => s.scene_number).join(', ')}
                                </strong>{' '}
                                will be marked as OMITTED.</>
                            )}
                        </p>
                    </div>
        </Modal>
    );
};

export default MultiMergeModal;
