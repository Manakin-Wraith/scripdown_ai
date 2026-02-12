import React, { useState, useRef, useEffect } from 'react';
import {
    Filter, X, ChevronDown, ChevronUp, Search,
    MapPin, Users, Sun, Moon, Sunrise, Sunset,
    CalendarDays, Hash, Layers, LayoutGrid, RotateCcw,
    BookmarkPlus, Bookmark, Trash2
} from 'lucide-react';
import './ReportFilterPanel.css';

const CATEGORY_OPTIONS = [
    { key: 'characters', label: 'Characters' },
    { key: 'props', label: 'Props' },
    { key: 'wardrobe', label: 'Wardrobe' },
    { key: 'makeup', label: 'Makeup' },
    { key: 'special_effects', label: 'Special FX' },
    { key: 'vehicles', label: 'Vehicles' },
    { key: 'animals', label: 'Animals' },
    { key: 'extras', label: 'Extras' },
    { key: 'stunts', label: 'Stunts' }
];

const GROUP_BY_OPTIONS = [
    { key: 'scene_number', label: 'Scene Number' },
    { key: 'location', label: 'Location' },
    { key: 'character', label: 'Character' },
    { key: 'story_day', label: 'Story Day' }
];

const TOD_ICONS = {
    'DAY': Sun,
    'NIGHT': Moon,
    'DAWN': Sunrise,
    'DUSK': Sunset
};

