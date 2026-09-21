import { useState, useEffect, useCallback } from 'react';
import { X, Download } from 'lucide-react';
import {
    getOrCreateCallSheet, getCallSheet, updateCallSheet,
    addCallSheetCrew, removeCallSheetCrew,
    addCallSheetCast, removeCallSheetCast,
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
    const [saving, setSaving] = useState(false);
    const [crewOptions, setCrewOptions] = useState([]);
    const [locationOptions, setLocationOptions] = useState([]);
    const [castOptions, setCastOptions] = useState([]);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const created = await getOrCreateCallSheet(dayId);
            const full = await getCallSheet(created.call_sheet.id);
            setCallSheet(full.call_sheet);
            if (productionId) {
                const [crewRes, locRes] = await Promise.all([
                    listProductionCrew(productionId),
                    listProductionLocations(productionId),
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
            toast.error('Error', 'Could not load the call sheet for this day.');
        } finally {
            setLoading(false);
        }
    }, [dayId, productionId, scriptId, toast]);

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

    const removeCastRow = async (castingId) => {
        await removeCallSheetCast(callSheet.id, castingId);
        await load();
    };

    if (loading || !callSheet) {
        return (
            <div className="cs-modal-backdrop" onClick={onClose}>
                <div className="cs-modal" onClick={(e) => e.stopPropagation()}><Spinner /></div>
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
                                        onBlur={(e) => patchField(field, e.target.value)}
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
                                        onBlur={(e) => addCallSheetCrew(callSheet.id, { crew_id: row.crew_id, call_time: e.target.value }).then(load)}
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
                                        onBlur={(e) => addCallSheetCast(callSheet.id, { casting_id: row.casting_id, call_time: e.target.value }).then(load)}
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
