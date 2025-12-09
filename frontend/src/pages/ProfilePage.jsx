/**
 * ProfilePage - User Profile & Settings
 * 
 * Displays user information, avatar, department memberships,
 * and allows editing profile details.
 */

import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
    User, 
    Mail, 
    Camera,
    Building2,
    Shield,
    Save,
    Loader,
    AlertCircle,
    CheckCircle,
    ArrowLeft,
    Crown,
    Users
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { supabase } from '../lib/supabase';
import './ProfilePage.css';

const ProfilePage = () => {
    const navigate = useNavigate();
    const fileInputRef = useRef(null);
    const { 
        user, 
        profile, 
        departments, 
        updateUserProfile, 
        refreshUserData,
        isAuthenticated,
        loading: authLoading 
    } = useAuth();
    
    const [fullName, setFullName] = useState(profile?.full_name || '');
    const [jobTitle, setJobTitle] = useState(profile?.job_title || '');
    const [phone, setPhone] = useState(profile?.phone || '');
    const [saving, setSaving] = useState(false);
    const [uploadingAvatar, setUploadingAvatar] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);

    // Sync form with profile when it loads
    React.useEffect(() => {
        if (profile) {
            setFullName(profile.full_name || '');
            setJobTitle(profile.job_title || '');
            setPhone(profile.phone || '');
        }
    }, [profile]);

    // Redirect if not authenticated
    React.useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            navigate('/login', { state: { from: { pathname: '/profile' } } });
        }
    }, [isAuthenticated, authLoading, navigate]);

    const handleSaveProfile = async (e) => {
        e.preventDefault();
        setError(null);
        setSuccess(null);
        setSaving(true);

        try {
            const result = await updateUserProfile({
                full_name: fullName.trim(),
                job_title: jobTitle.trim(),
                phone: phone.trim(),
                updated_at: new Date().toISOString()
            });

            if (result.success) {
                setSuccess('Profile updated successfully!');
            } else {
                setError(result.error || 'Failed to update profile');
            }
        } catch (err) {
            setError(err.message || 'An error occurred');
        } finally {
            setSaving(false);
        }
    };

    const handleAvatarClick = () => {
        fileInputRef.current?.click();
    };

    const handleAvatarChange = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        // Validate file type
        if (!file.type.startsWith('image/')) {
            setError('Please select an image file');
            return;
        }

        // Validate file size (max 2MB)
        if (file.size > 2 * 1024 * 1024) {
            setError('Image must be less than 2MB');
            return;
        }

        setError(null);
        setUploadingAvatar(true);

        try {
            // Create unique filename
            const fileExt = file.name.split('.').pop();
            const fileName = `${user.id}-${Date.now()}.${fileExt}`;
            const filePath = `avatars/${fileName}`;

            // Upload to Supabase Storage
            const { error: uploadError } = await supabase.storage
                .from('avatars')
                .upload(filePath, file, { upsert: true });

            if (uploadError) {
                throw uploadError;
            }

            // Get public URL
            const { data: { publicUrl } } = supabase.storage
                .from('avatars')
                .getPublicUrl(filePath);

            // Update profile with new avatar URL
            const result = await updateUserProfile({
                avatar_url: publicUrl,
                updated_at: new Date().toISOString()
            });

            if (result.success) {
                setSuccess('Avatar updated!');
                await refreshUserData();
            } else {
                throw new Error(result.error);
            }
        } catch (err) {
            console.error('Avatar upload error:', err);
            setError(err.message || 'Failed to upload avatar');
        } finally {
            setUploadingAvatar(false);
        }
    };

    const getInitials = () => {
        if (profile?.full_name) {
            return profile.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
        }
        if (user?.email) {
            return user.email[0].toUpperCase();
        }
        return 'U';
    };

    // Loading state
    if (authLoading) {
        return (
            <div className="profile-page">
                <div className="profile-loading">
                    <Loader size={32} className="spin" />
                    <p>Loading profile...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="profile-page">
            <div className="profile-container">
                {/* Header */}
                <div className="profile-header">
                    <button className="back-btn" onClick={() => navigate(-1)}>
                        <ArrowLeft size={20} />
                        <span>Back</span>
                    </button>
                    <h1>My Profile</h1>
                </div>

                {/* Messages */}
                {error && (
                    <div className="profile-message error">
                        <AlertCircle size={18} />
                        <span>{error}</span>
                    </div>
                )}
                {success && (
                    <div className="profile-message success">
                        <CheckCircle size={18} />
                        <span>{success}</span>
                    </div>
                )}

                <div className="profile-content">
                    {/* Left Column - Avatar & Quick Info */}
                    <div className="profile-sidebar">
                        <div className="avatar-section">
                            <div 
                                className="avatar-large"
                                onClick={handleAvatarClick}
                                style={profile?.avatar_url ? { backgroundImage: `url(${profile.avatar_url})` } : {}}
                            >
                                {!profile?.avatar_url && getInitials()}
                                <div className="avatar-overlay">
                                    {uploadingAvatar ? (
                                        <Loader size={24} className="spin" />
                                    ) : (
                                        <Camera size={24} />
                                    )}
                                </div>
                            </div>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/*"
                                onChange={handleAvatarChange}
                                style={{ display: 'none' }}
                            />
                            <p className="avatar-hint">Click to change avatar</p>
                        </div>

                        <div className="quick-info">
                            <div className="info-item">
                                <Mail size={16} />
                                <span>{user?.email}</span>
                            </div>
                            <div className="info-item">
                                <Shield size={16} />
                                <span>Member since {new Date(user?.created_at).toLocaleDateString()}</span>
                            </div>
                        </div>
                    </div>

                    {/* Right Column - Form & Departments */}
                    <div className="profile-main">
                        {/* Profile Form */}
                        <div className="profile-card">
                            <h2>
                                <User size={20} />
                                Personal Information
                            </h2>
                            <form onSubmit={handleSaveProfile}>
                                <div className="form-group">
                                    <label htmlFor="fullName">Full Name</label>
                                    <input
                                        id="fullName"
                                        type="text"
                                        value={fullName}
                                        onChange={(e) => setFullName(e.target.value)}
                                        placeholder="Your full name"
                                    />
                                </div>

                                <div className="form-group">
                                    <label htmlFor="email">Email</label>
                                    <input
                                        id="email"
                                        type="email"
                                        value={user?.email || ''}
                                        disabled
                                        className="disabled"
                                    />
                                    <span className="form-hint">Email cannot be changed</span>
                                </div>

                                <div className="form-row">
                                    <div className="form-group">
                                        <label htmlFor="jobTitle">Job Title</label>
                                        <input
                                            id="jobTitle"
                                            type="text"
                                            value={jobTitle}
                                            onChange={(e) => setJobTitle(e.target.value)}
                                            placeholder="e.g. Production Designer"
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label htmlFor="phone">Phone</label>
                                        <input
                                            id="phone"
                                            type="tel"
                                            value={phone}
                                            onChange={(e) => setPhone(e.target.value)}
                                            placeholder="+1 (555) 000-0000"
                                        />
                                    </div>
                                </div>

                                <button 
                                    type="submit" 
                                    className="save-btn"
                                    disabled={saving}
                                >
                                    {saving ? (
                                        <>
                                            <Loader size={18} className="spin" />
                                            Saving...
                                        </>
                                    ) : (
                                        <>
                                            <Save size={18} />
                                            Save Changes
                                        </>
                                    )}
                                </button>
                            </form>
                        </div>

                        {/* Departments */}
                        <div className="profile-card">
                            <h2>
                                <Building2 size={20} />
                                My Departments
                            </h2>
                            {departments.length > 0 ? (
                                <div className="departments-list">
                                    {departments.map((membership) => (
                                        <div key={membership.id} className="department-item">
                                            <div className="dept-info">
                                                <span 
                                                    className="dept-color" 
                                                    style={{ background: membership.department?.color || '#6366F1' }}
                                                />
                                                <div className="dept-details">
                                                    <span className="dept-name">
                                                        {membership.department?.name || 'Unknown'}
                                                    </span>
                                                    <span className="dept-code">
                                                        {membership.department?.code}
                                                    </span>
                                                </div>
                                            </div>
                                            <div className="dept-role">
                                                {membership.role === 'head' ? (
                                                    <span className="role-badge head">
                                                        <Crown size={14} />
                                                        Head
                                                    </span>
                                                ) : (
                                                    <span className="role-badge member">
                                                        <Users size={14} />
                                                        Member
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="no-departments">
                                    <Building2 size={32} />
                                    <p>You haven't joined any departments yet.</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ProfilePage;
