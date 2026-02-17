import React, { useCallback, useEffect, useRef, useState } from 'react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import GroupLane from './GroupLane';
import useBoardDrag from '../../hooks/useBoardDrag';
import './BoardCanvas.css';

const PAN_THRESHOLD = 5;

/**
 * BoardCanvas — 3-mode interaction layer
 *
 * GRAB mode:   Pan anywhere (including over cards). No card clicks. cursor: grab.
 * SELECT mode: Draw marquee frame to select cards. Click card to toggle. No panning.
 * MOVE mode:   Click card → drawer. Drag handle → reorder. No panning.
 */
const BoardCanvas = ({ viewModel, state, dispatch, zoomApiRef, scriptId, handleReorder, userItemsByScene }) => {
    const toolMode = state.toolMode;
    const mouseDownPos = useRef(null);
    const wasPanRef = useRef(false);

    // Marquee selection state (select mode only)
    const [marquee, setMarquee] = useState(null);
    const marqueeStartRef = useRef(null);
    const gridRef = useRef(null);

    // ─── Mouse handlers (attached to the WRAPPER, above TransformWrapper) ───

    const handleMouseDown = useCallback((e) => {
        mouseDownPos.current = { x: e.clientX, y: e.clientY };
        wasPanRef.current = false;

        // SELECT: start marquee from anywhere (empty space OR on top of cards)
        if (toolMode === 'select') {
            marqueeStartRef.current = { x: e.clientX, y: e.clientY };
        }
    }, [toolMode]);

    const handleMouseMove = useCallback((e) => {
        if (toolMode === 'select' && marqueeStartRef.current) {
            setMarquee({
                x1: marqueeStartRef.current.x,
                y1: marqueeStartRef.current.y,
                x2: e.clientX,
                y2: e.clientY,
            });
        }
    }, [toolMode]);

    const handleMouseUp = useCallback((e) => {
        // Click-vs-drag distance check (used by StripCard via didPan)
        if (mouseDownPos.current) {
            const dx = e.clientX - mouseDownPos.current.x;
            const dy = e.clientY - mouseDownPos.current.y;
            wasPanRef.current = Math.sqrt(dx * dx + dy * dy) > PAN_THRESHOLD;
        }
        mouseDownPos.current = null;

        // SELECT: finish marquee and compute which cards intersect
        if (toolMode === 'select' && marqueeStartRef.current && marquee) {
            const rect = {
                left: Math.min(marquee.x1, marquee.x2),
                top: Math.min(marquee.y1, marquee.y2),
                right: Math.max(marquee.x1, marquee.x2),
                bottom: Math.max(marquee.y1, marquee.y2),
            };
            const width = rect.right - rect.left;
            const height = rect.bottom - rect.top;

            if (width > 10 && height > 10) {
                const cards = document.querySelectorAll('.strip-card');
                const hitIds = [];
                cards.forEach(card => {
                    const cardRect = card.getBoundingClientRect();
                    if (
                        cardRect.left < rect.right &&
                        cardRect.right > rect.left &&
                        cardRect.top < rect.bottom &&
                        cardRect.bottom > rect.top
                    ) {
                        hitIds.push(card.dataset.stripId);
                    }
                });
                if (hitIds.length > 0) {
                    if (e.shiftKey) {
                        const existing = new Set(state.selectedStripIds);
                        hitIds.forEach(id => existing.add(id));
                        dispatch({ type: 'SET_SELECTED_STRIPS', payload: Array.from(existing) });
                    } else {
                        dispatch({ type: 'SET_SELECTED_STRIPS', payload: hitIds });
                    }
                }
            }
        }
        marqueeStartRef.current = null;
        setMarquee(null);
    }, [toolMode, marquee, state.selectedStripIds, dispatch]);

    // Exposed to StripCard — true if the user dragged > 5px (was a pan/marquee, not a click)
    const didPan = useCallback(() => wasPanRef.current, []);

    // Drag hook (reorder — only wired in move mode via onPointerMove/Up below)
    const { handlePointerDown, handlePointerMove, handlePointerUp, dragState } = useBoardDrag(
        state,
        dispatch,
        scriptId,
        handleReorder
    );

    // ─── Keyboard shortcuts ───
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;
            if (e.key === 'Escape') {
                if (state.selectedStripIds.length > 0) {
                    dispatch({ type: 'CLEAR_SELECTION' });
                } else if (state.activeStrip) {
                    dispatch({ type: 'CLOSE_DRAWER' });
                }
            }
            if (e.key === 's' || e.key === 'S') dispatch({ type: 'SET_TOOL_MODE', payload: 'select' });
            if (e.key === 'g' || e.key === 'G') dispatch({ type: 'SET_TOOL_MODE', payload: 'grab' });
            if (e.key === 'v' || e.key === 'V') dispatch({ type: 'SET_TOOL_MODE', payload: 'move' });
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [state.activeStrip, state.selectedStripIds, dispatch]);

    // ─── Empty states ───

    if (viewModel.totalScenes === 0) {
        return (
            <div className="board-empty-state">
                <div className="board-empty-icon">📋</div>
                <h3>No scenes found</h3>
                <p>Upload and analyze a script to see the board view.</p>
            </div>
        );
    }

    if (viewModel.totalScenes > 0 && viewModel.totalVisible === 0) {
        return (
            <div className="board-empty-state">
                <div className="board-empty-icon">🔍</div>
                <h3>No scenes match filters</h3>
                <p>Try adjusting or clearing your filters.</p>
                <button
                    className="board-clear-filters-btn"
                    onClick={() => dispatch({ type: 'CLEAR_FILTERS' })}
                >
                    Clear All Filters
                </button>
            </div>
        );
    }

    // ─── Mode-specific configuration ───

    // Cursor
    const cursorClass = toolMode === 'grab' ? 'cursor-grab'
        : toolMode === 'select' ? 'cursor-crosshair'
        : 'cursor-default';

    // Panning ONLY in grab mode. Select needs mousedown for marquee, move needs clicks for cards.
    const panningEnabled = toolMode === 'grab';

    // Marquee rect (screen coords)
    const marqueeStyle = marquee ? {
        left: Math.min(marquee.x1, marquee.x2),
        top: Math.min(marquee.y1, marquee.y2),
        width: Math.abs(marquee.x2 - marquee.x1),
        height: Math.abs(marquee.y2 - marquee.y1),
    } : null;

    return (
        <div
            className={`board-canvas-wrapper ${cursorClass}`}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
        >
            <TransformWrapper
                ref={(ref) => { if (zoomApiRef) zoomApiRef.current = ref; }}
                initialScale={1}
                minScale={0.15}
                maxScale={3}
                wheel={{ step: 0.08, smoothStep: 0.004 }}
                panning={{
                    disabled: !panningEnabled,
                    velocityDisabled: true,
                    excluded: ['drag-handle'],
                }}
                doubleClick={{ disabled: true }}
                limitToBounds={false}
            >
                <TransformComponent
                    wrapperStyle={{ width: '100%', height: '100%', overflow: 'hidden' }}
                    contentStyle={{ willChange: 'transform' }}
                >
                    <div
                        className="board-grid"
                        ref={gridRef}
                        onPointerMove={toolMode === 'move' ? handlePointerMove : undefined}
                        onPointerUp={toolMode === 'move' ? handlePointerUp : undefined}
                    >
                        {viewModel.lanes.map(lane => (
                            <GroupLane
                                key={lane.id}
                                lane={lane}
                                dispatch={dispatch}
                                dragState={dragState}
                                handlePointerDown={handlePointerDown}
                                userItemsByScene={userItemsByScene}
                                didPan={didPan}
                                toolMode={toolMode}
                                selectedStripIds={state.selectedStripIds}
                            />
                        ))}
                    </div>
                </TransformComponent>
            </TransformWrapper>

            {/* Marquee overlay (fixed position, drawn in screen coords) */}
            {marqueeStyle && (
                <div className="marquee-overlay" style={marqueeStyle} />
            )}
        </div>
    );
};

export default BoardCanvas;
