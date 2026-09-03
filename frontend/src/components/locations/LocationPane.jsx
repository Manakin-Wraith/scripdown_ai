import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import {
    getLocation, createLocation, updateLocation, deleteLocation,
    uploadLocationPhoto, deleteLocationPhoto,
} from '../../services/apiService';
import { Spinner } from '../ui';
import LocationForm from './LocationForm';
import StaticMap from './StaticMap';

const errMsg = (err, fallback) => err.response?.data?.error || err.message || fallback;

/**
 * Right-hand detail pane for the Locations directory. `mode` comes from the
 * route: 'new' | 'view' | 'edit'.
 */
export default function LocationPane({ mode }) {
    const { locationId } = useParams();
    const navigate = useNavigate();
    const { reloadList, contacts, setPaneDirty } = useOutletContext();

    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(mode !== 'new');
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [deleteError, setDeleteError] = useState(null);
    const [uploading, setUploading] = useState(false);
    const fileRef = useRef(null);

    const load = useCallback(() => getLocation(locationId)
        .then((d) => { setData(d); setError(null); })
        .catch((err) => setError(errMsg(err, 'Failed to load location'))), [locationId]);

    useEffect(() => {
        if (mode === 'new') {
            setData(null);
            setLoading(false);
            return;
        }
        let active = true;
        setLoading(true);
        getLocation(locationId)
            .then((d) => active && (setData(d), setError(null)))
            .catch((err) => active && setError(errMsg(err, 'Failed to load location')))
            .finally(() => active && setLoading(false));
        return () => { active = false; };
    }, [locationId, mode]);

    const handleCreate = useCallback(async (payload) => {
        setSaving(true);
        setError(null);
        try {
            const d = await createLocation(payload);
            setPaneDirty(false);
            reloadList();
            navigate(`/locations/${d.location.id}`);
        } catch (err) {
            setError(errMsg(err, 'Failed to create location'));
            setSaving(false);
        }
    }, [navigate, reloadList, setPaneDirty]);

    const handleSave = useCallback(async (payload) => {
        setSaving(true);
        setError(null);
        try {
            await updateLocation(locationId, payload);
            setPaneDirty(false);
            reloadList();
            navigate(`/locations/${locationId}`);
        } catch (err) {
            setError(errMsg(err, 'Failed to save location'));
            setSaving(false);
        }
    }, [locationId, navigate, reloadList, setPaneDirty]);

    const handleDelete = useCallback(async () => {
        setDeleting(true);
        setDeleteError(null);
        try {
            await deleteLocation(locationId);
            setPaneDirty(false);
            reloadList();
            navigate('/locations');
        } catch (err) {
            if (err.response?.status === 409) {
                const usedIn = err.response.data?.used_in || [];
                setDeleteError(`Linked to ${usedIn.map((u) => u.production_title).join(', ')} — unlink it from those productions first.`);
            } else {
                setDeleteError(errMsg(err, 'Failed to delete location'));
            }
            setDeleting(false);
        }
    }, [locationId, navigate, reloadList, setPaneDirty]);

    const handleUpload = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true);
        try {
            await uploadLocationPhoto(locationId, file);
            await load();
        } catch (err) {
            setError(errMsg(err, 'Failed to upload photo'));
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
            setError(errMsg(err, 'Failed to delete photo'));
        }
    };

    const backLink = (
        <button type="button" className="directory-pane-back" onClick={() => navigate('/locations')}>
            <ArrowLeft size={15} /> All locations
        </button>
    );

    if (loading) {
        return <div className="directory-pane-empty"><Spinner size={24} /></div>;
    }
    if (error && !data && mode !== 'new') {
        return <div>{backLink}<p className="production-page-error">{error}</p></div>;
    }

    if (mode === 'new' || mode === 'edit') {
        return (
            <div>
                {backLink}
                <h3 className="directory-pane-title">
                    {mode === 'new' ? 'New location' : `Edit ${data?.location?.name || 'location'}`}
                </h3>
                {error && <p className="production-page-error">{error}</p>}
                <LocationForm
                    initial={mode === 'edit' ? data.location : undefined}
                    contacts={contacts}
                    saving={saving}
                    onDirtyChange={setPaneDirty}
                    onSubmit={mode === 'new' ? handleCreate : handleSave}
                    onCancel={() => navigate(mode === 'edit' ? `/locations/${locationId}` : '/locations')}
                />
            </div>
        );
    }

    // view
    const loc = data.location;
    const photos = data.photos || [];
    const usedIn = data.used_in || [];

    return (
        <div>
            {backLink}
            <div className="directory-pane-head">
                <h3 className="directory-pane-title">{loc.name}</h3>
                <Link className="production-new-btn" to={`/locations/${locationId}/edit`}>Edit</Link>
            </div>
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
                            <button type="button" className="location-photo-delete"
                                onClick={() => handleDeletePhoto(p.id)} aria-label="Delete photo">×</button>
                        </div>
                    ))}
                </div>
                <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp"
                    onChange={handleUpload} disabled={uploading} />
            </div>

            <div className="contact-used-on">
                <span className="contact-field-label">Used on</span>
                {usedIn.length === 0 ? (
                    <p className="production-scripts-empty">Not linked to any production yet.</p>
                ) : (
                    <ul className="contact-used-on-list">
                        {usedIn.map((u) => (
                            <li key={u.production_id}>
                                <Link to={`/productions/${u.production_id}`}>{u.production_title || 'Untitled production'}</Link>
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            <div className="contact-delete-row">
                <button type="button" className="contact-delete-btn" onClick={handleDelete} disabled={deleting}>
                    {deleting ? 'Deleting…' : 'Delete location'}
                </button>
                {deleteError && <p className="production-page-error">{deleteError}</p>}
            </div>
        </div>
    );
}
