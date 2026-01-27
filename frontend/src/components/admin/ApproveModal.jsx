import React, { useState, useEffect } from 'react';
import { X, CheckCircle } from 'lucide-react';
import './ApproveModal.css';

const ApproveModal = ({ isOpen, onClose, onConfirm, paymentDetails }) => {
  const [reference, setReference] = useState('');
  const [notes, setNotes] = useState('');

  useEffect(() => {
    if (isOpen) {
      setReference('');
      setNotes('');
    }
  }, [isOpen]);

  const handleSubmit = (e) => {
    e.preventDefault();
    onConfirm(reference.trim(), notes.trim());
    setReference('');
    setNotes('');
  };

  const handleCancel = () => {
    setReference('');
    setNotes('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleCancel}>
      <div className="approve-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-section">
            <CheckCircle size={24} className="modal-icon-success" />
            <div>
              <h3>Approve Payment</h3>
              <p className="modal-subtitle">Verify and approve this credit purchase</p>
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
            <div className="info-row">
              <span className="info-label">Credits:</span>
              <span className="info-value success">{paymentDetails.credits} credits</span>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label htmlFor="yoco-reference">Yoco Reference Number (Optional)</label>
            <input
              type="text"
              id="yoco-reference"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="e.g., YC-123456789"
              autoFocus
            />
            <span className="field-hint">Enter the Yoco payment reference for tracking</span>
          </div>

          <div className="form-group">
            <label htmlFor="admin-notes">Admin Notes (Optional)</label>
            <textarea
              id="admin-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any internal notes about this approval..."
              rows={3}
            />
          </div>

          <div className="modal-actions">
            <button type="button" onClick={handleCancel} className="btn-cancel">
              Cancel
            </button>
            <button type="submit" className="btn-approve">
              <CheckCircle size={18} />
              Approve Payment
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ApproveModal;
