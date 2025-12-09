/**
 * TeamDrawer - Slide-out panel for team management
 * 
 * Allows script owners to:
 * - View all team members
 * - Remove team members
 * - View pending invites
 * - Revoke pending invites
 */

import React, { useState, useEffect } from 'react';
import { 
    X, 
    Crown, 
    Shield, 
    UserX,
    Clock, 
    Loader,
    Users,
    AlertCircle,
    Mail,
    UserPlus,
    Link as LinkIcon,
    ChevronDown,
    ChevronUp,
    Trash2
} from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import InviteModal from './InviteModal';
import './TeamDrawer.css';

const API_BASE_URL = 'http://localhost:5000';

const TeamDrawer = ({ 
    isOpen, 
    onClose, 
    scriptId,
    scriptTitle,
    currentUserId,
    isOwner
}) => {
    const toast = useToast();
    
    const [owner, setOwner] = useState(null);
    const [members, setMembers] = useState([]);
    const [invites, setInvites] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showInvites, setShowInvites] = useState(false);
    const [inviteModalOpen, setInviteModalOpen] = useState(false);
    const [removeConfirm, setRemoveConfirm] = useState(null);
    const [revokeConfirm, setRevokeConfirm] = useState(null);
    const [actionLoading, setActionLoading] = useState(null);

    // Fetch team data when drawer opens
    useEffect(() => {
        if (!isOpen || !scriptId) return;

        const fetchTeamData = async () => {
            setLoading(true);
            setError(null);

            try {
                const { supabase } = await import('../../lib/supabase');
                const { data: { session } } = await supabase.auth.getSession();
                const headers = {
                    'Authorization': `Bearer ${session?.access_token || ''}`
                };

                // Fetch members
                const membersResponse = await fetch(
                    `${API_BASE_URL}/api/scripts/${scriptId}/members`,
                    { headers }
                );
                
                if (!membersResponse.ok) {
                    throw new Error('Failed to fetch team members');
                }
                
                const membersData = await membersResponse.json();
                setOwner(membersData.owner);
                setMembers(membersData.members || []);

                // Fetch pending invites (only if owner)
                if (isOwner) {
                    const invitesResponse = await fetch(
                        `${API_BASE_URL}/api/scripts/${scriptId}/invites`,
                        { headers }
                    );
                    
                    if (invitesResponse.ok) {
                        const invitesData = await invitesResponse.json();
                        // Filter to only pending invites
                        setInvites((invitesData.invites || []).filter(i => i.status === 'pending'));
                    }
                }

            } catch (err) {
                console.error('Error fetching team data:', err);
                setError('Failed to load team data');
            } finally {
                setLoading(false);
            }
        };

        fetchTeamData();
    }, [isOpen, scriptId, isOwner]);

    const handleRemoveMember = async (memberId, memberName) => {
        setActionLoading(memberId);
        
        try {
            const { supabase } = await import('../../lib/supabase');
            const { data: { session } } = await supabase.auth.getSession();
            
            const response = await fetch(
                `${API_BASE_URL}/api/scripts/${scriptId}/members/${memberId}`,
                {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${session?.access_token || ''}`
                    }
                }
            );
            
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Failed to remove member');
            }
            
            // Update local state
            setMembers(prev => prev.filter(m => m.id !== memberId));
            setRemoveConfirm(null);
            toast.success('Member Removed', `${memberName} has been removed from the team`);
            
        } catch (err) {
            console.error('Error removing member:', err);
            toast.error('Error', err.message);
        } finally {
            setActionLoading(null);
        }
    };

    const handleRevokeInvite = async (inviteId, email) => {
        setActionLoading(inviteId);
        
        try {
            const { supabase } = await import('../../lib/supabase');
            const { data: { session } } = await supabase.auth.getSession();
            
            const response = await fetch(
                `${API_BASE_URL}/api/invites/${inviteId}`,
                {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${session?.access_token || ''}`
                    }
                }
            );
            
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Failed to revoke invite');
            }
            
            // Update local state
            setInvites(prev => prev.filter(i => i.id !== inviteId));
            setRevokeConfirm(null);
            toast.success('Invite Revoked', `Invite to ${email} has been revoked`);
            
        } catch (err) {
            console.error('Error revoking invite:', err);
            toast.error('Error', err.message);
        } finally {
            setActionLoading(null);
        }
    };

    const formatDate = (dateString) => {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric',
            year: 'numeric'
        });
    };

    const getExpiryText = (expiresAt) => {
        if (!expiresAt) return '';
        const expires = new Date(expiresAt);
        const now = new Date();
        const daysLeft = Math.ceil((expires - now) / (1000 * 60 * 60 * 24));
        
        if (daysLeft <= 0) return 'Expired';
        if (daysLeft === 1) return 'Expires tomorrow';
        return `Expires in ${daysLeft} days`;
    };

    const handleInviteSuccess = () => {
        // Refresh invites after new invite created
        setInviteModalOpen(false);
        // Re-fetch data
        if (isOpen && scriptId) {
            const fetchInvites = async () => {
                try {
                    const { supabase } = await import('../../lib/supabase');
                    const { data: { session } } = await supabase.auth.getSession();
                    
                    const response = await fetch(
                        `${API_BASE_URL}/api/scripts/${scriptId}/invites`,
                        {
                            headers: {
                                'Authorization': `Bearer ${session?.access_token || ''}`
                            }
                        }
                    );
                    
                    if (response.ok) {
                        const data = await response.json();
                        setInvites((data.invites || []).filter(i => i.status === 'pending'));
                    }
                } catch (err) {
                    console.error('Error refreshing invites:', err);
                }
            };
            fetchInvites();
        }
    };

    if (!isOpen) return null;

    return (
        <>
            {/* Backdrop */}
            <div className="drawer-backdrop" onClick={onClose} />
            
            {/* Drawer */}
            <div className={`team-drawer ${isOpen ? 'open' : ''}`}>
                {/* Header */}
                <div className="drawer-header">
                    <div className="drawer-title-group">
                        <h3>
                            <Users size={18} />
                            Team Members
                        </h3>
                        <span className="drawer-subtitle">{scriptTitle}</span>
                    </div>
                    <button className="close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="drawer-content">
                    {loading ? (
                        <div className="drawer-loading">
                            <Loader size={24} className="spin" />
                            <span>Loading team...</span>
                        </div>
                    ) : error ? (
                        <div className="drawer-error">
                            <AlertCircle size={20} />
                            <span>{error}</span>
                        </div>
                    ) : (
                        <>
                            {/* Owner Section */}
                            {owner && (
                                <div className="team-section">
                                    <div className="section-header">
                                        <Crown size={14} />
                                        <span>Owner</span>
                                    </div>
                                    <div className="member-card owner">
                                        <div className="member-avatar">
                                            {owner.avatar_url ? (
                                                <img src={owner.avatar_url} alt={owner.name} />
                                            ) : (
                                                <span>{owner.name?.charAt(0)?.toUpperCase() || 'O'}</span>
                                            )}
                                        </div>
                                        <div className="member-info">
                                            <span className="member-name">{owner.name}</span>
                                            <span className="member-email">{owner.email}</span>
                                        </div>
                                        <div className="owner-badge">
                                            <Crown size={12} />
                                            Owner
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Members Section */}
                            <div className="team-section">
                                <div className="section-header">
                                    <Shield size={14} />
                                    <span>Members ({members.length})</span>
                                </div>
                                
                                {members.length === 0 ? (
                                    <div className="no-members">
                                        <Users size={32} />
                                        <p>No team members yet</p>
                                        <span>Invite collaborators to join your team</span>
                                    </div>
                                ) : (
                                    <div className="members-list">
                                        {members.map(member => (
                                            <div key={member.id} className="member-card">
                                                <div className="member-avatar">
                                                    {member.avatar_url ? (
                                                        <img src={member.avatar_url} alt={member.name} />
                                                    ) : (
                                                        <span>{member.name?.charAt(0)?.toUpperCase() || '?'}</span>
                                                    )}
                                                </div>
                                                <div className="member-info">
                                                    <span className="member-name">{member.name}</span>
                                                    <div className="member-meta">
                                                        <span 
                                                            className="dept-tag"
                                                            title={member.department}
                                                        >
                                                            {member.department}
                                                        </span>
                                                        {member.role === 'admin' && (
                                                            <span className="role-tag admin">Admin</span>
                                                        )}
                                                    </div>
                                                    <span className="member-joined">
                                                        <Clock size={10} />
                                                        Joined {formatDate(member.joined_at)}
                                                    </span>
                                                </div>
                                                {isOwner && (
                                                    <button 
                                                        className="remove-btn"
                                                        onClick={() => setRemoveConfirm({
                                                            id: member.id,
                                                            name: member.name
                                                        })}
                                                        title="Remove member"
                                                    >
                                                        <UserX size={16} />
                                                    </button>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* Pending Invites Section (Owner only) */}
                            {isOwner && invites.length > 0 && (
                                <div className="team-section">
                                    <button 
                                        className="section-header collapsible"
                                        onClick={() => setShowInvites(!showInvites)}
                                    >
                                        <Mail size={14} />
                                        <span>Pending Invites ({invites.length})</span>
                                        {showInvites ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                    </button>
                                    
                                    {showInvites && (
                                        <div className="invites-list">
                                            {invites.map(invite => (
                                                <div key={invite.id} className="invite-card">
                                                    <div className="invite-info">
                                                        <span className="invite-email">{invite.email}</span>
                                                        <div className="invite-meta">
                                                            <span className="dept-tag">{invite.department}</span>
                                                            <span className="expiry-text">{getExpiryText(invite.expires_at)}</span>
                                                        </div>
                                                    </div>
                                                    <button 
                                                        className="revoke-btn"
                                                        onClick={() => setRevokeConfirm({
                                                            id: invite.id,
                                                            email: invite.email
                                                        })}
                                                        title="Revoke invite"
                                                    >
                                                        <LinkIcon size={14} />
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Invite Button */}
                            {isOwner && (
                                <button 
                                    className="invite-trigger"
                                    onClick={() => setInviteModalOpen(true)}
                                >
                                    <UserPlus size={18} />
                                    Invite Team Member
                                </button>
                            )}
                        </>
                    )}
                </div>
            </div>

            {/* Remove Member Confirmation Modal */}
            {removeConfirm && (
                <div className="confirm-overlay">
                    <div className="confirm-modal">
                        <div className="confirm-icon danger">
                            <UserX size={24} />
                        </div>
                        <h4>Remove Team Member?</h4>
                        <p className="confirm-name">{removeConfirm.name}</p>
                        <p className="confirm-warning">
                            They will lose access to this script and all their notes will remain.
                        </p>
                        <div className="confirm-actions">
                            <button 
                                className="confirm-cancel"
                                onClick={() => setRemoveConfirm(null)}
                                disabled={actionLoading === removeConfirm.id}
                            >
                                Cancel
                            </button>
                            <button 
                                className="confirm-delete"
                                onClick={() => handleRemoveMember(removeConfirm.id, removeConfirm.name)}
                                disabled={actionLoading === removeConfirm.id}
                            >
                                {actionLoading === removeConfirm.id ? (
                                    <Loader size={14} className="spin" />
                                ) : (
                                    <UserX size={14} />
                                )}
                                Remove
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Revoke Invite Confirmation Modal */}
            {revokeConfirm && (
                <div className="confirm-overlay">
                    <div className="confirm-modal">
                        <div className="confirm-icon warning">
                            <Trash2 size={24} />
                        </div>
                        <h4>Revoke Invite?</h4>
                        <p className="confirm-name">{revokeConfirm.email}</p>
                        <p className="confirm-warning">
                            The invite link will no longer work.
                        </p>
                        <div className="confirm-actions">
                            <button 
                                className="confirm-cancel"
                                onClick={() => setRevokeConfirm(null)}
                                disabled={actionLoading === revokeConfirm.id}
                            >
                                Cancel
                            </button>
                            <button 
                                className="confirm-delete warning"
                                onClick={() => handleRevokeInvite(revokeConfirm.id, revokeConfirm.email)}
                                disabled={actionLoading === revokeConfirm.id}
                            >
                                {actionLoading === revokeConfirm.id ? (
                                    <Loader size={14} className="spin" />
                                ) : (
                                    <Trash2 size={14} />
                                )}
                                Revoke
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Invite Modal */}
            <InviteModal
                isOpen={inviteModalOpen}
                onClose={handleInviteSuccess}
                scriptId={scriptId}
                scriptTitle={scriptTitle}
            />
        </>
    );
};

export default TeamDrawer;
