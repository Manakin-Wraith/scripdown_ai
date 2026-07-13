import React, { useMemo, useState, useCallback } from 'react';
import { X, MapPin, Edit3 } from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { locationKey, subLocationLabel } from '../../utils/locationKey';
import {
    renameParentLocation,
    renameSubLocation,
    reassignSceneLocation,
    mergeParentLocations,
} from '../../services/apiService';
import './LocationManager.css';

// Build parent -> sub -> scenes tree from the loaded scenes list (client-side).
function buildTree(scenes) {
    const parents = {};
    (scenes || []).forEach((scene) => {
        if (scene.is_omitted) return;
        const parent = locationKey(scene);
        const sub = subLocationLabel(scene) || '(main)';
        if (!parents[parent]) parents[parent] = { name: parent, count: 0, subs: {} };
        if (!parents[parent].subs[sub]) parents[parent].subs[sub] = { name: sub, scenes: [] };
        parents[parent].subs[sub].scenes.push(scene);
        parents[parent].count += 1;
    });
    return Object.values(parents).sort((a, b) => a.name.localeCompare(b.name));
}

const LocationManager = ({ scriptId, scenes, onClose, onChanged }) => {
    const toast = useToast();
    const [busy, setBusy] = useState(false);
    const [expanded, setExpanded] = useState({});
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
        }
    }, [busy, toast, onChanged]);

    const doRenameParent = (parent) => {
        const to = window.prompt(`Rename location "${parent.name}" to:`, parent.name);
        if (!to || to.trim() === parent.name) return;
        run('Location renamed', () => renameParentLocation(scriptId, parent.name, to.trim()));
    };

    const doRenameSub = (parent, sub) => {
        if (sub.name === '(main)') return;
        const to = window.prompt(`Rename sub-location "${sub.name}" under ${parent.name} to:`, sub.name);
        if (!to || to.trim() === sub.name) return;
        run('Sub-location renamed', () => renameSubLocation(scriptId, parent.name, sub.name, to.trim()));
    };

    const doReassign = (scene) => {
        const to = window.prompt(`Move scene #${scene.scene_number} to which location?`, '');
        if (!to || !to.trim()) return;
        run('Scene reassigned', () => reassignSceneLocation(scriptId, scene.id || scene.scene_id, to.trim()));
    };

    const doMerge = (parent) => {
        const src = window.prompt(`Merge which location INTO "${parent.name}"? (exact name)`, '');
        if (!src || !src.trim()) return;
        run('Locations merged', () => mergeParentLocations(scriptId, parent.name, [src.trim()]));
    };

    return (
        <div className="locmgr-overlay" onClick={onClose}>
            <div className="locmgr-modal" onClick={(e) => e.stopPropagation()}>
                <div className="locmgr-header">
                    <span><MapPin size={16} /> Manage Locations</span>
                    <button className="locmgr-close" onClick={onClose} aria-label="Close"><X size={18} /></button>
                </div>
                <div className="locmgr-body">
                    {tree.length === 0 && <p className="locmgr-empty">No locations yet.</p>}
                    {tree.map((parent) => {
                        const open = expanded[parent.name] !== false;
                        return (
                            <div key={parent.name} className="locmgr-parent">
                                <div className="locmgr-parent-row">
                                    <button
                                        className="locmgr-toggle"
                                        onClick={() => setExpanded((s) => ({ ...s, [parent.name]: !open }))}
                                    >
                                        {open ? '▼' : '▶'} <strong>{parent.name}</strong>
                                        <span className="locmgr-count">{parent.count}</span>
                                    </button>
                                    <span className="locmgr-actions">
                                        <button disabled={busy} onClick={() => doRenameParent(parent)}>Rename</button>
                                        <button disabled={busy} onClick={() => doMerge(parent)}>Merge…</button>
                                    </span>
                                </div>
                                {open && Object.values(parent.subs).map((sub) => (
                                    <div key={sub.name} className="locmgr-sub-row">
                                        <span className="locmgr-sub-name">
                                            {sub.name} <span className="locmgr-count">{sub.scenes.length}</span>
                                        </span>
                                        <span className="locmgr-actions">
                                            {sub.name !== '(main)' && (
                                                <button disabled={busy} onClick={() => doRenameSub(parent, sub)}>
                                                    <Edit3 size={12} /> Rename
                                                </button>
                                            )}
                                            <button
                                                disabled={busy}
                                                onClick={() => doReassign(sub.scenes[0])}
                                                title="Reassign the first scene here to another location"
                                            >
                                                Reassign scene
                                            </button>
                                        </span>
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
