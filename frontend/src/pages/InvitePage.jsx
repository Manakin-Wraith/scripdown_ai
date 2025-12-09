/**
 * InvitePage - Accept team invitations
 * 
 * Landing page for invite links.
 * Shows invite details and allows user to accept after authentication.
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
    Film, 
    Users, 
    Check, 
    X, 
    Loader, 
    AlertCircle,
    LogIn,
    ArrowRight
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import './InvitePage.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const InvitePage = () => {
    const { token } = useParams();
    const navigate = useNavigate();
    const { isAuthenticated, user, loading: authLoading } = useAuth();
    const toast = useToast();
    
    const [invite, setInvite] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [accepting, setAccepting] = useState(false);
    const [accepted, setAccepted] = useState(false);

    // Fetch invite details
    useEffect(() => {
        const fetchInvite = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/invites/token/${token}`);
                const data = await response.json();
                
                if (!response.ok) {
                    setError(data.error || 'Invalid invite');
                    return;
                }
                
                setInvite(data.invite);
            } catch (err) {
                console.error('Error fetching invite:', err);
                setError('Failed to load invite');
            } finally {
                setLoading(false);
            }
        };
        
        if (token) {
            fetchInvite();
        }
    }, [token]);

    // Accept invite
    const handleAccept = async () => {
        if (!isAuthenticated) {
            // Redirect to login with return URL
            navigate(`/login?redirect=/invite/${token}`);
            return;
        }
        
        setAccepting(true);
        
        try {
            const { supabase } = await import('../lib/supabase');
            const { data: { session } } = await supabase.auth.getSession();
            
            const response = await fetch(`${API_BASE_URL}/api/invites/token/${token}/accept`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session?.access_token || ''}`
                }
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to accept invite');
            }
            
            setAccepted(true);
            toast.success('Welcome', 'Successfully joined the team!');
            
            // Redirect to script after a moment
            setTimeout(() => {
                navigate(`/scenes/${data.script_id}`);
            }, 2000);
            
        } catch (err) {
            console.error('Error accepting invite:', err);
            toast.error('Error', err.message);
        } finally {
            setAccepting(false);
        }
    };

    // Loading state
    if (loading || authLoading) {
        return (
            <div className="invite-page">
                <div className="invite-card loading">
                    <Loader size={32} className="spin" />
                    <p>Loading invite...</p>
                </div>
            </div>
        );
    }

    // Error state
    if (error) {
        return (
            <div className="invite-page">
                <div className="invite-card error">
                    <div className="error-icon">
                        <X size={32} />
                    </div>
                    <h2>Invite Not Valid</h2>
                    <p>{error}</p>
                    <Link to="/scripts" className="btn-primary">
                        Go to My Scripts
                    </Link>
                </div>
            </div>
        );
    }

    // Success state
    if (accepted) {
        return (
            <div className="invite-page">
                <div className="invite-card success">
                    <div className="success-icon">
                        <Check size={32} />
                    </div>
                    <h2>Welcome to the Team!</h2>
                    <p>
                        You've joined <strong>{invite?.script_title}</strong> as <strong>{invite?.department}</strong>
                    </p>
                    <p className="redirect-note">Redirecting to script...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="invite-page">
            <div className="invite-card">
                {/* Logo */}
                <div className="invite-logo">
                    <Film size={32} />
                    <span>SlateOne</span>
                </div>

                {/* Invite Details */}
                <div className="invite-details">
                    <h1>You're Invited!</h1>
                    <p className="invite-subtitle">
                        You've been invited to collaborate on a script
                    </p>

                    <div className="script-info">
                        <div className="info-row">
                            <span className="label">Script</span>
                            <span className="value">{invite?.script_title}</span>
                        </div>
                        <div className="info-row">
                            <span className="label">Department</span>
                            <span className="value department-badge">
                                <Users size={14} />
                                {invite?.department}
                            </span>
                        </div>
                        <div className="info-row">
                            <span className="label">Role</span>
                            <span className="value role-badge">{invite?.role}</span>
                        </div>
                    </div>
                </div>

                {/* Actions */}
                <div className="invite-actions">
                    {isAuthenticated ? (
                        <>
                            <p className="auth-status">
                                Signed in as <strong>{user?.email}</strong>
                            </p>
                            <button 
                                className="btn-accept"
                                onClick={handleAccept}
                                disabled={accepting}
                            >
                                {accepting ? (
                                    <>
                                        <Loader size={18} className="spin" />
                                        Joining...
                                    </>
                                ) : (
                                    <>
                                        <Check size={18} />
                                        Accept Invite
                                    </>
                                )}
                            </button>
                        </>
                    ) : (
                        <>
                            <p className="auth-prompt">
                                Create an account or sign in to join the team
                            </p>
                            <div className="auth-buttons">
                                <button 
                                    className="btn-accept btn-signup"
                                    onClick={() => navigate(`/login?redirect=/invite/${token}&mode=signup`)}
                                >
                                    <Users size={18} />
                                    Create Account
                                </button>
                                <button 
                                    className="btn-secondary"
                                    onClick={() => navigate(`/login?redirect=/invite/${token}`)}
                                >
                                    <LogIn size={18} />
                                    Sign In
                                </button>
                            </div>
                            <p className="auth-hint">
                                New to SlateOne? Create a free account to get started.
                            </p>
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="invite-footer">
                    <p>
                        This invite was sent to <strong>{invite?.email}</strong>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default InvitePage;
