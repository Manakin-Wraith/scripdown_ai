import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Plus, CalendarDays, Trash2, Pencil, Check, X, ZoomIn, ZoomOut, Maximize, RotateCcw, FileText } from 'lucide-react';
import { Spinner, EmptyState } from '../ui';
import { useToast } from '../../context/ToastContext';
import { useConfirmDialog } from '../../context/ConfirmDialogContext';
import { useScript } from '../../context/ScriptContext';
import {
    getSchedules, createSchedule, getShootingDays,
    getScriptMetadata, deleteSchedule, updateSchedule,
} from '../../services/apiService';
import ScheduleKanban from './ScheduleKanban';
import ConflictPanel from './ConflictPanel';
import './ShootingSchedule.css';

const ShootingSchedulePage = () => {
    const { scriptId } = useParams();
    const navigate = useNavigate();
    const toast = useToast();
    const { confirm } = useConfirmDialog();
    const { setScript } = useScript();

    const [schedules, setSchedules] = useState([]);
    const [activeScheduleId, setActiveScheduleId] = useState(null);
    const [conflictDayIds, setConflictDayIds] = useState(new Set());
    const [conflictScenes, setConflictScenes] = useState(new Map());
    const [acknowledgedScenes, setAcknowledgedScenes] = useState(new Map());
    const [expandedConflictKey, setExpandedConflictKey] = useState(null);
    const [days, setDays] = useState([]);
    const [loading, setLoading] = useState(true);
    const [metadata, setMetadata] = useState(null);
    const [editingScheduleId, setEditingScheduleId] = useState(null);
    const [editingScheduleName, setEditingScheduleName] = useState('');
    const [genMenuOpen, setGenMenuOpen] = useState(false);
    const scheduleNameInputRef = useRef(null);
    const zoomApiRef = useRef(null);

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

    const handleResolve = useCallback((dayId, characterName) => {
        setExpandedConflictKey(`${dayId}:${characterName}`);
        document.querySelector('.conflict-panel')?.scrollIntoView({
            behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
            block: 'nearest',
        });
    }, []);

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
        const ok = await confirm({
            title: 'Delete Schedule?',
            message: `"${sched?.name || 'This schedule'}" and all its shooting days will be permanently deleted.`,
            variant: 'danger'
        });
        if (!ok) return;
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

    if (loading) {
        return (
            <div className="schedule-page">
                <div className="schedule-loading">
                    <Spinner size={32} />
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
                    <div className="schedule-title-group">
                        <span className="schedule-script-name">{metadata?.title || 'Untitled'}</span>
                    </div>
                </div>

                <div className="schedule-header-right">
                    {activeScheduleId && days.length > 0 && (
                        <div className="schedule-gen-wrapper">
                            <button
                                className="schedule-print-btn"
                                onClick={() => setGenMenuOpen((o) => !o)}
                                title="Generate a report from this schedule"
                            >
                                <FileText size={14} /> Generate ▾
                            </button>
                            {genMenuOpen && (
                                <div className="schedule-gen-menu" onMouseLeave={() => setGenMenuOpen(false)}>
                                    {[
                                        ['one_liner', 'One-Liner / Stripboard'],
                                        ['day_out_of_days', 'Day Out of Days'],
                                        ['shooting_schedule', 'Shooting Schedule'],
                                    ].map(([type, label]) => (
                                        <button
                                            key={type}
                                            className="schedule-gen-item"
                                            onClick={() => {
                                                setGenMenuOpen(false);
                                                navigate(`/scripts/${scriptId}/reports?type=${type}&schedule=${activeScheduleId}`);
                                            }}
                                        >
                                            {label}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
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

            <ConflictPanel
                scriptId={scriptId}
                scheduleId={activeScheduleId}
                days={days}
                onConflictDays={setConflictDayIds}
                onConflictScenes={setConflictScenes}
                onAcknowledgedScenes={setAcknowledgedScenes}
                expandedKey={expandedConflictKey}
                onExpandedKeyChange={setExpandedConflictKey}
                refreshDays={refreshDays}
            />

            {/* Kanban body */}
            {activeScheduleId ? (
                <ScheduleKanban
                    scheduleId={activeScheduleId}
                    days={days}
                    refreshDays={refreshDays}
                    zoomApiRef={zoomApiRef}
                    conflictDayIds={conflictDayIds}
                    conflictScenes={conflictScenes}
                    acknowledgedScenes={acknowledgedScenes}
                    onResolve={handleResolve}
                />
            ) : (
                <EmptyState
                    icon={CalendarDays}
                    title="No schedules yet"
                    message='Go to the Board, select scenes, and click "Schedule" to start building your shooting days.'
                    action={
                        <button className="schedule-create-btn" onClick={handleCreateSchedule}>
                            <Plus size={16} /> Create Schedule
                        </button>
                    }
                />
            )}
        </div>
    );
};

export default ShootingSchedulePage;
