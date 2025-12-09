import axios from 'axios';
import { supabase } from '../lib/supabase';

const API_BASE_URL = 'http://localhost:5000';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 30000, // 30 second timeout
});

// Cache for auth token to avoid repeated getSession calls
let cachedToken = null;
let tokenExpiry = 0;
let sessionPromiseInFlight = null;

// Get auth token with caching - optimized for speed
const getAuthToken = async () => {
    const now = Date.now();
    
    // Return cached token if still valid (with 5 min buffer)
    if (cachedToken && tokenExpiry > now + 300000) {
        return cachedToken;
    }
    
    // If a session request is already in flight, wait for it
    if (sessionPromiseInFlight) {
        try {
            await sessionPromiseInFlight;
            if (cachedToken) return cachedToken;
        } catch (e) {
            // Fall through to make new request
        }
    }
    
    try {
        // Single request with deduplication
        sessionPromiseInFlight = supabase.auth.getSession();
        const { data: { session } } = await sessionPromiseInFlight;
        sessionPromiseInFlight = null;
        
        if (session?.access_token) {
            cachedToken = session.access_token;
            // Cache for 55 minutes (tokens typically last 1 hour)
            tokenExpiry = session.expires_at ? session.expires_at * 1000 : now + 3300000;
            return cachedToken;
        }
    } catch (error) {
        sessionPromiseInFlight = null;
        console.warn('Failed to get auth session:', error.message);
    }
    
    return null;
};

// Get auth headers for manual fetch calls
export const getAuthHeaders = async () => {
    const token = await getAuthToken();
    return {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
};

// Clear token cache (call on logout)
export const clearAuthCache = () => {
    cachedToken = null;
    tokenExpiry = 0;
};

// Add auth token to all requests
api.interceptors.request.use(async (config) => {
    const token = await getAuthToken();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
}, (error) => {
    return Promise.reject(error);
});

// Handle 401 responses (token expired)
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            // Clear cache and try to refresh
            clearAuthCache();
            
            try {
                const { data: { session }, error: refreshError } = await supabase.auth.refreshSession();
                if (session && !refreshError) {
                    cachedToken = session.access_token;
                    tokenExpiry = session.expires_at ? session.expires_at * 1000 : Date.now() + 3600000;
                    
                    // Retry the original request with new token
                    error.config.headers.Authorization = `Bearer ${session.access_token}`;
                    return api.request(error.config);
                }
            } catch (refreshError) {
                console.error('Failed to refresh session:', refreshError);
            }
        }
        return Promise.reject(error);
    }
);

// Use Supabase API for uploads
export const uploadScript = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    // Get auth token for upload
    let headers = {};
    try {
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.access_token) {
            headers.Authorization = `Bearer ${session.access_token}`;
        }
    } catch (error) {
        console.warn('Failed to get auth session for upload:', error);
    }

    const response = await fetch(`${API_BASE_URL}/api/upload`, {
        method: 'POST',
        body: formData,
        headers,
    });

    return response.json();
};

// Use Supabase API for scenes
export const getScenes = async (scriptId) => {
    const response = await api.get(`/api/scripts/${scriptId}/scenes`);
    return response.data;
};

// Use Supabase API for scripts
export const getScripts = async () => {
    try {
        console.log('Fetching scripts from:', `${API_BASE_URL}/api/scripts`);
        const response = await api.get(`/api/scripts`, { timeout: 10000 });
        console.log('Scripts response:', response.data);
        return response.data;
    } catch (error) {
        console.error('Error fetching scripts:', error);
        throw error;
    }
};

// Use Supabase API for stats
export const getStats = async () => {
    try {
        console.log('Fetching stats from:', `${API_BASE_URL}/api/stats`);
        const response = await api.get(`/api/stats`, { timeout: 10000 });
        console.log('Stats response:', response.data);
        return response.data;
    } catch (error) {
        console.error('Error fetching stats:', error);
        throw error;
    }
};

