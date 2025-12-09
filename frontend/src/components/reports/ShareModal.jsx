import React, { useState, useEffect } from 'react';
import { 
    X, Copy, Check, Link2, Clock, Printer, 
    Download, ExternalLink, AlertCircle, Loader
} from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { 
    createReportShareLink, 
    revokeReportShareLink,
    getSharedReportPrintUrl,
    getSharedReportPdfUrl
} from '../../services/apiService';
import './ShareModal.css';

const ShareModal = ({ report, onClose, onUpdate }) => {
    const toast = useToast();
    const [isCreating, setIsCreating] = useState(false);
    const [isRevoking, setIsRevoking] = useState(false);
    const [copied, setCopied] = useState(false);
    const [expiresInDays, setExpiresInDays] = useState(7);
    
    const shareUrl = report.share_token 
        ? `${window.location.origin}/shared/${report.share_token}`
        : null;
    
    const expiresAt = report.expires_at 
        ? new Date(report.expires_at).toLocaleDateString()
        : null;

    const handleCreateLink = async () => {
        setIsCreating(true);
        try {
            const res = await createReportShareLink(report.id, expiresInDays);
            if (res.success) {
                toast.success('Link Created', 'Share link is ready!');
                onUpdate({
                    ...report,
                    share_token: res.share_token,
                    is_public: true,
                    expires_at: res.expires_at
                });
            }
        } catch (error) {
            toast.error('Error', 'Failed to create share link');
        } finally {
            setIsCreating(false);
        }
    };

    const handleRevokeLink = async () => {
        if (!window.confirm('Revoke this share link? Anyone with the link will lose access.')) return;
        
        setIsRevoking(true);
        try {
            await revokeReportShareLink(report.id);
            toast.success('Link Revoked', 'Share link has been disabled');
            onUpdate({
                ...report,
                share_token: null,
                is_public: false,
                expires_at: null
            });
        } catch (error) {
            toast.error('Error', 'Failed to revoke share link');
        } finally {
            setIsRevoking(false);
        }
    };

    const handleCopy = async () => {
        if (!shareUrl) return;
        
        try {
            await navigator.clipboard.writeText(shareUrl);
            setCopied(true);
            toast.success('Copied', 'Link copied to clipboard');
            setTimeout(() => setCopied(false), 2000);
        } catch (error) {
            toast.error('Error', 'Failed to copy link');
        }
    };

    const handleOpenPrint = () => {
        if (report.share_token) {
            window.open(getSharedReportPrintUrl(report.share_token), '_blank');
        }
    };

    const handleOpenPdf = () => {
        if (report.share_token) {
            window.open(getSharedReportPdfUrl(report.share_token), '_blank');
        }
    };

    return (
        <div className="share-modal-overlay" onClick={onClose}>
            <div className="share-modal" onClick={e => e.stopPropagation()}>
                <div className="share-modal-header">
                    <h2>
                        <Link2 size={20} />
                        Share Report
                    </h2>
                    <button className="close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                <div className="share-modal-content">
                    <div className="report-info">
                        <span className="report-name">{report.title}</span>
                    </div>

                    {report.share_token ? (
                        /* Existing Share Link */
                        <div className="share-link-section">
                            <label>Share Link</label>
                            <div className="share-link-input">
                                <input 
                                    type="text" 
                                    value={shareUrl} 
                                    readOnly 
                                />
                                <button 
                                    className="copy-btn"
                                    onClick={handleCopy}
                                >
                                    {copied ? <Check size={16} /> : <Copy size={16} />}
                                </button>
                            </div>
                            
                            <div className="link-meta">
                                <span className="expires">
                                    <Clock size={12} />
                                    Expires: {expiresAt}
                                </span>
                            </div>

                            <div className="share-actions">
                                <button 
                                    className="action-btn"
                                    onClick={handleOpenPrint}
                                >
                                    <Printer size={16} />
                                    Print View
                                </button>
                                <button 
                                    className="action-btn"
                                    onClick={handleOpenPdf}
                                >
                                    <Download size={16} />
                                    Download PDF
                                </button>
                                <button 
                                    className="action-btn"
                                    onClick={() => window.open(shareUrl, '_blank')}
                                >
                                    <ExternalLink size={16} />
                                    Open Link
                                </button>
                            </div>

                            <button 
                                className="revoke-btn"
                                onClick={handleRevokeLink}
                                disabled={isRevoking}
                            >
                                {isRevoking ? (
                                    <>
                                        <Loader size={14} className="spin" />
                                        Revoking...
                                    </>
                                ) : (
                                    'Revoke Share Link'
                                )}
                            </button>
                        </div>
                    ) : (
                        /* Create New Link */
                        <div className="create-link-section">
                            <p className="create-info">
                                Create a shareable link that anyone can use to view this report.
                            </p>

                            <div className="expiry-selector">
                                <label>Link expires in:</label>
                                <select 
                                    value={expiresInDays}
                                    onChange={(e) => setExpiresInDays(Number(e.target.value))}
                                >
                                    <option value={1}>1 day</option>
                                    <option value={7}>7 days</option>
                                    <option value={14}>14 days</option>
                                    <option value={30}>30 days</option>
                                    <option value={90}>90 days</option>
                                </select>
                            </div>

                            <button 
                                className="create-btn"
                                onClick={handleCreateLink}
                                disabled={isCreating}
                            >
                                {isCreating ? (
                                    <>
                                        <Loader size={16} className="spin" />
                                        Creating...
                                    </>
                                ) : (
                                    <>
                                        <Link2 size={16} />
                                        Create Share Link
                                    </>
                                )}
                            </button>

                            <div className="share-note">
                                <AlertCircle size={14} />
                                <span>Anyone with the link can view and print this report</span>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ShareModal;
