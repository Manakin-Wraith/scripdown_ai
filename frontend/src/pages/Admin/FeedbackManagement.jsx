import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
    MessageSquare, 
    Filter, 
    Search, 
    AlertCircle, 
    CheckCircle, 
    Clock,
    ChevronDown,
    Eye,
    Mail,
    ArrowLeft
} from 'lucide-react';
import { supabase } from '../../lib/supabase';
import FeedbackDetailModal from '../../components/admin/FeedbackDetailModal';
import './FeedbackManagement.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const FeedbackManagement = () => {
    const { feedbackId } = useParams();
    const navigate = useNavigate();
    
    const [feedback, setFeedback] = useState([]);
    const [selectedFeedback, setSelectedFeedback] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    
    // Filters
    const [filters, setFilters] = useState({
        status: 'all',
        priority: 'all',
        category: 'all',
        search: ''
    });

    // Fetch feedback list
    const fetchFeedback = async () => {
        try {
            setLoading(true);
            const { data: { session } } = await supabase.auth.getSession();
            if (!session?.access_token) return;

            const params = new URLSearchParams();
            if (filters.status !== 'all') params.append('status', filters.status);
            if (filters.priority !== 'all') params.append('priority', filters.priority);
            if (filters.category !== 'all') params.append('category', filters.category);
            if (filters.search) params.append('search', filters.search);

            const response = await fetch(`${API_BASE_URL}/api/feedback?${params}`, {
                headers: {
                    'Authorization': `Bearer ${session.access_token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                setFeedback(data.feedback || []);
            } else {
                setError('Failed to load feedback');
            }
        } catch (err) {
            console.error('Error fetching feedback:', err);
            setError('Error loading feedback');
        } finally {
            setLoading(false);
        }
    };

    // Fetch single feedback detail
    const fetchFeedbackDetail = async (id) => {
        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session?.access_token) return;

            const response = await fetch(`${API_BASE_URL}/api/feedback/${id}`, {
                headers: {
                    'Authorization': `Bearer ${session.access_token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                setSelectedFeedback(data);
            }
        } catch (err) {
            console.error('Error fetching feedback detail:', err);
        }
    };

    useEffect(() => {
        fetchFeedback();
    }, [filters]);

    useEffect(() => {
        if (feedbackId) {
            fetchFeedbackDetail(feedbackId);
        }
    }, [feedbackId]);

    // Get status badge
    const getStatusBadge = (status) => {
        const badges = {
            new: { icon: AlertCircle, color: 'status-new', label: 'New' },
            in_progress: { icon: Clock, color: 'status-progress', label: 'In Progress' },
            resolved: { icon: CheckCircle, color: 'status-resolved', label: 'Resolved' }
        };
        const badge = badges[status] || badges.new;
        const Icon = badge.icon;
        return (
            <span className={`status-badge ${badge.color}`}>
                <Icon size={14} />
                {badge.label}
            </span>
        );
    };

    // Get priority badge
    const getPriorityBadge = (priority) => {
        const colors = {
            low: 'priority-low',
            medium: 'priority-medium',
            high: 'priority-high'
        };
        return (
            <span className={`priority-badge ${colors[priority] || colors.medium}`}>
                {priority.toUpperCase()}
            </span>
        );
    };

    // Get category emoji
    const getCategoryEmoji = (category) => {
        const emojis = {
            bug: '🐛',
            feature: '✨',
            ui_ux: '🎨',
            general: '💬'
        };
        return emojis[category] || '💬';
    };

    // Format date
    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return new Intl.DateTimeFormat('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(date);
    };

    return (
        <>
            <div className="feedback-management">
                <div className="feedback-header">
                    <button 
                        className="back-button"
                        onClick={() => navigate('/admin')}
                        title="Back to Admin Dashboard"
                    >
                        <ArrowLeft size={20} />
                    </button>
                    <div className="header-left">
                        <MessageSquare size={28} />
                        <div>
                            <h1>Feedback Management</h1>
                            <p>View and manage user feedback submissions</p>
                        </div>
                    </div>
                </div>

            {/* Filters */}
            <div className="feedback-filters">
                <div className="filter-group">
                    <Filter size={18} />
                    <select 
                        value={filters.status} 
                        onChange={(e) => setFilters({...filters, status: e.target.value})}
                        className="filter-select"
                    >
                        <option value="all">All Status</option>
                        <option value="new">New</option>
                        <option value="in_progress">In Progress</option>
                        <option value="resolved">Resolved</option>
                    </select>

                    <select 
                        value={filters.priority} 
                        onChange={(e) => setFilters({...filters, priority: e.target.value})}
                        className="filter-select"
                    >
                        <option value="all">All Priority</option>
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                    </select>

                    <select 
                        value={filters.category} 
                        onChange={(e) => setFilters({...filters, category: e.target.value})}
                        className="filter-select"
                    >
                        <option value="all">All Categories</option>
                        <option value="bug">Bug</option>
                        <option value="feature">Feature</option>
                        <option value="ui_ux">UI/UX</option>
                        <option value="general">General</option>
                    </select>
                </div>

                <div className="search-box">
                    <Search size={18} />
                    <input
                        type="text"
                        placeholder="Search feedback..."
                        value={filters.search}
                        onChange={(e) => setFilters({...filters, search: e.target.value})}
                    />
                </div>
            </div>

            {/* Feedback List */}
            <div className="feedback-content">
                {loading ? (
                    <div className="feedback-loading">Loading feedback...</div>
                ) : error ? (
                    <div className="feedback-error">{error}</div>
                ) : feedback.length === 0 ? (
                    <div className="feedback-empty">
                        <MessageSquare size={48} />
                        <p>No feedback submissions found</p>
                    </div>
                ) : (
                    <div className="feedback-list">
                        {feedback.map((item) => (
                            <div 
                                key={item.id} 
                                className={`feedback-card ${selectedFeedback?.id === item.id ? 'selected' : ''}`}
                                onClick={() => {
                                    setSelectedFeedback(item);
                                    navigate(`/admin/feedback/${item.id}`);
                                }}
                            >
                                <div className="feedback-card-header">
                                    <div className="feedback-meta">
                                        <span className="category-emoji">{getCategoryEmoji(item.category)}</span>
                                        {getPriorityBadge(item.priority)}
                                        {getStatusBadge(item.status)}
                                        {item.last_reply_sent && (
                                            <span className="email-sent-badge">
                                                <Mail size={12} />
                                                Email Sent
                                            </span>
                                        )}
                                    </div>
                                    <span className="feedback-date">{formatDate(item.created_at)}</span>
                                </div>

                                <h3 className="feedback-subject">{item.subject}</h3>
                                
                                <p className="feedback-description">
                                    {item.description.length > 150 
                                        ? `${item.description.substring(0, 150)}...` 
                                        : item.description}
                                </p>

                                <div className="feedback-footer">
                                    <div className="feedback-user">
                                        From: <strong>{item.user_name || 'Unknown User'}</strong>
                                        {item.user_email && ` (${item.user_email})`}
                                    </div>
                                    <button className="view-btn">
                                        <Eye size={16} />
                                        View Details
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>

        {/* Detail Modal */}
        {selectedFeedback && (
            <FeedbackDetailModal
                feedback={selectedFeedback}
                onClose={() => {
                    setSelectedFeedback(null);
                    navigate('/admin/feedback');
                }}
                onUpdate={() => {
                    fetchFeedback();
                    if (feedbackId) {
                        fetchFeedbackDetail(feedbackId);
                    }
                }}
            />
        )}
        </>
    );
};

export default FeedbackManagement;