// Use Supabase API for delete
export const deleteScript = async (scriptId) => {
    const response = await api.delete(`/api/scripts/${scriptId}`);
    return response.data;
};

export const reanalyzeScript = async (scriptId) => {
    const response = await api.post(`/scripts/${scriptId}/reanalyze`);
    return response.data;
};

// Use Supabase API for metadata
export const getScriptMetadata = async (scriptId) => {
    try {
        const response = await api.get(`/api/scripts/${scriptId}/metadata`);
        return response.data;
    } catch (error) {
        console.error('Error fetching script metadata:', error);
        throw error;
    }
};

/**
 * Get full script text for manual scene labeling
 * @param {string} scriptId - The script UUID
 * @returns {Promise<Object>} Object with full_text property
 */
export const getScriptFullText = async (scriptId) => {
    try {
        const response = await api.get(`/api/scripts/${scriptId}/full-text`);
        return response.data;
    } catch (error) {
        console.error('Error fetching script full text:', error);
        throw error;
    }
};

/**
 * Create a scene manually
 * @param {Object} sceneData - Scene data including script_id, setting, etc.
 * @returns {Promise<Object>} Created scene
 */
export const createScene = async (sceneData) => {
    try {
        const response = await api.post('/api/scenes', sceneData);
        return response.data;
    } catch (error) {
        console.error('Error creating scene:', error);
        throw error;
    }
};

/**
 * Delete a scene
 * @param {string} sceneId - The scene UUID
 * @returns {Promise<Object>} Delete result
 */
export const deleteSceneById = async (sceneId) => {
    try {
        const response = await api.delete(`/api/scenes/${sceneId}`);
        return response.data;
    } catch (error) {
        console.error('Error deleting scene:', error);
        throw error;
    }
};

/**
 * Analyze characters using Gemini AI
 * @param {number} scriptId - The script ID
 * @returns {Promise<Object>} Character analysis with AI descriptions
 */
export const analyzeCharacters = async (scriptId) => {
    try {
        const response = await api.post(`/scripts/${scriptId}/analyze/characters`);
        return response.data;
    } catch (error) {
        console.error('Error analyzing characters:', error);
        throw error;
    }
};

/**
 * Analyze locations using Gemini AI
 * @param {number} scriptId - The script ID
 * @returns {Promise<Object>} Location analysis with AI descriptions
 */
export const analyzeLocations = async (scriptId) => {
    try {
        const response = await api.post(`/scripts/${scriptId}/analyze/locations`);
        return response.data;
    } catch (error) {
        console.error('Error analyzing locations:', error);
        throw error;
    }
};

/**
 * Clear cached analysis for a script
 * @param {number} scriptId - The script ID
 */
export const clearAnalysisCache = async (scriptId) => {
    try {
        const response = await api.post(`/scripts/${scriptId}/analysis/clear`);
        return response.data;
    } catch (error) {
        console.error('Error clearing analysis cache:', error);
        throw error;
    }
};

// ============================================
// Enhanced Analysis API (Queue-based)
// ============================================

/**
 * Get analysis status for all scripts
 * @returns {Promise<Object>} Status for all scripts
 */
export const getGlobalAnalysisStatus = async () => {
    try {
        const response = await api.get('/api/analysis/status');
        return response.data;
    } catch (error) {
        console.error('Error fetching global analysis status:', error);
        throw error;
    }
};

/**
 * Get detailed analysis status for a specific script
 * @param {number} scriptId - The script ID
 * @returns {Promise<Object>} Detailed status with job info
 */
export const getScriptAnalysisStatus = async (scriptId) => {
    try {
        const response = await api.get(`/api/scripts/${scriptId}/analysis/status`);
        return response.data;
    } catch (error) {
        console.error('Error fetching script analysis status:', error);
        throw error;
    }
};

