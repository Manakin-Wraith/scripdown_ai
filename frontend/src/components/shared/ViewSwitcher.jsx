import React from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { LayoutGrid, CalendarDays, List, ArrowLeft } from 'lucide-react';
import './ViewSwitcher.css';

const VIEWS = [
    { key: 'board', label: 'Board', icon: LayoutGrid, path: (id) => `/scripts/${id}/board` },
    { key: 'schedule', label: 'Schedule', icon: CalendarDays, path: (id) => `/scripts/${id}/schedule` },
];

const ViewSwitcher = ({ scriptId }) => {
    const navigate = useNavigate();
    const location = useLocation();

    const activeView = location.pathname.includes('/schedule') ? 'schedule'
        : location.pathname.includes('/board') ? 'board'
        : null;

    return (
        <div className="view-switcher">
            <button
                className="vs-back"
                onClick={() => navigate(`/scenes/${scriptId}`)}
                title="Back to script"
            >
                <ArrowLeft size={16} />
            </button>
            <div className="vs-pills">
                {VIEWS.map(v => {
                    const Icon = v.icon;
                    const isActive = activeView === v.key;
                    return (
                        <button
                            key={v.key}
                            className={`vs-pill ${isActive ? 'active' : ''}`}
                            onClick={() => !isActive && navigate(v.path(scriptId))}
                        >
                            <Icon size={14} />
                            <span>{v.label}</span>
                        </button>
                    );
                })}
            </div>
        </div>
    );
};

export default ViewSwitcher;
