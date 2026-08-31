import { useState, useEffect, useRef } from 'react';
import {
    listContacts,
    createContact,
    addProductionCrew,
    updateProductionCrew,
} from '../../services/apiService';

const RATE_UNITS = [
    { value: '', label: '—' },
    { value: 'hour', label: 'hour' },
    { value: 'day', label: 'day' },
    { value: 'week', label: 'week' },
    { value: 'flat', label: 'flat' },
];

const clean = (v) => {
    const t = typeof v === 'string' ? v.trim() : v;
    return t === '' || t === null || t === undefined ? undefined : t;
};

/**
 * Add or edit a crew assignment on a production.
 * Props: { productionId, initial, departments, onSaved, onClose }
 */
export default function CrewAssignmentModal({ productionId, initial, departments = [], onSaved, onClose }) {
    const isEdit = Boolean(initial);

    // Contact selection (create mode only)
    const [contactId, setContactId] = useState(initial?.contact_id || null);
    const [contactLabel, setContactLabel] = useState(
        initial?.contact ? (initial.contact.name || initial.contact.company_name || 'Contact') : ''
    );
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [searching, setSearching] = useState(false);
    const [showCreate, setShowCreate] = useState(false);
    const [newContact, setNewContact] = useState({ name: '', phone: '', email: '', company_name: '' });
    const searchTimer = useRef(null);

    // Assignment fields
    const [form, setForm] = useState({
        role: initial?.role || '',
        department_code: initial?.department_code || '',
        job_rate: initial?.job_rate ?? '',
        job_rate_unit: initial?.job_rate_unit || '',
        start_date: initial?.start_date || '',
        end_date: initial?.end_date || '',
        notes: initial?.notes || '',
    });

    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);

    const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
    const setNew = (key) => (e) => setNewContact((c) => ({ ...c, [key]: e.target.value }));

    useEffect(() => {
        if (isEdit) return undefined;
        if (searchTimer.current) clearTimeout(searchTimer.current);
        const q = query.trim();
        if (!q) { setResults([]); return undefined; }
        searchTimer.current = setTimeout(() => {
            setSearching(true);
            listContacts({ q })
                .then((data) => setResults(data.contacts || []))
                .catch(() => setResults([]))
                .finally(() => setSearching(false));
        }, 300);
        return () => searchTimer.current && clearTimeout(searchTimer.current);
    }, [query, isEdit]);

    const pickContact = (c) => {
        setContactId(c.id);
        setContactLabel(c.company_name ? `${c.name} (${c.company_name})` : c.name);
        setShowCreate(false);
        setResults([]);
        setQuery('');
    };

    const buildAssignmentFields = () => ({
        role: clean(form.role),
        department_code: form.department_code === '' ? null : form.department_code,
        job_rate: form.job_rate === '' ? undefined : Number(form.job_rate),
        job_rate_unit: clean(form.job_rate_unit),
        start_date: clean(form.start_date),
        end_date: clean(form.end_date),
        notes: clean(form.notes),
    });

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (saving) return;
        setError(null);
        setSaving(true);
        try {
            if (isEdit) {
                await updateProductionCrew(productionId, initial.id, buildAssignmentFields());
            } else {
                let cid = contactId;
                if (showCreate) {
                    const name = newContact.name.trim();
                    if (!name) { setError('New contact needs a name.'); setSaving(false); return; }
                    const created = await createContact({
                        name,
                        kind: 'person',
                        phone: clean(newContact.phone),
                        email: clean(newContact.email),
                        company_name: clean(newContact.company_name),
                    });
                    cid = created.contact?.id || created.id;
                }
                if (!cid) { setError('Pick a contact or create a new one.'); setSaving(false); return; }
                await addProductionCrew(productionId, { contact_id: cid, ...buildAssignmentFields() });
            }
            onSaved();
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Could not save that assignment');
            setSaving(false);
        }
    };

    return (
        <div className="production-modal-backdrop" onClick={onClose}>
            <div className="production-modal" onClick={(e) => e.stopPropagation()}>
                <h3>{isEdit ? 'Edit crew assignment' : 'Add crew'}</h3>
                {error && <p className="production-page-error">{error}</p>}
                <form className="contact-form" onSubmit={handleSubmit}>
                    {isEdit ? (
                        <label className="contact-field">
                            <span>Contact</span>
                            <input type="text" value={contactLabel} disabled readOnly />
                        </label>
                    ) : contactId && !showCreate ? (
                        <label className="contact-field">
                            <span>Contact</span>
                            <div className="crew-contact-picked">
                                <span>{contactLabel}</span>
                                <button type="button" onClick={() => { setContactId(null); setContactLabel(''); }}>
                                    Change
                                </button>
                            </div>
                        </label>
                    ) : (
                        <div className="contact-field">
                            <span className="contact-field-label">Contact *</span>
                            {!showCreate && (
                                <>
                                    <input
                                        type="text"
                                        placeholder="Search contacts…"
                                        value={query}
                                        onChange={(e) => setQuery(e.target.value)}
                                    />
                                    {searching && <p className="crew-search-hint">Searching…</p>}
                                    {results.length > 0 && (
                                        <ul className="production-picker-list">
                                            {results.map((c) => (
                                                <li key={c.id}>
                                                    <button type="button" onClick={() => pickContact(c)}>
                                                        {c.name}
                                                        {c.company_name ? ` · ${c.company_name}` : ''}
                                                    </button>
                                                </li>
                                            ))}
                                        </ul>
                                    )}
                                    <button
                                        type="button"
                                        className="crew-create-toggle"
                                        onClick={() => setShowCreate(true)}
                                    >
                                        ＋ Create new contact
                                    </button>
                                </>
                            )}
                            {showCreate && (
                                <div className="crew-new-contact">
                                    <label className="contact-field">
                                        <span>Name *</span>
                                        <input type="text" autoFocus value={newContact.name} onChange={setNew('name')} />
                                    </label>
                                    <label className="contact-field">
                                        <span>Phone</span>
                                        <input type="text" value={newContact.phone} onChange={setNew('phone')} />
                                    </label>
                                    <label className="contact-field">
                                        <span>Email</span>
                                        <input type="text" value={newContact.email} onChange={setNew('email')} />
                                    </label>
                                    <label className="contact-field">
                                        <span>Company</span>
                                        <input type="text" value={newContact.company_name} onChange={setNew('company_name')} />
                                    </label>
                                    <button
                                        type="button"
                                        className="crew-create-toggle"
                                        onClick={() => { setShowCreate(false); setNewContact({ name: '', phone: '', email: '', company_name: '' }); }}
                                    >
                                        ← Pick an existing contact instead
                                    </button>
                                </div>
                            )}
                        </div>
                    )}

                    <label className="contact-field">
                        <span>Role</span>
                        <input type="text" placeholder="Gaffer" value={form.role} onChange={set('role')} />
                    </label>

                    <label className="contact-field">
                        <span>Department</span>
                        <select value={form.department_code} onChange={set('department_code')}>
                            <option value="">— Vendor / none —</option>
                            {departments.map((d) => (
                                <option key={d.code} value={d.code}>{d.name}</option>
                            ))}
                        </select>
                    </label>

                    <div className="contact-field-row">
                        <label className="contact-field">
                            <span>Rate</span>
                            <input type="number" min="0" value={form.job_rate} onChange={set('job_rate')} />
                        </label>
                        <label className="contact-field">
                            <span>Rate unit</span>
                            <select value={form.job_rate_unit} onChange={set('job_rate_unit')}>
                                {RATE_UNITS.map((u) => (
                                    <option key={u.value} value={u.value}>{u.label}</option>
                                ))}
                            </select>
                        </label>
                    </div>

                    <div className="contact-field-row">
                        <label className="contact-field">
                            <span>Start date</span>
                            <input type="date" value={form.start_date} onChange={set('start_date')} />
                        </label>
                        <label className="contact-field">
                            <span>End date</span>
                            <input type="date" value={form.end_date} onChange={set('end_date')} />
                        </label>
                    </div>

                    <label className="contact-field">
                        <span>Notes</span>
                        <textarea rows={3} value={form.notes} onChange={set('notes')} />
                    </label>

                    <div className="contact-form-actions">
                        <button type="button" className="production-modal-close" onClick={onClose}>
                            Cancel
                        </button>
                        <button type="submit" className="production-new-btn" disabled={saving}>
                            {saving ? 'Saving…' : isEdit ? 'Save changes' : 'Add crew'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
