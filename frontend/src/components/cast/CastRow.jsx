// frontend/src/components/cast/CastRow.jsx
import { ChevronRight, TriangleAlert } from 'lucide-react';
import StatusBadge from './StatusBadge';
import TierBadge from './TierBadge';

function Avatar({ row }) {
    const url = row.casting?.headshot_url;
    if (url) return <img className="cast-row-avatar" src={url} alt="" />;
    if (!row.casting) return <span className="cast-row-avatar cast-row-avatar--empty" aria-hidden />;
    const initials = row.name.split(/\s+/).slice(0, 2).map((w) => w[0]).join('');
    return <span className="cast-row-avatar cast-row-avatar--mono" aria-hidden>{initials}</span>;
}

export default function CastRow({ row, onOpen }) {
    const actor = row.casting?.actor_name;
    const conflictCount = row.conflicts.length;
    const label = `${row.name} — ${actor || 'not cast'}${row.casting ? `, ${row.casting.status}` : ''}`;
    return (
        <button className="cast-row" onClick={onOpen} aria-label={label}>
            <Avatar row={row} />
            <span className="cast-row-main">
                <span className="cast-row-name">{row.name}</span>
                {row.scene_count != null && (
                    <span className="cast-row-sub">{row.scene_count} scenes</span>
                )}
            </span>
            <TierBadge tier={row.casting?.tier} />
            <span className="cast-row-actor">
                {actor || <span className="cast-row-addcta">Add casting &rarr;</span>}
            </span>
            {row.casting && <StatusBadge status={row.casting.status} />}
            {conflictCount > 0 && (
                <span className="cast-row-conflict" aria-label={`${conflictCount} availability conflicts`}>
                    <TriangleAlert size={13} aria-hidden /> {conflictCount} conflicts
                </span>
            )}
            {row.orphaned && <span className="cast-row-tag">Not in breakdown</span>}
            <ChevronRight size={16} className="cast-row-chev" aria-hidden />
        </button>
    );
}
