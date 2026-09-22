import { ArrowUp, ArrowDown, Trash2, Plus } from 'lucide-react';
import { moveItem, updateAt, removeAt, errorsFor, panelErrors, blankDepartment } from './templateUtils';

export default function DepartmentsPanel({ items, onChange, canEdit, errors }) {
    const set = (i, patch) => onChange(updateAt(items, i, patch));
    return (
        <section className="cst-panel">
            <div className="cst-panel-head">
                <h4>Department calls</h4>
                <span className="cst-hint">Default call time and &ldquo;As per&rdquo; contact per department. Each day can override.</span>
            </div>
            {panelErrors(errors, 'departments').map((m) => <div key={m} className="cst-error">{m}</div>)}
            {items.map((d, i) => (
                <div key={d.key} className="cst-row">
                    <input aria-label="Department" value={d.label} disabled={!canEdit}
                           onChange={(e) => set(i, { label: e.target.value })} />
                    <input aria-label="Default call" type="time" value={d.default_call} disabled={!canEdit}
                           onChange={(e) => set(i, { default_call: e.target.value })} />
                    <input aria-label="As per" placeholder="As per…" value={d.as_per} disabled={!canEdit}
                           onChange={(e) => set(i, { as_per: e.target.value })} />
                    {canEdit && (
                        <span className="cst-actions">
                            <button type="button" aria-label="Move up" onClick={() => onChange(moveItem(items, i, -1))}><ArrowUp size={14} /></button>
                            <button type="button" aria-label="Move down" onClick={() => onChange(moveItem(items, i, 1))}><ArrowDown size={14} /></button>
                            <button type="button" aria-label="Remove" onClick={() => onChange(removeAt(items, i))}><Trash2 size={14} /></button>
                        </span>
                    )}
                    {errorsFor(errors, `departments[${i}]`).map((m) => <div key={m} className="cst-error">{m}</div>)}
                </div>
            ))}
            {canEdit && (
                <button type="button" className="cst-add" onClick={() => onChange([...items, blankDepartment(items)])}>
                    <Plus size={14} /> Add department
                </button>
            )}
        </section>
    );
}
