import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Trash2,
    ChevronDown,
    ChevronUp,
    ChevronRight,
    Sparkles,
    Pencil,
    Check,
    X,
    Layers,
    Plus,
    ExternalLink
} from 'lucide-react';
import './ScriptTable.css';

const EXPANDED_GROUPS_STORAGE_KEY = 'scriptTable.expandedGroups';

function loadExpandedGroups() {
    try {
        const raw = localStorage.getItem(EXPANDED_GROUPS_STORAGE_KEY);
        return raw ? JSON.parse(raw) : {};
    } catch {
        return {};
    }
}

function saveExpandedGroups(state) {
    try {
        localStorage.setItem(EXPANDED_GROUPS_STORAGE_KEY, JSON.stringify(state));
    } catch {
        // best-effort only (e.g. private browsing may block localStorage)
    }
}

function groupScripts(scripts) {
    const seriesMap = new Map();

    for (const script of scripts) {
        if (!script.series_id) continue;
        if (!seriesMap.has(script.series_id)) {
            seriesMap.set(script.series_id, {
                id: script.series_id,
                title: script.series_title,
                seasons: new Map(),
            });
        }
        const series = seriesMap.get(script.series_id);
        if (!series.seasons.has(script.season_id)) {
            series.seasons.set(script.season_id, {
                id: script.season_id,
                seasonNumber: script.season_number,
                title: script.season_title,
                episodes: [],
            });
        }
        series.seasons.get(script.season_id).episodes.push(script);
    }

    return Array.from(seriesMap.values())
        .sort((a, b) => (a.title || '').localeCompare(b.title || ''))
        .map((series) => ({
            ...series,
            seasons: Array.from(series.seasons.values())
                .sort((a, b) => (a.seasonNumber || 0) - (b.seasonNumber || 0))
                .map((season) => ({
                    ...season,
                    episodes: [...season.episodes].sort(
                        (a, b) => (a.episode_number || 0) - (b.episode_number || 0)
                    ),
                })),
        }));
}

