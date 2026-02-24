import React, { useState } from 'react';
import { ZoomIn, ZoomOut, Maximize, RotateCcw, Filter, Layers, MousePointer2, Hand, Move, BoxSelect, CalendarPlus, X } from 'lucide-react';
import { countActiveFilters } from './boardModel';
import SchedulePopover from './SchedulePopover';
import ViewSwitcher from '../shared/ViewSwitcher';
import './BoardToolbar.css';

const BoardToolbar = ({ groupBy, filters, uniqueDays, uniqueCharacters, totalVisible, totalScenes, zoomApiRef, dispatch, toolMode, selectedCount, scriptId, selectedSceneIds, onScheduled }) => {
    const activeFilterCount = countActiveFilters(filters);
    const [showSchedule, setShowSchedule] = useState(false);

    const handleZoomIn = () => zoomApiRef.current?.zoomIn(0.3);
    const handleZoomOut = () => zoomApiRef.current?.zoomOut(0.3);
    const handleFitAll = () => zoomApiRef.current?.resetTransform();
    const handleReset = () => zoomApiRef.current?.setTransform(0, 0, 1);

    return (
        <div className="board-toolbar">
            {/* Left: View switcher + Tool mode toggle + Zoom controls */}
            <div className="toolbar-section">
                <ViewSwitcher scriptId={scriptId} />

                <div className="toolbar-tool-modes">
                    <button
                        className={`tool-mode-btn ${toolMode === 'select' ? 'active' : ''}`}
                        onClick={() => dispatch({ type: 'SET_TOOL_MODE', payload: 'select' })}
                        title="Select — Draw frame to select cards (S)"
                    >
                        <BoxSelect size={16} />
                    </button>
                    <button
                        className={`tool-mode-btn ${toolMode === 'grab' ? 'active' : ''}`}
                        onClick={() => dispatch({ type: 'SET_TOOL_MODE', payload: 'grab' })}
                        title="Grab — Pan the canvas (G)"
                    >
                        <Hand size={16} />
                    </button>
                    <button
                        className={`tool-mode-btn ${toolMode === 'move' ? 'active' : ''}`}
                        onClick={() => dispatch({ type: 'SET_TOOL_MODE', payload: 'move' })}
                        title="Move — Click cards for details, drag to reorder (V)"
                    >
                        <MousePointer2 size={16} />
                    </button>
                </div>

                {selectedCount > 0 && (
                    <div className="toolbar-selection-actions">
                        <span className="selection-count">{selectedCount} selected</span>
                        <span className="selection-divider" />
                        <div className="sp-anchor">
                            <button
                                className="schedule-btn"
                                onClick={() => setShowSchedule(!showSchedule)}
                                title="Add selected scenes to shooting schedule"
                            >
                                <CalendarPlus size={14} /> Schedule
                            </button>
                            {showSchedule && (
                                <SchedulePopover
                                    scriptId={scriptId}
                                    selectedSceneIds={selectedSceneIds}
                                    onSuccess={() => {
                                        setShowSchedule(false);
                                        dispatch({ type: 'CLEAR_SELECTION' });
                                    }}
                                    onClose={() => setShowSchedule(false)}
                                    onScheduled={onScheduled}
                                />
                            )}
                        </div>
                        <span className="selection-divider" />
                        <button
                            className="toolbar-btn clear-btn"
                            onClick={() => dispatch({ type: 'CLEAR_SELECTION' })}
                            title="Clear selection"
                        >
                            <X size={12} /> Clear
                        </button>
                    </div>
                )}

                <div className="toolbar-zoom-controls">
                    <button className="toolbar-btn" onClick={handleZoomOut} title="Zoom Out">
                        <ZoomOut size={16} />
                    </button>
                    <button className="toolbar-btn" onClick={handleZoomIn} title="Zoom In">
                        <ZoomIn size={16} />
                    </button>
                    <button className="toolbar-btn" onClick={handleFitAll} title="Fit All">
                        <Maximize size={16} />
                    </button>
                    <button className="toolbar-btn" onClick={handleReset} title="Reset to 100%">
                        <RotateCcw size={14} />
                    </button>
                </div>
            </div>

            {/* Center: Group By selector */}
            <div className="toolbar-section">
                <div className="toolbar-group-by">
                    <Layers size={14} className="toolbar-icon" />
                    <div className="pill-group">
                        {[
                            { key: 'scene_order', label: 'Scene Order' },
                            { key: 'location', label: 'Location' },
                            { key: 'story_day', label: 'Story Day' },
                        ].map(opt => (
                            <button
                                key={opt.key}
                                className={`pill-btn ${groupBy === opt.key ? 'active' : ''}`}
                                onClick={() => dispatch({ type: 'SET_GROUP_BY', payload: opt.key })}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Right: Inline filters */}
            <div className="toolbar-section toolbar-filters">
                <Filter size={14} className="toolbar-icon" />
                {activeFilterCount > 0 && (
                    <span className="filter-badge">{activeFilterCount}</span>
                )}

                <select
                    className="toolbar-select"
                    value={filters.intExt || 'all'}
                    onChange={(e) => dispatch({ type: 'SET_FILTER', payload: { intExt: e.target.value } })}
                >
                    <option value="all">All I/E</option>
                    <option value="INT">INT</option>
                    <option value="EXT">EXT</option>
                </select>

                <select
                    className="toolbar-select"
                    value={filters.timeOfDay || 'all'}
                    onChange={(e) => dispatch({ type: 'SET_FILTER', payload: { timeOfDay: e.target.value } })}
                >
                    <option value="all">All Times</option>
                    <option value="DAY">DAY</option>
                    <option value="NIGHT">NIGHT</option>
                    <option value="DAWN">DAWN</option>
                    <option value="DUSK">DUSK</option>
                </select>

                {uniqueDays.length > 0 && (
                    <select
                        className="toolbar-select"
                        value={filters.storyDay || 'all'}
                        onChange={(e) => dispatch({ type: 'SET_FILTER', payload: { storyDay: e.target.value } })}
                    >
                        <option value="all">All Days</option>
                        {uniqueDays.map(d => (
                            <option key={d.day} value={d.day}>
                                {d.label} ({d.count})
                            </option>
                        ))}
                    </select>
                )}

                {uniqueCharacters && uniqueCharacters.length > 0 && (
                    <select
                        className="toolbar-select"
                        value={filters.character || 'all'}
                        onChange={(e) => dispatch({ type: 'SET_FILTER', payload: { character: e.target.value } })}
                    >
                        <option value="all">All Characters</option>
                        {uniqueCharacters.map(c => (
                            <option key={c.name} value={c.name}>
                                {c.name} ({c.count})
                            </option>
                        ))}
                    </select>
                )}

                <select
                    className="toolbar-select"
                    value={filters.scheduledStatus || 'all'}
                    onChange={(e) => dispatch({ type: 'SET_FILTER', payload: { scheduledStatus: e.target.value } })}
                >
                    <option value="all">All Scenes</option>
                    <option value="unscheduled">Unscheduled</option>
                    <option value="scheduled">Scheduled</option>
                </select>

                {activeFilterCount > 0 && (
                    <button
                        className="toolbar-btn clear-btn"
                        onClick={() => dispatch({ type: 'CLEAR_FILTERS' })}
                        title="Clear all filters"
                    >
                        Clear
                    </button>
                )}

                <span className="toolbar-scene-count">
                    {totalVisible === totalScenes
                        ? `${totalScenes} scenes`
                        : `${totalVisible} / ${totalScenes} scenes`
                    }
                </span>
            </div>
        </div>
    );
};

export default BoardToolbar;
