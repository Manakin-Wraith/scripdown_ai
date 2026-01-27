import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  Search, 
  Filter,
  ChevronLeft,
  ChevronRight,
  Users,
  FileText,
  Calendar,
  AlertCircle
} from 'lucide-react';
import { getUserAnalytics } from '../../services/apiService';
import './UserActivityPage.css';

/**
 * User Activity Page - Detailed user list with filtering and search
 * Route: /admin/users
 */
export default function UserActivityPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  
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
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return date.toLocaleDateString();
  };

  const totalPages = Math.ceil(total / limit);

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
              <th>User</th>
              <th>Status</th>
              <th>Scripts</th>
              <th>Last Active</th>
              <th>Member Since</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.user_id} onClick={() => {/* TODO: Open user detail modal */}}>
                <td>
                  <div className="user-cell">
                    <div className="user-avatar">
                      {user.name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div className="user-name">{user.name}</div>
                      <div className="user-email">{user.email}</div>
                    </div>
                  </div>
                </td>
                <td>
                  <span className={`status-badge status-${user.subscription_status}`}>
                    {user.subscription_status}
                  </span>
                </td>
                <td>
                  <div className="metric-cell">
                    <FileText size={16} />
                    <span>{user.script_count}</span>
                  </div>
                </td>
                <td>
                  <div className="date-cell">
                    <Calendar size={16} />
                    <span>{formatDate(user.last_active)}</span>
                  </div>
                </td>
                <td>
                  <div className="date-cell">
                    <Users size={16} />
                    <span>{user.days_since_signup} days ago</span>
                  </div>
                </td>
              </tr>
            ))}
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
