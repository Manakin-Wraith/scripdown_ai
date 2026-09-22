import { ArrowUp, ArrowDown } from 'lucide-react';
import { moveItem, updateAt, errorsFor, panelErrors } from './templateUtils';

export default function SectionsPanel({ sections, onChange, canEdit, errors }) {
    return (
        <section className="cst-panel">
            <div className="cst-panel-head">
                <h4>Sections</h4>
                <span className="cst-hint">Show, hide, rename and reorder the parts of each call sheet.</span>
            </div>
            {panelErrors(errors, 'sections').map((m) => <div key={m} className="cst-error">{m}</div>)}
            {sections.map((s, i) => (
                <div key={s.key} className="cst-row">
                    <label className="cst-check">
                        <input type="checkbox" checked={s.visible} disabled={!canEdit}
                               onChange={(e) => onChange(updateAt(sections, i, { visible: e.target.checked }))} />
                        Show
                    </label>
                    <input aria-label="Section label" value={s.label} disabled={!canEdit}
                           onChange={(e) => onChange(updateAt(sections, i, { label: e.target.value }))} />
                    <span className="cst-key">{s.key}</span>
                    {canEdit && (
                        <span className="cst-actions">
                            <button type="button" aria-label="Move up" onClick={() => onChange(moveItem(sections, i, -1))}><ArrowUp size={14} /></button>
                            <button type="button" aria-label="Move down" onClick={() => onChange(moveItem(sections, i, 1))}><ArrowDown size={14} /></button>
                        </span>
                    )}
                    {errorsFor(errors, `sections[${i}]`).map((m) => <div key={m} className="cst-error">{m}</div>)}
                </div>
            ))}
        </section>
    );
}
