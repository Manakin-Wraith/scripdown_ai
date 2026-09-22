import { ArrowUp, ArrowDown, Trash2, Plus } from 'lucide-react';
import { moveItem, updateAt, removeAt, errorsFor, panelErrors, blankLabelled } from './templateUtils';

/** Label + one value: used for boilerplate blocks (body, multiline) and key crew (value, single line). */
export default function KeyValueListPanel({
    title, hint, items, onChange, valueField, multiline, canEdit, errors, errorPrefix, addLabel,
}) {
    const set = (i, patch) => onChange(updateAt(items, i, patch));
    return (
        <section className="cst-panel">
            <div className="cst-panel-head">
                <h4>{title}</h4>
                {hint && <span className="cst-hint">{hint}</span>}
            </div>
            {panelErrors(errors, errorPrefix).map((m) => <div key={m} className="cst-error">{m}</div>)}
            {items.map((item, i) => (
                <div key={item.key} className="cst-row">
                    <input aria-label="Label" value={item.label} disabled={!canEdit}
                           onChange={(e) => set(i, { label: e.target.value })} />
                    {multiline ? (
                        <textarea aria-label="Text" rows={3} value={item[valueField]} disabled={!canEdit}
                                  onChange={(e) => set(i, { [valueField]: e.target.value })} />
                    ) : (
                        <input aria-label="Value" value={item[valueField]} disabled={!canEdit}
                               onChange={(e) => set(i, { [valueField]: e.target.value })} />
                    )}
                    {canEdit && (
                        <span className="cst-actions">
                            <button type="button" aria-label="Move up" onClick={() => onChange(moveItem(items, i, -1))}><ArrowUp size={14} /></button>
                            <button type="button" aria-label="Move down" onClick={() => onChange(moveItem(items, i, 1))}><ArrowDown size={14} /></button>
                            <button type="button" aria-label="Remove" onClick={() => onChange(removeAt(items, i))}><Trash2 size={14} /></button>
                        </span>
                    )}
                    {errorsFor(errors, `${errorPrefix}[${i}]`).map((m) => <div key={m} className="cst-error">{m}</div>)}
                </div>
            ))}
            {canEdit && (
                <button type="button" className="cst-add"
                        onClick={() => onChange([...items, blankLabelled(items, valueField)])}>
                    <Plus size={14} /> {addLabel}
                </button>
            )}
        </section>
    );
}
