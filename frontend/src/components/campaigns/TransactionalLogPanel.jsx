import React, { useState, useEffect, useCallback } from 'react';
import { X, RefreshCw, Zap, ChevronDown, Filter } from 'lucide-react';
import { getTransactionalEmails } from '../../services/apiService';
import './TransactionalLogPanel.css';

const STATUS_COLORS = {
    sent:      '#F59E0B',
    delivered: '#10b981',
    bounced:   '#ef4444',
    failed:    '#ef4444',
    opened:    '#6366f1',
    clicked:   '#ec4899',
};

const TRANSACTIONAL_LABELS = {
    early_access_invite:   'Early Access Invite',
    feature_announcement:  'Feature Announcement',
    password_reset:        'Password Reset',
    beta_unlock:           'Beta Unlock',
    feedback_confirmation: 'Feedback Confirmation',
    welcome:               'Welcome',
    trial_expiring:        'Trial Expiring',
};

const fmtDate = (d) => {
    if (!d) return '—';
    return new Date(d).toLocaleString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
};

const fmtLabel = (key) =>
    TRANSACTIONAL_LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

const PAGE_SIZE = 50;

const TransactionalLogPanel = ({ emailType, onClose }) => {
    const [emails, setEmails]         = useState([]);
    const [total, setTotal]           = useState(0);
    const [page, setPage]             = useState(0);
    const [loading, setLoading]       = useState(true);
    const [statusFilter, setStatusFilter] = useState('');
    const [showFilters, setShowFilters]   = useState(false);

    const load = useCallback(async (pg = 0, status = statusFilter) => {
        try {
            setLoading(true);
            const params = { limit: PAGE_SIZE, offset: pg * PAGE_SIZE };
            if (emailType) params.email_type = emailType;
            if (status)    params.delivery_status = status;
            const data = await getTransactionalEmails(params);
            setEmails(data.emails || []);
            setTotal(data.total || 0);
            setPage(pg);
        } catch (err) {
            console.error('Error loading transactional emails:', err);
        } finally {
            setLoading(false);
        }
    }, [emailType, statusFilter]);

    useEffect(() => { load(0, ''); }, [emailType]);

    const handleStatusFilter = (s) => {
        setStatusFilter(s);
        load(0, s);
    };

    return (
        <div className="tlp-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="tlp-panel">

                {/* Header */}
                <div className="tlp-header">
                    <div className="tlp-header-left">
                        <Zap size={16} className="tlp-icon" />
                        <div>
                            <h2 className="tlp-title">
                                {emailType ? fmtLabel(emailType) : 'All Transactional Emails'}
                            </h2>
                            <span className="tlp-subtitle">{total} records</span>
                        </div>
                    </div>
                    <div className="tlp-header-right">
                        <button
                            className={`tlp-btn-filter ${showFilters ? 'active' : ''}`}
                            onClick={() => setShowFilters(v => !v)}
                            title="Filter by status"
                        >
                            <Filter size={14} />
                        </button>
                        <button className="tlp-btn-refresh" onClick={() => load(page)} title="Refresh">
                            <RefreshCw size={14} className={loading ? 'spin' : ''} />
                        </button>
                        <button className="tlp-btn-close" onClick={onClose}>
                            <X size={18} />
                        </button>
                    </div>
                </div>

                {/* Filter bar */}
                {showFilters && (
                    <div className="tlp-filter-bar">
                        <span className="tlp-filter-label">Status:</span>
                        {['', 'sent', 'delivered', 'bounced', 'failed'].map(s => (
                            <button
                                key={s}
                                className={`tlp-filter-chip ${statusFilter === s ? 'active' : ''}`}
                                onClick={() => handleStatusFilter(s)}
                            >
                                {s === '' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1)}
                            </button>
                        ))}
                    </div>
                )}

                {/* Table */}
                <div className="tlp-body">
                    {loading ? (
                        <div className="tlp-loading">
                            <RefreshCw size={20} className="spin" />
                            <span>Loading…</span>
                        </div>
                    ) : emails.length === 0 ? (
                        <div className="tlp-empty">No transactional emails found.</div>
                    ) : (
                        <>
                            <div className="tlp-table">
                                <div className="tlp-head">
                                    <span>Recipient</span>
                                    <span>Type</span>
                                    <span>Status</span>
                                    <span>Sent At</span>
                                    <span>Opened</span>
                                    <span>Clicked</span>
                                </div>
                                {emails.map(e => (
                                    <div key={e.id} className="tlp-row">
                                        <div className="tlp-cell-recipient">
                                            <span className="tlp-email">{e.recipient_email}</span>
                                            {e.recipient_name && (
                                                <span className="tlp-name">{e.recipient_name}</span>
                                            )}
                                        </div>
                                        <span className="tlp-type">{fmtLabel(e.email_type)}</span>
                                        <span
                                            className="tlp-status"
                                            style={{ color: STATUS_COLORS[e.delivery_status] || '#6b7280' }}
                                        >
                                            {e.delivery_status}
                                        </span>
                                        <span className="tlp-date">{fmtDate(e.sent_at)}</span>
                                        <span className="tlp-date">{e.opened_at ? fmtDate(e.opened_at) : '—'}</span>
                                        <span className="tlp-date">{e.clicked_at ? fmtDate(e.clicked_at) : '—'}</span>
                                    </div>
                                ))}
                            </div>

                            {/* Pagination */}
                            {total > PAGE_SIZE && (
                                <div className="tlp-pagination">
                                    <button
                                        className="tlp-page-btn"
                                        disabled={page === 0}
                                        onClick={() => load(page - 1)}
                                    >
                                        Prev
                                    </button>
                                    <span className="tlp-page-info">
                                        {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
                                    </span>
                                    <button
                                        className="tlp-page-btn"
                                        disabled={(page + 1) * PAGE_SIZE >= total}
                                        onClick={() => load(page + 1)}
                                    >
                                        Next
                                    </button>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

export default TransactionalLogPanel;
