/**
 * SettingsPage - User Settings Management
 * 
 * Sections:
 * - Account (email, password)
 * - Appearance (theme)
 * - Notifications
 * - Script Defaults
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
    ArrowLeft, 
    User, 
    Palette, 
    Bell, 
    FileText,
    Lock,
    Mail,
    Check,
    AlertCircle,
    Moon,
    Sun,
    Monitor,
    Loader
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { supabase } from '../lib/supabase';
import { useToast } from '../context/ToastContext';
import './SettingsPage.css';

const SettingsPage = () => {
    const navigate = useNavigate();
    const { user, profile } = useAuth();
    const { showToast } = useToast();
    
    // Active tab
    const [activeTab, setActiveTab] = useState('account');
    
    // Account settings state
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [passwordLoading, setPasswordLoading] = useState(false);
    const [passwordError, setPasswordError] = useState('');
    const [passwordSuccess, setPasswordSuccess] = useState(false);
    
    // Appearance settings
    const [theme, setTheme] = useState(() => {
        return localStorage.getItem('theme') || 'dark';
    });
    
    // Notification settings
    const [notifications, setNotifications] = useState({
        analysisComplete: true,
        reportShared: true,
        weeklyDigest: false
    });
    
    // Script defaults
    const [scriptDefaults, setScriptDefaults] = useState({
        autoAnalyze: true,
        pageFormat: 'us-letter',
        analysisDepth: 'standard'
    });

    // Handle password change
    const handlePasswordChange = async (e) => {
        e.preventDefault();
        setPasswordError('');
        setPasswordSuccess(false);
        
        if (newPassword !== confirmPassword) {
            setPasswordError('New passwords do not match');
            return;
        }
        
        if (newPassword.length < 6) {
            setPasswordError('Password must be at least 6 characters');
            return;
        }
        
        setPasswordLoading(true);
        
        try {
            const { error } = await supabase.auth.updateUser({
                password: newPassword
            });
            
            if (error) throw error;
            
            setPasswordSuccess(true);
            setCurrentPassword('');
            setNewPassword('');
            setConfirmPassword('');
            showToast('Password updated successfully', 'success');
        } catch (error) {
            setPasswordError(error.message);
        } finally {
            setPasswordLoading(false);
        }
    };
    
    // Handle theme change
    const handleThemeChange = (newTheme) => {
        setTheme(newTheme);
        localStorage.setItem('theme', newTheme);
        
        // Apply theme to document
        document.documentElement.setAttribute('data-theme', newTheme);
        showToast(`Theme changed to ${newTheme}`, 'success');
    };
    
    // Handle notification toggle
    const handleNotificationToggle = (key) => {
        setNotifications(prev => ({
            ...prev,
            [key]: !prev[key]
        }));
        showToast('Notification preference saved', 'success');
    };
    
    // Handle script default change
    const handleScriptDefaultChange = (key, value) => {
        setScriptDefaults(prev => ({
            ...prev,
            [key]: value
        }));
        showToast('Default setting saved', 'success');
    };

    const tabs = [
        { id: 'account', label: 'Account', icon: User },
        { id: 'appearance', label: 'Appearance', icon: Palette },
        { id: 'notifications', label: 'Notifications', icon: Bell },
        { id: 'defaults', label: 'Script Defaults', icon: FileText }
    ];

    return (
        <div className="settings-page">
            {/* Header */}
            <header className="settings-header">
                <button className="back-button" onClick={() => navigate(-1)}>
                    <ArrowLeft size={20} />
                    <span>Back</span>
                </button>
                <h1>Settings</h1>
            </header>

            <div className="settings-container">
                {/* Sidebar Navigation */}
                <nav className="settings-nav">
                    {tabs.map(tab => (
                        <button
                            key={tab.id}
                            className={`nav-item ${activeTab === tab.id ? 'active' : ''}`}
                            onClick={() => setActiveTab(tab.id)}
                        >
                            <tab.icon size={18} />
                            <span>{tab.label}</span>
                        </button>
                    ))}
                </nav>

                {/* Content Area */}
                <main className="settings-content">
                    {/* Account Settings */}
                    {activeTab === 'account' && (
                        <section className="settings-section">
                            <h2>Account Settings</h2>
                            
                            {/* Email Display */}
                            <div className="setting-group">
                                <label className="setting-label">
                                    <Mail size={16} />
                                    Email Address
                                </label>
                                <div className="email-display">
                                    <span>{user?.email}</span>
                                    <span className="verified-badge">
                                        <Check size={12} />
                                        Verified
                                    </span>
                                </div>
                            </div>
                            
                            {/* Password Change */}
                            <div className="setting-group">
                                <label className="setting-label">
                                    <Lock size={16} />
                                    Change Password
                                </label>
                                
                                <form onSubmit={handlePasswordChange} className="password-form">
                                    {passwordError && (
                                        <div className="form-error">
                                            <AlertCircle size={14} />
                                            {passwordError}
                                        </div>
                                    )}
                                    
                                    {passwordSuccess && (
                                        <div className="form-success">
                                            <Check size={14} />
                                            Password updated successfully
                                        </div>
                                    )}
                                    
                                    <input
                                        type="password"
                                        placeholder="Current password"
                                        value={currentPassword}
                                        onChange={(e) => setCurrentPassword(e.target.value)}
                                        className="form-input"
                                    />
                                    
                                    <input
                                        type="password"
                                        placeholder="New password"
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        className="form-input"
                                    />
                                    
                                    <input
                                        type="password"
                                        placeholder="Confirm new password"
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        className="form-input"
                                    />
                                    
                                    <button 
                                        type="submit" 
                                        className="btn-primary"
                                        disabled={passwordLoading || !newPassword || !confirmPassword}
                                    >
                                        {passwordLoading ? (
                                            <>
                                                <Loader size={16} className="spin" />
                                                Updating...
                                            </>
                                        ) : (
                                            'Update Password'
                                        )}
                                    </button>
                                </form>
                            </div>
                        </section>
                    )}

                    {/* Appearance Settings */}
                    {activeTab === 'appearance' && (
                        <section className="settings-section">
                            <h2>Appearance</h2>
                            
                            <div className="setting-group">
                                <label className="setting-label">Theme</label>
                                <p className="setting-description">
                                    Choose how SlateOne looks to you
                                </p>
                                
                                <div className="theme-options">
                                    <button
                                        className={`theme-option ${theme === 'light' ? 'active' : ''}`}
                                        onClick={() => handleThemeChange('light')}
                                    >
                                        <Sun size={24} />
                                        <span>Light</span>
                                    </button>
                                    
                                    <button
                                        className={`theme-option ${theme === 'dark' ? 'active' : ''}`}
                                        onClick={() => handleThemeChange('dark')}
                                    >
                                        <Moon size={24} />
                                        <span>Dark</span>
                                    </button>
                                    
                                    <button
                                        className={`theme-option ${theme === 'system' ? 'active' : ''}`}
                                        onClick={() => handleThemeChange('system')}
                                    >
                                        <Monitor size={24} />
                                        <span>System</span>
                                    </button>
                                </div>
                            </div>
                        </section>
                    )}

                    {/* Notification Settings */}
                    {activeTab === 'notifications' && (
                        <section className="settings-section">
                            <h2>Notifications</h2>
                            
                            <div className="setting-group">
                                <div className="toggle-setting">
                                    <div className="toggle-info">
                                        <span className="toggle-label">Analysis Complete</span>
                                        <span className="toggle-description">
                                            Get notified when script analysis finishes
                                        </span>
                                    </div>
                                    <button
                                        className={`toggle-switch ${notifications.analysisComplete ? 'on' : ''}`}
                                        onClick={() => handleNotificationToggle('analysisComplete')}
                                    >
                                        <span className="toggle-thumb" />
                                    </button>
                                </div>
                                
                                <div className="toggle-setting">
                                    <div className="toggle-info">
                                        <span className="toggle-label">Report Shared</span>
                                        <span className="toggle-description">
                                            Get notified when someone views your shared report
                                        </span>
                                    </div>
                                    <button
                                        className={`toggle-switch ${notifications.reportShared ? 'on' : ''}`}
                                        onClick={() => handleNotificationToggle('reportShared')}
                                    >
                                        <span className="toggle-thumb" />
                                    </button>
                                </div>
                                
                                <div className="toggle-setting">
                                    <div className="toggle-info">
                                        <span className="toggle-label">Weekly Digest</span>
                                        <span className="toggle-description">
                                            Receive a weekly summary of your activity
                                        </span>
                                    </div>
                                    <button
                                        className={`toggle-switch ${notifications.weeklyDigest ? 'on' : ''}`}
                                        onClick={() => handleNotificationToggle('weeklyDigest')}
                                    >
                                        <span className="toggle-thumb" />
                                    </button>
                                </div>
                            </div>
                        </section>
                    )}

                    {/* Script Defaults */}
                    {activeTab === 'defaults' && (
                        <section className="settings-section">
                            <h2>Script Defaults</h2>
                            
                            <div className="setting-group">
                                <div className="toggle-setting">
                                    <div className="toggle-info">
                                        <span className="toggle-label">Auto-Analyze on Upload</span>
                                        <span className="toggle-description">
                                            Automatically start analysis when uploading a script
                                        </span>
                                    </div>
                                    <button
                                        className={`toggle-switch ${scriptDefaults.autoAnalyze ? 'on' : ''}`}
                                        onClick={() => handleScriptDefaultChange('autoAnalyze', !scriptDefaults.autoAnalyze)}
                                    >
                                        <span className="toggle-thumb" />
                                    </button>
                                </div>
                            </div>
                            
                            <div className="setting-group">
                                <label className="setting-label">Page Format</label>
                                <select
                                    value={scriptDefaults.pageFormat}
                                    onChange={(e) => handleScriptDefaultChange('pageFormat', e.target.value)}
                                    className="form-select"
                                >
                                    <option value="us-letter">US Letter (8.5" × 11")</option>
                                    <option value="a4">A4 (210mm × 297mm)</option>
                                </select>
                            </div>
                            
                            <div className="setting-group">
                                <label className="setting-label">Analysis Depth</label>
                                <p className="setting-description">
                                    Controls how detailed the AI analysis will be
                                </p>
                                <select
                                    value={scriptDefaults.analysisDepth}
                                    onChange={(e) => handleScriptDefaultChange('analysisDepth', e.target.value)}
                                    className="form-select"
                                >
                                    <option value="quick">Quick (faster, less detail)</option>
                                    <option value="standard">Standard (balanced)</option>
                                    <option value="detailed">Detailed (slower, more thorough)</option>
                                </select>
                            </div>
                        </section>
                    )}
                </main>
            </div>
        </div>
    );
};

export default SettingsPage;
