/**
 * ProductionInviteAccept - Accept production team invitations
 *
 * Public landing page for production-invite links.
 * Shows invite details and lets the user accept after authentication.
 * Auto-accept-on-login is handled server-side (Task 9); this page never
 * auto-redirects or stashes anything in sessionStorage.
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
    Film,
    Users,
    Check,
    X,
    LogIn
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { Spinner } from '../components/ui';
import { getProductionInvite, acceptProductionInvite } from '../services/apiService';
import './InvitePage.css';

const ProductionInviteAccept = () => {
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
                const data = await getProductionInvite(token);
                setInvite(data);
            } catch (err) {
                console.error('Error fetching production invite:', err);
                setError(err.response?.data?.error || 'Invite not found');
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
        setAccepting(true);

        try {
            const res = await acceptProductionInvite(token);
            setAccepted(true);
            toast.success(
                'Welcome',
                res.already_member ? 'You are already on this production.' : 'Successfully joined the production!'
            );

            setTimeout(() => {
                navigate(`/productions/${res.production_id}`);
            }, 2000);
        } catch (err) {
            console.error('Error accepting production invite:', err);
            setError(err.response?.data?.error || 'Could not accept invite');
        } finally {
            setAccepting(false);
        }
    };

    // Loading state
    if (loading || authLoading) {
        return (
            <div className="invite-page">
                <div className="invite-card loading">
                    <Spinner size={32} />
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
                    <Link to="/productions" className="btn-primary">
                        Go to My Productions
                    </Link>
                </div>
            </div>
        );
    }

    // Invalid (expired / revoked / already handled)
    if (invite?.status !== 'pending' || invite?.expired) {
        return (
            <div className="invite-page">
                <div className="invite-card error">
                    <div className="error-icon">
                        <X size={32} />
                    </div>
                    <h2>Invite Not Valid</h2>
                    <p>
                        This invitation is {invite?.expired ? 'expired' : (invite?.status || 'no longer valid')}.
                    </p>
                    <Link to="/productions" className="btn-primary">
                        Go to My Productions
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
                    <h2>Welcome to the Production!</h2>
                    <p>
                        You've joined <strong>{invite?.production_title}</strong> as <strong>{invite?.role}</strong>
                    </p>
                    <p className="redirect-note">Redirecting to production...</p>
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
                        You've been invited to collaborate on a production
                    </p>

                    <div className="script-info">
                        <div className="info-row">
                            <span className="label">Production</span>
                            <span className="value">{invite?.production_title}</span>
                        </div>
                        <div className="info-row">
                            <span className="label">Invited by</span>
                            <span className="value">{invite?.inviter_name}</span>
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
                                        <Spinner size={18} />
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
                                Create an account or sign in to join the production
                            </p>
                            <div className="auth-buttons">
                                <button
                                    className="btn-accept btn-signup"
                                    onClick={() => navigate(`/login?redirect=/production-invites/${token}&mode=signup`)}
                                >
                                    <Users size={18} />
                                    Create Account
                                </button>
                                <button
                                    className="btn-secondary"
                                    onClick={() => navigate(`/login?redirect=/production-invites/${token}`)}
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

export default ProductionInviteAccept;
