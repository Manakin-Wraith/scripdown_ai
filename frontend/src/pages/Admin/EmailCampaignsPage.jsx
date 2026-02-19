import React, { useState, useEffect } from 'react';
import { 
    Mail, 
    Send, 
    Users, 
    Trash2,
    ArrowLeft,
    ChevronDown,
    ChevronUp
} from 'lucide-react';
import { 
    getCampaigns, 
    sendCampaign,
    deleteCampaign
} from '../../services/apiService';
import PersonalEmailModal from '../../components/campaigns/PersonalEmailModal';
import ConfirmDialog from '../../components/common/ConfirmDialog';
import AdminLayout from '../../components/admin/AdminLayout';
import './EmailCampaignsPageSimplified.css';

const EmailCampaignsPage = () => {
    const [campaigns, setCampaigns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showRecentCampaigns, setShowRecentCampaigns] = useState(true);
    const [confirmDialog, setConfirmDialog] = useState({
        isOpen: false,
        title: '',
        message: '',
        onConfirm: () => {},
        type: 'confirm',
        confirmText: 'OK',
        confirmButtonClass: 'btn-primary'
    });

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);
            setError(null);

            const campaignsData = await getCampaigns({ limit: 5 });
            setCampaigns(campaignsData.campaigns || []);
        } catch (err) {
            console.error('Error loading campaigns:', err);
            setError('Failed to load campaigns. Please try again.');
        } finally {
            setLoading(false);
        }
    };


    const handleSendCampaign = (campaignId) => {
        setConfirmDialog({
            isOpen: true,
            title: 'Send Campaign',
            message: 'Are you sure you want to send this campaign? This action cannot be undone.',
            confirmText: 'Send Now',
            cancelText: 'Cancel',
            type: 'confirm',
            confirmButtonClass: 'btn-primary',
            onConfirm: async () => {
                try {
                    await sendCampaign(campaignId);
                    await loadData();
                    setConfirmDialog({
                        isOpen: true,
                        title: 'Success',
                        message: 'Campaign sent successfully!',
                        confirmText: 'OK',
                        type: 'success',
                        confirmButtonClass: 'btn-primary',
                        onConfirm: () => {}
                    });
                } catch (err) {
                    console.error('Error sending campaign:', err);
                    setConfirmDialog({
                        isOpen: true,
                        title: 'Error',
                        message: 'Failed to send campaign. Please try again.',
                        confirmText: 'OK',
                        type: 'error',
                        confirmButtonClass: 'btn-danger',
                        onConfirm: () => {}
                    });
                }
            }
        });
    };

    const handleDeleteCampaign = (campaignId) => {
        setConfirmDialog({
            isOpen: true,
            title: 'Delete Campaign',
            message: 'Are you sure you want to delete this campaign? This action cannot be undone.',
            confirmText: 'Delete',
            cancelText: 'Cancel',
            type: 'confirm',
            confirmButtonClass: 'btn-danger',
            onConfirm: async () => {
                try {
                    await deleteCampaign(campaignId);
                    await loadData();
                    setConfirmDialog({
                        isOpen: true,
                        title: 'Success',
                        message: 'Campaign deleted successfully!',
                        confirmText: 'OK',
                        type: 'success',
                        confirmButtonClass: 'btn-primary',
                        onConfirm: () => {}
                    });
                } catch (err) {
                    console.error('Error deleting campaign:', err);
                    setConfirmDialog({
                        isOpen: true,
                        title: 'Error',
                        message: 'Failed to delete campaign. Please try again.',
                        confirmText: 'OK',
                        type: 'error',
                        confirmButtonClass: 'btn-danger',
                        onConfirm: () => {}
                    });
                }
            }
        });
    };

    const getStatusBadge = (status) => {
        const statusConfig = {
            draft: { icon: Clock, color: 'gray', label: 'Draft' },
            scheduled: { icon: Calendar, color: 'blue', label: 'Scheduled' },
            sending: { icon: Send, color: 'orange', label: 'Sending' },
            sent: { icon: CheckCircle, color: 'green', label: 'Sent' },
            paused: { icon: AlertCircle, color: 'yellow', label: 'Paused' },
            cancelled: { icon: AlertCircle, color: 'red', label: 'Cancelled' }
        };

        const config = statusConfig[status] || statusConfig.draft;
        const Icon = config.icon;

        return (
            <span className={`status-badge status-${config.color}`}>
                <Icon size={14} />
                {config.label}
            </span>
        );
    };

    const formatDate = (dateString) => {
        if (!dateString) return 'Not scheduled';
        return new Date(dateString).toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    if (loading) {
        return (
            <AdminLayout>
            <div className="email-campaigns-page">
                <div className="loading-state">
                    <Mail size={48} />
                    <p>Loading campaigns...</p>
                </div>
            </div>
            </AdminLayout>
        );
    }

    return (
        <AdminLayout>
        <div className="email-campaigns-page simplified">
            {/* Header */}
            <div className="page-header-simple">
                <Mail size={28} />
                <h1>Send Personal Email</h1>
            </div>

            {error && (
                <div className="error-banner">
                    {error}
                </div>
            )}

            {/* Quick Compose Section */}
            <div className="compose-section">
                <p className="compose-description">
                    Send a personal message to your users. Click "Create Email" to compose your message.
                </p>
                <button 
                    className="btn-primary-large"
                    onClick={() => setShowCreateModal(true)}
                >
                    <Mail size={20} />
                    Create Email
                </button>
            </div>

            {/* Recent Campaigns Section */}
            {campaigns.length > 0 && (
                <div className="recent-campaigns-section">
                    <button 
                        className="section-toggle"
                        onClick={() => setShowRecentCampaigns(!showRecentCampaigns)}
                    >
                        <h2>Recent Campaigns ({campaigns.length})</h2>
                        {showRecentCampaigns ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </button>

                    {showRecentCampaigns && (
                        <div className="campaigns-simple-list">
                            {campaigns.map(campaign => (
                                <div key={campaign.id} className="campaign-simple-card">
                                    <div className="campaign-simple-info">
                                        <h3>{campaign.name}</h3>
                                        <div className="campaign-simple-meta">
                                            <Users size={14} />
                                            <span>{campaign.total_recipients || 0} recipients</span>
                                            <span className="separator">•</span>
                                            <span>{formatDate(campaign.created_at)}</span>
                                        </div>
                                    </div>
                                    <div className="campaign-simple-actions">
                                        {campaign.status === 'draft' && (
                                            <button
                                                className="btn-send"
                                                onClick={() => handleSendCampaign(campaign.id)}
                                            >
                                                <Send size={16} />
                                                Send
                                            </button>
                                        )}
                                        {campaign.status === 'sent' && (
                                            <span className="status-sent">Sent</span>
                                        )}
                                        <button
                                            className="btn-delete-simple"
                                            onClick={() => handleDeleteCampaign(campaign.id)}
                                            title="Delete campaign"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Create Campaign Modal */}
            <PersonalEmailModal
                isOpen={showCreateModal}
                onClose={() => setShowCreateModal(false)}
                onSuccess={loadData}
            />

            <ConfirmDialog
                isOpen={confirmDialog.isOpen}
                onClose={() => setConfirmDialog({ ...confirmDialog, isOpen: false })}
                onConfirm={confirmDialog.onConfirm}
                title={confirmDialog.title}
                message={confirmDialog.message}
                confirmText={confirmDialog.confirmText}
                cancelText={confirmDialog.cancelText}
                type={confirmDialog.type}
                confirmButtonClass={confirmDialog.confirmButtonClass}
            />
        </div>
        </AdminLayout>
    );
};

export default EmailCampaignsPage;
