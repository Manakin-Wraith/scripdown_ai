import { useCallback, useEffect, useRef, useState } from 'react';
import { Outlet, useLocation, useParams } from 'react-router-dom';
import { Contact as ContactIcon } from 'lucide-react';
import { listContacts } from '../services/apiService';
import { Spinner } from '../components/ui';
import DirectoryShell from '../components/directory/DirectoryShell';
import useGuardedNav from '../components/directory/useGuardedNav';
import { initials } from '../components/directory/initials';
import './ProductionPages.css';

const roleTagsText = (t) => (Array.isArray(t) ? t.join(', ') : t || '');

export default function ContactsListPage() {
    const location = useLocation();
    const { contactId } = useParams();
    const { setPaneDirty, guardedNav } = useGuardedNav();

    const [contacts, setContacts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [q, setQ] = useState('');
    const [kindFilter, setKindFilter] = useState('');
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

    const isIndex = location.pathname === '/contacts';

    const list = loading ? (
        <div className="production-page-loading"><Spinner size={24} /></div>
    ) : contacts.length === 0 ? (
        <p className="production-scripts-empty">No contacts yet — add your address book of crew and vendors.</p>
    ) : (
        <ul className="directory-row-list">
            {contacts.map((c) => {
                const meta = [roleTagsText(c.role_tags), c.phone].filter(Boolean).join(' · ');
                return (
                    <li key={c.id}>
                        <button
                            type="button"
                            className={`directory-row${c.id === contactId ? ' is-active' : ''}`}
                            onClick={() => guardedNav(`/contacts/${c.id}`)}
                        >
                            <span className="directory-row-avatar" aria-hidden>{initials(c.name)}</span>
                            <span className="directory-row-body">
                                <span className="directory-row-title">{c.name}</span>
                                <span className="directory-row-sub">
                                    {c.company_name || (c.kind === 'company' ? 'Company' : 'Person')}
                                </span>
                                {meta && <span className="directory-row-meta">{meta}</span>}
                            </span>
                        </button>
                    </li>
                );
            })}
        </ul>
    );

    const toolbar = (
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
    );

    return (
        <DirectoryShell
            title="Contacts"
            subtitle="Your address book of crew and vendors, reusable across every production"
            newLabel="New contact"
            onNew={() => guardedNav('/contacts/new')}
            toolbar={toolbar}
            list={list}
            error={error && contacts.length > 0 ? error : null}
            hasSelection={!isIndex}
        >
            {isIndex ? (
                <div className="directory-pane-empty">
                    <ContactIcon size={28} />
                    <p>Select a contact, or add a new one.</p>
                </div>
            ) : null}
            <Outlet context={{ reloadList: load, setPaneDirty }} />
        </DirectoryShell>
    );
}
