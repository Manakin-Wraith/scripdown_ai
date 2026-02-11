import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
    List, Sun, Moon, Home, Building2, Users, MapPin,
    GripVertical, ArrowLeft,
    Loader, Filter, SortAsc, SortDesc,
    Package, Shirt, Sparkles, Car, Volume2, Cloud,
    CheckCircle, AlertCircle, Clock, FileText, MessageSquare,
    CalendarDays
} from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { useScript } from '../../context/ScriptContext';
import { getScenes, getScriptMetadata, getScriptItems } from '../../services/apiService';
import { getSceneEighthsDisplay, getSceneEighths, formatEighths } from '../../utils/sceneUtils';
import './Stripboard.css';

const Stripboard = () => {
    const { scriptId } = useParams();
    const navigate = useNavigate();
    const toast = useToast();
    const { setScript } = useScript();
    
    const [scenes, setScenes] = useState([]);
    const [metadata, setMetadata] = useState(null);
    const [loading, setLoading] = useState(true);
    const [userItemsByScene, setUserItemsByScene] = useState({}); // { sceneId: { category: [items] } }
    const [sortBy, setSortBy] = useState('scene_order');
    const [sortDir, setSortDir] = useState('asc');
    const [filterIntExt, setFilterIntExt] = useState('all');
    const [filterTimeOfDay, setFilterTimeOfDay] = useState('all');
    const [filterAnalysisStatus, setFilterAnalysisStatus] = useState('all');
    const [filterStoryDay, setFilterStoryDay] = useState('all');
    const [expandedRows, setExpandedRows] = useState(new Set());

    // Helper function to determine scene analysis status
    const getSceneAnalysisStatus = (scene) => {
        const hasCharacters = scene.characters && scene.characters.length > 0;
        const hasProps = scene.props && scene.props.length > 0;
        const hasWardrobe = scene.wardrobe && scene.wardrobe.length > 0;
        const hasVehicles = scene.vehicles && scene.vehicles.length > 0;
        const hasSpecialFx = scene.special_fx && scene.special_fx.length > 0;
        const hasSound = scene.sound && scene.sound.length > 0;
        const hasAtmosphere = scene.atmosphere && scene.atmosphere.trim().length > 0;
        
        const filledCategories = [hasCharacters, hasProps, hasWardrobe, hasVehicles, hasSpecialFx, hasSound, hasAtmosphere].filter(Boolean).length;
        
        if (filledCategories === 0) {
            return 'pending'; // Not analyzed
        } else if (filledCategories >= 3) {
            return 'analyzed'; // Well analyzed (3+ categories)
        } else {
            return 'incomplete'; // Partially analyzed
        }
    };

    // Helper to get notes for a scene (placeholder - would need API integration)
    const getSceneNotes = (scene) => {
        // For now, return empty - this would be populated from scene_notes table
        return scene.notes || [];
    };

    // Helper to get notes count by department
    const getNotesByDepartment = (notes) => {
        const byDept = {};
        (notes || []).forEach(note => {
            const dept = note.department || 'general';
            byDept[dept] = (byDept[dept] || 0) + 1;
        });
        return byDept;
    };

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                
                // Fetch scenes + user-added items in parallel
                const [sceneData, itemsData] = await Promise.all([
                    getScenes(scriptId),
                    getScriptItems(scriptId).catch(() => ({ items: [] }))
                ]);
                setScenes(sceneData.scenes || []);
                
                // Index user items by scene_id → item_type
                const itemMap = {};
                (itemsData.items || []).forEach(item => {
                    if (!item.scene_id || item.status === 'removed') return;
                    if (!itemMap[item.scene_id]) itemMap[item.scene_id] = {};
                    if (!itemMap[item.scene_id][item.item_type]) itemMap[item.scene_id][item.item_type] = [];
                    itemMap[item.scene_id][item.item_type].push(item.item_name);
                });
                setUserItemsByScene(itemMap);
                
                // Fetch metadata
                try {
                    const meta = await getScriptMetadata(scriptId);
                    setMetadata(meta);
                    // Update script context for breadcrumbs
                    setScript({
                        id: scriptId,
                        title: meta?.title || meta?.script_name
                    });
                } catch (e) {
                    console.warn('Could not fetch metadata:', e);
                }
            } catch (error) {
                toast.error('Error', 'Failed to load scenes');
            } finally {
                setLoading(false);
            }
        };
        
        fetchData();
    }, [scriptId]);

    // Compute unique story days for filter dropdown
    const uniqueStoryDays = useMemo(() => {
        const days = new Map();
        scenes.forEach(scene => {
            if (scene.story_day) {
                if (!days.has(scene.story_day)) {
                    days.set(scene.story_day, {
                        day: scene.story_day,
                        label: scene.story_day_label || `Day ${scene.story_day}`,
                        timeline: scene.timeline_code || 'PRESENT',
                        count: 0
                    });
                }
                days.get(scene.story_day).count++;
            }
        });
        return Array.from(days.values()).sort((a, b) => a.day - b.day);
    }, [scenes]);

    // Filter and sort scenes
    const filteredScenes = useMemo(() => {
        let result = [...scenes];
        
        // Apply filters
        if (filterIntExt !== 'all') {
            result = result.filter(s => s.int_ext === filterIntExt);
        }
        if (filterTimeOfDay !== 'all') {
            result = result.filter(s => s.time_of_day === filterTimeOfDay);
        }
        if (filterAnalysisStatus !== 'all') {
            result = result.filter(s => getSceneAnalysisStatus(s) === filterAnalysisStatus);
        }
        if (filterStoryDay !== 'all') {
            result = result.filter(s => s.story_day === parseInt(filterStoryDay));
        }
        
        // Apply sorting
        result.sort((a, b) => {
            let aVal, bVal;
            
            switch (sortBy) {
                case 'scene_number':
                    aVal = parseInt(a.scene_number) || 0;
                    bVal = parseInt(b.scene_number) || 0;
                    break;
                case 'setting':
                    aVal = a.setting || '';
                    bVal = b.setting || '';
                    break;
                case 'characters':
                    aVal = (a.characters || []).length;
                    bVal = (b.characters || []).length;
                    break;
                default:
                    aVal = a.scene_order || 0;
                    bVal = b.scene_order || 0;
            }
            
            if (typeof aVal === 'string') {
                return sortDir === 'asc' 
                    ? aVal.localeCompare(bVal)
                    : bVal.localeCompare(aVal);
            }
            return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
        });
        
        return result;
    }, [scenes, filterIntExt, filterTimeOfDay, filterAnalysisStatus, filterStoryDay, sortBy, sortDir]);

    // Calculate stats
    const stats = useMemo(() => {
        const intCount = scenes.filter(s => s.int_ext === 'INT').length;
        const extCount = scenes.filter(s => s.int_ext === 'EXT').length;
        const dayCount = scenes.filter(s => s.time_of_day === 'DAY').length;
        const nightCount = scenes.filter(s => s.time_of_day === 'NIGHT').length;
        
        // Calculate total eighths
        const totalEighths = scenes.reduce((sum, scene) => sum + getSceneEighths(scene), 0);
        const totalEighthsDisplay = formatEighths(totalEighths);
        
        // Calculate unique characters count (AI + user-added)
        const allChars = new Set();
        scenes.forEach(scene => {
            const sceneId = scene.id || scene.scene_id;
            const sceneItems = userItemsByScene[sceneId] || {};
            (scene.characters || []).forEach(char => allChars.add(char));
            (sceneItems.characters || []).forEach(char => allChars.add(char));
        });
        const totalCharacters = allChars.size;
        
        // Calculate unique locations count
        const allLocations = new Set();
        scenes.forEach(scene => {
            if (scene.setting) {
                allLocations.add(scene.setting.toUpperCase().trim());
            }
        });
        const totalLocations = allLocations.size;
        
        // Calculate unique story days
        const storyDays = new Set();
        scenes.forEach(scene => {
            if (scene.story_day) storyDays.add(scene.story_day);
        });
        const totalStoryDays = storyDays.size;

        return { intCount, extCount, dayCount, nightCount, totalEighths, totalEighthsDisplay, totalCharacters, totalLocations, totalStoryDays };
    }, [scenes, userItemsByScene]);


    const toggleSort = (field) => {
        if (sortBy === field) {
            setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
        } else {
            setSortBy(field);
            setSortDir('asc');
        }
    };

    const toggleRowExpand = (sceneId) => {
        setExpandedRows(prev => {
            const newSet = new Set(prev);
            if (newSet.has(sceneId)) {
                newSet.delete(sceneId);
            } else {
                newSet.add(sceneId);
            }
            return newSet;
        });
    };

    if (loading) {
        return (
            <div className="stripboard-loading">
                <Loader className="spin" size={32} />
                <p>Loading stripboard...</p>
            </div>
        );
    }

    // Format current date for print header
    const printDate = new Date().toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        year: 'numeric' 
    });

    return (
        <div className="stripboard">
            {/* Print-only Professional Header */}
            <div className="print-header">
                <div className="print-header-top">
                    <div className="print-brand">
                        <span className="print-brand-logo">SlateOne</span>
                        <span className="print-brand-tagline">Script Breakdown</span>
                    </div>
                    <span className="print-confidential">Confidential</span>
                </div>
                <div className="print-header-main">
                    <div className="print-title-section">
                        <h1 className="print-title">{metadata?.title || 'Untitled Script'}</h1>
                        <p className="print-subtitle">One-Liner / Stripboard</p>
                    </div>
                    <div className="print-meta-section">
                        {metadata?.writer_name && (
                            <div className="print-meta-row">
                                <span className="print-meta-label">Written by:</span>
                                <span className="print-meta-value">{metadata.writer_name}</span>
                            </div>
                        )}
                        {metadata?.genre && (
                            <div className="print-meta-row">
                                <span className="print-meta-label">Genre:</span>
                                <span className="print-meta-value">{metadata.genre}</span>
                            </div>
                        )}
                        {metadata?.draft_version && (
                            <div className="print-meta-row">
                                <span className="print-meta-label">Draft:</span>
                                <span className="print-meta-value">{metadata.draft_version}</span>
                            </div>
                        )}
                        <div className="print-meta-row">
                            <span className="print-meta-label">Generated:</span>
                            <span className="print-meta-value">{printDate}</span>
                        </div>
                    </div>
                </div>
                <div className="print-stats">
                    <span><strong>{scenes.length}</strong> Scenes</span>
                    <span><strong>{stats.intCount}</strong> INT</span>
                    <span><strong>{stats.extCount}</strong> EXT</span>
                    <span><strong>{stats.dayCount}</strong> DAY</span>
                    <span><strong>{stats.nightCount}</strong> NIGHT</span>
                    <span><strong>{stats.totalCharacters}</strong> Cast</span>
                    <span><strong>{stats.totalLocations}</strong> Locations</span>
                    {stats.totalStoryDays > 0 && (
                        <span><strong>{stats.totalStoryDays}</strong> Story Days</span>
                    )}
                    <span className="print-stats-highlight"><strong>{stats.totalEighthsDisplay}</strong> Pages</span>
                </div>
            </div>

            {/* Header */}
            <div className="stripboard-header">
                <h1>
                    <List size={24} />
                    One-Liner / Stripboard
                </h1>
            </div>

            {/* Stats Bar */}
            <div className="stripboard-stats">
                <div className="stat-group">
                    <span className="stat-label">Total:</span>
                    <span className="stat-value">{scenes.length} scenes</span>
                </div>
                <div className="stat-group">
                    <Home size={14} />
                    <span className="stat-value">{stats.intCount} INT</span>
                </div>
                <div className="stat-group">
                    <Building2 size={14} />
                    <span className="stat-value">{stats.extCount} EXT</span>
                </div>
                <div className="stat-group">
                    <Sun size={14} />
                    <span className="stat-value">{stats.dayCount} DAY</span>
                </div>
                <div className="stat-group">
                    <Moon size={14} />
                    <span className="stat-value">{stats.nightCount} NIGHT</span>
                </div>
                <div className="stat-group">
                    <Users size={14} />
                    <span className="stat-value">{stats.totalCharacters} Cast</span>
                </div>
                <div className="stat-group">
                    <MapPin size={14} />
                    <span className="stat-value">{stats.totalLocations} Locations</span>
                </div>
                {stats.totalStoryDays > 0 && (
                    <div className="stat-group">
                        <CalendarDays size={14} />
                        <span className="stat-value">{stats.totalStoryDays} Story Days</span>
                    </div>
                )}
                <div className="stat-group stat-eighths">
                    <span className="stat-label">Length:</span>
                    <span className="stat-value eighths-total">{stats.totalEighthsDisplay} pages</span>
                </div>
            </div>

            {/* Filters */}
            <div className="stripboard-filters">
                <div className="filter-group">
                    <select 
                        value={filterIntExt}
                        onChange={(e) => setFilterIntExt(e.target.value)}
                    >
                        <option value="all">All INT/EXT</option>
                        <option value="INT">INT only</option>
                        <option value="EXT">EXT only</option>
                    </select>
                </div>
                <div className="filter-group">
                    <select 
                        value={filterTimeOfDay}
                        onChange={(e) => setFilterTimeOfDay(e.target.value)}
                    >
                        <option value="all">All Times</option>
                        <option value="DAY">DAY only</option>
                        <option value="NIGHT">NIGHT only</option>
                        <option value="DAWN">DAWN</option>
                        <option value="DUSK">DUSK</option>
                    </select>
                </div>
                <div className="filter-group">
                    <select 
                        value={filterAnalysisStatus}
                        onChange={(e) => setFilterAnalysisStatus(e.target.value)}
                    >
                        <option value="all">All Status</option>
                        <option value="analyzed">Analyzed</option>
                        <option value="incomplete">Incomplete</option>
                        <option value="pending">Pending</option>
                    </select>
                </div>
                {uniqueStoryDays.length > 0 && (
                    <div className="filter-group">
                        <select
                            value={filterStoryDay}
                            onChange={(e) => setFilterStoryDay(e.target.value)}
                        >
                            <option value="all">All Days</option>
                            {uniqueStoryDays.map(d => (
                                <option key={d.day} value={d.day}>
                                    {d.label} ({d.count})
                                </option>
                            ))}
                        </select>
                    </div>
                )}
                <div className="filter-group">
                    <select 
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value)}
                    >
                        <option value="scene_order">Scene Order</option>
                        <option value="scene_number">Scene Number</option>
                        <option value="setting">Location</option>
                        <option value="characters">Cast Size</option>
                    </select>
                    <button 
                        className="sort-dir-btn"
                        onClick={() => setSortDir(sortDir === 'asc' ? 'desc' : 'asc')}
                    >
                        {sortDir === 'asc' ? <SortAsc size={14} /> : <SortDesc size={14} />}
                    </button>
                </div>
            </div>

            {/* Stripboard Table */}
            <div className="stripboard-table-container">
                <table className="stripboard-table">
                    <thead>
                        <tr>
                            <th className="col-scene" onClick={() => toggleSort('scene_number')}>
                                #
                                {sortBy === 'scene_number' && (
                                    sortDir === 'asc' ? <SortAsc size={12} /> : <SortDesc size={12} />
                                )}
                            </th>
                            <th className="col-ie">I/E</th>
                            <th className="col-setting" onClick={() => toggleSort('setting')}>
                                Setting
                                {sortBy === 'setting' && (
                                    sortDir === 'asc' ? <SortAsc size={12} /> : <SortDesc size={12} />
                                )}
                            </th>
                            <th className="col-time">D/N</th>
                            <th className="col-day">Day</th>
                            <th className="col-cast" onClick={() => toggleSort('characters')}>
                                Cast
                                {sortBy === 'characters' && (
                                    sortDir === 'asc' ? <SortAsc size={12} /> : <SortDesc size={12} />
                                )}
                            </th>
                            <th className="col-pages">pg</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredScenes.map((scene, index) => {
                            const sceneId = scene.id || scene.scene_id;
                            const sceneUserItems = userItemsByScene[sceneId] || {};
                            const chars = [...(scene.characters || []), ...(sceneUserItems.characters || [])];
                            const charDisplay = chars.slice(0, 3).join(', ');
                            const moreChars = chars.length > 3 ? ` +${chars.length - 3}` : '';
                            
                            // Calculate scene length in eighths
                            const eighthsDisplay = getSceneEighthsDisplay(scene);
                            
                            const isInt = scene.int_ext === 'INT';
                            const isDay = scene.time_of_day === 'DAY';
                            const isExpanded = expandedRows.has(sceneId);
                            
                            // Full cast list for print (second row)
                            const fullCast = chars.join(', ');
                            
                            // Breakdown data — merge AI items + user-added items
                            const props = [...(scene.props || []), ...(sceneUserItems.props || [])];
                            const wardrobe = [...(scene.wardrobe || []), ...(sceneUserItems.wardrobe || [])];
                            const vehicles = [...(scene.vehicles || []), ...(sceneUserItems.vehicles || [])];
                            const specialFx = [...(scene.special_fx || []), ...(sceneUserItems.special_fx || [])];
                            const sound = [...(scene.sound || []), ...(sceneUserItems.sound || [])];
                            const atmosphere = scene.atmosphere || '';
                            
                            // Analysis status
                            const analysisStatus = getSceneAnalysisStatus(scene);
                            const notes = getSceneNotes(scene);
                            const notesByDept = getNotesByDepartment(notes);
                            const totalNotes = notes.length;
                            
                            // Story day separator: show when day changes from previous scene
                            const prevScene = index > 0 ? filteredScenes[index - 1] : null;
                            const showDaySeparator = scene.story_day && (
                                !prevScene || prevScene.story_day !== scene.story_day
                            );
                            const timelineClass = (scene.timeline_code || 'PRESENT').toLowerCase();
                            
                            return (
                                <React.Fragment key={sceneId}>
                                    {/* Story Day Separator */}
                                    {showDaySeparator && (
                                        <tr className="sb-day-separator-row">
                                            <td colSpan="7">
                                                <div className={`sb-day-separator timeline-${timelineClass}`}>
                                                    <div className="sb-day-separator-line"></div>
                                                    <span className={`sb-day-separator-label timeline-${timelineClass}`}>
                                                        <CalendarDays size={11} />
                                                        {scene.story_day_label || `Day ${scene.story_day}`}
                                                    </span>
                                                    <div className="sb-day-separator-line"></div>
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                    <tr 
                                        className={`stripboard-row ${isInt ? 'int' : 'ext'} ${isDay ? 'day' : 'night'} ${isExpanded ? 'expanded' : ''} status-${analysisStatus}`}
                                        onClick={() => toggleRowExpand(sceneId)}
                                        style={{ cursor: 'pointer' }}
                                    >
                                        <td className="col-scene" style={{ display: 'table-cell' }}>
                                            <span className="scene-num">{scene.scene_number}</span>
                                            <span className={`status-icon status-${analysisStatus}`} title={
                                                analysisStatus === 'analyzed' ? 'Analyzed' :
                                                analysisStatus === 'incomplete' ? 'Incomplete - needs more breakdown' :
                                                'Pending analysis'
                                            }>
                                                {analysisStatus === 'analyzed' && <CheckCircle size={12} />}
                                                {analysisStatus === 'incomplete' && <AlertCircle size={12} />}
                                                {analysisStatus === 'pending' && <Clock size={12} />}
                                            </span>
                                        </td>
                                        <td className="col-ie">
                                            <span className={`ie-badge ${isInt ? 'int' : 'ext'}`}>
                                                {scene.int_ext}
                                            </span>
                                        </td>
                                        <td className="col-setting">
                                            <span className="setting-text">{scene.setting}</span>
                                        </td>
                                        <td className="col-time">
                                            <span className={`time-badge ${isDay ? 'day' : 'night'}`}>
                                                {scene.time_of_day}
                                            </span>
                                        </td>
                                        <td className="col-day">
                                            {scene.story_day && (
                                                <span className={`sb-day-badge timeline-${timelineClass}`}>
                                                    D{scene.story_day}
                                                </span>
                                            )}
                                        </td>
                                        <td className="col-cast">
                                            <span className="cast-text">
                                                {charDisplay}{moreChars}
                                            </span>
                                            {chars.length > 0 && (
                                                <span className="cast-count">({chars.length})</span>
                                            )}
                                        </td>
                                        <td className="col-pages">
                                            <span className="eighths-num">{eighthsDisplay}</span>
                                        </td>
                                    </tr>
                                    {/* Expanded Breakdown Row */}
                                    {isExpanded && (
                                        <tr className="breakdown-row">
                                            <td colSpan="7">
                                                <div className="breakdown-content">
                                                    <div className="breakdown-grid">
                                                        {/* Cast */}
                                                        <div className="breakdown-card">
                                                            <div className="breakdown-card-header">
                                                                <Users size={14} />
                                                                <span>Cast ({chars.length})</span>
                                                                {notesByDept.cast > 0 && (
                                                                    <span className="note-indicator">
                                                                        <MessageSquare size={10} />
                                                                        {notesByDept.cast}
                                                                    </span>
                                                                )}
                                                            </div>
                                                            <div className="breakdown-card-body">
                                                                {chars.length > 0 ? (
                                                                    <ul className="breakdown-list">
                                                                        {chars.map((char, i) => (
                                                                            <li key={i}>{char}</li>
                                                                        ))}
                                                                    </ul>
                                                                ) : (
                                                                    <span className="breakdown-empty">None</span>
                                                                )}
                                                            </div>
                                                        </div>
                                                        
                                                        {/* Props */}
                                                        <div className="breakdown-card">
                                                            <div className="breakdown-card-header">
                                                                <Package size={14} />
                                                                <span>Props ({props.length})</span>
                                                                {notesByDept.props > 0 && (
                                                                    <span className="note-indicator">
                                                                        <MessageSquare size={10} />
                                                                        {notesByDept.props}
                                                                    </span>
                                                                )}
                                                            </div>
                                                            <div className="breakdown-card-body">
                                                                {props.length > 0 ? (
                                                                    <ul className="breakdown-list">
                                                                        {props.map((prop, i) => (
                                                                            <li key={i}>{prop}</li>
                                                                        ))}
                                                                    </ul>
                                                                ) : (
                                                                    <span className="breakdown-empty">None</span>
                                                                )}
                                                            </div>
                                                        </div>
                                                        
                                                        {/* Wardrobe */}
                                                        <div className="breakdown-card">
                                                            <div className="breakdown-card-header">
                                                                <Shirt size={14} />
                                                                <span>Wardrobe ({wardrobe.length})</span>
                                                                {notesByDept.wardrobe > 0 && (
                                                                    <span className="note-indicator">
                                                                        <MessageSquare size={10} />
                                                                        {notesByDept.wardrobe}
                                                                    </span>
                                                                )}
                                                            </div>
                                                            <div className="breakdown-card-body">
                                                                {wardrobe.length > 0 ? (
                                                                    <ul className="breakdown-list">
                                                                        {wardrobe.map((item, i) => (
                                                                            <li key={i}>{item}</li>
                                                                        ))}
                                                                    </ul>
                                                                ) : (
                                                                    <span className="breakdown-empty">None</span>
                                                                )}
                                                            </div>
                                                        </div>
                                                        
                                                        {/* Vehicles */}
                                                        <div className="breakdown-card">
                                                            <div className="breakdown-card-header">
                                                                <Car size={14} />
                                                                <span>Vehicles ({vehicles.length})</span>
                                                                {notesByDept.vehicles > 0 && (
                                                                    <span className="note-indicator">
                                                                        <MessageSquare size={10} />
                                                                        {notesByDept.vehicles}
                                                                    </span>
                                                                )}
                                                            </div>
                                                            <div className="breakdown-card-body">
                                                                {vehicles.length > 0 ? (
                                                                    <ul className="breakdown-list">
                                                                        {vehicles.map((v, i) => (
                                                                            <li key={i}>{v}</li>
                                                                        ))}
                                                                    </ul>
                                                                ) : (
                                                                    <span className="breakdown-empty">None</span>
                                                                )}
                                                            </div>
                                                        </div>
                                                        
                                                        {/* Special FX */}
                                                        <div className="breakdown-card">
                                                            <div className="breakdown-card-header">
                                                                <Sparkles size={14} />
                                                                <span>Special FX ({specialFx.length})</span>
                                                                {notesByDept.special_fx > 0 && (
                                                                    <span className="note-indicator">
                                                                        <MessageSquare size={10} />
                                                                        {notesByDept.special_fx}
                                                                    </span>
                                                                )}
                                                            </div>
                                                            <div className="breakdown-card-body">
                                                                {specialFx.length > 0 ? (
                                                                    <ul className="breakdown-list">
                                                                        {specialFx.map((fx, i) => (
                                                                            <li key={i}>{fx}</li>
                                                                        ))}
                                                                    </ul>
                                                                ) : (
                                                                    <span className="breakdown-empty">None</span>
                                                                )}
                                                            </div>
                                                        </div>
                                                        
                                                        {/* Sound */}
                                                        <div className="breakdown-card">
                                                            <div className="breakdown-card-header">
                                                                <Volume2 size={14} />
                                                                <span>Sound ({sound.length})</span>
                                                                {notesByDept.sound > 0 && (
                                                                    <span className="note-indicator">
                                                                        <MessageSquare size={10} />
                                                                        {notesByDept.sound}
                                                                    </span>
                                                                )}
                                                            </div>
                                                            <div className="breakdown-card-body">
                                                                {sound.length > 0 ? (
                                                                    <ul className="breakdown-list">
                                                                        {sound.map((s, i) => (
                                                                            <li key={i}>{s}</li>
                                                                        ))}
                                                                    </ul>
                                                                ) : (
                                                                    <span className="breakdown-empty">None</span>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </div>
                                                    
                                                    {/* Atmosphere */}
                                                    {atmosphere && (
                                                        <div className="breakdown-atmosphere">
                                                            <Cloud size={14} />
                                                            <span className="atmosphere-label">Atmosphere:</span>
                                                            <span className="atmosphere-text">{atmosphere}</span>
                                                        </div>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                    {/* Print-only row for full cast list */}
                                    {chars.length > 0 && (
                                        <tr className="print-cast-row">
                                            <td colSpan="7">
                                                <span className="print-cast-label">Cast: </span>
                                                <span className="print-cast-list">{fullCast}</span>
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {filteredScenes.length === 0 && (
                <div className="stripboard-empty">
                    <List size={32} />
                    <p>No scenes match the current filters</p>
                </div>
            )}
        </div>
    );
};

export default Stripboard;
