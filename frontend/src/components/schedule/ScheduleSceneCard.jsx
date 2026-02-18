import React, { useState, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X, Sun, Moon, Sunrise, Sunset, GripVertical, MapPin, Users, FileText, Clock, Clapperboard, Tag } from 'lucide-react';
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
    const cardRef = useRef(null);
    const [tooltipPos, setTooltipPos] = useState(null);

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

    // Extra scene data for tooltip
    const props = Array.isArray(scene.props) ? scene.props : [];
    const wardrobe = Array.isArray(scene.wardrobe) ? scene.wardrobe : [];
    const vehicles = Array.isArray(scene.vehicles) ? scene.vehicles : [];
    const synopsis = scene.synopsis || scene.summary || scene.description || '';
    const pageStart = scene.page_start;
    const pageEnd = scene.page_end;
    const locationParent = scene.location_parent || scene.location_hierarchy?.[0] || '';
    const timelineCode = scene.timeline_code || '';

    const handleCardClick = (e) => {
        // Don't select if clicking the drag handle, remove button, or during drag
        if (isDragging || isDragOverlay) return;
        if (e.target.closest('.ssc-drag-handle') || e.target.closest('.ssc-remove')) return;
        onToggleSelect?.();
    };

    const handleMouseEnter = useCallback(() => {
        if (isDragging || isDragOverlay || !cardRef.current) return;
        const rect = cardRef.current.getBoundingClientRect();
        setTooltipPos({ top: rect.top, left: rect.right + 10 });
    }, [isDragging, isDragOverlay]);

    const handleMouseLeave = useCallback(() => {
        setTooltipPos(null);
    }, []);

    return (
        <>
        <div
            ref={(el) => { setNodeRef(el); cardRef.current = el; }}
            style={style}
            className={`schedule-scene-card ${intExtClass} ${isDragging ? 'dragging' : ''} ${isDragOverlay ? 'overlay' : ''} ${isSelected ? 'selected' : ''}`}
            onClick={handleCardClick}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
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

            {/* Tooltip rendered via portal — see bottom of component */}
        </div>

        {tooltipPos && createPortal(
            <div
                className="ssc-tooltip ssc-tooltip-portal"
                style={{ position: 'fixed', top: tooltipPos.top, left: tooltipPos.left, zIndex: 99999 }}
            >
                <div className="ssc-tt-header">
                    <span className="ssc-tt-scene-num">Scene {sceneNum}</span>
                    {intExt && <span className={`ssc-tt-ie ${intExtClass}`}>{intExt}</span>}
                    {timelineCode && <span className="ssc-tt-timeline">{timelineCode}</span>}
                    <span className="ssc-tt-pages">{formatEighths(eighths)} pgs</span>
                </div>

                <div className="ssc-tt-row">
                    <MapPin size={11} />
                    <span>{[intExt, setting, timeOfDay].filter(Boolean).join(' · ') || 'Unknown location'}</span>
                </div>

                {locationParent && locationParent !== setting && (
                    <div className="ssc-tt-row ssc-tt-sub">
                        <span className="ssc-tt-label">Parent</span>
                        <span>{locationParent}</span>
                    </div>
                )}

                {(pageStart || pageEnd) && (
                    <div className="ssc-tt-row">
                        <FileText size={11} />
                        <span>Pages {pageStart}{pageEnd && pageEnd !== pageStart ? `–${pageEnd}` : ''}</span>
                        {storyDay && <span className="ssc-tt-badge">Day {storyDay}</span>}
                    </div>
                )}

                {synopsis && (
                    <div className="ssc-tt-synopsis">{synopsis}</div>
                )}

                {castCount > 0 && (
                    <div className="ssc-tt-section">
                        <div className="ssc-tt-section-label">
                            <Users size={11} /> Cast ({castCount})
                        </div>
                        <div className="ssc-tt-tags">
                            {characters.slice(0, 12).map((c, i) => (
                                <span key={i} className="ssc-tt-tag ssc-tt-cast">
                                    {typeof c === 'string' ? c : c?.name || c}
                                </span>
                            ))}
                            {castCount > 12 && <span className="ssc-tt-more">+{castCount - 12}</span>}
                        </div>
                    </div>
                )}

                {props.length > 0 && (
                    <div className="ssc-tt-section">
                        <div className="ssc-tt-section-label">
                            <Tag size={11} /> Props
                        </div>
                        <div className="ssc-tt-tags">
                            {props.slice(0, 8).map((p, i) => (
                                <span key={i} className="ssc-tt-tag ssc-tt-prop">{p}</span>
                            ))}
                            {props.length > 8 && <span className="ssc-tt-more">+{props.length - 8}</span>}
                        </div>
                    </div>
                )}

                {wardrobe.length > 0 && (
                    <div className="ssc-tt-section">
                        <div className="ssc-tt-section-label">
                            <Clapperboard size={11} /> Wardrobe
                        </div>
                        <div className="ssc-tt-tags">
                            {wardrobe.slice(0, 6).map((w, i) => (
                                <span key={i} className="ssc-tt-tag ssc-tt-wardrobe">{w}</span>
                            ))}
                            {wardrobe.length > 6 && <span className="ssc-tt-more">+{wardrobe.length - 6}</span>}
                        </div>
                    </div>
                )}

                {vehicles.length > 0 && (
                    <div className="ssc-tt-section">
                        <div className="ssc-tt-section-label">
                            <Clock size={11} /> Vehicles
                        </div>
                        <div className="ssc-tt-tags">
                            {vehicles.slice(0, 6).map((v, i) => (
                                <span key={i} className="ssc-tt-tag ssc-tt-vehicle">{v}</span>
                            ))}
                        </div>
                    </div>
                )}
            </div>,
            document.body
        )}
        </>
    );
};

export default ScheduleSceneCard;
