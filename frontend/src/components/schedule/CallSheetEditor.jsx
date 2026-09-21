import { useState, useEffect, useCallback } from 'react';
import { X, Download } from 'lucide-react';
import {
    getOrCreateCallSheet, getCallSheet, getCallSheetByDay, updateCallSheet,
    addCallSheetCrew, updateCallSheetCrew, removeCallSheetCrew,
    addCallSheetCast, updateCallSheetCast, removeCallSheetCast,
    addCallSheetLocation, removeCallSheetLocation,
    downloadCallSheetPdf,
    listProductionCrew, listProductionLocations, getCasting,
} from '../../services/apiService';
import { Spinner } from '../ui';
import { useToast } from '../../context/ToastContext';
import './CallSheetEditor.css';

const DAY_INFO_FIELDS = [
    ['weather', 'Weather', 'text'],
    ['sunrise_time', 'Sunrise', 'time'],
    ['sunset_time', 'Sunset', 'time'],
    ['breakfast_time', 'Breakfast', 'time'],
    ['lunch_time', 'Lunch', 'time'],
    ['nearest_hospital', 'Nearest Hospital', 'text'],
    ['parking_notes', 'Parking Notes', 'text'],
    ['safety_notes', 'Safety / COVID Officer', 'text'],
    ['general_notes', 'General Notes', 'textarea'],
];

