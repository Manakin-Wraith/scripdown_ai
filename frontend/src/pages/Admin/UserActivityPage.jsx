import { useState, useEffect, Fragment } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  Search, 
  Filter,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Users,
  FileText,
  Calendar,
  AlertCircle,
  CreditCard,
  Star,
  Shield,
  Coins,
  TrendingUp,
  Clock,
  Phone,
  Briefcase
} from 'lucide-react';
import { getUserAnalytics } from '../../services/apiService';
import './UserActivityPage.css';

/**
 * User Activity Page - Enhanced user table with full profile data
 * Route: /admin/users
 */
export default function UserActivityPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [expandedUser, setExpandedUser] = useState(null);
  
  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const limit = 50;

  useEffect(() => {
    loadUsers();
  }, [page, statusFilter]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const offset = (page - 1) * limit;
      const response = await getUserAnalytics(30, limit, offset, statusFilter, search);
      
      if (response.success) {
        setUsers(response.data.users || []);
        setTotal(response.data.total || 0);
      } else {
        setError(response.error || 'Failed to load users');
      }
    } catch (err) {
      console.error('Failed to load users:', err);
      setError(err.message || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    loadUsers();
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
    return date.toLocaleDateString();
  };

  const formatSource = (source) => {
    if (!source) return 'direct';
    return source.replace(/_/g, ' ').replace(/landing /g, '');
  };

  const getExpiryStatus = (expiresAt) => {
    if (!expiresAt) return null;
    const now = new Date();
    const expiry = new Date(expiresAt);
    const diffDays = Math.floor((expiry - now) / (1000 * 60 * 60 * 24));
    if (diffDays < 0) return { label: 'Expired', cls: 'expiry-expired' };
    if (diffDays <= 3) return { label: `${diffDays}d left`, cls: 'expiry-critical' };
    if (diffDays <= 7) return { label: `${diffDays}d left`, cls: 'expiry-warning' };
    return { label: `${diffDays}d left`, cls: 'expiry-ok' };
  };

  const toggleExpand = (userId) => {
    setExpandedUser(expandedUser === userId ? null : userId);
  };

  const totalPages = Math.ceil(total / limit);

  // Summary stats from current page data
  const trialCount = users.filter(u => u.subscription_status === 'trial').length;
  const activeCount = users.filter(u => u.subscription_status === 'active').length;
  const legacyCount = users.filter(u => u.is_legacy_beta).length;
  const totalCreditsInPlay = users.reduce((sum, u) => sum + (u.credits_remaining || 0), 0);

  if (loading && users.length === 0) {
    return (
      <div className="user-activity-page">
        <div className="page-header">
          <button onClick={() => navigate('/admin')} className="back-button">
            <ArrowLeft size={20} />
          </button>
          <h1>User Activity</h1>
        </div>
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading users...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="user-activity-page">
      {/* Header */}
      <div className="page-header">
        <button onClick={() => navigate('/admin')} className="back-button">
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1>User Activity</h1>
          <p className="subtitle">{total} total users</p>
        </div>
        <button onClick={loadUsers} className="btn-secondary-sm">
          Refresh
        </button>
      </div>

      {/* Quick Stats Bar */}
      <div className="quick-stats-bar">
        <div className="quick-stat">
          <span className="quick-stat-value">{total}</span>
          <span className="quick-stat-label">Total</span>
        </div>
        <div className="quick-stat">
          <span className="quick-stat-value stat-trial">{trialCount}</span>
          <span className="quick-stat-label">Trial</span>
        </div>
        <div className="quick-stat">
          <span className="quick-stat-value stat-active">{activeCount}</span>
          <span className="quick-stat-label">Active</span>
        </div>
        <div className="quick-stat">
          <span className="quick-stat-value stat-legacy">{legacyCount}</span>
          <span className="quick-stat-label">Legacy Beta</span>
        </div>
        <div className="quick-stat">
          <Coins size={14} className="quick-stat-icon" />
          <span className="quick-stat-value">{totalCreditsInPlay}</span>
          <span className="quick-stat-label">Credits in play</span>
        </div>
      </div>

      {/* Filters */}
      <div className="filters-bar">
        <form onSubmit={handleSearch} className="search-form">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search by name or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button type="submit" className="btn-primary-sm">Search</button>
        </form>

        <div className="filter-group">
          <Filter size={18} />
          <select 
            value={statusFilter} 
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All Status</option>
            <option value="trial">Trial</option>
            <option value="active">Active</option>
            <option value="expired">Expired</option>
          </select>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="error-banner">
          <AlertCircle size={20} />
          <span>{error}</span>
          <button onClick={loadUsers}>Retry</button>
        </div>
      )}

      {/* Users Table */}
      <div className="table-container">
        <table className="users-table">
          <thead>
            <tr>
              <th className="th-expand"></th>
              <th>User</th>
              <th>Status</th>
              <th>Credits</th>
              <th>Scripts</th>
              <th>Source</th>
              <th>Last Active</th>
              <th>Joined</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => {
              const expiry = getExpiryStatus(user.subscription_expires_at);
              const isExpanded = expandedUser === user.user_id;
              
              return (
                <Fragment key={user.user_id}>
                  <tr 
                    className={isExpanded ? 'row-expanded' : ''}
                    onClick={() => toggleExpand(user.user_id)}
                  >
                    <td className="td-expand">
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </td>
                    <td>
                      <div className="user-cell">
                        <div className="user-avatar">
                          {(user.name || '?').charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="user-name">
                            {user.name}
                            {user.is_superuser && (
                              <Shield size={14} className="badge-icon badge-admin" title="Admin" />
                            )}
                            {user.is_legacy_beta && (
                              <Star size={14} className="badge-icon badge-beta" title="Legacy Beta" />
                            )}
                          </div>
                          <div className="user-email">{user.email}</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <div className="status-cell">
                        <span className={`status-badge status-${user.subscription_status}`}>
                          {user.subscription_status}
                        </span>
                        {expiry && (
                          <span className={`expiry-badge ${expiry.cls}`}>
                            {expiry.label}
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      <div className="credits-cell">
                        <span className={`credits-value ${user.credits_remaining === 0 ? 'credits-zero' : ''}`}>
                          {user.credits_remaining}
                        </span>
                        <span className="credits-label">left</span>
                        {user.credits_used > 0 && (
                          <span className="credits-used" title={`${user.credits_used} credits used`}>
                            ({user.credits_used} used)
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      <div className="metric-cell">
                        <FileText size={16} />
                        <span>{user.script_count}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`source-badge source-${(user.signup_source || 'direct').replace(/[^a-z]/g, '')}`}>
                        {formatSource(user.signup_source)}
                      </span>
                    </td>
                    <td>
                      <div className="date-cell">
                        <Clock size={14} />
                        <span>{formatDate(user.last_active)}</span>
                      </div>
                    </td>
                    <td>
                      <div className="date-cell">
                        <Calendar size={14} />
                        <span>{user.days_since_signup}d</span>
                      </div>
                    </td>
                  </tr>
                  
                  {/* Expanded Detail Row */}
                  {isExpanded && (
                    <tr key={`${user.user_id}-detail`} className="detail-row">
                      <td colSpan={8}>
                        <div className="user-detail-grid">
                          {/* Profile Info */}
                          <div className="detail-section">
                            <h4>Profile</h4>
                            <div className="detail-items">
                              {user.job_title && (
                                <div className="detail-item">
                                  <Briefcase size={14} />
                                  <span>{user.job_title}</span>
                                </div>
                              )}
                              {user.phone && (
                                <div className="detail-item">
                                  <Phone size={14} />
                                  <span>{user.phone}</span>
                                </div>
                              )}
                              <div className="detail-item">
                                <Calendar size={14} />
                                <span>Signed up {new Date(user.created_at).toLocaleDateString()}</span>
                              </div>
                              {user.signup_plan && (
                                <div className="detail-item">
                                  <TrendingUp size={14} />
                                  <span>Plan: {user.signup_plan}</span>
                                </div>
                              )}
                            </div>
                          </div>
                          
                          {/* Credit Economy */}
                          <div className="detail-section">
                            <h4>Credit Economy</h4>
                            <div className="detail-stats">
                              <div className="detail-stat">
                                <span className="detail-stat-value">{user.credits_remaining}</span>
                                <span className="detail-stat-label">Remaining</span>
                              </div>
                              <div className="detail-stat">
                                <span className="detail-stat-value">{user.credits_used}</span>
                                <span className="detail-stat-label">Used</span>
                              </div>
                              <div className="detail-stat">
                                <span className="detail-stat-value">{user.total_credits_bought}</span>
                                <span className="detail-stat-label">Purchased</span>
                              </div>
                              <div className="detail-stat">
                                <span className="detail-stat-value">R{user.total_spent || 0}</span>
                                <span className="detail-stat-label">Total Spent</span>
                              </div>
                            </div>
                          </div>
                          
                          {/* Account Flags */}
                          <div className="detail-section">
                            <h4>Account Flags</h4>
                            <div className="detail-flags">
                              {user.is_legacy_beta && (
                                <span className="flag-badge flag-legacy">
                                  <Star size={12} /> Legacy Beta
                                </span>
                              )}
                              {user.is_superuser && (
                                <span className="flag-badge flag-admin">
                                  <Shield size={12} /> Admin
                                </span>
                              )}
                              {user.script_upload_limit === null ? (
                                <span className="flag-badge flag-unlimited">Unlimited uploads</span>
                              ) : (
                                <span className="flag-badge flag-limited">Limit: {user.script_upload_limit}</span>
                              )}
                              {user.purchase_count > 0 && (
                                <span className="flag-badge flag-buyer">
                                  <CreditCard size={12} /> {user.purchase_count} purchase{user.purchase_count !== 1 ? 's' : ''}
                                </span>
                              )}
                              {user.pending_purchases > 0 && (
                                <span className="flag-badge flag-pending">
                                  {user.pending_purchases} pending
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>

        {users.length === 0 && !loading && (
          <div className="empty-state">
            <Users size={48} />
            <h3>No users found</h3>
            <p>Try adjusting your filters or search query</p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="pagination">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="pagination-button"
          >
            <ChevronLeft size={18} />
            Previous
          </button>
          
          <span className="pagination-info">
            Page {page} of {totalPages}
          </span>
          
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="pagination-button"
          >
            Next
            <ChevronRight size={18} />
          </button>
        </div>
      )}
    </div>
  );
}
