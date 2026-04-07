/**
 * InviteModal - Send team invitations
 * 
 * Allows script owners to invite team members by email
 * with department assignment.
 */

import React, { useState, useEffect } from 'react';
import { 
    X, 
    Mail, 
    Users, 
    Copy, 
    Check, 
    Loader,
    Send,
    Link as LinkIcon,
    Lock,
    Sparkles
} from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { useSubscription } from '../../hooks/useSubscription';
import { UpgradeModal } from '../subscription';
import './InviteModal.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const ROLES = [
    { value: 'member', label: 'Member', description: 'Can view and add notes' },
    { value: 'admin', label: 'Admin', description: 'Can manage team and settings' },
    { value: 'viewer', label: 'Viewer', description: 'View only access' },
];

const InviteModal = ({ isOpen, onClose, scriptId, scriptTitle }) => {
    const toast = useToast();
    const { canAccess, status, daysRemaining } = useSubscription();
    
    const [email, setEmail] = useState('');
    const [department, setDepartment] = useState('');
    const [role, setRole] = useState('member');
    const [loading, setLoading] = useState(false);
    const [inviteResult, setInviteResult] = useState(null);
    const [copied, setCopied] = useState(false);
    const [departments, setDepartments] = useState([]);
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    
    // Check if user has team collaboration access
    const hasTeamAccess = canAccess('team_collaboration');

    // Fetch departments from API
    useEffect(() => {
        const fetchDepartments = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/departments`);
                const data = await response.json();
                if (data.departments) {
                    setDepartments(data.departments);
                }
            } catch (error) {
                console.error('Error fetching departments:', error);
            }
        };
        fetchDepartments();
    }, []);

    // Reset form when modal opens
    useEffect(() => {
        if (isOpen) {
            setEmail('');
            setDepartment('');
            setRole('member');
            setInviteResult(null);
            setCopied(false);
        }
    }, [isOpen]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!email || !department) {
            toast.error('Error', 'Please fill in all fields');
            return;
        }
        
        setLoading(true);
        
        try {
            const { supabase } = await import('../../lib/supabase');
            const { data: { session } } = await supabase.auth.getSession();
            
            const response = await fetch(`${API_BASE_URL}/api/scripts/${scriptId}/invites`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session?.access_token || ''}`
                },
                body: JSON.stringify({
                    email,
                    department_code: department,
                    role
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to create invite');
            }
            
            setInviteResult(data.invite);
            toast.success('Success', 'Invite created successfully!');
            
        } catch (error) {
            console.error('Error creating invite:', error);
            toast.error('Error', error.message);
        } finally {
            setLoading(false);
        }
    };

    const copyInviteLink = async () => {
        if (!inviteResult?.invite_url) return;
        
        try {
            await navigator.clipboard.writeText(inviteResult.invite_url);
            setCopied(true);
            toast.success('Copied', 'Link copied to clipboard!');
            setTimeout(() => setCopied(false), 2000);
        } catch (error) {
            toast.error('Error', 'Failed to copy link');
        }
    };

    const sendAnotherInvite = () => {
        setEmail('');
        setDepartment('');
        setRole('member');
        setInviteResult(null);
        setCopied(false);
    };

    if (!isOpen) return null;

    // If no team access, show upgrade prompt
    if (!hasTeamAccess) {
        return (
            <>
                <div className="invite-modal-overlay" onClick={onClose}>
                    <div className="invite-modal" onClick={e => e.stopPropagation()}>
                        <header className="invite-modal-header">
                            <div className="header-content">
                                <Users size={24} />
                                <div>
                                    <h2>Invite Team Member</h2>
                                    <p className="script-name">{scriptTitle}</p>
                                </div>
                            </div>
                            <button className="close-btn" onClick={onClose}>
                                <X size={20} />
                            </button>
                        </header>

                        <div className="invite-modal-body invite-locked">
                            <div className="locked-content">
                                <div className="locked-icon">
                                    <Lock size={32} />
                                </div>
                                <h3>Team Collaboration Locked</h3>
                                <p>Upgrade to invite team members and collaborate on your scripts.</p>
                                <button 
                                    className="upgrade-btn"
                                    onClick={() => setShowUpgradeModal(true)}
                                >
                                    <Sparkles size={18} />
                                    Subscribe — $49/month
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                <UpgradeModal
                    isOpen={showUpgradeModal}
                    onClose={() => setShowUpgradeModal(false)}
                    feature="team_collaboration"
                    daysRemaining={daysRemaining}
                    isExpired={status === 'expired'}
                />
            </>
        );
    }

    return (
        <div className="invite-modal-overlay" onClick={onClose}>
            <div className="invite-modal" onClick={e => e.stopPropagation()}>
                <header className="invite-modal-header">
                    <div className="header-content">
                        <Users size={24} />
                        <div>
                            <h2>Invite Team Member</h2>
                            <p className="script-name">{scriptTitle}</p>
                        </div>
                    </div>
                    <button className="close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </header>

                <div className="invite-modal-body">
                    {!inviteResult ? (
                        <form onSubmit={handleSubmit}>
                            {/* Email Input */}
                            <div className="form-group">
                                <label>
                                    <Mail size={16} />
                                    Email Address
                                </label>
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="teammate@example.com"
                                    required
                                />
                            </div>

                            {/* Department Selection */}
                            <div className="form-group">
                                <label>
                                    <Users size={16} />
                                    Department
                                </label>
                                <div className="department-grid">
                                    {departments.map(dept => (
                                        <button
                                            key={dept.code}
                                            type="button"
                                            className={`department-option ${department === dept.code ? 'selected' : ''}`}
                                            onClick={() => setDepartment(dept.code)}
                                            style={{
                                                '--dept-color': dept.color,
                                                borderColor: department === dept.code ? dept.color : undefined
                                            }}
                                        >
                                            <span 
                                                className="dept-dot" 
                                                style={{ backgroundColor: dept.color }}
                                            />
                                            {dept.name}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Role Selection */}
                            <div className="form-group">
                                <label>Role</label>
                                <div className="role-options">
                                    {ROLES.map(r => (
                                        <label 
                                            key={r.value} 
                                            className={`role-option ${role === r.value ? 'selected' : ''}`}
                                        >
                                            <input
                                                type="radio"
                                                name="role"
                                                value={r.value}
                                                checked={role === r.value}
                                                onChange={(e) => setRole(e.target.value)}
                                            />
                                            <div className="role-content">
                                                <span className="role-name">{r.label}</span>
                                                <span className="role-desc">{r.description}</span>
                                            </div>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            {/* Submit Button */}
                            <button 
                                type="submit" 
                                className="submit-btn"
                                disabled={loading || !email || !department}
                            >
                                {loading ? (
                                    <>
                                        <Loader size={18} className="spin" />
                                        Creating Invite...
                                    </>
                                ) : (
                                    <>
                                        <Send size={18} />
                                        Create Invite Link
                                    </>
                                )}
                            </button>
                        </form>
                    ) : (
                        <div className="invite-success">
                            <div className="success-icon">
                                <Check size={32} />
                            </div>
                            <h3>Invite Created!</h3>
                            <p>
                                Share this link with <strong>{inviteResult.email}</strong> to invite them 
                                as <strong>{inviteResult.department}</strong>
                            </p>
                            
                            <div className="invite-link-box">
                                <LinkIcon size={16} />
                                <input 
                                    type="text" 
                                    value={inviteResult.invite_url} 
                                    readOnly 
                                />
                                <button 
                                    className="copy-btn"
                                    onClick={copyInviteLink}
                                >
                                    {copied ? <Check size={16} /> : <Copy size={16} />}
                                    {copied ? 'Copied!' : 'Copy'}
                                </button>
                            </div>
                            
                            <p className="expires-note">
                                This link expires in 7 days
                            </p>
                            
                            <div className="success-actions">
                                <button 
                                    className="btn-secondary"
                                    onClick={sendAnotherInvite}
                                >
                                    Invite Another
                                </button>
                                <button 
                                    className="btn-primary"
                                    onClick={onClose}
                                >
                                    Done
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default InviteModal;
