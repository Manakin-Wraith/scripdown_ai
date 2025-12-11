/**
 * AuthContext - Authentication and User Management
 * 
 * Provides:
 * - User authentication state
 * - Login/Signup/Logout functions
 * - User profile and department info
 * - Department switching
 */

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { 
    supabase, 
    signIn, 
    signUp, 
    signOut, 
    getProfile, 
    getUserDepartments,
    updateProfile,
    joinDepartment,
    leaveDepartment
} from '../lib/supabase';
import { clearAuthCache, getAuthHeaders } from '../services/apiService';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [profile, setProfile] = useState(null);
    const [departments, setDepartments] = useState([]);
    const [activeDepartment, setActiveDepartment] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [autoAcceptedInvites, setAutoAcceptedInvites] = useState([]);
    const hasAutoAccepted = useRef(false);

    // Fetch user profile and departments
    const fetchUserData = useCallback(async (userId) => {
        try {
            // Get profile
            const { data: profileData, error: profileError } = await getProfile(userId);
            if (profileError && profileError.code !== 'PGRST116') {
                console.error('Error fetching profile:', profileError);
            }
            setProfile(profileData);

            // Get departments
            const { data: deptData, error: deptError } = await getUserDepartments(userId);
            if (deptError) {
                console.error('Error fetching departments:', deptError);
            }
            
            const userDepts = deptData || [];
            setDepartments(userDepts);

            // Set active department (primary or first)
            const primaryDept = userDepts.find(d => d.is_primary);
            setActiveDepartment(primaryDept?.department || userDepts[0]?.department || null);

        } catch (err) {
            console.error('Error in fetchUserData:', err);
        }
    }, []);

    // Auto-accept pending invites for the user's email
    const autoAcceptInvites = useCallback(async (session) => {
        if (hasAutoAccepted.current) return;
        hasAutoAccepted.current = true;
        
        try {
            const headers = await getAuthHeaders();
            const response = await fetch(`${API_BASE_URL}/api/invites/auto-accept`, {
                method: 'POST',
                headers
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.accepted && data.accepted.length > 0) {
                    console.log('Auto-accepted invites:', data.accepted);
                    setAutoAcceptedInvites(data.accepted);
                }
            }
        } catch (err) {
            console.error('Error auto-accepting invites:', err);
        }
    }, []);

    // Initialize auth state - OPTIMIZED
    useEffect(() => {
        let isMounted = true;
        
        // Listen for auth changes FIRST (this fires immediately with cached session)
        const { data: { subscription } } = supabase.auth.onAuthStateChange(
            async (event, session) => {
                if (!isMounted) return;
                
                console.log('Auth state change:', event);
                setUser(session?.user ?? null);
                
                if (session?.user) {
                    // Check if we need to create a profile (after email verification)
                    if (event === 'SIGNED_IN') {
                        const pendingName = localStorage.getItem('pending_profile_name');
                        const pendingEmail = localStorage.getItem('pending_profile_email');
                        
                        if (pendingName && pendingEmail === session.user.email) {
                            // Create profile now that email is verified
                            supabase
                                .from('profiles')
                                .upsert({
                                    id: session.user.id,
                                    email: session.user.email,
                                    full_name: pendingName,
                                    created_at: new Date().toISOString(),
                                    updated_at: new Date().toISOString()
                                })
                                .then(({ error: profileError }) => {
                                    if (profileError) {
                                        console.error('Error creating profile:', profileError);
                                    } else {
                                        console.log('Profile created successfully');
                                        // Clear pending data
                                        localStorage.removeItem('pending_profile_name');
                                        localStorage.removeItem('pending_profile_email');
                                        // Refresh user data to get the new profile
                                        fetchUserData(session.user.id);
                                    }
                                });
                        }
                        
                        // Auto-accept pending invites on sign in (after email verification)
                        autoAcceptInvites(session).catch(console.error);
                    }
                    
                    // Fetch user data in background, don't block
                    fetchUserData(session.user.id).catch(console.error);
                } else {
                    setProfile(null);
                    setDepartments([]);
                    setActiveDepartment(null);
                    hasAutoAccepted.current = false; // Reset for next login
                }
                
                // Auth is ready as soon as we know the session state
                setLoading(false);
            }
        );
        
        // Fallback timeout - only if onAuthStateChange doesn't fire
        const timeout = setTimeout(() => {
            if (isMounted && loading) {
                console.warn('Auth fallback: setting loading false');
                setLoading(false);
            }
        }, 3000); // 3 second fallback

        return () => {
            isMounted = false;
            clearTimeout(timeout);
            subscription.unsubscribe();
        };
    }, [fetchUserData, autoAcceptInvites, loading]);

    // Login
    const login = async (email, password) => {
        setError(null);
        setLoading(true);
        
        const { data, error } = await signIn(email, password);
        
        if (error) {
            setError(error.message);
            setLoading(false);
            return { success: false, error: error.message };
        }
        
        return { success: true, data };
    };

    // Signup
    const signup = async (email, password, fullName) => {
        setError(null);
        setLoading(true);
        
        const { data, error } = await signUp(email, password);
        
        if (error) {
            setError(error.message);
            setLoading(false);
            return { success: false, error: error.message };
        }

        // Store full name in localStorage for profile creation after email verification
        // Profile will be created when user verifies email and signs in
        if (data.user) {
            localStorage.setItem('pending_profile_name', fullName);
            localStorage.setItem('pending_profile_email', email);
            
            // Send welcome email with Yoco paylink (fire and forget)
            try {
                fetch(`${API_BASE_URL}/api/auth/welcome-email`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, full_name: fullName })
                }).catch(err => console.error('Welcome email error:', err));
            } catch (err) {
                console.error('Failed to send welcome email:', err);
            }
        }
        
        setLoading(false);
        return { success: true, data };
    };

    // Logout - OPTIMIZED (instant UI update)
    const logout = async () => {
        // Clear state immediately for instant UI feedback
        clearAuthCache();
        setUser(null);
        setProfile(null);
        setDepartments([]);
        setActiveDepartment(null);
        
        // Sign out in background (don't wait)
        signOut().catch(err => console.error('Logout error:', err));
        
        return { success: true };
    };

    // Update user profile
    const updateUserProfile = async (updates) => {
        if (!user) return { success: false, error: 'Not authenticated' };
        
        const { data, error } = await updateProfile(user.id, updates);
        
        if (error) {
            return { success: false, error: error.message };
        }
        
        setProfile(data);
        return { success: true, data };
    };

    // Join a department
    const joinUserDepartment = async (departmentId, role = 'member', isPrimary = false) => {
        if (!user) return { success: false, error: 'Not authenticated' };
        
        const { data, error } = await joinDepartment(user.id, departmentId, role, isPrimary);
        
        if (error) {
            return { success: false, error: error.message };
        }
        
        // Refresh departments
        await fetchUserData(user.id);
        return { success: true, data };
    };

    // Leave a department
    const leaveUserDepartment = async (departmentId) => {
        if (!user) return { success: false, error: 'Not authenticated' };
        
        const { error } = await leaveDepartment(user.id, departmentId);
        
        if (error) {
            return { success: false, error: error.message };
        }
        
        // Refresh departments
        await fetchUserData(user.id);
        return { success: true };
    };

    // Switch active department
    const switchDepartment = (department) => {
        setActiveDepartment(department);
        // Store in localStorage for persistence
        localStorage.setItem('activeDepartmentId', department.id);
    };

    // Check if user is in a specific department
    const isInDepartment = (departmentId) => {
        return departments.some(d => d.department_id === departmentId);
    };

    // Check if user is department head
    const isDepartmentHead = (departmentId) => {
        const membership = departments.find(d => d.department_id === departmentId);
        return membership?.role === 'head';
    };

    const value = {
        // State
        user,
        profile,
        departments,
        activeDepartment,
        loading,
        error,
        isAuthenticated: !!user,
        autoAcceptedInvites,
        
        // Actions
        login,
        signup,
        logout,
        updateUserProfile,
        joinUserDepartment,
        leaveUserDepartment,
        switchDepartment,
        refreshUserData: () => user && fetchUserData(user.id),
        clearAutoAcceptedInvites: () => setAutoAcceptedInvites([]),
        
        // Helpers
        isInDepartment,
        isDepartmentHead
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};

/**
 * Hook to use auth context
 */
export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export default AuthContext;
