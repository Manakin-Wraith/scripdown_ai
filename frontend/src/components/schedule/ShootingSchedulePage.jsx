import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader, Plus, CalendarDays, Trash2, Pencil, Check, X, ZoomIn, ZoomOut, Maximize, RotateCcw, Printer } from 'lucide-react';
import SchedulePrintView from './SchedulePrintView';
import ViewSwitcher from '../shared/ViewSwitcher';
import { useToast } from '../../context/ToastContext';
import { useScript } from '../../context/ScriptContext';
import {
    getSchedules, createSchedule, getShootingDays,
    getScriptMetadata, deleteSchedule, updateSchedule,
} from '../../services/apiService';
import ScheduleKanban from './ScheduleKanban';
import './ShootingSchedule.css';

const ShootingSchedulePage = () => {
    const { scriptId } = useParams();
    const navigate = useNavigate();
    const toast = useToast();
    const { setScript } = useScript();

    const [schedules, setSchedules] = useState([]);
    const [activeScheduleId, setActiveScheduleId] = useState(null);
    const [days, setDays] = useState([]);
    const [loading, setLoading] = useState(true);
    const [metadata, setMetadata] = useState(null);
    const [editingScheduleId, setEditingScheduleId] = useState(null);
    const [editingScheduleName, setEditingScheduleName] = useState('');
    const [showPrintPreview, setShowPrintPreview] = useState(false);
    const scheduleNameInputRef = useRef(null);
    const zoomApiRef = useRef(null);

    // Lock body scroll when print preview is open
    useEffect(() => {
        document.body.style.overflow = showPrintPreview ? 'hidden' : '';
        return () => { document.body.style.overflow = ''; };
    }, [showPrintPreview]);

    // Load schedules + script metadata
    useEffect(() => {
        const load = async () => {
            try {
                const [schedData, metaData] = await Promise.all([
                    getSchedules(scriptId),
                    getScriptMetadata(scriptId),
                ]);
                setMetadata(metaData);
                if (metaData) setScript(metaData);

                const scheds = schedData.schedules || [];
                setSchedules(scheds);
                if (scheds.length > 0) {
                    setActiveScheduleId(scheds[0].id);
                }
            } catch (err) {
                console.error('Failed to load schedules:', err);
                toast.error('Error', 'Failed to load shooting schedules');
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [scriptId]);

    // Load days when active schedule changes
    useEffect(() => {
        if (!activeScheduleId) { setDays([]); return; }
        const loadDays = async () => {
            try {
                const data = await getShootingDays(activeScheduleId);
                setDays(data.days || []);
            } catch (err) {
                console.error('Failed to load days:', err);
            }
        };
        loadDays();
    }, [activeScheduleId]);

    const refreshDays = useCallback(async () => {
        if (!activeScheduleId) return;
        try {
            const data = await getShootingDays(activeScheduleId);
            setDays(data.days || []);
        } catch (err) {
            console.error('Failed to refresh days:', err);
        }
    }, [activeScheduleId]);

    // Keyboard shortcuts for zoom
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            if (e.key === '=' || e.key === '+') zoomApiRef.current?.zoomIn(0.3);
            if (e.key === '-') zoomApiRef.current?.zoomOut(0.3);
            if (e.key === '0') zoomApiRef.current?.setTransform(0, 0, 1);
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    const handleCreateSchedule = async () => {
        try {
            const name = `Schedule ${schedules.length + 1}`;
            const data = await createSchedule(scriptId, name);
            const newSched = data.schedule;
            setSchedules(prev => [...prev, newSched]);
            setActiveScheduleId(newSched.id);
            toast.success('Created', `${name} created`);
        } catch (err) {
            toast.error('Error', 'Failed to create schedule');
        }
    };

    const handleDeleteSchedule = async (schedId) => {
        const sched = schedules.find(s => s.id === schedId);
        if (!window.confirm(`Delete "${sched?.name || 'this schedule'}" and all its shooting days? This cannot be undone.`)) return;
        try {
            await deleteSchedule(schedId);
            const remaining = schedules.filter(s => s.id !== schedId);
            setSchedules(remaining);
            setActiveScheduleId(remaining.length > 0 ? remaining[0].id : null);
            toast.success('Deleted', `${sched?.name} deleted`);
        } catch (err) {
            toast.error('Error', 'Failed to delete schedule');
        }
    };

    const startEditingScheduleName = (sched, e) => {
        e.stopPropagation();
        setEditingScheduleId(sched.id);
        setEditingScheduleName(sched.name);
        setTimeout(() => scheduleNameInputRef.current?.select(), 0);
    };

    const commitScheduleRename = async () => {
        const trimmed = editingScheduleName.trim();
        if (!trimmed || !editingScheduleId) { cancelScheduleRename(); return; }
        const sched = schedules.find(s => s.id === editingScheduleId);
        if (sched?.name === trimmed) { cancelScheduleRename(); return; }
        try {
            await updateSchedule(editingScheduleId, { name: trimmed });
            setSchedules(prev => prev.map(s => s.id === editingScheduleId ? { ...s, name: trimmed } : s));
            toast.success('Renamed', `Schedule renamed to "${trimmed}"`);
        } catch (err) {
            toast.error('Error', 'Failed to rename schedule');
        }
        setEditingScheduleId(null);
    };

    const cancelScheduleRename = () => {
        setEditingScheduleId(null);
        setEditingScheduleName('');
    };

    const activeSchedule = schedules.find(s => s.id === activeScheduleId);

    if (loading) {
        return (
            <div className="schedule-page">
                <div className="schedule-loading">
                    <Loader className="spin" size={32} />
                    <p>Loading schedule...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="schedule-page">
            {/* Header */}
            <div className="schedule-header">
                <div className="schedule-header-left">
                    <ViewSwitcher scriptId={scriptId} />
                    <div className="schedule-title-group">
                        <span className="schedule-script-name">{metadata?.title || 'Untitled'}</span>
                    </div>
                </div>

                <div className="schedule-header-right">
                    {/* Print / Export button */}
                    {activeScheduleId && days.length > 0 && (
                        <button
                            className="schedule-print-btn"
                            onClick={() => setShowPrintPreview(true)}
                            title="Print / Export PDF"
                        >
                            <Printer size={14} />
                            Print / Export
                        </button>
                    )}

                    {/* Zoom controls */}
                    <div className="schedule-zoom-controls">
                        <button className="schedule-zoom-btn" onClick={() => zoomApiRef.current?.zoomOut(0.3)} title="Zoom Out">
                            <ZoomOut size={15} />
                        </button>
                        <button className="schedule-zoom-btn" onClick={() => zoomApiRef.current?.zoomIn(0.3)} title="Zoom In">
                            <ZoomIn size={15} />
                        </button>
                        <button className="schedule-zoom-btn" onClick={() => zoomApiRef.current?.resetTransform()} title="Fit">
                            <Maximize size={14} />
                        </button>
                        <button className="schedule-zoom-btn" onClick={() => zoomApiRef.current?.setTransform(0, 0, 1)} title="Reset to 100%">
                            <RotateCcw size={13} />
                        </button>
                    </div>

                    {/* Schedule tabs */}
                    <div className="schedule-tabs">
                        {schedules.map(sched => (
                            <div key={sched.id} className={`schedule-tab-wrapper ${sched.id === activeScheduleId ? 'active' : ''}`}>
                                {editingScheduleId === sched.id ? (
                                    <div className="schedule-tab-edit">
                                        <input
                                            ref={scheduleNameInputRef}
                                            className="schedule-tab-input"
                                            value={editingScheduleName}
                                            onChange={e => setEditingScheduleName(e.target.value)}
                                            onKeyDown={e => {
                                                if (e.key === 'Enter') commitScheduleRename();
                                                if (e.key === 'Escape') cancelScheduleRename();
                                            }}
                                            onBlur={commitScheduleRename}
                                            autoFocus
                                        />
                                        <button className="schedule-tab-confirm" onClick={commitScheduleRename} title="Save">
                                            <Check size={12} />
                                        </button>
                                        <button className="schedule-tab-cancel" onClick={cancelScheduleRename} title="Cancel">
                                            <X size={12} />
                                        </button>
                                    </div>
                                ) : (
                                    <button
                                        className={`schedule-tab ${sched.id === activeScheduleId ? 'active' : ''}`}
                                        onClick={() => setActiveScheduleId(sched.id)}
                                        onDoubleClick={e => startEditingScheduleName(sched, e)}
                                        title="Double-click to rename"
                                    >
                                        {sched.name}
                                    </button>
                                )}
                                {sched.id === activeScheduleId && editingScheduleId !== sched.id && (
                                    <>
                                        <button
                                            className="schedule-tab-rename"
                                            onClick={e => startEditingScheduleName(sched, e)}
                                            title="Rename schedule"
                                        >
                                            <Pencil size={11} />
                                        </button>
                                        <button
                                            className="schedule-tab-delete"
                                            onClick={() => handleDeleteSchedule(sched.id)}
                                            title="Delete this schedule"
                                        >
                                            <Trash2 size={12} />
                                        </button>
                                    </>
                                )}
                            </div>
                        ))}
                        <button className="schedule-tab schedule-tab-add" onClick={handleCreateSchedule} title="New schedule">
                            <Plus size={14} />
                        </button>
                    </div>
                </div>
            </div>

            {/* Print Preview Modal */}
            {showPrintPreview && (
                <div className="print-preview-overlay" onClick={(e) => { if (e.target === e.currentTarget) setShowPrintPreview(false); }}>
                    <div className="print-preview-toolbar">
                        <span className="print-preview-toolbar-title">
                            {metadata?.title || 'Untitled'} — {activeSchedule?.name || 'Schedule'}
                        </span>
                        <button
                            className="print-action-btn primary"
                            onClick={() => {
                                const printContent = document.getElementById('schedule-print-view');
                                if (!printContent) return;
                                const clone = printContent.cloneNode(true);
                                clone.id = 'schedule-print-clone';
                                clone.style.display = 'block';
                                document.body.appendChild(clone);
                                document.body.classList.add('printing-schedule');
                                window.print();
                                document.body.removeChild(clone);
                                document.body.classList.remove('printing-schedule');
                            }}
                        >
                            <Printer size={13} /> Print / Save PDF
                        </button>
                        <button
                            className="print-action-btn secondary"
                            onClick={() => setShowPrintPreview(false)}
                        >
                            <X size={13} /> Close
                        </button>
                    </div>

                    <div className="print-preview-paper">
                        <SchedulePrintView
                            days={days}
                            scheduleName={activeSchedule?.name}
                            metadata={metadata}
                        />
                    </div>
                </div>
            )}

            {/* Kanban body */}
            {activeScheduleId ? (
                <ScheduleKanban
                    scheduleId={activeScheduleId}
                    days={days}
                    refreshDays={refreshDays}
                    zoomApiRef={zoomApiRef}
                />
            ) : (
                <div className="schedule-empty">
                    <CalendarDays size={48} />
                    <h2>No schedules yet</h2>
                    <p>Go to the Board, select scenes, and click "Schedule" to start building your shooting days.</p>
                    <button className="schedule-create-btn" onClick={handleCreateSchedule}>
                        <Plus size={16} /> Create Schedule
                    </button>
                </div>
            )}
        </div>
    );
};

export default ShootingSchedulePage;
