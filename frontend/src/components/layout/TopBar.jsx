import React, { useState, useRef, useEffect } from 'react';
import { NavLink, Link, useNavigate } from 'react-router-dom';
import { 
  Library, 
  Settings, 
  LogOut,
  ChevronDown,
  User,
  Loader,
  Film,
  LogIn,
  Shield
} from 'lucide-react';
import { useAnalysis } from '../../context/AnalysisContext';
import { useAuth } from '../../context/AuthContext';
import NotificationBell from '../notifications/NotificationBell';
import { CreditBalance, CreditPurchaseModal } from '../credits';
import './Layout.css';

const TopBar = () => {
  const navigate = useNavigate();
  const { globalStatus, hasActiveAnalysis } = useAnalysis();
  const { user, profile, isAuthenticated, logout, loading: authLoading } = useAuth();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [showCreditPurchaseModal, setShowCreditPurchaseModal] = useState(false);
  const menuRef = useRef(null);
  
  // Check if user is superuser (from profile table)
  const isSuperuser = profile?.is_superuser === true;

  // Get user initials
  const getInitials = () => {
    if (profile?.full_name) {
      return profile.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    }
    if (user?.email) {
      return user.email[0].toUpperCase();
    }
    return 'U';
  };

  const handleLogout = async () => {
    await logout();
    setUserMenuOpen(false);
  };

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="topbar">
      {/* Left: Logo + Nav */}
      <div className="topbar-left">
        <Link to="/" className="topbar-brand">
          <div className="logo-icon"><Film size={24} /></div>
          <span className="logo-text">Slate<span className="accent">One</span></span>
        </Link>

        <nav className="topbar-nav">
          <NavLink 
            to="/scripts" 
            className={({ isActive }) => `topbar-nav-item ${isActive ? 'active' : ''}`}
          >
            <Library size={18} />
            <span>My Scripts</span>
          </NavLink>
          
          {/* Admin Button - only show for superusers */}
          {isSuperuser && (
            <NavLink 
              to="/admin" 
              className={({ isActive }) => `topbar-nav-item ${isActive ? 'active' : ''}`}
            >
              <Shield size={18} />
              <span>Admin</span>
            </NavLink>
          )}
          
          {/* Credit Balance - only show when authenticated */}
          {isAuthenticated && (
            <div className="topbar-credits">
              <CreditBalance 
                compact={true}
                onClick={() => setShowCreditPurchaseModal(true)}
              />
            </div>
          )}
        </nav>
      </div>

      {/* Right: Analysis Status + User Menu */}
      <div className="topbar-right">
        {/* Global Analysis Status Indicator */}
        {hasActiveAnalysis && (
          <div className="analysis-indicator">
            <Loader size={16} className="spin" />
            <span>Analyzing...</span>
          </div>
        )}

        {/* Notification Bell - only show when authenticated */}
        {isAuthenticated && <NotificationBell />}

        {/* User Dropdown or Login Button */}
        {authLoading ? (
          <div className="auth-loading">
            <Loader size={18} className="spin" />
          </div>
        ) : isAuthenticated ? (
          <div className="user-menu-container" ref={menuRef}>
            <button 
              className="user-menu-trigger"
              onClick={() => setUserMenuOpen(!userMenuOpen)}
            >
              <div className="user-avatar-sm">{getInitials()}</div>
              <ChevronDown size={16} className={`chevron ${userMenuOpen ? 'open' : ''}`} />
            </button>

            {userMenuOpen && (
              <div className="user-dropdown">
                <div className="dropdown-header">
                  <div className="user-avatar">{getInitials()}</div>
                  <div className="user-info">
                    <span className="user-name">{profile?.full_name || user?.email}</span>
                    <span className="user-plan">{user?.email}</span>
                  </div>
                </div>
                <div className="dropdown-divider"></div>
                <button 
                  className="dropdown-item"
                  onClick={() => { navigate('/profile'); setUserMenuOpen(false); }}
                >
                  <User size={16} />
                  <span>Profile</span>
                </button>
                {/* Phase 2+: Settings button - deferred
                <button 
                  className="dropdown-item"
                  onClick={() => { navigate('/settings'); setUserMenuOpen(false); }}
                >
                  <Settings size={16} />
                  <span>Settings</span>
                </button>
                */}
                <div className="dropdown-divider"></div>
                <button className="dropdown-item logout" onClick={handleLogout}>
                  <LogOut size={16} />
                  <span>Log out</span>
                </button>
              </div>
            )}
          </div>
        ) : (
          <button 
            className="login-btn"
            onClick={() => navigate('/login')}
          >
            <LogIn size={18} />
            <span>Sign In</span>
          </button>
        )}
      </div>
      
      <CreditPurchaseModal
        isOpen={showCreditPurchaseModal}
        onClose={() => setShowCreditPurchaseModal(false)}
      />
    </header>
  );
};

export default TopBar;
