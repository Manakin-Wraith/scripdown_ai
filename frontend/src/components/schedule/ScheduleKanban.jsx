import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { Plus } from 'lucide-react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
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

// ── Pure helpers for optimistic state mutations ───────────────────────────────

function reorderWithinDay(days, dayId, activeId, overId) {
    return days.map(day => {
        if (day.id !== dayId) return day;
        const scenes = [...(day.scenes || [])];
        const oldIdx = scenes.findIndex(ds => ds.scene_id === activeId);
        const newIdx = scenes.findIndex(ds => ds.scene_id === overId);
        if (oldIdx === -1 || newIdx === -1) return day;
        const [moved] = scenes.splice(oldIdx, 1);
        scenes.splice(newIdx, 0, moved);
        return { ...day, scenes };
    });
}

function moveBetweenDays(days, sourceDayId, targetDayId, activeId, targetIndex) {
    let movedScene = null;
    const next = days.map(day => {
        if (day.id === sourceDayId) {
            const scenes = (day.scenes || []).filter(ds => {
                if (ds.scene_id === activeId) { movedScene = ds; return false; }
                return true;
            });
            return { ...day, scenes };
        }
        return day;
    });
    if (!movedScene) return days;
    return next.map(day => {
        if (day.id !== targetDayId) return day;
        const scenes = [...(day.scenes || [])];
        const insertAt = targetIndex != null && targetIndex >= 0 ? targetIndex : scenes.length;
        scenes.splice(insertAt, 0, { ...movedScene, shooting_day_id: targetDayId });
        return { ...day, scenes };
    });
}

// ─────────────────────────────────────────────────────────────────────────────

