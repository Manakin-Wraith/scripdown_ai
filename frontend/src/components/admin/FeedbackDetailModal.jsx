import React, { useState } from 'react';
import { X, Image as ImageIcon, Mail, Save, ExternalLink, Trash2 } from 'lucide-react';
import { supabase } from '../../lib/supabase';
import './FeedbackDetailModal.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const FeedbackDetailModal = ({ feedback, onClose, onUpdate }) => {
    const [status, setStatus] = useState(feedback.status);
    const [adminNotes, setAdminNotes] = useState(feedback.admin_notes || '');
    const [replyMessage, setReplyMessage] = useState('');
    const [updating, setUpdating] = useState(false);
    const [sending, setSending] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);

    // Update feedback status
    const handleUpdateStatus = async () => {
        try {
            setUpdating(true);
            setError(null);
            
            const { data: { session } } = await supabase.auth.getSession();
            if (!session?.access_token) return;

            const response = await fetch(`${API_BASE_URL}/api/feedback/${feedback.id}/status`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${session.access_token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    status,
                    admin_notes: adminNotes
                })
            });

            if (response.ok) {
                setSuccess('Status updated successfully');
                setTimeout(() => {
                    onUpdate();
                    setSuccess(null);
                }, 1500);
            } else {
                setError('Failed to update status');
            }
        } catch (err) {
            console.error('Error updating status:', err);
            setError('Error updating status');
        } finally {
            setUpdating(false);
        }
    };

    // Send reply to user
    const handleSendReply = async () => {
        if (!replyMessage.trim()) {
            setError('Please enter a reply message');
            return;
        }

        try {
            setSending(true);
            setError(null);
            
            const { data: { session } } = await supabase.auth.getSession();
            if (!session?.access_token) return;

            const response = await fetch(`${API_BASE_URL}/api/feedback/${feedback.id}/reply`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${session.access_token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    reply_message: replyMessage
                })
            });

            if (response.ok) {
                const data = await response.json();
                const userEmail = feedback.user_email || 'user';
                setSuccess(`✅ Reply sent to ${userEmail}!`);
                setReplyMessage('');
                
                // Auto-close modal after 2 seconds
                setTimeout(() => {
                    onUpdate(); // Refresh feedback list
                    onClose(); // Close modal
                }, 2000);
            } else {
                setError('Failed to send reply');
            }
        } catch (err) {
            console.error('Error sending reply:', err);
            setError('Error sending reply');
        } finally {
            setSending(false);
        }
    };

    // Delete feedback
    const handleDelete = async () => {
        try {
            setDeleting(true);
            setError(null);
            
            const { data: { session } } = await supabase.auth.getSession();
            if (!session?.access_token) return;

            const response = await fetch(`${API_BASE_URL}/api/feedback/${feedback.id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${session.access_token}`
                }
            });

            if (response.ok) {
                setSuccess('Feedback deleted successfully');
                setTimeout(() => {
                    onUpdate();
                    onClose();
                }, 1000);
            } else {
                const data = await response.json();
                setError(data.error || 'Failed to delete feedback');
            }
        } catch (err) {
            console.error('Error deleting feedback:', err);
            setError('Error deleting feedback');
        } finally {
            setDeleting(false);
            setShowDeleteConfirm(false);
        }
    };

    // Get category emoji
    const getCategoryEmoji = (category) => {
        const emojis = {
            bug: '🐛',
            feature: '✨',
            ui_ux: '🎨',
            general: '💬'
        };
        return emojis[category] || '💬';
    };

    // Format date
    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return new Intl.DateTimeFormat('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(date);
    };

    return (
        <div className="feedback-modal-overlay" onClick={onClose}>
            <div className="feedback-modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <div className="modal-title">
                        <span className="category-emoji-large">{getCategoryEmoji(feedback.category)}</span>
                        <div>
                            <h2>Feedback Details</h2>
                            <p className="feedback-id">ID: {feedback.id.substring(0, 8)}</p>
                        </div>
                    </div>
                    <button className="close-btn" onClick={onClose}>
                        <X size={24} />
                    </button>
                </div>

                <div className="modal-content">
                    {/* Feedback Info */}
                    <div className="info-section">
                        <div className="info-grid">
                            <div className="info-item">
                                <label>Category</label>
                                <span className="info-value">{feedback.category.replace('_', '/')}</span>
                            </div>
                            <div className="info-item">
                                <label>Priority</label>
                                <span className={`priority-badge priority-${feedback.priority}`}>
                                    {feedback.priority.toUpperCase()}
                                </span>
                            </div>
                            <div className="info-item">
                                <label>Submitted</label>
                                <span className="info-value">{formatDate(feedback.created_at)}</span>
                            </div>
                        </div>
                    </div>

                    {/* Subject & Description */}
                    <div className="content-section">
                        <h3>Subject</h3>
                        <p className="subject-text">{feedback.subject}</p>

                        <h3>Description</h3>
                        <p className="description-text">{feedback.description}</p>
                    </div>

                    {/* Screenshot */}
                    {feedback.screenshot_url && (
                        <div className="screenshot-section">
                            <h3>Screenshot</h3>
                            <a 
                                href={feedback.screenshot_url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="screenshot-link"
                            >
                                <ImageIcon size={18} />
                                View Screenshot
                                <ExternalLink size={14} />
                            </a>
                        </div>
                    )}

                    {/* Page Context */}
                    {feedback.page_context && (
                        <div className="context-section">
                            <h3>Page Context</h3>
                            <div className="context-grid">
                                {feedback.page_context.url && (
                                    <div className="context-item">
                                        <label>URL</label>
                                        <span>{feedback.page_context.url}</span>
                                    </div>
                                )}
                                {feedback.page_context.user_agent && (
                                    <div className="context-item">
                                        <label>Browser</label>
                                        <span>{feedback.page_context.user_agent.substring(0, 50)}...</span>
                                    </div>
                                )}
                                {feedback.page_context.viewport && (
                                    <div className="context-item">
                                        <label>Viewport</label>
                                        <span>
                                            {typeof feedback.page_context.viewport === 'object' 
                                                ? `${feedback.page_context.viewport.width}x${feedback.page_context.viewport.height}`
                                                : feedback.page_context.viewport
                                            }
                                        </span>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* User Info */}
                    <div className="user-section">
                        <h3>Submitted By</h3>
                        <div className="user-info">
                            <div>
                                <p className="user-name">{feedback.user_name || 'Unknown User'}</p>
                                <p className="user-email">{feedback.user_email || 'No email'}</p>
                            </div>
                        </div>
                    </div>

                    {/* Status Update */}
                    <div className="action-section">
                        <h3>Update Status</h3>
                        <div className="status-update">
                            <select 
                                value={status} 
                                onChange={(e) => setStatus(e.target.value)}
                                className="status-select"
                            >
                                <option value="new">New</option>
                                <option value="in_progress">In Progress</option>
                                <option value="resolved">Resolved</option>
                            </select>

                            <textarea
                                placeholder="Admin notes (optional)..."
                                value={adminNotes}
                                onChange={(e) => setAdminNotes(e.target.value)}
                                className="admin-notes"
                                rows="3"
                            />

                            <button 
                                className="update-btn"
                                onClick={handleUpdateStatus}
                                disabled={updating}
                            >
                                <Save size={18} />
                                {updating ? 'Updating...' : 'Update Status'}
                            </button>
                        </div>
                    </div>

                    {/* Reply to User */}
                    <div className="reply-section">
                        <h3>Reply to User</h3>
                        <textarea
                            placeholder="Type your reply message..."
                            value={replyMessage}
                            onChange={(e) => setReplyMessage(e.target.value)}
                            className="reply-textarea"
                            rows="4"
                        />
                        <button 
                            className="send-btn"
                            onClick={handleSendReply}
                            disabled={sending || !replyMessage.trim()}
                        >
                            <Mail size={18} />
                            {sending ? 'Sending...' : 'Send Reply Email'}
                        </button>
                    </div>

                    {/* Delete Feedback */}
                    <div className="delete-section">
                        <h3>Danger Zone</h3>
                        {!showDeleteConfirm ? (
                            <button 
                                className="delete-btn"
                                onClick={() => setShowDeleteConfirm(true)}
                            >
                                <Trash2 size={18} />
                                Delete Feedback
                            </button>
                        ) : (
                            <div className="delete-confirm">
                                <p className="delete-warning">
                                    ⚠️ Are you sure? This action cannot be undone.
                                </p>
                                <div className="delete-actions">
                                    <button 
                                        className="confirm-delete-btn"
                                        onClick={handleDelete}
                                        disabled={deleting}
                                    >
                                        {deleting ? 'Deleting...' : 'Yes, Delete'}
                                    </button>
                                    <button 
                                        className="cancel-delete-btn"
                                        onClick={() => setShowDeleteConfirm(false)}
                                        disabled={deleting}
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Messages */}
                    {error && (
                        <div className="message error-message">
                            {error}
                        </div>
                    )}
                    {success && (
                        <div className="message success-message">
                            {success}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default FeedbackDetailModal;
