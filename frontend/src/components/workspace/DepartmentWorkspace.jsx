/**
 * DepartmentWorkspace - Main workspace view for a department
 * 
 * Features:
 * - Department-specific breakdown items
 * - Activity feed
 * - Threads/discussions
 * - Item tracking
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
    Loader,
    LayoutDashboard,
    ClipboardList,
    MessageSquare,
    Bell,
    Filter,
    Plus,
    ChevronDown,
    CheckCircle,
    Clock,
    AlertCircle,
    Clapperboard,
    Briefcase,
    Camera,
    Palette,
    Shirt,
    Users,
    MapPin,
    Sparkles,
    Volume2,
    Scissors,
    PenTool,
    User
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { 
    getDepartmentItems, 
    getActivityLog, 
    getThreads,
    getDepartments as fetchDepartments
} from '../../lib/supabase';
import { getScriptMetadata } from '../../services/apiService';
import AuthModal from '../auth/AuthModal';
import DepartmentSelector from '../auth/DepartmentSelector';
import CameraDeptView from './CameraDeptView';
import './DepartmentWorkspace.css';

// Icon mapping
const DEPARTMENT_ICONS = {
    'clapperboard': Clapperboard,
    'briefcase': Briefcase,
    'camera': Camera,
    'palette': Palette,
    'shirt': Shirt,
    'users': Users,
    'map-pin': MapPin,
    'sparkles': Sparkles,
    'volume-2': Volume2,
    'scissors': Scissors,
    'pen-tool': PenTool,
    'user': User
};

const DepartmentWorkspace = () => {
    const { scriptId, departmentCode } = useParams();
    const navigate = useNavigate();
    const { user, isAuthenticated, departments, activeDepartment, loading: authLoading } = useAuth();

    // State
    const [script, setScript] = useState(null);
    const [allDepartments, setAllDepartments] = useState([]);
    const [currentDepartment, setCurrentDepartment] = useState(null);
    const [items, setItems] = useState([]);
    const [activities, setActivities] = useState([]);
    const [threads, setThreads] = useState([]);
    const [activeTab, setActiveTab] = useState('dashboard'); // dashboard, items, threads, activity
    const [loading, setLoading] = useState(true);
    const [showAuthModal, setShowAuthModal] = useState(false);
    const [showDeptSelector, setShowDeptSelector] = useState(false);
    const [statusFilter, setStatusFilter] = useState('all');

    // Fetch script and department data
    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            
            try {
                // Fetch script metadata
                const scriptData = await getScriptMetadata(scriptId);
                setScript(scriptData);

                // Fetch all departments
                const { data: depts } = await fetchDepartments();
                setAllDepartments(depts || []);

                // Determine current department
                let dept = null;
                if (departmentCode) {
                    dept = depts?.find(d => d.code === departmentCode);
                } else if (activeDepartment) {
                    dept = activeDepartment;
                } else if (depts?.length > 0) {
                    dept = depts[0];
                }
                setCurrentDepartment(dept);

                if (dept) {
                    // Fetch department items
                    const { data: itemsData } = await getDepartmentItems(scriptId, dept.id);
                    setItems(itemsData || []);

                    // Fetch activity log
                    const { data: activityData } = await getActivityLog(scriptId, dept.id);
                    setActivities(activityData || []);

                    // Fetch threads
                    const { data: threadsData } = await getThreads(scriptId);
                    setThreads(threadsData || []);
                }

            } catch (err) {
                console.error('Error fetching workspace data:', err);
            } finally {
                setLoading(false);
            }
        };

        if (scriptId) {
            fetchData();
        }
    }, [scriptId, departmentCode, activeDepartment]);

    // Check if user needs to select departments
    useEffect(() => {
        if (isAuthenticated && departments.length === 0 && !authLoading) {
            setShowDeptSelector(true);
        }
    }, [isAuthenticated, departments, authLoading]);

    const getIcon = (iconName) => {
        return DEPARTMENT_ICONS[iconName] || Briefcase;
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'complete': return <CheckCircle size={16} className="status-complete" />;
            case 'in_progress': return <Clock size={16} className="status-progress" />;
            case 'on_hold': return <AlertCircle size={16} className="status-hold" />;
            default: return <Clock size={16} className="status-pending" />;
        }
    };

    const filteredItems = items.filter(item => {
        if (statusFilter === 'all') return true;
        return item.status === statusFilter;
    });

    const stats = {
        total: items.length,
        pending: items.filter(i => i.status === 'pending').length,
        inProgress: items.filter(i => i.status === 'in_progress').length,
        complete: items.filter(i => i.status === 'complete').length
    };

    // Show auth modal if not authenticated
    if (!isAuthenticated && !authLoading) {
        return (
            <div className="workspace-auth-prompt">
                <div className="auth-prompt-content">
                    <Clapperboard size={48} />
                    <h2>Sign in to access your workspace</h2>
                    <p>Department workspaces require authentication to track your items and collaborate with your team.</p>
                    <button 
                        className="auth-prompt-btn"
                        onClick={() => setShowAuthModal(true)}
                    >
                        Sign In
                    </button>
                </div>
                <AuthModal 
                    isOpen={showAuthModal} 
                    onClose={() => setShowAuthModal(false)} 
                />
            </div>
        );
    }

    // Show department selector if user has no departments
    if (showDeptSelector) {
        return (
            <DepartmentSelector 
                isOpen={true} 
                onComplete={() => setShowDeptSelector(false)} 
            />
        );
    }

    if (loading || authLoading) {
        return (
            <div className="workspace-loading">
                <Loader size={32} className="spin" />
                <span>Loading workspace...</span>
            </div>
        );
    }

    const DeptIcon = currentDepartment ? getIcon(currentDepartment.icon) : Briefcase;

    return (
        <div className="department-workspace">
            {/* Header */}
            <div className="workspace-header">
                <div className="header-left">
                    <div 
                        className="dept-badge"
                        style={{ 
                            backgroundColor: `${currentDepartment?.color}20`,
                            color: currentDepartment?.color 
                        }}
                    >
                        <DeptIcon size={20} />
                        <span>{currentDepartment?.name || 'Workspace'}</span>
                        <ChevronDown size={16} />
                    </div>
                    <h1>{script?.title || 'Script'}</h1>
                </div>
                <div className="header-right">
                    <button className="icon-btn">
                        <Bell size={20} />
                        {activities.length > 0 && (
                            <span className="notification-badge">{Math.min(activities.length, 9)}</span>
                        )}
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div className="workspace-tabs">
                <button 
                    className={`tab ${activeTab === 'dashboard' ? 'active' : ''}`}
                    onClick={() => setActiveTab('dashboard')}
                >
                    <LayoutDashboard size={18} />
                    Dashboard
                </button>
                <button 
                    className={`tab ${activeTab === 'items' ? 'active' : ''}`}
                    onClick={() => setActiveTab('items')}
                >
                    <ClipboardList size={18} />
                    My Items
                    <span className="tab-count">{items.length}</span>
                </button>
                <button 
                    className={`tab ${activeTab === 'threads' ? 'active' : ''}`}
                    onClick={() => setActiveTab('threads')}
                >
                    <MessageSquare size={18} />
                    Threads
                    <span className="tab-count">{threads.length}</span>
                </button>
                <button 
                    className={`tab ${activeTab === 'activity' ? 'active' : ''}`}
                    onClick={() => setActiveTab('activity')}
                >
                    <Bell size={18} />
                    Activity
                </button>
                <button 
                    className={`tab ${activeTab === 'camera' ? 'active' : ''}`}
                    onClick={() => setActiveTab('camera')}
                >
                    <Camera size={18} />
                    Camera
                </button>
            </div>

            {/* Content */}
            <div className="workspace-content">
                {activeTab === 'dashboard' && (
                    <div className="dashboard-view">
                        {/* Stats */}
                        <div className="stats-grid">
                            <div className="stat-card">
                                <span className="stat-value">{stats.total}</span>
                                <span className="stat-label">Total Items</span>
                            </div>
                            <div className="stat-card pending">
                                <span className="stat-value">{stats.pending}</span>
                                <span className="stat-label">Pending</span>
                            </div>
                            <div className="stat-card progress">
                                <span className="stat-value">{stats.inProgress}</span>
                                <span className="stat-label">In Progress</span>
                            </div>
                            <div className="stat-card complete">
                                <span className="stat-value">{stats.complete}</span>
                                <span className="stat-label">Complete</span>
                            </div>
                        </div>

                        {/* Recent Activity */}
                        <div className="dashboard-section">
                            <h3>Recent Activity</h3>
                            {activities.length === 0 ? (
                                <div className="empty-state">
                                    <Bell size={32} />
                                    <p>No recent activity</p>
                                </div>
                            ) : (
                                <div className="activity-list">
                                    {activities.slice(0, 5).map(activity => (
                                        <div key={activity.id} className="activity-item">
                                            <span className="activity-summary">{activity.summary}</span>
                                            <span className="activity-time">
                                                {new Date(activity.created_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Open Threads */}
                        <div className="dashboard-section">
                            <h3>Open Threads</h3>
                            {threads.filter(t => t.status === 'open').length === 0 ? (
                                <div className="empty-state">
                                    <MessageSquare size={32} />
                                    <p>No open threads</p>
                                </div>
                            ) : (
                                <div className="threads-preview">
                                    {threads.filter(t => t.status === 'open').slice(0, 3).map(thread => (
                                        <div key={thread.id} className="thread-preview">
                                            <span className="thread-title">{thread.title}</span>
                                            <span className="thread-meta">
                                                {thread.messages?.length || 0} messages
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {activeTab === 'items' && (
                    <div className="items-view">
                        {/* Toolbar */}
                        <div className="items-toolbar">
                            <div className="filter-group">
                                <Filter size={16} />
                                <select 
                                    value={statusFilter} 
                                    onChange={(e) => setStatusFilter(e.target.value)}
                                >
                                    <option value="all">All Status</option>
                                    <option value="pending">Pending</option>
                                    <option value="in_progress">In Progress</option>
                                    <option value="complete">Complete</option>
                                    <option value="on_hold">On Hold</option>
                                </select>
                            </div>
                            <button className="add-item-btn">
                                <Plus size={16} />
                                Add Item
                            </button>
                        </div>

                        {/* Items List */}
                        {filteredItems.length === 0 ? (
                            <div className="empty-state large">
                                <ClipboardList size={48} />
                                <h3>No items yet</h3>
                                <p>Items from scene breakdowns will appear here, or add your own.</p>
                                <button className="add-item-btn">
                                    <Plus size={16} />
                                    Add First Item
                                </button>
                            </div>
                        ) : (
                            <div className="items-list">
                                {filteredItems.map(item => (
                                    <div key={item.id} className="item-card">
                                        <div className="item-status">
                                            {getStatusIcon(item.status)}
                                        </div>
                                        <div className="item-info">
                                            <span className="item-name">{item.item_name}</span>
                                            <span className="item-type">{item.item_type}</span>
                                        </div>
                                        <div className="item-meta">
                                            {item.due_date && (
                                                <span className="item-due">
                                                    Due: {new Date(item.due_date).toLocaleDateString()}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'threads' && (
                    <div className="threads-view">
                        {threads.length === 0 ? (
                            <div className="empty-state large">
                                <MessageSquare size={48} />
                                <h3>No threads yet</h3>
                                <p>Start a discussion with other departments.</p>
                                <button className="add-item-btn">
                                    <Plus size={16} />
                                    Start Thread
                                </button>
                            </div>
                        ) : (
                            <div className="threads-list">
                                {threads.map(thread => (
                                    <div key={thread.id} className="thread-card">
                                        <div className="thread-header">
                                            <span className={`thread-status ${thread.status}`}>
                                                {thread.status}
                                            </span>
                                            <span className="thread-title">{thread.title}</span>
                                        </div>
                                        <div className="thread-participants">
                                            {thread.participants?.map(p => (
                                                <span 
                                                    key={p.department?.id} 
                                                    className="participant-badge"
                                                    style={{ backgroundColor: `${p.department?.color}30` }}
                                                >
                                                    {p.department?.name}
                                                </span>
                                            ))}
                                        </div>
                                        <div className="thread-meta">
                                            <span>{thread.messages?.length || 0} messages</span>
                                            <span>{new Date(thread.created_at).toLocaleDateString()}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'activity' && (
                    <div className="activity-view">
                        {activities.length === 0 ? (
                            <div className="empty-state large">
                                <Bell size={48} />
                                <h3>No activity yet</h3>
                                <p>Activity from your department will appear here.</p>
                            </div>
                        ) : (
                            <div className="activity-feed">
                                {activities.map(activity => (
                                    <div key={activity.id} className="activity-feed-item">
                                        <div className="activity-icon">
                                            <Bell size={16} />
                                        </div>
                                        <div className="activity-content">
                                            <span className="activity-summary">{activity.summary}</span>
                                            <span className="activity-time">
                                                {new Date(activity.created_at).toLocaleString()}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'camera' && (
                    <CameraDeptView scriptId={scriptId} />
                )}
            </div>
        </div>
    );
};

export default DepartmentWorkspace;
