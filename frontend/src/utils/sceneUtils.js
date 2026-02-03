/**
 * Scene utility functions for script breakdown
 */

/**
 * Calculate scene length in eighths of a page.
 * Industry standard: 1 page ≈ 55 lines (screenplay format) ≈ 8/8
 * 
 * @param {string} sceneText - The full text of the scene
 * @returns {number} - Number of eighths (1-80 max)
 */
export function calculateEighths(sceneText) {
    if (!sceneText || typeof sceneText !== 'string' || !sceneText.trim()) {
        return 8; // Default to 1 page
    }
    
    // Count lines (industry standard: 55 lines = 1 page)
    const lines = sceneText.trim().split('\n').length;
    
    // Calculate eighths: 55 lines = 8 eighths
    // Round to nearest eighth
    const eighths = Math.round((lines / 55) * 8);
    
    // Minimum 1/8, maximum 80 eighths (10 pages)
    return Math.max(1, Math.min(eighths, 80));
}

/**
 * Format eighths as a display string.
 * Examples: "1/8", "4/8", "1 2/8", "2 4/8"
 * 
 * @param {number} eighths - Total number of eighths
 * @returns {string} - Formatted string like "1/8" or "1 2/8"
 */
export function formatEighths(eighths) {
    if (!eighths || eighths < 1) {
        return '1/8';
    }
    
    const pages = Math.floor(eighths / 8);
    const remainder = eighths % 8;
    
    if (pages === 0) {
        return `${remainder}/8`;
    } else if (remainder === 0) {
        return `${pages}`;
    } else {
        return `${pages} ${remainder}/8`;
    }
}

/**
 * Calculate eighths from page range (less accurate fallback).
 * Uses page_start and page_end when scene_text is not available.
 * 
 * @param {number} pageStart - Starting page number
 * @param {number} pageEnd - Ending page number
 * @param {string} sceneText - Optional scene text for more accurate calculation
 * @returns {number} - Estimated eighths
 */
export function calculateEighthsFromPages(pageStart, pageEnd, sceneText = null) {
    if (!pageStart || !pageEnd) {
        return 8; // Default to 1 page
    }
    
    // If we have scene text, use line-based calculation (most accurate)
    if (sceneText && sceneText.trim()) {
        return calculateEighths(sceneText);
    }
    
    // Otherwise, estimate based on page span
    // Each page = 8 eighths (assumes full pages)
    const pageSpan = pageEnd - pageStart + 1;
    const totalEighths = pageSpan * 8;
    
    // Cap at maximum 80 eighths (10 pages)
    return Math.max(1, Math.min(totalEighths, 80));
}

/**
 * Get eighths for a scene, using database value if available, with fallbacks.
 * 
 * @param {object} scene - Scene object with page_length_eighths, scene_text, page_start, page_end
 * @returns {number} - Number of eighths
 */
export function getSceneEighths(scene) {
    if (!scene) return 8;
    
    // Priority 1: ALWAYS use pre-calculated eighths from database
    // Backend has already calculated this accurately
    if (scene.page_length_eighths && scene.page_length_eighths > 0) {
        return scene.page_length_eighths;
    }
    
    // Priority 2: Calculate from text if available (rare - only if DB value missing)
    if (scene.scene_text && scene.scene_text.length > 10) {
        return calculateEighths(scene.scene_text);
    }
    
    // Priority 3: Fallback to page-based estimation (last resort)
    return calculateEighthsFromPages(scene.page_start, scene.page_end, scene.scene_text);
}

/**
 * Get formatted eighths display for a scene.
 * 
 * @param {object} scene - Scene object
 * @returns {string} - Formatted string like "2/8" or "1 4/8"
 */
export function getSceneEighthsDisplay(scene) {
    const eighths = getSceneEighths(scene);
    return formatEighths(eighths);
}
