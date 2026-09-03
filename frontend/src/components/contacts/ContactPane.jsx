import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { getContact, createContact, updateContact, deleteContact } from '../../services/apiService';
import { Spinner } from '../ui';
import ContactForm from './ContactForm';

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
            <div>
                {backLink}
                <p className="production-page-error">{error}</p>
            </div>
        );
    }

    if (mode === 'new' || mode === 'edit') {
        return (
            <div>
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
    return (
        <div>
            {backLink}
            <div className="directory-pane-head">
                <h3 className="directory-pane-title">{contact.name}</h3>
                <Link className="production-new-btn" to={`/contacts/${contactId}/edit`}>Edit</Link>
            </div>
            {error && <p className="production-page-error">{error}</p>}

            <dl className="location-detail-fields">
                <dt>Kind</dt><dd style={{ textTransform: 'capitalize' }}>{contact.kind}</dd>
                {contact.company_name && (<><dt>Company</dt><dd>{contact.company_name}</dd></>)}
                {(Array.isArray(contact.role_tags) ? contact.role_tags.length : contact.role_tags) ? (
                    <><dt>Role tags</dt><dd>{Array.isArray(contact.role_tags) ? contact.role_tags.join(', ') : contact.role_tags}</dd></>
                ) : null}
                {contact.phone && (<><dt>Phone</dt><dd>{contact.phone}</dd></>)}
                {contact.email && (<><dt>Email</dt><dd>{contact.email}</dd></>)}
                {contact.agent_contact && (<><dt>Agent</dt><dd>{contact.agent_contact}</dd></>)}
                {contact.standard_rate != null && (
                    <><dt>Rate</dt><dd>{contact.standard_rate}{contact.rate_unit ? ` / ${contact.rate_unit}` : ''}</dd></>
                )}
                {contact.notes && (<><dt>Notes</dt><dd>{contact.notes}</dd></>)}
            </dl>

            <div className="contact-used-on">
                <span className="contact-field-label">Used on</span>
                {assignments.length === 0 ? (
                    <p className="production-scripts-empty">Not assigned to any production yet.</p>
                ) : (
                    <ul className="contact-used-on-list">
                        {assignments.map((a) => (
                            <li key={a.crew_id || `${a.production_id}-${a.role}`}>
                                <Link to={`/productions/${a.production_id}`}>{a.production_title || 'Untitled production'}</Link>
                                {a.role && <span className="contact-used-on-role">{a.role}</span>}
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            <div className="contact-delete-row">
                <button type="button" className="contact-delete-btn" onClick={handleDelete} disabled={deleting}>
                    {deleting ? 'Deleting…' : 'Delete contact'}
                </button>
                {deleteError && <p className="production-page-error">{deleteError}</p>}
            </div>
        </div>
    );
}
