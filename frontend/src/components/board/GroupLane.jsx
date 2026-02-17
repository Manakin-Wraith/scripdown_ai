import React from 'react';
import StripCard from './StripCard';

const GroupLane = ({ lane, dispatch, dragState, handlePointerDown, userItemsByScene, didPan, toolMode, selectedStripIds }) => {
    return (
        <div className="group-lane" data-lane-id={lane.id}>
            <div className="group-header">
                <span className="group-label">{lane.label}</span>
                <span className="group-count">{lane.count}</span>
            </div>
            <div className="group-strips">
                {lane.strips.map((strip, index) => (
                    <StripCard
                        key={strip.id}
                        strip={strip}
                        index={index}
                        laneId={lane.id}
                        dispatch={dispatch}
                        dragState={dragState}
                        handlePointerDown={handlePointerDown}
                        userItems={userItemsByScene?.[strip.id] || {}}
                        didPan={didPan}
                        toolMode={toolMode}
                        isSelected={selectedStripIds?.includes(strip.id)}
                    />
                ))}
            </div>
        </div>
    );
};

export default React.memo(GroupLane);
