/**
 * boardReducer.js — Centralized state management for Zoomable Stripboard
 * Implements §3.4 + §3.6 from SPEC-1
 * 
 * Drag lifecycle state machine:
 *   idle → dragging → pending_api → idle (success) or idle (rollback on failure)
 */

export const initialBoardState = {
    // Data (set by effects)
    scenes: [],
    userItemsByScene: {},
    metadata: null,
    loading: true,

    // Board controls
    groupBy: 'scene_order',     // 'scene_order' | 'location' | 'story_day'
    filters: {
        intExt: 'all',
        timeOfDay: 'all',
        storyDay: 'all',
        scheduledStatus: 'all',  // 'all' | 'unscheduled' | 'scheduled'
    },

    // Tool mode: 'select' | 'grab' | 'move'
    toolMode: 'grab',

    // Selection (for select mode)
    selectedStripIds: [],       // array of selected strip IDs

    // Interaction
    activeStrip: null,          // strip ID for detail drawer

    // Drag lifecycle (state machine — §3.6)
    drag: {
        status: 'idle',         // 'idle' | 'dragging' | 'pending_api'
        stripId: null,
        fromLane: null,
        fromIndex: null,
        previousScenes: null,   // snapshot for rollback
    },
};

export function boardReducer(state, action) {
    switch (action.type) {
        case 'SET_SCENES':
            return {
                ...state,
                scenes: action.payload.scenes,
                userItemsByScene: action.payload.userItemsByScene || state.userItemsByScene,
                loading: false,
            };

        case 'SET_METADATA':
            return { ...state, metadata: action.payload };

        case 'SET_LOADING':
            return { ...state, loading: action.payload };

        case 'SET_GROUP_BY':
            return { ...state, groupBy: action.payload };

        case 'SET_FILTER':
            return {
                ...state,
                filters: { ...state.filters, ...action.payload },
            };

        case 'CLEAR_FILTERS':
            return {
                ...state,
                filters: { intExt: 'all', timeOfDay: 'all', storyDay: 'all', scheduledStatus: 'all' },
            };

        // Optimistic update: mark a set of scene IDs as scheduled
        case 'MARK_SCENES_SCHEDULED': {
            const { sceneIds, dayLabel } = action.payload;
            const idSet = new Set(sceneIds);
            return {
                ...state,
                scenes: state.scenes.map(s =>
                    idSet.has(s.id)
                        ? { ...s, is_scheduled: true, scheduled_day_label: dayLabel || s.scheduled_day_label || 'Scheduled' }
                        : s
                ),
            };
        }

        case 'OPEN_DRAWER':
            return { ...state, activeStrip: action.payload };

        case 'CLOSE_DRAWER':
            return { ...state, activeStrip: null };

        // --- Drag lifecycle (§3.6) ---

        case 'DRAG_START':
            if (state.drag.status === 'pending_api') return state; // locked
            return {
                ...state,
                drag: {
                    status: 'dragging',
                    stripId: action.payload.stripId,
                    fromLane: action.payload.laneId,
                    fromIndex: action.payload.fromIndex,
                    previousScenes: null,
                },
            };

        case 'REORDER_OPTIMISTIC': {
            // Snapshot current scenes for rollback, then apply local reorder
            const { fromIndex, toIndex, laneId } = action.payload;
            const prevScenes = [...state.scenes];
            const newScenes = [...state.scenes];

            // Find the actual scene objects by their position in the filtered/grouped view
            // The caller must provide the reordered scene IDs for the full list
            if (action.payload.reorderedScenes) {
                return {
                    ...state,
                    scenes: action.payload.reorderedScenes,
                    drag: {
                        ...state.drag,
                        status: 'pending_api',
                        previousScenes: prevScenes,
                    },
                };
            }

            return {
                ...state,
                scenes: newScenes,
                drag: {
                    ...state.drag,
                    status: 'pending_api',
                    previousScenes: prevScenes,
                },
            };
        }

        case 'REORDER_SUCCESS':
            return {
                ...state,
                drag: {
                    status: 'idle',
                    stripId: null,
                    fromLane: null,
                    fromIndex: null,
                    previousScenes: null,
                },
            };

        case 'REORDER_FAILURE':
            return {
                ...state,
                scenes: state.drag.previousScenes || state.scenes,
                drag: {
                    status: 'idle',
                    stripId: null,
                    fromLane: null,
                    fromIndex: null,
                    previousScenes: null,
                },
            };

        case 'DRAG_END':
            // Cancel drag without reorder
            if (state.drag.status === 'pending_api') return state; // don't cancel mid-API
            return {
                ...state,
                drag: {
                    status: 'idle',
                    stripId: null,
                    fromLane: null,
                    fromIndex: null,
                    previousScenes: null,
                },
            };

        case 'HYDRATE_STATE':
            return {
                ...state,
                groupBy: action.payload.groupBy || state.groupBy,
                filters: action.payload.filters || state.filters,
            };

        // --- Tool mode ---

        case 'SET_TOOL_MODE':
            return {
                ...state,
                toolMode: action.payload,
            };

        // --- Selection ---

        case 'TOGGLE_SELECT_STRIP': {
            const id = action.payload;
            const idx = state.selectedStripIds.indexOf(id);
            return {
                ...state,
                selectedStripIds: idx === -1
                    ? [...state.selectedStripIds, id]
                    : state.selectedStripIds.filter(s => s !== id),
            };
        }

        case 'SET_SELECTED_STRIPS':
            return { ...state, selectedStripIds: action.payload };

        case 'CLEAR_SELECTION':
            return { ...state, selectedStripIds: [] };

        default:
            return state;
    }
}
