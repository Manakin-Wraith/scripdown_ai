import React from 'react';
import { X, Sun, Moon, Sunrise, Sunset, GripVertical } from 'lucide-react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { formatEighths, getSceneEighths } from '../../utils/sceneUtils';

const TIME_ICONS = {
    DAY: Sun,
    NIGHT: Moon,
    DAWN: Sunrise,
    DUSK: Sunset,
};

const ScheduleSceneCard = ({ dayScene, onRemove, isDragOverlay = false, isSelected = false, onToggleSelect }) => {
    const scene = dayScene.scene || dayScene.scenes || {};
    const sceneId = dayScene.scene_id;

    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({
        id: sceneId,
        disabled: isDragOverlay,
    });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.35 : 1,
    };

    const sceneNum = scene.scene_number || '?';
    const intExt = scene.int_ext || '';
    const setting = scene.setting || '';
    const timeOfDay = scene.time_of_day || '';
    const eighths = getSceneEighths(scene);
    const storyDay = scene.story_day || '';

    const intExtClass = intExt === 'INT' ? 'int' : intExt === 'EXT' ? 'ext' : '';
    const TimeIcon = TIME_ICONS[timeOfDay] || null;

    const characters = Array.isArray(scene.characters) ? scene.characters : [];
    const castCount = characters.length;

    const handleCardClick = (e) => {
        // Don't select if clicking the drag handle, remove button, or during drag
        if (isDragging || isDragOverlay) return;
        if (e.target.closest('.ssc-drag-handle') || e.target.closest('.ssc-remove')) return;
        onToggleSelect?.();
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={`schedule-scene-card ${intExtClass} ${isDragging ? 'dragging' : ''} ${isDragOverlay ? 'overlay' : ''} ${isSelected ? 'selected' : ''}`}
            onClick={handleCardClick}
        >
            <div className="ssc-header">
                <span className="ssc-drag-handle" {...attributes} {...listeners}>
                    <GripVertical size={12} />
                </span>
                <span className="ssc-number">{sceneNum}</span>
                <span className={`ssc-ie ${intExtClass}`}>{intExt}</span>
                <span className="ssc-eighths">{formatEighths(eighths)}</span>
                <button className="ssc-remove" onClick={onRemove} title="Remove from day">
                    <X size={12} />
                </button>
            </div>
            <div className="ssc-setting" title={setting}>
                {setting || 'Unknown location'}
            </div>
            <div className="ssc-meta">
                {TimeIcon && <TimeIcon size={11} />}
                {timeOfDay && <span className="ssc-time">{timeOfDay}</span>}
                {storyDay && <span className="ssc-story-day">D{storyDay}</span>}
                {castCount > 0 && <span className="ssc-cast">{castCount} cast</span>}
            </div>
        </div>
    );
};

export default ScheduleSceneCard;
