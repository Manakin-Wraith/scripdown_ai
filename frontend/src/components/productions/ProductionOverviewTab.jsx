import { Link } from 'react-router-dom';
import { Trash2, Plus, X } from 'lucide-react';
import ProductionScriptPicker from './ProductionScriptPicker';

const STATUSES = ['development', 'prep', 'shooting', 'wrapped', 'archived'];

export default function ProductionOverviewTab({
    production, scripts, form, setForm, isOwner, canDelete = false, saving,
    onSave, onDelete, onPick, onRemove, picking, setPicking,
}) {
    return (
        <>
            <form className="production-overview" onSubmit={onSave}>
                <label>
                    Title
                    <input value={form.title} disabled={!isOwner}
                        onChange={(e) => setForm({ ...form, title: e.target.value })} />
                </label>
                <label>
                    Status
                    <select value={form.status} disabled={!isOwner}
                        onChange={(e) => setForm({ ...form, status: e.target.value })}>
                        {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                </label>
                <div className="production-date-row">
                    <label>
                        Shoot start
                        <input type="date" value={form.shoot_start_date} disabled={!isOwner}
                            onChange={(e) => setForm({ ...form, shoot_start_date: e.target.value })} />
                    </label>
                    <label>
                        Shoot end
                        <input type="date" value={form.shoot_end_date} disabled={!isOwner}
                            onChange={(e) => setForm({ ...form, shoot_end_date: e.target.value })} />
                    </label>
                </div>
                <label>
                    Notes
                    <textarea value={form.notes} disabled={!isOwner} rows={3}
                        onChange={(e) => setForm({ ...form, notes: e.target.value })} />
                </label>
                {(isOwner || canDelete) && (
                    <div className="production-overview-actions">
                        {isOwner && (
                            <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
                        )}
                        {canDelete && (
                            <button type="button" className="production-delete-btn" onClick={onDelete}>
                                <Trash2 size={14} /> Delete production
                            </button>
                        )}
                    </div>
                )}
            </form>

            <section className="production-scripts">
                <div className="production-scripts-head">
                    <h3>Scripts</h3>
                    {canDelete && (
                        <button onClick={() => setPicking(true)}><Plus size={14} /> Add script</button>
                    )}
                </div>
                {scripts.length === 0 ? (
                    <p className="production-scripts-empty">No scripts attached yet.</p>
                ) : (
                    <ul className="production-scripts-list">
                        {scripts.map((s) => (
                            <li key={s.id}>
                                <Link to={`/scenes/${s.id}`}>{s.title || 'Untitled script'}</Link>
                                {canDelete && (
                                    <button className="production-script-remove"
                                        onClick={() => onRemove(s.id)} aria-label="Remove script">
                                        <X size={14} />
                                    </button>
                                )}
                            </li>
                        ))}
                    </ul>
                )}
            </section>

            {picking && (
                <ProductionScriptPicker onPick={onPick} onClose={() => setPicking(false)} />
            )}
        </>
    );
}
