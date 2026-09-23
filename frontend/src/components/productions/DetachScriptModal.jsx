import { useState, useEffect } from 'react';
import { listProductionMembers } from '../../services/apiService';
import { Spinner } from '../ui';

export default function DetachScriptModal({ productionId, script, onConfirm, onClose }) {
    const [members, setMembers] = useState([]);
    const [keep, setKeep] = useState(() => new Set());
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        listProductionMembers(productionId)
            .then((d) => setMembers((d.members || []).filter(
                (m) => m.script_access && m.script_access !== 'none')))
            .catch((e) => setError(e.response?.data?.error || 'Failed to load members'))
            .finally(() => setLoading(false));
    }, [productionId]);

    const toggle = (userId) => setKeep((prev) => {
        const next = new Set(prev);
        if (next.has(userId)) next.delete(userId); else next.add(userId);
        return next;
    });

    const confirm = async () => {
        setBusy(true);
        setError(null);
        try {
            await onConfirm([...keep]);
        } catch (e) {
            setError(e.response?.data?.error || 'Failed to remove script');
            setBusy(false);
        }
    };

    return (
        <div className="production-modal-backdrop" onClick={onClose}>
            <div className="production-modal" onClick={(e) => e.stopPropagation()}>
                <h3>Remove “{script.title || 'Untitled script'}” from this production?</h3>
                {error && <p className="production-page-error">{error}</p>}
                {loading ? (
                    <Spinner size={24} />
                ) : members.length === 0 ? (
                    <p>No production members currently have access to this script.</p>
                ) : (
                    <>
                        <p>
                            These members will lose access to the script. Tick anyone who should
                            keep it on the script&apos;s own team.
                        </p>
                        <ul className="production-attach-list">
                            {members.map((m) => (
                                <li key={m.user_id}>
                                    <label>
                                        <input type="checkbox" checked={keep.has(m.user_id)}
                                            onChange={() => toggle(m.user_id)} />
                                        {' '}{m.name} <span>({m.script_access})</span> — keep on script
                                    </label>
                                </li>
                            ))}
                        </ul>
                    </>
                )}
                <div className="production-overview-actions">
                    <button className="production-delete-btn" disabled={busy || loading} onClick={confirm}>
                        {busy ? 'Removing…' : 'Remove script'}
                    </button>
                    <button className="production-modal-close" disabled={busy} onClick={onClose}>
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
}
