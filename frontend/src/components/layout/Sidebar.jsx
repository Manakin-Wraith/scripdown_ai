import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  UploadCloud, 
  Library, 
  Settings, 
  PanelLeftClose,
  PanelLeftOpen,
  LogOut,
  Film
} from 'lucide-react';
import './Layout.css';

const Sidebar = ({ isCollapsed, toggleSidebar }) => {
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
            to="/" 
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            title={isCollapsed ? "Dashboard" : ""}
            end
          >
            <LayoutDashboard size={20} />
            {!isCollapsed && <span>Dashboard</span>}
          </NavLink>
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

        <div className="nav-section mt-auto">
          {!isCollapsed && <p className="nav-label">SYSTEM</p>}
          <a href="#" className="nav-item" title={isCollapsed ? "Settings" : ""}>
            <Settings size={20} />
            {!isCollapsed && <span>Settings</span>}
          </a>
        </div>
      </nav>

      <div className="sidebar-footer">
        <div className="user-profile">
          <div className="user-avatar">JD</div>
          {!isCollapsed && (
            <div className="user-info">
              <span className="user-name">John Doe</span>
              <span className="user-role">Pro Plan</span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
