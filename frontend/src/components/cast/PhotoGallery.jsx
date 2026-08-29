// frontend/src/components/cast/PhotoGallery.jsx
import { useState } from 'react';
import { ChevronRight, ChevronDown, Plus, X } from 'lucide-react';
import { addCastingPhoto, deleteCastingPhoto } from '../../services/apiService';

const KIND_LABEL = { headshot: 'Headshot', full_body: 'Full body', other: 'Other' };
const KINDS = ['full_body', 'headshot', 'other'];

export default function PhotoGallery({ castingId, primaryUrl, photos = [], canEdit, onPrimaryChange, onPhotosChange, onPrimaryFile }) {
    const [open, setOpen] = useState(false);
    const [kind, setKind] = useState('full_body');
    const [busy, setBusy] = useState(false);
    const [err, setErr] = useState(null);

    const add = async (file) => {
        if (!file) return;
        if (file.size > 5 * 1024 * 1024) { setErr('That image is over 5 MB. Use a smaller file.'); return; }
        setBusy(true); setErr(null);
        try {
            const { photo } = await addCastingPhoto(castingId, file, kind);
            onPhotosChange([...photos, photo]);
            setOpen(true);
        } catch { setErr('Couldn’t add that photo.'); }
        finally { setBusy(false); }
    };
    const remove = async (id) => {
        setBusy(true);
        try { await deleteCastingPhoto(id); onPhotosChange(photos.filter((p) => p.id !== id)); }
        catch { setErr('Couldn’t remove that photo.'); }
        finally { setBusy(false); }
    };

    return (
        <div className="cd-photos">
            <div className="cd-photo-primary">
                {primaryUrl ? <img src={primaryUrl} alt="Primary headshot" />
                            : <span className="cd-photo-empty">No photo</span>}
                {canEdit && (
                    <label className="cd-photo-btn">
                        {primaryUrl ? 'Replace' : 'Upload'}
                        <input type="file" accept="image/jpeg,image/png,image/webp" hidden
                               onChange={(e) => onPrimaryFile(e.target.files?.[0])} />
                    </label>
                )}
            </div>

            {(photos.length > 0 || canEdit) && (
                <button type="button" className="cd-photo-expander" onClick={() => setOpen((o) => !o)}>
                    {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    {photos.length} more {photos.length === 1 ? 'photo' : 'photos'}
                </button>
            )}

            {open && (
                <div className="cd-photo-thumbs">
                    {photos.map((p) => (
                        <figure key={p.id} className="cd-photo-thumb">
                            <img src={p.url} alt={KIND_LABEL[p.kind]} />
                            <figcaption>{KIND_LABEL[p.kind]}</figcaption>
                            {canEdit && (
                                <button type="button" className="cd-photo-remove"
                                        aria-label={`Remove ${KIND_LABEL[p.kind]} photo`}
                                        onClick={() => remove(p.id)}><X size={12} /></button>
                            )}
                        </figure>
                    ))}
                    {canEdit && (
                        <div className="cd-photo-add">
                            <select value={kind} onChange={(e) => setKind(e.target.value)} disabled={busy}>
                                {KINDS.map((k) => <option key={k} value={k}>{KIND_LABEL[k]}</option>)}
                            </select>
                            <label className="cd-photo-addtile">
                                <Plus size={16} />
                                <input type="file" accept="image/jpeg,image/png,image/webp" hidden
                                       disabled={busy} onChange={(e) => add(e.target.files?.[0])} />
                            </label>
                        </div>
                    )}
                </div>
            )}
            {err && <p className="cd-photo-err">{err}</p>}
        </div>
    );
}
