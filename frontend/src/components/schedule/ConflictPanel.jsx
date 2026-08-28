// frontend/src/components/schedule/ConflictPanel.jsx
import { useEffect, useMemo, useRef, useState } from 'react';
import { TriangleAlert, ChevronDown, ChevronRight, Loader2 } from 'lucide-react';
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

// A stable string that changes only when something conflict-relevant about the
// schedule changes: a day's date, or which scenes sit on which day. Scene order
// within a day is irrelevant, so it's sorted out.
function scheduleSignature(days) {
    return JSON.stringify(
        (days || []).map((d) => [
            d.id,
            d.shoot_date || null,
            (d.scenes || []).map((s) => s.scene_id).sort(),
        ]),
    );
}

export default function ConflictPanel({ scriptId, scheduleId, days, onConflictDays, onConflictScenes }) {
    const [conflicts, setConflicts] = useState([]);
    const [open, setOpen] = useState(true);
    const [checking, setChecking] = useState(false);
    const firstLoadDone = useRef(false);

    const daysSig = useMemo(() => scheduleSignature(days), [days]);

    useEffect(() => {
        let cancelled = false;
        if (!scheduleId) {
            setConflicts([]);
            onConflictDays?.(new Set());
            onConflictScenes?.(new Map());
            return;
        }
        // Only surface the "re-checking" indicator for updates after the first
        // load — the initial fetch is covered by the board's own loading state.
        if (firstLoadDone.current) setChecking(true);
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
            })
            .finally(() => {
                if (cancelled) return;
                firstLoadDone.current = true;
                setChecking(false);
            });
        return () => { cancelled = true; };
    }, [scriptId, scheduleId, daysSig, onConflictDays, onConflictScenes]);

    // Nothing to show and nothing in flight — stay out of the way.
    if (conflicts.length === 0 && !checking) return null;

    if (conflicts.length === 0 && checking) {
        return (
            <div className="conflict-panel conflict-panel--checking">
                <span className="conflict-panel-checking">
                    <Loader2 size={13} className="conflict-panel-spin" />
                    Checking availability…
                </span>
            </div>
        );
    }

    return (
        <div className="conflict-panel">
            <button className="conflict-panel-head" onClick={() => setOpen((o) => !o)}>
                {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                <TriangleAlert size={14} />
                Availability conflicts ({conflicts.length})
                {checking && (
                    <span className="conflict-panel-checking conflict-panel-checking--inline">
                        <Loader2 size={12} className="conflict-panel-spin" />
                        updating…
                    </span>
                )}
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
