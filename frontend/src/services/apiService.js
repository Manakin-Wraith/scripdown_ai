import axios from 'axios';
import { supabase } from '../lib/supabase';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

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

// Update script metadata (title, writer_name, etc.)
export const updateScript = async (scriptId, data) => {
    const response = await api.patch(`/api/scripts/${scriptId}`, data);
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
 * Get available report configuration presets
 * @returns {Promise<Object>} Report presets with metadata
 */
export const getReportPresets = async () => {
    try {
        const response = await api.get('/api/reports/report-presets');
        return response.data;
    } catch (error) {
        console.error('Error fetching report presets:', error);
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
// Breakdown Items CRUD API
// ============================================

/**
 * Get all breakdown items for a scene
 * @param {string} scriptId - The script UUID
 * @param {string} sceneId - The scene UUID
 * @param {string} [itemType] - Optional filter by item_type (e.g., 'characters', 'props')
 * @returns {Promise<{items: Array}>}
 */
export const getScriptItems = async (scriptId, includeRemoved = false) => {
    try {
        const params = new URLSearchParams();
        if (includeRemoved) params.append('include_removed', 'true');
        const query = params.toString() ? `?${params.toString()}` : '';
        const response = await api.get(`/api/scripts/${scriptId}/items${query}`);
        return response.data;
    } catch (error) {
        console.error('Error getting script items:', error);
        throw error;
    }
};

export const getSceneItems = async (scriptId, sceneId, itemType = null, includeRemoved = false) => {
    try {
        const params = new URLSearchParams();
        if (itemType) params.append('item_type', itemType);
        if (includeRemoved) params.append('include_removed', 'true');
        const query = params.toString() ? `?${params.toString()}` : '';
        const response = await api.get(`/api/scripts/${scriptId}/scenes/${sceneId}/items${query}`);
        return response.data;
    } catch (error) {
        console.error('Error getting scene items:', error);
        throw error;
    }
};

/**
 * Create a new breakdown item for a scene
 * @param {string} scriptId - The script UUID
 * @param {string} sceneId - The scene UUID
 * @param {Object} itemData - { item_type, item_name, description?, priority?, status? }
 * @returns {Promise<Object>} Created item
 */
export const createSceneItem = async (scriptId, sceneId, itemData) => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/scenes/${sceneId}/items`, itemData);
        return response.data;
    } catch (error) {
        console.error('Error creating scene item:', error);
        throw error;
    }
};

/**
 * Update a breakdown item
 * @param {string} itemId - The item UUID
 * @param {Object} updates - { item_name?, description?, status?, priority?, assigned_to?, due_date? }
 * @returns {Promise<Object>} Updated item
 */
export const updateSceneItem = async (itemId, updates) => {
    try {
        const response = await api.put(`/api/items/${itemId}`, updates);
        return response.data;
    } catch (error) {
        console.error('Error updating scene item:', error);
        throw error;
    }
};

/**
 * Remove an AI-detected item from a scene's JSONB breakdown array
 * @param {string} scriptId - The script UUID
 * @param {string} sceneId - The scene UUID
 * @param {string} itemType - The category column (e.g., 'vehicles', 'characters')
 * @param {string} itemName - The exact item name to remove
 * @returns {Promise<Object>} { remaining_items }
 */
export const removeAiItem = async (scriptId, sceneId, itemType, itemName) => {
    try {
        const response = await api.patch(`/api/scripts/${scriptId}/scenes/${sceneId}/remove-ai-item`, {
            item_type: itemType,
            item_name: itemName
        });
        return response.data;
    } catch (error) {
        console.error('Error removing AI item:', error);
        throw error;
    }
};

/**
 * Delete a breakdown item
 * @param {string} itemId - The item UUID
 * @returns {Promise<Object>}
 */
export const deleteSceneItem = async (itemId) => {
    try {
        const response = await api.delete(`/api/items/${itemId}`);
        return response.data;
    } catch (error) {
        console.error('Error deleting scene item:', error);
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
// Story Day Management API (Phase 2)
// ============================================

/**
 * Toggle is_new_story_day on a scene, triggering cascade recalculation
 * @param {string} scriptId - The script UUID
 * @param {string} sceneId - The scene UUID
 * @returns {Promise<Object>} Toggle result with recalculation info
 */
export const toggleNewDay = async (scriptId, sceneId) => {
    try {
        const response = await api.patch(`/api/scripts/${scriptId}/scenes/${sceneId}/toggle-new-day`);
        return response.data;
    } catch (error) {
        console.error('Error toggling new day:', error);
        throw error;
    }
};

/**
 * Toggle or set story_day_is_locked on a scene
 * @param {string} scriptId - The script UUID
 * @param {string} sceneId - The scene UUID
 * @param {boolean|null} locked - Explicit lock state, or null to toggle
 * @returns {Promise<Object>} Lock result
 */
export const lockStoryDay = async (scriptId, sceneId, locked = null) => {
    try {
        const response = await api.patch(`/api/scripts/${scriptId}/scenes/${sceneId}/lock-story-day`, {
            locked
        });
        return response.data;
    } catch (error) {
        console.error('Error locking story day:', error);
        throw error;
    }
};

/**
 * Set timeline_code on a scene (PRESENT, FLASHBACK, DREAM, etc.)
 * @param {string} scriptId - The script UUID
 * @param {string} sceneId - The scene UUID
 * @param {string} timelineCode - Timeline code
 * @returns {Promise<Object>} Result with recalculation info
 */
export const setTimelineCode = async (scriptId, sceneId, timelineCode) => {
    try {
        const response = await api.patch(`/api/scripts/${scriptId}/scenes/${sceneId}/timeline-code`, {
            timeline_code: timelineCode
        });
        return response.data;
    } catch (error) {
        console.error('Error setting timeline code:', error);
        throw error;
    }
};

/**
 * Manually set story_day on a scene (locks it automatically)
 * @param {string} scriptId - The script UUID
 * @param {string} sceneId - The scene UUID
 * @param {number} storyDay - Day number (positive integer)
 * @returns {Promise<Object>} Result with recalculation info
 */
export const setStoryDay = async (scriptId, sceneId, storyDay) => {
    try {
        const response = await api.patch(`/api/scripts/${scriptId}/scenes/${sceneId}/story-day`, {
            story_day: storyDay
        });
        return response.data;
    } catch (error) {
        console.error('Error setting story day:', error);
        throw error;
    }
};

/**
 * Trigger full recalculation of story days for a script
 * @param {string} scriptId - The script UUID
 * @returns {Promise<Object>} Recalculation result
 */
export const calculateStoryDays = async (scriptId) => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/story-days/calculate`);
        return response.data;
    } catch (error) {
        console.error('Error calculating story days:', error);
        throw error;
    }
};

