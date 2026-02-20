import React, { useState, useEffect, useCallback } from 'react';
import {
    X, Send, Trash2, Edit2, Check, XCircle, Clock, CheckCircle,
    AlertCircle, Users, TrendingUp, MousePointer, Eye, RefreshCw,
    ChevronDown, ChevronUp, Calendar,
} from 'lucide-react';
import {
    getCampaign,
    getCampaignAnalytics,
    getCampaignRecipients,
    updateCampaign,
    sendCampaign,
    deleteCampaign,
} from '../../services/apiService';
import './CampaignDetailPanel.css';

const STATUS_CONFIG = {
    draft:     { color: 'gray',   label: 'Draft',     Icon: Clock },
    scheduled: { color: 'blue',   label: 'Scheduled', Icon: Calendar },
    sending:   { color: 'orange', label: 'Sending',   Icon: Send },
    sent:      { color: 'green',  label: 'Sent',      Icon: CheckCircle },
    partial:   { color: 'yellow', label: 'Partial',   Icon: AlertCircle },
    failed:    { color: 'red',    label: 'Failed',    Icon: XCircle },
    cancelled: { color: 'red',    label: 'Cancelled', Icon: XCircle },
};

const RECIPIENT_STATUS_COLORS = {
    pending:   '#6b7280',
    sent:      '#F59E0B',
    delivered: '#10b981',
    opened:    '#6366f1',
    clicked:   '#ec4899',
    failed:    '#ef4444',
    bounced:   '#f97316',
};

const fmtDate = (d) => {
    if (!d) return '—';
    return new Date(d).toLocaleString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
};

const RateBar = ({ label, value, color, count }) => (
    <div className="cdp-rate-row">
        <span className="cdp-rate-label">{label}</span>
        <div className="cdp-rate-bar-wrap">
            <div className="cdp-rate-bar-fill" style={{ width: `${Math.min(value, 100)}%`, background: color }} />
        </div>
        <span className="cdp-rate-pct">{value}%</span>
        {count != null && <span className="cdp-rate-count">({count})</span>}
    </div>
);

