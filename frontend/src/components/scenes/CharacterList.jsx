import React from 'react';
import { Users, ChevronRight } from 'lucide-react';
import './SceneList.css'; // Re-use basic list styles

const CharacterList = ({ characters, selectedName, onSelect }) => {
    if (!characters || Object.keys(characters).length === 0) {
        return (
            <div className="list-empty">
                <Users size={32} className="empty-icon-small" />
                <p>No characters found</p>
            </div>
        );
    }

    const sortedNames = Object.keys(characters).sort();

    return (
        <div className="scene-list">
            {sortedNames.map((name) => {
                const sceneCount = characters[name].length;
                const scenesText = characters[name]
                    .map(s => `#${s.scene_number}`)
                    .join(', ');
                
                return (
                    <div 
                        key={name}
                        className={`scene-item character-item ${selectedName === name ? 'selected' : ''}`}
                        onClick={() => onSelect(name)}
                    >
                        <div className="scene-item-content">
                            <div className="entity-header">
                                <span className="entity-badge char-badge">CHAR</span>
                                <span className="entity-count">{sceneCount} {sceneCount === 1 ? 'Scene' : 'Scenes'}</span>
                            </div>
                            
                            <div className="entity-name" title={name}>
                                {name}
                            </div>
                            
                            <div className="entity-meta">
                                <span className="meta-label">In:</span>
                                <span className="meta-value">{scenesText}</span>
                            </div>
                        </div>
                        
                        <ChevronRight size={16} className="arrow-icon" />
                    </div>
                );
            })}
        </div>
    );
};

export default CharacterList;