/**
 * Start full analysis for a script (queues all analysis jobs)
 * @param {number} scriptId - The script ID
 * @param {number} priority - Priority level (1=highest, 10=lowest)
 * @returns {Promise<Object>} Queue result with job IDs
 */
export const startScriptAnalysis = async (scriptId, priority = 5) => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/analysis/start`, { priority });
        return response.data;
    } catch (error) {
        console.error('Error starting script analysis:', error);
        throw error;
    }
};

/**
 * Retry failed analyses for a script
 * @param {number} scriptId - The script ID
 * @returns {Promise<Object>} Retry result
 */
export const retryScriptAnalysis = async (scriptId) => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/analysis/retry`);
        return response.data;
    } catch (error) {
        console.error('Error retrying script analysis:', error);
        throw error;
    }
};

/**
 * Get all character analyses for a script (from new cache)
 * @param {number} scriptId - The script ID
 * @returns {Promise<Object>} All character analyses with story arc
 */
export const getCharacterAnalyses = async (scriptId) => {
    try {
        const response = await api.get(`/api/scripts/${scriptId}/analysis/characters`);
        return response.data;
    } catch (error) {
        console.error('Error fetching character analyses:', error);
        throw error;
    }
};

/**
 * Get analysis for a specific character
 * @param {number} scriptId - The script ID
 * @param {string} characterName - The character name
 * @returns {Promise<Object>} Character analysis
 */
export const getCharacterAnalysis = async (scriptId, characterName) => {
    try {
        const encodedName = encodeURIComponent(characterName);
        const response = await api.get(`/api/scripts/${scriptId}/analysis/characters/${encodedName}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching character analysis:', error);
        throw error;
    }
};

/**
 * Get story arc analysis for a script
 * @param {number} scriptId - The script ID
 * @returns {Promise<Object>} Story arc analysis
 */
export const getStoryArcAnalysis = async (scriptId) => {
    try {
        const response = await api.get(`/api/scripts/${scriptId}/analysis/story-arc`);
        return response.data;
    } catch (error) {
        console.error('Error fetching story arc analysis:', error);
        throw error;
    }
};

/**
 * Queue priority analysis for a specific character
 * @param {number} scriptId - The script ID
 * @param {string} characterName - The character name
 * @returns {Promise<Object>} Queue result
 */
export const queueCharacterAnalysis = async (scriptId, characterName) => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/analysis/queue-character`, {
            character_name: characterName
        });
        return response.data;
    } catch (error) {
        console.error('Error queuing character analysis:', error);
        throw error;
    }
};

/**
 * Queue priority analysis for a specific location
 * @param {number} scriptId - The script ID
 * @param {string} locationName - The location name
 * @returns {Promise<Object>} Queue result
 */
export const queueLocationAnalysis = async (scriptId, locationName) => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/analysis/queue-location`, {
            location_name: locationName
        });
        return response.data;
    } catch (error) {
        console.error('Error queuing location analysis:', error);
        throw error;
    }
};

/**
 * Cancel all pending/processing analysis for a script
 * @param {number} scriptId - The script ID
 * @returns {Promise<Object>} Cancel result
 */
export const cancelScriptAnalysis = async (scriptId) => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/analysis/cancel`, {});
        return response.data;
    } catch (error) {
        console.error('Error cancelling analysis:', error);
        throw error;
    }
};

// ============================================
// Scene-Level Analysis API (On-Demand)
// ============================================

/**
 * Analyze a single scene on-demand (Supabase)
 * @param {string} sceneId - The scene UUID
 * @returns {Promise<Object>} Analysis result
 */
export const analyzeScene = async (sceneId) => {
    try {
        const response = await api.post(`/api/scenes/${sceneId}/analyze`);
        return response.data;
    } catch (error) {
        console.error('Error analyzing scene:', error);
        throw error;
    }
};

/**
 * Analyze all pending scenes for a script (bulk)
 * @param {string} scriptId - The script UUID
 * @returns {Promise<Object>} Bulk analysis result
 */
