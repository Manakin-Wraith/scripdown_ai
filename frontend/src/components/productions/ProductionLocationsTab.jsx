import { useState, useEffect, useCallback } from 'react';
import {
    listProductionLocations,
    linkProductionLocation,
    updateProductionLocation,
    unlinkProductionLocation,
} from '../../services/apiService';
import { Spinner } from '../ui';
import StaticMap from '../locations/StaticMap';
import LocationPickerModal from './LocationPickerModal';

export default function ProductionLocationsTab({ productionId, access }) {
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [picking, setPicking] = useState(false);
    const [editingNote, setEditingNote] = useState(null); // link_id
    const [noteDraft, setNoteDraft] = useState('');

    const canEdit = access?.can_edit_production;

    const load = useCallback(() => {
        return listProductionLocations(productionId)
            .then((data) => { setRows(data.locations || []); setError(null); })
            .catch((err) => setError(err.response?.data?.error || err.message || 'Failed to load locations'));
    }, [productionId]);

    useEffect(() => {
        let active = true;
        listProductionLocations(productionId)
            .then((data) => { if (active) { setRows(data.locations || []); setError(null); } })
            .catch((err) => active && setError(err.response?.data?.error || err.message || 'Failed to load locations'))
            .finally(() => { if (active) setLoading(false); });
        return () => { active = false; };
    }, [productionId]);

    const handlePick = async (locationId, notes) => {
        try {
            await linkProductionLocation(productionId, { location_id: locationId, production_notes: notes });
            setPicking(false);
            await load();
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Could not link that location');
        }
    };

    const startEditNote = (row) => {
        setEditingNote(row.link_id);
        setNoteDraft(row.production_notes || '');
    };

    const saveNote = async (linkId) => {
        try {
            await updateProductionLocation(productionId, linkId, { production_notes: noteDraft.trim() || null });
            setEditingNote(null);
            await load();
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Could not save the note');
        }
    };

    const handleUnlink = async (row) => {
        if (!window.confirm(`Unlink ${row.name || 'this location'} from the production?`)) return;
        try {
            await unlinkProductionLocation(productionId, row.link_id);
            await load();
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Could not unlink that location');
        }
    };

    if (loading) {
        return <div className="production-page-loading"><Spinner size={32} /></div>;
    }

    return (
        <div className="production-locations">
            <div className="production-scripts-head">
                <h3>Locations</h3>
                {canEdit && (
                    <button onClick={() => setPicking(true)}>Link a location</button>
                )}
            </div>

            {error && <p className="production-page-error">{error}</p>}

            {rows.length === 0 ? (
                <p className="production-scripts-empty">
                    {canEdit ? 'No locations linked yet. Link one from your directory.' : 'No locations linked yet.'}
                </p>
            ) : (
                <table className="contact-table">
                    <thead>
                        <tr>
                            <th>Map</th>
                            <th>Name</th>
                            <th>Address</th>
                            <th>Contact</th>
                            <th>Notes</th>
                            {canEdit && <th />}
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((row) => (
                            <tr key={row.link_id}>
                                <td style={{ width: 88 }}>
                                    <StaticMap
                                        lat={row.lat}
                                        lng={row.lng}
                                        geocodeStatus={row.geocode_status}
                                        height={48}
                                    />
                                </td>
                                <td>{row.name}</td>
                                <td>{row.address || '—'}</td>
                                <td>{row.primary_contact_name || '—'}</td>
                                <td>
                                    {editingNote === row.link_id ? (
                                        <span className="production-locations-note-edit">
                                            <input
                                                type="text"
                                                value={noteDraft}
                                                onChange={(e) => setNoteDraft(e.target.value)}
                                            />
                                            <button type="button" onClick={() => saveNote(row.link_id)}>Save</button>
                                            <button type="button" onClick={() => setEditingNote(null)}>Cancel</button>
                                        </span>
                                    ) : (
                                        <span
                                            onClick={canEdit ? () => startEditNote(row) : undefined}
                                            style={canEdit ? { cursor: 'pointer' } : undefined}
                                        >
                                            {row.production_notes || (canEdit ? 'Add a note…' : '—')}
                                        </span>
                                    )}
                                </td>
                                {canEdit && (
                                    <td>
                                        <button type="button" onClick={() => handleUnlink(row)}>Unlink</button>
                                    </td>
                                )}
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}

            {picking && (
                <LocationPickerModal
                    onPick={handlePick}
                    onClose={() => setPicking(false)}
                    excludeIds={rows.map((r) => r.location_id)}
                />
            )}
        </div>
    );
}
