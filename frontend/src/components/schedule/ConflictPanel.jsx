// frontend/src/components/schedule/ConflictPanel.jsx
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { TriangleAlert, ChevronDown, ChevronRight, Loader2 } from 'lucide-react';
import {
    getCastingConflicts,
    moveSceneToDay,
    removeSceneFromDay,
    acknowledgeSceneConflict,
} from '../../services/apiService';
import { Button } from '../ui';
import './ConflictPanel.css';

// scene_id -> [{ actor_name, character_name, ack_reason? }] for every conflicted scene card
function sceneMapFromConflicts(conflicts) {
    const m = new Map();
    for (const c of conflicts) {
        for (const sid of (c.scene_ids || [])) {
            if (!m.has(sid)) m.set(sid, []);
            m.get(sid).push({
                actor_name: c.actor_name,
                character_name: c.character_name,
                ack_reason: c.ack_reason,
            });
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

const keyOf = (c) => `${c.shooting_day_id}:${c.character_name}`;

export default function ConflictPanel({
    scriptId,
    scheduleId,
    days,
    onConflictDays,
    onConflictScenes,
    onAcknowledgedScenes,
    expandedKey,
    onExpandedKeyChange,
    refreshDays,
}) {
    const [conflicts, setConflicts] = useState([]);
    const [acknowledged, setAcknowledged] = useState([]);
    const [open, setOpen] = useState(true);
    const [checking, setChecking] = useState(false);
    const [ackDraft, setAckDraft] = useState(null);
    const [ackReason, setAckReason] = useState('');
    const [ackedOpen, setAckedOpen] = useState(false);
    const firstLoadDone = useRef(false);

    const daysSig = useMemo(() => scheduleSignature(days), [days]);

    const refetch = useCallback(() => {
        if (!scheduleId) {
            setConflicts([]);
            setAcknowledged([]);
            onConflictDays?.(new Set());
            onConflictScenes?.(new Map());
            onAcknowledgedScenes?.(new Map());
            return;
        }
        // Only surface the "re-checking" indicator for updates after the first
        // load — the initial fetch is covered by the board's own loading state.
        if (firstLoadDone.current) setChecking(true);
        return getCastingConflicts(scriptId, scheduleId)
            .then((data) => {
                const rows = data.conflicts || [];
                const acked = data.acknowledged || [];
                setConflicts(rows);
                setAcknowledged(acked);
                onConflictDays?.(new Set(rows.map((c) => c.shooting_day_id)));
                onConflictScenes?.(sceneMapFromConflicts(rows));
                onAcknowledgedScenes?.(sceneMapFromConflicts(acked));
            })
            .catch(() => {
                setConflicts([]);
                setAcknowledged([]);
                onConflictDays?.(new Set());
                onConflictScenes?.(new Map());
                onAcknowledgedScenes?.(new Map());
            })
            .finally(() => {
                firstLoadDone.current = true;
                setChecking(false);
            });
    }, [scriptId, scheduleId, onConflictDays, onConflictScenes, onAcknowledgedScenes]);

    useEffect(() => {
        refetch();
    }, [refetch, daysSig]);

    const doMove = async (c) => {
        for (const sid of (c.scene_ids || [])) {
            await moveSceneToDay(c.shooting_day_id, sid, c.suggested_day.shooting_day_id);
        }
        onExpandedKeyChange?.(null);
        refreshDays?.();
        refetch();
    };

    const doUnassign = async (c) => {
        for (const sid of (c.scene_ids || [])) {
            await removeSceneFromDay(c.shooting_day_id, sid);
        }
        onExpandedKeyChange?.(null);
        refreshDays?.();
        refetch();
    };

    const doAck = async (c) => {
        for (const sid of (c.scene_ids || [])) {
            await acknowledgeSceneConflict(c.shooting_day_id, sid, { acknowledged: true, reason: ackReason });
        }
        setAckDraft(null);
        setAckReason('');
        onExpandedKeyChange?.(null);
        refetch();
    };

    const doUnack = async (c) => {
        for (const sid of (c.scene_ids || [])) {
            await acknowledgeSceneConflict(c.shooting_day_id, sid, { acknowledged: false });
        }
        refetch();
    };

    // Nothing to show and nothing in flight — stay out of the way.
    if (conflicts.length === 0 && acknowledged.length === 0 && !checking) return null;

    if (conflicts.length === 0 && acknowledged.length === 0 && checking) {
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
                <>
                    <ul className="conflict-panel-list">
                        {conflicts.map((c) => {
                            const k = keyOf(c);
                            const isOpen = expandedKey === k;
                            return (
                                <li key={k} className={`conflict-row${isOpen ? ' conflict-row--open' : ''}`}>
                                    <button
                                        className="conflict-row-head"
                                        onClick={() => onExpandedKeyChange?.(isOpen ? null : k)}
                                    >
                                        {isOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                                        Day {c.day_number} · {c.shoot_date} — {c.actor_name || 'Actor'} ({c.character_name}) unavailable
                                        {c.reason ? ` · ${c.reason}` : ''}
                                    </button>
                                    {isOpen && (
                                        <div className="conflict-row-actions">
                                            <Button
                                                size="sm"
                                                disabled={!c.suggested_day}
                                                title={c.suggested_day ? undefined : "Every dated day has an availability clash for this scene's principals."}
                                                onClick={() => doMove(c)}
                                            >
                                                {c.suggested_day
                                                    ? `Move to Day ${c.suggested_day.day_number} (${c.suggested_day.shoot_date})`
                                                    : 'No conflict-free day'}
                                            </Button>
                                            <Button size="sm" variant="ghost" onClick={() => doUnassign(c)}>Unassign</Button>
                                            <Button size="sm" variant="ghost" onClick={() => setAckDraft(k)}>Acknowledge</Button>
                                            {ackDraft === k && (
                                                <span className="conflict-ack-input">
                                                    <input
                                                        type="text"
                                                        placeholder="Reason (optional)"
                                                        value={ackReason}
                                                        onChange={(e) => setAckReason(e.target.value)}
                                                    />
                                                    <Button size="sm" onClick={() => doAck(c)}>Save</Button>
                                                </span>
                                            )}
                                        </div>
                                    )}
                                </li>
                            );
                        })}
                    </ul>
                    {acknowledged.length > 0 && (
                        <div className="conflict-acked">
                            <button className="conflict-acked-head" onClick={() => setAckedOpen((o) => !o)}>
                                {ackedOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                                Acknowledged ({acknowledged.length})
                            </button>
                            {ackedOpen && (
                                <ul>
                                    {acknowledged.map((c) => (
                                        <li key={keyOf(c)}>
                                            Day {c.day_number} · {c.shoot_date} — {c.actor_name || 'Actor'} ({c.character_name})
                                            {c.ack_reason ? ` · “${c.ack_reason}”` : ''}
                                            <button className="conflict-unack" onClick={() => doUnack(c)}>Un-acknowledge</button>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
