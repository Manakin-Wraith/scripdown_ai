import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
    List, Sun, Moon, Home, Building2, Users, 
    GripVertical, Printer, Download, ArrowLeft,
    Loader, Filter, SortAsc, SortDesc
} from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { useScript } from '../../context/ScriptContext';
import { getScenes, getScriptMetadata, previewReport } from '../../services/apiService';
import './Stripboard.css';

const Stripboard = () => {
    const { scriptId } = useParams();
    const navigate = useNavigate();
    const toast = useToast();
    const { setScript } = useScript();
    
    const [scenes, setScenes] = useState([]);
    const [metadata, setMetadata] = useState(null);
    const [loading, setLoading] = useState(true);
    const [sortBy, setSortBy] = useState('scene_order');
    const [sortDir, setSortDir] = useState('asc');
    const [filterIntExt, setFilterIntExt] = useState('all');
    const [filterTimeOfDay, setFilterTimeOfDay] = useState('all');

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                
                // Fetch scenes
                const sceneData = await getScenes(scriptId);
                setScenes(sceneData.scenes || []);
                
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
    }, [scenes, filterIntExt, filterTimeOfDay, sortBy, sortDir]);

    // Calculate stats
    const stats = useMemo(() => {
        const intCount = scenes.filter(s => s.int_ext === 'INT').length;
        const extCount = scenes.filter(s => s.int_ext === 'EXT').length;
        const dayCount = scenes.filter(s => s.time_of_day === 'DAY').length;
        const nightCount = scenes.filter(s => s.time_of_day === 'NIGHT').length;
        
        return { intCount, extCount, dayCount, nightCount };
    }, [scenes]);

    const handlePrint = () => {
        window.print();
    };

    const toggleSort = (field) => {
        if (sortBy === field) {
            setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
        } else {
            setSortBy(field);
            setSortDir('asc');
        }
    };

    if (loading) {
        return (
            <div className="stripboard-loading">
                <Loader className="spin" size={32} />
                <p>Loading stripboard...</p>
            </div>
        );
    }

    return (
        <div className="stripboard">
            {/* Header */}
            <div className="stripboard-header">
                <h1>
                    <List size={24} />
                    One-Liner / Stripboard
                </h1>
                <div className="header-actions">
                    <button className="action-btn" onClick={handlePrint}>
                        <Printer size={16} />
                        Print
                    </button>
                </div>
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
            </div>

            {/* Filters */}
            <div className="stripboard-filters">
                <div className="filter-group">
                    <Filter size={14} />
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
                    <span className="filter-label">Sort:</span>
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
                            <th className="col-cast" onClick={() => toggleSort('characters')}>
                                Cast
                                {sortBy === 'characters' && (
                                    sortDir === 'asc' ? <SortAsc size={12} /> : <SortDesc size={12} />
                                )}
                            </th>
                            <th className="col-pages">Pg</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredScenes.map((scene, index) => {
                            const chars = scene.characters || [];
                            const charDisplay = chars.slice(0, 3).join(', ');
                            const moreChars = chars.length > 3 ? ` +${chars.length - 3}` : '';
                            
                            const pageInfo = scene.page_start 
                                ? (scene.page_end && scene.page_end !== scene.page_start
                                    ? `${scene.page_start}-${scene.page_end}`
                                    : scene.page_start)
                                : '-';
                            
                            const isInt = scene.int_ext === 'INT';
                            const isDay = scene.time_of_day === 'DAY';
                            
                            return (
                                <tr 
                                    key={scene.id || scene.scene_id}
                                    className={`stripboard-row ${isInt ? 'int' : 'ext'} ${isDay ? 'day' : 'night'}`}
                                >
                                    <td className="col-scene">
                                        <span className="scene-num">{scene.scene_number}</span>
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
                                    <td className="col-cast">
                                        <span className="cast-text">
                                            {charDisplay}{moreChars}
                                        </span>
                                        {chars.length > 0 && (
                                            <span className="cast-count">({chars.length})</span>
                                        )}
                                    </td>
                                    <td className="col-pages">
                                        <span className="page-num">{pageInfo}</span>
                                    </td>
                                </tr>
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
