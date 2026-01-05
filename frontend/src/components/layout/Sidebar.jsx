import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  UploadCloud, 
  Library, 
  Settings, 
  PanelLeftClose,
  PanelLeftOpen,
  Film,
  Users,
  FileText,
  Clock
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import './Layout.css';

const Sidebar = ({ isCollapsed, toggleSidebar }) => {
  const { user } = useAuth();
  
  // Get user initials for avatar
  const getInitials = () => {
    if (!user) return 'U';
    const name = user.user_metadata?.full_name || user.email || '';
    if (name.includes('@')) {
      return name.charAt(0).toUpperCase();
    }
    const parts = name.split(' ');
    return parts.map(p => p.charAt(0).toUpperCase()).slice(0, 2).join('');
  };

  return (
    <aside className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="logo-container">
          <div className="logo-icon"><Film size={24} /></div>
          {!isCollapsed && <span className="logo-text">Slate<span className="accent">One</span></span>}
        </div>
        <button 
          className="collapse-btn" 
          onClick={toggleSidebar}
          title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {isCollapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}
        </button>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section">
          {!isCollapsed && <p className="nav-label">MENU</p>}
          <NavLink 
            to="/upload" 
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            title={isCollapsed ? "Upload Script" : ""}
          >
            <UploadCloud size={20} />
            {!isCollapsed && <span>Upload Script</span>}
          </NavLink>
          <NavLink 
            to="/scripts" 
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            title={isCollapsed ? "My Scripts" : ""}
          >
            <Library size={20} />
            {!isCollapsed && <span>My Scripts</span>}
          </NavLink>
        </div>

        {/* Coming Soon Section */}
        <div className="nav-section">
          {!isCollapsed && <p className="nav-label">COMING SOON</p>}
          <div className="nav-item disabled" title={isCollapsed ? "Reports (Coming Soon)" : ""}>
            <FileText size={20} />
            {!isCollapsed && (
              <>
                <span>Reports</span>
                <span className="coming-soon-badge"><Clock size={12} /></span>
              </>
            )}
          </div>
          <div className="nav-item disabled" title={isCollapsed ? "Team (Coming Soon)" : ""}>
            <Users size={20} />
            {!isCollapsed && (
              <>
                <span>Team</span>
                <span className="coming-soon-badge"><Clock size={12} /></span>
              </>
            )}
          </div>
          <div className="nav-item disabled" title={isCollapsed ? "Settings (Coming Soon)" : ""}>
            <Settings size={20} />
            {!isCollapsed && (
              <>
                <span>Settings</span>
                <span className="coming-soon-badge"><Clock size={12} /></span>
              </>
            )}
          </div>
        </div>
      </nav>

      <div className="sidebar-footer">
        <NavLink to="/profile" className="user-profile">
          <div className="user-avatar">{getInitials()}</div>
          {!isCollapsed && (
            <div className="user-info">
              <span className="user-name">{user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'User'}</span>
              <span className="user-role">Beta Access</span>
            </div>
          )}
        </NavLink>
      </div>
    </aside>
  );
};

export default Sidebar;
