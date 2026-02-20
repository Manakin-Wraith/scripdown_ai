import React, { useState, useEffect } from 'react';
import {
    Mail, Send, Users, Trash2, ChevronDown, ChevronUp,
    BarChart2, CheckCircle, Clock, AlertCircle, RefreshCw,
    FileText, Zap, TrendingUp, MousePointer, Package, Eye, XCircle,
} from 'lucide-react';
import {
    getCampaigns,
    sendCampaign,
    deleteCampaign,
    getEmailStats,
    getEmailTemplates,
} from '../../services/apiService';
import CampaignBuilderModal from '../../components/campaigns/CampaignBuilderModal';
import CampaignDetailPanel from '../../components/campaigns/CampaignDetailPanel';
import TemplateEditorModal from '../../components/campaigns/TemplateEditorModal';
import TransactionalLogPanel from '../../components/campaigns/TransactionalLogPanel';
import AudienceUsersPanel from '../../components/campaigns/AudienceUsersPanel';
import ConfirmDialog from '../../components/common/ConfirmDialog';
import AdminLayout from '../../components/admin/AdminLayout';
import './EmailCampaignsPageSimplified.css';

// ── Helpers ──────────────────────────────────────────────────────────────────
const TRANSACTIONAL_LABELS = {
    early_access_invite:   'Early Access Invite',
    feature_announcement:  'Feature Announcement',
    password_reset:        'Password Reset',
    beta_unlock:           'Beta Unlock',
    feedback_confirmation: 'Feedback Confirmation',
    welcome:               'Welcome',
    trial_expiring:        'Trial Expiring',
};

const STATUS_CONFIG = {
    draft:     { color: 'gray',   label: 'Draft',     Icon: Clock },
    scheduled: { color: 'blue',   label: 'Scheduled', Icon: Clock },
    sending:   { color: 'orange', label: 'Sending',   Icon: Send },
    sent:      { color: 'green',  label: 'Sent',      Icon: CheckCircle },
    partial:   { color: 'yellow', label: 'Partial',   Icon: AlertCircle },
    failed:    { color: 'red',    label: 'Failed',    Icon: XCircle },
    cancelled: { color: 'red',    label: 'Cancelled', Icon: XCircle },
};

const TEMPLATE_CATEGORY_COLORS = {
    transactional: '#6366f1',
    marketing:     '#F59E0B',
    notification:  '#10b981',
    personal:      '#ec4899',
};

const fmtDate = (d) => {
    if (!d) return '—';
    return new Date(d).toLocaleString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
};

const fmtLabel = (key) =>
    TRANSACTIONAL_LABELS[key] ||
    key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

// ── Sub-components ────────────────────────────────────────────────────────────
const KpiCard = ({ icon: Icon, label, value, sub, color = '#F59E0B' }) => (
    <div className="ec-kpi-card">
        <div className="ec-kpi-icon" style={{ background: `${color}18`, color }}>
            <Icon size={20} />
        </div>
        <div className="ec-kpi-body">
            <div className="ec-kpi-value">{value ?? '—'}</div>
            <div className="ec-kpi-label">{label}</div>
            {sub && <div className="ec-kpi-sub">{sub}</div>}
        </div>
    </div>
);

const RateBar = ({ label, value, color }) => (
    <div className="ec-rate-row">
        <span className="ec-rate-label">{label}</span>
        <div className="ec-rate-bar-wrap">
            <div className="ec-rate-bar-fill" style={{ width: `${Math.min(value, 100)}%`, background: color }} />
        </div>
        <span className="ec-rate-pct">{value}%</span>
    </div>
);

const StatusBadge = ({ status }) => {
    const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
    const { Icon, color, label } = cfg;
    return (
        <span className={`ec-status-badge ec-status-${color}`}>
            <Icon size={12} />{label}
        </span>
    );
};

