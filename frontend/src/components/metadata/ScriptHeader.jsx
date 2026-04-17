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
    List,
    ClipboardList,
    LayoutGrid,
    CalendarDays,
    Users
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import TeamDrawer from '../team/TeamDrawer';
import './ScriptHeader.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const ScriptHeader = ({ metadata, sceneCount = 0 }) => {
    const navigate = useNavigate();
    const { scriptId } = useParams();
    const [infoOpen, setInfoOpen] = useState(false);
    const [copiedField, setCopiedField] = useState(null);
    const [teamDrawerOpen, setTeamDrawerOpen] = useState(false);
    const popoverRef = useRef(null);
    const { user } = useAuth();
    const isOwner = metadata?.user_id && user?.id && metadata.user_id === user.id;

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
            
            {/* Phase 1: Membership badge deferred */}
            
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

                {/* Action buttons */}
                <button 
                    className="header-action-btn primary" 
                    title="One-Liner / Stripboard"
                    onClick={() => navigate(`/scripts/${scriptId}/stripboard`)}
                >
                    <List size={18} />
                    <span>Stripboard</span>
                </button>

                <button 
                    className="header-action-btn primary" 
                    title="Zoomable Board"
                    onClick={() => navigate(`/scripts/${scriptId}/board`)}
                >
                    <LayoutGrid size={18} />
                    <span>Board</span>
                </button>

                <button 
                    className="header-action-btn primary" 
                    title="Generate Reports"
                    onClick={() => navigate(`/scripts/${scriptId}/reports`)}
                >
                    <ClipboardList size={18} />
                    <span>Reports</span>
                </button>

                <button 
                    className="header-action-btn primary" 
                    title="Shooting Schedule"
                    onClick={() => navigate(`/scripts/${scriptId}/schedule`)}
                >
                    <CalendarDays size={18} />
                    <span>Schedule</span>
                </button>

                <button 
                    className="header-action-btn primary" 
                    title="Team Members"
                    onClick={() => setTeamDrawerOpen(true)}
                >
                    <Users size={18} />
                    <span>Team</span>
                </button>
            </div>

            <TeamDrawer
                isOpen={teamDrawerOpen}
                onClose={() => setTeamDrawerOpen(false)}
                scriptId={scriptId}
                scriptTitle={scriptName}
                currentUserId={user?.id}
                isOwner={isOwner}
            />
        </div>
    );
};

export default ScriptHeader;
