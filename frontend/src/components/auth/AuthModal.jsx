/**
 * AuthModal - Login/Signup Modal Component
 * 
 * Tablet-first design with clean, modern UI
 */

import React, { useState } from 'react';
import { 
    X, 
    Mail, 
    Lock, 
    User, 
    Eye, 
    EyeOff, 
    Loader,
    Clapperboard,
    AlertCircle
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import ForgotPasswordModal from './ForgotPasswordModal';
import './AuthModal.css';

const AuthModal = ({ isOpen, onClose, initialMode = 'login' }) => {
    const [mode, setMode] = useState(initialMode); // 'login' | 'signup'
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [fullName, setFullName] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [showForgotPassword, setShowForgotPassword] = useState(false);

    const { login, signup } = useAuth();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setSuccess(null);
        setLoading(true);

        try {
            if (mode === 'login') {
                const result = await login(email, password);
                if (result.success) {
                    onClose();
                } else {
                    setError(result.error);
                }
            } else {
                if (!fullName.trim()) {
                    setError('Please enter your full name');
                    setLoading(false);
                    return;
                }
                const result = await signup(email, password, fullName);
                if (result.success) {
                    setSuccess('Account created! Please check your email to verify your account.');
                    // Don't close - show success message
                } else {
                    setError(result.error);
                }
            }
        } catch (err) {
            setError(err.message || 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    const switchMode = () => {
        setMode(mode === 'login' ? 'signup' : 'login');
        setError(null);
        setSuccess(null);
    };

    if (!isOpen) return null;

    return (
        <>
            {/* Backdrop */}
            <div className="auth-backdrop" onClick={onClose} />
            
            {/* Modal */}
            <div className="auth-modal">
                {/* Close button */}
                <button className="auth-close" onClick={onClose}>
                    <X size={20} />
                </button>

                {/* Header */}
                <div className="auth-header">
                    <div className="auth-logo">
                        <Clapperboard size={32} />
                    </div>
                    <h2>{mode === 'login' ? 'Welcome Back' : 'Create Account'}</h2>
                    <p>
                        {mode === 'login' 
                            ? 'Sign in to access your scripts and breakdowns'
                            : 'Join your production team on ScripDown'
                        }
                    </p>
                </div>

                {/* Error/Success Messages */}
                {error && (
                    <div className="auth-message error">
                        <AlertCircle size={18} />
                        <span>{error}</span>
                    </div>
                )}
                {success && (
                    <div className="auth-message success">
                        <AlertCircle size={18} />
                        <span>{success}</span>
                    </div>
                )}

                {/* Form */}
                <form onSubmit={handleSubmit} className="auth-form">
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
                        />
                    </div>

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

                    {mode === 'login' && (
                        <div className="forgot-password">
                            <button 
                                type="button" 
                                className="link-btn"
                                onClick={() => setShowForgotPassword(true)}
                            >
                                Forgot password?
                            </button>
                        </div>
                    )}

                    <button 
                        type="submit" 
                        className="auth-submit"
                        disabled={loading}
                    >
                        {loading ? (
                            <>
                                <Loader size={18} className="spin" />
                                {mode === 'login' ? 'Signing in...' : 'Creating account...'}
                            </>
                        ) : (
                            mode === 'login' ? 'Sign In' : 'Create Account'
                        )}
                    </button>
                </form>

                {/* Switch mode */}
                <div className="auth-switch">
                    <span>
                        {mode === 'login' 
                            ? "Don't have an account?" 
                            : 'Already have an account?'
                        }
                    </span>
                    <button type="button" className="link-btn" onClick={switchMode}>
                        {mode === 'login' ? 'Sign up' : 'Sign in'}
                    </button>
                </div>
            </div>

            {/* Forgot Password Modal */}
            <ForgotPasswordModal 
                isOpen={showForgotPassword}
                onClose={() => setShowForgotPassword(false)}
                onBackToLogin={() => setShowForgotPassword(false)}
            />
        </>
    );
};

export default AuthModal;
