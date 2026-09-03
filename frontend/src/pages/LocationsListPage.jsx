import { useCallback, useEffect, useRef, useState } from 'react';
import { Outlet, useLocation, useParams } from 'react-router-dom';
import { MapPin } from 'lucide-react';
import { listLocations, listContacts } from '../services/apiService';
import { Spinner } from '../components/ui';
import DirectoryShell from '../components/directory/DirectoryShell';
import StaticMap from '../components/locations/StaticMap';
import useGuardedNav from '../components/directory/useGuardedNav';
import './ProductionPages.css';

export default function LocationsListPage() {
    const location = useLocation();
    const { locationId } = useParams();
    const { setPaneDirty, guardedNav } = useGuardedNav();

    const [locations, setLocations] = useState([]);
    const [contacts, setContacts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [q, setQ] = useState('');
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

    const isIndex = location.pathname === '/locations';

    const list = loading ? (
        <div className="production-page-loading"><Spinner size={24} /></div>
    ) : locations.length === 0 ? (
        <p className="production-scripts-empty">Add the places you shoot at — they'll be reusable across productions.</p>
    ) : (
        <ul className="directory-row-list">
            {locations.map((l) => (
                <li key={l.id}>
                    <button
                        type="button"
                        className={`directory-row${l.id === locationId ? ' is-active' : ''}`}
                        onClick={() => guardedNav(`/locations/${l.id}`)}
                    >
                        <span className="directory-row-thumb directory-row-thumb--lg">
                            {l.lat != null && l.lng != null
                                ? <StaticMap lat={l.lat} lng={l.lng} geocodeStatus={l.geocode_status} height={52} />
                                : <span className="directory-row-thumb-blank"><MapPin size={18} /></span>}
                        </span>
                        <span className="directory-row-body">
                            <span className="directory-row-title">{l.name}</span>
                            <span className="directory-row-sub directory-row-sub--2line">{l.address || 'No address'}</span>
                            {l.permit_status && <span className="directory-row-meta">Permit: {l.permit_status}</span>}
                        </span>
                    </button>
                </li>
            ))}
        </ul>
    );

    const toolbar = (
        <div className="contact-toolbar">
            <input
                type="text"
                className="contact-search"
                placeholder="Search locations…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
            />
        </div>
    );

    return (
        <DirectoryShell
            title="Locations"
            subtitle="Your directory of real-world places, reusable across every production"
            newLabel="New location"
            onNew={() => guardedNav('/locations/new')}
            toolbar={toolbar}
            list={list}
            error={error && locations.length > 0 ? error : null}
            hasSelection={!isIndex}
        >
            {isIndex ? (
                <div className="directory-pane-empty">
                    <MapPin size={28} />
                    <p>Select a location, or add a new one.</p>
                </div>
            ) : null}
            <Outlet context={{ reloadList: load, contacts, setPaneDirty }} />
        </DirectoryShell>
    );
}