const CallSheetEditor = ({ dayId, dayNumber, productionId, scriptId, onClose }) => {
    const toast = useToast();
    const [callSheet, setCallSheet] = useState(null);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(null);
    const [saving, setSaving] = useState(false);
    const [crewOptions, setCrewOptions] = useState([]);
    const [locationOptions, setLocationOptions] = useState([]);
    const [castOptions, setCastOptions] = useState([]);

    // Sequencing matters here: production_id isn't known until the call
    // sheet itself has loaded, so the crew/location fetches (keyed off it)
    // run AFTER that resolves rather than in the same Promise.all batch.
    const load = useCallback(async () => {
        setLoading(true);
        setLoadError(null);
        try {
            let full;
            try {
                // Viewer-accessible GET first -- a read-only member can open
                // an existing call sheet without ever hitting the edit-gated
                // POST below.
                full = await getCallSheetByDay(dayId);
            } catch (err) {
                if (err.response?.status !== 404) throw err;
                try {
                    const created = await getOrCreateCallSheet(dayId);
                    full = await getCallSheet(created.call_sheet.id);
                } catch (createErr) {
                    if (createErr.response?.status === 403) {
                        setLoadError("You don't have permission to create a call sheet for this day.");
                        return;
                    }
                    throw createErr;
                }
            }
            setCallSheet(full.call_sheet);

            const pid = full.call_sheet.production_id;
            if (pid) {
                const [crewRes, locRes] = await Promise.all([
                    listProductionCrew(pid),
                    listProductionLocations(pid),
                ]);
                setCrewOptions(crewRes.crew || []);
                setLocationOptions((locRes.locations || []).map((l) => {
                    const loc = l.location || l;
                    return { ...loc, id: loc.id || l.location_id };
                }));
            }
            if (scriptId) {
                const castRes = await getCasting(scriptId);
                setCastOptions(castRes.casting || []);
            }
        } catch (err) {
            console.error('Failed to load call sheet:', err);
            setLoadError('Could not load the call sheet for this day.');
            toast.error('Error', 'Could not load the call sheet for this day.');
        } finally {
            setLoading(false);
        }
    }, [dayId, scriptId, toast]);

    useEffect(() => { load(); }, [load]);

    const patchField = async (field, value) => {
        setSaving(true);
        try {
            const res = await updateCallSheet(callSheet.id, { [field]: value });
            setCallSheet((prev) => ({ ...prev, ...res.call_sheet }));
        } catch (err) {
            console.error('Failed to update call sheet:', err);
            toast.error('Update Failed', 'Could not save that change.');
        } finally {
            setSaving(false);
        }
    };

    const publish = () => patchField('status', 'published');
    const unpublish = () => patchField('status', 'draft');

    const addCrewRow = async (crewId) => {
        if (!crewId) return;
        try {
            await addCallSheetCrew(callSheet.id, { crew_id: crewId });
            await load();
        } catch (err) {
            toast.error('Error', err.response?.data?.error || 'Could not add crew member.');
        }
    };

    const updateCrewCallTime = async (crewId, callTime) => {
        try {
            await updateCallSheetCrew(callSheet.id, crewId, { call_time: callTime || null });
            await load();
        } catch (err) {
            toast.error('Error', err.response?.data?.error || 'Could not update call time.');
        }
    };

    const removeCrewRow = async (crewId) => {
        await removeCallSheetCrew(callSheet.id, crewId);
        await load();
    };

    const addLocationRow = async (locationId) => {
        if (!locationId) return;
        try {
            await addCallSheetLocation(callSheet.id, { location_id: locationId });
            await load();
        } catch (err) {
            toast.error('Error', err.response?.data?.error || 'Could not add location.');
        }
    };

    const removeLocationRow = async (locationId) => {
        await removeCallSheetLocation(callSheet.id, locationId);
        await load();
    };

    const addCastRow = async (castingId) => {
        if (!castingId) return;
        try {
            await addCallSheetCast(callSheet.id, { casting_id: castingId });
            await load();
        } catch (err) {
            toast.error('Error', err.response?.data?.error || 'Could not add cast member.');
        }
    };

    const updateCastCallTime = async (castingId, callTime) => {
        try {
            await updateCallSheetCast(callSheet.id, castingId, { call_time: callTime || null });
            await load();
        } catch (err) {
            toast.error('Error', err.response?.data?.error || 'Could not update call time.');
        }
    };

    const removeCastRow = async (castingId) => {
        await removeCallSheetCast(callSheet.id, castingId);
        await load();
    };

    if (loading || (!callSheet && !loadError)) {
        return (
            <div className="cs-modal-backdrop" onClick={onClose}>
                <div className="cs-modal" onClick={(e) => e.stopPropagation()}><Spinner /></div>
            </div>
        );
    }

    if (loadError) {
        return (
            <div className="cs-modal-backdrop" onClick={onClose}>
                <div className="cs-modal" onClick={(e) => e.stopPropagation()}>
                    <div className="cs-modal-header">
                        <h3>Call Sheet &middot; Day {dayNumber}</h3>
                        <button className="cs-modal-close" onClick={onClose}><X size={18} /></button>
                    </div>
                    <p className="cs-load-error">{loadError}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="cs-modal-backdrop" onClick={onClose}>
            <div className="cs-modal" onClick={(e) => e.stopPropagation()}>
                <div className="cs-modal-header">
                    <h3>Call Sheet &middot; Day {dayNumber}</h3>
                    <span className={`cs-status-chip cs-status-${callSheet.status}`}>{callSheet.status}</span>
                    <button className="cs-modal-close" onClick={onClose}><X size={18} /></button>
                </div>

                <div className="cs-modal-body">
                    <section className="cs-section">
                        <h4>Day Info</h4>
                        {DAY_INFO_FIELDS.map(([field, label, type]) => (
                            <label key={field} className="cs-field">
                                <span>{label}</span>
                                {type === 'textarea' ? (
                                    <textarea
                                        defaultValue={callSheet[field] || ''}
                                        onBlur={(e) => patchField(field, e.target.value)}
                                    />
                                ) : (
                                    <input
                                        type={type}
                                        defaultValue={callSheet[field] || ''}
                                        onBlur={(e) => patchField(field, type === 'time' ? (e.target.value || null) : e.target.value)}
                                    />
                                )}
                            </label>
                        ))}
                    </section>

                    <section className="cs-section">
                        <h4>Locations</h4>
                        <select defaultValue="" onChange={(e) => addLocationRow(e.target.value)}>
                            <option value="" disabled>Add a location…</option>
                            {locationOptions.map((l) => (
                                <option key={l.id} value={l.id}>{l.name}</option>
                            ))}
                        </select>
                        <ul className="cs-roster-list">
                            {(callSheet.locations || []).map((row) => (
                                <li key={row.id}>
                                    {row.location?.name} {row.is_primary && '(Primary)'}
                                    <button onClick={() => removeLocationRow(row.location_id)}>Remove</button>
                                </li>
                            ))}
                        </ul>
                    </section>

                    <section className="cs-section">
                        <h4>Crew</h4>
                        <select defaultValue="" onChange={(e) => addCrewRow(e.target.value)}>
                            <option value="" disabled>Add a crew member…</option>
                            {crewOptions.map((c) => (
                                <option key={c.id} value={c.id}>{c.contact?.name} — {c.role}</option>
                            ))}
                        </select>
                        <ul className="cs-roster-list">
                            {(callSheet.crew || []).map((row) => (
                                <li key={row.id}>
                                    {row.crew?.contact?.name}
                                    <input
                                        type="time"
                                        defaultValue={row.call_time || ''}
                                        onBlur={(e) => updateCrewCallTime(row.crew_id, e.target.value)}
                                    />
                                    <button onClick={() => removeCrewRow(row.crew_id)}>Remove</button>
                                </li>
                            ))}
                        </ul>
                    </section>

                    <section className="cs-section">
                        <h4>Cast</h4>
                        <select defaultValue="" onChange={(e) => addCastRow(e.target.value)}>
                            <option value="" disabled>Add a cast member…</option>
                            {castOptions.map((c) => (
                                <option key={c.id} value={c.id}>{c.character_name} — {c.actor_name || 'unbooked'}</option>
                            ))}
                        </select>
                        <ul className="cs-roster-list">
                            {(callSheet.cast || []).map((row) => (
                                <li key={row.id}>
                                    {row.casting?.character_name} ({row.casting?.actor_name || 'unbooked'})
                                    <input
                                        type="time"
                                        defaultValue={row.call_time || ''}
                                        onBlur={(e) => updateCastCallTime(row.casting_id, e.target.value)}
                                    />
                                    <button onClick={() => removeCastRow(row.casting_id)}>Remove</button>
                                </li>
                            ))}
                        </ul>
                    </section>

                    <section className="cs-section">
                        <h4>Scene Schedule</h4>
                        <table className="cs-scene-table">
                            <thead><tr><th>Sc</th><th>I/E</th><th>Set</th><th>D/N</th></tr></thead>
                            <tbody>
                                {(callSheet.scenes || []).map((s) => (
                                    <tr key={s.id}>
                                        <td>{s.scene_number}</td><td>{s.int_ext}</td>
                                        <td>{s.setting || s.location_canonical}</td><td>{s.time_of_day}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </section>
                </div>

                <div className="cs-modal-footer">
                    <button
                        className="cs-download-btn"
                        onClick={() => downloadCallSheetPdf(callSheet.id, dayNumber)}
                    >
                        <Download size={14} /> Download PDF
                    </button>
                    {callSheet.status === 'draft' ? (
                        <button className="cs-publish-btn" disabled={saving} onClick={publish}>Publish</button>
                    ) : (
                        <button className="cs-unpublish-btn" disabled={saving} onClick={unpublish}>Move back to draft</button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default CallSheetEditor;
