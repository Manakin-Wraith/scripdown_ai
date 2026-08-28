// frontend/src/components/schedule/ConflictPanel.jsx
import { useEffect, useState } from 'react';
import { TriangleAlert, ChevronDown, ChevronRight } from 'lucide-react';
import { getCastingConflicts } from '../../services/apiService';
import './ConflictPanel.css';

// scene_id -> [{ actor_name, character_name }] for every conflicted scene card
function sceneMapFromConflicts(conflicts) {
    const m = new Map();
    for (const c of conflicts) {
        for (const sid of (c.scene_ids || [])) {
            if (!m.has(sid)) m.set(sid, []);
            m.get(sid).push({ actor_name: c.actor_name, character_name: c.character_name });
        }
    }
    return m;
}

export default function ConflictPanel({ scriptId, scheduleId, onConflictDays, onConflictScenes }) {
    const [conflicts, setConflicts] = useState([]);
    const [open, setOpen] = useState(true);

    useEffect(() => {
        let cancelled = false;
        if (!scheduleId) {
            setConflicts([]);
            onConflictDays?.(new Set());
            onConflictScenes?.(new Map());
            return;
        }
        getCastingConflicts(scriptId, scheduleId)
            .then((data) => {
                if (cancelled) return;
                const rows = data.conflicts || [];
                setConflicts(rows);
                onConflictDays?.(new Set(rows.map((c) => c.shooting_day_id)));
                onConflictScenes?.(sceneMapFromConflicts(rows));
            })
            .catch(() => {
                if (cancelled) return;
                setConflicts([]);
                onConflictDays?.(new Set());
                onConflictScenes?.(new Map());
            });
        return () => { cancelled = true; };
    }, [scriptId, scheduleId, onConflictDays, onConflictScenes]);

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
