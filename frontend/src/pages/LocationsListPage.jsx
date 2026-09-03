import { useState, useEffect, useCallback, useRef } from 'react';
import { MapPin, Plus } from 'lucide-react';
import { listLocations, createLocation, listContacts } from '../services/apiService';
import PageHeader from '../components/layout/PageHeader';
import { Spinner } from '../components/ui';
import LocationFormModal from '../components/locations/LocationFormModal';
import LocationDetailDrawer from '../components/locations/LocationDetailDrawer';
import StaticMap from '../components/locations/StaticMap';
import './ProductionPages.css';

export default function LocationsListPage() {
    const [locations, setLocations] = useState([]);
    const [contacts, setContacts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [q, setQ] = useState('');
    const [creating, setCreating] = useState(false);
    const [saving, setSaving] = useState(false);
    const [openId, setOpenId] = useState(null);
    const firstLoad = useRef(true);

    const load = useCallback(async () => {
        try {
            const params = {};
            if (q.trim()) params.q = q.trim();
            const data = await listLocations(params);
            setLocations(data.locations || []);
            setError(null);
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Failed to load locations');
        } finally {
            setLoading(false);
        }
    }, [q]);

    useEffect(() => {
        if (firstLoad.current) {
            firstLoad.current = false;
            load();
            listContacts().then((d) => setContacts(d.contacts || [])).catch(() => {});
            return;
        }
        const t = setTimeout(load, 300);
        return () => clearTimeout(t);
    }, [load]);

    const handleCreate = async (payload) => {
        setSaving(true);
        try {
            await createLocation(payload);
            setCreating(false);
            setSaving(false);
            load();
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Failed to create location');
            setSaving(false);
        }
    };

    if (loading) {
        return <div className="production-page-loading"><Spinner size={32} /></div>;
    }
    if (error && !locations.length) {
        return <p className="production-page-error">{error}</p>;
    }

    return (
        <div className="production-page">
            <PageHeader
                title="Locations"
                subtitle="Your directory of real-world places, reusable across every production"
                actions={
                    <button className="production-new-btn" onClick={() => setCreating(true)}>
                        <Plus size={16} /> New location
                    </button>
                }
            />

            <div className="contact-toolbar">
                <input
                    type="text"
                    className="contact-search"
                    placeholder="Search locations…"
                    value={q}
                    onChange={(e) => setQ(e.target.value)}
                />
            </div>

            {error && locations.length > 0 && <p className="production-page-error">{error}</p>}

            {locations.length === 0 ? (
                <div className="production-empty-state">
                    <div className="production-empty-content">
                        <div className="production-empty-icon-wrapper">
                            <MapPin size={28} className="production-empty-icon" />
                        </div>
                        <h2>No locations yet</h2>
                        <p>Add the places you shoot at — they'll be reusable across productions.</p>
                    </div>
                </div>
            ) : (
                <table className="contact-table">
                    <thead>
                        <tr>
                            <th>Map</th>
                            <th>Name</th>
                            <th>Address</th>
                        </tr>
                    </thead>
                    <tbody>
                        {locations.map((l) => (
                            <tr key={l.id} onClick={() => setOpenId(l.id)}>
                                <td style={{ width: 96 }}>
                                    <StaticMap
                                        lat={l.lat}
                                        lng={l.lng}
                                        geocodeStatus={l.geocode_status}
                                        height={56}
                                    />
                                </td>
                                <td>{l.name}</td>
                                <td>{l.address || '—'}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}

            {creating && (
                <LocationFormModal
                    contacts={contacts}
                    onSubmit={handleCreate}
                    onClose={() => setCreating(false)}
                    saving={saving}
                />
            )}

            {openId && (
                <LocationDetailDrawer
                    locationId={openId}
                    contacts={contacts}
                    onClose={() => setOpenId(null)}
                    onChanged={load}
                    onDeleted={() => { setOpenId(null); load(); }}
                />
            )}
        </div>
    );
}
