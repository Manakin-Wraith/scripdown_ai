import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle, XCircle, Clock, ExternalLink, ArrowLeft } from 'lucide-react';
import { supabase } from '../../lib/supabase';
import ApproveModal from './ApproveModal';
import RejectModal from './RejectModal';
import Toast from './Toast';
import AdminLayout from './AdminLayout';
import './PaymentVerification.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const PaymentVerification = () => {
  const navigate = useNavigate();
  const [pendingPayments, setPendingPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [approveModalOpen, setApproveModalOpen] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [selectedPayment, setSelectedPayment] = useState(null);
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    fetchPendingPayments();
  }, []);

  const showToast = (message, type = 'success') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
  };

  const removeToast = (id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  const fetchPendingPayments = async () => {
    try {
      setLoading(true);
      
      // Get auth token from Supabase session
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        throw new Error('Not authenticated');
      }
      
      const response = await fetch(`${API_BASE_URL}/api/admin/payments/pending`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      });
      
      if (!response.ok) throw new Error('Failed to fetch pending payments');
      
      const data = await response.json();
      setPendingPayments(data.data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveClick = (payment) => {
    setSelectedPayment({
      id: payment.id,
      email: payment.email,
      package: getPackageName(payment.package_type),
      amount: payment.amount,
      credits: payment.credits_purchased
    });
    setApproveModalOpen(true);
  };

  const handleApproveConfirm = async (reference, notes) => {
    try {
      // Get auth token from Supabase session
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(`${API_BASE_URL}/api/admin/payments/${selectedPayment.id}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          admin_reference: reference || null,
          notes: notes || null
        })
      });

      if (!response.ok) throw new Error('Failed to approve payment');

      setApproveModalOpen(false);
      setSelectedPayment(null);
      showToast('Payment approved! Credits added to user account.', 'success');
      fetchPendingPayments(); // Refresh list
    } catch (err) {
      showToast(`Error: ${err.message}`, 'error');
      setApproveModalOpen(false);
      setSelectedPayment(null);
    }
  };

  const handleRejectClick = (payment) => {
    setSelectedPayment({
      id: payment.id,
      email: payment.email,
      package: getPackageName(payment.package_type),
      amount: payment.amount
    });
    setRejectModalOpen(true);
  };

  const handleRejectConfirm = async (reason) => {
    try {
      // Get auth token from Supabase session
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(`${API_BASE_URL}/api/admin/payments/${selectedPayment.id}/reject`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({ reason })
      });

      if (!response.ok) throw new Error('Failed to reject payment');

      setRejectModalOpen(false);
      setSelectedPayment(null);
      showToast('Payment rejected successfully.', 'success');
      fetchPendingPayments(); // Refresh list
    } catch (err) {
      showToast(`Error: ${err.message}`, 'error');
      setRejectModalOpen(false);
      setSelectedPayment(null);
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

  const getPackageName = (packageType) => {
    const packages = {
      'single': '1 Script',
      'pack_5': '5 Scripts',
      'pack_10': '10 Scripts',
      'pack_25': '25 Scripts'
    };
    return packages[packageType] || packageType;
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="payment-verification">
          <div className="loading">Loading pending payments...</div>
        </div>
      </AdminLayout>
    );
  }

  if (error) {
    return (
      <AdminLayout>
        <div className="payment-verification">
          <div className="error">Error: {error}</div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
    <div className="payment-verification">
      <div className="verification-header">
        <div>
          <h2>Payment Verification</h2>
          <p className="subtitle">Review and approve pending credit purchases</p>
        </div>
        <div className="pending-count">
          <Clock size={20} />
          <span>{pendingPayments.length} pending</span>
        </div>
      </div>

      {pendingPayments.length === 0 ? (
        <div className="empty-state">
          <CheckCircle size={48} />
          <p>No pending payments</p>
          <small>All payments have been verified</small>
        </div>
      ) : (
        <div className="payments-table">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>User Email</th>
                <th>Package</th>
                <th>Amount</th>
                <th>Credits</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {pendingPayments.map((payment) => (
                <tr key={payment.id}>
                  <td className="date-cell">
                    {formatDate(payment.created_at)}
                  </td>
                  <td className="email-cell">
                    {payment.email}
                  </td>
                  <td className="package-cell">
                    {getPackageName(payment.package_type)}
                  </td>
                  <td className="amount-cell">
                    R{payment.amount.toFixed(2)}
                  </td>
                  <td className="credits-cell">
                    {payment.credits_purchased}
                  </td>
                  <td className="actions-cell">
                    <button
                      className="approve-btn"
                      onClick={() => handleApproveClick(payment)}
                      title="Approve payment"
                    >
                      <CheckCircle size={18} />
                      Approve
                    </button>
                    <button
                      className="reject-btn"
                      onClick={() => handleRejectClick(payment)}
                      title="Reject payment"
                    >
                      <XCircle size={18} />
                      Reject
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="verification-footer">
        <a
          href="https://app.yoco.com/sales"
          target="_blank"
          rel="noopener noreferrer"
          className="yoco-link"
        >
          <ExternalLink size={16} />
          Open Yoco Dashboard
        </a>
        <button onClick={fetchPendingPayments} className="refresh-btn">
          Refresh
        </button>
      </div>

      {/* Approve Modal */}
      <ApproveModal
        isOpen={approveModalOpen}
        onClose={() => {
          setApproveModalOpen(false);
          setSelectedPayment(null);
        }}
        onConfirm={handleApproveConfirm}
        paymentDetails={selectedPayment}
      />

      {/* Reject Modal */}
      <RejectModal
        isOpen={rejectModalOpen}
        onClose={() => {
          setRejectModalOpen(false);
          setSelectedPayment(null);
        }}
        onConfirm={handleRejectConfirm}
        paymentDetails={selectedPayment}
      />

      {/* Toast Notifications */}
      <div className="toast-container">
        {toasts.map(toast => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </div>
    </AdminLayout>
  );
};

export default PaymentVerification;
