import React from 'react';
import './SceneCard.css';

const SceneCard = ({ scene }) => {
    return (
        <div className="scene-card">
            <div className="scene-header">
                <span className="scene-number">Scene {scene.scene_number}</span>
                <span className="scene-setting">{scene.setting}</span>
            </div>

            <div className="scene-description">
                <p>{scene.description}</p>
            </div>

            {scene.atmosphere && (
                <div className="scene-atmosphere">
                    <span className="atmosphere-icon">🎬</span>
                    <span>{scene.atmosphere}</span>
                </div>
            )}

            {scene.characters && scene.characters.length > 0 && (
                <div className="scene-section">
                    <h4>👥 Characters</h4>
                    <div className="badge-container">
                        {scene.characters.map((character, index) => (
                            <span key={index} className="badge badge-character">
                                {character}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {scene.props && scene.props.length > 0 && (
                <div className="scene-section">
                    <h4>📦 Props</h4>
                    <div className="badge-container">
                        {scene.props.map((prop, index) => (
                            <span key={index} className="badge badge-prop">
                                {prop}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {scene.special_fx && scene.special_fx.length > 0 && (
                <div className="scene-section">
                    <h4>✨ Special FX</h4>
                    <div className="badge-container">
                        {scene.special_fx.map((fx, index) => (
                            <span key={index} className="badge badge-fx">
                                {fx}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {scene.wardrobe && scene.wardrobe.length > 0 && (
                <div className="scene-section">
                    <h4>👔 Wardrobe</h4>
                    <div className="detail-list">
                        {scene.wardrobe.map((item, index) => (
                            <div key={index} className="detail-item">{item}</div>
                        ))}
                    </div>
                </div>
            )}

            {scene.makeup_hair && scene.makeup_hair.length > 0 && (
                <div className="scene-section">
                    <h4>💄 Makeup & Hair</h4>
                    <div className="detail-list">
                        {scene.makeup_hair.map((item, index) => (
                            <div key={index} className="detail-item">{item}</div>
                        ))}
                    </div>
                </div>
            )}

            {scene.vehicles && scene.vehicles.length > 0 && (
                <div className="scene-section">
                    <h4>🚗 Vehicles</h4>
                    <div className="badge-container">
                        {scene.vehicles.map((vehicle, index) => (
                            <span key={index} className="badge badge-vehicle">
                                {vehicle}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default SceneCard;