// ── Page ──────────────────────────────────────────────────────────────────────
const EmailCampaignsPage = () => {
    const [campaigns, setCampaigns]           = useState([]);
    const [templates, setTemplates]           = useState([]);
    const [stats, setStats]                   = useState(null);
    const [loading, setLoading]               = useState(true);
    const [statsLoading, setStatsLoading]     = useState(true);
    const [error, setError]                   = useState(null);
    const [showCreateModal, setShowCreateModal]     = useState(false);
    const [showCampaigns, setShowCampaigns]         = useState(true);
    const [showTransactional, setShowTransactional] = useState(true);
    const [showTemplates, setShowTemplates]         = useState(false);
    const [selectedCampaignId, setSelectedCampaignId]     = useState(null);
    const [selectedTemplate, setSelectedTemplate]         = useState(null);
    const [transactionalType, setTransactionalType]       = useState(null);
    const [audienceStatus, setAudienceStatus]             = useState(null);
    const [confirmDialog, setConfirmDialog] = useState({
        isOpen: false, title: '', message: '', onConfirm: () => {},
        type: 'confirm', confirmText: 'OK', confirmButtonClass: 'btn-primary',
    });

    useEffect(() => { loadAll(); }, []);

    const loadAll = () => Promise.all([loadCampaignsAndTemplates(), loadStats()]);

    const loadCampaignsAndTemplates = async () => {
        try {
            setLoading(true); setError(null);
            const [cd, td] = await Promise.all([
                getCampaigns({ limit: 50 }),
                getEmailTemplates({ active_only: false }),
            ]);
            setCampaigns(cd.campaigns || []);
            setTemplates(td.templates || []);
        } catch (err) {
            console.error('Error loading campaigns:', err);
            setError('Failed to load campaign data.');
        } finally { setLoading(false); }
    };

    const loadStats = async () => {
        try {
            setStatsLoading(true);
            const data = await getEmailStats();
            if (data.success) setStats(data);
        } catch (err) {
            console.error('Error loading stats:', err);
        } finally { setStatsLoading(false); }
    };

    const handleSendCampaign = (campaignId) => {
        setConfirmDialog({
            isOpen: true,
            title: 'Send Campaign',
            message: 'Are you sure you want to send this campaign? This action cannot be undone.',
            confirmText: 'Send Now', cancelText: 'Cancel',
            type: 'confirm', confirmButtonClass: 'btn-primary',
            onConfirm: async () => {
                try { await sendCampaign(campaignId); await loadAll(); }
                catch (err) { console.error('Error sending campaign:', err); }
                finally { setConfirmDialog(d => ({ ...d, isOpen: false })); }
            },
        });
    };

    const handleDeleteCampaign = (campaignId) => {
        setConfirmDialog({
            isOpen: true,
            title: 'Delete Campaign',
            message: 'Are you sure you want to delete this campaign? This action cannot be undone.',
            confirmText: 'Delete', cancelText: 'Cancel',
            type: 'confirm', confirmButtonClass: 'btn-danger',
            onConfirm: async () => {
                try { await deleteCampaign(campaignId); await loadAll(); }
                catch (err) { console.error('Error deleting campaign:', err); }
                finally { setConfirmDialog(d => ({ ...d, isOpen: false })); }
            },
        });
    };

    const cStats  = stats?.campaigns    || {};
    const tStats  = stats?.transactional || {};
    const tmStats = stats?.templates    || {};
    const aStats  = stats?.audience     || {};

    const transactionalEntries = Object.entries(tStats.by_type || {}).sort(
        (a, b) => b[1].total - a[1].total
    );
    const maxTrans = transactionalEntries.reduce((m, [, v]) => Math.max(m, v.total), 1);

    return (
        <AdminLayout>
        <div className="ec-page">

            {/* Header */}
            <div className="ec-page-header">
                <div className="ec-page-title">
                    <Mail size={26} />
                    <div>
                        <h1>Email Campaigns</h1>
                        <p>Campaigns &middot; Transactional &middot; Templates &middot; Audience</p>
                    </div>
                </div>
                <div className="ec-header-actions">
                    <button className="ec-btn-refresh" onClick={loadAll} title="Refresh">
                        <RefreshCw size={16} />
                    </button>
                    <button className="ec-btn-compose" onClick={() => setShowCreateModal(true)}>
                        <Mail size={16} /> New Email
                    </button>
                </div>
            </div>

            {error && <div className="error-banner">{error}</div>}

            {/* KPI Row */}
            <div className="ec-kpi-row">
                <KpiCard icon={Send}         label="Emails Sent"
                    value={(cStats.emails_sent ?? 0) + (tStats.total ?? 0)}
                    sub={`${cStats.emails_sent ?? 0} campaign · ${tStats.total ?? 0} transactional`}
                    color="#F59E0B" />
                <KpiCard icon={TrendingUp}   label="Delivery Rate"
                    value={cStats.delivery_rate != null ? `${cStats.delivery_rate}%` : '—'}
                    sub={`${cStats.emails_delivered ?? 0} delivered`}
                    color="#10b981" />
                <KpiCard icon={Eye}          label="Open Rate"
                    value={cStats.open_rate != null ? `${cStats.open_rate}%` : '—'}
                    sub={`${cStats.emails_opened ?? 0} opened`}
                    color="#6366f1" />
                <KpiCard icon={MousePointer} label="Click Rate"
                    value={cStats.click_rate != null ? `${cStats.click_rate}%` : '—'}
                    sub={`${cStats.emails_clicked ?? 0} clicked`}
                    color="#ec4899" />
                <KpiCard icon={Users}        label="Total Audience" value={aStats.total ?? '—'}
                    sub={`${aStats.by_status?.active ?? 0} active · ${aStats.by_status?.trial ?? 0} trial`}
                    color="#8b5cf6" />
                <KpiCard icon={FileText}     label="Templates"      value={tmStats.active ?? '—'}
                    sub={`${tmStats.total ?? 0} total`} color="#0ea5e9" />
            </div>

            {/* Main grid */}
            <div className="ec-grid">

                {/* LEFT: Campaign list */}
                <div className="ec-panel">
                    <button className="ec-section-toggle" onClick={() => setShowCampaigns(v => !v)}>
                        <span className="ec-section-title">
                            <BarChart2 size={16} /> Campaigns
                            <span className="ec-badge">{campaigns.length}</span>
                        </span>
                        {showCampaigns ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>

                    {showCampaigns && (
                        loading ? (
                            <div className="ec-loading"><RefreshCw size={18} className="spin" /><span>Loading…</span></div>
                        ) : campaigns.length === 0 ? (
                            <div className="ec-empty">No campaigns yet. Create your first email above.</div>
                        ) : (
                            <div className="ec-campaign-list">
                                {campaigns.map(c => {
                                    const sent    = c.emails_sent || 0;
                                    const opened  = c.emails_opened || 0;
                                    const clicked = c.emails_clicked || 0;
                                    const openRate  = sent > 0 ? Math.round(opened  / sent * 100) : 0;
                                    const clickRate = sent > 0 ? Math.round(clicked / sent * 100) : 0;
                                    return (
                                        <div key={c.id} className="ec-campaign-card" onClick={() => setSelectedCampaignId(c.id)} style={{ cursor: 'pointer' }}>
                                            <div className="ec-campaign-top">
                                                <div className="ec-campaign-name-row">
                                                    <span className="ec-campaign-name">{c.name}</span>
                                                    <StatusBadge status={c.status} />
                                                </div>
                                                <div className="ec-campaign-meta">
                                                    <span>{c.email_templates?.name || 'Custom template'}</span>
                                                    <span className="ec-dot">&middot;</span>
                                                    <span>{fmtDate(c.sent_at || c.created_at)}</span>
                                                </div>
                                            </div>
                                            <div className="ec-campaign-metrics">
                                                <div className="ec-metric">
                                                    <span className="ec-metric-val">{c.total_recipients || 0}</span>
                                                    <span className="ec-metric-lbl">Recipients</span>
                                                </div>
                                                <div className="ec-metric">
                                                    <span className="ec-metric-val">{sent}</span>
                                                    <span className="ec-metric-lbl">Sent</span>
                                                </div>
                                                <div className="ec-metric">
                                                    <span className="ec-metric-val">{openRate}%</span>
                                                    <span className="ec-metric-lbl">Open Rate</span>
                                                </div>
                                                <div className="ec-metric">
                                                    <span className="ec-metric-val">{clickRate}%</span>
                                                    <span className="ec-metric-lbl">Click Rate</span>
                                                </div>
                                            </div>
                                            <div className="ec-campaign-actions" onClick={e => e.stopPropagation()}>
                                                {c.status === 'draft' && (
                                                    <button className="ec-btn-send" onClick={() => handleSendCampaign(c.id)}>
                                                        <Send size={13} /> Send
                                                    </button>
                                                )}
                                                <button className="ec-btn-delete" onClick={() => handleDeleteCampaign(c.id)} title="Delete">
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )
                    )}
                </div>

                {/* RIGHT: Stats panels */}
                <div className="ec-right-col">

                    {/* Campaign performance rates */}
                    {!statsLoading && cStats.total > 0 && (
                        <div className="ec-panel ec-rates-panel">
                            <div className="ec-panel-header">
                                <TrendingUp size={15} /><span>Campaign Performance</span>
                            </div>
                            <div className="ec-rates">
                                <RateBar label="Delivery" value={cStats.delivery_rate ?? 0} color="#10b981" />
                                <RateBar label="Open"     value={cStats.open_rate ?? 0}     color="#6366f1" />
                                <RateBar label="Click"    value={cStats.click_rate ?? 0}    color="#ec4899" />
                            </div>
                            <div className="ec-rates-sub">
                                <span><AlertCircle size={12} /> {cStats.emails_bounced ?? 0} bounced</span>
                                <span><XCircle size={12} /> {cStats.emails_failed ?? 0} failed</span>
                            </div>
                        </div>
                    )}

                    {/* Audience breakdown */}
                    <div className="ec-panel">
                        <div className="ec-panel-header">
                            <Users size={15} /><span>Audience Breakdown</span>
                        </div>
                        {statsLoading ? (
                            <div className="ec-loading"><RefreshCw size={16} className="spin" /></div>
                        ) : (
                            <div className="ec-audience-rows">
                                {Object.entries(aStats.by_status || {}).map(([status, count]) => {
                                    const pct   = Math.round(count / (aStats.total || 1) * 100);
                                    const color = status === 'active' ? '#10b981' : status === 'trial' ? '#F59E0B' : '#6b7280';
                                    return (
                                        <div
                                            key={status}
                                            className="ec-audience-row"
                                            onClick={() => setAudienceStatus(status)}
                                            style={{ cursor: 'pointer' }}
                                            title={`View ${status} users`}
                                        >
                                            <div className="ec-audience-dot" style={{ background: color }} />
                                            <span className="ec-audience-status">
                                                {status.charAt(0).toUpperCase() + status.slice(1)}
                                            </span>
                                            <span className="ec-audience-count">{count}</span>
                                            <div className="ec-audience-bar-wrap">
                                                <div className="ec-audience-bar" style={{ width: `${pct}%`, background: color }} />
                                            </div>
                                            <span className="ec-audience-pct">{pct}%</span>
                                        </div>
                                    );
                                })}
                                <div
                                    className="ec-audience-total"
                                    onClick={() => setAudienceStatus('')}
                                    style={{ cursor: 'pointer' }}
                                    title="View all users"
                                >
                                    <span>Total reachable</span>
                                    <strong>{aStats.total ?? 0} users</strong>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Transactional emails */}
                    <div className="ec-panel">
                        <button className="ec-section-toggle" onClick={() => setShowTransactional(v => !v)}>
                            <span className="ec-section-title">
                                <Zap size={16} /> Transactional Emails
                                <span className="ec-badge">{tStats.total ?? 0}</span>
                            </span>
                            {showTransactional ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>
                        {showTransactional && (
                            statsLoading ? (
                                <div className="ec-loading"><RefreshCw size={16} className="spin" /></div>
                            ) : transactionalEntries.length === 0 ? (
                                <div className="ec-empty">No transactional emails logged.</div>
                            ) : (
                                <div className="ec-trans-list">
                                    {transactionalEntries.map(([type, data]) => (
                                        <div
                                            key={type}
                                            className="ec-trans-row"
                                            onClick={() => setTransactionalType(type)}
                                            style={{ cursor: 'pointer' }}
                                            title="Click to view log"
                                        >
                                            <div className="ec-trans-info">
                                                <span className="ec-trans-label">{fmtLabel(type)}</span>
                                                <span className="ec-trans-count">{data.total}</span>
                                            </div>
                                            <div className="ec-trans-bar-wrap">
                                                <div className="ec-trans-bar"
                                                    style={{ width: `${Math.round(data.total / maxTrans * 100)}%` }} />
                                                {data.delivered > 0 && (
                                                    <div className="ec-trans-bar ec-trans-bar-delivered"
                                                        style={{ width: `${Math.round(data.delivered / maxTrans * 100)}%` }} />
                                                )}
                                            </div>
                                            <div className="ec-trans-sub-counts">
                                                {data.delivered > 0 && <span className="ec-trans-chip delivered">{data.delivered} delivered</span>}
                                                {data.opened   > 0 && <span className="ec-trans-chip opened">{data.opened} opened</span>}
                                                {data.clicked  > 0 && <span className="ec-trans-chip clicked">{data.clicked} clicked</span>}
                                                {data.failed   > 0 && <span className="ec-trans-chip failed">{data.failed} failed</span>}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )
                        )}
                    </div>

                    {/* Templates */}
                    <div className="ec-panel">
                        <button className="ec-section-toggle" onClick={() => setShowTemplates(v => !v)}>
                            <span className="ec-section-title">
                                <Package size={16} /> Email Templates
                                <span className="ec-badge">{templates.length}</span>
                            </span>
                            {showTemplates ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>
                        {showTemplates && (
                            loading ? (
                                <div className="ec-loading"><RefreshCw size={16} className="spin" /></div>
                            ) : (
                                <div className="ec-template-list">
                                    {templates.map(t => (
                                        <div key={t.id} className="ec-template-row" onClick={() => setSelectedTemplate(t)} style={{ cursor: 'pointer' }}>
                                            <div className="ec-template-dot"
                                                style={{ background: TEMPLATE_CATEGORY_COLORS[t.category] || '#6b7280' }} />
                                            <div className="ec-template-info">
                                                <span className="ec-template-name">{t.name}</span>
                                                <span className="ec-template-subject">{t.subject}</span>
                                            </div>
                                            <span className="ec-template-cat"
                                                style={{ color: TEMPLATE_CATEGORY_COLORS[t.category] || '#6b7280' }}>
                                                {t.category}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )
                        )}
                    </div>

                </div>{/* end right col */}
            </div>{/* end grid */}

            <CampaignBuilderModal
                isOpen={showCreateModal}
                onClose={() => setShowCreateModal(false)}
                onSuccess={loadAll}
            />

            {selectedCampaignId && (
                <CampaignDetailPanel
                    campaignId={selectedCampaignId}
                    onClose={() => setSelectedCampaignId(null)}
                    onUpdate={loadAll}
                    onDelete={loadAll}
                />
            )}

            {selectedTemplate && (
                <TemplateEditorModal
                    template={selectedTemplate}
                    onClose={() => setSelectedTemplate(null)}
                    onSave={() => { setSelectedTemplate(null); loadAll(); }}
                    onDelete={() => { setSelectedTemplate(null); loadAll(); }}
                />
            )}

            {transactionalType !== null && (
                <TransactionalLogPanel
                    emailType={transactionalType || null}
                    onClose={() => setTransactionalType(null)}
                />
            )}

            {audienceStatus !== null && (
                <AudienceUsersPanel
                    statusFilter={audienceStatus}
                    onClose={() => setAudienceStatus(null)}
                />
            )}

            <ConfirmDialog
                isOpen={confirmDialog.isOpen}
                onClose={() => setConfirmDialog(d => ({ ...d, isOpen: false }))}
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
