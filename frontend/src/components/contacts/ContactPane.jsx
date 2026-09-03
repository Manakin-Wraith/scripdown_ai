import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { getContact, createContact, updateContact, deleteContact } from '../../services/apiService';
import { Spinner } from '../ui';
import ContactForm from './ContactForm';
import { DetailRow, DetailSection } from '../directory/DetailRow';

const initials = (name) => (name || '?').trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join('').toUpperCase();

const errMsg = (err, fallback) => err.response?.data?.error || err.message || fallback;

/**
 * Right-hand detail pane for the Contacts directory. `mode` comes from the
 * route: 'new' | 'view' | 'edit'.
 */
export default function ContactPane({ mode }) {
    const { contactId } = useParams();
    const navigate = useNavigate();
    const { reloadList, setPaneDirty } = useOutletContext();

    const [contact, setContact] = useState(null);
    const [assignments, setAssignments] = useState([]);
    const [loading, setLoading] = useState(mode !== 'new');
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [deleteError, setDeleteError] = useState(null);

    useEffect(() => {
        if (mode === 'new') {
            setContact(null);
            setLoading(false);
            return;
        }
        let active = true;
        setLoading(true);
        getContact(contactId)
            .then((d) => {
                if (!active) return;
                setContact(d.contact);
                setAssignments(d.assignments || []);
                setError(null);
            })
            .catch((err) => active && setError(errMsg(err, 'Failed to load contact')))
            .finally(() => active && setLoading(false));
        return () => { active = false; };
    }, [contactId, mode]);

    const handleCreate = useCallback(async (payload) => {
        setSaving(true);
        setError(null);
        try {
            const d = await createContact(payload);
            setPaneDirty(false);
            reloadList();
            navigate(`/contacts/${d.contact.id}`);
        } catch (err) {
            setError(errMsg(err, 'Failed to create contact'));
            setSaving(false);
        }
    }, [navigate, reloadList, setPaneDirty]);

    const handleSave = useCallback(async (payload) => {
        setSaving(true);
        setError(null);
        try {
            await updateContact(contactId, payload);
            setPaneDirty(false);
            reloadList();
            navigate(`/contacts/${contactId}`);
        } catch (err) {
            setError(errMsg(err, 'Failed to save contact'));
            setSaving(false);
        }
    }, [contactId, navigate, reloadList, setPaneDirty]);

    const handleDelete = useCallback(async () => {
        setDeleting(true);
        setDeleteError(null);
        try {
            await deleteContact(contactId);
            setPaneDirty(false);
            reloadList();
            navigate('/contacts');
        } catch (err) {
            if (err.response?.status === 409) {
                const usedIn = err.response.data?.used_in || [];
                setDeleteError(`Assigned to ${usedIn.map((u) => u.production_title).join(', ')} — remove those crew assignments first.`);
            } else {
                setDeleteError(errMsg(err, 'Failed to delete contact'));
            }
            setDeleting(false);
        }
    }, [contactId, navigate, reloadList, setPaneDirty]);

    const backLink = (
        <button type="button" className="directory-pane-back" onClick={() => navigate('/contacts')}>
            <ArrowLeft size={15} /> All contacts
        </button>
    );

    if (loading) {
        return <div className="directory-pane-empty"><Spinner size={24} /></div>;
    }
    if (error && !contact && mode !== 'new') {
        return (
            <div className="directory-pane">
                {backLink}
                <p className="production-page-error">{error}</p>
            </div>
        );
    }

    if (mode === 'new' || mode === 'edit') {
        return (
            <div className="directory-pane">
                {backLink}
                <h3 className="directory-pane-title">{mode === 'new' ? 'New contact' : `Edit ${contact?.name || 'contact'}`}</h3>
                {error && <p className="production-page-error">{error}</p>}
                <ContactForm
                    initial={mode === 'edit' ? contact : undefined}
                    saving={saving}
                    onDirtyChange={setPaneDirty}
                    onSubmit={mode === 'new' ? handleCreate : handleSave}
                    onCancel={() => navigate(mode === 'edit' ? `/contacts/${contactId}` : '/contacts')}
                />
            </div>
        );
    }

    // view
    const roleTags = Array.isArray(contact.role_tags) ? contact.role_tags.join(', ') : contact.role_tags;
    return (
        <div className="directory-pane">
            {backLink}
            <header className="directory-pane-head">
                <div className="directory-pane-identity">
                    <span className="directory-avatar" aria-hidden>{initials(contact.name)}</span>
                    <div>
                        <h3 className="directory-pane-title">{contact.name}</h3>
                        <span className="directory-pane-subtitle">
                            {contact.company_name || (contact.kind === 'company' ? 'Company' : 'Person')}
                        </span>
                    </div>
                </div>
                <Link className="production-new-btn" to={`/contacts/${contactId}/edit`}>Edit</Link>
            </header>
            {error && <p className="production-page-error">{error}</p>}

            <div className="directory-detail">
                <DetailRow label="Kind" value={contact.kind} capitalize />
                <DetailRow label="Company" value={contact.company_name} />
                <DetailRow label="Role tags" value={roleTags || null} />
                <DetailRow label="Phone" value={contact.phone} />
                <DetailRow label="Email" value={contact.email} />
                <DetailRow label="Agent" value={contact.agent_contact} />
                <DetailRow
                    label="Rate"
                    value={contact.standard_rate != null
                        ? `${contact.standard_rate}${contact.rate_unit ? ` / ${contact.rate_unit}` : ''}`
                        : null}
                />
                <DetailRow label="Notes" value={contact.notes} />
            </div>

            <DetailSection title="Used on">
                {assignments.length === 0 ? (
                    <p className="directory-detail-muted">Not assigned to any production yet.</p>
                ) : (
                    <div className="directory-chips">
                        {assignments.map((a) => (
                            <Link
                                key={a.crew_id || `${a.production_id}-${a.role}`}
                                className="directory-chip"
                                to={`/productions/${a.production_id}`}
                            >
                                {a.production_title || 'Untitled production'}
                                {a.role && <span className="directory-chip-meta">{a.role}</span>}
                            </Link>
                        ))}
                    </div>
                )}
            </DetailSection>

            <div className="directory-pane-danger">
                <button type="button" className="directory-danger-btn" onClick={handleDelete} disabled={deleting}>
                    {deleting ? 'Deleting…' : 'Delete contact'}
                </button>
                {deleteError && <p className="production-page-error">{deleteError}</p>}
            </div>
        </div>
    );
}
