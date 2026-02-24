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
    ArrowRight,
    CreditCard,
    Sparkles,
    RefreshCw
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { resetPassword, resendVerificationEmail } from '../lib/supabase';
import SignupSuccess from '../components/auth/SignupSuccess';
import './LoginPage.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const LoginPage = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { login, signup, isAuthenticated, loading: authLoading, user, profile } = useAuth();
    
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
    const [resendingVerification, setResendingVerification] = useState(false);
    const [showEmailNotConfirmed, setShowEmailNotConfirmed] = useState(false);

    // Get redirect URL from query params or state
    const getRedirectUrl = () => {
        const params = new URLSearchParams(location.search);
        const redirectParam = params.get('redirect');
        if (redirectParam) return redirectParam;
        return location.state?.from?.pathname || '/scripts';
    };

    // Redirect if already authenticated (unless showing signup completion)
    useEffect(() => {
        const params = new URLSearchParams(location.search);
        const isVerified = params.get('verified') === 'true';
        const isSignupMode = params.get('mode') === 'signup';
        
        // If user just verified email, show signup completion screen
        if (isAuthenticated && !authLoading && isVerified && isSignupMode) {
            setSignupComplete(true);
            return;
        }
        
        // Otherwise redirect authenticated users
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
                    // Check if it's an email not confirmed error
                    const isEmailNotConfirmed = result.error?.toLowerCase().includes('email not confirmed') ||
                                                result.error?.toLowerCase().includes('email_not_confirmed');
                    setShowEmailNotConfirmed(isEmailNotConfirmed);
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
        setShowEmailNotConfirmed(false);
    };

    const handleResendVerification = async () => {
        if (!email) {
            setError('Please enter your email address first');
            return;
        }
        
        setResendingVerification(true);
        setError(null);
        
        try {
            const { error } = await resendVerificationEmail(email);
            if (error) {
                setError(error.message);
            } else {
                setSuccess('Verification email sent! Please check your inbox.');
                setShowEmailNotConfirmed(false);
            }
        } catch (err) {
            setError('Failed to resend verification email');
        } finally {
            setResendingVerification(false);
        }
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
                <div className={`login-form-container ${mode === 'signup' && !inviteContext ? 'signup-split-layout' : ''}`}>
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
                            email={user?.email || email}
                            fullName={profile?.full_name || fullName}
                            inviteContext={inviteContext}
                            verified={new URLSearchParams(location.search).get('verified') === 'true'}
                            onContinue={() => navigate('/scripts', { replace: true })}
                        />
                    ) : (
                    <>
                    {/* Beta Access Panel - Only for Signup */}
                    {/* COMMENTED OUT - Can be restored later
                    {mode === 'signup' && !inviteContext && (
                        <div className="signup-beta-panel">
                            <div className="beta-panel-content">
                                <div className="beta-badge-large">
                                    <Sparkles size={24} />
                                    <span>Beta Access</span>
                                </div>
                                <h3>Get 1 Year of Full Access</h3>
                                <div className="beta-price">
                                    <span className="price-amount">R249</span>
                                    <span className="price-period">one-time payment</span>
                                </div>
                                <ul className="beta-features-list">
                                    <li>
                                        <CheckCircle size={18} />
                                        <span>AI-powered script breakdown</span>
                                    </li>
                                    <li>
                                        <CheckCircle size={18} />
                                        <span>Unlimited scene analysis</span>
                                    </li>
                                    <li>
                                        <CheckCircle size={18} />
                                        <span>Team collaboration tools</span>
                                    </li>
                                    <li>
                                        <CheckCircle size={18} />
                                        <span>Export reports & stripboards</span>
                                    </li>
                                </ul>
                                <button 
                                    type="button"
                                    className="beta-panel-cta"
                                    onClick={() => {
                                        const paymentEmail = email || '';
                                        if (paymentEmail) {
                                            localStorage.setItem('beta_payment_email', paymentEmail);
                                        }
                                        
                                        const width = 500;
                                        const height = 700;
                                        const left = window.screenX + (window.outerWidth - width) / 2;
                                        const top = window.screenY + (window.outerHeight - height) / 2;
                                        
                                        window.open(
                                            'https://pay.yoco.com/celebration-house-entertainment?amount=249.00&reference=BetaAccess',
                                            'yoco-payment',
                                            `width=${width},height=${height},left=${left},top=${top}`
                                        );
                                    }}
                                >
                                    <CreditCard size={20} />
                                    Pay & Get Access
                                </button>
                                <p className="beta-note">Enter your email above first</p>
                            </div>
                        </div>
                    )}
                    */}

                    {/* Form Section */}
                    <div className="signup-form-section">
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
                            <div className="error-content">
                                <span>{error}</span>
                                {showEmailNotConfirmed && (
                                    <button 
                                        type="button"
                                        className="resend-verification-btn"
                                        onClick={handleResendVerification}
                                        disabled={resendingVerification}
                                    >
                                        {resendingVerification ? (
                                            <><RefreshCw size={14} className="spin" /> Sending...</>
                                        ) : (
                                            <><RefreshCw size={14} /> Resend verification email</>
                                        )}
                                    </button>
                                )}
                            </div>
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
                                <button type="button" className="link-btn" onClick={() => {
                                    navigate('/login?mode=signup&plan=free_trial&source=landing_hero', { replace: true });
                                    switchMode('signup');
                                }}>
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
                    </div>
                    </>
                    )}
                </div>
            </div>
        </div>
    );
};

export default LoginPage;
