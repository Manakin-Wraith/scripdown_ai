import React, { useState } from 'react';
import { X, Save, Trash2, Eye, EyeOff, RefreshCw, ToggleLeft, ToggleRight } from 'lucide-react';
import { updateTemplate, deleteTemplate } from '../../services/apiService';
import './TemplateEditorModal.css';

const CATEGORIES = ['transactional', 'marketing', 'notification', 'personal'];

const TemplateEditorModal = ({ template, onClose, onSave, onDelete }) => {
    const [form, setForm] = useState({
        name:      template.name      || '',
        subject:   template.subject   || '',
        body_html: template.body_html || '',
        body_text: template.body_text || '',
        category:  template.category  || 'marketing',
        is_active: template.is_active !== false,
    });
    const [tab, setTab]         = useState('html');
    const [preview, setPreview] = useState(false);
    const [saving, setSaving]   = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [error, setError]     = useState(null);

    const set = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }));

    const handleSave = async () => {
        if (!form.name.trim() || !form.subject.trim()) {
            setError('Name and Subject are required.');
            return;
        }
        try {
            setSaving(true); setError(null);
            const result = await updateTemplate(template.id, form);
            if (result.success) {
                onSave && onSave(result.template);
            } else {
                setError(result.error || 'Failed to save template.');
            }
        } catch (err) {
            setError('Failed to save template.');
        } finally { setSaving(false); }
    };

    const handleDelete = async () => {
        if (!window.confirm(`Delete template "${template.name}"? This cannot be undone.`)) return;
        try {
            setDeleting(true); setError(null);
            const result = await deleteTemplate(template.id);
            if (result.success) {
                onDelete && onDelete();
            } else {
                setError(result.error || 'Failed to delete template.');
            }
        } catch (err) {
            setError('Failed to delete template.');
        } finally { setDeleting(false); }
    };

    return (
        <div className="tem-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="tem-modal">

                {/* Header */}
                <div className="tem-header">
                    <div className="tem-header-left">
                        <h2 className="tem-title">Edit Template</h2>
                        <button
                            className={`tem-toggle-active ${form.is_active ? 'active' : ''}`}
                            onClick={() => setForm(f => ({ ...f, is_active: !f.is_active }))}
                            title={form.is_active ? 'Active — click to deactivate' : 'Inactive — click to activate'}
                        >
                            {form.is_active
                                ? <><ToggleRight size={16} /> Active</>
                                : <><ToggleLeft size={16} /> Inactive</>
                            }
                        </button>
                    </div>
                    <div className="tem-header-right">
                        <button
                            className="tem-btn-preview"
                            onClick={() => setPreview(v => !v)}
                            title={preview ? 'Hide preview' : 'Show HTML preview'}
                        >
                            {preview ? <EyeOff size={15} /> : <Eye size={15} />}
                            {preview ? 'Editor' : 'Preview'}
                        </button>
                        <button className="tem-btn-save" onClick={handleSave} disabled={saving || deleting}>
                            {saving
                                ? <RefreshCw size={14} className="spin" />
                                : <Save size={14} />
                            }
                            Save
                        </button>
                        <button className="tem-btn-delete" onClick={handleDelete} disabled={saving || deleting} title="Delete template">
                            {deleting ? <RefreshCw size={14} className="spin" /> : <Trash2 size={14} />}
                        </button>
                        <button className="tem-btn-close" onClick={onClose}>
                            <X size={18} />
                        </button>
                    </div>
                </div>

                {error && <div className="tem-error">{error}</div>}

                <div className="tem-body">

                    {/* Left: form fields */}
                    <div className="tem-fields">
                        <div className="tem-field-row">
                            <div className="tem-field">
                                <label className="tem-label">Template Name *</label>
                                <input className="tem-input" value={form.name} onChange={set('name')} placeholder="e.g. Welcome Email" />
                            </div>
                            <div className="tem-field tem-field-sm">
                                <label className="tem-label">Category</label>
                                <select className="tem-select" value={form.category} onChange={set('category')}>
                                    {CATEGORIES.map(c => (
                                        <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        <div className="tem-field">
                            <label className="tem-label">Subject Line *</label>
                            <input className="tem-input" value={form.subject} onChange={set('subject')} placeholder="Email subject…" />
                        </div>

                        {/* Body tabs */}
                        <div className="tem-field tem-field-grow">
                            <div className="tem-tabs">
                                <button
                                    className={`tem-tab ${tab === 'html' ? 'active' : ''}`}
                                    onClick={() => setTab('html')}
                                >HTML Body</button>
                                <button
                                    className={`tem-tab ${tab === 'text' ? 'active' : ''}`}
                                    onClick={() => setTab('text')}
                                >Plain Text</button>
                            </div>

                            {preview && tab === 'html' ? (
                                <div
                                    className="tem-preview-frame"
                                    dangerouslySetInnerHTML={{ __html: form.body_html }}
                                />
                            ) : (
                                <textarea
                                    className="tem-textarea"
                                    value={tab === 'html' ? form.body_html : form.body_text}
                                    onChange={tab === 'html' ? set('body_html') : set('body_text')}
                                    placeholder={tab === 'html' ? '<p>Your HTML email body…</p>' : 'Plain text fallback…'}
                                    spellCheck={false}
                                />
                            )}
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
};

export default TemplateEditorModal;