export const analyzeBulkScenes = async (scriptId) => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/analyze/bulk`);
        return response.data;
    } catch (error) {
        console.error('Error starting bulk analysis:', error);
        throw error;
    }
};

/**
 * Get analysis status for all scenes in a script
 * @param {number} scriptId - The script ID
 * @returns {Promise<Object>} Scenes with analysis status
 */
export const getScenesAnalysisStatus = async (scriptId) => {
    try {
        const response = await api.get(`/scripts/${scriptId}/scenes/status`);
        return response.data;
    } catch (error) {
        console.error('Error fetching scenes analysis status:', error);
        throw error;
    }
};

/**
 * Get a signed URL for the script's PDF file
 * @param {string} scriptId - The script ID
 * @returns {Promise<{pdf_url: string, file_name: string, title: string, expires_in: number}>}
 */
export const getPdfUrl = async (scriptId) => {
    try {
        const response = await api.get(`/api/scripts/${scriptId}/pdf-url`);
        return response.data;
    } catch (error) {
        console.error('Error fetching PDF URL:', error);
        throw error;
    }
};

/**
 * Get page-to-scene mapping for bidirectional sync
 * @param {string} scriptId - The script ID
 * @returns {Promise<{scene_pages: Object, page_to_scenes: Object, total_pages: number}>}
 */
export const getPageMapping = async (scriptId) => {
    try {
        const response = await api.get(`/api/scripts/${scriptId}/page-mapping`);
        return response.data;
    } catch (error) {
        console.error('Error fetching page mapping:', error);
        throw error;
    }
};

// ============================================
// Report Generation API
// ============================================

/**
 * Get available report templates
 * @param {string} reportType - Optional filter by report type
 * @returns {Promise<Object>} Templates list
 */
export const getReportTemplates = async (reportType = null) => {
    try {
        const params = reportType ? `?type=${reportType}` : '';
        const response = await api.get(`/api/reports/templates${params}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching report templates:', error);
        throw error;
    }
};

/**
 * Get available report types
 * @returns {Promise<Object>} Report types with descriptions
 */
export const getReportTypes = async () => {
    try {
        const response = await api.get('/api/reports/report-types');
        return response.data;
    } catch (error) {
        console.error('Error fetching report types:', error);
        throw error;
    }
};

/**
 * Generate a new report
 * @param {string} scriptId - The script UUID
 * @param {string} reportType - Type of report to generate
 * @param {string} title - Optional custom title
 * @param {Object} config - Optional configuration overrides
 * @returns {Promise<Object>} Generated report
 */
export const generateReport = async (scriptId, reportType, title = null, config = null) => {
    try {
        const response = await api.post(`/api/reports/scripts/${scriptId}/reports/generate`, {
            report_type: reportType,
            title,
            config
        });
        return response.data;
    } catch (error) {
        console.error('Error generating report:', error);
        throw error;
    }
};

/**
 * Preview report data without saving
 * @param {string} scriptId - The script UUID
 * @param {string} reportType - Type of report to preview
 * @returns {Promise<Object>} Aggregated report data
 */
export const previewReport = async (scriptId, reportType) => {
    try {
        const response = await api.post(`/api/reports/scripts/${scriptId}/reports/preview`, {
            report_type: reportType
        });
        return response.data;
    } catch (error) {
        console.error('Error previewing report:', error);
        throw error;
    }
};

/**
 * Get all reports for a script
 * @param {string} scriptId - The script UUID
 * @returns {Promise<Object>} Reports list
 */
export const getScriptReports = async (scriptId) => {
    try {
        const response = await api.get(`/api/reports/scripts/${scriptId}/reports`);
        return response.data;
    } catch (error) {
        console.error('Error fetching script reports:', error);
        throw error;
    }
};

/**
 * Get a specific report
 * @param {string} reportId - The report UUID
 * @returns {Promise<Object>} Report data
 */
