import React, { useState, useEffect } from 'react';
import { X, Search, TrendingUp, DollarSign, CreditCard, Calendar } from 'lucide-react';
import { supabase } from '../../lib/supabase';
import './RevenueBreakdownModal.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const PACKAGE_NAMES = {
  'single':        '1 Breakdown (R500)',
  'pack_5':        '5 Breakdowns (R2,000)',
  'pack_10':       '10 Breakdowns (R3,500)',
  'pack_25':       '25 Breakdowns (R7,500)',
  'five':          '5 Breakdowns',
  'ten':           '10 Breakdowns',
  'twentyfive':    '25 Breakdowns',
  'beta_access':   'Beta Access (6 months)',
  'early_adopter': 'Early Adopter'
};

const getBadgeStyle = (packageType) => {
  switch (packageType) {
    case 'beta_access':
      return { background: 'rgba(124,58,237,0.2)', color: '#c4b5fd', border: '1px solid rgba(124,58,237,0.4)' };
    case 'early_adopter':
      return { background: 'rgba(245,158,11,0.2)', color: '#fcd34d', border: '1px solid rgba(245,158,11,0.4)' };
    default:
      return {};
  }
};

const RevenueBreakdownModal = ({ isOpen, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');

  useEffect(() => {
    if (isOpen) {
      fetchRevenueDetails();
    }
  }, [isOpen, searchTerm, sortBy, sortOrder]);

  const fetchRevenueDetails = async () => {
    try {
      setLoading(true);
      
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        throw new Error('Not authenticated');
      }

      const params = new URLSearchParams({
        sort_by: sortBy,
        sort_order: sortOrder
      });

      if (searchTerm) {
        params.append('search', searchTerm);
      }

      const response = await fetch(`${API_BASE_URL}/api/admin/analytics/revenue/details?${params}`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      });

      if (!response.ok) throw new Error('Failed to fetch revenue details');

      const result = await response.json();
      console.log('[RevenueModal] payments sample:', result.payments?.slice(0, 3).map(p => ({ email: p.email, package_type: p.package_type, payment_type: p.payment_type })));
      setData(result);
    } catch (err) {
      console.error('Error fetching revenue details:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('en-ZA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="revenue-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="revenue-modal__header">
          <div className="revenue-modal__title-section">
            <TrendingUp size={24} className="revenue-modal__icon" />
            <div>
              <h2>Revenue Breakdown</h2>
              <p className="revenue-modal__subtitle">Detailed payment history and analytics</p>
            </div>
          </div>
          <button onClick={onClose} className="modal-close-btn">
            <X size={20} />
          </button>
        </div>

        {loading ? (
          <div className="revenue-modal__loading">
            <div className="spinner"></div>
            <p>Loading revenue data...</p>
          </div>
        ) : data?.success ? (
          <>
            {/* Summary Stats */}
            <div className="revenue-summary">
              <div className="summary-card">
                <div className="summary-card__icon">
                  <DollarSign size={20} />
                </div>
                <div className="summary-card__content">
                  <span className="summary-card__label">Total Revenue</span>
                  <span className="summary-card__value">R{data.summary.total_revenue.toFixed(2)}</span>
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-card__icon">
                  <CreditCard size={20} />
                </div>
                <div className="summary-card__content">
                  <span className="summary-card__label">Payments</span>
                  <span className="summary-card__value">{data.summary.payment_count}</span>
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-card__icon">
                  <TrendingUp size={20} />
                </div>
                <div className="summary-card__content">
                  <span className="summary-card__label">Average</span>
                  <span className="summary-card__value">R{data.summary.average_payment.toFixed(2)}</span>
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-card__icon">
                  <Calendar size={20} />
                </div>
                <div className="summary-card__content">
                  <span className="summary-card__label">Period</span>
                  <span className="summary-card__value">{data.summary.period}</span>
                </div>
              </div>
            </div>

            {/* Search Bar */}
            <div className="revenue-modal__controls">
              <div className="search-box">
                <Search size={18} />
                <input
                  type="text"
                  placeholder="Search by email..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>

            {/* Payments Table */}
            <div className="revenue-table-container">
              <table className="revenue-table">
                <thead>
                  <tr>
                    <th onClick={() => handleSort('created_at')} className="sortable">
                      Date {sortBy === 'created_at' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th onClick={() => handleSort('email')} className="sortable">
                      Email {sortBy === 'email' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th>Package</th>
                    <th>Credits</th>
                    <th onClick={() => handleSort('amount')} className="sortable">
                      Amount {sortBy === 'amount' && (sortOrder === 'asc' ? '↑' : '↓')}
                    </th>
                    <th>Reference</th>
                  </tr>
                </thead>
                <tbody>
                  {data.payments.length > 0 ? (
                    data.payments.map((payment) => (
                      <tr key={payment.id}>
                        <td className="date-cell">{formatDate(payment.created_at)}</td>
                        <td className="email-cell">{payment.email}</td>
                        <td className="revenue-package-cell">
                          {payment.package_type
                            ? (PACKAGE_NAMES[payment.package_type] || payment.package_type)
                            : '—'}
                        </td>
                        <td className="credits-cell">
                          {payment.package_type === 'beta_access' ? 1 : payment.credits_purchased}
                        </td>
                        <td className="amount-cell">R{Number(payment.amount).toFixed(2)}</td>
                        <td className="reference-cell">
                          {payment.payment_reference || '-'}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="6" className="empty-state">
                        {searchTerm ? 'No payments found matching your search' : 'No payments yet'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <div className="revenue-modal__error">
            <p>Failed to load revenue data</p>
            <button onClick={fetchRevenueDetails} className="btn-retry">
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default RevenueBreakdownModal;
