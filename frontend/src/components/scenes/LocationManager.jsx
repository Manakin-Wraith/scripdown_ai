import React, { useMemo, useState, useCallback, useRef } from 'react';
import { X, MapPin } from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { locationKey, subLocationLabel } from '../../utils/locationKey';
import {
    renameParentLocation,
    renameSubLocation,
    nestLocation,
    unnestLocation,
} from '../../services/apiService';
import './LocationManager.css';

// Build parent -> real subs tree. A parent whose scenes sit directly on it
// (no sub-location) simply carries a higher count; no "(main)" row is rendered.
function buildTree(scenes) {
    const parents = {};
    (scenes || []).forEach((scene) => {
        if (scene.is_omitted) return;
        const parent = locationKey(scene);
        const sub = subLocationLabel(scene);
        if (!parents[parent]) parents[parent] = { name: parent, count: 0, subs: {} };
        parents[parent].count += 1;
        if (sub) {
            if (!parents[parent].subs[sub]) parents[parent].subs[sub] = { name: sub, count: 0 };
            parents[parent].subs[sub].count += 1;
        }
    });
    return Object.values(parents)
        .map((p) => ({ ...p, subs: Object.values(p.subs).sort((a, b) => a.name.localeCompare(b.name)) }))
        .sort((a, b) => a.name.localeCompare(b.name));
}

const LocationManager = ({ scriptId, scenes, onClose, onChanged }) => {
    const toast = useToast();
    const [busy, setBusy] = useState(false);
    const [editing, setEditing] = useState(null); // { kind:'parent'|'sub', parent, name }
    const [editValue, setEditValue] = useState('');
    const cancelRef = useRef(false);
    const tree = useMemo(() => buildTree(scenes), [scenes]);

    const run = useCallback(async (label, fn) => {
        if (busy) return;
        setBusy(true);
        try {
            const res = await fn();
            toast.success(label, `${res?.scenes_updated ?? 0} scene(s) updated.`);
            if (onChanged) await onChanged();
        } catch (e) {
            toast.error('Update failed', e?.response?.data?.error || e.message);
        } finally {
            setBusy(false);
            setEditing(null);
        }
    }, [busy, toast, onChanged]);

    const startEdit = (kind, parent, name) => {
        setEditing({ kind, parent, name });
        setEditValue(name);
    };

    const commitEdit = () => {
        if (cancelRef.current) { cancelRef.current = false; return; }
        if (!editing) return;
        const to = editValue.trim();
        if (!to || to === editing.name) { setEditing(null); return; }
        if (editing.kind === 'parent') {
            run('Location renamed', () => renameParentLocation(scriptId, editing.name, to));
        } else {
            run('Sub-location renamed', () => renameSubLocation(scriptId, editing.parent, editing.name, to));
        }
    };

    const onEditKey = (e) => {
        if (e.key === 'Enter') commitEdit();
        else if (e.key === 'Escape') { cancelRef.current = true; setEditing(null); }
    };

    const doNest = (source, parentName) => {
        if (!parentName) return;
        run('Location nested', () => nestLocation(scriptId, source, parentName));
    };

    const doUnnest = (parent, setName) => {
        run('Location moved out', () => unnestLocation(scriptId, parent, setName));
    };

    // A top-level location may be nested under another only if it has no real
    // subs of its own (two-level constraint). Any other top-level is a valid target.
    const parentNames = tree.map((p) => p.name);

    const renderName = (kind, parent, name) => {
        const isEditing = editing && editing.kind === kind && editing.name === name
            && (kind === 'parent' || editing.parent === parent);
        if (isEditing) {
            return (
                <input
                    className="locmgr-edit"
                    autoFocus
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onKeyDown={onEditKey}
                    onBlur={commitEdit}
                    disabled={busy}
                />
            );
        }
        return (
            <button className="locmgr-name" onClick={() => startEdit(kind, parent, name)} title="Click to rename">
                {name}
            </button>
        );
    };

    return (
        <div className="locmgr-overlay" onClick={onClose}>
            <div className="locmgr-modal" onClick={(e) => e.stopPropagation()}>
                <div className="locmgr-header">
                    <span><MapPin size={16} /> Manage Locations</span>
                    <button className="locmgr-close" onClick={onClose} aria-label="Close"><X size={18} /></button>
                </div>
                <p className="locmgr-purpose">
                    Group your locations the way you'll shoot them — nest rooms and areas under
                    the building or place they belong to.
                </p>
                <div className="locmgr-body">
                    {tree.length === 0 && <p className="locmgr-empty">No locations yet.</p>}
                    {tree.map((parent) => {
                        const nestable = parent.subs.length === 0;
                        return (
                            <div key={parent.name} className="locmgr-parent">
                                <div className="locmgr-parent-row">
                                    <span className="locmgr-parent-name">
                                        {renderName('parent', null, parent.name)}
                                        <span className="locmgr-count">{parent.count}</span>
                                    </span>
                                    {nestable && (
                                        <select
                                            className="locmgr-move"
                                            disabled={busy}
                                            value=""
                                            onChange={(e) => doNest(parent.name, e.target.value)}
                                        >
                                            <option value="">Move under…</option>
                                            {parentNames
                                                .filter((n) => n !== parent.name)
                                                .map((n) => <option key={n} value={n}>{n}</option>)}
                                        </select>
                                    )}
                                </div>
                                {parent.subs.map((sub) => (
                                    <div key={sub.name} className="locmgr-sub-row">
                                        <span className="locmgr-sub-name">
                                            {renderName('sub', parent.name, sub.name)}
                                            <span className="locmgr-count">{sub.count}</span>
                                        </span>
                                        <button
                                            className="locmgr-moveout"
                                            disabled={busy}
                                            onClick={() => doUnnest(parent.name, sub.name)}
                                        >
                                            Move out
                                        </button>
                                    </div>
                                ))}
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default LocationManager;
