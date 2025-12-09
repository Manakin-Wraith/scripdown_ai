import React, { useState, useEffect } from 'react';
import { 
    Film, 
    User, 
    Mail, 
    Phone, 
    Calendar, 
    FileText, 
    Copyright,
    Award,
    Copy,
    Check
} from 'lucide-react';
import './ScriptHero.css';

const ScriptHero = ({ scriptId, metadata: propMetadata }) => {
    const [metadata, setMetadata] = useState(propMetadata || null);
    const [copiedField, setCopiedField] = useState(null);

    useEffect(() => {
        if (propMetadata) {
            setMetadata(propMetadata);
        }
    }, [propMetadata]);

    const copyToClipboard = async (text, field) => {
        if (!text) return;
        
        try {
            await navigator.clipboard.writeText(text);
            setCopiedField(field);
            setTimeout(() => setCopiedField(null), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    if (!metadata) {
        return null;
    }

    const hasContactInfo = metadata.writer_email || metadata.writer_phone;
    const hasDraftInfo = metadata.draft_version || metadata.draft_date;
    const hasLegalInfo = metadata.copyright_info || metadata.wga_registration;

    return (
        <div className="script-hero">
            <div className="hero-container">
                {/* Main Title Section */}
                <div className="hero-header">
                    <div className="title-section">
                        <Film size={32} className="title-icon" />
                        <div>
                            <h1 className="script-title">
                                {metadata.script_name?.replace('.pdf', '') || 'Untitled Script'}
                            </h1>
                            {metadata.writer_name && (
                                <p className="writer-name">
                                    <User size={16} />
                                    Written by {metadata.writer_name}
                                </p>
                            )}
                        </div>
                    </div>

                    {/* Draft Info Pills */}
                    {hasDraftInfo && (
                        <div className="draft-info">
                            {metadata.draft_version && (
                                <span className="draft-badge">
                                    <FileText size={14} />
                                    {metadata.draft_version}
                                </span>
                            )}
                            {metadata.draft_date && (
                                <span className="date-badge">
                                    <Calendar size={14} />
                                    {metadata.draft_date}
                                </span>
                            )}
                        </div>
                    )}
                </div>

                {/* Contact & Legal Info Grid */}
                {(hasContactInfo || hasLegalInfo || metadata.additional_credits) && (
                    <div className="hero-details">
                        {/* Contact Information */}
                        {hasContactInfo && (
                            <div className="detail-section">
                                <h3 className="section-title">Contact Information</h3>
                                <div className="contact-grid">
                                    {metadata.writer_email && (
                                        <div className="contact-item">
                                            <Mail size={16} className="contact-icon" />
                                            <span className="contact-text">{metadata.writer_email}</span>
                                            <button
                                                className="copy-btn"
                                                onClick={() => copyToClipboard(metadata.writer_email, 'email')}
                                                title="Copy email"
                                            >
                                                {copiedField === 'email' ? <Check size={14} /> : <Copy size={14} />}
                                            </button>
                                        </div>
                                    )}
                                    {metadata.writer_phone && (
                                        <div className="contact-item">
                                            <Phone size={16} className="contact-icon" />
                                            <span className="contact-text">{metadata.writer_phone}</span>
                                            <button
                                                className="copy-btn"
                                                onClick={() => copyToClipboard(metadata.writer_phone, 'phone')}
                                                title="Copy phone"
                                            >
                                                {copiedField === 'phone' ? <Check size={14} /> : <Copy size={14} />}
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Legal Information */}
                        {hasLegalInfo && (
                            <div className="detail-section">
                                <h3 className="section-title">Legal Information</h3>
                                <div className="legal-tags">
                                    {metadata.copyright_info && (
                                        <span className="legal-tag">
                                            <Copyright size={14} />
                                            {metadata.copyright_info}
                                        </span>
                                    )}
                                    {metadata.wga_registration && (
                                        <span className="legal-tag wga-tag">
                                            <Award size={14} />
                                            {metadata.wga_registration}
                                        </span>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Additional Credits */}
                        {metadata.additional_credits && (
                            <div className="detail-section full-width">
                                <h3 className="section-title">Additional Credits</h3>
                                <p className="credits-text">{metadata.additional_credits}</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default ScriptHero;
