import { useEffect, useState } from 'react';
import { geocodeAddress } from '../../services/apiService';
import StaticMap from './StaticMap';

const blankFromInitial = (initial) => ({
    name: initial?.name || '',
    address: initial?.address || '',
    lat: initial?.lat ?? '',
    lng: initial?.lng ?? '',
    primary_contact_id: initial?.primary_contact_id || '',
    permit_status: initial?.permit_status || '',
    parking_notes: initial?.parking_notes || '',
    loadin_notes: initial?.loadin_notes || '',
    restrictions: initial?.restrictions || '',
    notes: initial?.notes || '',
});

/**
 * Controlled create/edit form for a location, rendered inline in the detail
 * pane (no modal chrome).
 *
 * lat/lng are only included in the payload when the user set or changed them
 * (via Locate or by editing the fields), so the backend's manual-vs-geocode
 * branch fires correctly.
 *
 * Props: { initial, contacts, onSubmit, onCancel, saving, onDirtyChange }
 */
export default function LocationForm({ initial, contacts = [], onSubmit, onCancel, saving, onDirtyChange }) {
    const [form, setForm] = useState(() => blankFromInitial(initial));
    const [coordsTouched, setCoordsTouched] = useState(false);
    const [dirty, setDirty] = useState(false);
    const [locating, setLocating] = useState(false);
    const [locateError, setLocateError] = useState(null);
    const isEdit = Boolean(initial);

    useEffect(() => { onDirtyChange?.(dirty); }, [dirty, onDirtyChange]);
    useEffect(() => () => onDirtyChange?.(false), [onDirtyChange]);

    const set = (key) => (e) => {
        setDirty(true);
        setForm((f) => ({ ...f, [key]: e.target.value }));
    };
    const setCoord = (key) => (e) => {
        setDirty(true);
        setCoordsTouched(true);
        setForm((f) => ({ ...f, [key]: e.target.value }));
    };

    const locate = async () => {
        if (!form.address.trim()) return;
        setLocating(true);
        setLocateError(null);
        try {
            const { lat, lng } = await geocodeAddress(form.address.trim());
            if (lat != null && lng != null) {
                setDirty(true);
                setCoordsTouched(true);
                setForm((f) => ({ ...f, lat, lng }));
            } else {
                setLocateError("Couldn't locate that address — enter coordinates manually.");
            }
        } catch {
            setLocateError('Geocoding failed — enter coordinates manually.');
        } finally {
            setLocating(false);
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        const name = form.name.trim();
        if (!name || saving) return;

        const opt = (v) => {
            const t = typeof v === 'string' ? v.trim() : v;
            if (t === '' || t === null || t === undefined) return isEdit ? null : undefined;
            return t;
        };

        const payload = {
            name,
            address: opt(form.address),
            primary_contact_id: form.primary_contact_id || (isEdit ? null : undefined),
            permit_status: opt(form.permit_status),
            parking_notes: opt(form.parking_notes),
            loadin_notes: opt(form.loadin_notes),
            restrictions: opt(form.restrictions),
            notes: opt(form.notes),
        };

        if (coordsTouched) {
            const lat = form.lat === '' ? null : Number(form.lat);
            const lng = form.lng === '' ? null : Number(form.lng);
            payload.lat = Number.isFinite(lat) ? lat : null;
            payload.lng = Number.isFinite(lng) ? lng : null;
        }

        setDirty(false);
        onSubmit(payload);
    };

    return (
        <form className="contact-form" onSubmit={handleSubmit}>
            <label className="contact-field">
                <span>Name *</span>
                <input autoFocus type="text" value={form.name} onChange={set('name')} />
            </label>

            <label className="contact-field">
                <span>Address</span>
                <input type="text" value={form.address} onChange={set('address')} />
            </label>

            <div className="location-coord-row">
                <label className="contact-field">
                    <span>Latitude</span>
                    <input type="number" step="any" value={form.lat} onChange={setCoord('lat')} />
                </label>
                <label className="contact-field">
                    <span>Longitude</span>
                    <input type="number" step="any" value={form.lng} onChange={setCoord('lng')} />
                </label>
            </div>
            <button type="button" className="location-locate-btn" onClick={locate}
                disabled={locating || !form.address.trim()}>
                {locating ? 'Locating…' : 'Locate from address'}
            </button>
            {locateError && <p className="production-page-error">{locateError}</p>}

            <StaticMap lat={form.lat} lng={form.lng} height={160} />

            <label className="contact-field">
                <span>Primary contact</span>
                <select value={form.primary_contact_id} onChange={set('primary_contact_id')}>
                    <option value="">— none —</option>
                    {contacts.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                </select>
            </label>

            <label className="contact-field">
                <span>Permit status</span>
                <input type="text" value={form.permit_status} onChange={set('permit_status')} />
            </label>

            <label className="contact-field">
                <span>Parking notes</span>
                <textarea rows={2} value={form.parking_notes} onChange={set('parking_notes')} />
            </label>

            <label className="contact-field">
                <span>Load-in notes</span>
                <textarea rows={2} value={form.loadin_notes} onChange={set('loadin_notes')} />
            </label>

            <label className="contact-field">
                <span>Restrictions</span>
                <textarea rows={2} value={form.restrictions} onChange={set('restrictions')} />
            </label>

            <label className="contact-field">
                <span>Notes</span>
                <textarea rows={3} value={form.notes} onChange={set('notes')} />
            </label>

            <div className="contact-form-actions">
                <button type="button" className="production-modal-close" onClick={onCancel}>
                    Cancel
                </button>
                <button type="submit" className="production-new-btn"
                    disabled={saving || !form.name.trim()}>
                    {saving ? 'Saving…' : isEdit ? 'Save changes' : 'Create location'}
                </button>
            </div>
        </form>
    );
}
