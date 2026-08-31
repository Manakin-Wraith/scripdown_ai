import { useState } from 'react';

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
 * Controlled create/edit form for a contact, rendered as a modal.
 * Props: { initial, onSubmit, onClose, saving }
 */
export default function ContactFormModal({ initial, onSubmit, onClose, saving, title, children }) {
    const [form, setForm] = useState(() => blankFromInitial(initial));
    const isEdit = Boolean(initial);

    const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

    const handleSubmit = (e) => {
        e.preventDefault();
        const name = form.name.trim();
        if (!name || saving) return;

        const clean = (v) => {
            const t = typeof v === 'string' ? v.trim() : v;
            return t === '' || t === null || t === undefined ? undefined : t;
        };

        const roleTags = form.role_tags
            .split(',')
            .map((t) => t.trim())
            .filter(Boolean);

        const rate = form.standard_rate === '' ? undefined : Number(form.standard_rate);

        onSubmit({
            name,
            kind: form.kind,
            company_name: clean(form.company_name),
            role_tags: roleTags.length ? roleTags : undefined,
            phone: clean(form.phone),
            email: clean(form.email),
            agent_contact: clean(form.agent_contact),
            standard_rate: Number.isFinite(rate) ? rate : undefined,
            rate_unit: clean(form.rate_unit),
            notes: clean(form.notes),
        });
    };

    return (
        <div className="production-modal-backdrop" onClick={onClose}>
            <div className="production-modal" onClick={(e) => e.stopPropagation()}>
                <h3>{title || (isEdit ? 'Edit contact' : 'New contact')}</h3>
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
                        <input
                            type="text"
                            placeholder="Gaffer, Best Boy"
                            value={form.role_tags}
                            onChange={set('role_tags')}
                        />
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
                            <input
                                type="number"
                                min="0"
                                value={form.standard_rate}
                                onChange={set('standard_rate')}
                            />
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

                    {children}

                    <div className="contact-form-actions">
                        <button type="button" className="production-modal-close" onClick={onClose}>
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="production-new-btn"
                            disabled={saving || !form.name.trim()}
                        >
                            {saving ? 'Saving…' : isEdit ? 'Save changes' : 'Create contact'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
