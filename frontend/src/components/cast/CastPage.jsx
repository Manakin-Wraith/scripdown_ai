// frontend/src/components/cast/CastPage.jsx
import { useEffect, useMemo, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Users } from 'lucide-react';
import { getCasting, getCastingConflicts } from '../../services/apiService';
import { SkeletonList, EmptyState } from '../ui';
import CastRow from './CastRow';
import CastingDetailPanel from './CastingDetailPanel';
import './CastPage.css';

const STATUS_FILTERS = ['all', 'wishlist', 'offer', 'booked', 'declined', 'released', 'uncast'];

export default function CastPage() {
    const { scriptId } = useParams();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [casting, setCasting] = useState([]);
    const [characters, setCharacters] = useState([]);
    const [conflicts, setConflicts] = useState([]);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [openId, setOpenId] = useState(null); // casting id OR `new:<CHARACTER>`

    const fetchData = useCallback(async () => {
        const data = await getCasting(scriptId);
        setCasting(data.casting || []);
        setCharacters(data.characters || []);
        try {
            const conf = await getCastingConflicts(scriptId);
            setConflicts(conf.conflicts || []);
        } catch {
            setConflicts([]);
        }
    }, [scriptId]);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            await fetchData();
        } catch (e) {
            setError('Couldn’t load casting. Check your connection and try again.');
        } finally {
            setLoading(false);
        }
    }, [fetchData]);

    // Silent refetch for post-save updates from the detail drawer — never toggles
    // `loading`, so the drawer stays mounted and keeps its local state.
    const refresh = useCallback(async () => {
        try {
            await fetchData();
        } catch {
            /* keep showing stale data; the drawer stays open */
        }
    }, [fetchData]);

    useEffect(() => { load(); }, [load]);

    const castingByName = useMemo(
        () => Object.fromEntries(casting.map((c) => [c.character_name, c])),
        [casting],
    );
    const conflictsByName = useMemo(() => {
        const m = {};
        for (const c of conflicts) (m[c.character_name] ||= []).push(c);
        return m;
    }, [conflicts]);

    // Breakdown characters + orphaned casting rows (no matching breakdown char).
    const rows = useMemo(() => {
        const breakdownNames = new Set(characters.map((c) => c.name));
        const base = characters.map((c) => ({
            name: c.name,
            scene_count: c.scene_count,
            casting: castingByName[c.name] || null,
            conflicts: conflictsByName[c.name] || [],
            orphaned: false,
        }));
        const orphans = casting
            .filter((c) => !breakdownNames.has(c.character_name))
            .map((c) => ({
                name: c.character_name,
                scene_count: null,
                casting: c,
                conflicts: conflictsByName[c.character_name] || [],
                orphaned: true,
            }));
        return { base, orphans };
    }, [characters, casting, castingByName, conflictsByName]);

    const applyFilters = (list) => list.filter((r) => {
        const q = search.trim().toLowerCase();
        if (q && !r.name.toLowerCase().includes(q)
            && !(r.casting?.actor_name || '').toLowerCase().includes(q)) return false;
        if (statusFilter === 'all') return true;
        if (statusFilter === 'uncast') return !r.casting;
        return r.casting?.status === statusFilter;
    });

    const visibleBase = applyFilters(rows.base);
    const visibleOrphans = applyFilters(rows.orphans);

    const bookedCount = casting.filter((c) => c.status === 'booked').length;
    const conflictCharCount = new Set(conflicts.map((c) => c.character_name)).size;

    const openRow = (row) => setOpenId(row.casting ? row.casting.id : `new:${row.name}`);

    if (loading) {
        return (
            <div className="cast-page">
                <div className="cast-page-head"><h1>Cast</h1></div>
                <SkeletonList count={6} />
            </div>
        );
    }

    if (error) {
        return (
            <div className="cast-page">
                <div className="cast-page-head"><h1>Cast</h1></div>
                <div className="cast-error">
                    {error} <button onClick={load}>Retry</button>
                </div>
            </div>
        );
    }

    if (characters.length === 0 && casting.length === 0) {
        return (
            <div className="cast-page">
                <div className="cast-page-head"><h1>Cast</h1></div>
                <EmptyState
                    icon={Users}
                    title="No characters yet"
                    message="Run the breakdown on your scenes to detect characters — then cast them here."
                    action={<button onClick={() => navigate(`/scenes/${scriptId}`)}>Go to Scenes</button>}
                />
            </div>
        );
    }

    return (
        <div className="cast-page">
            <div className="cast-page-head">
                <h1>Cast</h1>
                <p className="cast-summary">
                    {characters.length} characters &middot; {bookedCount} booked
                    {conflictCharCount > 0 && (
                        <span className="cast-summary-conflict">
                            {' '}&middot; {conflictCharCount} availability {conflictCharCount === 1 ? 'conflict' : 'conflicts'}
                        </span>
                    )}
                </p>
            </div>

            <div className="cast-filterbar">
                <input
                    className="cast-search"
                    type="search"
                    placeholder="Search characters…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
                <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                    {STATUS_FILTERS.map((s) => (
                        <option key={s} value={s}>
                            {s === 'all' ? 'All statuses'
                                : s === 'uncast' ? 'Not cast'
                                : s[0].toUpperCase() + s.slice(1)}
                        </option>
                    ))}
                </select>
            </div>

            {visibleBase.length === 0 && visibleOrphans.length === 0 ? (
                <div className="cast-nomatch">
                    No characters match. <button onClick={() => { setSearch(''); setStatusFilter('all'); }}>Clear filters</button>
                </div>
            ) : (
                <div className="cast-list">
                    {visibleBase.map((row) => (
                        <CastRow key={row.name} row={row} onOpen={() => openRow(row)} />
                    ))}
                    {visibleOrphans.length > 0 && (
                        <>
                            <div className="cast-divider">Not in current breakdown</div>
                            {visibleOrphans.map((row) => (
                                <CastRow key={`orphan:${row.name}`} row={row} onOpen={() => openRow(row)} />
                            ))}
                        </>
                    )}
                </div>
            )}

            {openId && (
                <CastingDetailPanel
                    scriptId={scriptId}
                    openId={openId}
                    casting={openId.startsWith('new:') ? null
                        : casting.find((c) => c.id === openId) || null}
                    characterName={openId.startsWith('new:') ? openId.slice(4)
                        : (casting.find((c) => c.id === openId)?.character_name)}
                    conflicts={conflicts}
                    onClose={() => setOpenId(null)}
                    onChanged={refresh}
                    onCreated={(id) => setOpenId(id)}
                />
            )}
        </div>
    );
}
