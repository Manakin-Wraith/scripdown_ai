import React, { useState, useEffect, useCallback, useRef } from 'react';
import { X, Trash2, ChevronUp, ChevronDown, Plus, Clapperboard } from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { useConfirmDialog } from '../../context/ConfirmDialogContext';
import { getSegments, createSegment, updateSegment, deleteSegment } from '../../services/apiService';
import { segmentDotColor, SEGMENT_TYPES } from '../../utils/segmentTint';
import { Spinner, SkeletonList } from '../ui';
import './SegmentManager.css';

/**
 * SegmentManager — manage timeline segments (flashbacks / montages) for a script.
 * Colour is derived from a segment's type. Renames refresh scene labels server-side.
 */
const SegmentManager = ({ scriptId, scenes, onClose, onChanged }) => {
    const toast = useToast();
    const { confirm } = useConfirmDialog();
    const [segments, setSegments] = useState([]);
    const [loading, setLoading] = useState(true);
    // busy tracks WHICH item/action is in flight so only that control spins.
    // Shape: { id, action } | null. id is null for the create action.
    const [busy, setBusy] = useState(null);
    const [editingId, setEditingId] = useState(null);
    const [editName, setEditName] = useState('');
    const [typePickerId, setTypePickerId] = useState(null);
    const [newName, setNewName] = useState('');
    const [newType, setNewType] = useState('MONTAGE');

    const isBusy = busy != null;
    const busyIs = (id, action) => busy?.id === id && busy?.action === action;

    const load = useCallback(async () => {
        setLoading(true);
        try { setSegments(await getSegments(scriptId)); }
        catch { setSegments([]); }
        finally { setLoading(false); }
    }, [scriptId]);
    useEffect(() => { load(); }, [load]);

    const countFor = useCallback(
        (segId) => (scenes || []).filter(s => s.segment_id === segId).length,
        [scenes]
    );

    const run = async (fn, errMsg, marker) => {
        if (isBusy) return;
        setBusy(marker);
        try {
            await fn();
            await load();
            if (onChanged) await onChanged();
        } catch (e) {
            console.error('[SegmentManager]', e);
            toast.error('Something went wrong', errMsg);
        } finally {
            setBusy(null);
        }
    };

    const cancelRenameRef = useRef(false);
    const startRename = (seg) => { setEditingId(seg.id); setEditName(seg.name); };
    const saveRename = (seg) => {
        const name = editName.trim();
        setEditingId(null);
        if (!name || name === seg.name) return;
        run(() => updateSegment(seg.id, { name }), 'Couldn’t rename the segment. Try again.', { id: seg.id, action: 'rename' });
    };

    const setType = (seg, code) => {
        setTypePickerId(null);
        if (code === seg.segment_type) return;
        run(() => updateSegment(seg.id, { segment_type: code }), 'Couldn’t recolour the segment. Try again.', { id: seg.id, action: 'type' });
    };

    const move = (index, dir) => {
        const target = index + dir;
        if (target < 0 || target >= segments.length) return;
        const reordered = [...segments];
        const [moved] = reordered.splice(index, 1);
        reordered.splice(target, 0, moved);
        run(async () => {
            // Normalize display_order to list position. Existing values may all
            // be 0, so a pairwise swap can't express order — assign each its index.
            await Promise.all(
                reordered
                    .map((seg, i) => (seg.display_order === i ? null : updateSegment(seg.id, { display_order: i })))
                    .filter(Boolean)
            );
        }, 'Couldn’t reorder the segments. Try again.', { id: moved.id, action: 'move' });
    };

    const remove = async (seg) => {
        const ok = await confirm({
            title: 'Delete segment',
            message: `Delete “${seg.name}”? Its scenes return to the story-day timeline.`,
            confirmText: 'Delete',
        });
        if (!ok) return;
        run(() => deleteSegment(seg.id, scriptId), 'Couldn’t delete the segment. Try again.', { id: seg.id, action: 'delete' });
    };

    const create = () => {
        const name = newName.trim();
        if (!name) return;
        run(async () => {
            await createSegment(scriptId, { name, segment_type: newType });
            setNewName('');
            setNewType('MONTAGE');
        }, 'Couldn’t create the segment. Try again.', { id: null, action: 'create' });
    };

    return (
        <div className="segmgr-overlay" onClick={onClose}>
            <div className="segmgr" onClick={e => e.stopPropagation()} role="dialog" aria-modal="true">
                <div className="segmgr-header">
                    <div className="segmgr-title"><Clapperboard size={16} /> Segments</div>
                    <button className="segmgr-close" onClick={onClose} aria-label="Close"><X size={18} /></button>
                </div>

                <div className="segmgr-body">
                    {loading && <SkeletonList count={4} rowHeight={34} label="Loading segments" />}
                    {!loading && segments.length === 0 && (
                        <p className="segmgr-empty">
                            No segments yet. Group flashback or montage scenes from a scene’s detail panel,
                            or create one below.
                        </p>
                    )}
                    {!loading && segments.map((seg, i) => {
                        const n = countFor(seg.id);
                        return (
                            <div className="segmgr-row" key={seg.id}>
                                <div className="segmgr-swatch-wrap">
                                    {busyIs(seg.id, 'type') ? (
                                        <span className="segmgr-swatch-spin"><Spinner size={14} label="Recolouring" /></span>
                                    ) : (
                                        <button
                                            className="segmgr-swatch"
                                            style={{ background: segmentDotColor(seg.segment_type) }}
                                            onClick={() => setTypePickerId(typePickerId === seg.id ? null : seg.id)}
                                            disabled={isBusy}
                                            title="Change type / colour"
                                        />
                                    )}
                                    {typePickerId === seg.id && (
                                        <div className="segmgr-type-picker">
                                            {SEGMENT_TYPES.map(t => (
                                                <button
                                                    key={t.code}
                                                    className="segmgr-type-option"
                                                    onClick={() => setType(seg, t.code)}
                                                >
                                                    <span className="segmgr-dot" style={{ background: segmentDotColor(t.code) }} />
                                                    {t.label}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>

                                {editingId === seg.id ? (
                                    <input
                                        className="segmgr-name-input"
                                        value={editName}
                                        autoFocus
                                        onChange={e => setEditName(e.target.value)}
                                        onBlur={() => {
                                            if (cancelRenameRef.current) { cancelRenameRef.current = false; setEditingId(null); return; }
                                            saveRename(seg);
                                        }}
                                        onKeyDown={e => {
                                            // Enter commits via blur (single save path); Escape cancels.
                                            if (e.key === 'Enter') e.currentTarget.blur();
                                            if (e.key === 'Escape') { cancelRenameRef.current = true; e.currentTarget.blur(); }
                                        }}
                                    />
                                ) : (
                                    <button className="segmgr-name" onClick={() => startRename(seg)} disabled={isBusy} title="Click to rename">
                                        {seg.name}
                                        {busyIs(seg.id, 'rename') && <span className="segmgr-name-spin"><Spinner size={13} label="Renaming" /></span>}
                                    </button>
                                )}

                                <span className="segmgr-count">{n} {n === 1 ? 'scene' : 'scenes'}</span>

                                <div className="segmgr-actions">
                                    {busyIs(seg.id, 'move') ? (
                                        <span className="segmgr-actions-spin"><Spinner size={15} label="Reordering" /></span>
                                    ) : busyIs(seg.id, 'delete') ? (
                                        <span className="segmgr-actions-spin"><Spinner size={15} label="Deleting" /></span>
                                    ) : (
                                        <>
                                            <button className="segmgr-icon-btn" disabled={isBusy || i === 0} onClick={() => move(i, -1)} title="Move up"><ChevronUp size={15} /></button>
                                            <button className="segmgr-icon-btn" disabled={isBusy || i === segments.length - 1} onClick={() => move(i, 1)} title="Move down"><ChevronDown size={15} /></button>
                                            <button className="segmgr-icon-btn segmgr-delete" disabled={isBusy} onClick={() => remove(seg)} title="Delete"><Trash2 size={15} /></button>
                                        </>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>

                <div className="segmgr-create">
                    <select className="segmgr-type-select" value={newType} onChange={e => setNewType(e.target.value)}>
                        {SEGMENT_TYPES.map(t => <option key={t.code} value={t.code}>{t.label}</option>)}
                    </select>
                    <input
                        className="segmgr-create-input"
                        placeholder="New segment name"
                        value={newName}
                        onChange={e => setNewName(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') create(); }}
                        disabled={isBusy}
                    />
                    <button className="segmgr-add" onClick={create} disabled={!newName.trim() || isBusy} title="Create segment">
                        {busyIs(null, 'create') ? <Spinner size={16} label="Creating" /> : <Plus size={16} />}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default SegmentManager;
