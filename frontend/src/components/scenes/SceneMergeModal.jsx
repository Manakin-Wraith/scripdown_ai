import React, { useState } from 'react';
import { Merge, AlertCircle, ChevronRight } from 'lucide-react';
import { mergeScenes } from '../../services/apiService';
import { useToast } from '../../context/ToastContext';
import { Modal, Button, Badge } from '../ui';
import './SceneModals.css';

/**
 * SceneMergeModal - Modal for merging two adjacent scenes
 * 
 * Industry standard: One scene number is kept, the other becomes OMITTED
 */
const SceneMergeModal = ({ isOpen, onClose, scene, adjacentScene, scriptId, onSuccess }) => {
    const toast = useToast();
    const [loading, setLoading] = useState(false);
    const [keepNumber, setKeepNumber] = useState('first');
    
    if (!isOpen || !scene || !adjacentScene) return null;
    
    // Determine which is first by order
    const isSceneFirst = (scene.scene_order || 0) < (adjacentScene.scene_order || 0);
    const firstScene = isSceneFirst ? scene : adjacentScene;
    const secondScene = isSceneFirst ? adjacentScene : scene;
    
    const keptNumber = keepNumber === 'first' ? firstScene.scene_number : secondScene.scene_number;
    const omittedNumber = keepNumber === 'first' ? secondScene.scene_number : firstScene.scene_number;
    
    const handleMerge = async () => {
        try {
            setLoading(true);
            
            await mergeScenes(scriptId, scene.id, adjacentScene.id, keepNumber);
            
            toast.success('Scenes Merged', `Scenes merged. Scene ${omittedNumber} is now OMITTED.`);
            onSuccess?.();
            onClose();
        } catch (error) {
            console.error('Error merging scenes:', error);
            toast.error('Error', error.response?.data?.error || 'Failed to merge scenes');
        } finally {
            setLoading(false);
        }
    };
    
    const formatSceneHeader = (s) => {
        return `${s.int_ext || 'INT'}. ${s.setting || 'LOCATION'} - ${s.time_of_day || 'DAY'}`;
    };
    
    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={<><Merge size={20} /> Merge Scenes</>}
            footer={
                <>
                    <Button variant="secondary" onClick={onClose} disabled={loading}>
                        Cancel
                    </Button>
                    <Button variant="primary" onClick={handleMerge} loading={loading} icon={Merge}>
                        {loading ? 'Merging…' : 'Merge Scenes'}
                    </Button>
                </>
            }
        >
                    {/* Info Banner */}
                    <div className="info-banner warning">
                        <AlertCircle size={16} />
                        <span>
                            Scene <strong>{omittedNumber}</strong> will be marked as OMITTED
                        </span>
                    </div>
                    
                    {/* Scenes to Merge */}
                    <div className="merge-preview">
                        <div className={`merge-scene ${keepNumber === 'first' ? 'kept' : 'omitted'}`}>
                            <div className="merge-scene-header">
                                <span className="scene-badge">{firstScene.scene_number}</span>
                                {keepNumber === 'first' ? (
                                    <Badge variant="success">KEPT</Badge>
                                ) : (
                                    <Badge variant="danger">OMITTED</Badge>
                                )}
                            </div>
                            <div className="merge-scene-content">
                                {formatSceneHeader(firstScene)}
                            </div>
                        </div>
                        
                        <div className="merge-arrow">
                            <ChevronRight size={24} />
                        </div>
                        
                        <div className={`merge-scene ${keepNumber === 'second' ? 'kept' : 'omitted'}`}>
                            <div className="merge-scene-header">
                                <span className="scene-badge">{secondScene.scene_number}</span>
                                {keepNumber === 'second' ? (
                                    <Badge variant="success">KEPT</Badge>
                                ) : (
                                    <Badge variant="danger">OMITTED</Badge>
                                )}
                            </div>
                            <div className="merge-scene-content">
                                {formatSceneHeader(secondScene)}
                            </div>
                        </div>
                    </div>
                    
                    {/* Keep Number Selection */}
                    <div className="keep-number-section">
                        <label>Keep Scene Number</label>
                        <div className="radio-group">
                            <label className={`radio-option ${keepNumber === 'first' ? 'selected' : ''}`}>
                                <input
                                    type="radio"
                                    name="keepNumber"
                                    value="first"
                                    checked={keepNumber === 'first'}
                                    onChange={(e) => setKeepNumber(e.target.value)}
                                />
                                <span className="radio-label">
                                    Keep <strong>{firstScene.scene_number}</strong>
                                </span>
                            </label>
                            <label className={`radio-option ${keepNumber === 'second' ? 'selected' : ''}`}>
                                <input
                                    type="radio"
                                    name="keepNumber"
                                    value="second"
                                    checked={keepNumber === 'second'}
                                    onChange={(e) => setKeepNumber(e.target.value)}
                                />
                                <span className="radio-label">
                                    Keep <strong>{secondScene.scene_number}</strong>
                                </span>
                            </label>
                        </div>
                    </div>
                    
                    {/* Result Preview */}
                    <div className="result-preview">
                        <h4>Result</h4>
                        <p>
                            The content from both scenes will be combined into scene{' '}
                            <strong>{keptNumber}</strong>. Scene <strong>{omittedNumber}</strong>{' '}
                            will be marked as OMITTED but will retain its number for continuity.
                        </p>
                    </div>
        </Modal>
    );
};

export default SceneMergeModal;
