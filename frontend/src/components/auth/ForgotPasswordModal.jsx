/**
 * ForgotPasswordModal - Password Reset Request Component
 * 
 * Allows users to request a password reset email.
 * Tablet-first design matching AuthModal styling.
 */

import React, { useState } from 'react';
import { 
    X, 
    Mail, 
    Loader,
    ArrowLeft,
    CheckCircle,
    AlertCircle,
    KeyRound
} from 'lucide-react';
import { resetPassword } from '../../lib/supabase';
import './AuthModal.css';

const ForgotPasswordModal = ({ isOpen, onClose, onBackToLogin }) => {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            const { error } = await resetPassword(email);
            
            if (error) {
                setError(error.message);
            } else {
                setSuccess(true);
            }
        } catch (err) {
            setError(err.message || 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        setEmail('');
        setError(null);
        setSuccess(false);
        onClose();
    };

    const handleBackToLogin = () => {
        setEmail('');
        setError(null);
        setSuccess(false);
        onBackToLogin();
    };

    if (!isOpen) return null;

    return (
        <>
            {/* Backdrop */}
            <div className="auth-backdrop" onClick={handleClose} />
            
            {/* Modal */}
            <div className="auth-modal">
                {/* Close button */}
                <button className="auth-close" onClick={handleClose}>
                    <X size={20} />
                </button>

                {/* Header */}
                <div className="auth-header">
                    <div className="auth-logo">
                        <KeyRound size={32} />
                    </div>
                    <h2>{success ? 'Check Your Email' : 'Reset Password'}</h2>
                    <p>
                        {success 
                            ? `We've sent a password reset link to ${email}`
                            : 'Enter your email and we\'ll send you a reset link'
                        }
                    </p>
                </div>

                {/* Error Message */}
                {error && (
                    <div className="auth-message error">
                        <AlertCircle size={18} />
                        <span>{error}</span>
                    </div>
                )}

                {/* Success State */}
                {success ? (
                    <div className="auth-success-state">
                        <div className="success-icon">
                            <CheckCircle size={48} />
                        </div>
                        <p className="success-text">
                            Click the link in the email to reset your password. 
                            The link will expire in 1 hour.
                        </p>
                        <p className="success-hint">
                            Didn't receive the email? Check your spam folder or try again.
                        </p>
                        <button 
                            type="button" 
                            className="auth-submit secondary"
                            onClick={() => setSuccess(false)}
                        >
                            Try Again
                        </button>
                    </div>
                ) : (
                    /* Form */
                    <form onSubmit={handleSubmit} className="auth-form">
                        <div className="form-group">
                            <label htmlFor="reset-email">
                                <Mail size={18} />
                                Email Address
                            </label>
                            <input
                                id="reset-email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="you@production.com"
                                required
                                autoComplete="email"
                                autoFocus
                            />
                        </div>

                        <button 
                            type="submit" 
                            className="auth-submit"
                            disabled={loading}
                        >
                            {loading ? (
                                <>
                                    <Loader size={18} className="spin" />
                                    Sending...
                                </>
                            ) : (
                                'Send Reset Link'
                            )}
                        </button>
                    </form>
                )}

                {/* Back to Login */}
                <div className="auth-switch">
                    <button 
                        type="button" 
                        className="link-btn back-btn" 
                        onClick={handleBackToLogin}
                    >
                        <ArrowLeft size={16} />
                        Back to Sign In
                    </button>
                </div>
            </div>
        </>
    );
};

export default ForgotPasswordModal;
