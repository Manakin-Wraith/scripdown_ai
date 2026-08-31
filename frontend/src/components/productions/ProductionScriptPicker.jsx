import { useState, useEffect } from 'react';
import { getScripts } from '../../services/apiService';
import { Spinner } from '../ui';

export default function ProductionScriptPicker({ onPick, onClose }) {
    const [scripts, setScripts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [busyId, setBusyId] = useState(null);

    useEffect(() => {
        getScripts()
            .then((data) => setScripts((data.scripts || []).filter(
                (s) => !s.production_id && (s.is_owner ?? true))))
            .catch((err) => setError(err.message || 'Failed to load scripts'))
            .finally(() => setLoading(false));
    }, []);

    const pick = async (scriptId) => {
        setBusyId(scriptId);
        try {
            await onPick(scriptId);
        } catch (err) {
            setError(err.response?.data?.error || 'Could not add that script');
            setBusyId(null);
        }
    };

    return (
        <div className="production-modal-backdrop" onClick={onClose}>
            <div className="production-modal" onClick={(e) => e.stopPropagation()}>
                <h3>Add a script</h3>
                {loading ? (
                    <Spinner size={24} />
                ) : error ? (
                    <p className="production-page-error">{error}</p>
                ) : scripts.length === 0 ? (
                    <p>Every script you own is already in a production.</p>
                ) : (
                    <ul className="production-picker-list">
                        {scripts.map((s) => (
                            <li key={s.id}>
                                <button disabled={busyId === s.id} onClick={() => pick(s.id)}>
                                    {s.title || 'Untitled script'}
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
                <button className="production-modal-close" onClick={onClose}>Close</button>
            </div>
        </div>
    );
}
