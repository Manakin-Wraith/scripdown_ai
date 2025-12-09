import React from 'react';
import { Users, MapPin, CheckCircle, Clock } from 'lucide-react';
import './ScriptSummary.css';

/**
 * ScriptSummary - Collapsible panel showing aggregated script data
 * 
 * Displays:
 * - All characters with scene counts
 * - All locations with scene counts
 * - Analysis progress stats
 */
const ScriptSummary = ({ characters, locations, stats }) => {
    // Sort characters by appearance count
    const sortedCharacters = Object.entries(characters)
        .sort((a, b) => b[1].count - a[1].count);
    
    // Sort locations by appearance count
    const sortedLocations = Object.entries(locations)
        .sort((a, b) => b[1].count - a[1].count);

    return (
        <div className="script-summary">
            {/* Stats Row */}
            <div className="summary-stats-row">
                <div className="stat-item">
                    <CheckCircle size={16} className="stat-icon complete" />
                    <span className="stat-value">{stats.analyzed}</span>
                    <span className="stat-label">Analyzed</span>
                </div>
                <div className="stat-item">
                    <Clock size={16} className="stat-icon pending" />
                    <span className="stat-value">{stats.pending}</span>
                    <span className="stat-label">Pending</span>
                </div>
                <div className="stat-item">
                    <Users size={16} className="stat-icon" />
                    <span className="stat-value">{sortedCharacters.length}</span>
                    <span className="stat-label">Characters</span>
                </div>
                <div className="stat-item">
                    <MapPin size={16} className="stat-icon" />
                    <span className="stat-value">{sortedLocations.length}</span>
                    <span className="stat-label">Locations</span>
                </div>
            </div>

            <div className="summary-columns">
                {/* Characters Column */}
                <div className="summary-column">
                    <h4 className="column-title">
                        <Users size={14} />
                        Characters
                    </h4>
                    <div className="summary-list">
                        {sortedCharacters.length === 0 ? (
                            <p className="empty-text">No characters detected yet</p>
                        ) : (
                            sortedCharacters.map(([name, data]) => (
                                <div key={name} className="summary-item">
                                    <span className="item-name">{name}</span>
                                    <span className="item-count">{data.count} scenes</span>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Locations Column */}
                <div className="summary-column">
                    <h4 className="column-title">
                        <MapPin size={14} />
                        Locations
                    </h4>
                    <div className="summary-list">
                        {sortedLocations.length === 0 ? (
                            <p className="empty-text">No locations detected yet</p>
                        ) : (
                            sortedLocations.map(([name, data]) => (
                                <div key={name} className="summary-item">
                                    <span className="item-name" title={name}>
                                        {name.length > 40 ? name.substring(0, 40) + '...' : name}
                                    </span>
                                    <span className="item-count">{data.count} scenes</span>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ScriptSummary;
