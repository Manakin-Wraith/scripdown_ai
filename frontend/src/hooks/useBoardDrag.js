import { useRef, useCallback, useState } from 'react';

/**
 * useBoardDrag — Drag reorder hook with floating ghost clone
 *
 * Uses a DEFERRED drag start: pointerdown records intent, drag only begins
 * after pointer moves > DRAG_THRESHOLD px. This lets short clicks pass through
 * to the onClick handler for opening the detail drawer.
 *
 * Ghost clone follows the cursor during drag. Drop target resolved via
 * elementFromPoint (ghost has pointer-events:none so it sees through).
 */

const DRAG_THRESHOLD = 6; // px — movement below this is a click, above starts drag

function createGhost(sourceCard, x, y) {
    const ghost = sourceCard.cloneNode(true);
    ghost.classList.add('drag-ghost');
    ghost.style.position = 'fixed';
    ghost.style.zIndex = '9999';
    ghost.style.pointerEvents = 'none';
    ghost.style.width = sourceCard.offsetWidth + 'px';
    ghost.style.opacity = '0.92';
    ghost.style.transform = 'rotate(2deg) scale(1.04)';
    ghost.style.boxShadow = '0 12px 40px rgba(79, 70, 229, 0.35), 0 0 0 2px #6366f1';
    ghost.style.transition = 'none';
    ghost.style.left = (x - sourceCard.offsetWidth / 2) + 'px';
    ghost.style.top = (y - 20) + 'px';
    document.body.appendChild(ghost);
    return ghost;
}

function moveGhost(ghost, x, y, width) {
    ghost.style.left = (x - width / 2) + 'px';
    ghost.style.top = (y - 20) + 'px';
}

function removeGhost(ghost) {
    if (ghost && ghost.parentNode) {
        ghost.parentNode.removeChild(ghost);
    }
}

