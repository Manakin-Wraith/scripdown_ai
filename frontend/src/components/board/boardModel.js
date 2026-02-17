/**
 * boardModel.js — Pure view model functions for Zoomable Stripboard
 * Implements §3.7 + §4.4 from SPEC-1
 * 
 * filterScenes → groupScenes → buildBoardViewModel
 * All pure functions, testable in isolation.
 */
import { getSceneEighths } from '../../utils/sceneUtils';

/**
 * Apply filter predicates to scenes array.
 * @param {Array} scenes - Raw scenes from API
 * @param {Object} filters - { intExt, timeOfDay, storyDay }
 * @returns {Array} Filtered scenes
 */
export function filterScenes(scenes, filters) {
    if (!scenes || scenes.length === 0) return [];
    if (!filters) return scenes;

    let result = scenes;

    if (filters.intExt && filters.intExt !== 'all') {
        result = result.filter(s => s.int_ext === filters.intExt);
    }

    if (filters.timeOfDay && filters.timeOfDay !== 'all') {
        result = result.filter(s => s.time_of_day === filters.timeOfDay);
    }

    if (filters.storyDay && filters.storyDay !== 'all') {
        const dayNum = parseInt(filters.storyDay, 10);
        if (!isNaN(dayNum)) {
            result = result.filter(s => s.story_day === dayNum);
        }
    }

    return result;
}

/**
 * Helper: group array by key function.
 */
function groupByKey(items, keyFn) {
    const groups = {};
    items.forEach(item => {
        const key = keyFn(item);
        if (!groups[key]) groups[key] = [];
        groups[key].push(item);
    });
    return groups;
}

/**
 * Group scenes by dimension.
 * @param {Array} scenes - Filtered scenes
 * @param {string} groupBy - 'scene_order' | 'location' | 'story_day'
 * @returns {Object} { [groupKey]: scenes[] }
 */
export function groupScenes(scenes, groupBy) {
    if (!scenes || scenes.length === 0) return {};

    switch (groupBy) {
        case 'location':
            return groupByKey(scenes, s => s.setting || 'UNKNOWN');
        case 'story_day':
            return groupByKey(scenes, s =>
                s.story_day ? `Day ${s.story_day}` : 'Unassigned'
            );
        case 'scene_order':
        default:
            return { 'All Scenes': scenes };
    }
}

/**
 * Build the full board view model consumed by the UI.
 * @param {Array} scenes - Raw scenes from API
 * @param {Object} filters - Filter state
 * @param {string} groupBy - Grouping dimension
 * @returns {{ lanes: Array<{ id, label, count, strips }>, totalVisible, totalScenes }}
 */
export function buildBoardViewModel(scenes, filters, groupBy) {
    if (!scenes || scenes.length === 0) {
        return { lanes: [], totalVisible: 0, totalScenes: 0 };
    }

    const filtered = filterScenes(scenes, filters);
    const grouped = groupScenes(filtered, groupBy);

    // Sort group keys for consistent ordering
    const sortedKeys = Object.keys(grouped).sort((a, b) => {
        // "All Scenes" always first
        if (a === 'All Scenes') return -1;
        if (b === 'All Scenes') return 1;

        // Story day: numeric sort
        if (groupBy === 'story_day') {
            const aNum = parseInt(a.replace('Day ', ''), 10);
            const bNum = parseInt(b.replace('Day ', ''), 10);
            if (a === 'Unassigned') return 1;
            if (b === 'Unassigned') return -1;
            return (aNum || 0) - (bNum || 0);
        }

        // Location: alphabetical
        return a.localeCompare(b);
    });

    const lanes = sortedKeys.map(key => ({
        id: key,
        label: key,
        count: grouped[key].length,
        strips: grouped[key].map(scene => ({
            id: scene.id || scene.scene_id,
            sceneNumber: scene.scene_number,
            sceneOrder: scene.scene_order,
            intExt: scene.int_ext,
            setting: scene.setting,
            timeOfDay: scene.time_of_day,
            characters: scene.characters || [],
            props: scene.props || [],
            wardrobe: scene.wardrobe || [],
            vehicles: scene.vehicles || [],
            specialFx: scene.special_fx || [],
            sound: scene.sound || [],
            atmosphere: scene.atmosphere || '',
            storyDay: scene.story_day,
            storyDayLabel: scene.story_day_label,
            timelineCode: scene.timeline_code || 'PRESENT',
            pageLengthEighths: getSceneEighths(scene),
            isOmitted: scene.is_omitted,
            shotType: scene.shot_type,
            locationHierarchy: scene.location_hierarchy,
            parseMethod: scene.parse_method,
        })),
    }));

    return {
        lanes,
        totalVisible: filtered.length,
        totalScenes: scenes.length,
    };
}

/**
 * Get unique story days from scenes for filter dropdown.
 * @param {Array} scenes
 * @returns {Array<{ day, label, count }>}
 */
export function getUniqueStoryDays(scenes) {
    if (!scenes) return [];
    const days = new Map();
    scenes.forEach(scene => {
        if (scene.story_day) {
            if (!days.has(scene.story_day)) {
                days.set(scene.story_day, {
                    day: scene.story_day,
                    label: scene.story_day_label || `Day ${scene.story_day}`,
                    count: 0,
                });
            }
            days.get(scene.story_day).count++;
        }
    });
    return Array.from(days.values()).sort((a, b) => a.day - b.day);
}

/**
 * Count active filters.
 * @param {Object} filters
 * @returns {number}
 */
export function countActiveFilters(filters) {
    if (!filters) return 0;
    let count = 0;
    if (filters.intExt && filters.intExt !== 'all') count++;
    if (filters.timeOfDay && filters.timeOfDay !== 'all') count++;
    if (filters.storyDay && filters.storyDay !== 'all') count++;
    return count;
}
