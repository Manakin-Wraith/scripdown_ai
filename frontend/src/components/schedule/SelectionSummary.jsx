import React, { useMemo, useState, useRef, useCallback } from 'react';
import { X, FileText, Users, MapPin, Sun, Moon, Sunrise, Sunset, Clapperboard, ArrowRight, Loader, GripHorizontal } from 'lucide-react';
import { formatEighths, getSceneEighths } from '../../utils/sceneUtils';
import './SelectionSummary.css';

/**
 * SelectionSummary — works with two data shapes:
 *   1. Board: pass `scenes` (flat array) + `selectedSceneIds` (array or Set of scene.id)
 *   2. Kanban: pass `days` (array with .scenes[]) + `selectedSceneIds` (Set of scene_id)
 *
 * Kanban-only: pass `onBulkMove(targetDayId, sceneIds)` to enable "Move to Day" action.
 */
const SelectionSummary = ({ scenes: rawScenes, days, selectedSceneIds, onClear, onBulkMove }) => {
    const [targetDayId, setTargetDayId] = useState('');
    const [moving, setMoving] = useState(false);

    // Draggable popup position — null = default CSS centering
    const [pos, setPos] = useState(null);
    const dragRef = useRef(null);

    const handleDragPointerDown = useCallback((e) => {
        e.preventDefault();
        dragRef.current = { startX: e.clientX, startY: e.clientY, startPos: pos };

        const onMove = (ev) => {
            if (!dragRef.current) return;
            const dx = ev.clientX - dragRef.current.startX;
            const dy = ev.clientY - dragRef.current.startY;
            const base = dragRef.current.startPos || { x: 0, y: 0 };
            setPos({ x: base.x + dx, y: base.y + dy });
        };

        const onUp = () => {
            dragRef.current = null;
            window.removeEventListener('pointermove', onMove);
            window.removeEventListener('pointerup', onUp);
        };

        window.addEventListener('pointermove', onMove);
        window.addEventListener('pointerup', onUp);
    }, [pos]);

    const stats = useMemo(() => {
        const idSet = selectedSceneIds instanceof Set
            ? selectedSceneIds
            : new Set(Array.isArray(selectedSceneIds) ? selectedSceneIds : []);

        const selected = [];

        if (rawScenes) {
            // Board mode — flat scene array, ids match scene.id
            rawScenes.forEach(s => {
                if (idSet.has(s.id)) selected.push(s);
            });
        } else if (days) {
            // Kanban mode — nested in days
            days.forEach(day => {
                (day.scenes || []).forEach(ds => {
                    if (idSet.has(ds.scene_id)) {
                        selected.push(ds.scenes || ds.scene || {});
                    }
                });
            });
        }

        const totalEighths = selected.reduce((sum, s) => sum + getSceneEighths(s), 0);

        const characters = new Set();
        selected.forEach(s => {
            if (Array.isArray(s.characters)) {
                s.characters.forEach(c => {
                    const name = typeof c === 'string' ? c : c?.name;
                    if (name) characters.add(name);
                });
            }
        });

        const locations = new Set(selected.map(s => s.setting).filter(Boolean));

        const intCount = selected.filter(s => s.int_ext === 'INT').length;
        const extCount = selected.filter(s => s.int_ext === 'EXT').length;

        const timeCounts = {};
        selected.forEach(s => {
            const t = s.time_of_day;
            if (t) timeCounts[t] = (timeCounts[t] || 0) + 1;
        });

        return {
            count: selected.length,
            totalEighths,
            characters,
            locations,
            intCount,
            extCount,
            timeCounts,
        };
    }, [rawScenes, days, selectedSceneIds]);

    const TIME_ICONS = { DAY: Sun, NIGHT: Moon, DAWN: Sunrise, DUSK: Sunset };

    const idSet = selectedSceneIds instanceof Set
        ? selectedSceneIds
        : new Set(Array.isArray(selectedSceneIds) ? selectedSceneIds : []);

    const handleBulkMove = async () => {
        if (!targetDayId || !onBulkMove || moving) return;
        setMoving(true);
        try {
            await onBulkMove(targetDayId, Array.from(idSet));
            setTargetDayId('');
        } finally {
            setMoving(false);
        }
    };

    // Days available to move TO (exclude days that already contain ALL selected scenes)
    const movableDays = days ? days.filter(day => {
        const daySceneIds = new Set((day.scenes || []).map(ds => ds.scene_id));
        // Show day if at least one selected scene is NOT already in it
        return Array.from(idSet).some(id => !daySceneIds.has(id));
    }) : [];

    // Build inline style: when dragged, override bottom/left/transform with top/left
    const popupStyle = pos
        ? {
            bottom: 'auto',
            top: `calc(100vh - 120px + ${pos.y}px)`,
            left: `calc(50% + ${pos.x}px)`,
            transform: 'translateX(-50%)',
          }
        : {};

    return (
        <div className="selection-summary" style={popupStyle}>
            <div
                className="ss-header"
                onPointerDown={handleDragPointerDown}
                style={{ cursor: 'grab' }}
            >
                <GripHorizontal size={13} className="ss-grip" />
                <Clapperboard size={14} />
                <span className="ss-count">{stats.count} scene{stats.count !== 1 ? 's' : ''} selected</span>
                <button className="ss-close" onClick={onClear} title="Clear selection" onPointerDown={e => e.stopPropagation()}>
                    <X size={14} />
                </button>
            </div>

            <div className="ss-stats">
                <div className="ss-stat" title="Total page count">
                    <FileText size={13} />
                    <span>{stats.totalEighths > 0 ? formatEighths(stats.totalEighths) : '0'} pages</span>
                </div>

                <div className="ss-stat" title="Unique cast members">
                    <Users size={13} />
                    <span>{stats.characters.size} cast</span>
                </div>

                <div className="ss-stat" title="Unique locations">
                    <MapPin size={13} />
                    <span>{stats.locations.size} location{stats.locations.size !== 1 ? 's' : ''}</span>
                </div>
            </div>

            <div className="ss-breakdown">
                {stats.intCount > 0 && (
                    <span className="ss-tag ss-int">INT {stats.intCount}</span>
                )}
                {stats.extCount > 0 && (
                    <span className="ss-tag ss-ext">EXT {stats.extCount}</span>
                )}
                {Object.entries(stats.timeCounts).map(([time, count]) => {
                    const Icon = TIME_ICONS[time];
                    return (
                        <span key={time} className="ss-tag ss-time">
                            {Icon && <Icon size={11} />} {time} {count}
                        </span>
                    );
                })}
            </div>

            {stats.characters.size > 0 && (
                <div className="ss-cast-list">
                    {[...stats.characters].sort().map(name => (
                        <span key={name} className="ss-cast-chip">{name}</span>
                    ))}
                </div>
            )}

            {onBulkMove && movableDays.length > 0 && (
                <div className="ss-move-row">
                    <select
                        className="ss-day-select"
                        value={targetDayId}
                        onChange={e => setTargetDayId(e.target.value)}
                        disabled={moving}
                    >
                        <option value="">Move to day…</option>
                        {movableDays.map(day => (
                            <option key={day.id} value={day.id}>
                                Day {day.day_number}{day.shoot_date ? ` — ${day.shoot_date}` : ''}
                            </option>
                        ))}
                    </select>
                    <button
                        className="ss-move-btn"
                        onClick={handleBulkMove}
                        disabled={!targetDayId || moving}
                        title="Move selected scenes to this day"
                    >
                        {moving ? <Loader size={13} className="ss-spinner" /> : <ArrowRight size={13} />}
                        {moving ? 'Moving…' : 'Move'}
                    </button>
                </div>
            )}
        </div>
    );
};

export default SelectionSummary;
