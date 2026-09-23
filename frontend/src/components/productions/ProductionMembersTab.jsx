import { useState, useEffect, useCallback } from 'react';
import {
    listProductionMembers,
    addProductionMember,
    updateProductionMember,
    removeProductionMember,
    revokeProductionInvite,
} from '../../services/apiService';
import { Spinner } from '../ui';

const ROLES = ['viewer', 'coordinator', 'admin'];

const CAP_LABELS = {
    can_view_sensitive: 'See rates & phone',
    can_edit_crew: 'Edit crew',
    can_manage_members: 'Manage members',
    can_edit_production: 'Edit production',
    can_edit_call_sheets: 'Edit call sheets',
    can_edit_call_sheet_template: 'Edit call sheet template',
};

const PRESETS = {
    admin: {
        can_view_sensitive: true,
        can_edit_crew: true,
        can_manage_members: true,
        can_edit_production: true,
        can_edit_call_sheets: true,
        can_edit_call_sheet_template: true,
        script_access: 'edit',
    },
    coordinator: {
        can_view_sensitive: false,
        can_edit_crew: true,
        can_manage_members: false,
        can_edit_production: false,
        can_edit_call_sheets: true,
        can_edit_call_sheet_template: true,
        script_access: 'edit',
    },
    viewer: {
        can_view_sensitive: false,
        can_edit_crew: false,
        can_manage_members: false,
        can_edit_production: false,
        can_edit_call_sheets: false,
        can_edit_call_sheet_template: false,
        script_access: 'view',
    },
};

const RANK = { viewer: 1, coordinator: 2, admin: 3, owner: 4 };

const SCRIPT_ACCESS_OPTIONS = [
    { value: 'none', label: 'None' },
    { value: 'view', label: 'View' },
    { value: 'edit', label: 'Edit' },
];
const ACCESS_RANK = { none: 0, view: 1, edit: 2 };

// Machine-readable `code` values the members API returns → friendly copy.
const CODE_MESSAGES = {
    no_seats_available: 'All paid seats are in use. Purchase more seats to add members.',
    tier_2_required: 'Team features require an active Team License.',
    duplicate_member: 'That person is already a member of this production.',
    duplicate_invite: 'An invite is already pending for that email address.',
    rank_denied: 'You cannot grant a role or permission above your own.',
    bad_role: 'Pick one of: viewer, coordinator, admin.',
    cannot_target_owner: 'The production owner already has full access.',
    bad_script_access: 'Script access must be None, View or Edit.',
};

