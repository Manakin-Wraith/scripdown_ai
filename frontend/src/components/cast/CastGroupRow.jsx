// frontend/src/components/cast/CastGroupRow.jsx
import { ChevronRight } from 'lucide-react';
import StatusBadge from './StatusBadge';

export default function CastGroupRow({ group, onOpen }) {
    const n = group.scene_ids?.length || 0;
    return (
        <button className="cast-group-row" onClick={onOpen}
                aria-label={`${group.label}, ${group.headcount} people, ${group.status}, ${n} scenes`}>
            <span className="cast-group-label">{group.label}</span>
            <span className="cast-group-count">×{group.headcount}</span>
            <span className={`cast-group-scenes${n === 0 ? ' cast-group-scenes--none' : ''}`}>
                {n === 0 ? 'No scenes' : `${n} scene${n === 1 ? '' : 's'}`}
            </span>
            <StatusBadge status={group.status} />
            <ChevronRight size={16} className="cast-row-chev" />
        </button>
    );
}
