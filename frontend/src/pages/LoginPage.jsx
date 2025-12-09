/**
 * LoginPage - Full-page Login/Signup Component
 * 
 * Standalone page for authentication with modern, tablet-first design.
 * Redirects to /scripts after successful login.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { 
    Mail, 
    Lock, 
    User, 
    Eye, 
    EyeOff, 
    Loader,
    Film,
    AlertCircle,
    CheckCircle,
    ArrowRight
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { resetPassword } from '../lib/supabase';
import SignupSuccess from '../components/auth/SignupSuccess';
import './LoginPage.css';

const API_BASE_URL = 'http://localhost:5000';

const LoginPage = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { login, signup, isAuthenticated, loading: authLoading } = useAuth();
    
    // Check for mode in query params (for invite flow)
    const getInitialMode = () => {
        const params = new URLSearchParams(location.search);
        const modeParam = params.get('mode');
        if (modeParam === 'signup') return 'signup';
        return 'login';
    };
    
    const [mode, setMode] = useState(getInitialMode); // 'login' | 'signup' | 'forgot'
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [fullName, setFullName] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [signupComplete, setSignupComplete] = useState(false);
    const [inviteContext, setInviteContext] = useState(null);

    // Get redirect URL from query params or state
    const getRedirectUrl = () => {
        const params = new URLSearchParams(location.search);
        const redirectParam = params.get('redirect');
        if (redirectParam) return redirectParam;
        return location.state?.from?.pathname || '/scripts';
    };

    // Redirect if already authenticated
    useEffect(() => {
        if (isAuthenticated && !authLoading) {
            navigate(getRedirectUrl(), { replace: true });
        }
    }, [isAuthenticated, authLoading, navigate, location]);

    // Fetch invite context if coming from an invite
    useEffect(() => {
        const fetchInviteContext = async () => {
            const redirectUrl = getRedirectUrl();
            const inviteMatch = redirectUrl.match(/\/invite\/([^/?]+)/);
            
            if (inviteMatch) {
                const token = inviteMatch[1];
                try {
                    const response = await fetch(`${API_BASE_URL}/api/invites/token/${token}`);
                    if (response.ok) {
                        const data = await response.json();
                        setInviteContext({
                            scriptTitle: data.invite?.script_title,
                            department: data.invite?.department,
                            role: data.invite?.role
                        });
                    }
                } catch (err) {
                    console.error('Failed to fetch invite context:', err);
                }
            }
        };
        
        fetchInviteContext();
    }, [location.search]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setSuccess(null);
        setLoading(true);

        try {
            if (mode === 'login') {
                const result = await login(email, password);
                if (result.success) {
                    navigate(getRedirectUrl(), { replace: true });
                } else {
                    setError(result.error);
                }
            } else if (mode === 'signup') {
                if (!fullName.trim()) {
                    setError('Please enter your full name');
                    setLoading(false);
                    return;
                }
                const result = await signup(email, password, fullName);
                if (result.success) {
                    setSignupComplete(true);
                } else {
                    setError(result.error);
                }
            } else if (mode === 'forgot') {
                const { error } = await resetPassword(email);
                if (error) {
                    setError(error.message);
                } else {
                    setSuccess('Password reset email sent! Check your inbox.');
                }
            }
        } catch (err) {
            setError(err.message || 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    const switchMode = (newMode) => {
        setMode(newMode);
        setError(null);
        setSuccess(null);
    };

    // Show loading while checking auth
    if (authLoading) {
        return (
            <div className="login-page">
                <div className="login-loading">
                    <Loader size={32} className="spin" />
                    <p>Loading...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="login-page">
            {/* Left Panel - Branding */}
            <div className="login-branding">
                <div className="branding-content">
                    <Link to="/" className="brand-logo">
                        <div className="logo-icon"><Film size={32} /></div>
                        <span className="logo-text">Slate<span className="accent">One</span></span>
                    </Link>
                    <h1>Script Breakdown<br />Made Simple</h1>
                    <p>AI-powered scene analysis for film and television production teams.</p>
                    <div className="branding-features">
                        <div className="feature">
                            <CheckCircle size={20} />
                            <span>Instant scene detection</span>
                        </div>
                        <div className="feature">
                            <CheckCircle size={20} />
                            <span>AI character & prop extraction</span>
                        </div>
                        <div className="feature">
                            <CheckCircle size={20} />
                            <span>Department collaboration</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Right Panel - Form */}
            <div className="login-form-panel">
                <div className="login-form-container">
                    {/* Mobile Logo */}
                    <div className="mobile-logo">
                        <Link to="/" className="brand-logo">
                            <div className="logo-icon"><Film size={24} /></div>
                            <span className="logo-text">Slate<span className="accent">One</span></span>
                        </Link>
                    </div>

                    {/* Signup Success State */}
                    {signupComplete ? (
                        <SignupSuccess 
                            email={email}
                            fullName={fullName}
                            inviteContext={inviteContext}
                        />
                    ) : (
                    <>
                    {/* Header */}
                    <div className="login-header">
                        <h2>
                            {mode === 'login' && 'Welcome back'}
                            {mode === 'signup' && 'Create your account'}
                            {mode === 'forgot' && 'Reset password'}
                        </h2>
                        <p>
                            {mode === 'login' && 'Sign in to access your scripts and breakdowns'}
                            {mode === 'signup' && (inviteContext 
                                ? `Join "${inviteContext.scriptTitle}" as ${inviteContext.department}`
                                : 'Join your production team on SlateOne'
                            )}
                            {mode === 'forgot' && 'Enter your email to receive a reset link'}
                        </p>
                    </div>

                    {/* Messages */}
                    {error && (
                        <div className="login-message error">
                            <AlertCircle size={18} />
                            <span>{error}</span>
                        </div>
                    )}
                    {success && (
                        <div className="login-message success">
                            <CheckCircle size={18} />
                            <span>{success}</span>
                        </div>
                    )}

                    {/* Form */}
                    <form onSubmit={handleSubmit} className="login-form">
                        {mode === 'signup' && (
                            <div className="form-group">
                                <label htmlFor="fullName">
                                    <User size={18} />
                                    Full Name
                                </label>
                                <input
                                    id="fullName"
                                    type="text"
                                    value={fullName}
                                    onChange={(e) => setFullName(e.target.value)}
                                    placeholder="John Smith"
                                    required
                                    autoComplete="name"
                                />
                            </div>
                        )}

                        <div className="form-group">
                            <label htmlFor="email">
                                <Mail size={18} />
                                Email
                            </label>
                            <input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="you@production.com"
                                required
                                autoComplete="email"
                                autoFocus
                            />
                        </div>

                        {mode !== 'forgot' && (
                            <div className="form-group">
                                <label htmlFor="password">
                                    <Lock size={18} />
                                    Password
                                </label>
                                <div className="password-input">
                                    <input
                                        id="password"
                                        type={showPassword ? 'text' : 'password'}
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        placeholder="••••••••"
                                        required
                                        minLength={6}
                                        autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
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
                        )}

                        {mode === 'login' && (
                            <div className="forgot-password">
                                <button 
                                    type="button" 
                                    className="link-btn"
                                    onClick={() => switchMode('forgot')}
                                >
                                    Forgot password?
                                </button>
                            </div>
                        )}

                        <button 
                            type="submit" 
                            className="login-submit"
                            disabled={loading}
                        >
                            {loading ? (
                                <>
                                    <Loader size={18} className="spin" />
                                    {mode === 'login' && 'Signing in...'}
                                    {mode === 'signup' && 'Creating account...'}
                                    {mode === 'forgot' && 'Sending...'}
                                </>
                            ) : (
                                <>
                                    {mode === 'login' && 'Sign In'}
                                    {mode === 'signup' && 'Create Account'}
                                    {mode === 'forgot' && 'Send Reset Link'}
                                    <ArrowRight size={18} />
                                </>
                            )}
                        </button>
                    </form>

                    {/* Mode Switch */}
                    <div className="login-switch">
                        {mode === 'login' && (
                            <>
                                <span>Don't have an account?</span>
                                <button type="button" className="link-btn" onClick={() => switchMode('signup')}>
                                    Sign up
                                </button>
                            </>
                        )}
                        {mode === 'signup' && (
                            <>
                                <span>Already have an account?</span>
                                <button type="button" className="link-btn" onClick={() => switchMode('login')}>
                                    Sign in
                                </button>
                            </>
                        )}
                        {mode === 'forgot' && (
                            <>
                                <span>Remember your password?</span>
                                <button type="button" className="link-btn" onClick={() => switchMode('login')}>
                                    Back to sign in
                                </button>
                            </>
                        )}
                    </div>
                    </>
                    )}
                </div>
            </div>
        </div>
    );
};

export default LoginPage;
