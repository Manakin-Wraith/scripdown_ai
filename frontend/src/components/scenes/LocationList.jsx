import React from 'react';
import { MapPin, ChevronRight } from 'lucide-react';
import './SceneList.css';

const LocationList = ({ locations, selectedLocation, onSelect }) => {
    if (!locations || Object.keys(locations).length === 0) {
        return (
            <div className="list-empty">
                <MapPin size={32} className="empty-icon-small" />
                <p>No locations found</p>
            </div>
        );
    }

    const sortedLocations = Object.keys(locations).sort();

    return (
        <div className="scene-list">
            {sortedLocations.map((loc) => {
                const sceneCount = locations[loc].length;
                const scenesText = locations[loc]
                    .map(s => `#${s.scene_number}`)
                    .join(', ');

                return (
                    <div 
                        key={loc}
                        className={`scene-item location-item ${selectedLocation === loc ? 'selected' : ''}`}
                        onClick={() => onSelect(loc)}
                    >
                        <div className="scene-item-content">
                            <div className="entity-header">
                                <span className="entity-badge loc-badge">LOC</span>
                                <span className="entity-count">{sceneCount} {sceneCount === 1 ? 'Scene' : 'Scenes'}</span>
                            </div>
                            
                            <div className="entity-name" title={loc}>
                                {loc}
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

export default LocationList;
