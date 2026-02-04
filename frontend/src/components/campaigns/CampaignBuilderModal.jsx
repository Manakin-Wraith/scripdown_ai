import React, { useState, useEffect } from 'react';
import { 
    X, 
    Mail, 
    Users, 
    Calendar, 
    Send,
    Eye,
    AlertCircle,
    CheckCircle,
    Loader
} from 'lucide-react';
import { 
    getEmailTemplates,
    createCampaign,
    previewCampaignAudience
} from '../../services/apiService';
import './CampaignBuilderModal.css';

const CampaignBuilderModal = ({ isOpen, onClose, onSuccess }) => {
    const [step, setStep] = useState(1); // 1: Details, 2: Template, 3: Audience, 4: Review
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [templates, setTemplates] = useState([]);
    const [audiencePreview, setAudiencePreview] = useState(null);
    const [loadingPreview, setLoadingPreview] = useState(false);

    // Form state
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        template_id: '',
        targeting_mode: 'filters', // 'filters' or 'manual'
        manual_recipients: '', // Comma-separated email addresses
        template_variables: {}, // Custom values for template variables
        audience_filter: {
            subscription_status: [],
            min_scripts: null,
            max_scripts: null,
            signup_days_ago_min: null,
            signup_days_ago_max: null,
            inactive_days: null,
            trial_expiring_days: null
        },
        scheduled_at: null,
        send_immediately: true
    });

    useEffect(() => {
        if (isOpen) {
            loadTemplates();
        }
    }, [isOpen]);

    const loadTemplates = async () => {
        try {
            const data = await getEmailTemplates();
            setTemplates(data.templates || []);
        } catch (err) {
            console.error('Error loading templates:', err);
            setError('Failed to load templates');
        }
    };

    const handleInputChange = (field, value) => {
        setFormData(prev => ({
            ...prev,
            [field]: value
        }));
        setError(null);
    };

    const handleAudienceFilterChange = (field, value) => {
        setFormData(prev => ({
            ...prev,
            audience_filter: {
                ...prev.audience_filter,
                [field]: value
            }
        }));
        setError(null);
    };

    const handlePreviewAudience = async () => {
        try {
            setLoadingPreview(true);
            setError(null);
            const data = await previewCampaignAudience(formData.audience_filter);
            setAudiencePreview(data);
        } catch (err) {
            console.error('Error previewing audience:', err);
            setError('Failed to preview audience. Please try again.');
        } finally {
            setLoadingPreview(false);
        }
    };

    const handleSubmit = async () => {
        try {
            setLoading(true);
            setError(null);

            // Validate required fields
            if (!formData.name.trim()) {
                setError('Campaign name is required');
                return;
            }
            if (!formData.template_id) {
                setError('Please select a template');
                return;
            }

            // Clean up audience filter (remove null/empty values)
            const cleanedFilter = Object.entries(formData.audience_filter).reduce((acc, [key, value]) => {
                if (value !== null && value !== '' && !(Array.isArray(value) && value.length === 0)) {
                    acc[key] = value;
                }
                return acc;
            }, {});

            const payload = {
                name: formData.name,
                description: formData.description,
                template_id: formData.template_id,
                audience_filter: cleanedFilter,
                scheduled_at: formData.send_immediately ? null : formData.scheduled_at
            };

            const result = await createCampaign(payload);
            
            if (result.success) {
                onSuccess();
                handleClose();
            } else {
                setError(result.error || 'Failed to create campaign');
            }
        } catch (err) {
            console.error('Error creating campaign:', err);
            setError(err.response?.data?.error || 'Failed to create campaign');
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        setStep(1);
        setFormData({
            name: '',
            description: '',
            template_id: '',
            audience_filter: {
                subscription_status: [],
                min_scripts: null,
                max_scripts: null,
                signup_days_ago_min: null,
                signup_days_ago_max: null,
                inactive_days: null,
                trial_expiring_days: null
            },
            scheduled_at: null,
            send_immediately: true
        });
        setError(null);
        setAudiencePreview(null);
        onClose();
    };

    const canProceed = () => {
        switch (step) {
            case 1:
                return formData.name.trim().length > 0;
            case 2:
                return formData.template_id !== '';
            case 3:
                return true; // Audience is optional
            case 4:
                return true;
            default:
                return false;
        }
    };

    const selectedTemplate = templates.find(t => t.id === formData.template_id);

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={handleClose}>
            <div className="campaign-builder-modal" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="modal-header">
                    <div className="header-content">
                        <Mail size={24} />
                        <h2>Create Email Campaign</h2>
                    </div>
                    <button className="close-button" onClick={handleClose}>
                        <X size={20} />
                    </button>
                </div>

                {/* Progress Steps */}
                <div className="progress-steps">
                    {[
                        { num: 1, label: 'Details' },
                        { num: 2, label: 'Template' },
                        { num: 3, label: 'Audience' },
                        { num: 4, label: 'Review' }
                    ].map(({ num, label }) => (
                        <div 
                            key={num}
                            className={`step ${step === num ? 'active' : ''} ${step > num ? 'completed' : ''}`}
                        >
                            <div className="step-number">
                                {step > num ? <CheckCircle size={20} /> : num}
                            </div>
                            <span className="step-label">{label}</span>
                        </div>
                    ))}
                </div>

                {/* Error Banner */}
                {error && (
                    <div className="error-banner">
                        <AlertCircle size={20} />
                        {error}
                    </div>
                )}

                {/* Modal Body */}
                <div className="modal-body">
                    {/* Step 1: Campaign Details */}
                    {step === 1 && (
                        <div className="step-content">
                            <h3>Campaign Details</h3>
                            <div className="form-group">
                                <label>Campaign Name *</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={e => handleInputChange('name', e.target.value)}
                                    placeholder="e.g., Trial Expiring Reminder - January 2026"
                                    autoFocus
                                />
                            </div>
                            <div className="form-group">
                                <label>Description</label>
                                <textarea
                                    value={formData.description}
                                    onChange={e => handleInputChange('description', e.target.value)}
                                    placeholder="Optional: Add notes about this campaign"
                                    rows={3}
                                />
                            </div>
                        </div>
                    )}

                    {/* Step 2: Template Selection */}
                    {step === 2 && (
                        <div className="step-content">
                            <h3>Select Email Template</h3>
                            <div className="template-grid">
                                {templates.map(template => (
                                    <div
                                        key={template.id}
                                        className={`template-card ${formData.template_id === template.id ? 'selected' : ''}`}
                                        onClick={() => handleInputChange('template_id', template.id)}
                                    >
                                        <div className="template-header">
                                            <h4>{template.name}</h4>
                                            <span className={`category-badge ${template.category}`}>
                                                {template.category}
                                            </span>
                                        </div>
                                        <p className="template-subject">{template.subject}</p>
                                        {template.variables && template.variables.length > 0 && (
                                            <div className="template-variables">
                                                <small>Variables: {template.variables.join(', ')}</small>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>

                            {/* Template Variable Editor */}
                            {formData.template_id && templates.find(t => t.id === formData.template_id)?.variables?.length > 0 && (
                                <div className="template-variables-editor" style={{ marginTop: '2rem' }}>
                                    <h4>Customize Template Content</h4>
                                    <p className="step-description">Fill in the template variables for this campaign.</p>
                                    {templates.find(t => t.id === formData.template_id).variables.map(variable => (
                                        <div key={variable} className="form-group">
                                            <label>{variable.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}</label>
                                            {variable === 'message_body' || variable === 'body' ? (
                                                <textarea
                                                    value={formData.template_variables[variable] || ''}
                                                    onChange={e => setFormData(prev => ({
                                                        ...prev,
                                                        template_variables: {
                                                            ...prev.template_variables,
                                                            [variable]: e.target.value
                                                        }
                                                    }))}
                                                    placeholder={`Enter ${variable.replace(/_/g, ' ')}...`}
                                                    rows={variable === 'message_body' ? 8 : 4}
                                                />
                                            ) : (
                                                <input
                                                    type="text"
                                                    value={formData.template_variables[variable] || ''}
                                                    onChange={e => setFormData(prev => ({
                                                        ...prev,
                                                        template_variables: {
                                                            ...prev.template_variables,
                                                            [variable]: e.target.value
                                                        }
                                                    }))}
                                                    placeholder={`Enter ${variable.replace(/_/g, ' ')}...`}
                                                />
                                            )}
                                            <small style={{ color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>
                                                Variable: {`{{${variable}}}`}
                                            </small>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Step 3: Audience Selection */}
                    {step === 3 && (
                        <div className="step-content">
                            <h3>Target Audience</h3>
                            <p className="step-description">
                                Choose how to target recipients for this campaign.
                            </p>

                            <div className="form-group">
                                <label>Targeting Mode</label>
                                <div className="radio-group">
                                    <label className="radio-label">
                                        <input
                                            type="radio"
                                            name="targeting_mode"
                                            value="filters"
                                            checked={formData.targeting_mode === 'filters'}
                                            onChange={e => handleInputChange('targeting_mode', e.target.value)}
                                        />
                                        <span>Use Filters (segment users)</span>
                                    </label>
                                    <label className="radio-label">
                                        <input
                                            type="radio"
                                            name="targeting_mode"
                                            value="manual"
                                            checked={formData.targeting_mode === 'manual'}
                                            onChange={e => handleInputChange('targeting_mode', e.target.value)}
                                        />
                                        <span>Manual Recipients (specific emails)</span>
                                    </label>
                                </div>
                            </div>

                            {formData.targeting_mode === 'manual' ? (
                                <div className="form-group">
                                    <label>Recipient Email Addresses</label>
                                    <textarea
                                        value={formData.manual_recipients}
                                        onChange={e => handleInputChange('manual_recipients', e.target.value)}
                                        placeholder="Enter email addresses, one per line or comma-separated&#10;&#10;Example:&#10;user1@example.com&#10;user2@example.com, user3@example.com"
                                        rows="6"
                                        style={{ fontFamily: 'monospace', fontSize: '14px' }}
                                    />
                                    <small>
                                        {formData.manual_recipients.trim() 
                                            ? `${formData.manual_recipients.split(/[\n,]+/).filter(e => e.trim()).length} recipient(s)`
                                            : 'Enter email addresses separated by commas or new lines'}
                                    </small>
                                </div>
                            ) : (
                                <>
                                    <p className="step-description" style={{ marginTop: '10px' }}>
                                        Define filters to target specific user segments. Leave empty to send to all users.
                                    </p>

                                    <div className="form-group">
                                <label>Subscription Status</label>
                                <div className="checkbox-group">
                                    {['trial', 'active', 'expired', 'cancelled'].map(status => (
                                        <label key={status} className="checkbox-label">
                                            <input
                                                type="checkbox"
                                                checked={formData.audience_filter.subscription_status.includes(status)}
                                                onChange={e => {
                                                    const current = formData.audience_filter.subscription_status;
                                                    const updated = e.target.checked
                                                        ? [...current, status]
                                                        : current.filter(s => s !== status);
                                                    handleAudienceFilterChange('subscription_status', updated);
                                                }}
                                            />
                                            {status.charAt(0).toUpperCase() + status.slice(1)}
                                        </label>
                                    ))}
                                </div>
                            </div>

                            <div className="form-row">
                                <div className="form-group">
                                    <label>Min Scripts</label>
                                    <input
                                        type="number"
                                        min="0"
                                        value={formData.audience_filter.min_scripts || ''}
                                        onChange={e => handleAudienceFilterChange('min_scripts', e.target.value ? parseInt(e.target.value) : null)}
                                        placeholder="0"
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Max Scripts</label>
                                    <input
                                        type="number"
                                        min="0"
                                        value={formData.audience_filter.max_scripts || ''}
                                        onChange={e => handleAudienceFilterChange('max_scripts', e.target.value ? parseInt(e.target.value) : null)}
                                        placeholder="Unlimited"
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label>Inactive for (days)</label>
                                <input
                                    type="number"
                                    min="1"
                                    value={formData.audience_filter.inactive_days || ''}
                                    onChange={e => handleAudienceFilterChange('inactive_days', e.target.value ? parseInt(e.target.value) : null)}
                                    placeholder="e.g., 30"
                                />
                                <small>Target users who haven't logged in for X days</small>
                            </div>

                            <div className="form-group">
                                <label>Trial Expiring Within (days)</label>
                                <input
                                    type="number"
                                    min="1"
                                    value={formData.audience_filter.trial_expiring_days || ''}
                                    onChange={e => handleAudienceFilterChange('trial_expiring_days', e.target.value ? parseInt(e.target.value) : null)}
                                    placeholder="e.g., 7"
                                />
                                <small>Target users whose trial expires in X days</small>
                            </div>

                            <button
                                className="btn-secondary preview-btn"
                                onClick={handlePreviewAudience}
                                disabled={loadingPreview}
                            >
                                {loadingPreview ? (
                                    <>
                                        <Loader size={16} className="spin" />
                                        Loading...
                                    </>
                                ) : (
                                    <>
                                        <Eye size={16} />
                                        Preview Audience
                                    </>
                                )}
                            </button>

                            {audiencePreview && (
                                <div className="audience-preview">
                                    <div className="preview-stat">
                                        <Users size={20} />
                                        <div>
                                            <div className="stat-value">{audiencePreview.total_recipients}</div>
                                            <div className="stat-label">Recipients</div>
                                        </div>
                                    </div>
                                    {audiencePreview.sample_users && audiencePreview.sample_users.length > 0 && (
                                        <div className="sample-users">
                                            <small>Sample users:</small>
                                            <ul>
                                                {audiencePreview.sample_users.slice(0, 5).map((user, idx) => (
                                                    <li key={idx}>{user.email}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            )}
                                </>
                            )}
                        </div>
                    )}

                    {/* Step 4: Review */}
                    {step === 4 && (
                        <div className="step-content">
                            <h3>Review Campaign</h3>
                            
                            <div className="review-section">
                                <h4>Campaign Details</h4>
                                <div className="review-item">
                                    <span className="label">Name:</span>
                                    <span className="value">{formData.name}</span>
                                </div>
                                {formData.description && (
                                    <div className="review-item">
                                        <span className="label">Description:</span>
                                        <span className="value">{formData.description}</span>
                                    </div>
                                )}
                            </div>

                            <div className="review-section">
                                <h4>Template</h4>
                                <div className="review-item">
                                    <span className="label">Template:</span>
                                    <span className="value">{selectedTemplate?.name}</span>
                                </div>
                                <div className="review-item">
                                    <span className="label">Subject:</span>
                                    <span className="value">{selectedTemplate?.subject}</span>
                                </div>
                            </div>

                            <div className="review-section">
                                <h4>Audience</h4>
                                {audiencePreview ? (
                                    <div className="review-item">
                                        <span className="label">Recipients:</span>
                                        <span className="value">{audiencePreview.total_recipients} users</span>
                                    </div>
                                ) : (
                                    <div className="review-item">
                                        <span className="value">All users (no filters applied)</span>
                                    </div>
                                )}
                            </div>

                            <div className="review-section">
                                <h4>Scheduling</h4>
                                <div className="form-group">
                                    <label className="checkbox-label">
                                        <input
                                            type="checkbox"
                                            checked={formData.send_immediately}
                                            onChange={e => handleInputChange('send_immediately', e.target.checked)}
                                        />
                                        Save as draft (don't send immediately)
                                    </label>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="modal-footer">
                    <button
                        className="btn-secondary"
                        onClick={() => step > 1 ? setStep(step - 1) : handleClose()}
                        disabled={loading}
                    >
                        {step === 1 ? 'Cancel' : 'Back'}
                    </button>
                    
                    {step < 4 ? (
                        <button
                            className="btn-primary"
                            onClick={() => setStep(step + 1)}
                            disabled={!canProceed()}
                        >
                            Next
                        </button>
                    ) : (
                        <button
                            className="btn-primary"
                            onClick={handleSubmit}
                            disabled={loading || !canProceed()}
                        >
                            {loading ? (
                                <>
                                    <Loader size={16} className="spin" />
                                    Creating...
                                </>
                            ) : (
                                <>
                                    <Send size={16} />
                                    Create Campaign
                                </>
                            )}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default CampaignBuilderModal;