const CampaignDetailPanel = ({ campaignId, onClose, onUpdate, onDelete }) => {
    const [campaign, setCampaign]     = useState(null);
    const [analytics, setAnalytics]   = useState(null);
    const [recipients, setRecipients] = useState([]);
    const [recipTotal, setRecipTotal] = useState(0);
    const [loading, setLoading]       = useState(true);
    const [recipLoading, setRecipLoading] = useState(false);
    const [error, setError]           = useState(null);
    const [showRecipients, setShowRecipients] = useState(false);
    const [recipPage, setRecipPage]   = useState(0);
    const PAGE_SIZE = 20;

    const [editing, setEditing]       = useState(false);
    const [editForm, setEditForm]     = useState({ name: '', description: '', scheduled_at: '' });
    const [saving, setSaving]         = useState(false);
    const [saveError, setSaveError]   = useState(null);

    const [actionLoading, setActionLoading] = useState(false);

    const load = useCallback(async () => {
        if (!campaignId) return;
        try {
            setLoading(true); setError(null);
            const [cd, ad] = await Promise.all([
                getCampaign(campaignId),
                getCampaignAnalytics(campaignId),
            ]);
            if (cd.success) {
                setCampaign(cd.campaign);
                setEditForm({
                    name: cd.campaign.name || '',
                    description: cd.campaign.description || '',
                    scheduled_at: cd.campaign.scheduled_at
                        ? cd.campaign.scheduled_at.slice(0, 16)
                        : '',
                });
            }
            if (ad.success) setAnalytics(ad.analytics);
        } catch (err) {
            setError('Failed to load campaign details.');
        } finally { setLoading(false); }
    }, [campaignId]);

    useEffect(() => { load(); }, [load]);

    const loadRecipients = useCallback(async (page = 0) => {
        try {
            setRecipLoading(true);
            const data = await getCampaignRecipients(campaignId, {
                limit: PAGE_SIZE,
                offset: page * PAGE_SIZE,
            });
            setRecipients(data.recipients || []);
            setRecipTotal(data.total || 0);
            setRecipPage(page);
        } catch (err) {
            console.error('Error loading recipients:', err);
        } finally { setRecipLoading(false); }
    }, [campaignId]);

    const handleToggleRecipients = () => {
        if (!showRecipients && recipients.length === 0) loadRecipients(0);
        setShowRecipients(v => !v);
    };

    const handleSaveEdit = async () => {
        try {
            setSaving(true); setSaveError(null);
            const updates = { name: editForm.name, description: editForm.description };
            if (editForm.scheduled_at) updates.scheduled_at = editForm.scheduled_at;
            const result = await updateCampaign(campaignId, updates);
            if (result.success) {
                setCampaign(prev => ({ ...prev, ...result.campaign }));
                setEditing(false);
                onUpdate && onUpdate();
            } else {
                setSaveError(result.error || 'Failed to save.');
            }
        } catch (err) {
            setSaveError('Failed to save changes.');
        } finally { setSaving(false); }
    };

    const handleSend = async () => {
        if (!window.confirm('Send this campaign now? This cannot be undone.')) return;
        try {
            setActionLoading(true);
            await sendCampaign(campaignId);
            await load();
            onUpdate && onUpdate();
        } catch (err) {
            console.error('Error sending:', err);
        } finally { setActionLoading(false); }
    };

    const handleDelete = async () => {
        if (!window.confirm('Delete this campaign? This cannot be undone.')) return;
        try {
            setActionLoading(true);
            await deleteCampaign(campaignId);
            onDelete && onDelete();
            onClose();
        } catch (err) {
            console.error('Error deleting:', err);
        } finally { setActionLoading(false); }
    };

    const canEdit = campaign && ['draft', 'scheduled'].includes(campaign.status);
    const statusCfg = campaign ? (STATUS_CONFIG[campaign.status] || STATUS_CONFIG.draft) : null;

    return (
        <div className="cdp-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="cdp-panel">

                {/* Header */}
                <div className="cdp-header">
                    <div className="cdp-header-left">
                        {loading ? (
                            <span className="cdp-title-placeholder">Loading…</span>
                        ) : editing ? (
                            <input
                                className="cdp-title-input"
                                value={editForm.name}
                                onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))}
                                autoFocus
                            />
                        ) : (
                            <h2 className="cdp-title">{campaign?.name}</h2>
                        )}
                        {statusCfg && !loading && (
                            <span className={`cdp-status-badge cdp-status-${statusCfg.color}`}>
                                <statusCfg.Icon size={12} />{statusCfg.label}
                            </span>
                        )}
                    </div>
                    <div className="cdp-header-right">
                        {canEdit && !editing && (
                            <button className="cdp-btn-icon" onClick={() => setEditing(true)} title="Edit">
                                <Edit2 size={15} />
                            </button>
                        )}
                        {editing && (
                            <>
                                <button className="cdp-btn-save" onClick={handleSaveEdit} disabled={saving}>
                                    {saving ? <RefreshCw size={14} className="spin" /> : <Check size={14} />}
                                    Save
                                </button>
                                <button className="cdp-btn-icon" onClick={() => { setEditing(false); setSaveError(null); }}>
                                    <X size={15} />
                                </button>
                            </>
                        )}
                        {!editing && campaign?.status === 'draft' && (
                            <button className="cdp-btn-send" onClick={handleSend} disabled={actionLoading}>
                                <Send size={14} /> Send Now
                            </button>
                        )}
                        {!editing && (
                            <button className="cdp-btn-delete" onClick={handleDelete} disabled={actionLoading} title="Delete">
                                <Trash2 size={15} />
                            </button>
                        )}
                        <button className="cdp-btn-close" onClick={onClose}>
                            <X size={18} />
                        </button>
                    </div>
                </div>

                {saveError && <div className="cdp-save-error">{saveError}</div>}

                {loading ? (
                    <div className="cdp-loading">
                        <RefreshCw size={22} className="spin" />
                        <span>Loading campaign…</span>
                    </div>
                ) : error ? (
                    <div className="cdp-error">{error}</div>
                ) : (
                    <div className="cdp-body">

                        {/* Meta info / editable fields */}
                        <div className="cdp-meta-grid">
                            <div className="cdp-meta-item">
                                <span className="cdp-meta-label">Template</span>
                                <span className="cdp-meta-value">{campaign.email_templates?.name || '—'}</span>
                            </div>
                            <div className="cdp-meta-item">
                                <span className="cdp-meta-label">Created</span>
                                <span className="cdp-meta-value">{fmtDate(campaign.created_at)}</span>
                            </div>
                            <div className="cdp-meta-item">
                                <span className="cdp-meta-label">Sent At</span>
                                <span className="cdp-meta-value">{fmtDate(campaign.sent_at)}</span>
                            </div>
                            <div className="cdp-meta-item">
                                <span className="cdp-meta-label">Scheduled</span>
                                {editing ? (
                                    <input
                                        type="datetime-local"
                                        className="cdp-input"
                                        value={editForm.scheduled_at}
                                        onChange={e => setEditForm(f => ({ ...f, scheduled_at: e.target.value }))}
                                    />
                                ) : (
                                    <span className="cdp-meta-value">{fmtDate(campaign.scheduled_at)}</span>
                                )}
                            </div>
                            {editing && (
                                <div className="cdp-meta-item cdp-meta-full">
                                    <span className="cdp-meta-label">Description</span>
                                    <textarea
                                        className="cdp-textarea"
                                        value={editForm.description}
                                        onChange={e => setEditForm(f => ({ ...f, description: e.target.value }))}
                                        rows={2}
                                        placeholder="Campaign description…"
                                    />
                                </div>
                            )}
                            {!editing && campaign.description && (
                                <div className="cdp-meta-item cdp-meta-full">
                                    <span className="cdp-meta-label">Description</span>
                                    <span className="cdp-meta-value">{campaign.description}</span>
                                </div>
                            )}
                        </div>

                        {/* Analytics */}
                        {analytics && (
                            <div className="cdp-section">
                                <div className="cdp-section-title">
                                    <TrendingUp size={14} /> Performance
                                </div>

                                {/* Metric tiles */}
                                <div className="cdp-metric-tiles">
                                    <div className="cdp-tile">
                                        <span className="cdp-tile-val">{analytics.total_recipients}</span>
                                        <span className="cdp-tile-lbl">Recipients</span>
                                    </div>
                                    <div className="cdp-tile">
                                        <span className="cdp-tile-val">{analytics.emails_sent}</span>
                                        <span className="cdp-tile-lbl">Sent</span>
                                    </div>
                                    <div className="cdp-tile">
                                        <span className="cdp-tile-val">{analytics.emails_delivered}</span>
                                        <span className="cdp-tile-lbl">Delivered</span>
                                    </div>
                                    <div className="cdp-tile">
                                        <span className="cdp-tile-val">{analytics.emails_opened}</span>
                                        <span className="cdp-tile-lbl">Opened</span>
                                    </div>
                                    <div className="cdp-tile">
                                        <span className="cdp-tile-val">{analytics.emails_clicked}</span>
                                        <span className="cdp-tile-lbl">Clicked</span>
                                    </div>
                                    <div className="cdp-tile cdp-tile-warn">
                                        <span className="cdp-tile-val">{analytics.emails_bounced}</span>
                                        <span className="cdp-tile-lbl">Bounced</span>
                                    </div>
                                    <div className="cdp-tile cdp-tile-danger">
                                        <span className="cdp-tile-val">{analytics.emails_failed}</span>
                                        <span className="cdp-tile-lbl">Failed</span>
                                    </div>
                                </div>

                                {/* Rate bars */}
                                <div className="cdp-rates">
                                    <RateBar label="Delivery" value={analytics.delivery_rate} color="#10b981" count={analytics.emails_delivered} />
                                    <RateBar label="Open"     value={analytics.open_rate}     color="#6366f1" count={analytics.emails_opened} />
                                    <RateBar label="Click"    value={analytics.click_rate}    color="#ec4899" count={analytics.emails_clicked} />
                                    <RateBar label="CTO"      value={analytics.click_to_open_rate} color="#F59E0B" />
                                </div>
                            </div>
                        )}

                        {/* Recipient status breakdown from campaign detail */}
                        {campaign.recipient_status_counts && Object.keys(campaign.recipient_status_counts).length > 0 && (
                            <div className="cdp-section">
                                <div className="cdp-section-title">
                                    <Users size={14} /> Recipient Status Breakdown
                                </div>
                                <div className="cdp-recip-status-grid">
                                    {Object.entries(campaign.recipient_status_counts).map(([status, count]) => (
                                        <div key={status} className="cdp-recip-status-tile">
                                            <div className="cdp-recip-dot" style={{ background: RECIPIENT_STATUS_COLORS[status] || '#6b7280' }} />
                                            <span className="cdp-recip-status-label">
                                                {status.charAt(0).toUpperCase() + status.slice(1)}
                                            </span>
                                            <span className="cdp-recip-status-count">{count}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Recipient list drill-down */}
                        <div className="cdp-section">
                            <button className="cdp-collapsible" onClick={handleToggleRecipients}>
                                <span className="cdp-section-title">
                                    <Eye size={14} /> Recipient List
                                    <span className="cdp-badge">{recipTotal || campaign.total_recipients || 0}</span>
                                </span>
                                {showRecipients ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            </button>

                            {showRecipients && (
                                recipLoading ? (
                                    <div className="cdp-loading-sm"><RefreshCw size={14} className="spin" /> Loading…</div>
                                ) : recipients.length === 0 ? (
                                    <div className="cdp-empty">No recipient records found.</div>
                                ) : (
                                    <>
                                        <div className="cdp-recip-table">
                                            <div className="cdp-recip-head">
                                                <span>Email</span>
                                                <span>Status</span>
                                                <span>Sent At</span>
                                            </div>
                                            {recipients.map(r => (
                                                <div key={r.id} className="cdp-recip-row">
                                                    <span className="cdp-recip-email">{r.email}</span>
                                                    <span
                                                        className="cdp-recip-status"
                                                        style={{ color: RECIPIENT_STATUS_COLORS[r.status] || '#6b7280' }}
                                                    >
                                                        {r.status}
                                                    </span>
                                                    <span className="cdp-recip-date">{fmtDate(r.sent_at)}</span>
                                                </div>
                                            ))}
                                        </div>
                                        {/* Pagination */}
                                        {recipTotal > PAGE_SIZE && (
                                            <div className="cdp-pagination">
                                                <button
                                                    className="cdp-page-btn"
                                                    disabled={recipPage === 0}
                                                    onClick={() => loadRecipients(recipPage - 1)}
                                                >
                                                    Prev
                                                </button>
                                                <span className="cdp-page-info">
                                                    {recipPage * PAGE_SIZE + 1}–{Math.min((recipPage + 1) * PAGE_SIZE, recipTotal)} of {recipTotal}
                                                </span>
                                                <button
                                                    className="cdp-page-btn"
                                                    disabled={(recipPage + 1) * PAGE_SIZE >= recipTotal}
                                                    onClick={() => loadRecipients(recipPage + 1)}
                                                >
                                                    Next
                                                </button>
                                            </div>
                                        )}
                                    </>
                                )
                            )}
                        </div>

                    </div>
                )}
            </div>
        </div>
    );
};

export default CampaignDetailPanel;
