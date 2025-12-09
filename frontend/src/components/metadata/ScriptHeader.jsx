import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { 
    User, 
    Mail, 
    Phone, 
    Info,
    Copy,
    Check,
    FileText,
    Download,
    Share2,
    ClipboardList,
    List,
    Users,
    Crown,
    Shield,
    Settings2,
    Lock,
    Unlock
} from 'lucide-react';
import TeamDrawer from '../team/TeamDrawer';
import LockScriptModal from '../scripts/LockScriptModal';
import './ScriptHeader.css';

const API_BASE_URL = 'http://localhost:5000';

const ScriptHeader = ({ metadata, sceneCount = 0 }) => {
    const navigate = useNavigate();
    const { scriptId } = useParams();
    const [infoOpen, setInfoOpen] = useState(false);
    const [copiedField, setCopiedField] = useState(null);
    const [teamDrawerOpen, setTeamDrawerOpen] = useState(false);
    const [lockModalOpen, setLockModalOpen] = useState(false);
    const [membership, setMembership] = useState(null);
    const [currentUserId, setCurrentUserId] = useState(null);
    const [scriptData, setScriptData] = useState(null);
    const popoverRef = useRef(null);

    // Fetch user's membership for this script
    useEffect(() => {
        const fetchMembership = async () => {
            if (!scriptId) return;
            
            try {
                const { supabase } = await import('../../lib/supabase');
                const { data: { session } } = await supabase.auth.getSession();
                
                if (!session?.access_token) return;
                
                // Get current user ID from session
                const userId = session.user?.id;
                setCurrentUserId(userId);
                
                const response = await fetch(`${API_BASE_URL}/api/scripts/${scriptId}/my-membership`, {
                    headers: {
                        'Authorization': `Bearer ${session.access_token}`
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    setMembership(data.membership);
                }
            } catch (error) {
                console.error('Error fetching membership:', error);
            }
        };
        
        fetchMembership();
    }, [scriptId]);

    // Close popover when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (popoverRef.current && !popoverRef.current.contains(event.target)) {
                setInfoOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const copyToClipboard = async (text, field) => {
        if (!text) return;
        try {
            await navigator.clipboard.writeText(text);
            setCopiedField(field);
            setTimeout(() => setCopiedField(null), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    const scriptName = (metadata?.title || metadata?.script_name)?.replace('.pdf', '') || 'Untitled Script';
    const writerName = metadata?.writer_name || null;
    const hasContactInfo = metadata?.writer_email || metadata?.writer_phone;

    return (
        <div className="script-header">
            {/* All items inline */}
            <span className="script-name">{scriptName}</span>
            {writerName && (
                <span className="writer-name">
                    <User size={14} />
                    {writerName}
                </span>
            )}
            <span className="scene-count-badge">{sceneCount} Scenes</span>
            {/* Department/Role Badge */}
            {membership && (
                <span 
                    className="membership-badge"
                    style={{ 
                        '--badge-color': membership.department_color || '#6366F1'
                    }}
                >
                    {membership.is_owner ? (
                        <>
                            <Crown size={14} />
                            <span>Owner</span>
                        </>
                    ) : (
                        <>
                            <Shield size={14} />
                            <span>{membership.department}</span>
                            {membership.role === 'admin' && (
                                <span className="role-tag">Admin</span>
                            )}
                        </>
                    )}
                </span>
            )}
            
            <div className="header-spacer"></div>

            <div className="header-right">
                {/* Info Popover Trigger */}
                {hasContactInfo && (
                    <div className="info-popover-container" ref={popoverRef}>
                        <button 
                            className={`header-action-btn ${infoOpen ? 'active' : ''}`}
                            onClick={() => setInfoOpen(!infoOpen)}
                            title="Contact Info"
                        >
                            <Info size={18} />
                            <span>Info</span>
                        </button>

                        {infoOpen && (
                            <div className="info-popover">
                                <div className="popover-header">
                                    <h3>Contact Information</h3>
                                </div>
                                <div className="popover-content">
                                    {metadata.writer_email && (
                                        <div className="contact-row">
                                            <Mail size={16} className="contact-icon" />
                                            <span className="contact-text">{metadata.writer_email}</span>
                                            <button
                                                className="copy-btn-sm"
                                                onClick={() => copyToClipboard(metadata.writer_email, 'email')}
                                            >
                                                {copiedField === 'email' ? <Check size={14} /> : <Copy size={14} />}
                                            </button>
                                        </div>
                                    )}
                                    {metadata.writer_phone && (
                                        <div className="contact-row">
                                            <Phone size={16} className="contact-icon" />
                                            <span className="contact-text">{metadata.writer_phone}</span>
                                            <button
                                                className="copy-btn-sm"
                                                onClick={() => copyToClipboard(metadata.writer_phone, 'phone')}
                                            >
                                                {copiedField === 'phone' ? <Check size={14} /> : <Copy size={14} />}
                                            </button>
                                        </div>
                                    )}
                                </div>
                                {metadata.draft_version && (
                                    <div className="popover-footer">
                                        <FileText size={14} />
                                        <span>{metadata.draft_version}</span>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {/* Lock Status Badge */}
                {metadata?.is_locked && (
                    <div className="lock-status-badge">
                        <Lock size={14} />
                        <span>{metadata.current_revision_color || 'LOCKED'}</span>
                    </div>
                )}

                {/* Action Buttons */}
                <button 
                    className="header-action-btn"
                    title="Manage Scenes"
                    onClick={() => navigate(`/scripts/${scriptId}/manage`)}
                >
                    <Settings2 size={18} />
                    <span>Manage</span>
                </button>

                <button 
                    className={`header-action-btn ${metadata?.is_locked ? 'locked' : ''}`}
                    title={metadata?.is_locked ? 'Unlock Script' : 'Lock Script'}
                    onClick={() => setLockModalOpen(true)}
                >
                    {metadata?.is_locked ? <Unlock size={18} /> : <Lock size={18} />}
                    <span>{metadata?.is_locked ? 'Unlock' : 'Lock'}</span>
                </button>

                <button 
                    className="header-action-btn"
                    title="Manage Team Members"
                    onClick={() => setTeamDrawerOpen(true)}
                >
                    <Users size={18} />
                    <span>Team</span>
                </button>

                <button 
                    className="header-action-btn" 
                    title="One-Liner / Stripboard"
                    onClick={() => navigate(`/scripts/${scriptId}/stripboard`)}
                >
                    <List size={18} />
                    <span>Stripboard</span>
                </button>

                {metadata?.is_locked && (
                    <button 
                        className="header-action-btn shooting-script" 
                        title="View Shooting Script"
                        onClick={() => navigate(`/scripts/${scriptId}/shooting-script`)}
                    >
                        <FileText size={18} />
                        <span>Shooting Script</span>
                    </button>
                )}

                <button 
                    className="header-action-btn primary" 
                    title="Generate Reports"
                    onClick={() => navigate(`/scripts/${scriptId}/reports`)}
                >
                    <ClipboardList size={18} />
                    <span>Reports</span>
                </button>
            </div>

            {/* Team Drawer */}
            <TeamDrawer
                isOpen={teamDrawerOpen}
                onClose={() => setTeamDrawerOpen(false)}
                scriptId={scriptId}
                scriptTitle={scriptName}
                currentUserId={currentUserId}
                isOwner={membership?.is_owner || false}
            />
            
            {/* Lock Script Modal */}
            <LockScriptModal
                isOpen={lockModalOpen}
                onClose={() => setLockModalOpen(false)}
                script={{ 
                    id: scriptId, 
                    is_locked: metadata?.is_locked,
                    current_revision_color: metadata?.current_revision_color,
                    locked_at: metadata?.locked_at
                }}
                onSuccess={() => window.location.reload()}
            />
        </div>
    );
};

export default ScriptHeader;
