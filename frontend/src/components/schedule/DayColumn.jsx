import React, { useState, useMemo, useRef } from 'react';
import { Trash2, FileText, Users, MapPin, CalendarDays } from 'lucide-react';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useDroppable } from '@dnd-kit/core';
import { removeSceneFromDay, deleteShootingDay, updateShootingDay } from '../../services/apiService';
import ScheduleSceneCard from './ScheduleSceneCard';
import { formatEighths, getSceneEighths } from '../../utils/sceneUtils';

const DayColumn = ({ day, refreshDays, selectedSceneIds, onToggleSelect }) => {
    const [editingDate, setEditingDate] = useState(false);
    const [localDate, setLocalDate] = useState(day.shoot_date || '');
    const dateInputRef = useRef(null);

    const scenes = (day.scenes || []).map(ds => ({
        ...ds,
        scene: ds.scenes || ds.scene || {},
    }));

    const sceneIds = useMemo(() => scenes.map(ds => ds.scene_id), [scenes]);

    // Make the column body a droppable target (for empty columns)
    const { setNodeRef: setDropRef, isOver } = useDroppable({
        id: `day-${day.id}`,
    });

    // Stats
    const totalEighths = scenes.reduce((sum, ds) => sum + getSceneEighths(ds.scene), 0);

    const uniqueLocations = new Set(
        scenes.map(ds => ds.scene?.setting).filter(Boolean)
    );

    const uniqueCharacters = new Set();
    scenes.forEach(ds => {
        const chars = ds.scene?.characters;
        if (Array.isArray(chars)) {
            chars.forEach(c => {
                const name = typeof c === 'string' ? c : c?.name;
                if (name) uniqueCharacters.add(name);
            });
        }
    });

    const handleRemoveScene = async (sceneId) => {
        try {
            await removeSceneFromDay(day.id, sceneId);
            await refreshDays();
        } catch (err) {
            console.error('Failed to remove scene:', err);
        }
    };

    const handleDeleteDay = async () => {
        if (!window.confirm(`Delete Day ${day.day_number} and unschedule all its scenes?`)) return;
        try {
            await deleteShootingDay(day.id);
            await refreshDays();
        } catch (err) {
            console.error('Failed to delete day:', err);
        }
    };

    const handleSaveDate = async (value) => {
        setEditingDate(false);
        const trimmed = (value || '').trim();
        if (trimmed === (day.shoot_date || '')) return;
        setLocalDate(trimmed);
        try {
            await updateShootingDay(day.id, { shoot_date: trimmed || null });
            await refreshDays();
        } catch (err) {
            console.error('Failed to update shoot date:', err);
            setLocalDate(day.shoot_date || '');
        }
    };

    const formatDisplayDate = (dateStr) => {
        if (!dateStr) return null;
        try {
            return new Date(dateStr + 'T00:00:00').toLocaleDateString(undefined, {
                month: 'short', day: 'numeric', year: 'numeric',
            });
        } catch {
            return dateStr;
        }
    };

    const statusClass = day.status === 'confirmed' ? 'confirmed' : day.status === 'wrapped' ? 'wrapped' : '';

    return (
        <div className={`kanban-column ${statusClass}`}>
            {/* Column header */}
            <div className="kanban-col-header">
                <div className="kanban-col-title">
                    <span className="kanban-day-number">Day {day.day_number}</span>
                    {editingDate ? (
                        <input
                            ref={dateInputRef}
                            type="date"
                            className="kanban-date-input"
                            defaultValue={localDate}
                            autoFocus
                            onBlur={e => handleSaveDate(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === 'Enter') handleSaveDate(e.target.value);
                                if (e.key === 'Escape') setEditingDate(false);
                            }}
                        />
                    ) : (
                        <button
                            className="kanban-day-date-btn"
                            onClick={() => setEditingDate(true)}
                            title="Set shoot date"
                        >
                            <CalendarDays size={11} />
                            <span>{localDate ? formatDisplayDate(localDate) : 'Add date'}</span>
                        </button>
                    )}
                </div>
                <div className="kanban-col-actions">
                    <span className="kanban-scene-count">{scenes.length}</span>
                    <button className="kanban-delete-day" onClick={handleDeleteDay} title="Delete this day">
                        <Trash2 size={13} />
                    </button>
                </div>
            </div>

            {/* Scene cards — sortable + droppable */}
            <SortableContext items={sceneIds} strategy={verticalListSortingStrategy}>
                <div
                    ref={setDropRef}
                    className={`kanban-col-body ${isOver ? 'kanban-col-over' : ''}`}
                >
                    {scenes.length === 0 ? (
                        <div className="kanban-col-empty">
                            Drop scenes here
                        </div>
                    ) : (
                        scenes.map(ds => (
                            <ScheduleSceneCard
                                key={ds.scene_id}
                                dayScene={ds}
                                onRemove={() => handleRemoveScene(ds.scene_id)}
                                isSelected={selectedSceneIds?.has(ds.scene_id)}
                                onToggleSelect={() => onToggleSelect?.(ds.scene_id)}
                            />
                        ))
                    )}
                </div>
            </SortableContext>

            {/* Column footer stats */}
            <div className="kanban-col-footer">
                <div className="kanban-stat" title="Page count">
                    <FileText size={12} />
                    <span>{totalEighths > 0 ? formatEighths(totalEighths) : '0'} pgs</span>
                </div>
                <div className="kanban-stat" title="Cast members">
                    <Users size={12} />
                    <span>{uniqueCharacters.size}</span>
                </div>
                <div className="kanban-stat" title="Locations">
                    <MapPin size={12} />
                    <span>{uniqueLocations.size}</span>
                </div>
            </div>
        </div>
    );
};

export default DayColumn;
