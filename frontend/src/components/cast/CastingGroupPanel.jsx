// frontend/src/components/cast/CastingGroupPanel.jsx
import { useEffect, useMemo, useRef, useState } from 'react';
import { Drawer } from '../ui';
import { useConfirmDialog } from '../../context/ConfirmDialogContext';
import {
    getScenes, createCastingGroup, updateCastingGroup,
    deleteCastingGroup, setCastingGroupScenes,
} from '../../services/apiService';
import './CastingDetailPanel.css';

const STATUSES = ['wishlist', 'offer', 'booked', 'declined', 'released'];
const LABEL = { wishlist: 'Wishlist', offer: 'Offer', booked: 'Booked', declined: 'Declined', released: 'Released' };

const sceneHeading = (s) => `${s.int_ext || 'INT'}. ${s.setting || ''} — ${s.time_of_day || 'DAY'}`;

export default function CastingGroupPanel({ scriptId, group, onClose, onChanged, onCreated }) {
    const { confirm } = useConfirmDialog();
    const [row, setRow] = useState(group);
    const [saveState, setSaveState] = useState('idle');
    const [canEdit, setCanEdit] = useState(true);
    const [scenes, setScenes] = useState([]);
    const [sceneFilter, setSceneFilter] = useState('');
    const [localSceneIds, setLocalSceneIds] = useState(new Set(group?.scene_ids || []));
    const idRef = useRef(group?.id || null);
    const createPromise = useRef(null);
    const flushTimer = useRef(null);
    const sceneIdsRef = useRef(localSceneIds);

    useEffect(() => { sceneIdsRef.current = localSceneIds; }, [localSceneIds]);

    useEffect(() => {
        getScenes(scriptId).then((d) => setScenes(d.scenes || [])).catch(() => setScenes([]));
    }, [scriptId]);
    useEffect(() => {
        setRow(group);
        idRef.current = group?.id || null;
        setLocalSceneIds(new Set(group?.scene_ids || []));
    }, [group]);

    const ensureRow = () => {
        if (idRef.current) return Promise.resolve(idRef.current);
        if (!createPromise.current) {
            const label = (draft.label ?? row?.label ?? '').trim();
            if (!label) return Promise.reject(new Error('label'));
            createPromise.current = createCastingGroup(scriptId, { label })
                .then(({ group: g }) => { idRef.current = g.id; setRow(g); onCreated?.(g.id); return g.id; })
                .catch((e) => { createPromise.current = null; throw e; });
        }
        return createPromise.current;
    };

    const persist = async (fields) => {
        setSaveState('saving');
        try {
            const id = await ensureRow();
            const { group: g } = await updateCastingGroup(id, fields);
            setRow(g); setSaveState('idle'); onChanged();
        } catch (e) {
            if (e?.message === 'label') { setSaveState('idle'); return; }
            if (e?.response?.status === 403) { setCanEdit(false); setSaveState('idle'); return; }
            setSaveState('error');
        }
    };

    const flushScenes = async (ids) => {
        try { const id = await ensureRow(); await setCastingGroupScenes(id, [...ids]); onChanged(); }
        catch (e) {
            if (e?.response?.status === 403) { setCanEdit(false); }
            /* keep local state; retry on next toggle */
        }
    };
    const toggleScene = (sid) => {
        setLocalSceneIds((prev) => {
            const next = new Set(prev);
            next.has(sid) ? next.delete(sid) : next.add(sid);
            clearTimeout(flushTimer.current);
            flushTimer.current = setTimeout(() => flushScenes(next), 600);
            return next;
        });
    };
    useEffect(() => () => {
        clearTimeout(flushTimer.current);
        if (idRef.current) flushScenes(sceneIdsRef.current);
    }, []); // flush on unmount

    const [draft, setDraft] = useState({});
    useEffect(() => { setDraft({}); }, [row?.id]);
    const val = (name) => (name in draft ? draft[name] : (row?.[name] ?? ''));
    const field = (name, transform = (v) => v) => ({
        value: val(name),
        onChange: (e) => setDraft((d) => ({ ...d, [name]: e.target.value })),
        onBlur: (e) => {
            const v = transform(e.target.value);
            if (v !== (row?.[name] ?? '')) persist({ [name]: v });
            setDraft((d) => { const n = { ...d }; delete n[name]; return n; });
        },
        disabled: !canEdit,
    });

    const onDelete = async () => {
        if (!idRef.current) { onClose(); return; }
        const ok = await confirm({
            title: 'Delete this background group?',
            message: `This removes “${row.label}” and its scene links. It doesn’t affect the breakdown or the schedule.`,
            variant: 'danger',
            confirmText: 'Delete group',
        });
        if (!ok) return;
        await deleteCastingGroup(idRef.current); onChanged(); onClose();
    };

    const visibleScenes = useMemo(() => {
        const q = sceneFilter.trim().toLowerCase();
        return scenes.filter((s) => !q
            || String(s.scene_number).includes(q)
            || sceneHeading(s).toLowerCase().includes(q));
    }, [scenes, sceneFilter]);

    return (
        <Drawer isOpen onClose={onClose} width="440px"
                title={row?.label || 'New background group'} subtitle="Background group"
                subHeader={<span className="cd-savestate">
                    {saveState === 'saving' && 'Saving…'}
                    {saveState === 'idle' && '✓ All changes saved'}
                    {saveState === 'error' && '⚠ Couldn’t save — change a field to retry'}
                </span>}
                footer={canEdit && idRef.current ? <button className="cd-delete" onClick={onDelete}>Delete group</button> : null}>
            {!canEdit && <p className="cd-muted">Only the owner and admins can edit casting.</p>}

            <label className="cd-label">Label</label>
            <input type="text" {...field('label')} placeholder="e.g. Restaurant patrons" />

            <div className="cd-tier-status">
                <div>
                    <label className="cd-label" htmlFor="grp-headcount">Headcount</label>
                    <input id="grp-headcount" type="number" min="1"
                           {...field('headcount', (v) => Math.max(1, parseInt(v || '1', 10)))} />
                </div>
                <div>
                    <label className="cd-label" htmlFor="grp-status">Status</label>
                    <select id="grp-status" value={row?.status || 'wishlist'} disabled={!canEdit}
                            onChange={(e) => persist({ status: e.target.value })}>
                        {STATUSES.map((s) => <option key={s} value={s}>{LABEL[s]}</option>)}
                    </select>
                </div>
            </div>

            <label className="cd-label">Day rate (optional)</label>
            <span className="cd-rate">
                <span>R</span>
                <input type="number" min="0" {...field('day_rate', (v) => (v === '' ? null : Number(v)))} />
            </span>

            <p className="cd-section">Scenes</p>
            {scenes.length > 12 && (
                <input type="search" className="cast-search" placeholder="Search scenes…"
                       value={sceneFilter} onChange={(e) => setSceneFilter(e.target.value)} />
            )}
            <div className="cd-scene-list" role="group" aria-label="Scenes">
                {visibleScenes.map((s) => (
                    <label key={s.id} className="cd-scene-item">
                        <input type="checkbox" checked={localSceneIds.has(s.id)} disabled={!canEdit}
                               onChange={() => toggleScene(s.id)} />
                        <span>{s.scene_number} · {sceneHeading(s)}</span>
                    </label>
                ))}
            </div>

            <label className="cd-label">Notes</label>
            <textarea rows={3} {...field('notes')} />
        </Drawer>
    );
}
