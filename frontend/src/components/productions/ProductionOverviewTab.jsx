import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Trash2, Plus, X } from 'lucide-react';
import ProductionScriptPicker from './ProductionScriptPicker';
import { scriptStatusInfo, scriptsNeedingAttention } from './scriptStatus';

const STATUSES = ['development', 'prep', 'shooting', 'wrapped', 'archived'];
const STATUS_LABELS = {
    development: 'Development', prep: 'Prep', shooting: 'Shooting',
    wrapped: 'Wrapped', archived: 'Archived',
};

const formatDate = (iso) => {
    if (!iso) return null;
    const d = new Date(`${iso}T00:00:00`);
    return Number.isNaN(d.getTime())
        ? iso
        : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
};

export default function ProductionOverviewTab({
    production, scripts, form, setForm, isOwner, canDelete = false, saving,
    onSave, onDelete, onPick, onRemove, picking, setPicking,
}) {
    const start = formatDate(production.shoot_start_date);
    const end = formatDate(production.shoot_end_date);
    const dates = start && end ? `${start} → ${end}` : (start || end || 'Dates not set');
    const totalPages = scripts.reduce((sum, s) => sum + (Number(s.total_pages) || 0), 0);
    const attention = scriptsNeedingAttention(scripts);

    // Open the settings once on mount for an owner with no title yet. Not a
    // controlled `open` prop: typing a title would otherwise collapse it mid-edit.
    const settingsRef = useRef(null);
    useEffect(() => {
        if (isOwner && !form.title && settingsRef.current) settingsRef.current.open = true;
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <>
            <section className="production-summary" aria-label="Production summary">
                <div>
                    <span className="production-summary-label">Status</span>
                    <span className={`production-row-status status-${production.status}`}>
                        {STATUS_LABELS[production.status] || production.status}
                    </span>
                </div>
                <div>
                    <span className="production-summary-label">Shoot dates</span>
                    <span className="production-summary-value">{dates}</span>
                </div>
                <div>
                    <span className="production-summary-label">Scripts</span>
                    <span className="production-summary-value">
                        {scripts.length}{totalPages > 0 ? ` · ${totalPages} pp` : ''}
                    </span>
                </div>
            </section>

            {attention.length > 0 && (
                <div className="production-attention" role="status">
                    <p>
                        <strong>{attention.length} script{attention.length === 1 ? '' : 's'} need{attention.length === 1 ? 's' : ''} attention.</strong>
                    </p>
                    <span className="production-attention-links">
                        {attention.map((s) => (
                            <Link key={s.id} to={`/scenes/${s.id}`}>{s.title || 'Untitled script'}</Link>
                        ))}
                    </span>
                </div>
            )}

            <section className="production-scripts">
                <div className="production-scripts-head">
                    <h3>Scripts</h3>
                    {canDelete && (
                        <button onClick={() => setPicking(true)}><Plus size={14} /> Add script</button>
                    )}
                </div>
                {scripts.length === 0 ? (
                    <p className="production-scripts-empty">
                        {canDelete ? 'No scripts attached yet.' : 'No scripts shared with you in this production.'}
                    </p>
                ) : (
                    <ul className="production-script-grid">
                        {scripts.map((s) => {
                            const info = scriptStatusInfo(s.analysis_status);
                            return (
                                <li key={s.id} className="production-script-card">
                                    <div className="production-script-card-top">
                                        <Link to={`/scenes/${s.id}`} className="production-script-title">
                                            {s.title || 'Untitled script'}
                                        </Link>
                                        {canDelete && (
                                            <button className="production-script-remove"
                                                onClick={() => onRemove(s)} aria-label="Remove script">
                                                <X size={14} />
                                            </button>
                                        )}
                                    </div>
                                    <div className="production-script-meta">
                                        {s.episode_number != null && <span>Ep {s.episode_number}</span>}
                                        {Number(s.total_pages) > 0 && <span>{s.total_pages} pp</span>}
                                        <span className={`production-script-status tone-${info.tone}`}>{info.label}</span>
                                    </div>
                                    <nav className="production-script-links" aria-label={`${s.title || 'Script'} sections`}>
                                        <Link to={`/scenes/${s.id}`}>Breakdown</Link>
                                        <Link to={`/scripts/${s.id}/stripboard`}>Stripboard</Link>
                                        <Link to={`/scripts/${s.id}/schedule`}>Schedule</Link>
                                    </nav>
                                </li>
                            );
                        })}
                    </ul>
                )}
            </section>

            <details className="production-settings" ref={settingsRef}>
                <summary>Production settings</summary>
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
            </details>

            {picking && (
                <ProductionScriptPicker onPick={onPick} onClose={() => setPicking(false)} />
            )}
        </>
    );
}
