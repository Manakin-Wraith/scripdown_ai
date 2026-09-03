import { useEffect, useState } from 'react';

const RATE_UNITS = [
    { value: '', label: '—' },
    { value: 'day', label: 'day' },
    { value: 'week', label: 'week' },
    { value: 'flat', label: 'flat' },
];

const blankFromInitial = (initial) => ({
    name: initial?.name || '',
    kind: initial?.kind || 'person',
    company_name: initial?.company_name || '',
    role_tags: Array.isArray(initial?.role_tags)
        ? initial.role_tags.join(', ')
        : (initial?.role_tags || ''),
    phone: initial?.phone || '',
    email: initial?.email || '',
    agent_contact: initial?.agent_contact || '',
    standard_rate: initial?.standard_rate ?? '',
    rate_unit: initial?.rate_unit || '',
    notes: initial?.notes || '',
});

/**
 * Controlled create/edit form for a contact, rendered inline in the detail
 * pane (no modal chrome).
 * Props: { initial, onSubmit, onCancel, saving, onDirtyChange }
 */
export default function ContactForm({ initial, onSubmit, onCancel, saving, onDirtyChange }) {
    const [form, setForm] = useState(() => blankFromInitial(initial));
    const [dirty, setDirty] = useState(false);
    const isEdit = Boolean(initial);

    useEffect(() => { onDirtyChange?.(dirty); }, [dirty, onDirtyChange]);
    useEffect(() => () => onDirtyChange?.(false), [onDirtyChange]);

    const set = (key) => (e) => {
        setDirty(true);
        setForm((f) => ({ ...f, [key]: e.target.value }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        const name = form.name.trim();
        if (!name || saving) return;

        // CREATE: omit empty optional fields. EDIT: send explicit null for a
        // cleared field so update_contact (patches only present keys) nulls it.
        const opt = (v) => {
            const t = typeof v === 'string' ? v.trim() : v;
            if (t === '' || t === null || t === undefined) return isEdit ? null : undefined;
            return t;
        };

        const roleTags = form.role_tags.split(',').map((t) => t.trim()).filter(Boolean);
        const rate = form.standard_rate === '' ? undefined : Number(form.standard_rate);

        setDirty(false);
        onSubmit({
            name,
            kind: form.kind,
            company_name: opt(form.company_name),
            role_tags: roleTags.length ? roleTags : (isEdit ? [] : undefined),
            phone: opt(form.phone),
            email: opt(form.email),
            agent_contact: opt(form.agent_contact),
            standard_rate: Number.isFinite(rate) ? rate : (isEdit ? null : undefined),
            rate_unit: opt(form.rate_unit),
            notes: opt(form.notes),
        });
    };

    return (
        <form className="contact-form" onSubmit={handleSubmit}>
            <label className="contact-field">
                <span>Name *</span>
                <input autoFocus type="text" value={form.name} onChange={set('name')} />
            </label>

            <label className="contact-field">
                <span>Kind</span>
                <select value={form.kind} onChange={set('kind')}>
                    <option value="person">Person</option>
                    <option value="company">Company</option>
                </select>
            </label>

            <label className="contact-field">
                <span>Company</span>
                <input type="text" value={form.company_name} onChange={set('company_name')} />
            </label>

            <label className="contact-field">
                <span>Role tags</span>
                <input type="text" placeholder="Gaffer, Best Boy"
                    value={form.role_tags} onChange={set('role_tags')} />
            </label>

            <label className="contact-field">
                <span>Phone</span>
                <input type="text" value={form.phone} onChange={set('phone')} />
            </label>

            <label className="contact-field">
                <span>Email</span>
                <input type="text" value={form.email} onChange={set('email')} />
            </label>

            <label className="contact-field">
                <span>Agent contact</span>
                <input type="text" value={form.agent_contact} onChange={set('agent_contact')} />
            </label>

            <div className="contact-field-row">
                <label className="contact-field">
                    <span>Standard rate</span>
                    <input type="number" min="0"
                        value={form.standard_rate} onChange={set('standard_rate')} />
                </label>
                <label className="contact-field">
                    <span>Rate unit</span>
                    <select value={form.rate_unit} onChange={set('rate_unit')}>
                        {RATE_UNITS.map((u) => (
                            <option key={u.value} value={u.value}>{u.label}</option>
                        ))}
                    </select>
                </label>
            </div>

            <label className="contact-field">
                <span>Notes</span>
                <textarea rows={3} value={form.notes} onChange={set('notes')} />
            </label>

            <div className="contact-form-actions">
                <button type="button" className="production-modal-close" onClick={onCancel}>
                    Cancel
                </button>
                <button type="submit" className="production-new-btn"
                    disabled={saving || !form.name.trim()}>
                    {saving ? 'Saving…' : isEdit ? 'Save changes' : 'Create contact'}
                </button>
            </div>
        </form>
    );
}