const ScheduleKanban = ({ scheduleId, days: propDays, refreshDays, zoomApiRef }) => {
    // Mirror prop days into local state so we can apply optimistic updates instantly
    const [localDays, setLocalDays] = useState(propDays);
    const [activeItem, setActiveItem] = useState(null);
    const [selectedSceneIds, setSelectedSceneIds] = useState(new Set());
    const [isDragging, setIsDragging] = useState(false);

    // Keep local state in sync when parent refreshes (after rollback or add-day)
    useEffect(() => {
        setLocalDays(propDays);
    }, [propDays]);

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

    // Build a lookup: sceneId → { dayId, dayScene } — derived from localDays
    const sceneMap = useMemo(() => {
        const map = {};
        localDays.forEach(day => {
            (day.scenes || []).forEach(ds => {
                map[ds.scene_id] = { dayId: day.id, dayScene: ds };
            });
        });
        return map;
    }, [localDays]);

    const findDayForScene = useCallback((sceneId) => {
        return sceneMap[sceneId]?.dayId || null;
    }, [sceneMap]);

    const handleDragStart = useCallback((event) => {
        const { active } = event;
        const info = sceneMap[active.id];
        if (info) setActiveItem(info.dayScene);
        setIsDragging(true);
    }, [sceneMap]);

    const handleDragEnd = useCallback(async (event) => {
        const { active, over } = event;
        setActiveItem(null);
        setIsDragging(false);

        if (!over || active.id === over.id) return;

        const sourceDayId = findDayForScene(active.id);
        let targetDayId = findDayForScene(over.id);
        let targetIndex = null;

        if (!targetDayId && typeof over.id === 'string' && over.id.startsWith('day-')) {
            targetDayId = over.id.replace('day-', '');
            targetIndex = 0;
        }

        if (!sourceDayId || !targetDayId) return;

        if (sourceDayId === targetDayId) {
            // ── Reorder within same day ──────────────────────────────────────
            const day = localDays.find(d => d.id === sourceDayId);
            if (!day) return;
            const sceneIds = (day.scenes || []).map(ds => ds.scene_id);
            const oldIdx = sceneIds.indexOf(active.id);
            const newIdx = sceneIds.indexOf(over.id);
            if (oldIdx === -1 || newIdx === -1 || oldIdx === newIdx) return;

            // 1. Optimistic update — instant
            const optimistic = reorderWithinDay(localDays, sourceDayId, active.id, over.id);
            setLocalDays(optimistic);

            // 2. Persist in background
            const reorderedIds = optimistic.find(d => d.id === sourceDayId)
                .scenes.map(ds => ds.scene_id);
            try {
                await reorderDayScenes(sourceDayId, reorderedIds);
            } catch (err) {
                console.error('Reorder failed, rolling back:', err);
                await refreshDays(); // rollback via parent
            }
        } else {
            // ── Move between days ────────────────────────────────────────────
            const targetDay = localDays.find(d => d.id === targetDayId);
            const targetSceneIds = (targetDay?.scenes || []).map(ds => ds.scene_id);
            const overIdx = targetSceneIds.indexOf(over.id);
            targetIndex = overIdx >= 0 ? overIdx : targetSceneIds.length;

            // 1. Optimistic update — instant
            const optimistic = moveBetweenDays(localDays, sourceDayId, targetDayId, active.id, targetIndex);
            setLocalDays(optimistic);

            // 2. Persist in background
            try {
                await moveSceneToDay(sourceDayId, active.id, targetDayId, targetIndex);
            } catch (err) {
                console.error('Move failed, rolling back:', err);
                await refreshDays(); // rollback via parent
            }
        }
    }, [localDays, findDayForScene, refreshDays]);

    const handleAddDay = async () => {
        try {
            await createShootingDay(scheduleId, [], '');
            await refreshDays();
        } catch (err) {
            console.error('Failed to create day:', err);
        }
    };

    // Bulk-move: optimistic batch then parallel API calls
    const handleBulkMove = useCallback(async (targetDayId, sceneIds) => {
        // 1. Optimistic: move all scenes at once
        let optimistic = localDays;
        sceneIds.forEach(sceneId => {
            const sourceDayId = sceneMap[sceneId]?.dayId;
            if (!sourceDayId || sourceDayId === targetDayId) return;
            optimistic = moveBetweenDays(optimistic, sourceDayId, targetDayId, sceneId, null);
        });
        setLocalDays(optimistic);
        clearSelection();

        // 2. Parallel API calls
        const moves = sceneIds
            .filter(sceneId => {
                const sourceDayId = sceneMap[sceneId]?.dayId;
                return sourceDayId && sourceDayId !== targetDayId;
            })
            .map(sceneId =>
                moveSceneToDay(sceneMap[sceneId].dayId, sceneId, targetDayId, null)
                    .catch(err => console.error(`Failed to move scene ${sceneId}:`, err))
            );

        await Promise.all(moves);
        // Sync to get server-authoritative order after bulk move
        await refreshDays();
    }, [localDays, sceneMap, clearSelection, refreshDays]);

    return (
        <DndContext
            sensors={sensors}
            collisionDetection={kanbanCollision}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
        >
            <div className="kanban-board">
                <TransformWrapper
                    ref={(ref) => { if (zoomApiRef) zoomApiRef.current = ref; }}
                    initialScale={1}
                    minScale={0.2}
                    maxScale={2.5}
                    wheel={{ step: 0.08, smoothStep: 0.004 }}
                    panning={{
                        disabled: isDragging,
                        velocityDisabled: true,
                    }}
                    doubleClick={{ disabled: true }}
                    limitToBounds={false}
                    wrapperStyle={{ width: '100%', height: '100%' }}
                >
                    <TransformComponent
                        wrapperStyle={{ width: '100%', height: '100%', overflow: 'visible' }}
                        contentStyle={{ willChange: 'transform' }}
                    >
                        <div className="kanban-columns">
                            {localDays.map(day => (
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
                    </TransformComponent>
                </TransformWrapper>
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
                    days={localDays}
                    selectedSceneIds={selectedSceneIds}
                    onClear={clearSelection}
                    onBulkMove={handleBulkMove}
                />
            )}
        </DndContext>
    );
};

export default ScheduleKanban;
