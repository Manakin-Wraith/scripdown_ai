import React, { useState } from 'react';
import { Scissors, X, AlertCircle, Loader } from 'lucide-react';
import { splitScene } from '../../services/apiService';
import { useToast } from '../../context/ToastContext';
import './SceneModals.css';

/**
 * SceneSplitModal - Modal for splitting a scene into two
 * 
 * Industry standard: Scene 15 becomes 15A and 15B
 */
const SceneSplitModal = ({ isOpen, onClose, scene, scriptId, onSuccess }) => {
    const toast = useToast();
    const [loading, setLoading] = useState(false);
    const [splitPoint, setSplitPoint] = useState(50); // Percentage
    
    if (!isOpen || !scene) return null;
    
    const sceneNumber = scene.scene_number || '?';
    const sceneText = scene.scene_text || '';
    
    // Calculate preview of split
    const lines = sceneText.split('\n');
    const splitLineIndex = Math.floor(lines.length * (splitPoint / 100));
    const firstHalf = lines.slice(0, splitLineIndex).join('\n');
    const secondHalf = lines.slice(splitLineIndex).join('\n');
    
    // Determine new scene numbers
    const baseNumber = sceneNumber.replace(/[A-Z]+$/i, '');
    const hasLetter = /[A-Z]+$/i.test(sceneNumber);
    const firstNumber = hasLetter ? `${sceneNumber}1` : `${sceneNumber}A`;
    const secondNumber = hasLetter ? `${sceneNumber}2` : `${sceneNumber}B`;
    
    const handleSplit = async () => {
        try {
            setLoading(true);
            
            await splitScene(scriptId, scene.id, {
                first_scene_text: firstHalf,
                second_scene_text: secondHalf
            });
            
            toast.success('Scene Split', `Scene ${sceneNumber} split into ${firstNumber} and ${secondNumber}`);
            onSuccess?.();
            onClose();
        } catch (error) {
            console.error('Error splitting scene:', error);
            toast.error('Error', error.response?.data?.error || 'Failed to split scene');
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="scene-modal" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="modal-header">
                    <div className="modal-title">
                        <Scissors size={20} />
                        <h2>Split Scene {sceneNumber}</h2>
                    </div>
                    <button className="modal-close" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>
                
                {/* Content */}
                <div className="modal-content">
                    {/* Info Banner */}
                    <div className="info-banner">
                        <AlertCircle size={16} />
                        <span>
                            Scene <strong>{sceneNumber}</strong> will become{' '}
                            <strong>{firstNumber}</strong> and <strong>{secondNumber}</strong>
                        </span>
                    </div>
                    
                    {/* Scene Header Preview */}
                    <div className="scene-header-preview">
                        <span className="int-ext">{scene.int_ext}</span>
                        <span className="setting">{scene.setting}</span>
                        <span className="time">{scene.time_of_day}</span>
                    </div>
                    
                    {/* Split Point Slider */}
                    {sceneText && (
                        <div className="split-slider-section">
                            <label>Split Point</label>
                            <div className="slider-container">
                                <input
                                    type="range"
                                    min="10"
                                    max="90"
                                    value={splitPoint}
                                    onChange={(e) => setSplitPoint(Number(e.target.value))}
                                    className="split-slider"
                                />
                                <span className="slider-value">{splitPoint}%</span>
                            </div>
                        </div>
                    )}
                    
                    {/* Preview */}
                    <div className="split-preview">
                        <div className="preview-section first">
                            <div className="preview-header">
                                <span className="preview-badge first">{firstNumber}</span>
                                <span className="preview-label">First Half</span>
                            </div>
                            <div className="preview-content">
                                {firstHalf || <em className="empty">No content</em>}
                            </div>
                        </div>
                        
                        <div className="split-divider">
                            <Scissors size={16} />
                        </div>
                        
                        <div className="preview-section second">
                            <div className="preview-header">
                                <span className="preview-badge second">{secondNumber}</span>
                                <span className="preview-label">Second Half</span>
                            </div>
                            <div className="preview-content">
                                {secondHalf || <em className="empty">No content</em>}
                            </div>
                        </div>
                    </div>
                </div>
                
                {/* Footer */}
                <div className="modal-footer">
                    <button className="btn-cancel" onClick={onClose} disabled={loading}>
                        Cancel
                    </button>
                    <button className="btn-primary" onClick={handleSplit} disabled={loading}>
                        {loading ? (
                            <>
                                <Loader size={16} className="spin" />
                                Splitting...
                            </>
                        ) : (
                            <>
                                <Scissors size={16} />
                                Split Scene
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default SceneSplitModal;
