import { useState, useEffect } from 'react';
import { listLocations } from '../../services/apiService';
import { Spinner } from '../ui';

/**
 * Pick a location from the owner's directory to link to a production.
 * Props: { onPick, onClose, excludeIds }
 *   onPick(locationId, notes) — the caller then calls linkProductionLocation.
 */
export default function LocationPickerModal({ onPick, onClose, excludeIds = [] }) {
    const [locations, setLocations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [q, setQ] = useState('');
    const [notes, setNotes] = useState('');
    const [busyId, setBusyId] = useState(null);

    useEffect(() => {
        listLocations()
            .then((data) => setLocations(data.locations || []))
            .catch((err) => setError(err.response?.data?.error || err.message || 'Failed to load locations'))
            .finally(() => setLoading(false));
    }, []);

    const exclude = new Set(excludeIds);
    const needle = q.trim().toLowerCase();
    const shown = locations.filter((l) => {
        if (exclude.has(l.id)) return false;
        if (!needle) return true;
        return (l.name || '').toLowerCase().includes(needle)
            || (l.address || '').toLowerCase().includes(needle);
    });

    const pick = async (locationId) => {
        setBusyId(locationId);
        try {
            await onPick(locationId, notes.trim() || undefined);
        } finally {
            setBusyId(null);
        }
    };

    return (
        <div className="production-modal-backdrop" onClick={onClose}>
            <div className="production-modal" onClick={(e) => e.stopPropagation()}>
                <h3>Link a location</h3>

                {error && <p className="production-page-error">{error}</p>}

                <input
                    type="text"
                    className="contact-search"
                    placeholder="Search your locations…"
                    value={q}
                    onChange={(e) => setQ(e.target.value)}
                />

                <label className="contact-field">
                    <span>Production notes (optional)</span>
                    <textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
                </label>

                {loading ? (
                    <Spinner size={24} />
                ) : shown.length === 0 ? (
                    <p className="production-scripts-empty">
                        No locations to link. Add them in the Locations directory first.
                    </p>
                ) : (
                    <ul className="contact-used-on-list">
                        {shown.map((l) => (
                            <li key={l.id}>
                                <button
                                    type="button"
                                    className="production-new-btn"
                                    disabled={busyId === l.id}
                                    onClick={() => pick(l.id)}
                                >
                                    {l.name}{l.address ? ` — ${l.address}` : ''}
                                </button>
                            </li>
                        ))}
                    </ul>
                )}

                <div className="contact-form-actions">
                    <button type="button" className="production-modal-close" onClick={onClose}>
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
}
