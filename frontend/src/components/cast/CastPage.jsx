// frontend/src/components/cast/CastPage.jsx
import { useEffect, useMemo, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Users, UsersRound, ChevronRight, ChevronDown } from 'lucide-react';
import { getCasting, getCastingConflicts, getCastingGroups } from '../../services/apiService';
import { SkeletonList, EmptyState } from '../ui';
import CastRow from './CastRow';
import CastGroupRow from './CastGroupRow';
import CastingDetailPanel from './CastingDetailPanel';
import CastingGroupPanel from './CastingGroupPanel';
import './CastPage.css';

const STATUS_FILTERS = ['all', 'wishlist', 'offer', 'booked', 'declined', 'released', 'uncast'];

const TIER_LABELS = { lead: 'Leads', supporting: 'Supporting', featured: 'Featured', uncast: 'Uncast' };
const TIER_ORDER = ['lead', 'supporting', 'featured', 'uncast'];

const TIER_OF = (r) => r.casting?.tier || null; // null = uncast breakdown char

function TierSection({ id, title, rows, collapsed, onToggle, openRow }) {
    return (
        <div className="cast-tier-section">
            <button className="cast-tier-head" aria-expanded={!collapsed} onClick={onToggle}>
                {collapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
                {title} <span className="cast-tier-count">&middot; {rows.length}</span>
            </button>
            {!collapsed && rows.length > 0 && (
                <div className="cast-list">
                    {rows.map((row) => (
                        <CastRow key={(row.orphaned ? 'orphan:' : '') + row.name}
                                 row={row} onOpen={() => openRow(row)} />
                    ))}
                </div>
            )}
        </div>
    );
}

export default function CastPage() {
    const { scriptId } = useParams();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [casting, setCasting] = useState([]);
    const [characters, setCharacters] = useState([]);
    const [conflicts, setConflicts] = useState([]);
    const [groups, setGroups] = useState([]);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [tab, setTab] = useState('principals');
    const [openId, setOpenId] = useState(null); // casting id OR `new:<CHARACTER>` OR `group:<id>` OR `new-group`

    const COLLAPSE_KEY = `castTierCollapsed:${scriptId}`;
    const [collapsed, setCollapsed] = useState(() => {
        try {
            const raw = localStorage.getItem(COLLAPSE_KEY);
            if (raw == null) return new Set(['uncast']); // Uncast collapsed on first visit
            return new Set(JSON.parse(raw));
        } catch {
            return new Set(['uncast']);
        }
    });
    const toggleSection = (key) => setCollapsed((prev) => {
        const next = new Set(prev);
        next.has(key) ? next.delete(key) : next.add(key);
        try { localStorage.setItem(COLLAPSE_KEY, JSON.stringify([...next])); } catch { /* ignore */ }
        return next;
    });

    const fetchData = useCallback(async () => {
        const data = await getCasting(scriptId);
        setCasting(data.casting || []);
        setCharacters(data.characters || []);
        try {
            const g = await getCastingGroups(scriptId);
            setGroups(g.groups || []);
        } catch {
            setGroups([]);
        }
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
        } catch (e) {
            console.error('Cast refresh failed:', e);
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

    const principals = useMemo(() => {
        const buckets = { lead: [], supporting: [], featured: [], uncast: [] };
        for (const r of rows.base) {
            const t = TIER_OF(r);
            if (t === 'background') continue; // background individual -> Background tab
            if (t) buckets[t].push(r); else buckets.uncast.push(r);
        }
        for (const r of rows.orphans) {
            const t = TIER_OF(r);
            if (t && t !== 'background') buckets[t].push(r);
        }
        return buckets;
    }, [rows]);

    const backgroundIndividuals = useMemo(
        () => [...rows.base, ...rows.orphans].filter((r) => TIER_OF(r) === 'background'),
        [rows],
    );

    const principalsCount = principals.lead.length + principals.supporting.length
        + principals.featured.length + principals.uncast.length;
    const backgroundCount = backgroundIndividuals.length + groups.length;

    const applyFilters = (list) => list.filter((r) => {
        const q = search.trim().toLowerCase();
        if (q && !r.name.toLowerCase().includes(q)
            && !(r.casting?.actor_name || '').toLowerCase().includes(q)) return false;
        if (statusFilter === 'all') return true;
        if (statusFilter === 'uncast') return !r.casting;
        return r.casting?.status === statusFilter;
    });

    const visibleGroups = groups
        .filter((g) => (statusFilter === 'all' || statusFilter === 'uncast') ? true : g.status === statusFilter)
        .filter((g) => !search.trim() || (g.label || '').toLowerCase().includes(search.trim().toLowerCase()));

    const bookedCount = casting.filter((c) => c.status === 'booked').length
        + groups.filter((g) => g.status === 'booked').length;
    const conflictCharCount = new Set(conflicts.map((c) => c.character_name)).size;

    const openRow = (row) => setOpenId(row.casting ? row.casting.id : `new:${row.name}`);
    const clearFilters = () => { setSearch(''); setStatusFilter('all'); };

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

    const principalsTierRows = TIER_ORDER.map((tier) => ({ tier, rows: applyFilters(principals[tier]) }));
    const principalsEmpty = principalsTierRows.every((s) => s.rows.length === 0);
    const bgIndividuals = applyFilters(backgroundIndividuals);
    const backgroundEmptyAfterFilter = bgIndividuals.length === 0 && visibleGroups.length === 0 && groups.length > 0;

    return (
        <div className="cast-page">
            <div className="cast-page-head">
                <h1>Cast</h1>
                <p className="cast-summary">
                    {principalsCount} principals
                    {groups.length > 0 && ` · ${groups.length} background ${groups.length === 1 ? 'group' : 'groups'}`}
                    {' · '}{bookedCount} booked
                    {conflictCharCount > 0 && (
                        <span className="cast-summary-conflict">
                            {' '}&middot; {conflictCharCount} {conflictCharCount === 1 ? 'conflict' : 'conflicts'}
                        </span>
                    )}
                </p>
            </div>

            <div className="cast-tabbar">
                <div className="cast-tabs" role="tablist" aria-label="Cast view">
                    <button role="tab" aria-selected={tab === 'principals'}
                            className={tab === 'principals' ? 'active' : ''}
                            onClick={() => setTab('principals')}>Principals ({principalsCount})</button>
                    <button role="tab" aria-selected={tab === 'background'}
                            className={tab === 'background' ? 'active' : ''}
                            onClick={() => setTab('background')}>Background ({backgroundCount})</button>
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
            </div>

            {tab === 'principals' && (
                principalsEmpty ? (
                    <div className="cast-nomatch">
                        No characters match. <button onClick={clearFilters}>Clear filters</button>
                    </div>
                ) : (
                    principalsTierRows.map(({ tier, rows: tierRows }) => (
                        <TierSection
                            key={tier}
                            id={tier}
                            title={TIER_LABELS[tier]}
                            rows={tierRows}
                            collapsed={collapsed.has(tier)}
                            onToggle={() => toggleSection(tier)}
                            openRow={openRow}
                        />
                    ))
                )
            )}

            {tab === 'background' && (
                <>
                    {bgIndividuals.length > 0 && (
                        <>
                            <div className="cast-divider">Individuals</div>
                            <div className="cast-list">
                                {bgIndividuals.map((row) => (
                                    <CastRow key={`bg:${row.name}`} row={row} onOpen={() => openRow(row)} />
                                ))}
                            </div>
                        </>
                    )}
                    <div className="cast-divider">Groups</div>
                    {groups.length === 0 ? (
                        <EmptyState
                            icon={UsersRound}
                            title="No background yet"
                            message="Add a background group for crowd scenes, or set a character’s tier to Background."
                            action={<button onClick={() => setOpenId('new-group')}>New group</button>}
                        />
                    ) : backgroundEmptyAfterFilter ? (
                        <div className="cast-nomatch">
                            No groups match. <button onClick={clearFilters}>Clear filters</button>
                        </div>
                    ) : (
                        <div className="cast-list">
                            {visibleGroups.map((g) => (
                                <CastGroupRow key={g.id} group={g} onOpen={() => setOpenId(`group:${g.id}`)} />
                            ))}
                        </div>
                    )}
                    {groups.length > 0 && (
                        <button className="cast-newgroup" onClick={() => setOpenId('new-group')}>+ New group</button>
                    )}
                </>
            )}

            {(openId?.startsWith('group:') || openId === 'new-group') ? (
                <CastingGroupPanel
                    scriptId={scriptId}
                    group={openId === 'new-group' ? null : groups.find((g) => g.id === openId.slice(6)) || null}
                    onClose={() => setOpenId(null)}
                    onChanged={refresh}
                    onCreated={(id) => setOpenId(`group:${id}`)}
                />
            ) : openId ? (
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
            ) : null}
        </div>
    );
}