export default function useBoardDrag(state, dispatch, scriptId, handleReorder) {
    const pendingRef = useRef(null);   // { stripId, laneId, fromIndex, card, startX, startY }
    const dragRef = useRef(null);      // set only after threshold exceeded
    const ghostRef = useRef(null);
    const [dragOverIndex, setDragOverIndex] = useState(null);
    const [dragOverLane, setDragOverLane] = useState(null);
    const [dropPosition, setDropPosition] = useState(null);

    // ─── Pointer Down: record intent, DON'T start drag yet ───
    const handlePointerDown = useCallback((e, stripId, laneId, index) => {
        if (state.drag.status === 'pending_api') return;

        const card = e.target.closest('.strip-card');
        if (!card) return;

        // Record intent — drag only starts after movement exceeds threshold
        pendingRef.current = {
            stripId,
            laneId,
            fromIndex: index,
            card,
            cardWidth: card.offsetWidth,
            startX: e.clientX,
            startY: e.clientY,
        };

        document.addEventListener('pointermove', onDocPointerMove);
        document.addEventListener('pointerup', onDocPointerUp);
    }, [state.drag.status]);

    // ─── Pointer Move: check threshold, then move ghost ───
    const onDocPointerMove = useCallback((e) => {
        // Phase 1: pending (haven't exceeded threshold yet)
        if (pendingRef.current && !dragRef.current) {
            const dx = e.clientX - pendingRef.current.startX;
            const dy = e.clientY - pendingRef.current.startY;
            const dist = Math.sqrt(dx * dx + dy * dy);

            if (dist < DRAG_THRESHOLD) return; // not enough movement — still a click

            // Threshold exceeded → START the drag
            const { stripId, laneId, fromIndex, card, cardWidth } = pendingRef.current;

            dragRef.current = { stripId, laneId, fromIndex, cardWidth };

            dispatch({
                type: 'DRAG_START',
                payload: { stripId, laneId, fromIndex },
            });

            ghostRef.current = createGhost(card, e.clientX, e.clientY);
            return;
        }

        // Phase 2: actively dragging
        if (!dragRef.current) return;

        if (ghostRef.current) {
            moveGhost(ghostRef.current, e.clientX, e.clientY, dragRef.current.cardWidth);
        }

        const el = document.elementFromPoint(e.clientX, e.clientY);
        if (!el) return;

        const target = el.closest('.strip-card');
        if (!target || target.classList.contains('drag-ghost')) {
            setDragOverIndex(null);
            setDragOverLane(null);
            setDropPosition(null);
            return;
        }

        const targetIndex = parseInt(target.dataset.index, 10);
        const targetLaneId = target.dataset.laneId;

        if (targetLaneId === dragRef.current.laneId) {
            const rect = target.getBoundingClientRect();
            const midY = rect.top + rect.height / 2;
            const pos = e.clientY < midY ? 'above' : 'below';

            setDragOverIndex(targetIndex);
            setDragOverLane(targetLaneId);
            setDropPosition(pos);
        }
    }, [dispatch]);

    // ─── Pointer Up: drop or click-through ───
    const onDocPointerUp = useCallback(async (e) => {
        document.removeEventListener('pointermove', onDocPointerMove);
        document.removeEventListener('pointerup', onDocPointerUp);

        // If drag never started (threshold not exceeded) → it was a CLICK
        if (!dragRef.current) {
            pendingRef.current = null;
            return; // onClick on StripCard will fire normally
        }

        // Remove ghost
        removeGhost(ghostRef.current);
        ghostRef.current = null;

        const { laneId: fromLane, fromIndex } = dragRef.current;

        setDragOverIndex(null);
        setDragOverLane(null);
        setDropPosition(null);

        // Resolve drop target
        const el = document.elementFromPoint(e.clientX, e.clientY);
        const target = el?.closest('.strip-card');

        if (!target) {
            dragRef.current = null;
            pendingRef.current = null;
            dispatch({ type: 'DRAG_END' });
            return;
        }

        const targetIndex = parseInt(target.dataset.index, 10);
        const targetLaneId = target.dataset.laneId;

        if (fromLane !== targetLaneId || fromIndex === targetIndex || isNaN(targetIndex)) {
            dragRef.current = null;
            pendingRef.current = null;
            dispatch({ type: 'DRAG_END' });
            return;
        }

        // Build reordered scene list
        const laneSceneIds = [];
        const laneContainer = document.querySelector(`[data-lane-id="${fromLane}"]`);
        if (laneContainer) {
            const cards = laneContainer.querySelectorAll('.strip-card:not(.drag-ghost)');
            cards.forEach(card => {
                laneSceneIds.push(card.dataset.stripId);
            });
        }

        if (laneSceneIds.length === 0) {
            dragRef.current = null;
            pendingRef.current = null;
            dispatch({ type: 'DRAG_END' });
            return;
        }

        const movedId = laneSceneIds[fromIndex];
        laneSceneIds.splice(fromIndex, 1);
        laneSceneIds.splice(targetIndex, 0, movedId);

        const allSceneIds = state.scenes.map(s => s.id || s.scene_id);

        let reorderedFullList;
        if (state.groupBy === 'scene_order') {
            reorderedFullList = laneSceneIds;
        } else {
            const laneSet = new Set(laneSceneIds);
            const lanePositions = [];
            allSceneIds.forEach((id, idx) => {
                if (laneSet.has(id)) lanePositions.push(idx);
            });

            reorderedFullList = [...allSceneIds];
            laneSceneIds.forEach((id, i) => {
                reorderedFullList[lanePositions[i]] = id;
            });
        }

        const reorderedScenes = reorderedFullList.map(id =>
            state.scenes.find(s => (s.id || s.scene_id) === id)
        ).filter(Boolean);

        dispatch({
            type: 'REORDER_OPTIMISTIC',
            payload: {
                laneId: fromLane,
                fromIndex,
                toIndex: targetIndex,
                reorderedScenes,
            },
        });

        dragRef.current = null;
        pendingRef.current = null;
        await handleReorder(reorderedFullList);
    }, [state.scenes, state.groupBy, dispatch, handleReorder, onDocPointerMove]);

    // No-ops — all work is done via document-level listeners
    const handlePointerMove = useCallback(() => {}, []);
    const handlePointerUp = useCallback(() => {}, []);

    return {
        handlePointerDown,
        handlePointerMove,
        handlePointerUp,
        dragState: {
            ...state.drag,
            overIndex: dragOverIndex,
            overLane: dragOverLane,
            dropPosition,
        },
    };
}
