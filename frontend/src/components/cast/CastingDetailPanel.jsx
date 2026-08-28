// frontend/src/components/cast/CastingDetailPanel.jsx
import { useEffect, useRef, useState } from 'react';
import { Drawer } from '../ui';
import {
    createCasting, updateCasting, deleteCasting, uploadHeadshot,
} from '../../services/apiService';
import UnavailabilityEditor from './UnavailabilityEditor';
import './CastingDetailPanel.css';

const STATUSES = ['wishlist', 'offer', 'booked', 'declined', 'released'];
const LABEL = { wishlist: 'Wishlist', offer: 'Offer', booked: 'Booked', declined: 'Declined', released: 'Released' };

export default function CastingDetailPanel({
    scriptId, casting, characterName, conflicts, onClose, onChanged,
}) {
    const [row, setRow] = useState(casting);
    const [saveState, setSaveState] = useState('idle'); // idle | saving | error
    const [canEdit, setCanEdit] = useState(true);
    const rowIdRef = useRef(casting?.id || null);

    useEffect(() => { setRow(casting); rowIdRef.current = casting?.id || null; }, [casting]);

    const myConflicts = conflicts.filter((c) => c.character_name === (row?.character_name || characterName));

    // Ensure a casting row exists, then apply `fields`. Returns updated row.
    const persist = async (fields) => {
        setSaveState('saving');
        try {
            let id = rowIdRef.current;
            if (!id) {
                const created = await createCasting(scriptId, characterName);
                id = created.casting.id;
                rowIdRef.current = id;
                setRow(created.casting);
            }
            const res = await updateCasting(id, fields);
            setRow(res.casting);
            setSaveState('idle');
            onChanged();
            return res.casting;
        } catch (e) {
            if (e?.response?.status === 403) { setCanEdit(false); setSaveState('idle'); return null; }
            setSaveState('error');
            return null;
        }
    };

    const field = (name) => ({
        defaultValue: row?.[name] ?? '',
        onBlur: (e) => { if (e.target.value !== (row?.[name] ?? '')) persist({ [name]: e.target.value }); },
        disabled: !canEdit,
    });

    const onHeadshot = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        if (file.size > 5 * 1024 * 1024) { setSaveState('error'); return; }
        setSaveState('saving');
        try {
            let id = rowIdRef.current;
            if (!id) { const c = await createCasting(scriptId, characterName); id = c.casting.id; rowIdRef.current = id; }
            const res = await uploadHeadshot(id, file);
            setRow(res.casting); setSaveState('idle'); onChanged();
        } catch { setSaveState('error'); }
    };

    const onDelete = async () => {
        if (!rowIdRef.current) { onClose(); return; }
        if (!window.confirm(`Delete casting for ${row.character_name}? This removes the actor, contacts, headshot, and availability for this character. It doesn’t affect the breakdown.`)) return;
        await deleteCasting(rowIdRef.current);
        onChanged();
        onClose();
    };

    const subtitle = row?.orphaned
        ? 'Not in the latest breakdown — details are kept.'
        : (row ? null : 'Not cast yet.');

    return (
        <Drawer
            isOpen
            onClose={onClose}
            width="440px"
            title={row?.character_name || characterName}
            subtitle={subtitle}
            subHeader={
                <span className="cd-savestate">
                    {saveState === 'saving' && 'Saving…'}
                    {saveState === 'idle' && '✓ All changes saved'}
                    {saveState === 'error' && '⚠ Couldn’t save — change a field to retry'}
                </span>
            }
            footer={canEdit && rowIdRef.current
                ? <button className="cd-delete" onClick={onDelete}>Delete casting</button>
                : null}
        >
            {!canEdit && <p className="cd-muted">Only the owner and admins can edit casting.</p>}

            {myConflicts.length > 0 && (
                <div className="cd-conflict-callout">
                    <strong>Conflicts with {myConflicts.length} shoot {myConflicts.length === 1 ? 'day' : 'days'}</strong>
                    <span>{myConflicts.map((c) => `Day ${c.day_number} (${c.shoot_date})`).join(' · ')}</span>
                </div>
            )}

            <label className="cd-label">Actor</label>
            <input type="text" {...field('actor_name')} placeholder="Actor name" />

            <label className="cd-label">Status</label>
            <div className="cd-status" role="radiogroup" aria-label="Status">
                {STATUSES.map((s) => (
                    <button
                        key={s}
                        role="radio"
                        aria-checked={(row?.status || 'wishlist') === s}
                        className={(row?.status || 'wishlist') === s ? 'active' : ''}
                        disabled={!canEdit}
                        onClick={() => persist({ status: s })}
                    >{LABEL[s]}</button>
                ))}
            </div>

            <label className="cd-label">Headshot</label>
            <div className="cd-headshot">
                {row?.headshot_url
                    ? <img src={row.headshot_url} alt={`${row.character_name} headshot`} />
                    : <span className="cd-headshot-empty">No photo</span>}
                {canEdit && (
                    <label className="cd-headshot-btn">
                        {row?.headshot_url ? 'Replace' : 'Upload'}
                        <input type="file" accept="image/jpeg,image/png,image/webp" onChange={onHeadshot} hidden />
                    </label>
                )}
            </div>

            {'contact_phone' in (row || {}) || canEdit ? (
                <>
                    <p className="cd-section">Contact</p>
                    <label className="cd-label">Phone</label>
                    <input type="tel" {...field('contact_phone')} />
                    <label className="cd-label">Email</label>
                    <input type="email" {...field('contact_email')} />
                    <label className="cd-label">Agent</label>
                    <textarea rows={2} {...field('agent_contact')} placeholder="Agency, agent name, phone" />
                </>
            ) : null}

            <p className="cd-section">Availability</p>
            {rowIdRef.current
                ? <UnavailabilityEditor
                    castingId={rowIdRef.current}
                    ranges={row?.unavailability || []}
                    canEdit={canEdit}
                    onChanged={onChanged}
                  />
                : <p className="cd-muted">Add an actor or status first to record unavailable dates.</p>}

            <label className="cd-label">Notes</label>
            <textarea rows={3} {...field('notes')} />
        </Drawer>
    );
}
