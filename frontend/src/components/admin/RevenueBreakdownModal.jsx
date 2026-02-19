import React, { useState, useEffect } from 'react';
import { X, Search, TrendingUp, DollarSign, CreditCard, Calendar } from 'lucide-react';
import { supabase } from '../../lib/supabase';
import './RevenueBreakdownModal.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const PACKAGE_NAMES = {
  'single':   '1 Script (R99)',
  'pack_5':   '5 Scripts',
  'pack_10':  '10 Scripts',
  'pack_25':  '25 Scripts',
  'five':     '5 Scripts',
  'ten':      '10 Scripts',
  'twentyfive': '25 Scripts'
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
                        <td className="package-cell">
                          <span className="package-badge">
                            {PACKAGE_NAMES[payment.package_type] || payment.package_type}
                          </span>
                        </td>
                        <td className="credits-cell">{payment.credits_purchased}</td>
                        <td className="amount-cell">R{payment.amount.toFixed(2)}</td>
                        <td className="reference-cell">
                          {payment.payment_reference || payment.yoco_payment_id || '-'}
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