export default function ProductionMembersTab({ productionId, access, scriptCount = 0 }) {
    const [members, setMembers] = useState([]);
    const [invites, setInvites] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [adding, setAdding] = useState(false);

    const myRank = RANK[access?.role] || 0;
    const isOwner = access?.role === 'owner';
    const myAccessRank = isOwner ? ACCESS_RANK.edit : (ACCESS_RANK[access?.script_access] ?? 0);
    const accessAllowed = (v) => isOwner || ACCESS_RANK[v] <= myAccessRank;

    // `isActive` lets the mount effect below cancel state updates after unmount;
    // manual refreshes call load() with no argument and always apply.
    const load = useCallback((isActive = () => true) => {
        setLoading(true);
        return listProductionMembers(productionId)
            .then((d) => {
                if (!isActive()) return;
                setMembers(d.members || []);
                setInvites(d.invites || []);
                setError(null);
            })
            .catch((e) => {
                if (isActive()) setError(e.response?.data?.error || 'Failed to load members');
            })
            .finally(() => { if (isActive()) setLoading(false); });
    }, [productionId]);

    useEffect(() => {
        let active = true;
        load(() => active);
        return () => { active = false; };
    }, [load]);

    const patchMember = async (m, patch) => {
        try {
            const { member } = await updateProductionMember(productionId, m.id, patch);
            setMembers((prev) => prev.map((x) => (x.id === member.id ? member : x)));
            setError(null);
        } catch (e) {
            setError(e.response?.data?.error || 'Update failed');
        }
    };

    const remove = async (m) => {
        if (!window.confirm(`Remove ${m.name || m.email} from this production?`)) return;
        try {
            await removeProductionMember(productionId, m.id);
            setMembers((prev) => prev.filter((x) => x.id !== m.id));
            setError(null);
        } catch (e) {
            setError(e.response?.data?.error || 'Remove failed');
        }
    };

    const revoke = async (inv) => {
        if (!window.confirm(`Revoke the invite for ${inv.email}?`)) return;
        try {
            await revokeProductionInvite(inv.id);
            setInvites((prev) => prev.filter((x) => x.id !== inv.id));
            setError(null);
        } catch (e) {
            setError(e.response?.data?.error || 'Revoke failed');
        }
    };

    if (loading) {
        return <div className="production-page-loading"><Spinner size={32} /></div>;
    }

    return (
        <div className="production-members">
            <div className="production-scripts-head">
                <h3>Members</h3>
                <div className="production-crew-actions">
                    <button onClick={() => setAdding(true)}>Add member</button>
                </div>
            </div>

            <p className="members-script-hint">
                Script access applies to all scripts in this production ({scriptCount}).
            </p>

            {error && <p className="production-page-error">{error}</p>}

            <div className="members-table-wrap">
                <table className="members-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Role</th>
                            <th>Script access</th>
                            {Object.values(CAP_LABELS).map((l) => <th key={l}>{l}</th>)}
                            <th aria-label="Actions" />
                        </tr>
                    </thead>
                    <tbody>
                        {members.map((m) => {
                            const locked = (RANK[m.role] || 0) >= myRank && !isOwner;
                            return (
                                <tr key={m.id}>
                                    <td>{m.name}</td>
                                    <td>{m.email}</td>
                                    <td>
                                        <select
                                            value={m.role}
                                            disabled={locked}
                                            onChange={(e) => patchMember(m, {
                                                role: e.target.value,
                                                ...PRESETS[e.target.value],
                                            })}
                                        >
                                            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                                        </select>
                                    </td>
                                    <td>
                                        <select
                                            value={m.script_access || 'none'}
                                            disabled={locked}
                                            onChange={(e) => patchMember(m, { script_access: e.target.value })}
                                        >
                                            {SCRIPT_ACCESS_OPTIONS.map((o) => (
                                                <option key={o.value} value={o.value}
                                                    disabled={!accessAllowed(o.value) && o.value !== m.script_access}>
                                                    {o.label}
                                                </option>
                                            ))}
                                        </select>
                                    </td>
                                    {Object.keys(CAP_LABELS).map((c) => (
                                        <td key={c} className="members-cap-cell">
                                            <input
                                                type="checkbox"
                                                checked={!!m[c]}
                                                disabled={locked}
                                                onChange={(e) => patchMember(m, { [c]: e.target.checked })}
                                            />
                                        </td>
                                    ))}
                                    <td className="members-row-actions">
                                        {!locked && (
                                            <button type="button" onClick={() => remove(m)}>Remove</button>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                        {members.length === 0 && (
                            <tr>
                                <td colSpan={4 + Object.keys(CAP_LABELS).length + 1} className="members-empty">
                                    No members yet.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {invites.length > 0 && (
                <>
                    <h3 className="members-invites-heading">Pending invites</h3>
                    <div className="members-table-wrap">
                        <table className="members-table">
                            <thead>
                                <tr>
                                    <th>Email</th>
                                    <th>Role</th>
                                    <th>Script access</th>
                                    <th>Sent</th>
                                    <th aria-label="Actions" />
                                </tr>
                            </thead>
                            <tbody>
                                {invites.map((inv) => (
                                    <tr key={inv.id}>
                                        <td>{inv.email}</td>
                                        <td>{inv.role}</td>
                                        <td>{inv.script_access || 'none'}</td>
                                        <td>{(inv.created_at || '').slice(0, 10)}</td>
                                        <td className="members-row-actions">
                                            <button type="button" onClick={() => revoke(inv)}>Revoke</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}

            {adding && (
                <AddMemberModal
                    productionId={productionId}
                    myRank={myRank}
                    isOwner={isOwner}
                    accessAllowed={accessAllowed}
                    onClose={() => setAdding(false)}
                    onDone={() => { setAdding(false); load(); }}
                    setError={setError}
                />
            )}
        </div>
    );
}

function AddMemberModal({ productionId, myRank, isOwner, accessAllowed, onClose, onDone, setError }) {
    const [email, setEmail] = useState('');
    const [role, setRole] = useState('viewer');
    const [flags, setFlags] = useState(PRESETS.viewer);
    const [touched, setTouched] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    const changeRole = (r) => {
        setRole(r);
        if (!touched) setFlags(PRESETS[r]);
    };

    const roleAllowed = (r) => isOwner || RANK[r] < myRank;

    const submit = async (e) => {
        e.preventDefault();
        if (submitting) return;
        setSubmitting(true);
        try {
            await addProductionMember(productionId, { email: email.trim(), role, ...flags });
            onDone();
        } catch (err) {
            const code = err.response?.data?.code;
            setError(CODE_MESSAGES[code] || err.response?.data?.error || 'Failed to add member');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="production-modal-backdrop" onClick={onClose}>
            <div className="production-modal" onClick={(e) => e.stopPropagation()}>
                <h3>Add member</h3>
                <form className="contact-form" onSubmit={submit}>
                    <label className="contact-field">
                        <span>Email</span>
                        <input
                            type="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                        />
                    </label>

                    <label className="contact-field">
                        <span>Role</span>
                        <select value={role} onChange={(e) => changeRole(e.target.value)}>
                            {ROLES.filter(roleAllowed).map((r) => (
                                <option key={r} value={r}>{r}</option>
                            ))}
                        </select>
                    </label>

                    <label className="contact-field">
                        <span>Script access</span>
                        <select
                            value={flags.script_access}
                            onChange={(e) => {
                                setTouched(true);
                                setFlags((f) => ({ ...f, script_access: e.target.value }));
                            }}
                        >
                            {SCRIPT_ACCESS_OPTIONS.filter((o) => accessAllowed(o.value)).map((o) => (
                                <option key={o.value} value={o.value}>{o.label}</option>
                            ))}
                        </select>
                    </label>

                    <details className="members-advanced">
                        <summary>Advanced permissions</summary>
                        {Object.keys(CAP_LABELS).map((c) => (
                            <label key={c} className="members-cap-check">
                                <input
                                    type="checkbox"
                                    checked={!!flags[c]}
                                    onChange={(e) => {
                                        setTouched(true);
                                        setFlags((f) => ({ ...f, [c]: e.target.checked }));
                                    }}
                                />
                                {CAP_LABELS[c]}
                            </label>
                        ))}
                    </details>

                    <div className="contact-form-actions">
                        <button type="button" className="production-modal-close" onClick={onClose}>
                            Cancel
                        </button>
                        <button type="submit" className="production-new-btn" disabled={submitting}>
                            {submitting ? 'Adding…' : 'Add member'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
