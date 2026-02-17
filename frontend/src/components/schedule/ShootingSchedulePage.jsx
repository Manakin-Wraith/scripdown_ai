import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader, Plus, CalendarDays, Trash2 } from 'lucide-react';
import ViewSwitcher from '../shared/ViewSwitcher';
import { useToast } from '../../context/ToastContext';
import { useScript } from '../../context/ScriptContext';
import {
    getSchedules, createSchedule, getShootingDays,
    getScriptMetadata, deleteSchedule,
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
                    {/* Schedule tabs */}
                    <div className="schedule-tabs">
                        {schedules.map(sched => (
                            <div key={sched.id} className={`schedule-tab-wrapper ${sched.id === activeScheduleId ? 'active' : ''}`}>
                                <button
                                    className={`schedule-tab ${sched.id === activeScheduleId ? 'active' : ''}`}
                                    onClick={() => setActiveScheduleId(sched.id)}
                                >
                                    {sched.name}
                                </button>
                                {sched.id === activeScheduleId && (
                                    <button
                                        className="schedule-tab-delete"
                                        onClick={() => handleDeleteSchedule(sched.id)}
                                        title="Delete this schedule"
                                    >
                                        <Trash2 size={12} />
                                    </button>
                                )}
                            </div>
                        ))}
                        <button className="schedule-tab schedule-tab-add" onClick={handleCreateSchedule} title="New schedule">
                            <Plus size={14} />
                        </button>
                    </div>
                </div>
            </div>

            {/* Kanban body */}
            {activeScheduleId ? (
                <ScheduleKanban
                    scheduleId={activeScheduleId}
                    days={days}
                    refreshDays={refreshDays}
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
