import React from 'react';
import { MapPin, Clapperboard, Users } from 'lucide-react';
import SceneDetail from './SceneDetail';
import './FilteredSceneList.css';

const FilteredSceneList = ({ title, type, scenes }) => {
    if (!title) {
        return (
            <div className="scene-detail-empty">
                <div className="empty-content">
                    {type === 'character' ? <Users size={64} /> : <MapPin size={64} />}
                    <h3>Select a {type}</h3>
                    <p>Choose from the sidebar to view their scenes</p>
                </div>
            </div>
        );
    }

    return (
        <div className="filtered-view">
            <div className="filtered-header">
                <div className="header-badge">
                    {type === 'character' ? 'CHARACTER PROFILE' : 'LOCATION PROFILE'}
                </div>
                <h1>{title}</h1>
                <p className="scene-count-label">
                    Appears in {scenes.length} scenes
                </p>
            </div>

            <div className="filtered-content">
                {scenes.map((scene) => (
                    <div key={scene.scene_id} className="filtered-scene-card">
                        <div className="scene-card-header">
                            <div className="scene-number-badge">SCENE {scene.scene_number}</div>
                            <h3>{scene.setting}</h3>
                        </div>
                        <p className="scene-desc">{scene.description}</p>
                        
                        {/* Mini Breakdown for Context */}
                        <div className="mini-breakdown">
                            {scene.props && scene.props.length > 0 && (
                                <div className="mini-section">
                                    <span className="mini-label">Props:</span>
                                    <span className="mini-value">{scene.props.join(', ')}</span>
                                </div>
                            )}
                             {scene.wardrobe && scene.wardrobe.length > 0 && (
                                <div className="mini-section">
                                    <span className="mini-label">Wardrobe:</span>
                                    <span className="mini-value">{scene.wardrobe.join(', ')}</span>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default FilteredSceneList;
