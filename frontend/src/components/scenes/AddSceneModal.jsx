import React, { useState } from 'react';
import { Plus } from 'lucide-react';
import { addManualScene } from '../../services/apiService';
import { useToast } from '../../context/ToastContext';
import { Modal, Button } from '../ui';
import './SceneModals.css';

/**
 * AddSceneModal - Modal for adding a new scene manually
 */
const AddSceneModal = ({ isOpen, onClose, scriptId, insertAfterScene, onSuccess }) => {
    const toast = useToast();
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        scene_number: '',
        int_ext: 'INT',
        setting: '',
        time_of_day: 'DAY'
    });
    
    const handleChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };
    
    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!formData.setting.trim()) {
            toast.error('Required', 'Please enter a location/setting');
            return;
        }
        
        try {
            setLoading(true);
            
            const sceneData = {
                ...formData,
                setting: formData.setting.toUpperCase(),
                insert_after_scene_id: insertAfterScene?.id || null
            };
            
            // Remove empty scene_number to let backend auto-generate
            if (!sceneData.scene_number) {
                delete sceneData.scene_number;
            }
            
            await addManualScene(scriptId, sceneData);
            
            toast.success('Scene Added', 'New scene created successfully');
            onSuccess?.();
            onClose();
            
            // Reset form
            setFormData({
                scene_number: '',
                int_ext: 'INT',
                setting: '',
                time_of_day: 'DAY'
            });
        } catch (error) {
            console.error('Error adding scene:', error);
            toast.error('Error', error.response?.data?.error || 'Failed to add scene');
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={<><Plus size={20} /> Add New Scene</>}
            footer={
                <>
                    <Button variant="secondary" onClick={onClose} disabled={loading}>
                        Cancel
                    </Button>
                    <Button type="submit" form="add-scene-form" variant="primary" loading={loading} icon={Plus}>
                        {loading ? 'Adding…' : 'Add Scene'}
                    </Button>
                </>
            }
        >
            <form id="add-scene-form" onSubmit={handleSubmit}>
                        {/* Insert Position Info */}
                        {insertAfterScene && (
                            <div className="insert-info">
                                Inserting after Scene {insertAfterScene.scene_number}
                            </div>
                        )}
                        
                        {/* Scene Number (Optional) */}
                        <div className="form-group">
                            <label>Scene Number <span className="optional">(optional)</span></label>
                            <input
                                type="text"
                                value={formData.scene_number}
                                onChange={(e) => handleChange('scene_number', e.target.value)}
                                placeholder="Auto-generated if empty"
                                className="form-input"
                            />
                        </div>
                        
                        {/* Scene Header Row */}
                        <div className="form-row">
                            {/* INT/EXT */}
                            <div className="form-group">
                                <label>INT/EXT</label>
                                <select
                                    value={formData.int_ext}
                                    onChange={(e) => handleChange('int_ext', e.target.value)}
                                    className="form-select"
                                >
                                    <option value="INT">INT</option>
                                    <option value="EXT">EXT</option>
                                    <option value="INT/EXT">INT/EXT</option>
                                </select>
                            </div>
                            
                            {/* Time of Day */}
                            <div className="form-group">
                                <label>Time of Day</label>
                                <select
                                    value={formData.time_of_day}
                                    onChange={(e) => handleChange('time_of_day', e.target.value)}
                                    className="form-select"
                                >
                                    <option value="DAY">DAY</option>
                                    <option value="NIGHT">NIGHT</option>
                                    <option value="DAWN">DAWN</option>
                                    <option value="DUSK">DUSK</option>
                                    <option value="CONTINUOUS">CONTINUOUS</option>
                                    <option value="LATER">LATER</option>
                                    <option value="MOMENTS LATER">MOMENTS LATER</option>
                                </select>
                            </div>
                        </div>
                        
                        {/* Setting/Location */}
                        <div className="form-group">
                            <label>Location / Setting <span className="required">*</span></label>
                            <input
                                type="text"
                                value={formData.setting}
                                onChange={(e) => handleChange('setting', e.target.value.toUpperCase())}
                                placeholder="e.g., COFFEE SHOP, JOHN'S APARTMENT"
                                className="form-input"
                                required
                                autoFocus
                            />
                        </div>
                        
                        {/* Preview */}
                        <div className="scene-header-preview">
                            <span className="preview-label">Preview:</span>
                            <span className="preview-text">
                                {formData.int_ext}. {formData.setting || 'LOCATION'} - {formData.time_of_day}
                            </span>
                        </div>
            </form>
        </Modal>
    );
};

export default AddSceneModal;
