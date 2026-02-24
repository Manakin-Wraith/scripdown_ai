import React, { useReducer, useEffect, useMemo, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader, ArrowLeft } from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { useScript } from '../../context/ScriptContext';
import { getScenes, getScriptMetadata, getScriptItems, reorderScenes } from '../../services/apiService';
import { boardReducer, initialBoardState } from './boardReducer';
import { buildBoardViewModel, getUniqueStoryDays, getUniqueCharacters } from './boardModel';
import BoardToolbar from './BoardToolbar';
import BoardCanvas from './BoardCanvas';
import StripDetailDrawer from './StripDetailDrawer';
import SelectionSummary from '../schedule/SelectionSummary';
import './ZoomableStripboard.css';

const STORAGE_VERSION = 1;

const ZoomableStripboard = () => {
    const { scriptId } = useParams();
    const navigate = useNavigate();
    const toast = useToast();
    const { setScript } = useScript();
    const [state, dispatch] = useReducer(boardReducer, initialBoardState);
    const zoomApiRef = useRef(null);

    // Hydrate from localStorage on mount
    useEffect(() => {
        try {
            const saved = JSON.parse(localStorage.getItem(`board-state-${scriptId}`));
            if (saved && saved.version === STORAGE_VERSION) {
                dispatch({
                    type: 'HYDRATE_STATE',
                    payload: {
                        groupBy: saved.groupBy,
                        filters: saved.filters,
                    },
                });
            }
        } catch (e) {
            // Discard invalid saved state
        }
    }, [scriptId]);

    // Persist state to localStorage (debounced)
    const persistTimer = useRef(null);
    useEffect(() => {
        if (state.loading) return;
        clearTimeout(persistTimer.current);
        persistTimer.current = setTimeout(() => {
            try {
                localStorage.setItem(`board-state-${scriptId}`, JSON.stringify({
                    version: STORAGE_VERSION,
                    groupBy: state.groupBy,
                    filters: state.filters,
                }));
            } catch (e) {
                // Silently fail on storage issues
            }
        }, 500);
        return () => clearTimeout(persistTimer.current);
    }, [state.groupBy, state.filters, state.loading, scriptId]);

    // Fetch data
    useEffect(() => {
        const fetchData = async () => {
            try {
                dispatch({ type: 'SET_LOADING', payload: true });

                const [sceneData, itemsData] = await Promise.all([
                    getScenes(scriptId),
                    getScriptItems(scriptId).catch(() => ({ items: [] })),
                ]);

                // Index user items by scene_id → item_type
                const itemMap = {};
                (itemsData.items || []).forEach(item => {
                    if (!item.scene_id || item.status === 'removed') return;
                    if (!itemMap[item.scene_id]) itemMap[item.scene_id] = {};
                    if (!itemMap[item.scene_id][item.item_type]) itemMap[item.scene_id][item.item_type] = [];
                    itemMap[item.scene_id][item.item_type].push(item.item_name);
                });

                dispatch({
                    type: 'SET_SCENES',
                    payload: {
                        scenes: sceneData.scenes || [],
                        userItemsByScene: itemMap,
                    },
                });

                // Fetch metadata for breadcrumbs
                try {
                    const meta = await getScriptMetadata(scriptId);
                    dispatch({ type: 'SET_METADATA', payload: meta });
                    setScript({ id: scriptId, title: meta?.title || meta?.script_name });
                } catch (e) {
                    console.warn('Could not fetch metadata:', e);
                }
            } catch (error) {
                toast.error('Error', 'Failed to load board data');
                dispatch({ type: 'SET_LOADING', payload: false });
            }
        };

        fetchData();
    }, [scriptId]);

    // Build view model (memoized)
    const viewModel = useMemo(
        () => buildBoardViewModel(state.scenes, state.filters, state.groupBy),
        [state.scenes, state.filters, state.groupBy]
    );

    const uniqueDays = useMemo(
        () => getUniqueStoryDays(state.scenes),
        [state.scenes]
    );

    const uniqueCharacters = useMemo(
        () => getUniqueCharacters(state.scenes),
        [state.scenes]
    );

    // Optimistic update: mark scenes as scheduled on the board without a full reload
    const handleScheduled = useCallback((sceneIds, dayLabel) => {
        dispatch({ type: 'MARK_SCENES_SCHEDULED', payload: { sceneIds, dayLabel } });
    }, []);

    // Reorder handler for drag
    const handleReorder = useCallback(async (reorderedSceneIds) => {
        try {
            await reorderScenes(scriptId, reorderedSceneIds);
            dispatch({ type: 'REORDER_SUCCESS' });
            toast.success('Reordered', 'Scene order updated');
        } catch (err) {
            dispatch({ type: 'REORDER_FAILURE' });
            toast.error('Reorder failed', 'Scene order has been restored');
        }
    }, [scriptId, toast]);

    if (state.loading) {
        return (
            <div className="board-loading">
                <Loader className="spin" size={32} />
                <p>Loading board...</p>
            </div>
        );
    }

    return (
        <div className="zoomable-stripboard">
            <BoardToolbar
                groupBy={state.groupBy}
                filters={state.filters}
                uniqueDays={uniqueDays}
                uniqueCharacters={uniqueCharacters}
                totalVisible={viewModel.totalVisible}
                totalScenes={viewModel.totalScenes}
                zoomApiRef={zoomApiRef}
                dispatch={dispatch}
                toolMode={state.toolMode}
                selectedCount={state.selectedStripIds.length}
                scriptId={scriptId}
                selectedSceneIds={state.selectedStripIds}
                onScheduled={handleScheduled}
            />

            <BoardCanvas
                viewModel={viewModel}
                state={state}
                dispatch={dispatch}
                zoomApiRef={zoomApiRef}
                scriptId={scriptId}
                handleReorder={handleReorder}
                userItemsByScene={state.userItemsByScene}
            />

            {state.activeStrip && (
                <StripDetailDrawer
                    stripId={state.activeStrip}
                    scenes={state.scenes}
                    userItemsByScene={state.userItemsByScene}
                    onClose={() => dispatch({ type: 'CLOSE_DRAWER' })}
                />
            )}

            {state.selectedStripIds.length > 0 && (
                <SelectionSummary
                    scenes={state.scenes}
                    selectedSceneIds={state.selectedStripIds}
                    onClear={() => dispatch({ type: 'CLEAR_SELECTION' })}
                />
            )}
        </div>
    );
};

export default ZoomableStripboard;
