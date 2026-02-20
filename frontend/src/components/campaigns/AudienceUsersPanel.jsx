import React, { useState, useEffect, useCallback } from 'react';
import { X, RefreshCw, Users } from 'lucide-react';
import { getAudienceUsers } from '../../services/apiService';
import './AudienceUsersPanel.css';

const STATUS_COLORS = {
    active:    '#10b981',
    trial:     '#F59E0B',
    expired:   '#6b7280',
    cancelled: '#ef4444',
    unknown:   '#4b5563',
};

const fmtDate = (d) => {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
    });
};

const PAGE_SIZE = 50;

const AudienceUsersPanel = ({ statusFilter, onClose }) => {
    const [users, setUsers]   = useState([]);
    const [total, setTotal]   = useState(0);
    const [page, setPage]     = useState(0);
    const [loading, setLoading] = useState(true);

    const load = useCallback(async (pg = 0) => {
        try {
            setLoading(true);
            const params = { limit: PAGE_SIZE, offset: pg * PAGE_SIZE };
            if (statusFilter) params.status = statusFilter;
            const data = await getAudienceUsers(params);
            setUsers(data.users || []);
            setTotal(data.total || 0);
            setPage(pg);
        } catch (err) {
            console.error('Error loading audience users:', err);
        } finally {
            setLoading(false);
        }
    }, [statusFilter]);

    useEffect(() => { load(0); }, [statusFilter]);

    const statusColor = STATUS_COLORS[statusFilter] || '#9ca3af';
    const statusLabel = statusFilter
        ? statusFilter.charAt(0).toUpperCase() + statusFilter.slice(1)
        : 'All';

    return (
        <div className="aup-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="aup-panel">

                {/* Header */}
                <div className="aup-header">
                    <div className="aup-header-left">
                        <div className="aup-status-dot" style={{ background: statusColor }} />
                        <div>
                            <h2 className="aup-title">
                                <Users size={15} />
                                {statusLabel} Users
                            </h2>
                            <span className="aup-subtitle">{total} total</span>
                        </div>
                    </div>
                    <div className="aup-header-right">
                        <button className="aup-btn-refresh" onClick={() => load(page)} title="Refresh">
                            <RefreshCw size={14} className={loading ? 'spin' : ''} />
                        </button>
                        <button className="aup-btn-close" onClick={onClose}>
                            <X size={18} />
                        </button>
                    </div>
                </div>

                {/* Body */}
                <div className="aup-body">
                    {loading ? (
                        <div className="aup-loading">
                            <RefreshCw size={20} className="spin" />
                            <span>Loading users…</span>
                        </div>
                    ) : users.length === 0 ? (
                        <div className="aup-empty">No users found for this segment.</div>
                    ) : (
                        <>
                            <div className="aup-table">
                                <div className="aup-head">
                                    <span>Name</span>
                                    <span>Email</span>
                                    <span>Status</span>
                                    <span>Trial Ends</span>
                                    <span>Joined</span>
                                </div>
                                {users.map(u => (
                                    <div key={u.id} className="aup-row">
                                        <span className="aup-name">{u.full_name || '—'}</span>
                                        <span className="aup-email">{u.email}</span>
                                        <span
                                            className="aup-status"
                                            style={{ color: STATUS_COLORS[u.subscription_status] || '#6b7280' }}
                                        >
                                            {u.subscription_status || '—'}
                                        </span>
                                        <span className="aup-date">{fmtDate(u.trial_ends_at)}</span>
                                        <span className="aup-date">{fmtDate(u.created_at)}</span>
                                    </div>
                                ))}
                            </div>

                            {total > PAGE_SIZE && (
                                <div className="aup-pagination">
                                    <button
                                        className="aup-page-btn"
                                        disabled={page === 0}
                                        onClick={() => load(page - 1)}
                                    >
                                        Prev
                                    </button>
                                    <span className="aup-page-info">
                                        {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
                                    </span>
                                    <button
                                        className="aup-page-btn"
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

export default AudienceUsersPanel;
