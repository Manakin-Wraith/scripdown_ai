/**
 * Supabase Client for SlateOne
 * 
 * This module provides the Supabase client for frontend operations.
 */

import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
    console.error('Missing Supabase environment variables');
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// ============================================
// Auth Helpers
// ============================================

export const signUp = async (email, password) => {
    const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
            emailRedirectTo: `${window.location.origin}/auth/callback`
        }
    });
    return { data, error };
};

export const signIn = async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
    });
    return { data, error };
};

export const signOut = async () => {
    const { error } = await supabase.auth.signOut();
    return { error };
};

export const getCurrentUser = async () => {
    const { data: { user } } = await supabase.auth.getUser();
    return user;
};

export const onAuthStateChange = (callback) => {
    return supabase.auth.onAuthStateChange(callback);
};

/**
 * Request a password reset email
 * @param {string} email - User's email address
 * @returns {Promise<{data: any, error: any}>}
 */
export const resetPassword = async (email) => {
    const { data, error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`
    });
    return { data, error };
};

/**
 * Update user's password (must be called after user clicks reset link)
 * @param {string} newPassword - New password
 * @returns {Promise<{data: any, error: any}>}
 */
export const updatePassword = async (newPassword) => {
    const { data, error } = await supabase.auth.updateUser({
        password: newPassword
    });
    return { data, error };
};

/**
 * Resend email verification
 * @param {string} email - User's email address
 * @returns {Promise<{data: any, error: any}>}
 */
export const resendVerificationEmail = async (email) => {
    const { data, error } = await supabase.auth.resend({
        type: 'signup',
        email
    });
    return { data, error };
};

// ============================================
// Script Operations
// ============================================

export const getScripts = async () => {
    const { data, error } = await supabase
        .from('scripts')
        .select('*')
        .order('created_at', { ascending: false });
    return { data, error };
};

export const getScript = async (scriptId) => {
    const { data, error } = await supabase
        .from('scripts')
        .select('*')
        .eq('id', scriptId)
        .single();
    return { data, error };
};

export const createScript = async (scriptData) => {
    const { data, error } = await supabase
        .from('scripts')
        .insert(scriptData)
        .select()
        .single();
    return { data, error };
};

export const updateScript = async (scriptId, updates) => {
    const { data, error } = await supabase
        .from('scripts')
        .update(updates)
        .eq('id', scriptId)
        .select()
        .single();
    return { data, error };
};

export const deleteScript = async (scriptId) => {
    const { error } = await supabase
        .from('scripts')
        .delete()
        .eq('id', scriptId);
    return { error };
};

// ============================================
// Scene Operations
// ============================================

export const getScenes = async (scriptId) => {
    const { data, error } = await supabase
        .from('scenes')
        .select('*')
        .eq('script_id', scriptId)
        .order('scene_order');
    return { data, error };
};

export const getScene = async (sceneId) => {
    const { data, error } = await supabase
        .from('scenes')
        .select('*')
        .eq('id', sceneId)
        .single();
    return { data, error };
};

export const createScene = async (sceneData) => {
    const { data, error } = await supabase
        .from('scenes')
        .insert(sceneData)
        .select()
        .single();
    return { data, error };
};

export const updateScene = async (sceneId, updates) => {
    const { data, error } = await supabase
        .from('scenes')
        .update(updates)
        .eq('id', sceneId)
        .select()
        .single();
    return { data, error };
};

export const deleteScene = async (sceneId) => {
    const { error } = await supabase
        .from('scenes')
        .delete()
        .eq('id', sceneId);
    return { error };
};

// Create scene from text selection (for manual scene labeling)
export const createSceneFromSelection = async (scriptId, selectionData) => {
    // Get current max scene_order
    const { data: existingScenes } = await supabase
        .from('scenes')
        .select('scene_order')
        .eq('script_id', scriptId)
        .order('scene_order', { ascending: false })
        .limit(1);
    
    const nextOrder = existingScenes?.length > 0 
        ? existingScenes[0].scene_order + 1 
        : 1;
    
    const sceneData = {
        script_id: scriptId,
        scene_number: selectionData.scene_number || String(nextOrder),
        scene_order: nextOrder,
        int_ext: selectionData.int_ext || 'INT',
        setting: selectionData.setting || 'Untitled Scene',
        time_of_day: selectionData.time_of_day || 'DAY',
        scene_text: selectionData.text,
        text_start: selectionData.start,
        text_end: selectionData.end,
        is_manual: true,
        analysis_status: 'pending'
    };
    
    return createScene(sceneData);
};

// ============================================
// Script Pages
// ============================================

export const getScriptPages = async (scriptId) => {
    const { data, error } = await supabase
        .from('script_pages')
        .select('*')
        .eq('script_id', scriptId)
        .order('page_number');
    return { data, error };
};

// ============================================
// Real-time Subscriptions
// ============================================

export const subscribeToScenes = (scriptId, callback) => {
    return supabase
        .channel(`scenes:${scriptId}`)
        .on(
            'postgres_changes',
            {
                event: '*',
                schema: 'public',
                table: 'scenes',
                filter: `script_id=eq.${scriptId}`
            },
            callback
        )
        .subscribe();
};

export const subscribeToAnalysisJobs = (scriptId, callback) => {
    return supabase
        .channel(`analysis:${scriptId}`)
        .on(
            'postgres_changes',
            {
                event: '*',
                schema: 'public',
                table: 'analysis_jobs',
                filter: `script_id=eq.${scriptId}`
            },
            callback
        )
        .subscribe();
};

// ============================================
// Profile & Department Operations
// ============================================

export const getProfile = async (userId) => {
    const { data, error } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', userId)
        .single();
    return { data, error };
};

export const updateProfile = async (userId, updates) => {
    const { data, error } = await supabase
        .from('profiles')
        .update(updates)
        .eq('id', userId)
        .select()
        .single();
    return { data, error };
};

export const getUserDepartments = async (userId) => {
    const { data, error } = await supabase
        .from('user_departments')
        .select(`
            *,
            department:departments(*)
        `)
        .eq('user_id', userId);
    return { data, error };
};

export const getDepartments = async () => {
    const { data, error } = await supabase
        .from('departments')
        .select('*')
        .order('sort_order');
    return { data, error };
};

export const joinDepartment = async (userId, departmentId, role = 'member', isPrimary = false) => {
    const { data, error } = await supabase
        .from('user_departments')
        .insert({
            user_id: userId,
            department_id: departmentId,
            role,
            is_primary: isPrimary
        })
        .select()
        .single();
    return { data, error };
};

export const leaveDepartment = async (userId, departmentId) => {
    const { error } = await supabase
        .from('user_departments')
        .delete()
        .eq('user_id', userId)
        .eq('department_id', departmentId);
    return { error };
};

// ============================================
// Department Items
// ============================================

export const getDepartmentItems = async (scriptId, departmentId = null, sceneId = null) => {
    let query = supabase
        .from('department_items')
        .select(`
            *,
            department:departments(*),
            assigned_user:profiles(id, full_name, avatar_url)
        `)
        .eq('script_id', scriptId);
    
    if (departmentId) {
        query = query.eq('department_id', departmentId);
    }
    if (sceneId) {
        query = query.eq('scene_id', sceneId);
    }
    
    const { data, error } = await query.order('created_at', { ascending: false });
    return { data, error };
};

export const createDepartmentItem = async (itemData) => {
    const { data, error } = await supabase
        .from('department_items')
        .insert(itemData)
        .select()
        .single();
    return { data, error };
};

export const updateDepartmentItem = async (itemId, updates) => {
    const { data, error } = await supabase
        .from('department_items')
        .update(updates)
        .eq('id', itemId)
        .select()
        .single();
    return { data, error };
};

// ============================================
// Threads & Collaboration
// ============================================

export const getThreads = async (scriptId, sceneId = null) => {
    let query = supabase
        .from('threads')
        .select(`
            *,
            started_by_department:departments(*),
            participants:thread_participants(department:departments(*)),
            messages:thread_messages(
                *,
                department:departments(*),
                user:profiles(id, full_name, avatar_url)
            )
        `)
        .eq('script_id', scriptId);
    
    if (sceneId) {
        query = query.eq('scene_id', sceneId);
    }
    
    const { data, error } = await query.order('created_at', { ascending: false });
    return { data, error };
};

export const createThread = async (threadData, participantDepartmentIds) => {
    // Create thread
    const { data: thread, error: threadError } = await supabase
        .from('threads')
        .insert(threadData)
        .select()
        .single();
    
    if (threadError) return { data: null, error: threadError };
    
    // Add participants
    const participants = participantDepartmentIds.map(deptId => ({
        thread_id: thread.id,
        department_id: deptId
    }));
    
    const { error: participantError } = await supabase
        .from('thread_participants')
        .insert(participants);
    
    if (participantError) return { data: thread, error: participantError };
    
    return { data: thread, error: null };
};

export const addThreadMessage = async (threadId, departmentId, userId, content) => {
    const { data, error } = await supabase
        .from('thread_messages')
        .insert({
            thread_id: threadId,
            department_id: departmentId,
            user_id: userId,
            content
        })
        .select()
        .single();
    return { data, error };
};

export const resolveThread = async (threadId, userId) => {
    const { data, error } = await supabase
        .from('threads')
        .update({
            status: 'resolved',
            resolved_at: new Date().toISOString(),
            resolved_by: userId
        })
        .eq('id', threadId)
        .select()
        .single();
    return { data, error };
};

// ============================================
// Activity Log
// ============================================

export const getActivityLog = async (scriptId, departmentId = null, limit = 50) => {
    let query = supabase
        .from('activity_log')
        .select(`
            *,
            actor_department:departments(*),
            actor_user:profiles(id, full_name, avatar_url)
        `)
        .eq('script_id', scriptId)
        .order('created_at', { ascending: false })
        .limit(limit);
    
    // Note: RLS will filter based on user's departments
    
    const { data, error } = await query;
    return { data, error };
};

export const logActivity = async (activityData) => {
    const { data, error } = await supabase
        .from('activity_log')
        .insert(activityData)
        .select()
        .single();
    return { data, error };
};

// ============================================
// Real-time Subscriptions for Collaboration
// ============================================

export const subscribeToThreadMessages = (threadId, callback) => {
    return supabase
        .channel(`thread_messages:${threadId}`)
        .on(
            'postgres_changes',
            {
                event: 'INSERT',
                schema: 'public',
                table: 'thread_messages',
                filter: `thread_id=eq.${threadId}`
            },
            callback
        )
        .subscribe();
};

export const subscribeToActivityLog = (scriptId, callback) => {
    return supabase
        .channel(`activity:${scriptId}`)
        .on(
            'postgres_changes',
            {
                event: 'INSERT',
                schema: 'public',
                table: 'activity_log',
                filter: `script_id=eq.${scriptId}`
            },
            callback
        )
        .subscribe();
};

export const subscribeToDepartmentNotes = (scriptId, callback) => {
    return supabase
        .channel(`dept_notes:${scriptId}`)
        .on(
            'postgres_changes',
            {
                event: '*',
                schema: 'public',
                table: 'department_notes',
                filter: `script_id=eq.${scriptId}`
            },
            callback
        )
        .subscribe();
};

export default supabase;
