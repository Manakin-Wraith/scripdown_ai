import React, { useState, useEffect } from 'react';
import { X, AlertCircle } from 'lucide-react';
import './RejectModal.css';

const RejectModal = ({ isOpen, onClose, onConfirm, paymentDetails }) => {
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen) {
      setReason('');
      setError('');
    }
  }, [isOpen]);

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!reason.trim()) {
      setError('Please provide a rejection reason');
      return;
    }

    onConfirm(reason.trim());
    setReason('');
    setError('');
  };

  const handleCancel = () => {
    setReason('');
    setError('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleCancel}>
      <div className="reject-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-section">
            <AlertCircle size={24} className="modal-icon" />
            <div>
              <h3>Reject Payment</h3>
              <p className="modal-subtitle">Provide a reason for rejection</p>
            </div>
          </div>
          <button onClick={handleCancel} className="modal-close-btn">
            <X size={20} />
          </button>
        </div>

        {paymentDetails && (
          <div className="payment-info">
            <div className="info-row">
              <span className="info-label">Email:</span>
              <span className="info-value">{paymentDetails.email}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Package:</span>
              <span className="info-value">{paymentDetails.package}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Amount:</span>
              <span className="info-value">R{paymentDetails.amount}</span>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label htmlFor="rejection-reason">Rejection Reason *</label>
            <textarea
              id="rejection-reason"
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                setError('');
              }}
              placeholder="e.g., Payment not found in Yoco, Invalid reference, Duplicate payment..."
              rows={4}
              className={error ? 'error' : ''}
              autoFocus
            />
            {error && (
              <span className="error-message">
                <AlertCircle size={14} />
                {error}
              </span>
            )}
          </div>

          <div className="modal-actions">
            <button type="button" onClick={handleCancel} className="btn-cancel">
              Cancel
            </button>
            <button type="submit" className="btn-reject">
              Reject Payment
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default RejectModal;
