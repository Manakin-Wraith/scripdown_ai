// frontend/src/components/productions/ProductionCastTab.jsx
// Cast for a production: one card per script (cast stays stored per script),
// each opening that script's cast page in place under the production.
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Users, ChevronRight } from 'lucide-react';
import { getCasting } from '../../services/apiService';
import { EmptyState } from '../ui';
import CastPage from '../cast/CastPage';
import './ProductionCastTab.css';

function ScriptCastCard({ productionId, script }) {
    const [summary, setSummary] = useState(null); // null = loading, false = failed

    useEffect(() => {
        let cancelled = false;
        getCasting(script.id)
            .then((d) => {
                if (cancelled) return;
                const casting = d.casting || [];
                setSummary({
                    characters: (d.characters || []).length,
                    booked: casting.filter((c) => c.status === 'booked').length,
                    offers: casting.filter((c) => c.status === 'offer').length,
                });
            })
            .catch(() => { if (!cancelled) setSummary(false); });
        return () => { cancelled = true; };
    }, [script.id]);

    let meta = 'Loading…';
    if (summary === false) meta = 'Couldn’t load cast';
    else if (summary) {
        meta = summary.characters === 0
            ? 'No characters yet'
            : `${summary.characters} characters · ${summary.booked} booked`
              + (summary.offers ? ` · ${summary.offers} offer${summary.offers === 1 ? '' : 's'}` : '');
    }

    return (
        <Link to={`/productions/${productionId}/cast/${script.id}`} className="production-cast-card">
            <Users size={18} />
            <span className="production-cast-card-body">
                <span className="production-cast-card-title">{script.title || 'Untitled script'}</span>
                <span className="production-cast-card-meta">{meta}</span>
            </span>
            <ChevronRight size={16} />
        </Link>
    );
}

export default function ProductionCastTab({ productionId, scripts, scriptId }) {
    if (scriptId) {
        const script = scripts.find((s) => String(s.id) === String(scriptId));
        // Not in this production, or not visible to this member.
        if (!script) {
            return (
                <EmptyState
                    icon={Users}
                    title="Script not available"
                    message="This script isn’t part of the production, or you don’t have access to it."
                    action={<Link to={`/productions/${productionId}/cast`}>Back to cast</Link>}
                />
            );
        }
        // The breadcrumb (Productions › Production › Cast › Script) is the way back.
        return <CastPage key={scriptId} scriptId={scriptId} />;
    }

    if (scripts.length === 0) {
        return (
            <EmptyState
                icon={Users}
                title="No scripts yet"
                message="Add a script to this production on the Overview tab, then cast its characters here."
            />
        );
    }

    return (
        <div className="production-cast-list">
            {scripts.map((s) => <ScriptCastCard key={s.id} productionId={productionId} script={s} />)}
        </div>
    );
}
