import React, { useEffect, useState } from 'react';
import { X, Users, Package, Shirt, Car, Sparkles, Volume2, Cloud, MapPin, CalendarDays, Sun, Pencil, Check } from 'lucide-react';
import { formatEighths } from '../../utils/sceneUtils';
import { toggleNewDay, setTimelineCode, setStoryDay } from '../../services/apiService';
import { useStoryDayNotify } from '../../context/StoryDayContext';
import './StripDetailDrawer.css';

const TIMELINE_CODE_OPTIONS = ['PRESENT', 'FLASHBACK', 'DREAM', 'FANTASY', 'MONTAGE', 'TITLE_CARD'];

const StripDetailDrawer = ({ stripId, scenes, userItemsByScene, onClose, scriptId, onStoryDayChanged }) => {
    const scene = scenes.find(s => (s.id || s.scene_id) === stripId);
    const userItems = userItemsByScene?.[stripId] || {};

    // Close on Escape
    useEffect(() => {
        const handleKey = (e) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', handleKey);
        return () => window.removeEventListener('keydown', handleKey);
    }, [onClose]);

    const notifyStoryDayChange = useStoryDayNotify();
    const [sdEditing, setSdEditing] = useState(false);
    const [sdDraft, setSdDraft] = useState('');
    const [sdSaving, setSdSaving] = useState(false);

    const sceneId = scene?.id || scene?.scene_id;

    const handleStoryDayAction = async (action) => {
        if (!scriptId || !sceneId) return;
        setSdSaving(true);
        try {
            await action();
            notifyStoryDayChange(scriptId);
        } catch (e) { console.error('Story day action error:', e); }
        finally { setSdSaving(false); }
    };

    if (!scene) return null;

    // Merge AI + user items
    const chars = [...(scene.characters || []), ...(userItems.characters || [])];
    const props = [...(scene.props || []), ...(userItems.props || [])];
    const wardrobe = [...(scene.wardrobe || []), ...(userItems.wardrobe || [])];
    const vehicles = [...(scene.vehicles || []), ...(userItems.vehicles || [])];
    const specialFx = [...(scene.special_fx || []), ...(userItems.special_fx || [])];
    const sound = [...(scene.sound || []), ...(userItems.sound || [])];
    const atmosphere = scene.atmosphere || '';

    const breakdownSections = [
        { icon: Users, label: 'Cast', items: chars, color: '#818cf8' },
        { icon: Package, label: 'Props', items: props, color: '#f59e0b' },
        { icon: Shirt, label: 'Wardrobe', items: wardrobe, color: '#ec4899' },
        { icon: Car, label: 'Vehicles', items: vehicles, color: '#14b8a6' },
        { icon: Sparkles, label: 'Special FX', items: specialFx, color: '#f97316' },
        { icon: Volume2, label: 'Sound', items: sound, color: '#06b6d4' },
    ];

    return (
        <>
            <div className="drawer-backdrop" onClick={onClose} />
            <div className="strip-detail-drawer">
                <div className="drawer-header">
                    <div className="drawer-title-row">
                        <span className="drawer-scene-number">Scene {scene.scene_number}</span>
                        <span className={`drawer-ie-badge ${scene.int_ext === 'INT' ? 'int' : 'ext'}`}>
                            {scene.int_ext}
                        </span>
                        <span className="drawer-time">{scene.time_of_day}</span>
                        <button className="drawer-close-btn" onClick={onClose} title="Close (Esc)">
                            <X size={18} />
                        </button>
                    </div>

                    <div className="drawer-setting">
                        <MapPin size={14} />
                        <span>{scene.setting || 'Unknown Location'}</span>
                    </div>

                    <div className="drawer-meta-row">
                        {/* Story Day Editing Controls */}
                        <div className="drawer-sd-controls">
                            {scene.story_day && !sdEditing && (
                                <button
                                    className={`drawer-day-badge timeline-${(scene.timeline_code || 'PRESENT').toLowerCase()} editable-drawer-badge`}
                                    onClick={() => { setSdDraft(scene.story_day.toString()); setSdEditing(true); }}
                                    title="Click to edit story day"
                                >
                                    <CalendarDays size={12} />
                                    {scene.story_day_label || `Day ${scene.story_day}`}
                                    <Pencil size={9} className="drawer-edit-hint" />
                                </button>
                            )}
                            {!scene.story_day && !sdEditing && (
                                <button
                                    className="drawer-day-badge unassigned editable-drawer-badge"
                                    onClick={() => { setSdDraft('1'); setSdEditing(true); }}
                                    title="Assign story day"
                                >
                                    <CalendarDays size={12} />
                                    No Day
                                    <Pencil size={9} className="drawer-edit-hint" />
                                </button>
                            )}
                            {sdEditing && (
                                <div className="drawer-sd-edit">
                                    <span className="drawer-sd-label">Day</span>
                                    <input
                                        className="drawer-sd-input"
                                        type="number"
                                        min="1"
                                        value={sdDraft}
                                        onChange={e => setSdDraft(e.target.value)}
                                        onKeyDown={e => {
                                            if (e.key === 'Enter') {
                                                const val = parseInt(sdDraft, 10);
                                                if (val >= 1) handleStoryDayAction(() => setStoryDay(scriptId, sceneId, val)).then(() => setSdEditing(false));
                                            }
                                            if (e.key === 'Escape') setSdEditing(false);
                                        }}
                                        disabled={sdSaving}
                                        autoFocus
                                    />
                                    <button className="drawer-sd-btn confirm" disabled={sdSaving} onClick={() => {
                                        const val = parseInt(sdDraft, 10);
                                        if (val >= 1) handleStoryDayAction(() => setStoryDay(scriptId, sceneId, val)).then(() => setSdEditing(false));
                                    }}><Check size={14} /></button>
                                    <button className="drawer-sd-btn cancel" disabled={sdSaving} onClick={() => setSdEditing(false)}><X size={14} /></button>
                                </div>
                            )}
                            {scene.story_day && !sdEditing && scriptId && (
                                <>
                                    <button
                                        className={`drawer-sd-action ${scene.is_new_story_day ? 'active' : ''}`}
                                        onClick={() => handleStoryDayAction(() => toggleNewDay(scriptId, sceneId))}
                                        disabled={sdSaving}
                                        title={scene.is_new_story_day ? 'Starts new day (toggle)' : 'Mark as new day'}
                                    >
                                        <Sun size={11} />
                                    </button>
                                    <select
                                        className="drawer-sd-timeline"
                                        value={scene.timeline_code || 'PRESENT'}
                                        onChange={(e) => handleStoryDayAction(() => setTimelineCode(scriptId, sceneId, e.target.value))}
                                        disabled={sdSaving}
                                        title="Timeline code"
                                    >
                                        {TIMELINE_CODE_OPTIONS.map(opt => (
                                            <option key={opt} value={opt}>{opt.charAt(0) + opt.slice(1).toLowerCase().replace('_', ' ')}</option>
                                        ))}
                                    </select>
                                </>
                            )}
                        </div>
                        {scene.page_length_eighths > 0 && (
                            <span className="drawer-pages">{formatEighths(scene.page_length_eighths)} pages</span>
                        )}
                        {scene.shot_type && (
                            <span className="drawer-shot-type">{scene.shot_type}</span>
                        )}
                    </div>
                </div>

                <div className="drawer-body">
                    {breakdownSections.map(section => (
                        <div key={section.label} className="drawer-section">
                            <div className="drawer-section-header" style={{ '--section-color': section.color }}>
                                <section.icon size={14} />
                                <span>{section.label}</span>
                                <span className="drawer-section-count">{section.items.length}</span>
                            </div>
                            {section.items.length > 0 ? (
                                <ul className="drawer-item-list">
                                    {section.items.map((item, i) => (
                                        <li key={i}>{item}</li>
                                    ))}
                                </ul>
                            ) : (
                                <span className="drawer-empty">None</span>
                            )}
                        </div>
                    ))}

                    {atmosphere && (
                        <div className="drawer-section">
                            <div className="drawer-section-header" style={{ '--section-color': '#94a3b8' }}>
                                <Cloud size={14} />
                                <span>Atmosphere</span>
                            </div>
                            <p className="drawer-atmosphere-text">{atmosphere}</p>
                        </div>
                    )}
                </div>
            </div>
        </>
    );
};

export default StripDetailDrawer;
