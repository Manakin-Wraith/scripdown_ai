import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getContact, updateContact, deleteContact } from '../../services/apiService';
import { Spinner } from '../ui';
import ContactFormModal from './ContactFormModal';

/**
 * Loads a single contact and reuses ContactFormModal for editing, plus a
 * "Used on" assignments list and a delete action.
 * Props: { contactId, onClose, onChanged, onDeleted }
 */
export default function ContactDetailDrawer({ contactId, onClose, onChanged, onDeleted }) {
    const [contact, setContact] = useState(null);
    const [assignments, setAssignments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);
    const [deleteError, setDeleteError] = useState(null);
    const [deleting, setDeleting] = useState(false);

    useEffect(() => {
        let active = true;
        setLoading(true);
        getContact(contactId)
            .then((data) => {
                if (!active) return;
                setContact(data.contact);
                setAssignments(data.assignments || []);
            })
            .catch((err) => active && setError(err.response?.data?.error || err.message || 'Failed to load contact'))
            .finally(() => active && setLoading(false));
        return () => { active = false; };
    }, [contactId]);

    const handleSave = async (payload) => {
        setSaving(true);
        setError(null);
        try {
            await updateContact(contactId, payload);
            onChanged?.();
            onClose?.();
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Failed to save contact');
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        setDeleting(true);
        setDeleteError(null);
        try {
            await deleteContact(contactId);
            onDeleted?.();
        } catch (err) {
            if (err.response?.status === 409) {
                const usedIn = err.response.data?.used_in || [];
                setDeleteError(
                    `Assigned to ${usedIn.map((u) => u.production_title).join(', ')} — remove those crew assignments first.`
                );
            } else {
                setDeleteError(err.response?.data?.error || err.message || 'Failed to delete contact');
            }
            setDeleting(false);
        }
    };

    if (loading) {
        return (
            <div className="production-modal-backdrop" onClick={onClose}>
                <div className="production-modal" onClick={(e) => e.stopPropagation()}>
                    <Spinner size={24} />
                </div>
            </div>
        );
    }

    if (error && !contact) {
        return (
            <div className="production-modal-backdrop" onClick={onClose}>
                <div className="production-modal" onClick={(e) => e.stopPropagation()}>
                    <p className="production-page-error">{error}</p>
                    <button className="production-modal-close" onClick={onClose}>Close</button>
                </div>
            </div>
        );
    }

    return (
        <ContactFormModal
            title="Edit contact"
            initial={contact}
            saving={saving}
            onSubmit={handleSave}
            onClose={onClose}
        >
            {error && <p className="production-page-error">{error}</p>}

            <div className="contact-used-on">
                <span className="contact-field-label">Used on</span>
                {assignments.length === 0 ? (
                    <p className="production-scripts-empty">Not assigned to any production yet.</p>
                ) : (
                    <ul className="contact-used-on-list">
                        {assignments.map((a) => (
                            <li key={a.crew_id || `${a.production_id}-${a.role}`}>
                                <Link to={`/productions/${a.production_id}`}>
                                    {a.production_title || 'Untitled production'}
                                </Link>
                                {a.role && <span className="contact-used-on-role">{a.role}</span>}
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            <div className="contact-delete-row">
                <button
                    type="button"
                    className="contact-delete-btn"
                    onClick={handleDelete}
                    disabled={deleting}
                >
                    {deleting ? 'Deleting…' : 'Delete contact'}
                </button>
                {deleteError && <p className="production-page-error">{deleteError}</p>}
            </div>
        </ContactFormModal>
    );
}
