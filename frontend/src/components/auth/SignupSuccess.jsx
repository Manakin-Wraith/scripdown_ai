/**
 * SignupSuccess - Contextual success state after signup
 * 
 * Shows a celebratory success screen with:
 * - Personalized welcome message
 * - Email verification instructions
 * - Invite context (if coming from an invite)
 * - Quick actions (open email, resend)
 */

import React, { useState, useEffect } from 'react';
import { 
    Mail, 
    CheckCircle, 
    RefreshCw, 
    ExternalLink,
    Film,
    Users,
    FileText,
    MessageSquare,
    Sparkles
} from 'lucide-react';
import { resendVerificationEmail } from '../../lib/supabase';
import './SignupSuccess.css';

const SignupSuccess = ({ email, fullName, inviteContext }) => {
    const [resending, setResending] = useState(false);
    const [resent, setResent] = useState(false);
    const [error, setError] = useState(null);

    // Detect email provider for quick open button
    const getEmailProvider = (email) => {
        const domain = email.split('@')[1]?.toLowerCase();
        if (domain?.includes('gmail')) return { name: 'Gmail', url: 'https://mail.google.com' };
        if (domain?.includes('outlook') || domain?.includes('hotmail') || domain?.includes('live')) 
            return { name: 'Outlook', url: 'https://outlook.live.com' };
        if (domain?.includes('yahoo')) return { name: 'Yahoo Mail', url: 'https://mail.yahoo.com' };
        if (domain?.includes('icloud')) return { name: 'iCloud Mail', url: 'https://www.icloud.com/mail' };
        return null;
    };

    const emailProvider = getEmailProvider(email);

    const handleResend = async () => {
        setResending(true);
        setError(null);
        
        try {
            const { error } = await resendVerificationEmail(email);
            if (error) {
                setError(error.message);
            } else {
                setResent(true);
                setTimeout(() => setResent(false), 5000);
            }
        } catch (err) {
            setError('Failed to resend email');
        } finally {
            setResending(false);
        }
    };

    const firstName = fullName?.split(' ')[0] || 'there';

    return (
        <div className="signup-success">
            {/* Animated Success Icon */}
            <div className="success-icon-container">
                <div className="success-icon">
                    <Sparkles className="sparkle sparkle-1" size={16} />
                    <Sparkles className="sparkle sparkle-2" size={12} />
                    <Sparkles className="sparkle sparkle-3" size={14} />
                    <CheckCircle size={48} className="check-icon" />
                </div>
            </div>

            {/* Welcome Message */}
            <h2 className="success-title">
                {inviteContext ? (
                    <>Almost there, {firstName}!</>
                ) : (
                    <>Welcome to SlateOne, {firstName}!</>
                )}
            </h2>

            {/* Invite Context */}
            {inviteContext && (
                <div className="invite-context">
                    <p className="context-text">
                        One more step to join <strong>"{inviteContext.scriptTitle}"</strong> as
                    </p>
                    <div className="department-badge">
                        <Users size={16} />
                        <span>{inviteContext.department}</span>
                    </div>
                </div>
            )}

            {/* Email Verification Card */}
            <div className="verification-card">
                <div className="card-icon">
                    <Mail size={24} />
                </div>
                <div className="card-content">
                    <h3>Verify your email</h3>
                    <p className="email-address">{email}</p>
                    <p className="card-hint">
                        We sent a verification link to your inbox. 
                        Click the link to activate your account.
                    </p>
                </div>
            </div>

            {/* Quick Actions */}
            <div className="quick-actions">
                {emailProvider && (
                    <a 
                        href={emailProvider.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="btn-primary"
                    >
                        <ExternalLink size={18} />
                        Open {emailProvider.name}
                    </a>
                )}
                <button 
                    className="btn-secondary"
                    onClick={handleResend}
                    disabled={resending || resent}
                >
                    {resending ? (
                        <>
                            <RefreshCw size={18} className="spin" />
                            Sending...
                        </>
                    ) : resent ? (
                        <>
                            <CheckCircle size={18} />
                            Email Sent!
                        </>
                    ) : (
                        <>
                            <RefreshCw size={18} />
                            Resend Email
                        </>
                    )}
                </button>
            </div>

            {error && (
                <p className="resend-error">{error}</p>
            )}

            {/* What's Next Section */}
            {inviteContext && (
                <div className="whats-next">
                    <h4>After verification, you'll be able to:</h4>
                    <ul className="benefits-list">
                        <li>
                            <FileText size={16} />
                            <span>View script breakdowns & scene details</span>
                        </li>
                        <li>
                            <MessageSquare size={16} />
                            <span>Add notes for your department</span>
                        </li>
                        <li>
                            <Users size={16} />
                            <span>Collaborate with the production team</span>
                        </li>
                    </ul>
                </div>
            )}

            {/* Help Text */}
            <p className="help-text">
                Didn't receive the email? Check your spam folder or{' '}
                <button className="link-button" onClick={handleResend} disabled={resending}>
                    click here to resend
                </button>
            </p>
        </div>
    );
};

export default SignupSuccess;
