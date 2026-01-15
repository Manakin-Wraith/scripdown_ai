/**
 * AuthCallbackPage - Handles auth callbacks (email verification, password reset, etc.)
 * 
 * This page is the redirect target after a user clicks email links.
 * Supabase automatically handles the token exchange when the page loads.
 * 
 * Supported callback types (via ?type= query param):
 * - signup: Email verification after signup → user is authenticated → redirects to /scripts
 * - recovery: Password reset → redirects to /reset-password
 * - default: Direct login (magic link, etc.) → redirects to /scripts
 */

import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { Loader, CheckCircle, XCircle, Film } from 'lucide-react';
import './AuthCallbackPage.css';

const AuthCallbackPage = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [status, setStatus] = useState('verifying'); // 'verifying' | 'success' | 'error'
    const [error, setError] = useState(null);
    const [callbackType, setCallbackType] = useState(null);

    useEffect(() => {
        const handleCallback = async () => {
            try {
                // Get callback type from URL
                const type = searchParams.get('type') || 'default';
                setCallbackType(type);

                // Check for error in URL params (Supabase puts errors here)
                const errorParam = searchParams.get('error');
                const errorDescription = searchParams.get('error_description');
                
                if (errorParam) {
                    setStatus('error');
                    setError(errorDescription || errorParam);
                    return;
                }

                // Get the current session - Supabase auto-handles the token from URL hash
                const { data: { session }, error: sessionError } = await supabase.auth.getSession();
                
                if (sessionError) {
                    setStatus('error');
                    setError(sessionError.message);
                    return;
                }

                if (session) {
                    // Session established successfully
                    setStatus('success');
                    
                    // Redirect based on callback type
                    setTimeout(() => {
                        switch (type) {
                            case 'signup':
                                // Email verified - user is now authenticated, go to scripts
                                navigate('/scripts', { replace: true });
                                break;
                            case 'recovery':
                                // Password reset - redirect to reset password page
                                navigate('/reset-password', { replace: true });
                                break;
                            default:
                                // Default - direct login, go to scripts
                                navigate('/scripts', { replace: true });
                                break;
                        }
                    }, 2000);
                } else {
                    // No session yet, might need to wait for auth state change
                    // Listen for auth state change
                    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
                        if (event === 'SIGNED_IN' && session) {
                            setStatus('success');
                            setTimeout(() => {
                                switch (type) {
                                    case 'signup':
                                        navigate('/scripts', { replace: true });
                                        break;
                                    case 'recovery':
                                        navigate('/reset-password', { replace: true });
                                        break;
                                    default:
                                        navigate('/scripts', { replace: true });
                                        break;
                                }
                                subscription.unsubscribe();
                            }, 2000);
                        }
                    });

                    // Timeout fallback
                    setTimeout(() => {
                        if (status === 'verifying') {
                            setStatus('error');
                            setError('Verification timed out. Please try logging in.');
                        }
                    }, 10000);
                }
            } catch (err) {
                setStatus('error');
                setError(err.message || 'An unexpected error occurred');
            }
        };

        handleCallback();
    }, [navigate, searchParams, status]);

    return (
        <div className="auth-callback-page">
            <div className="callback-card">
                <div className="brand-logo">
                    <div className="logo-icon"><Film size={32} /></div>
                    <span className="logo-text">Slate<span className="accent">One</span></span>
                </div>

                {status === 'verifying' && (
                    <>
                        <div className="status-icon verifying">
                            <Loader size={48} className="spin" />
                        </div>
                        <h2>Verifying your email...</h2>
                        <p>Please wait while we confirm your account.</p>
                    </>
                )}

                {status === 'success' && (
                    <>
                        <div className="status-icon success">
                            <CheckCircle size={48} />
                        </div>
                        {callbackType === 'signup' && (
                            <>
                                <h2>Email Verified!</h2>
                                <p>Your account is now active. Redirecting you to your scripts...</p>
                            </>
                        )}
                        {callbackType === 'recovery' && (
                            <>
                                <h2>Verification Complete!</h2>
                                <p>Redirecting you to reset your password...</p>
                            </>
                        )}
                        {callbackType !== 'signup' && callbackType !== 'recovery' && (
                            <>
                                <h2>Email Verified!</h2>
                                <p>Your account is now active. Redirecting you to your scripts...</p>
                            </>
                        )}
                    </>
                )}

                {status === 'error' && (
                    <>
                        <div className="status-icon error">
                            <XCircle size={48} />
                        </div>
                        <h2>Verification Failed</h2>
                        <p className="error-message">{error}</p>
                        <div className="callback-actions">
                            <button 
                                className="btn-primary"
                                onClick={() => navigate('/login', { replace: true })}
                            >
                                Go to Login
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default AuthCallbackPage;
