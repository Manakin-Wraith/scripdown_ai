import React, { useState } from 'react';
import { 
    Trash2, 
    ChevronDown,
    ChevronUp,
    Sparkles
} from 'lucide-react';
import AnalysisStatusBadge from '../common/AnalysisStatusBadge';
import './ScriptTable.css';

const ScriptTable = ({ scripts, onView, onDelete }) => {
    const [sortConfig, setSortConfig] = useState({ key: 'upload_date', direction: 'desc' });

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
                                <div className="script-name">{script.script_name}</div>
                            </td>
                            <td className="writer-cell">
                                <span className="writer-name">{script.writer_name || '—'}</span>
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
