import React, { useEffect } from 'react';
import { X, Users, Package, Shirt, Car, Sparkles, Volume2, Cloud, MapPin, CalendarDays } from 'lucide-react';
import { formatEighths } from '../../utils/sceneUtils';
import './StripDetailDrawer.css';

const StripDetailDrawer = ({ stripId, scenes, userItemsByScene, onClose }) => {
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
                        {scene.story_day && (
                            <span className={`drawer-day-badge timeline-${(scene.timeline_code || 'PRESENT').toLowerCase()}`}>
                                <CalendarDays size={12} />
                                {scene.story_day_label || `Day ${scene.story_day}`}
                            </span>
                        )}
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
