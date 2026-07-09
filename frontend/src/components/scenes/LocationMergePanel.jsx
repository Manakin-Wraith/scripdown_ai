import { useEffect, useState } from 'react';
import { getLocationSuggestions, mergeLocations } from '../../services/apiService';

// Surfaces auto-suggested duplicate locations. Merges are user-confirmed.
export default function LocationMergePanel({ scriptId, onMerged }) {
    const [suggestions, setSuggestions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [busyIdx, setBusyIdx] = useState(null);

    const load = async () => {
        setLoading(true);
        try {
            const data = await getLocationSuggestions(scriptId);
            setSuggestions(data.suggestions || []);
        } catch (e) {
            console.error('Failed to load location suggestions', e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { if (scriptId) load(); }, [scriptId]);

    const handleMerge = async (group, idx) => {
        setBusyIdx(idx);
        try {
            const aliases = group.members.filter((m) => m !== group.canonical);
            await mergeLocations(scriptId, group.canonical, aliases);
            await load();
            if (onMerged) onMerged();
        } catch (e) {
            console.error('Merge failed', e);
        } finally {
            setBusyIdx(null);
        }
    };

    if (loading) return <div className="location-merge-panel">Checking for duplicate locations…</div>;
    if (!suggestions.length) return null;

    return (
        <div className="location-merge-panel">
            <h4>Possible duplicate locations</h4>
            {suggestions.map((g, idx) => (
                <div key={idx} className="location-merge-suggestion">
                    <span>
                        {g.members.join('  ·  ')} → <strong>{g.canonical}</strong>
                        {g.reason === 'typo' ? ' (possible typo)' : ' (name variant)'}
                    </span>
                    <button disabled={busyIdx === idx} onClick={() => handleMerge(g, idx)}>
                        {busyIdx === idx ? 'Merging…' : 'Merge'}
                    </button>
                </div>
            ))}
        </div>
    );
}