export const getReport = async (reportId) => {
    try {
        const response = await api.get(`/api/reports/reports/${reportId}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching report:', error);
        throw error;
    }
};

/**
 * Delete a report
 * @param {string} reportId - The report UUID
 * @returns {Promise<Object>} Delete result
 */
export const deleteReport = async (reportId) => {
    try {
        const response = await api.delete(`/api/reports/reports/${reportId}`);
        return response.data;
    } catch (error) {
        console.error('Error deleting report:', error);
        throw error;
    }
};

/**
 * Get PDF download URL for a report
 * @param {string} reportId - The report UUID
 * @returns {string} PDF download URL
 */
export const getReportPdfUrl = (reportId) => {
    return `${API_BASE_URL}/api/reports/reports/${reportId}/pdf`;
};

/**
 * Get printable HTML URL for a report
 * @param {string} reportId - The report UUID
 * @returns {string} Printable HTML URL
 */
export const getReportPrintUrl = (reportId) => {
    return `${API_BASE_URL}/api/reports/reports/${reportId}/print`;
};

/**
 * Create a share link for a report
 * @param {string} reportId - The report UUID
 * @param {number} expiresInDays - Days until link expires (default 7)
 * @returns {Promise<Object>} Share info with token and URL
 */
export const createReportShareLink = async (reportId, expiresInDays = 7) => {
    try {
        const response = await api.post(`/api/reports/reports/${reportId}/share`, {
            expires_in_days: expiresInDays
        });
        return response.data;
    } catch (error) {
        console.error('Error creating share link:', error);
        throw error;
    }
};

/**
 * Revoke a share link
 * @param {string} reportId - The report UUID
 * @returns {Promise<Object>} Revoke result
 */
export const revokeReportShareLink = async (reportId) => {
    try {
        const response = await api.delete(`/api/reports/reports/${reportId}/share`);
        return response.data;
    } catch (error) {
        console.error('Error revoking share link:', error);
        throw error;
    }
};

/**
 * Get a shared report by token (public access)
 * @param {string} shareToken - The share token
 * @returns {Promise<Object>} Shared report data
 */
export const getSharedReport = async (shareToken) => {
    try {
        const response = await api.get(`/api/reports/shared/${shareToken}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching shared report:', error);
        throw error;
    }
};

/**
 * Get PDF URL for a shared report
 * @param {string} shareToken - The share token
 * @returns {string} PDF download URL
 */
export const getSharedReportPdfUrl = (shareToken) => {
    return `${API_BASE_URL}/api/reports/shared/${shareToken}/pdf`;
};

/**
 * Get printable HTML URL for a shared report
 * @param {string} shareToken - The share token
 * @returns {string} Printable HTML URL
 */
export const getSharedReportPrintUrl = (shareToken) => {
    return `${API_BASE_URL}/api/reports/shared/${shareToken}/print`;
};

// ============================================
// Department Notes API
// ============================================

/**
 * Get all departments
 * @returns {Promise<{departments: Array}>}
 */
export const getDepartments = async () => {
    try {
        const response = await api.get('/api/departments');
        return response.data;
    } catch (error) {
        console.error('Error fetching departments:', error);
        throw error;
    }
};

/**
 * Get all notes for a script
 * @param {string} scriptId - The script ID
 * @param {Object} filters - Optional filters
 * @param {string} filters.department - Filter by department code
 * @param {string} filters.scene_id - Filter by scene ID
 * @param {string} filters.status - Filter by status
 * @returns {Promise<{notes: Array}>}
 */
export const getScriptNotes = async (scriptId, filters = {}) => {
    try {
        const params = new URLSearchParams();
        if (filters.department) params.append('department', filters.department);
        if (filters.scene_id) params.append('scene_id', filters.scene_id);
        if (filters.status) params.append('status', filters.status);
        
        const queryString = params.toString();
        const url = `/api/scripts/${scriptId}/notes${queryString ? `?${queryString}` : ''}`;
        
        const response = await api.get(url);
        return response.data;
    } catch (error) {
        console.error('Error fetching script notes:', error);
        throw error;
    }
};

/**
 * Get notes for a specific scene, grouped by department
 * @param {string} sceneId - The scene ID
 * @returns {Promise<{scene_id: string, departments: Array, total_notes: number}>}
 */
export const getSceneNotes = async (sceneId) => {
    try {
        const response = await api.get(`/api/scenes/${sceneId}/notes`);
        return response.data;
    } catch (error) {
        console.error('Error fetching scene notes:', error);
        throw error;
    }
};

/**
 * Create a new note
 * @param {string} scriptId - The script ID
 * @param {Object} noteData - Note data
 * @param {string} noteData.department_code - Department code (required)
 * @param {string} noteData.content - Note content (required)
 * @param {string} noteData.scene_id - Scene ID (optional)
 * @param {string} noteData.title - Note title (optional)
 * @param {string} noteData.note_type - Note type (optional, default: 'general')
 * @param {string} noteData.priority - Priority (optional, default: 'normal')
 * @returns {Promise<Object>} Created note
 */
export const createNote = async (scriptId, noteData) => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/notes`, noteData);
        return response.data;
    } catch (error) {
        console.error('Error creating note:', error);
        throw error;
    }
};

/**
 * Update a note
 * @param {string} noteId - The note ID
 * @param {Object} updateData - Fields to update
 * @returns {Promise<Object>} Updated note
 */
export const updateNote = async (noteId, updateData) => {
    try {
        const response = await api.put(`/api/notes/${noteId}`, updateData);
        return response.data;
    } catch (error) {
        console.error('Error updating note:', error);
        throw error;
    }
};

/**
 * Delete a note
 * @param {string} noteId - The note ID
 * @returns {Promise<Object>}
 */
export const deleteNote = async (noteId) => {
    try {
        const response = await api.delete(`/api/notes/${noteId}`);
        return response.data;
    } catch (error) {
        console.error('Error deleting note:', error);
        throw error;
    }
};

/**
 * Update note status (open/resolved)
 * @param {string} noteId - The note ID
 * @param {string} status - New status: 'open' | 'resolved' | 'in_progress'
 * @returns {Promise<Object>}
 */
export const updateNoteStatus = async (noteId, status) => {
    try {
        const response = await api.patch(`/api/notes/${noteId}/status`, { status });
        return response.data;
    } catch (error) {
        console.error('Error updating note status:', error);
        throw error;
    }
};

/**
 * Create a reply to a note
 * @param {string} noteId - The parent note ID
 * @param {string} content - Reply content
 * @returns {Promise<Object>}
 */
export const createReply = async (noteId, content) => {
    try {
        const response = await api.post(`/api/notes/${noteId}/replies`, { content });
        return response.data;
    } catch (error) {
        console.error('Error creating reply:', error);
        throw error;
    }
};

// ============================================
// Scene Management API (Phase 1)
// ============================================

/**
 * Get scenes for management view (includes omitted scenes)
 * @param {string} scriptId - The script UUID
 * @returns {Promise<Object>} Script info and scenes with management fields
 */
export const getScenesForManagement = async (scriptId) => {
    try {
        const response = await api.get(`/api/scripts/${scriptId}/scenes/manage`);
        return response.data;
    } catch (error) {
        console.error('Error fetching scenes for management:', error);
        throw error;
    }
};

/**
 * Reorder scenes
 * @param {string} scriptId - The script UUID
 * @param {string[]} sceneIds - Ordered array of scene UUIDs
 * @returns {Promise<Object>} Result message
 */
export const reorderScenes = async (scriptId, sceneIds) => {
    try {
        const response = await api.patch(`/api/scripts/${scriptId}/scenes/reorder`, {
            scene_ids: sceneIds
        });
        return response.data;
    } catch (error) {
        console.error('Error reordering scenes:', error);
        throw error;
    }
};

/**
 * Omit or restore a scene
 * @param {string} scriptId - The script UUID
 * @param {string} sceneId - The scene UUID
 * @param {boolean} isOmitted - True to omit, false to restore
 * @returns {Promise<Object>} Updated scene
 */
export const omitScene = async (scriptId, sceneId, isOmitted = true) => {
    try {
        const response = await api.patch(`/api/scripts/${scriptId}/scenes/${sceneId}/omit`, {
            is_omitted: isOmitted
        });
        return response.data;
    } catch (error) {
        console.error('Error omitting scene:', error);
        throw error;
    }
};

/**
 * Update scene header (INT/EXT, setting, time of day)
 * @param {string} scriptId - The script UUID
 * @param {string} sceneId - The scene UUID
 * @param {Object} headerData - { int_ext, setting, time_of_day }
 * @returns {Promise<Object>} Updated scene
 */
export const updateSceneHeader = async (scriptId, sceneId, headerData) => {
    try {
        const response = await api.patch(`/api/scripts/${scriptId}/scenes/${sceneId}/header`, headerData);
        return response.data;
    } catch (error) {
        console.error('Error updating scene header:', error);
        throw error;
    }
};

/**
 * Get scene change history
 * @param {string} scriptId - The script UUID
 * @param {string} sceneId - The scene UUID
 * @returns {Promise<Object>} History entries
 */
export const getSceneHistory = async (scriptId, sceneId) => {
    try {
        const response = await api.get(`/api/scripts/${scriptId}/scenes/${sceneId}/history`);
        return response.data;
    } catch (error) {
        console.error('Error fetching scene history:', error);
        throw error;
    }
};

// ============================================
// Scene Operations API (Phase 2)
// ============================================

/**
 * Split a scene into two scenes
 * @param {string} scriptId - The script UUID
 * @param {string} sceneId - The scene UUID to split
 * @param {Object} splitData - { first_scene_text, second_scene_text }
 * @returns {Promise<Object>} First and second scene info
 */
export const splitScene = async (scriptId, sceneId, splitData = {}) => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/scenes/${sceneId}/split`, splitData);
        return response.data;
    } catch (error) {
        console.error('Error splitting scene:', error);
        throw error;
    }
};

