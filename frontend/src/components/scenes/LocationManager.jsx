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
// (no sub-location) simply carries a higher count; no standalone-main row is rendered.
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
    const [addingUnder, setAddingUnder] = useState(null); // parent name whose Add picker is open
    const [picked, setPicked] = useState([]);             // checked source names
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
            setAddingUnder(null);
            setPicked([]);
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

    // Eligible to group under parent P: any OTHER top-level location that does
    // not already hold its own group (keeps grouping two-level).
    const eligibleFor = (parentName) =>
        tree.filter((t) => t.name !== parentName && t.subs.length === 0).map((t) => t.name);

    const openAdd = (parentName) => {
        setAddingUnder((cur) => (cur === parentName ? null : parentName));
        setPicked([]);
    };

    const togglePick = (name) =>
        setPicked((cur) => (cur.includes(name) ? cur.filter((n) => n !== name) : [...cur, name]));

    const doAddSelected = (parentName) => {
        const sources = picked;
        if (!sources.length) return;
        run('Locations grouped', async () => {
            let total = 0;
            for (const src of sources) {
                const res = await nestLocation(scriptId, src, parentName);
                total += res?.scenes_updated ?? 0;
            }
            return { scenes_updated: total };
        });
    };

    const doRemove = (parent, setName) => {
        run('Location removed', () => unnestLocation(scriptId, parent, setName));
    };

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
                    Group the locations you'll shoot together — add them under one
                    heading so they schedule as a unit.
                </p>
                <div className="locmgr-body">
                    {tree.length === 0 && <p className="locmgr-empty">No locations yet.</p>}
                    {tree.map((parent) => {
                        const isAdding = addingUnder === parent.name;
                        const candidates = isAdding ? eligibleFor(parent.name) : [];
                        return (
                            <div key={parent.name} className="locmgr-parent">
                                <div className="locmgr-parent-row">
                                    <span className="locmgr-parent-name">
                                        {renderName('parent', null, parent.name)}
                                        <span className="locmgr-count">{parent.count}</span>
                                    </span>
                                    <button
                                        className="locmgr-add"
                                        disabled={busy}
                                        onClick={() => openAdd(parent.name)}
                                    >
                                        {isAdding ? 'Cancel' : '+ Add'}
                                    </button>
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
                                            onClick={() => doRemove(parent.name, sub.name)}
                                        >
                                            Remove
                                        </button>
                                    </div>
                                ))}
                                {isAdding && (
                                    <div className="locmgr-picker">
                                        {candidates.length === 0 && (
                                            <p className="locmgr-picker-empty">No other locations to add.</p>
                                        )}
                                        {candidates.map((name) => (
                                            <label key={name} className="locmgr-picker-row">
                                                <input
                                                    type="checkbox"
                                                    checked={picked.includes(name)}
                                                    onChange={() => togglePick(name)}
                                                    disabled={busy}
                                                />
                                                <span>{name}</span>
                                            </label>
                                        ))}
                                        {candidates.length > 0 && (
                                            <div className="locmgr-picker-actions">
                                                <button
                                                    className="locmgr-add"
                                                    disabled={busy || picked.length === 0}
                                                    onClick={() => doAddSelected(parent.name)}
                                                >
                                                    Add selected
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default LocationManager;
