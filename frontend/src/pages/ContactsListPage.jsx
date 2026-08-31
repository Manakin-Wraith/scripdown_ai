import { useState, useEffect, useCallback, useRef } from 'react';
import { Contact as ContactIcon, Plus } from 'lucide-react';
import { listContacts, createContact } from '../services/apiService';
import PageHeader from '../components/layout/PageHeader';
import { Spinner } from '../components/ui';
import ContactFormModal from '../components/contacts/ContactFormModal';
import ContactDetailDrawer from '../components/contacts/ContactDetailDrawer';
import './ProductionPages.css';

export default function ContactsListPage() {
    const [contacts, setContacts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [q, setQ] = useState('');
    const [kindFilter, setKindFilter] = useState('');
    const [creating, setCreating] = useState(false);
    const [saving, setSaving] = useState(false);
    const [openId, setOpenId] = useState(null);
    const firstLoad = useRef(true);

    const load = useCallback(async () => {
        try {
            const params = {};
            if (q.trim()) params.q = q.trim();
            if (kindFilter) params.kind = kindFilter;
            const data = await listContacts(params);
            setContacts(data.contacts || []);
            setError(null);
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Failed to load contacts');
        } finally {
            setLoading(false);
        }
    }, [q, kindFilter]);

    useEffect(() => {
        if (firstLoad.current) {
            firstLoad.current = false;
            load();
            return;
        }
        const t = setTimeout(load, 300);
        return () => clearTimeout(t);
    }, [load]);

    const handleCreate = async (payload) => {
        setSaving(true);
        try {
            await createContact(payload);
            setCreating(false);
            setSaving(false);
            load();
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Failed to create contact');
            setSaving(false);
        }
    };

    if (loading) {
        return <div className="production-page-loading"><Spinner size={32} /></div>;
    }
    if (error && !contacts.length) {
        return <p className="production-page-error">{error}</p>;
    }

    return (
        <div className="production-page">
            <PageHeader
                title="Contacts"
                subtitle="Your address book of crew and vendors, reusable across every production"
                actions={
                    <button className="production-new-btn" onClick={() => setCreating(true)}>
                        <Plus size={16} /> New contact
                    </button>
                }
            />

            <div className="contact-toolbar">
                <input
                    type="text"
                    className="contact-search"
                    placeholder="Search contacts…"
                    value={q}
                    onChange={(e) => setQ(e.target.value)}
                />
                <select value={kindFilter} onChange={(e) => setKindFilter(e.target.value)}>
                    <option value="">All</option>
                    <option value="person">Person</option>
                    <option value="company">Company</option>
                </select>
            </div>

            {error && contacts.length > 0 && <p className="production-page-error">{error}</p>}

            {contacts.length === 0 ? (
                <div className="production-empty-state">
                    <div className="production-empty-content">
                        <div className="production-empty-icon-wrapper">
                            <ContactIcon size={28} className="production-empty-icon" />
                        </div>
                        <h2>No contacts yet</h2>
                        <p>No contacts yet — add your address book of crew and vendors.</p>
                    </div>
                </div>
            ) : (
                <table className="contact-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Kind</th>
                            <th>Company</th>
                            <th>Role tags</th>
                            <th>Phone</th>
                            <th>Email</th>
                        </tr>
                    </thead>
                    <tbody>
                        {contacts.map((c) => (
                            <tr key={c.id} onClick={() => setOpenId(c.id)}>
                                <td>{c.name}</td>
                                <td>
                                    <span className={`contact-kind-badge kind-${c.kind}`}>{c.kind}</span>
                                </td>
                                <td>{c.company_name || '—'}</td>
                                <td>
                                    {Array.isArray(c.role_tags)
                                        ? c.role_tags.join(', ')
                                        : (c.role_tags || '—')}
                                </td>
                                <td>{c.phone || '—'}</td>
                                <td>{c.email || '—'}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}

            {creating && (
                <ContactFormModal
                    onSubmit={handleCreate}
                    onClose={() => setCreating(false)}
                    saving={saving}
                />
            )}

            {openId && (
                <ContactDetailDrawer
                    contactId={openId}
                    onClose={() => setOpenId(null)}
                    onChanged={load}
                    onDeleted={() => { setOpenId(null); load(); }}
                />
            )}
        </div>
    );
}