/**
 * Merge two adjacent scenes
 * @param {string} scriptId - The script UUID
 * @param {string} sceneId - The first scene UUID
 * @param {string} mergeWithSceneId - The second scene UUID to merge with
 * @param {string} keepSceneNumber - "first" or "second" - which number to keep
 * @returns {Promise<Object>} Merged scene info
 */
export const mergeScenes = async (scriptId, sceneId, mergeWithSceneId, keepSceneNumber = 'first') => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/scenes/${sceneId}/merge`, {
            merge_with_scene_id: mergeWithSceneId,
            keep_scene_number: keepSceneNumber
        });
        return response.data;
    } catch (error) {
        console.error('Error merging scenes:', error);
        throw error;
    }
};

/**
 * Add a new scene manually
 * @param {string} scriptId - The script UUID
 * @param {Object} sceneData - { scene_number, int_ext, setting, time_of_day, insert_after_scene_id }
 * @returns {Promise<Object>} Created scene
 */
export const addManualScene = async (scriptId, sceneData) => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/scenes/manual`, sceneData);
        return response.data;
    } catch (error) {
        console.error('Error adding manual scene:', error);
        throw error;
    }
};

/**
 * Merge multiple scenes into one
 * @param {string} scriptId - The script UUID
 * @param {string[]} sceneIds - Array of scene UUIDs to merge
 * @param {string} keepSceneId - UUID of the scene whose number to keep
 * @returns {Promise<Object>} Merge result
 */
