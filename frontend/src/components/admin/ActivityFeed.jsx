import { useState, useEffect } from 'react';
import { 
  Users, 
  FileText, 
  CheckCircle, 
  Clock,
  RefreshCw,
  CreditCard
} from 'lucide-react';
import PropTypes from 'prop-types';
import './ActivityFeed.css';

/**
 * ActivityFeed - Real-time activity timeline component
 * Shows recent platform events (signups, uploads, analysis)
 * 
 * @param {Array} activities - Array of activity objects
 * @param {boolean} loading - Loading state
 * @param {Function} onRefresh - Callback to refresh activities
 * @param {boolean} autoRefresh - Enable auto-refresh every 30s
 */
export default function ActivityFeed({ activities = [], loading = false, onRefresh, autoRefresh = false }) {
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (!autoRefresh || !onRefresh) return;

    const interval = setInterval(() => {
      onRefresh();
    }, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, [autoRefresh, onRefresh]);

  const handleRefresh = async () => {
    if (!onRefresh || refreshing) return;
    setRefreshing(true);
    await onRefresh();
    setTimeout(() => setRefreshing(false), 500);
  };

  const getActivityIcon = (type) => {
    switch (type) {
      case 'user_signup':      return <Users size={20} />;
      case 'script_upload':    return <FileText size={20} />;
      case 'scene_analyzed':   return <CheckCircle size={20} />;
      case 'payment_approved': return <CreditCard size={20} />;
      default:                 return <Clock size={20} />;
    }
  };

  const getActivityColor = (type) => {
    switch (type) {
      case 'user_signup':      return 'blue';
      case 'script_upload':    return 'indigo';
      case 'scene_analyzed':   return 'green';
      case 'payment_approved': return 'emerald';
      default:                 return 'gray';
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  if (loading && activities.length === 0) {
    return (
      <div className="activity-feed">
        <div className="activity-feed__header">
          <h3>Recent Activity</h3>
        </div>
        <div className="activity-feed__loading">
          <div className="spinner-sm"></div>
          <p>Loading activity...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="activity-feed">
      <div className="activity-feed__header">
        <h3>Recent Activity</h3>
        {onRefresh && (
          <button 
            onClick={handleRefresh} 
            className={`refresh-button ${refreshing ? 'refreshing' : ''}`}
            disabled={refreshing}
          >
            <RefreshCw size={16} />
            {autoRefresh && <span className="auto-badge">Auto</span>}
          </button>
        )}
      </div>

      <div className="activity-feed__timeline">
        {activities.length === 0 ? (
          <div className="activity-feed__empty">
            <Clock size={32} />
            <p>No recent activity</p>
          </div>
        ) : (
          activities.map((activity, index) => (
            <div 
              key={`${activity.type}-${activity.timestamp}-${index}`} 
              className={`activity-item activity-item--${getActivityColor(activity.type)}`}
            >
              <div className="activity-item__icon">
                {getActivityIcon(activity.type)}
              </div>
              <div className="activity-item__content">
                <p className="activity-item__description">
                  {activity.description}
                </p>
                <span className="activity-item__time">
                  {formatTimestamp(activity.timestamp)}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

ActivityFeed.propTypes = {
  activities: PropTypes.arrayOf(PropTypes.shape({
    type: PropTypes.string.isRequired,
    description: PropTypes.string.isRequired,
    timestamp: PropTypes.string.isRequired,
    user_name: PropTypes.string,
    script_title: PropTypes.string,
  })),
  loading: PropTypes.bool,
  onRefresh: PropTypes.func,
  autoRefresh: PropTypes.bool
};
