import React, { useState, useEffect, useRef } from 'react';
import { CalendarPlus, Plus, ChevronDown, Check, Loader2 } from 'lucide-react';
import { getSchedules, getShootingDays, quickAddToSchedule } from '../../services/apiService';
import './SchedulePopover.css';

const SchedulePopover = ({ scriptId, selectedSceneIds, onSuccess, onClose }) => {
    const [schedules, setSchedules] = useState([]);
    const [expandedSchedule, setExpandedSchedule] = useState(null);
    const [days, setDays] = useState([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [result, setResult] = useState(null);
    const popoverRef = useRef(null);

    // Close on outside click
    useEffect(() => {
        const handleClick = (e) => {
            if (popoverRef.current && !popoverRef.current.contains(e.target)) {
                onClose();
            }
        };
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [onClose]);

    // Fetch schedules on mount
    useEffect(() => {
        const fetch = async () => {
            try {
                const data = await getSchedules(scriptId);
                setSchedules(data.schedules || []);
            } catch (err) {
                console.error('Failed to fetch schedules:', err);
            } finally {
                setLoading(false);
            }
        };
        fetch();
    }, [scriptId]);

    // Fetch days when a schedule is expanded
    useEffect(() => {
        if (!expandedSchedule) { setDays([]); return; }
        const fetch = async () => {
            try {
                const data = await getShootingDays(expandedSchedule);
                setDays(data.days || []);
            } catch (err) {
                console.error('Failed to fetch days:', err);
            }
        };
        fetch();
    }, [expandedSchedule]);

    const handleQuickAdd = async (scheduleId = null, dayId = null) => {
        setSubmitting(true);
        setResult(null);
        try {
            const res = await quickAddToSchedule(scriptId, selectedSceneIds, scheduleId, dayId);
            setResult(res);
            setTimeout(() => {
                onSuccess(res);
            }, 800);
        } catch (err) {
            console.error('Failed to add to schedule:', err);
            setResult({ error: err.message || 'Failed to add' });
            setSubmitting(false);
        }
    };

    const count = selectedSceneIds.length;

    if (result && !result.error) {
        return (
            <div className="schedule-popover" ref={popoverRef}>
                <div className="sp-success">
                    <Check size={20} />
                    <span>Added {result.added_count} scene{result.added_count !== 1 ? 's' : ''} to schedule</span>
                    {result.skipped_count > 0 && (
                        <span className="sp-skipped">({result.skipped_count} already scheduled)</span>
                    )}
                </div>
            </div>
        );
    }

    return (
        <div className="schedule-popover" ref={popoverRef}>
            <div className="sp-header">
                <CalendarPlus size={16} />
                <span>Add {count} scene{count !== 1 ? 's' : ''} to schedule</span>
            </div>

            {loading ? (
                <div className="sp-loading"><Loader2 size={16} className="sp-spin" /> Loading...</div>
            ) : (
                <div className="sp-body">
                    {/* Quick action: New schedule + new day */}
                    <button
                        className="sp-option sp-new"
                        onClick={() => handleQuickAdd(null, null)}
                        disabled={submitting}
                    >
                        <Plus size={14} />
                        <span>New Schedule &amp; New Day</span>
                        {submitting && <Loader2 size={14} className="sp-spin" />}
                    </button>

                    {/* Existing schedules */}
                    {schedules.map(sched => (
                        <div key={sched.id} className="sp-schedule-group">
                            <button
                                className="sp-option sp-schedule"
                                onClick={() => setExpandedSchedule(
                                    expandedSchedule === sched.id ? null : sched.id
                                )}
                            >
                                <ChevronDown
                                    size={14}
                                    className={`sp-chevron ${expandedSchedule === sched.id ? 'open' : ''}`}
                                />
                                <span>{sched.name}</span>
                                <span className="sp-badge">{sched.status}</span>
                            </button>

                            {expandedSchedule === sched.id && (
                                <div className="sp-days">
                                    {/* Add to new day in this schedule */}
                                    <button
                                        className="sp-option sp-day-new"
                                        onClick={() => handleQuickAdd(sched.id, null)}
                                        disabled={submitting}
                                    >
                                        <Plus size={12} />
                                        <span>New Day</span>
                                    </button>

                                    {days.map(day => (
                                        <button
                                            key={day.id}
                                            className="sp-option sp-day"
                                            onClick={() => handleQuickAdd(sched.id, day.id)}
                                            disabled={submitting}
                                        >
                                            <span className="sp-day-num">Day {day.day_number}</span>
                                            <span className="sp-day-count">
                                                {day.scenes?.length || 0} scene{(day.scenes?.length || 0) !== 1 ? 's' : ''}
                                            </span>
                                        </button>
                                    ))}

                                    {days.length === 0 && (
                                        <div className="sp-empty">No days yet</div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}

                    {schedules.length === 0 && (
                        <div className="sp-empty-msg">No schedules yet. Click above to create one.</div>
                    )}
                </div>
            )}
        </div>
    );
};

export default SchedulePopover;