/**
 * Get story day summary for a script
 * @param {string} scriptId - The script UUID
 * @returns {Promise<Object>} Summary with day counts, timeline breakdown
 */
export const getStoryDaySummary = async (scriptId) => {
    try {
        const response = await api.get(`/api/scripts/${scriptId}/story-days/summary`);
        return response.data;
    } catch (error) {
        console.error('Error getting story day summary:', error);
        throw error;
    }
};

/**
 * Bulk update story day fields on multiple scenes
 * @param {string} scriptId - The script UUID
 * @param {Array<Object>} updates - Array of {scene_id, story_day?, is_new_story_day?, timeline_code?}
 * @returns {Promise<Object>} Update result with recalculation info
 */
export const bulkUpdateStoryDays = async (scriptId, updates) => {
    try {
        const response = await api.post(`/api/scripts/${scriptId}/story-days/bulk-update`, {
            updates
        });
        return response.data;
    } catch (error) {
        console.error('Error bulk updating story days:', error);
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

/**
 * Download stripboard as PDF
 * @param {string} scriptId - The script UUID
 * @param {string} title - The script title for filename
 * @returns {Promise<void>} Downloads the PDF file
 */
export const downloadStripboardPdf = async (scriptId, title = 'Stripboard') => {
    try {
        const response = await api.get(`/api/scripts/${scriptId}/stripboard/pdf`, {
            responseType: 'blob'
        });
        
        // Create download link
        const blob = new Blob([response.data], { type: 'application/pdf' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${title.replace(/[^a-zA-Z0-9]/g, '_')}_Stripboard.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Error downloading stripboard PDF:', error);
        throw error;
    }
};

// ============================================
// Admin API Endpoints (Superuser Only)
// ============================================

/**
 * Get analytics overview (global stats + subscriptions)
 * @returns {Promise<Object>} Analytics overview data
 */
export const getAnalyticsOverview = async () => {
    try {
        const response = await api.get('/api/admin/analytics/overview');
        return response.data;
    } catch (error) {
        console.error('Error getting analytics overview:', error);
        throw error;
    }
};

/**
 * Get user activity analytics with pagination and filtering
 * @param {number} days - Number of days to look back (default: 30)
 * @param {number} limit - Maximum records to return (default: 50)
 * @param {number} offset - Number of records to skip (default: 0)
 * @param {string} status - Filter by subscription status (optional)
 * @param {string} search - Search by name or email (optional)
 * @returns {Promise<Object>} User activity data with pagination
 */
export const getUserAnalytics = async (days = 30, limit = 50, offset = 0, status = null, search = null) => {
    try {
        const params = { days, limit, offset };
        if (status) params.status = status;
        if (search) params.search = search;
        
        const response = await api.get('/api/admin/analytics/users', { params });
        return response.data;
    } catch (error) {
        console.error('Error getting user analytics:', error);
        throw error;
    }
};

/**
 * Get chart data for visualizations
 * @param {number} days - Number of days to look back (default: 30)
 * @returns {Promise<Object>} Chart data for scripts and users over time
 */
export const getChartData = async (days = 30) => {
    try {
        const response = await api.get('/api/admin/analytics/charts', {
            params: { days }
        });
        return response.data;
    } catch (error) {
        console.error('Error getting chart data:', error);
        throw error;
    }
};

/**
 * Get recent platform activity feed
 * @param {number} limit - Maximum number of events to return (default: 50)
 * @returns {Promise<Object>} Recent activity events
 */
export const getRecentActivity = async (limit = 50) => {
    try {
        const response = await api.get('/api/admin/analytics/activity', {
            params: { limit }
        });
        return response.data;
    } catch (error) {
        console.error('Error getting recent activity:', error);
        throw error;
    }
};

/**
 * Get comprehensive script analytics and performance metrics
 * @returns {Promise<Object>} Script analytics data
 */
export const getScriptAnalytics = async () => {
    try {
        const response = await api.get('/api/admin/analytics/scripts');
        return response.data;
    } catch (error) {
        console.error('Error getting script analytics:', error);
        throw error;
    }
};

/**
 * Get script analysis statistics (legacy)
 * @param {number} days - Number of days to look back (default: 30)
 * @returns {Promise<Object>} Script statistics
 */
export const getScriptStats = async (days = 30) => {
    try {
        const response = await api.get('/api/admin/analytics/scripts/stats', {
            params: { days }
        });
        return response.data;
    } catch (error) {
        console.error('Error getting script analytics:', error);
        throw error;
    }
};

/**
 * Get system performance metrics
 * @returns {Promise<Object>} Performance metrics
 */
export const getPerformanceAnalytics = async () => {
    try {
        const response = await api.get('/api/admin/analytics/performance');
        return response.data;
    } catch (error) {
        console.error('Error getting performance analytics:', error);
        throw error;
    }
};

/**
 * Get subscription metrics
 * @returns {Promise<Object>} Subscription statistics
 */
export const getSubscriptionAnalytics = async () => {
    try {
        const response = await api.get('/api/admin/analytics/subscriptions');
        return response.data;
    } catch (error) {
        console.error('Error getting subscription analytics:', error);
        throw error;
    }
};

/**
 * Get system health status
 * @returns {Promise<Object>} System health indicators
 */
export const getSystemHealth = async () => {
    try {
        const response = await api.get('/api/admin/health');
        return response.data;
    } catch (error) {
        console.error('Error getting system health:', error);
        throw error;
    }
};

/**
 * List users with filtering
 * @param {Object} params - Query parameters (status, limit, offset)
 * @returns {Promise<Object>} User list
 */
export const listUsers = async (params = {}) => {
    try {
        const response = await api.get('/api/admin/users', { params });
        return response.data;
    } catch (error) {
        console.error('Error listing users:', error);
        throw error;
    }
};

/**
 * Get user details
 * @param {string} userId - User UUID
 * @returns {Promise<Object>} User details with scripts
 */
export const getUserDetails = async (userId) => {
    try {
        const response = await api.get(`/api/admin/users/${userId}`);
        return response.data;
    } catch (error) {
        console.error('Error getting user details:', error);
        throw error;
    }
};

// ==================== Feedback API ====================

/**
 * Submit feedback
 * @param {FormData} formData - Form data with feedback fields and optional screenshot
 * @returns {Promise<Object>} Feedback submission response
 */
export const submitFeedback = async (formData) => {
    try {
        const response = await api.post('/api/feedback', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    } catch (error) {
        console.error('Error submitting feedback:', error);
        throw error;
    }
};

/**
 * Get user's feedback submissions
 * @param {Object} params - Query parameters (page, limit)
 * @returns {Promise<Object>} Feedback list with pagination
 */
export const getUserFeedback = async (params = {}) => {
    try {
        const response = await api.get('/api/feedback', { params });
        return response.data;
    } catch (error) {
        console.error('Error fetching user feedback:', error);
        throw error;
    }
};

/**
 * Get single feedback by ID
 * @param {string} feedbackId - Feedback UUID
 * @returns {Promise<Object>} Feedback details
 */
export const getFeedbackById = async (feedbackId) => {
    try {
        const response = await api.get(`/api/feedback/${feedbackId}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching feedback:', error);
        throw error;
    }
};

// ==================== Email Campaigns API ====================

/**
 * List email templates
 * @param {Object} params - Query parameters (category, active_only)
 * @returns {Promise<Object>} Template list
 */
export const getEmailTemplates = async (params = {}) => {
    try {
        const response = await api.get('/api/campaigns/templates', { params });
        return response.data;
    } catch (error) {
        console.error('Error fetching email templates:', error);
        throw error;
    }
};

/**
 * Get single email template
 * @param {string} templateId - Template UUID
 * @returns {Promise<Object>} Template details
 */
export const getEmailTemplate = async (templateId) => {
    try {
        const response = await api.get(`/api/campaigns/templates/${templateId}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching email template:', error);
        throw error;
    }
};

/**
 * Create new email template
 * @param {Object} templateData - Template data (name, subject, body_html, etc.)
 * @returns {Promise<Object>} Created template
 */
export const createEmailTemplate = async (templateData) => {
    try {
        const response = await api.post('/api/campaigns/templates', templateData);
        return response.data;
    } catch (error) {
        console.error('Error creating email template:', error);
        throw error;
    }
};

/**
 * List email campaigns
 * @param {Object} params - Query parameters (status, limit, offset)
 * @returns {Promise<Object>} Campaign list with pagination
 */
export const getCampaigns = async (params = {}) => {
    try {
        const response = await api.get('/api/campaigns/', { params });
        return response.data;
    } catch (error) {
        console.error('Error fetching campaigns:', error);
        throw error;
    }
};

/**
 * Get single campaign with details
 * @param {string} campaignId - Campaign UUID
 * @returns {Promise<Object>} Campaign details with recipient counts
 */
export const getCampaign = async (campaignId) => {
    try {
        const response = await api.get(`/api/campaigns/${campaignId}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching campaign:', error);
        throw error;
    }
};

/**
 * Create new email campaign
 * @param {Object} campaignData - Campaign data (name, template_id, audience_filter, etc.)
 * @returns {Promise<Object>} Created campaign with recipient count
 */
export const createCampaign = async (campaignData) => {
    try {
        const response = await api.post('/api/campaigns/', campaignData);
        return response.data;
    } catch (error) {
        console.error('Error creating campaign:', error);
        throw error;
    }
};

/**
 * Update campaign (draft/scheduled only)
 * @param {string} campaignId - Campaign UUID
 * @param {Object} updates - Fields to update
 * @returns {Promise<Object>} Updated campaign
 */
export const updateCampaign = async (campaignId, updates) => {
    try {
        const response = await api.patch(`/api/campaigns/${campaignId}`, updates);
        return response.data;
    } catch (error) {
        console.error('Error updating campaign:', error);
        throw error;
    }
};

/**
 * Delete campaign (draft only)
 * @param {string} campaignId - Campaign UUID
 * @returns {Promise<Object>} Success status
 */
export const deleteCampaign = async (campaignId) => {
    try {
        const response = await api.delete(`/api/campaigns/${campaignId}`);
        return response.data;
    } catch (error) {
        console.error('Error deleting campaign:', error);
        throw error;
    }
};

/**
 * Send campaign immediately
 * @param {string} campaignId - Campaign UUID
 * @returns {Promise<Object>} Updated campaign
 */
export const sendCampaign = async (campaignId) => {
    try {
        const response = await api.post(`/api/campaigns/${campaignId}/send`);
        return response.data;
    } catch (error) {
        console.error('Error sending campaign:', error);
        throw error;
    }
};

/**
 * Get campaign analytics
 * @param {string} campaignId - Campaign UUID
 * @returns {Promise<Object>} Campaign performance metrics
 */
export const getCampaignAnalytics = async (campaignId) => {
    try {
        const response = await api.get(`/api/campaigns/${campaignId}/analytics`);
        return response.data;
    } catch (error) {
        console.error('Error fetching campaign analytics:', error);
        throw error;
    }
};

/**
 * Preview campaign audience
 * @param {Object} audienceFilter - Audience segmentation filters
 * @returns {Promise<Object>} Audience statistics and sample users
 */
export const previewCampaignAudience = async (audienceFilter) => {
    try {
        const response = await api.post('/api/campaigns/preview', { audience_filter: audienceFilter });
        return response.data;
    } catch (error) {
        console.error('Error previewing campaign audience:', error);
        throw error;
    }
};

/**
 * Get campaign recipients
 * @param {string} campaignId - Campaign UUID
 * @param {Object} params - Query parameters (status, limit, offset)
 * @returns {Promise<Object>} Recipient list with pagination
 */
export const getCampaignRecipients = async (campaignId, params = {}) => {
    try {
        const response = await api.get(`/api/campaigns/${campaignId}/recipients`, { params });
        return response.data;
    } catch (error) {
        console.error('Error fetching campaign recipients:', error);
        throw error;
    }
};

export default api;
