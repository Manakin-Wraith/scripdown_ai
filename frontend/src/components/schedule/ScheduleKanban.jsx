import React, { useState, useCallback, useMemo } from 'react';
import { Plus } from 'lucide-react';
import {
    DndContext,
    DragOverlay,
    PointerSensor,
    useSensor,
    useSensors,
    pointerWithin,
    rectIntersection,
} from '@dnd-kit/core';
import {
    createShootingDay,
    reorderDayScenes,
    moveSceneToDay,
} from '../../services/apiService';
import DayColumn from './DayColumn';
import ScheduleSceneCard from './ScheduleSceneCard';
import SelectionSummary from './SelectionSummary';

// Custom collision: try pointerWithin first (works for empty droppable
// containers), then fall back to rectIntersection for sortable items.
function kanbanCollision(args) {
    const pointerHits = pointerWithin(args);
    if (pointerHits.length > 0) {
        // Prefer sortable items (scene cards) over container droppables
        const sortableHit = pointerHits.find(h => !String(h.id).startsWith('day-'));
        if (sortableHit) return [sortableHit];
        // Otherwise return the container (empty column)
        return [pointerHits[0]];
    }
    // Fallback to rect intersection
    return rectIntersection(args);
}

const ScheduleKanban = ({ scheduleId, days, refreshDays }) => {
    const [activeItem, setActiveItem] = useState(null);
    const [selectedSceneIds, setSelectedSceneIds] = useState(new Set());

    const toggleSelect = useCallback((sceneId) => {
        setSelectedSceneIds(prev => {
            const next = new Set(prev);
            if (next.has(sceneId)) next.delete(sceneId);
            else next.add(sceneId);
            return next;
        });
    }, []);

    const clearSelection = useCallback(() => setSelectedSceneIds(new Set()), []);

    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
    );

    // Build a lookup: sceneId → { dayId, dayScene }
    const sceneMap = useMemo(() => {
        const map = {};
        days.forEach(day => {
            (day.scenes || []).forEach(ds => {
                map[ds.scene_id] = { dayId: day.id, dayScene: ds };
            });
        });
        return map;
    }, [days]);

    // Find which day a sortable id belongs to
    const findDayForScene = useCallback((sceneId) => {
        return sceneMap[sceneId]?.dayId || null;
    }, [sceneMap]);

    const handleDragStart = useCallback((event) => {
        const { active } = event;
        const info = sceneMap[active.id];
        if (info) {
            setActiveItem(info.dayScene);
        }
    }, [sceneMap]);

    const handleDragEnd = useCallback(async (event) => {
        const { active, over } = event;
        setActiveItem(null);

        if (!over || active.id === over.id) return;

        const sourceDayId = findDayForScene(active.id);
        // over.id could be a scene_id or a day container id (prefixed with "day-")
        let targetDayId = findDayForScene(over.id);
        let targetIndex = null;

        // If dropped on a day container itself (empty column)
        if (!targetDayId && typeof over.id === 'string' && over.id.startsWith('day-')) {
            targetDayId = over.id.replace('day-', '');
            targetIndex = 0;
        }

        if (!sourceDayId || !targetDayId) return;

        if (sourceDayId === targetDayId) {
            // Reorder within same day
            const day = days.find(d => d.id === sourceDayId);
            if (!day) return;
            const sceneIds = (day.scenes || []).map(ds => ds.scene_id);
            const oldIdx = sceneIds.indexOf(active.id);
            const newIdx = sceneIds.indexOf(over.id);
            if (oldIdx === -1 || newIdx === -1 || oldIdx === newIdx) return;

            // Optimistic reorder
            sceneIds.splice(oldIdx, 1);
            sceneIds.splice(newIdx, 0, active.id);

            try {
                await reorderDayScenes(sourceDayId, sceneIds);
                await refreshDays();
            } catch (err) {
                console.error('Reorder failed:', err);
                await refreshDays();
            }
        } else {
            // Move between days
            const targetDay = days.find(d => d.id === targetDayId);
            const targetSceneIds = (targetDay?.scenes || []).map(ds => ds.scene_id);
            const overIdx = targetSceneIds.indexOf(over.id);
            targetIndex = overIdx >= 0 ? overIdx : targetSceneIds.length;

            try {
                await moveSceneToDay(sourceDayId, active.id, targetDayId, targetIndex);
                await refreshDays();
            } catch (err) {
                console.error('Move failed:', err);
                await refreshDays();
            }
        }
    }, [days, findDayForScene, refreshDays]);

    const handleAddDay = async () => {
        try {
            await createShootingDay(scheduleId, [], '');
            await refreshDays();
        } catch (err) {
            console.error('Failed to create day:', err);
        }
    };

    return (
        <DndContext
            sensors={sensors}
            collisionDetection={kanbanCollision}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
        >
            <div className="kanban-board">
                <div className="kanban-columns">
                    {days.map(day => (
                        <DayColumn
                            key={day.id}
                            day={day}
                            refreshDays={refreshDays}
                            selectedSceneIds={selectedSceneIds}
                            onToggleSelect={toggleSelect}
                        />
                    ))}

                    {/* Add Day column */}
                    <div className="kanban-add-col">
                        <button className="kanban-add-day-btn" onClick={handleAddDay}>
                            <Plus size={18} />
                            <span>Add Day</span>
                        </button>
                    </div>
                </div>
            </div>

            <DragOverlay dropAnimation={null}>
                {activeItem ? (
                    <div className="schedule-scene-card-overlay">
                        <ScheduleSceneCard dayScene={activeItem} onRemove={() => {}} isDragOverlay />
                    </div>
                ) : null}
            </DragOverlay>

            {selectedSceneIds.size > 0 && (
                <SelectionSummary
                    days={days}
                    selectedSceneIds={selectedSceneIds}
                    onClear={clearSelection}
                />
            )}
        </DndContext>
    );
};

export default ScheduleKanban;
