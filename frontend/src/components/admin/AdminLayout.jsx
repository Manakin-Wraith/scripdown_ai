import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  FileText,
  CreditCard,
  Mail,
  MessageSquare,
  Activity,
  ChevronLeft,
  ExternalLink,
  Shield
} from 'lucide-react';
import './AdminLayout.css';

const NAV_ITEMS = [
  { path: '/admin', label: 'Overview', icon: LayoutDashboard, exact: true },
  { path: '/admin/users', label: 'Users', icon: Users },
  { path: '/admin/scripts', label: 'Scripts', icon: FileText },
  { path: '/admin/payments', label: 'Payments', icon: CreditCard, badge: 'pending' },
  { path: '/admin/emails', label: 'Email Campaigns', icon: Mail },
  { path: '/admin/feedback', label: 'Feedback', icon: MessageSquare },
];

export default function AdminLayout({ children, pendingPayments = 0 }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const isActive = (item) => {
    if (item.exact) return location.pathname === item.path;
    return location.pathname.startsWith(item.path);
  };

  return (
    <div className={`admin-layout ${collapsed ? 'admin-layout--collapsed' : ''}`}>
      {/* Sidebar */}
      <aside className="admin-sidebar">
        <div className="admin-sidebar__header">
          <div className="admin-sidebar__brand">
            <Shield size={20} />
            {!collapsed && <span>Admin</span>}
          </div>
          <button
            className="admin-sidebar__collapse"
            onClick={() => setCollapsed(!collapsed)}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <ChevronLeft size={16} className={collapsed ? 'rotated' : ''} />
          </button>
        </div>

        <nav className="admin-sidebar__nav">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = isActive(item);
            const hasBadge = item.badge === 'pending' && pendingPayments > 0;

            return (
              <button
                key={item.path}
                className={`admin-nav-item ${active ? 'admin-nav-item--active' : ''}`}
                onClick={() => navigate(item.path)}
                title={collapsed ? item.label : undefined}
              >
                <div className="admin-nav-item__icon">
                  <Icon size={18} />
                  {hasBadge && collapsed && (
                    <span className="admin-nav-item__dot" />
                  )}
                </div>
                {!collapsed && (
                  <>
                    <span className="admin-nav-item__label">{item.label}</span>
                    {hasBadge && (
                      <span className="admin-nav-item__badge">{pendingPayments}</span>
                    )}
                  </>
                )}
              </button>
            );
          })}
        </nav>

        <div className="admin-sidebar__footer">
          <button
            className="admin-nav-item admin-nav-item--muted"
            onClick={() => navigate('/scripts')}
            title={collapsed ? 'Back to App' : undefined}
          >
            <div className="admin-nav-item__icon">
              <ExternalLink size={18} />
            </div>
            {!collapsed && <span className="admin-nav-item__label">Back to App</span>}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="admin-main">
        {children}
      </main>
    </div>
  );
}
