import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
    getLocation, updateLocation, deleteLocation,
    uploadLocationPhoto, deleteLocationPhoto,
} from '../../services/apiService';
import { Spinner } from '../ui';
import LocationFormModal from './LocationFormModal';
import StaticMap from './StaticMap';

/**
 * Loads a single location with its photos + usage, reuses LocationFormModal
 * for editing, and adds a photo gallery and delete action.
 * Props: { locationId, contacts, onClose, onChanged, onDeleted }
 */
export default function LocationDetailDrawer({ locationId, contacts = [], onClose, onChanged, onDeleted }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [editing, setEditing] = useState(false);
    const [saving, setSaving] = useState(false);
    const [deleteError, setDeleteError] = useState(null);
    const [deleting, setDeleting] = useState(false);
    const [uploading, setUploading] = useState(false);
    const fileRef = useRef(null);

    const load = () => {
        setLoading(true);
        return getLocation(locationId)
            .then((d) => { setData(d); setError(null); })
            .catch((err) => setError(err.response?.data?.error || err.message || 'Failed to load location'))
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        let active = true;
        getLocation(locationId)
            .then((d) => { if (active) { setData(d); setError(null); } })
            .catch((err) => active && setError(err.response?.data?.error || err.message || 'Failed to load location'))
            .finally(() => active && setLoading(false));
        return () => { active = false; };
    }, [locationId]);

    const handleSave = async (payload) => {
        setSaving(true);
        setError(null);
        try {
            await updateLocation(locationId, payload);
            setEditing(false);
            setSaving(false);
            await load();
            onChanged?.();
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Failed to save location');
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        setDeleting(true);
        setDeleteError(null);
        try {
            await deleteLocation(locationId);
            onDeleted?.();
        } catch (err) {
            if (err.response?.status === 409) {
                const usedIn = err.response.data?.used_in || [];
                setDeleteError(
                    `Linked to ${usedIn.map((u) => u.production_title).join(', ')} — unlink it from those productions first.`
                );
            } else {
                setDeleteError(err.response?.data?.error || err.message || 'Failed to delete location');
            }
            setDeleting(false);
        }
    };

    const handleUpload = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true);
        try {
            await uploadLocationPhoto(locationId, file);
            await load();
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Failed to upload photo');
        } finally {
            setUploading(false);
            if (fileRef.current) fileRef.current.value = '';
        }
    };

    const handleDeletePhoto = async (photoId) => {
        try {
            await deleteLocationPhoto(locationId, photoId);
            await load();
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Failed to delete photo');
        }
    };

    if (loading) {
        return (
            <div className="production-modal-backdrop" onClick={onClose}>
                <div className="production-modal" onClick={(e) => e.stopPropagation()}>
                    <Spinner size={24} />
                </div>
            </div>
        );
    }

    if (error && !data) {
        return (
            <div className="production-modal-backdrop" onClick={onClose}>
                <div className="production-modal" onClick={(e) => e.stopPropagation()}>
                    <p className="production-page-error">{error}</p>
                    <button className="production-modal-close" onClick={onClose}>Close</button>
                </div>
            </div>
        );
    }

    if (editing) {
        return (
            <LocationFormModal
                title="Edit location"
                initial={data.location}
                contacts={contacts}
                saving={saving}
                onSubmit={handleSave}
                onClose={() => setEditing(false)}
            />
        );
    }

    const loc = data.location;
    const photos = data.photos || [];
    const usedIn = data.used_in || [];

    return (
        <div className="production-modal-backdrop" onClick={onClose}>
            <div className="production-modal" onClick={(e) => e.stopPropagation()}>
                <h3>{loc.name}</h3>
                {error && <p className="production-page-error">{error}</p>}

                <StaticMap lat={loc.lat} lng={loc.lng} geocodeStatus={loc.geocode_status} height={200} />

                <dl className="location-detail-fields">
                    {loc.address && (<><dt>Address</dt><dd>{loc.address}</dd></>)}
                    {loc.permit_status && (<><dt>Permit</dt><dd>{loc.permit_status}</dd></>)}
                    {loc.parking_notes && (<><dt>Parking</dt><dd>{loc.parking_notes}</dd></>)}
                    {loc.loadin_notes && (<><dt>Load-in</dt><dd>{loc.loadin_notes}</dd></>)}
                    {loc.restrictions && (<><dt>Restrictions</dt><dd>{loc.restrictions}</dd></>)}
                    {loc.notes && (<><dt>Notes</dt><dd>{loc.notes}</dd></>)}
                </dl>

                <div className="location-photos">
                    <span className="contact-field-label">Reference photos</span>
                    <div className="location-photo-grid">
                        {photos.map((p) => (
                            <div key={p.id} className="location-photo-thumb">
                                <img src={p.url} alt={p.caption || 'Location photo'} />
                                <button
                                    type="button"
                                    className="location-photo-delete"
                                    onClick={() => handleDeletePhoto(p.id)}
                                    aria-label="Delete photo"
                                >
                                    ×
                                </button>
                            </div>
                        ))}
                    </div>
                    <input
                        ref={fileRef}
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        onChange={handleUpload}
                        disabled={uploading}
                    />
                </div>

                <div className="contact-used-on">
                    <span className="contact-field-label">Used on</span>
                    {usedIn.length === 0 ? (
                        <p className="production-scripts-empty">Not linked to any production yet.</p>
                    ) : (
                        <ul className="contact-used-on-list">
                            {usedIn.map((u) => (
                                <li key={u.production_id}>
                                    <Link to={`/productions/${u.production_id}`}>
                                        {u.production_title || 'Untitled production'}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                <div className="contact-form-actions">
                    <button type="button" className="production-modal-close" onClick={onClose}>Close</button>
                    <button type="button" className="production-new-btn" onClick={() => setEditing(true)}>
                        Edit
                    </button>
                </div>

                <div className="contact-delete-row">
                    <button
                        type="button"
                        className="contact-delete-btn"
                        onClick={handleDelete}
                        disabled={deleting}
                    >
                        {deleting ? 'Deleting…' : 'Delete location'}
                    </button>
                    {deleteError && <p className="production-page-error">{deleteError}</p>}
                </div>
            </div>
        </div>
    );
}
