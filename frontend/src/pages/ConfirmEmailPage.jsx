/**
 * ConfirmEmailPage - Email Confirmation Handler
 * 
 * Handles email confirmation via app.slateone.studio domain
 * to avoid Supabase subdomain mismatch in emails
 */

import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { CheckCircle, XCircle, Loader } from 'lucide-react';
import './ConfirmEmailPage.css';

const ConfirmEmailPage = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [status, setStatus] = useState('loading'); // 'loading' | 'success' | 'error'
    const [message, setMessage] = useState('');
    const [debugInfo, setDebugInfo] = useState('');

    // Debug: Log component mount
    console.log('ConfirmEmailPage mounted');

    useEffect(() => {
        console.log('ConfirmEmailPage useEffect running');
        const confirmEmail = async () => {
            // Get all URL parameters
            const token_hash = searchParams.get('token_hash');
            const type = searchParams.get('type');

            console.log('Confirmation params:', { token_hash, type, allParams: Object.fromEntries(searchParams) });

            if (!token_hash) {
                setStatus('error');
                setMessage('Invalid confirmation link - missing token');
                setDebugInfo('No token_hash in URL');
                return;
            }

            setDebugInfo(`Verifying token: ${token_hash.substring(0, 20)}...`);

            try {
                // Verify OTP with token_hash and type
                // Supabase sends type='signup' for email confirmations
                const { data, error } = await supabase.auth.verifyOtp({
                    token_hash,
                    type: type || 'signup'  // Default to 'signup' for email confirmation
                });

                console.log('Verification result:', { data, error });
                setDebugInfo(`Verification complete. Session: ${!!data?.session}, User: ${!!data?.user}, Error: ${!!error}`);

                if (error) {
                    setStatus('error');
                    setMessage(error.message || 'Failed to confirm email');
                    setDebugInfo(`Error: ${error.message} (Code: ${error.code || 'N/A'})`);
                    console.error('Verification error:', error);
                    return;
                }

                if (data?.session || data?.user) {
                    setStatus('success');
                    setMessage('Email confirmed successfully! Redirecting...');
                    setDebugInfo('Session created, redirecting to /scripts');

                    // User is confirmed, redirect to scripts
                    setTimeout(() => {
                        console.log('Redirecting to /scripts');
                        window.location.href = '/scripts';
                    }, 1500);
                } else {
                    setStatus('error');
                    setMessage('Confirmation succeeded but no session created.');
                    setDebugInfo('No session or user in response. Please log in manually.');
                    
                    setTimeout(() => {
                        navigate('/login?confirmed=true');
                    }, 2000);
                }

            } catch (err) {
                setStatus('error');
                setMessage('An unexpected error occurred');
                setDebugInfo(`Exception: ${err.message}`);
                console.error('Confirmation error:', err);
            }
        };

        confirmEmail();
    }, [searchParams, navigate]);

    return (
        <div className="confirm-email-page">
            <div className="confirm-email-container">
                {status === 'loading' && (
                    <>
                        <Loader size={48} className="spin" />
                        <h2>Confirming your email...</h2>
                        <p>Please wait while we verify your account</p>
                        {debugInfo && (
                            <p style={{ fontSize: '12px', color: '#9ca3af', marginTop: '16px' }}>
                                {debugInfo}
                            </p>
                        )}
                    </>
                )}

                {status === 'success' && (
                    <>
                        <CheckCircle size={48} className="success-icon" />
                        <h2>Email Confirmed!</h2>
                        <p>{message}</p>
                        <p className="redirect-message">Redirecting...</p>
                        {debugInfo && (
                            <p style={{ fontSize: '12px', color: '#9ca3af', marginTop: '8px' }}>
                                {debugInfo}
                            </p>
                        )}
                    </>
                )}

                {status === 'error' && (
                    <>
                        <XCircle size={48} className="error-icon" />
                        <h2>Confirmation Failed</h2>
                        <p>{message}</p>
                        {debugInfo && (
                            <p style={{ fontSize: '12px', color: '#ef4444', marginTop: '8px', fontFamily: 'monospace' }}>
                                Debug: {debugInfo}
                            </p>
                        )}
                        <button 
                            className="btn-primary"
                            onClick={() => navigate('/login')}
                        >
                            Go to Login
                        </button>
                    </>
                )}
            </div>
        </div>
    );
};

export default ConfirmEmailPage;
