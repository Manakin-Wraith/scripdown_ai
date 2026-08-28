// frontend/src/components/schedule/ConflictPanel.jsx
import { useEffect, useState } from 'react';
import { TriangleAlert, ChevronDown, ChevronRight } from 'lucide-react';
import { getCastingConflicts } from '../../services/apiService';
import './ConflictPanel.css';

export default function ConflictPanel({ scriptId, scheduleId, onConflictDays }) {
    const [conflicts, setConflicts] = useState([]);
    const [open, setOpen] = useState(true);

    useEffect(() => {
        let cancelled = false;
        if (!scheduleId) { setConflicts([]); onConflictDays?.(new Set()); return; }
        getCastingConflicts(scriptId, scheduleId)
            .then((data) => {
                if (cancelled) return;
                setConflicts(data.conflicts || []);
                onConflictDays?.(new Set((data.conflicts || []).map((c) => c.shooting_day_id)));
            })
            .catch(() => { if (!cancelled) { setConflicts([]); onConflictDays?.(new Set()); } });
        return () => { cancelled = true; };
    }, [scriptId, scheduleId, onConflictDays]);

    if (conflicts.length === 0) return null;

    return (
        <div className="conflict-panel">
            <button className="conflict-panel-head" onClick={() => setOpen((o) => !o)}>
                {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                <TriangleAlert size={14} />
                Availability conflicts ({conflicts.length})
            </button>
            {open && (
                <ul className="conflict-panel-list">
                    {conflicts.map((c) => (
                        <li key={`${c.shooting_day_id}:${c.character_name}`}>
                            Day {c.day_number} &middot; {c.shoot_date} &mdash;{' '}
                            {c.actor_name || 'Actor'} ({c.character_name}) unavailable
                            {c.reason ? ` · ${c.reason}` : ''}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