export const mergeMultipleScenes = async (scriptId, sceneIds, keepSceneId) => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/scenes/merge-multiple`, {
            scene_ids: sceneIds,
            keep_scene_id: keepSceneId
        });
        return response.data;
    } catch (error) {
        console.error('Error merging multiple scenes:', error);
        throw error;
    }
};

// ============================================
// Script Lock & Export API (Phase 4)
// ============================================

/**
 * Lock a script for production (shooting script)
 * @param {string} scriptId - The script UUID
 * @param {string} revisionColor - Revision color (WHITE, BLUE, PINK, etc.)
 * @returns {Promise<Object>} Lock result
 */
export const lockScript = async (scriptId, revisionColor = 'WHITE') => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/lock`, {
            revision_color: revisionColor
        });
        return response.data;
    } catch (error) {
        console.error('Error locking script:', error);
        throw error;
    }
};

/**
 * Unlock a script (revert to working draft)
 * @param {string} scriptId - The script UUID
 * @returns {Promise<Object>} Unlock result
 */
export const unlockScript = async (scriptId) => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/unlock`);
        return response.data;
    } catch (error) {
        console.error('Error unlocking script:', error);
        throw error;
    }
};

/**
 * Get shooting script data for preview/export
 * @param {string} scriptId - The script UUID
 * @returns {Promise<Object>} Shooting script data
 */
export const getShootingScriptData = async (scriptId) => {
    try {
        const response = await api.get(`/api/scripts/${scriptId}/shooting-script`);
        return response.data;
    } catch (error) {
        console.error('Error getting shooting script data:', error);
        throw error;
    }
};


// ============================================
// Phase 3: Revision Import API
// ============================================

/**
 * Get all versions/revisions of a script
 * @param {string} scriptId - The script UUID
 * @returns {Promise<Object>} List of versions
 */
export const getScriptVersions = async (scriptId) => {
    try {
        const response = await api.get(`/api/scripts/${scriptId}/versions`);
        return response.data;
    } catch (error) {
        console.error('Error getting script versions:', error);
        throw error;
    }
};

/**
 * Import a new revision of a script
 * @param {string} scriptId - The script UUID
 * @param {File} file - The PDF file
 * @param {string} revisionColor - The revision color (white, blue, pink, etc.)
 * @param {string} notes - Optional notes
 * @param {boolean} applyChanges - Whether to apply changes or just preview
 * @returns {Promise<Object>} Import result with diff
 */
export const importRevision = async (scriptId, file, revisionColor = 'white', notes = '', applyChanges = false) => {
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('revision_color', revisionColor);
        formData.append('notes', notes);
        formData.append('apply_changes', applyChanges.toString());
        
        const response = await api.post(`/api/scripts/${scriptId}/versions/import`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });
        return response.data;
    } catch (error) {
        console.error('Error importing revision:', error);
        throw error;
    }
};

/**
 * Get diff for a specific version
 * @param {string} scriptId - The script UUID
 * @param {string} versionId - The version UUID
 * @param {string} compareToId - Optional version to compare against
 * @returns {Promise<Object>} Diff data
 */
export const getVersionDiff = async (scriptId, versionId, compareToId = null) => {
    try {
        const params = compareToId ? `?compare_to=${compareToId}` : '';
        const response = await api.get(`/api/scripts/${scriptId}/versions/${versionId}/diff${params}`);
        return response.data;
    } catch (error) {
        console.error('Error getting version diff:', error);
        throw error;
    }
};

/**
 * Get details of a specific version
 * @param {string} scriptId - The script UUID
 * @param {string} versionId - The version UUID
 * @returns {Promise<Object>} Version details
 */
export const getVersionDetails = async (scriptId, versionId) => {
    try {
        const response = await api.get(`/api/scripts/${scriptId}/versions/${versionId}`);
        return response.data;
    } catch (error) {
        console.error('Error getting version details:', error);
        throw error;
    }
};

export default api;
