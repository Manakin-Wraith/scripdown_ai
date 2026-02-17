import React from 'react';
import { GripVertical, Users, Package, Shirt, Car, Sparkles, Volume2 } from 'lucide-react';
import { formatEighths } from '../../utils/sceneUtils';
import './StripCard.css';

/**
 * StripCard — Single scene strip on the board.
 * Renders ALL detail sections; CSS controls visibility via [data-zoom-level].
 * Explicit data attributes for drag resolution (§7.2).
 */
const StripCard = ({ strip, index, laneId, dispatch, dragState, handlePointerDown, userItems, didPan, toolMode, isSelected }) => {
    const isDragging = dragState?.status === 'dragging' && dragState?.stripId === strip.id;
    const isPendingApi = dragState?.status === 'pending_api';
    const isAnyDragging = dragState?.status === 'dragging';

    // Drop indicator: is the pointer hovering over THIS card during a drag?
    const isDropTarget = isAnyDragging
        && dragState?.overIndex === index
        && dragState?.overLane === laneId
        && dragState?.stripId !== strip.id;
    const dropPos = isDropTarget ? dragState?.dropPosition : null;

    // INT/EXT color class
    const intExtClass = strip.intExt === 'INT' ? 'strip-int'
        : strip.intExt === 'EXT' ? 'strip-ext'
        : 'strip-other';

    // Merge AI + user characters
    const allChars = [...(strip.characters || []), ...(userItems.characters || [])];
    const charPreview = allChars.slice(0, 3).join(', ');
    const moreChars = allChars.length > 3 ? ` +${allChars.length - 3}` : '';

    // Breakdown summary counts
    const allProps = [...(strip.props || []), ...(userItems.props || [])];
    const allWardrobe = [...(strip.wardrobe || []), ...(userItems.wardrobe || [])];
    const allVehicles = [...(strip.vehicles || []), ...(userItems.vehicles || [])];
    const allSpecialFx = [...(strip.specialFx || []), ...(userItems.special_fx || [])];
    const allSound = [...(strip.sound || []), ...(userItems.sound || [])];

    const handleClick = (e) => {
        if (e.target.closest('.drag-handle')) return;
        if (didPan && didPan()) return;
        // Don't open drawer if we just finished dragging
        if (isAnyDragging) return;

        if (toolMode === 'select') {
            dispatch({ type: 'TOGGLE_SELECT_STRIP', payload: strip.id });
            return;
        }

        if (toolMode === 'move') {
            dispatch({ type: 'OPEN_DRAWER', payload: strip.id });
            return;
        }
    };

    // Initiate drag: In Move mode → entire card. Otherwise → only drag-handle fires this.
    const handleCardPointerDown = (e) => {
        if (isPendingApi) return;
        if (toolMode === 'move') {
            // Entire card is draggable in move mode
            handlePointerDown(e, strip.id, laneId, index);
        }
        // In other modes, only the drag-handle (below) initiates drag
    };

    const classes = [
        'strip-card',
        intExtClass,
        isDragging ? 'dragging' : '',
        strip.isOmitted ? 'omitted' : '',
        isSelected ? 'selected' : '',
        toolMode === 'move' ? 'move-mode' : '',
        dropPos === 'above' ? 'drop-above' : '',
        dropPos === 'below' ? 'drop-below' : '',
    ].filter(Boolean).join(' ');

    return (
        <div
            className={classes}
            data-strip-id={strip.id}
            data-lane-id={laneId}
            data-index={index}
            onClick={handleClick}
            onPointerDown={handleCardPointerDown}
        >
            {/* Header — always visible at all zoom levels */}
            <div className="strip-header">
                <div
                    className="drag-handle"
                    onPointerDown={(e) => {
                        if (isPendingApi) return;
                        if (toolMode === 'move') return; // card-level handler takes over in move mode
                        e.stopPropagation();
                        handlePointerDown(e, strip.id, laneId, index);
                    }}
                    title={isPendingApi ? 'Reorder in progress...' : 'Drag to reorder'}
                >
                    <GripVertical size={16} />
                </div>
                <span className="strip-scene-number">{strip.sceneNumber}</span>
                <span className={`strip-ie-badge ${strip.intExt === 'INT' ? 'int' : 'ext'}`}>
                    {strip.intExt}
                </span>
            </div>

            {/* Body — hidden at micro zoom */}
            <div className="strip-body">
                <div className="strip-setting" title={strip.setting}>
                    {strip.setting || 'Unknown'}
                </div>
                <div className="strip-meta">
                    <span className="strip-time">{strip.timeOfDay}</span>
                    <span className="strip-pages">{formatEighths(strip.pageLengthEighths)}</span>
                </div>
                {allChars.length > 0 && (
                    <div className="strip-cast-preview">
                        <Users size={11} />
                        <span>{charPreview}{moreChars}</span>
                    </div>
                )}
            </div>

            {/* Footer — hidden at micro zoom */}
            <div className="strip-footer">
                {strip.storyDay && (
                    <span className={`strip-day-badge timeline-${(strip.timelineCode || 'PRESENT').toLowerCase()}`}>
                        D{strip.storyDay}
                    </span>
                )}
            </div>

            {/* Breakdown summary — only visible at detailed zoom */}
            <div className="strip-breakdown-summary">
                {allChars.length > 0 && (
                    <span className="bd-count" title="Cast"><Users size={10} /> {allChars.length}</span>
                )}
                {allProps.length > 0 && (
                    <span className="bd-count" title="Props"><Package size={10} /> {allProps.length}</span>
                )}
                {allWardrobe.length > 0 && (
                    <span className="bd-count" title="Wardrobe"><Shirt size={10} /> {allWardrobe.length}</span>
                )}
                {allVehicles.length > 0 && (
                    <span className="bd-count" title="Vehicles"><Car size={10} /> {allVehicles.length}</span>
                )}
                {allSpecialFx.length > 0 && (
                    <span className="bd-count" title="Special FX"><Sparkles size={10} /> {allSpecialFx.length}</span>
                )}
                {allSound.length > 0 && (
                    <span className="bd-count" title="Sound"><Volume2 size={10} /> {allSound.length}</span>
                )}
            </div>
        </div>
    );
};

export default React.memo(StripCard);
