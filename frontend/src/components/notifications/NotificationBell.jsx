import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Bell, Check, CheckCheck, X, UserPlus, FileText } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../../lib/supabase';
import './NotificationBell.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const NotificationBell = () => {
    const navigate = useNavigate();
    const [notifications, setNotifications] = useState([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [isOpen, setIsOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const dropdownRef = useRef(null);

    // Fetch notifications
    const fetchNotifications = useCallback(async () => {
        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session?.access_token) return;

            const response = await fetch(`${API_BASE_URL}/api/notifications?limit=10`, {
                headers: {
                    'Authorization': `Bearer ${session.access_token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                setNotifications(data.notifications || []);
                setUnreadCount(data.unread_count || 0);
            }
        } catch (error) {
            console.error('Error fetching notifications:', error);
        }
    }, []);

    // Initial fetch
    useEffect(() => {
        fetchNotifications();
    }, [fetchNotifications]);

    // Subscribe to realtime notifications
    useEffect(() => {
        const setupRealtimeSubscription = async () => {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) return;

            const channel = supabase
                .channel('notifications')
                .on(
                    'postgres_changes',
                    {
                        event: 'INSERT',
                        schema: 'public',
                        table: 'notifications',
                        filter: `user_id=eq.${user.id}`
                    },
                    (payload) => {
                        // Add new notification to the top
                        setNotifications(prev => [payload.new, ...prev]);
                        setUnreadCount(prev => prev + 1);
                        
                        // Show browser notification if supported
                        if ('Notification' in window && Notification.permission === 'granted') {
                            new Notification(payload.new.title, {
                                body: payload.new.message,
                                icon: '/favicon.ico'
                            });
                        }
                    }
                )
                .subscribe();

            return () => {
                supabase.removeChannel(channel);
            };
        };

        setupRealtimeSubscription();
    }, []);

    // Request notification permission
    useEffect(() => {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }, []);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Mark single notification as read
    const markAsRead = async (notificationId, e) => {
        e?.stopPropagation();
        
        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session?.access_token) return;

            await fetch(`${API_BASE_URL}/api/notifications/${notificationId}/read`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${session.access_token}`
                }
            });

            setNotifications(prev => 
                prev.map(n => n.id === notificationId ? { ...n, read: true } : n)
            );
            setUnreadCount(prev => Math.max(0, prev - 1));
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    };

    // Mark all as read
    const markAllAsRead = async () => {
        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session?.access_token) return;

            await fetch(`${API_BASE_URL}/api/notifications/read-all`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${session.access_token}`
                }
            });

            setNotifications(prev => prev.map(n => ({ ...n, read: true })));
            setUnreadCount(0);
        } catch (error) {
            console.error('Error marking all as read:', error);
        }
    };

    // Handle notification click
    const handleNotificationClick = (notification) => {
        if (!notification.read) {
            markAsRead(notification.id);
        }

        // Navigate based on notification type
        if (notification.data?.script_id) {
            navigate(`/scenes/${notification.data.script_id}`);
            setIsOpen(false);
        }
    };

    // Get icon based on notification type
    const getNotificationIcon = (type) => {
        switch (type) {
            case 'invite_accepted':
            case 'member_joined':
                return <UserPlus size={16} />;
            case 'script_shared':
                return <FileText size={16} />;
            default:
                return <Bell size={16} />;
        }
    };

    // Format time ago
    const formatTimeAgo = (dateString) => {
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);

        if (seconds < 60) return 'Just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
        return date.toLocaleDateString();
    };

    return (
        <div className="notification-bell-container" ref={dropdownRef}>
            <button 
                className={`notification-bell-btn ${unreadCount > 0 ? 'has-unread' : ''}`}
                onClick={() => setIsOpen(!isOpen)}
                title="Notifications"
            >
                <Bell size={20} />
                {unreadCount > 0 && (
                    <span className="notification-badge">
                        {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                )}
            </button>

            {isOpen && (
                <div className="notification-dropdown">
                    <div className="notification-header">
                        <h3>Notifications</h3>
                        {unreadCount > 0 && (
                            <button 
                                className="mark-all-read-btn"
                                onClick={markAllAsRead}
                                title="Mark all as read"
                            >
                                <CheckCheck size={16} />
                            </button>
                        )}
                    </div>

                    <div className="notification-list">
                        {notifications.length === 0 ? (
                            <div className="notification-empty">
                                <Bell size={32} />
                                <p>No notifications yet</p>
                            </div>
                        ) : (
                            notifications.map(notification => (
                                <div 
                                    key={notification.id}
                                    className={`notification-item ${!notification.read ? 'unread' : ''}`}
                                    onClick={() => handleNotificationClick(notification)}
                                >
                                    <div className="notification-icon">
                                        {getNotificationIcon(notification.type)}
                                    </div>
                                    <div className="notification-content">
                                        <div className="notification-title">{notification.title}</div>
                                        <div className="notification-message">{notification.message}</div>
                                        <div className="notification-time">
                                            {formatTimeAgo(notification.created_at)}
                                        </div>
                                    </div>
                                    {!notification.read && (
                                        <button 
                                            className="notification-mark-read"
                                            onClick={(e) => markAsRead(notification.id, e)}
                                            title="Mark as read"
                                        >
                                            <Check size={14} />
                                        </button>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default NotificationBell;
