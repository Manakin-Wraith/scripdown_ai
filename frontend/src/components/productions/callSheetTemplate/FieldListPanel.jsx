import { ArrowUp, ArrowDown, Trash2, Lock, Plus } from 'lucide-react';
import {
    FIELD_TYPES, DAY_FIELD_SECTIONS, moveItem, updateAt, removeAt,
    errorsFor, panelErrors, blankDayField, blankColumn,
} from './templateUtils';

/** mode 'day': built-in-aware day-info fields. mode 'column': table columns. */
export default function FieldListPanel({ title, hint, items, onChange, mode, canEdit, errors, errorPrefix }) {
    const isDay = mode === 'day';
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
                    {item.builtin && <Lock size={12} title="Built-in field: can be hidden or renamed, not removed" />}
                    <input aria-label="Label" value={item.label} disabled={!canEdit}
                           onChange={(e) => set(i, { label: e.target.value })} />
                    <select aria-label="Type" value={item.type} disabled={!canEdit || item.builtin}
                            onChange={(e) => set(i, { type: e.target.value })}>
                        {FIELD_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                    {isDay && (
                        <select aria-label="Section" value={item.section} disabled={!canEdit}
                                onChange={(e) => set(i, { section: e.target.value })}>
                            {DAY_FIELD_SECTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                        </select>
                    )}
                    {isDay && (
                        <input aria-label="Default value" placeholder="Default" value={item.default} disabled={!canEdit}
                               onChange={(e) => set(i, { default: e.target.value })} />
                    )}
                    <label className="cst-check">
                        <input type="checkbox" checked={item.sensitive} disabled={!canEdit}
                               onChange={(e) => set(i, { sensitive: e.target.checked })} />
                        Sensitive
                    </label>
                    {isDay && (
                        <label className="cst-check">
                            <input type="checkbox" checked={item.visible} disabled={!canEdit}
                                   onChange={(e) => set(i, { visible: e.target.checked })} />
                            Show
                        </label>
                    )}
                    {canEdit && (
                        <span className="cst-actions">
                            <button type="button" aria-label="Move up" onClick={() => onChange(moveItem(items, i, -1))}><ArrowUp size={14} /></button>
                            <button type="button" aria-label="Move down" onClick={() => onChange(moveItem(items, i, 1))}><ArrowDown size={14} /></button>
                            <button type="button" aria-label="Remove" disabled={item.builtin}
                                    onClick={() => onChange(removeAt(items, i))}><Trash2 size={14} /></button>
                        </span>
                    )}
                    {errorsFor(errors, `${errorPrefix}[${i}]`).map((m) => <div key={m} className="cst-error">{m}</div>)}
                </div>
            ))}
            {canEdit && (
                <button type="button" className="cst-add"
                        onClick={() => onChange([...items, isDay ? blankDayField(items) : blankColumn(items)])}>
                    <Plus size={14} /> Add {isDay ? 'field' : 'column'}
                </button>
            )}
        </section>
    );
}
