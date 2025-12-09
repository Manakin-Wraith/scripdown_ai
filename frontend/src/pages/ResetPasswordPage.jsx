/**
 * ResetPasswordPage - Password Update Landing Page
 * 
 * Users land here after clicking the password reset link in their email.
 * Supabase automatically handles the token verification via URL hash.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
    Lock, 
    Eye, 
    EyeOff, 
    Loader,
    CheckCircle,
    AlertCircle,
    KeyRound,
    Film
} from 'lucide-react';
import { supabase, updatePassword } from '../lib/supabase';
import './ResetPasswordPage.css';

const ResetPasswordPage = () => {
    const navigate = useNavigate();
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);
    const [sessionReady, setSessionReady] = useState(false);
    const [checkingSession, setCheckingSession] = useState(true);

    // Check if user has a valid recovery session
    useEffect(() => {
        const checkSession = async () => {
            try {
                // Supabase automatically handles the recovery token from URL hash
                const { data: { session }, error } = await supabase.auth.getSession();
                
                if (error) {
                    console.error('Session error:', error);
                    setError('Invalid or expired reset link. Please request a new one.');
                } else if (session) {
                    setSessionReady(true);
                } else {
                    // No session - might be loading from hash
                    // Listen for auth state change
                    const { data: { subscription } } = supabase.auth.onAuthStateChange(
                        (event, session) => {
                            if (event === 'PASSWORD_RECOVERY') {
                                setSessionReady(true);
                            } else if (event === 'SIGNED_IN' && session) {
                                setSessionReady(true);
                            }
                        }
                    );
                    
                    // Cleanup subscription after 5 seconds if no event
                    setTimeout(() => {
                        if (!sessionReady) {
                            setError('Invalid or expired reset link. Please request a new one.');
                        }
                        subscription.unsubscribe();
                    }, 5000);
                }
            } catch (err) {
                console.error('Check session error:', err);
                setError('Something went wrong. Please try again.');
            } finally {
                setCheckingSession(false);
            }
        };

        checkSession();
    }, []);

    const validatePassword = () => {
        if (password.length < 6) {
            setError('Password must be at least 6 characters');
            return false;
        }
        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return false;
        }
        return true;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);

        if (!validatePassword()) {
            return;
        }

        setLoading(true);

        try {
            const { error } = await updatePassword(password);
            
            if (error) {
                setError(error.message);
            } else {
                setSuccess(true);
                // Redirect to scripts after 3 seconds
                setTimeout(() => {
                    navigate('/scripts');
                }, 3000);
            }
        } catch (err) {
            setError(err.message || 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    // Loading state while checking session
    if (checkingSession) {
        return (
            <div className="reset-password-page">
                <div className="reset-password-card">
                    <div className="reset-loading">
                        <Loader size={32} className="spin" />
                        <p>Verifying reset link...</p>
                    </div>
                </div>
            </div>
        );
    }

    // Error state - invalid/expired link
    if (error && !sessionReady) {
        return (
            <div className="reset-password-page">
                <div className="reset-password-card">
                    <div className="reset-header">
                        <div className="reset-logo error">
                            <AlertCircle size={32} />
                        </div>
                        <h1>Link Expired</h1>
                        <p>{error}</p>
                    </div>
                    <button 
                        className="reset-submit"
                        onClick={() => navigate('/scripts')}
                    >
                        Back to Home
                    </button>
                </div>
            </div>
        );
    }

    // Success state
    if (success) {
        return (
            <div className="reset-password-page">
                <div className="reset-password-card">
                    <div className="reset-header">
                        <div className="reset-logo success">
                            <CheckCircle size={32} />
                        </div>
                        <h1>Password Updated!</h1>
                        <p>Your password has been successfully changed. Redirecting you to your scripts...</p>
                    </div>
                    <div className="reset-loading">
                        <Loader size={24} className="spin" />
                    </div>
                </div>
            </div>
        );
    }

    // Main form
    return (
        <div className="reset-password-page">
            <div className="reset-password-card">
                {/* Brand */}
                <div className="reset-brand">
                    <div className="brand-icon"><Film size={24} /></div>
                    <span className="brand-text">Slate<span className="accent">One</span></span>
                </div>

                {/* Header */}
                <div className="reset-header">
                    <div className="reset-logo">
                        <KeyRound size={32} />
                    </div>
                    <h1>Set New Password</h1>
                    <p>Enter your new password below</p>
                </div>

                {/* Error Message */}
                {error && (
                    <div className="reset-message error">
                        <AlertCircle size={18} />
                        <span>{error}</span>
                    </div>
                )}

                {/* Form */}
                <form onSubmit={handleSubmit} className="reset-form">
                    <div className="form-group">
                        <label htmlFor="new-password">
                            <Lock size={18} />
                            New Password
                        </label>
                        <div className="password-input">
                            <input
                                id="new-password"
                                type={showPassword ? 'text' : 'password'}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                                minLength={6}
                                autoComplete="new-password"
                                autoFocus
                            />
                            <button
                                type="button"
                                className="toggle-password"
                                onClick={() => setShowPassword(!showPassword)}
                            >
                                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                    </div>

                    <div className="form-group">
                        <label htmlFor="confirm-password">
                            <Lock size={18} />
                            Confirm Password
                        </label>
                        <div className="password-input">
                            <input
                                id="confirm-password"
                                type={showConfirmPassword ? 'text' : 'password'}
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                                minLength={6}
                                autoComplete="new-password"
                            />
                            <button
                                type="button"
                                className="toggle-password"
                                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                            >
                                {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                    </div>

                    <div className="password-requirements">
                        <p>Password must be at least 6 characters</p>
                    </div>

                    <button 
                        type="submit" 
                        className="reset-submit"
                        disabled={loading}
                    >
                        {loading ? (
                            <>
                                <Loader size={18} className="spin" />
                                Updating...
                            </>
                        ) : (
                            'Update Password'
                        )}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default ResetPasswordPage;
