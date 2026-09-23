import { useState, useEffect } from 'react';
import { getScripts } from '../../services/apiService';
import { Spinner } from '../ui';

export default function ProductionScriptPicker({ onPick, onClose }) {
    const [scripts, setScripts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [busyId, setBusyId] = useState(null);
    // Set when the server answers 409 script_has_members: {scriptId, members, invites}
    const [team, setTeam] = useState(null);

    useEffect(() => {
        getScripts()
            .then((data) => setScripts((data.scripts || []).filter(
                (s) => !s.production_id && (s.is_owner ?? true))))
            .catch((err) => setError(err.message || 'Failed to load scripts'))
            .finally(() => setLoading(false));
    }, []);

    const pick = async (scriptId, membersAction = null) => {
        setBusyId(scriptId);
        setError(null);
        try {
            await onPick(scriptId, membersAction);
        } catch (err) {
            const status = err.response?.status;
            const data = err.response?.data || {};
            if (status === 409 && data.code === 'script_has_members') {
                setTeam({ scriptId, members: data.members || [], invites: data.invites || [] });
            } else if (membersAction) {
                // The script may already be attached; re-sending the same choice
                // is safe (the server treats "already here" as success).
                setError(`${data.error || 'Moving the team failed'}. Try again.`);
            } else {
                setError(data.error || 'Could not add that script');
            }
            setBusyId(null);
        }
    };

    const teamCount = team ? team.members.length : 0;
    const inviteCount = team ? team.invites.length : 0;

    return (
        <div className="production-modal-backdrop" onClick={onClose}>
            <div className="production-modal" onClick={(e) => e.stopPropagation()}>
                <h3>{team ? 'This script has its own team' : 'Add a script'}</h3>
                {error && <p className="production-page-error">{error}</p>}
                {team ? (
                    <div className="production-attach-team">
                        <p>
                            {teamCount} team member{teamCount === 1 ? '' : 's'}
                            {inviteCount > 0 && ` and ${inviteCount} pending invite${inviteCount === 1 ? '' : 's'}`}
                            {' '}can open this script. Once it is in the production, access is
                            managed from the production&apos;s Members tab.
                        </p>
                        <ul className="production-attach-list">
                            {team.members.map((m) => (
                                <li key={m.user_id}>{m.name} <span>({m.role})</span></li>
                            ))}
                            {team.invites.map((i) => (
                                <li key={i.email}>{i.email} <span>(invite pending)</span></li>
                            ))}
                        </ul>
                        <p className="production-attach-note">
                            Moved people join the production as viewers — they will also see its
                            crew, locations and call sheets — with their script access carried over.
                        </p>
                        <div className="production-overview-actions">
                            <button disabled={!!busyId} onClick={() => pick(team.scriptId, 'move')}>
                                Move to production
                            </button>
                            <button className="production-delete-btn" disabled={!!busyId}
                                onClick={() => pick(team.scriptId, 'drop')}>
                                Remove their access
                            </button>
                            <button className="production-modal-close" disabled={!!busyId}
                                onClick={() => { setTeam(null); setError(null); }}>
                                Back
                            </button>
                        </div>
                    </div>
                ) : loading ? (
                    <Spinner size={24} />
                ) : !error && scripts.length === 0 ? (
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
                {!team && <button className="production-modal-close" onClick={onClose}>Close</button>}
            </div>
        </div>
    );
}