const ReportFilterPanel = ({ filterOptions, filters, onFilterChange, isCollapsed, onToggleCollapse, presets, onLoadPreset, onSavePreset, onDeletePreset }) => {
    const [locationSearch, setLocationSearch] = useState('');
    const [characterSearch, setCharacterSearch] = useState('');
    const [locationDropdownOpen, setLocationDropdownOpen] = useState(false);
    const [characterDropdownOpen, setCharacterDropdownOpen] = useState(false);
    const [presetDropdownOpen, setPresetDropdownOpen] = useState(false);
    const [showSaveInput, setShowSaveInput] = useState(false);
    const [presetName, setPresetName] = useState('');
    const [storyDaysExpanded, setStoryDaysExpanded] = useState(false);
    
    const STORY_DAYS_COLLAPSE_THRESHOLD = 14;
    const locationRef = useRef(null);
    const characterRef = useRef(null);
    const presetRef = useRef(null);

    // Close dropdowns on outside click
    useEffect(() => {
        const handleClick = (e) => {
            if (locationRef.current && !locationRef.current.contains(e.target)) {
                setLocationDropdownOpen(false);
            }
            if (characterRef.current && !characterRef.current.contains(e.target)) {
                setCharacterDropdownOpen(false);
            }
            if (presetRef.current && !presetRef.current.contains(e.target)) {
                setPresetDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, []);

    const handleLoadPreset = (preset) => {
        if (onLoadPreset) onLoadPreset(preset);
        setPresetDropdownOpen(false);
    };

    const handleSavePreset = () => {
        if (!presetName.trim()) return;
        if (onSavePreset) onSavePreset(presetName.trim());
        setPresetName('');
        setShowSaveInput(false);
    };

    const activeFilterCount = Object.entries(filters).filter(([key, val]) => {
        if (!val) return false;
        if (Array.isArray(val) && val.length === 0) return false;
        if (typeof val === 'object' && !Array.isArray(val)) {
            return Object.values(val).some(v => v);
        }
        return true;
    }).length;

    const updateFilter = (key, value) => {
        onFilterChange({ ...filters, [key]: value });
    };

    const toggleArrayItem = (key, item) => {
        const current = filters[key] || [];
        const next = current.includes(item)
            ? current.filter(i => i !== item)
            : [...current, item];
        updateFilter(key, next);
    };

    const clearAllFilters = () => {
        onFilterChange({
            locations: [],
            location_parents: [],
            characters: [],
            int_ext: [],
            time_of_day: [],
            story_days: [],
            scene_numbers: [],
            scene_range: { from: '', to: '' },
            timeline_codes: [],
            categories: [],
            group_by: 'scene_number'
        });
    };

    if (!filterOptions) return null;

    const filteredLocations = (filterOptions.locations || []).filter(
        loc => loc.toLowerCase().includes(locationSearch.toLowerCase())
    );

    const filteredCharacters = (filterOptions.characters || []).filter(
        char => char.toLowerCase().includes(characterSearch.toLowerCase())
    );

    if (isCollapsed) {
        return (
            <div className="filter-panel collapsed" onClick={onToggleCollapse}>
                <div className="filter-panel-collapsed-icon">
                    <Filter size={18} />
                    {activeFilterCount > 0 && (
                        <span className="filter-count-badge">{activeFilterCount}</span>
                    )}
                </div>
            </div>
        );
    }

    return (
        <div className="filter-panel">
            {/* Header */}
            <div className="filter-panel-header">
                <div className="filter-panel-title">
                    <Filter size={16} />
                    <span>Filters</span>
                    {activeFilterCount > 0 && (
                        <span className="filter-count-badge">{activeFilterCount}</span>
                    )}
                </div>
                <div className="filter-panel-actions">
                    {activeFilterCount > 0 && (
                        <button className="filter-clear-btn" onClick={clearAllFilters} title="Clear all filters">
                            <RotateCcw size={14} />
                            <span>Clear</span>
                        </button>
                    )}
                    <button className="filter-collapse-btn" onClick={onToggleCollapse} title="Collapse filters">
                        <ChevronDown size={16} />
                    </button>
                </div>
            </div>

            <div className="filter-panel-body">
                {/* Preset Selector */}
                {presets && presets.length > 0 && (
                    <div className="filter-section preset-section">
                        <label className="filter-label">
                            <Bookmark size={14} />
                            Presets
                        </label>
                        <div className="multi-select" ref={presetRef}>
                            <div
                                className="multi-select-trigger"
                                onClick={() => setPresetDropdownOpen(!presetDropdownOpen)}
                            >
                                <span className="multi-select-placeholder">Load a preset...</span>
                                <ChevronDown size={14} />
                            </div>
                            {presetDropdownOpen && (
                                <div className="multi-select-dropdown preset-dropdown">
                                    <div className="dropdown-options">
                                        {presets.map(preset => (
                                            <div key={preset.id} className="preset-option">
                                                <button
                                                    className="preset-option-btn"
                                                    onClick={() => handleLoadPreset(preset)}
                                                >
                                                    <span className="preset-name">{preset.name}</span>
                                                    {preset.is_default && <span className="preset-default-badge">Default</span>}
                                                </button>
                                                {!preset.is_default && onDeletePreset && (
                                                    <button
                                                        className="preset-delete-btn"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            onDeletePreset(preset.id);
                                                        }}
                                                        title="Delete preset"
                                                    >
                                                        <Trash2 size={12} />
                                                    </button>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                        {/* Save current as preset */}
                        {onSavePreset && (
                            <div className="save-preset-area">
                                {showSaveInput ? (
                                    <div className="save-preset-input">
                                        <input
                                            type="text"
                                            placeholder="Preset name..."
                                            value={presetName}
                                            onChange={(e) => setPresetName(e.target.value)}
                                            onKeyDown={(e) => e.key === 'Enter' && handleSavePreset()}
                                            autoFocus
                                        />
                                        <button className="save-preset-confirm" onClick={handleSavePreset} disabled={!presetName.trim()}>
                                            Save
                                        </button>
                                        <button className="save-preset-cancel" onClick={() => { setShowSaveInput(false); setPresetName(''); }}>
                                            <X size={14} />
                                        </button>
                                    </div>
                                ) : (
                                    <button className="save-preset-btn" onClick={() => setShowSaveInput(true)}>
                                        <BookmarkPlus size={14} />
                                        <span>Save Current Filter</span>
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                )}

                <div className="filter-divider" />

                {/* Location Filter */}
                {filterOptions.locations?.length > 0 && (
                    <div className="filter-section">
                        <label className="filter-label">
                            <MapPin size={14} />
                            Location
                        </label>
                        <div className="multi-select" ref={locationRef}>
                            <div
                                className="multi-select-trigger"
                                onClick={() => setLocationDropdownOpen(!locationDropdownOpen)}
                            >
                                <span className="multi-select-placeholder">
                                    {(filters.locations || []).length > 0
                                        ? `${filters.locations.length} selected`
                                        : 'All locations'}
                                </span>
                                <ChevronDown size={14} />
                            </div>
                            {locationDropdownOpen && (
                                <div className="multi-select-dropdown">
                                    <div className="dropdown-search">
                                        <Search size={14} />
                                        <input
                                            type="text"
                                            placeholder="Search locations..."
                                            value={locationSearch}
                                            onChange={(e) => setLocationSearch(e.target.value)}
                                            autoFocus
                                        />
                                    </div>
                                    <div className="dropdown-options">
                                        {filteredLocations.map(loc => (
                                            <label key={loc} className="dropdown-option">
                                                <input
                                                    type="checkbox"
                                                    checked={(filters.locations || []).includes(loc)}
                                                    onChange={() => toggleArrayItem('locations', loc)}
                                                />
                                                <span>{loc}</span>
                                            </label>
                                        ))}
                                        {filteredLocations.length === 0 && (
                                            <div className="dropdown-empty">No locations found</div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                        {/* Selected tags */}
                        {(filters.locations || []).length > 0 && (
                            <div className="selected-tags">
                                {filters.locations.map(loc => (
                                    <span key={loc} className="filter-tag">
                                        {loc.length > 25 ? loc.substring(0, 25) + '...' : loc}
                                        <button onClick={() => toggleArrayItem('locations', loc)}>
                                            <X size={12} />
                                        </button>
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Character Filter */}
                {filterOptions.characters?.length > 0 && (
                    <div className="filter-section">
                        <label className="filter-label">
                            <Users size={14} />
                            Character
                        </label>
                        <div className="multi-select" ref={characterRef}>
                            <div
                                className="multi-select-trigger"
                                onClick={() => setCharacterDropdownOpen(!characterDropdownOpen)}
                            >
                                <span className="multi-select-placeholder">
                                    {(filters.characters || []).length > 0
                                        ? `${filters.characters.length} selected`
                                        : 'All characters'}
                                </span>
                                <ChevronDown size={14} />
                            </div>
                            {characterDropdownOpen && (
                                <div className="multi-select-dropdown">
                                    <div className="dropdown-search">
                                        <Search size={14} />
                                        <input
                                            type="text"
                                            placeholder="Search characters..."
                                            value={characterSearch}
                                            onChange={(e) => setCharacterSearch(e.target.value)}
                                            autoFocus
                                        />
                                    </div>
                                    <div className="dropdown-options">
                                        {filteredCharacters.map(char => (
                                            <label key={char} className="dropdown-option">
                                                <input
                                                    type="checkbox"
                                                    checked={(filters.characters || []).includes(char)}
                                                    onChange={() => toggleArrayItem('characters', char)}
                                                />
                                                <span>{char}</span>
                                            </label>
                                        ))}
                                        {filteredCharacters.length === 0 && (
                                            <div className="dropdown-empty">No characters found</div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                        {(filters.characters || []).length > 0 && (
                            <div className="selected-tags">
                                {filters.characters.map(char => (
                                    <span key={char} className="filter-tag">
                                        {char}
                                        <button onClick={() => toggleArrayItem('characters', char)}>
                                            <X size={12} />
                                        </button>
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* INT/EXT Toggle */}
                {filterOptions.int_ext_values?.length > 0 && (
                    <div className="filter-section">
                        <label className="filter-label">INT / EXT</label>
                        <div className="pill-group">
                            {filterOptions.int_ext_values.map(val => (
                                <button
                                    key={val}
                                    className={`pill-btn ${(filters.int_ext || []).includes(val) ? 'active' : ''}`}
                                    onClick={() => toggleArrayItem('int_ext', val)}
                                >
                                    {val}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Time of Day Toggle */}
                {filterOptions.time_of_day_values?.length > 0 && (
                    <div className="filter-section">
                        <label className="filter-label">Time of Day</label>
                        <div className="pill-group">
                            {filterOptions.time_of_day_values.map(val => {
                                const Icon = TOD_ICONS[val] || Sun;
                                return (
                                    <button
                                        key={val}
                                        className={`pill-btn ${(filters.time_of_day || []).includes(val) ? 'active' : ''}`}
                                        onClick={() => toggleArrayItem('time_of_day', val)}
                                    >
                                        <Icon size={12} />
                                        {val}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Story Days */}
                {filterOptions.story_days?.length > 0 && (
                    <div className="filter-section">
                        <label className="filter-label">
                            <CalendarDays size={14} />
                            Story Days
                            {filterOptions.story_days.length > STORY_DAYS_COLLAPSE_THRESHOLD && (
                                <span className="filter-label-count">({filterOptions.story_days.length})</span>
                            )}
                        </label>
                        <div className={`chip-group ${!storyDaysExpanded && filterOptions.story_days.length > STORY_DAYS_COLLAPSE_THRESHOLD ? 'chip-group-collapsed' : ''}`}>
                            {filterOptions.story_days.map(day => (
                                <button
                                    key={day}
                                    className={`chip-btn ${(filters.story_days || []).includes(day) ? 'active' : ''}`}
                                    onClick={() => toggleArrayItem('story_days', day)}
                                >
                                    D{day}
                                </button>
                            ))}
                        </div>
                        {filterOptions.story_days.length > STORY_DAYS_COLLAPSE_THRESHOLD && (
                            <button
                                className="chip-group-toggle"
                                onClick={() => setStoryDaysExpanded(!storyDaysExpanded)}
                            >
                                {storyDaysExpanded
                                    ? 'Show less'
                                    : `Show all ${filterOptions.story_days.length} days`
                                }
                                <ChevronDown size={12} className={storyDaysExpanded ? 'toggle-icon-rotated' : ''} />
                            </button>
                        )}
                    </div>
                )}

                {/* Scene Range */}
                <div className="filter-section">
                    <label className="filter-label">
                        <Hash size={14} />
                        Scene Range
                    </label>
                    <div className="range-inputs">
                        <input
                            type="text"
                            className="range-input"
                            placeholder="From"
                            value={(filters.scene_range || {}).from || ''}
                            onChange={(e) => updateFilter('scene_range', {
                                ...(filters.scene_range || {}),
                                from: e.target.value
                            })}
                        />
                        <span className="range-separator">-</span>
                        <input
                            type="text"
                            className="range-input"
                            placeholder="To"
                            value={(filters.scene_range || {}).to || ''}
                            onChange={(e) => updateFilter('scene_range', {
                                ...(filters.scene_range || {}),
                                to: e.target.value
                            })}
                        />
                    </div>
                </div>

                {/* Timeline Codes */}
                {filterOptions.timeline_codes?.length > 1 && (
                    <div className="filter-section">
                        <label className="filter-label">Timeline</label>
                        <div className="pill-group wrap">
                            {filterOptions.timeline_codes.map(code => (
                                <button
                                    key={code}
                                    className={`pill-btn ${(filters.timeline_codes || []).includes(code) ? 'active' : ''}`}
                                    onClick={() => toggleArrayItem('timeline_codes', code)}
                                >
                                    {code}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                <div className="filter-divider" />

                {/* Categories */}
                <div className="filter-section">
                    <label className="filter-label">
                        <Layers size={14} />
                        Categories
                    </label>
                    <div className="checkbox-grid">
                        {CATEGORY_OPTIONS.map(cat => (
                            <label key={cat.key} className="checkbox-item">
                                <input
                                    type="checkbox"
                                    checked={(filters.categories || []).includes(cat.key)}
                                    onChange={() => toggleArrayItem('categories', cat.key)}
                                />
                                <span>{cat.label}</span>
                            </label>
                        ))}
                    </div>
                </div>

                {/* Group By */}
                <div className="filter-section">
                    <label className="filter-label">
                        <LayoutGrid size={14} />
                        Group By
                    </label>
                    <div className="radio-group">
                        {GROUP_BY_OPTIONS.map(opt => (
                            <label key={opt.key} className="radio-item">
                                <input
                                    type="radio"
                                    name="group_by"
                                    checked={(filters.group_by || 'scene_number') === opt.key}
                                    onChange={() => updateFilter('group_by', opt.key)}
                                />
                                <span>{opt.label}</span>
                            </label>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ReportFilterPanel;
