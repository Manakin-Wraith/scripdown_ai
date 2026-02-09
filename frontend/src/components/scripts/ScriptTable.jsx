import React, { useState, useRef, useEffect } from 'react';
import { 
    Trash2, 
    ChevronDown,
    ChevronUp,
    Sparkles,
    Pencil,
    Check,
    X
} from 'lucide-react';
import AnalysisStatusBadge from '../common/AnalysisStatusBadge';
import './ScriptTable.css';

const ScriptTable = ({ scripts, onView, onDelete, onRename, onUpdateWriter }) => {
    const [sortConfig, setSortConfig] = useState({ key: 'upload_date', direction: 'desc' });
    const [editingId, setEditingId] = useState(null);
    const [editingField, setEditingField] = useState(null); // 'name' or 'writer'
    const [editValue, setEditValue] = useState('');
    const inputRef = useRef(null);

    useEffect(() => {
        if (editingId && inputRef.current) {
            inputRef.current.focus();
            inputRef.current.select();
        }
    }, [editingId, editingField]);

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

    const sortedScripts = [...scripts].sort((a, b) => {
        if (a[sortConfig.key] < b[sortConfig.key]) {
            return sortConfig.direction === 'asc' ? -1 : 1;
        }
        if (a[sortConfig.key] > b[sortConfig.key]) {
            return sortConfig.direction === 'asc' ? 1 : -1;
        }
        return 0;
    });

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
                    {sortedScripts.map((script) => (
                        <tr 
                            key={script.script_id}
                            className="clickable-row"
                            onClick={() => onView(script.script_id)}
                        >
                            <td className="name-cell">
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
                                        <div className="script-name">{script.script_name}</div>
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
                                <button 
                                    className="action-icon-btn danger"
                                    onClick={(e) => {
                                        e.stopPropagation(); // Prevent row click
                                        onDelete(script.script_id, script.script_name);
                                    }}
                                    title="Delete Script"
                                >
                                    <Trash2 size={18} />
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default ScriptTable;
