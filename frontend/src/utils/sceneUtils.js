/**
 * Scene utility functions for script breakdown
 */

/**
 * Calculate scene length in eighths of a page.
 * Industry standard: 1 page ≈ 250 words ≈ 8/8
 * 
 * @param {string} sceneText - The full text of the scene
 * @returns {number} - Number of eighths (1-8+ per page)
 */
export function calculateEighths(sceneText) {
    if (!sceneText || typeof sceneText !== 'string') {
        return 1; // Minimum 1/8
    }
    
    // Count words (split by whitespace)
    const words = sceneText.trim().split(/\s+/).filter(w => w.length > 0);
    const wordCount = words.length;
    
    // Standard: 250 words = 1 page = 8 eighths
    // So 31.25 words = 1 eighth
    const WORDS_PER_EIGHTH = 31.25;
    
    const eighths = Math.ceil(wordCount / WORDS_PER_EIGHTH);
    
    // Minimum 1/8, no maximum (scenes can span multiple pages)
    return Math.max(1, eighths);
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
 * @returns {number} - Estimated eighths
 */
export function calculateEighthsFromPages(pageStart, pageEnd) {
    if (!pageStart) return 1;
    if (!pageEnd || pageEnd < pageStart) {
        return 4; // Default to half page for single page
    }
    
    // Estimate: each page span = 8 eighths
    const pageSpan = pageEnd - pageStart + 1;
    return pageSpan * 8;
}

/**
 * Get eighths for a scene, using text if available, pages as fallback.
 * 
 * @param {object} scene - Scene object with scene_text, page_start, page_end
 * @returns {number} - Number of eighths
 */
export function getSceneEighths(scene) {
    if (!scene) return 1;
    
    // Prefer text-based calculation
    if (scene.scene_text && scene.scene_text.length > 10) {
        return calculateEighths(scene.scene_text);
    }
    
    // Fallback to page-based estimation
    return calculateEighthsFromPages(scene.page_start, scene.page_end);
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
