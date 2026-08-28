// frontend/src/components/cast/UnavailabilityEditor.jsx
import { useEffect, useState } from 'react';
import { X, Plus } from 'lucide-react';
import { addUnavailability, removeUnavailability } from '../../services/apiService';

const fmt = (d) => new Date(d + 'T00:00:00').toLocaleDateString(undefined,
    { day: '2-digit', month: 'short' });

const byStart = (a, b) => String(a.start_date).localeCompare(String(b.start_date));

export default function UnavailabilityEditor({ castingId, ranges, canEdit, onChanged }) {
    const [adding, setAdding] = useState(false);
    const [start, setStart] = useState('');
    const [end, setEnd] = useState('');
    const [reason, setReason] = useState('');
    const [err, setErr] = useState(null);
    const [saving, setSaving] = useState(false);

    // Render from a local copy so an add/remove shows immediately, without
    // waiting on the parent's refetch (which can lag or fail silently).
    // Reconciles to server truth whenever the `ranges` prop changes.
    const [localRanges, setLocalRanges] = useState(ranges);
    useEffect(() => { setLocalRanges(ranges); }, [ranges]);

    const submit = async () => {
        setErr(null);
        if (!start || !end) { setErr('Pick both dates.'); return; }
        if (end < start) { setErr('End date is before the start date.'); return; }
        setSaving(true);
        try {
            const { unavailability } = await addUnavailability(
                castingId, { start_date: start, end_date: end, reason },
            );
            setLocalRanges((prev) => [...prev.filter((r) => r.id !== unavailability.id),
                unavailability].sort(byStart));
            setAdding(false); setStart(''); setEnd(''); setReason('');
            onChanged();
        } catch {
            setErr('Couldn’t save — retry.');
        } finally {
            setSaving(false);
        }
    };

    const remove = async (id) => {
        const prev = localRanges;
        setLocalRanges((rs) => rs.filter((r) => r.id !== id));
        try {
            await removeUnavailability(id);
            onChanged();
        } catch {
            setLocalRanges(prev); // restore on failure
            setErr('Couldn’t remove — retry.');
        }
    };

    return (
        <div className="cd-unavail">
            <p className="cd-label">Unavailable dates</p>
            {localRanges.length === 0 && <p className="cd-muted">None set.</p>}
            {localRanges.map((r) => (
                <div className="cd-range" key={r.id}>
                    <span>{fmt(r.start_date)} – {fmt(r.end_date)}</span>
                    <span className="cd-range-reason">{r.reason || '—'}</span>
                    {canEdit && (
                        <button aria-label="Remove range" onClick={() => remove(r.id)}>
                            <X size={14} />
                        </button>
                    )}
                </div>
            ))}
            {canEdit && !adding && (
                <button className="cd-add" onClick={() => setAdding(true)}>
                    <Plus size={14} /> Add unavailable dates
                </button>
            )}
            {adding && (
                <div className="cd-range-form">
                    <input type="date" value={start} onChange={(e) => setStart(e.target.value)} aria-label="Start date" />
                    <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} aria-label="End date" />
                    <input type="text" placeholder="Reason (optional)" value={reason}
                        onChange={(e) => setReason(e.target.value)} />
                    <div className="cd-range-actions">
                        <button onClick={submit} disabled={saving}>{saving ? 'Adding…' : 'Add'}</button>
                        <button onClick={() => setAdding(false)} disabled={saving}>Cancel</button>
                    </div>
                    {err && <p className="cd-err">{err}</p>}
                </div>
            )}
        </div>
    );
}
