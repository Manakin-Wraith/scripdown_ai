import React from 'react';
import { reportIcon } from './reportIcons';
import ReportFilterPanel from './ReportFilterPanel';
import './ReportRail.css';

const ReportRail = ({
    reportTypes,
    selectedType,
    onSelectType,
    customTitle,
    onTitleChange,
    filterPanelProps,
    schedules = [],
    scheduleId = null,
    onScheduleChange,
}) => {
    return (
        <div className="report-rail">
            <div className="rail-section">
                <span className="rail-label">Report type</span>
                <div className="rail-type-list">
                    {Object.entries(reportTypes || {}).map(([type, info]) => {
                        const Icon = reportIcon(type);
                        return (
                            <button
                                key={type}
                                className={`rail-type ${selectedType === type ? 'on' : ''}`}
                                onClick={() => onSelectType(type)}
                                title={info.description}
                            >
                                <Icon size={16} />
                                <span>{info.name}</span>
                            </button>
                        );
                    })}
                </div>
            </div>

            {reportTypes?.[selectedType]?.requires_schedule && (
                <div className="rail-section">
                    <span className="rail-label">Source schedule</span>
                    <select
                        className="rail-title-input"
                        value={scheduleId || ''}
                        onChange={(e) => onScheduleChange?.(e.target.value || null)}
                    >
                        <option value="">— Select a schedule —</option>
                        {schedules.map((s) => (
                            <option key={s.id} value={s.id}>{s.name}</option>
                        ))}
                    </select>
                </div>
            )}

            <div className="rail-section rail-filters">
                <ReportFilterPanel {...filterPanelProps} isCollapsed={false} />
            </div>

            <div className="rail-section">
                <label className="rail-label" htmlFor="report-title">Title (optional)</label>
                <input
                    id="report-title"
                    type="text"
                    className="rail-title-input"
                    value={customTitle}
                    onChange={(e) => onTitleChange(e.target.value)}
                    placeholder="e.g. Week 1 — Interiors"
                />
            </div>
        </div>
    );
};

export default ReportRail;
