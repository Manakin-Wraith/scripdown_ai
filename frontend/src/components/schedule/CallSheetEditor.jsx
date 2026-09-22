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
import {
    DayFieldsPanel, KeyCrewPanel, BlocksPanel, DeptCallsPanel, CateringPanel, ColumnInputs,
} from './CallSheetPanels';
import './CallSheetEditor.css';

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

    // One save path for every day-level edit. Keys the template no longer
    // defines come back in ignored_keys -> reload so the UI matches the template.
    const patchCallSheet = async (payload, { reload = false } = {}) => {
        setSaving(true);
        try {
            const res = await updateCallSheet(callSheet.id, payload);
            if (res.ignored_keys?.length) {
                toast.warning('Template changed', 'Some fields were removed from the template. Reloading.');
                await load();
            } else if (reload) {
                await load();
            } else {
                setCallSheet((prev) => ({ ...prev, ...res.call_sheet }));
            }
        } catch (err) {
            console.error('Failed to update call sheet:', err);
            toast.error('Update Failed', err.response?.data?.error || 'Could not save that change.');
        } finally {
            setSaving(false);
        }
    };

    const publish = () => patchCallSheet({ status: 'published' });
    const unpublish = () => patchCallSheet({ status: 'draft' });

    const addCrewRow = async (crewId) => {
        if (!crewId) return;
        try {
            await addCallSheetCrew(callSheet.id, { crew_id: crewId });
            await load();
        } catch (err) {
            toast.error('Error', err.response?.data?.error || 'Could not add crew member.');
        }
    };

    const updateCrewRow = async (crewId, payload) => {
        try {
            await updateCallSheetCrew(callSheet.id, crewId, payload);
            await load();
        } catch (err) {
            toast.error('Error', err.response?.data?.error || 'Could not update crew row.');
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

    const updateCastRow = async (castingId, payload) => {
        try {
            await updateCallSheetCast(callSheet.id, castingId, payload);
            await load();
        } catch (err) {
            toast.error('Error', err.response?.data?.error || 'Could not update cast row.');
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

    const template = callSheet.template;
    const canSeeSensitive = !!callSheet.can_view_sensitive;
    const extrasVisible = template.sections.some((s) => s.key === 'extras' && s.visible);
    const isBackground = (row) => row.casting?.tier === 'background';
    const castRows = extrasVisible ? (callSheet.cast || []).filter((r) => !isBackground(r)) : (callSheet.cast || []);
    const extrasRows = extrasVisible ? (callSheet.cast || []).filter(isBackground) : [];

    const castList = (rows) => (
        <ul className="cs-roster-list">
            {rows.map((row) => (
                <li key={row.id}>
                    {row.casting?.character_name} ({row.casting?.actor_name || 'unbooked'})
                    <input type="time" defaultValue={row.call_time || ''}
                           onBlur={(e) => updateCastRow(row.casting_id, { call_time: e.target.value || null })} />
                    <button onClick={() => removeCastRow(row.casting_id)}>Remove</button>
                    <ColumnInputs columns={template.cast_columns} values={row.extra} canSeeSensitive={canSeeSensitive}
                                  onCommit={(key, value) => updateCastRow(row.casting_id, { extra: { [key]: value } })} />
                </li>
            ))}
        </ul>
    );

    const renderSection = (key) => {
        switch (key) {
            case 'header':
                return (
                    <>
                        <DayFieldsPanel callSheet={callSheet} section="header" onPatch={patchCallSheet} />
                        <KeyCrewPanel callSheet={callSheet} onPatch={patchCallSheet} />
                    </>
                );
            case 'day_info':
                return <DayFieldsPanel callSheet={callSheet} section="day_info" onPatch={patchCallSheet} />;
            case 'locations':
                return (
                    <>
                        <select defaultValue="" onChange={(e) => addLocationRow(e.target.value)}>
                            <option value="" disabled>Add a location…</option>
                            {locationOptions.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                        </select>
                        <ul className="cs-roster-list">
                            {(callSheet.locations || []).map((row) => (
                                <li key={row.id}>
                                    {row.location?.name} {row.is_primary && '(Primary)'}
                                    <button onClick={() => removeLocationRow(row.location_id)}>Remove</button>
                                </li>
                            ))}
                        </ul>
                    </>
                );
            case 'scenes':
                return (
                    <table className="cs-scene-table">
                        <thead><tr><th>Sc</th><th>I/E</th><th>Set</th><th>D/N</th></tr></thead>
                        <tbody>
                            {(callSheet.scenes || []).map((s) => (
                                <tr key={s.id}>
                                    <td>{s.scene_number}</td><td>{s.int_ext}</td>
                                    <td>{s.setting || s.location_canonical}</td><td>{s.time_of_day}</td>
                                    {template.scene_columns.some((c) => canSeeSensitive || !c.sensitive) && (
                                        <td>
                                            <ColumnInputs columns={template.scene_columns}
                                                          values={(callSheet.scene_extras || {})[s.id]}
                                                          canSeeSensitive={canSeeSensitive}
                                                          onCommit={(k, v) => patchCallSheet({ scene_extras: { [s.id]: { [k]: v } } })} />
                                        </td>
                                    )}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                );
            case 'cast':
                return (
                    <>
                        <select defaultValue="" onChange={(e) => addCastRow(e.target.value)}>
                            <option value="" disabled>Add a cast member…</option>
                            {castOptions.map((c) => (
                                <option key={c.id} value={c.id}>{c.character_name} — {c.actor_name || 'unbooked'}</option>
                            ))}
                        </select>
                        {castList(castRows)}
                    </>
                );
            case 'extras':
                return extrasRows.length
                    ? castList(extrasRows)
                    : <p className="cs-note">Background cast added in the Cast section appear here.</p>;
            case 'crew':
                return (
                    <>
                        <select defaultValue="" onChange={(e) => addCrewRow(e.target.value)}>
                            <option value="" disabled>Add a crew member…</option>
                            {crewOptions.map((c) => <option key={c.id} value={c.id}>{c.contact?.name} — {c.role}</option>)}
                        </select>
                        <ul className="cs-roster-list">
                            {(callSheet.crew || []).map((row) => (
                                <li key={row.id}>
                                    {row.crew?.contact?.name}
                                    <input type="time" defaultValue={row.call_time || ''}
                                           onBlur={(e) => updateCrewRow(row.crew_id, { call_time: e.target.value || null })} />
                                    <button onClick={() => removeCrewRow(row.crew_id)}>Remove</button>
                                    <ColumnInputs columns={template.crew_columns} values={row.extra} canSeeSensitive={canSeeSensitive}
                                                  onCommit={(k, v) => updateCrewRow(row.crew_id, { extra: { [k]: v } })} />
                                </li>
                            ))}
                        </ul>
                    </>
                );
            case 'dept_calls':
                return <DeptCallsPanel callSheet={callSheet} onPatch={patchCallSheet} />;
            case 'catering':
                return <CateringPanel callSheet={callSheet} onPatch={patchCallSheet} />;
            case 'notes':
                return (
                    <>
                        <DayFieldsPanel callSheet={callSheet} section="notes" onPatch={patchCallSheet} />
                        <BlocksPanel callSheet={callSheet} onPatch={patchCallSheet} />
                    </>
                );
            case 'advanced':
                return <p className="cs-note">The next shooting day&rsquo;s scenes are added to the PDF automatically.</p>;
            default:
                return null;
        }
    };

    return (
        <div className="cs-modal-backdrop" onClick={onClose}>
            <div className="cs-modal" onClick={(e) => e.stopPropagation()}>
                <div className="cs-modal-header">
                    <h3>Call Sheet &middot; Day {dayNumber}</h3>
                    <span className={`cs-status-chip cs-status-${callSheet.status}`}>{callSheet.status}</span>
                    <button className="cs-modal-close" onClick={onClose}><X size={18} /></button>
                </div>

                <div className="cs-modal-body">
                    {template.sections.filter((s) => s.visible).map((s) => (
                        <section key={s.key} className="cs-section">
                            <h4>{s.label}</h4>
                            {renderSection(s.key)}
                        </section>
                    ))}
                </div>

                <div className="cs-modal-footer">
                    <button className="cs-download-btn" onClick={() => downloadCallSheetPdf(callSheet.id, dayNumber)}>
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
