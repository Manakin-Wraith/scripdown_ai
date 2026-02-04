import React, { useState, useEffect } from 'react';
import { X, Mail, Send, Loader } from 'lucide-react';
import { getEmailTemplates, createCampaign } from '../../services/apiService';
import './PersonalEmailModal.css';

const PersonalEmailModal = ({ isOpen, onClose, onSuccess }) => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [personalTemplate, setPersonalTemplate] = useState(null);

    const [formData, setFormData] = useState({
        name: '',
        recipient_emails: '',
        subject: '',
        message_body: '',
        founder_name: '',
        founder_title: 'Founder & CEO'
    });

    useEffect(() => {
        if (isOpen) {
            loadPersonalTemplate();
        }
    }, [isOpen]);

    const loadPersonalTemplate = async () => {
        try {
            const data = await getEmailTemplates();
            const template = data.templates?.find(t => t.name === 'Personal Message from Founder');
            setPersonalTemplate(template);
        } catch (err) {
            console.error('Error loading template:', err);
            setError('Failed to load email template');
        }
    };

    const handleInputChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        setError(null);
    };

    const handleSubmit = async () => {
        try {
            setLoading(true);
            setError(null);

            // Validate
            if (!formData.name.trim()) {
                setError('Campaign name is required');
                return;
            }
            if (!formData.recipient_emails.trim()) {
                setError('At least one recipient email is required');
                return;
            }
            if (!formData.subject.trim()) {
                setError('Email subject is required');
                return;
            }
            if (!formData.message_body.trim()) {
                setError('Message body is required');
                return;
            }
            if (!personalTemplate) {
                setError('Template not loaded');
                return;
            }

            const payload = {
                name: formData.name,
                description: 'Personal message from founder',
                template_id: personalTemplate.id,
                manual_recipients: formData.recipient_emails,
                template_variables: {
                    subject: formData.subject,
                    user_name: '{{user_name}}', // Will be replaced per recipient
                    message_body: formData.message_body,
                    founder_name: formData.founder_name,
                    founder_title: formData.founder_title,
                    founder_signature: ''
                },
                audience_filter: {}
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
        setFormData({
            name: '',
            recipient_emails: '',
            subject: '',
            message_body: '',
            founder_name: '',
            founder_title: 'Founder & CEO'
        });
        setError(null);
        onClose();
    };

    if (!isOpen) return null;

    const recipientCount = formData.recipient_emails.trim() 
        ? formData.recipient_emails.split(/[\n,]+/).filter(e => e.trim()).length 
        : 0;

    return (
        <div className="modal-overlay" onClick={handleClose}>
            <div className="personal-email-modal" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="modal-header">
                    <div className="header-content">
                        <Mail size={24} />
                        <h2>Send Personal Email</h2>
                    </div>
                    <button className="close-button" onClick={handleClose}>
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="modal-body">
                    {error && (
                        <div className="error-banner">
                            {error}
                        </div>
                    )}

                    <div className="form-section">
                        <div className="form-group">
                            <label>Campaign Name *</label>
                            <input
                                type="text"
                                value={formData.name}
                                onChange={e => handleInputChange('name', e.target.value)}
                                placeholder="e.g., Personal Check-in - January 2026"
                            />
                        </div>

                        <div className="form-group">
                            <label>Recipient Email Addresses *</label>
                            <textarea
                                value={formData.recipient_emails}
                                onChange={e => handleInputChange('recipient_emails', e.target.value)}
                                placeholder="Enter email addresses, one per line or comma-separated&#10;&#10;Example:&#10;user1@example.com&#10;user2@example.com, user3@example.com"
                                rows="4"
                                style={{ fontFamily: 'monospace', fontSize: '14px' }}
                            />
                            <small>
                                {recipientCount > 0 ? `${recipientCount} recipient(s)` : 'Enter email addresses'}
                            </small>
                        </div>

                        <div className="form-group">
                            <label>Email Subject *</label>
                            <input
                                type="text"
                                value={formData.subject}
                                onChange={e => handleInputChange('subject', e.target.value)}
                                placeholder="e.g., A personal note from the founder"
                            />
                        </div>

                        <div className="form-group">
                            <label>Your Message *</label>
                            <textarea
                                value={formData.message_body}
                                onChange={e => handleInputChange('message_body', e.target.value)}
                                placeholder="Write your personal message here...&#10;&#10;This will be sent as the main body of the email."
                                rows="10"
                            />
                            <small>Write your message in plain text or HTML</small>
                        </div>

                        <div className="form-row">
                            <div className="form-group">
                                <label>Your Name *</label>
                                <input
                                    type="text"
                                    value={formData.founder_name}
                                    onChange={e => handleInputChange('founder_name', e.target.value)}
                                    placeholder="e.g., John Smith"
                                />
                            </div>
                            <div className="form-group">
                                <label>Your Title</label>
                                <input
                                    type="text"
                                    value={formData.founder_title}
                                    onChange={e => handleInputChange('founder_title', e.target.value)}
                                    placeholder="e.g., Founder & CEO"
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="modal-footer">
                    <button className="btn-secondary" onClick={handleClose} disabled={loading}>
                        Cancel
                    </button>
                    <button className="btn-primary" onClick={handleSubmit} disabled={loading}>
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
                </div>
            </div>
        </div>
    );
};

export default PersonalEmailModal;