const ScriptTable = ({ scripts, onView, onDelete, onRename, onUpdateWriter, onAssignSeries, locationHealthCounts = {} }) => {
    const navigate = useNavigate();
    const [sortConfig, setSortConfig] = useState({ key: 'upload_date', direction: 'desc' });
    const [editingId, setEditingId] = useState(null);
    const [editingField, setEditingField] = useState(null); // 'name' or 'writer'
    const [editValue, setEditValue] = useState('');
    const [expandedGroups, setExpandedGroups] = useState(loadExpandedGroups);
    const inputRef = useRef(null);

    useEffect(() => {
        if (editingId && inputRef.current) {
            inputRef.current.focus();
            inputRef.current.select();
        }
    }, [editingId, editingField]);

    const toggleGroup = (id) => {
        setExpandedGroups((prev) => {
            const next = { ...prev, [id]: !prev[id] };
            saveExpandedGroups(next);
            return next;
        });
    };

    const startEditing = (e, script, field) => {
        e.stopPropagation();
        setEditingId(script.script_id);
        setEditingField(field);
        setEditValue(field === 'writer' ? (script.writer_name || '') : (script.script_name || ''));
    };

    const cancelEditing = (e) => {
        if (e) e.stopPropagation();
        setEditingId(null);
        setEditingField(null);
        setEditValue('');
    };

    const saveEdit = async (e, scriptId) => {
        if (e) e.stopPropagation();
        const trimmed = editValue.trim();
        if (editingField === 'name') {
            if (!trimmed) return cancelEditing();
            if (onRename) await onRename(scriptId, trimmed);
        } else if (editingField === 'writer') {
            if (onUpdateWriter) await onUpdateWriter(scriptId, trimmed || null);
        }
        setEditingId(null);
        setEditingField(null);
        setEditValue('');
    };

    const handleKeyDown = (e, scriptId) => {
        if (e.key === 'Enter') {
            saveEdit(e, scriptId);
        } else if (e.key === 'Escape') {
            cancelEditing(e);
        }
    };

    const handleSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    const sortedUngrouped = scripts
        .filter((s) => !s.series_id)
        .sort((a, b) => {
            if (a[sortConfig.key] < b[sortConfig.key]) {
                return sortConfig.direction === 'asc' ? -1 : 1;
            }
            if (a[sortConfig.key] > b[sortConfig.key]) {
                return sortConfig.direction === 'asc' ? 1 : -1;
            }
            return 0;
        });

    const seriesGroups = groupScripts(scripts);

    const SortIcon = ({ columnKey }) => {
        if (sortConfig.key !== columnKey) return null;
        return sortConfig.direction === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />;
    };

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    };

    const renderScriptRow = (script, indent = 0) => (
        <tr
            key={script.script_id}
            className="clickable-row"
            onClick={() => onView(script.script_id)}
        >
            <td className="name-cell" style={indent ? { paddingLeft: `${1.5 + indent}rem` } : undefined}>
                {editingId === script.script_id && editingField === 'name' ? (
                    <div className="name-edit-row">
                        <input
                            ref={inputRef}
                            className="name-edit-input"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onKeyDown={(e) => handleKeyDown(e, script.script_id)}
                            onClick={(e) => e.stopPropagation()}
                        />
                        <button className="name-edit-btn save" onClick={(e) => saveEdit(e, script.script_id)} title="Save"><Check size={14} /></button>
                        <button className="name-edit-btn cancel" onClick={cancelEditing} title="Cancel"><X size={14} /></button>
                    </div>
                ) : (
                    <div className="script-name-row">
                        {indent > 0 && script.episode_number != null && (
                            <span className="episode-badge">Ep {script.episode_number}</span>
                        )}
                        <div className="script-name">{script.script_name}</div>
                        {locationHealthCounts[script.script_id] > 0 && (
                            <span
                                className="location-health-badge"
                                title={`${locationHealthCounts[script.script_id]} location${locationHealthCounts[script.script_id] === 1 ? '' : 's'} need review`}
                            >
                                ⚠ {locationHealthCounts[script.script_id]}
                            </span>
                        )}
                        <button
                            className="rename-btn"
                            onClick={(e) => startEditing(e, script, 'name')}
                            title="Rename script"
                        >
                            <Pencil size={13} />
                        </button>
                    </div>
                )}
            </td>
            <td className="writer-cell">
                {editingId === script.script_id && editingField === 'writer' ? (
                    <div className="name-edit-row">
                        <input
                            ref={inputRef}
                            className="name-edit-input writer-edit-input"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onKeyDown={(e) => handleKeyDown(e, script.script_id)}
                            onClick={(e) => e.stopPropagation()}
                            placeholder="Writer name"
                        />
                        <button className="name-edit-btn save" onClick={(e) => saveEdit(e, script.script_id)} title="Save"><Check size={14} /></button>
                        <button className="name-edit-btn cancel" onClick={cancelEditing} title="Cancel"><X size={14} /></button>
                    </div>
                ) : (
                    <div className="script-name-row">
                        <span className="writer-name">{script.writer_name || '—'}</span>
                        <button
                            className="rename-btn"
                            onClick={(e) => startEditing(e, script, 'writer')}
                            title="Edit writer"
                        >
                            <Pencil size={13} />
                        </button>
                    </div>
                )}
            </td>
            <td className="date-cell">
                {formatDate(script.upload_date)}
            </td>
            <td className="scenes-cell">
                <span className="scene-count-badge">{script.scene_count}</span>
            </td>
            <td className="analysis-cell">
                <span className="analysis-progress">
                    {script.analyzed_scenes || 0}/{script.scene_count || 0} scenes
                </span>
            </td>
            <td className="actions-cell">
                {onAssignSeries && (
                    <button
                        className="action-icon-btn"
                        onClick={(e) => {
                            e.stopPropagation();
                            onAssignSeries(script);
                        }}
                        title={script.episode_number ? `Episode ${script.episode_number} of a series` : 'Assign to a series'}
                    >
                        <Layers size={18} />
                    </button>
                )}
                <button
                    className="action-icon-btn danger"
                    onClick={(e) => {
                        e.stopPropagation();
                        onDelete(script.script_id, script.script_name);
                    }}
                    title="Delete Script"
                >
                    <Trash2 size={18} />
                </button>
            </td>
        </tr>
    );

    return (
        <div className="table-container">
            <table className="script-table">
                <thead>
                    <tr>
                        <th onClick={() => handleSort('script_name')}>
                            <div className="th-content">Script Name <SortIcon columnKey="script_name" /></div>
                        </th>
                        <th onClick={() => handleSort('writer_name')}>
                            <div className="th-content">Writer <SortIcon columnKey="writer_name" /></div>
                        </th>
                        <th onClick={() => handleSort('upload_date')}>
                            <div className="th-content">Date Uploaded <SortIcon columnKey="upload_date" /></div>
                        </th>
                        <th onClick={() => handleSort('scene_count')}>
                            <div className="th-content">Scenes <SortIcon columnKey="scene_count" /></div>
                        </th>
                        <th>
                            <div className="th-content">
                                <Sparkles size={14} />
                                AI Analysis
                            </div>
                        </th>
                        <th className="actions-col">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {seriesGroups.map((series) => {
                        const seriesExpanded = !!expandedGroups[series.id];
                        const totalEpisodes = series.seasons.reduce((sum, s) => sum + s.episodes.length, 0);
                        return (
                            <React.Fragment key={series.id}>
                                <tr className="group-header-row series-header-row" onClick={() => toggleGroup(series.id)}>
                                    <td colSpan={6}>
                                        <div className="group-header-content">
                                            {seriesExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                            <span className="group-title">{series.title || 'Untitled Series'}</span>
                                            <span className="group-count">{totalEpisodes} episode{totalEpisodes === 1 ? '' : 's'}</span>
                                            <button
                                                className="group-header-link"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    navigate(`/series/${series.id}`);
                                                }}
                                                title="View series"
                                            >
                                                <ExternalLink size={14} />
                                                View series
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                                {seriesExpanded && series.seasons.map((season) => {
                                    const seasonExpanded = !!expandedGroups[season.id];
                                    return (
                                        <React.Fragment key={season.id}>
                                            <tr className="group-header-row season-header-row" onClick={() => toggleGroup(season.id)}>
                                                <td colSpan={6}>
                                                    <div className="group-header-content indent-1">
                                                        {seasonExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                                        <span className="group-title">{season.title || `Season ${season.seasonNumber}`}</span>
                                                        <span className="group-count">{season.episodes.length} episode{season.episodes.length === 1 ? '' : 's'}</span>
                                                        <button
                                                            className="group-header-link"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                navigate(`/upload?seriesId=${series.id}&seasonId=${season.id}`);
                                                            }}
                                                            title="Add the next episode to this season"
                                                        >
                                                            <Plus size={14} />
                                                            Add episode
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                            {seasonExpanded && season.episodes.map((script) => renderScriptRow(script, 2))}
                                        </React.Fragment>
                                    );
                                })}
                            </React.Fragment>
                        );
                    })}
                    {sortedUngrouped.map((script) => renderScriptRow(script, 0))}
                </tbody>
            </table>
        </div>
    );
};

export default ScriptTable;
