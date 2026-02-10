import React, { useState, useEffect, useMemo } from 'react';
import { 
    X, 
    Plus, 
    Trash2, 
    Clock, 
    Loader,
    MessageSquare,
    AlertCircle,
    Circle,
    CheckCircle,
    Reply,
    ChevronDown,
    ChevronUp,
    Send,
    Edit3,
    Check,
    XCircle,
    Zap,
    UserPlus2,
    Flag,
    // Department icons
    Clapperboard,
    Briefcase,
    Camera,
    Palette,
    Shirt,
    Users,
    MapPin,
    Sparkles,
    Volume2,
    Scissors,
    PenTool,
    User,
    FileText,
    Maximize2,
    Minimize2
} from 'lucide-react';
import { 
    getScriptNotes, getDepartments, createNote, deleteNote, updateNoteStatus, createReply,
    getSceneItems, createSceneItem, updateSceneItem, deleteSceneItem, removeAiItem 
} from '../../services/apiService';
import './BreakdownDrawer.css';

// Category to department mapping
const CATEGORY_DEPARTMENTS = {
    characters: ['director', 'casting', 'actor'],
    props: ['production_design', 'director'],
    wardrobe: ['costume', 'director'],
    makeup_hair: ['makeup_hair', 'director'],
    special_fx: ['vfx', 'director'],
    vehicles: ['locations', 'director', 'production_design'],
    locations: ['locations', 'production_design', 'director'],
    sound: ['sound', 'director', 'post_production'],
    animals: ['production_design', 'director'],
    extras: ['casting', 'director'],
    stunts: ['stunts', 'director', 'safety'],
    general: ['director', 'producer', 'dop', 'production_design', 'costume', 'casting', 'locations', 'vfx', 'sound', 'makeup_hair', 'writer', 'actor']
};

// Icon mapping
const DEPARTMENT_ICONS = {
    'clapperboard': Clapperboard,
    'briefcase': Briefcase,
    'camera': Camera,
    'palette': Palette,
    'shirt': Shirt,
    'users': Users,
    'map-pin': MapPin,
    'sparkles': Sparkles,
    'volume-2': Volume2,
    'scissors': Scissors,
    'pen-tool': PenTool,
    'user': User
};

const STATUS_CONFIG = {
    pending: { label: 'Pending', color: '#f59e0b', icon: Circle },
    in_progress: { label: 'In Progress', color: '#3b82f6', icon: Loader },
    complete: { label: 'Complete', color: '#22c55e', icon: CheckCircle },
};

const PRIORITY_CONFIG = {
    low: { label: 'Low', color: '#6b7280' },
    normal: { label: 'Normal', color: '#3b82f6' },
    high: { label: 'High', color: '#ef4444' },
};

const BreakdownDrawer = ({ 
    isOpen, 
    onClose, 
    category,
    categoryTitle,
    sceneId, 
    scriptId,
    sceneNumber,
    sceneSetting,
    pageStart,
    pageEnd,
    aiItems: aiItemsProp = [],  // AI-extracted items from scenes JSONB (strings)
    onAiItemRemoved,           // callback to refresh parent scene data
    sceneText = ''             // raw scene text for highlighted display
}) => {
    // --- Tab state ---
    const [activeTab, setActiveTab] = useState('items'); // 'items' | 'notes'
    
    // --- Local AI items (so we can remove without re-fetching scene) ---
    const [localAiItems, setLocalAiItems] = useState(aiItemsProp);
    
    // --- Items state ---
    const [userItems, setUserItems] = useState([]);       // active items
    const [removedItems, setRemovedItems] = useState([]); // soft-deleted (strikethrough)
    const [showRemoved, setShowRemoved] = useState(false);
    const [itemsLoading, setItemsLoading] = useState(true);
    const [showAddItem, setShowAddItem] = useState(false);
    const [newItemName, setNewItemName] = useState('');
    const [newItemDesc, setNewItemDesc] = useState('');
    const [newItemPriority, setNewItemPriority] = useState('normal');
    const [submittingItem, setSubmittingItem] = useState(false);
    const [editingItem, setEditingItem] = useState(null); // { id, item_name, description }
    const [deleteItemConfirm, setDeleteItemConfirm] = useState(null);

    // --- Notes state ---
    const [notes, setNotes] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [notesLoading, setNotesLoading] = useState(true);
    const [showAddNote, setShowAddNote] = useState(false);
    const [newNoteContent, setNewNoteContent] = useState('');
    const [submittingNote, setSubmittingNote] = useState(false);
    const [deleteNoteConfirm, setDeleteNoteConfirm] = useState(null);
    const [expandedReplies, setExpandedReplies] = useState({});
    const [replyingTo, setReplyingTo] = useState(null);
    const [replyContent, setReplyContent] = useState('');
    const [submittingReply, setSubmittingReply] = useState(false);

    // --- Script text state ---
    const [showScriptText, setShowScriptText] = useState(true);
    const [expandedScriptText, setExpandedScriptText] = useState(false);

    // --- Shared state ---
    const [error, setError] = useState(null);

    // Sync local AI items when prop changes (new category opened)
    useEffect(() => {
        setLocalAiItems(aiItemsProp);
    }, [aiItemsProp]);

    // Fetch data when drawer opens
    useEffect(() => {
        if (!isOpen || !sceneId) return;

        const fetchData = async () => {
            setItemsLoading(true);
            setNotesLoading(true);
            setError(null);

            try {
                // Fetch items, notes, and departments in parallel
                const [itemsRes, notesRes, deptRes] = await Promise.all([
                    getSceneItems(scriptId, sceneId, category, true),  // include_removed=true
                    getScriptNotes(scriptId, { scene_id: sceneId }),
                    getDepartments()
                ]);

                const allItems = itemsRes.items || [];
                setUserItems(allItems.filter(i => i.status !== 'removed'));
                setRemovedItems(allItems.filter(i => i.status === 'removed'));
                
                const filteredNotes = (notesRes.notes || []).filter(n => n.note_type === category);
                setNotes(filteredNotes);
                
                setDepartments(deptRes.departments || []);
            } catch (err) {
                console.error('Error fetching breakdown data:', err);
                setError('Failed to load data');
            } finally {
                setItemsLoading(false);
                setNotesLoading(false);
            }
        };

        fetchData();
    }, [isOpen, sceneId, scriptId, category]);

    // ========== AI ITEM REMOVAL ==========

    const handleRemoveAiItem = async (itemName) => {
        const nameStr = typeof itemName === 'string' ? itemName : (itemName.name || itemName.item_name || JSON.stringify(itemName));
        try {
            await removeAiItem(scriptId, sceneId, category, nameStr);
            setLocalAiItems(prev => prev.filter(i => {
                const n = typeof i === 'string' ? i : (i.name || i.item_name || JSON.stringify(i));
                return n !== nameStr;
            }));
            // Add to removed list for strikethrough display
            setRemovedItems(prev => [...prev, { item_name: nameStr, source_type: 'ai_removed', status: 'removed', created_at: new Date().toISOString() }]);
            if (onAiItemRemoved) onAiItemRemoved();
        } catch (err) {
            console.error('Error removing item:', err);
            setError('Failed to remove item');
        }
    };

    // ========== ITEM HANDLERS ==========

    const handleAddItem = async (e) => {
        e.preventDefault();
        if (!newItemName.trim()) return;

        setSubmittingItem(true);
        try {
            const created = await createSceneItem(scriptId, sceneId, {
                item_type: category,
                item_name: newItemName.trim(),
                description: newItemDesc.trim(),
                priority: newItemPriority,
            });
            setUserItems(prev => [created, ...prev]);
            setNewItemName('');
            setNewItemDesc('');
            setNewItemPriority('normal');
            setShowAddItem(false);
        } catch (err) {
            console.error('Error creating item:', err);
            setError('Failed to create item');
        } finally {
            setSubmittingItem(false);
        }
    };

    const handleUpdateItem = async (itemId, updates) => {
        try {
            const updated = await updateSceneItem(itemId, updates);
            setUserItems(prev => prev.map(i => i.id === itemId ? updated : i));
            setEditingItem(null);
        } catch (err) {
            console.error('Error updating item:', err);
            setError('Failed to update item');
        }
    };

    const handleDeleteItem = async (itemId) => {
        try {
            await deleteSceneItem(itemId);
            // Move item from active to removed list (soft-delete)
            const removedItem = userItems.find(i => i.id === itemId);
            setUserItems(prev => prev.filter(i => i.id !== itemId));
            if (removedItem) {
                setRemovedItems(prev => [...prev, { ...removedItem, status: 'removed' }]);
            }
            setDeleteItemConfirm(null);
        } catch (err) {
            console.error('Error deleting item:', err);
            setError('Failed to delete item');
            setDeleteItemConfirm(null);
        }
    };

    const handleCycleStatus = async (item) => {
        const order = ['pending', 'in_progress', 'complete'];
        const nextIdx = (order.indexOf(item.status) + 1) % order.length;
        await handleUpdateItem(item.id, { status: order[nextIdx] });
    };

    // ========== NOTE HANDLERS ==========

    const handleAddNote = async (e) => {
        e.preventDefault();
        if (!newNoteContent.trim()) return;

        setSubmittingNote(true);
        try {
            await createNote(scriptId, {
                content: newNoteContent,
                scene_id: sceneId,
                note_type: category
            });
            // Refresh notes
            const notesRes = await getScriptNotes(scriptId, { scene_id: sceneId });
            setNotes((notesRes.notes || []).filter(n => n.note_type === category));
            setNewNoteContent('');
            setShowAddNote(false);
        } catch (err) {
            console.error('Error creating note:', err);
            setError('Failed to create note');
        } finally {
            setSubmittingNote(false);
        }
    };

    const handleDeleteNote = async (noteId) => {
        try {
            await deleteNote(noteId);
            setNotes(prev => prev.filter(n => n.id !== noteId));
            setDeleteNoteConfirm(null);
        } catch (err) {
            console.error('Error deleting note:', err);
            setError('Failed to delete note');
            setDeleteNoteConfirm(null);
        }
    };

    const handleToggleNoteStatus = async (noteId, currentStatus) => {
        const newStatus = currentStatus === 'resolved' ? 'open' : 'resolved';
        try {
            const updated = await updateNoteStatus(noteId, newStatus);
            setNotes(prev => prev.map(n => n.id === noteId ? { ...n, status: updated.status } : n));
        } catch (err) {
            console.error('Error updating note status:', err);
        }
    };

    const handleReply = async (noteId) => {
        if (!replyContent.trim()) return;
        setSubmittingReply(true);
        try {
            const newReply = await createReply(noteId, replyContent);
            setNotes(prev => prev.map(n => {
                if (n.id === noteId) {
                    return { ...n, replies: [...(n.replies || []), newReply], reply_count: (n.reply_count || 0) + 1 };
                }
                return n;
            }));
            setReplyContent('');
            setReplyingTo(null);
            setExpandedReplies(prev => ({ ...prev, [noteId]: true }));
        } catch (err) {
            console.error('Error creating reply:', err);
        } finally {
            setSubmittingReply(false);
        }
    };

    // ========== HELPERS ==========

    const getDepartmentIcon = (iconName) => {
        return DEPARTMENT_ICONS[iconName] || MessageSquare;
    };

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    };

    // Build highlighted scene text with extraction markers
    // NOTE: useMemo must be called before any early returns (Rules of Hooks)
    const { highlightedLines, notFoundItems } = useMemo(() => {
        if (!sceneText) return { highlightedLines: null, notFoundItems: [] };

        // Collect all item names to highlight (AI + user-added)
        const aiNames = localAiItems.map(i =>
            typeof i === 'string' ? i : (i.name || i.item_name || '')
        ).filter(Boolean);
        const userNames = userItems.map(i => i.item_name).filter(Boolean);

        if (aiNames.length === 0 && userNames.length === 0) {
            const lines = sceneText.split('\n').map((line, i) => (
                <div key={i} className="bd-script-line">{line || '\u00A0'}</div>
            ));
            return { highlightedLines: lines, notFoundItems: [] };
        }

        // Sort by length descending so longer matches take priority
        const allNames = [
            ...aiNames.map(n => ({ name: n, type: 'ai' })),
            ...userNames.map(n => ({ name: n, type: 'user' }))
        ].sort((a, b) => b.name.length - a.name.length);

        // Check which items actually appear in text (case-insensitive)
        const textLower = sceneText.toLowerCase();
        const foundNames = allNames.filter(n => textLower.includes(n.name.toLowerCase()));
        const notFound = allNames.filter(n => !textLower.includes(n.name.toLowerCase()));

        if (foundNames.length === 0) {
            const lines = sceneText.split('\n').map((line, i) => (
                <div key={i} className="bd-script-line">{line || '\u00A0'}</div>
            ));
            return { highlightedLines: lines, notFoundItems: notFound };
        }

        // Build a single regex with found item names only
        const escaped = foundNames.map(n => n.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
        const regex = new RegExp(`(${escaped.join('|')})`, 'gi');

        // Build a lookup for type
        const typeLookup = {};
        foundNames.forEach(n => {
            typeLookup[n.name.toLowerCase()] = n.type;
        });

        const lines = sceneText.split('\n').map((line, lineIdx) => {
            if (!line.trim()) return <div key={lineIdx} className="bd-script-line">&nbsp;</div>;

            const parts = line.split(regex);
            return (
                <div key={lineIdx} className="bd-script-line">
                    {parts.map((part, partIdx) => {
                        const matchType = typeLookup[part.toLowerCase()];
                        if (matchType) {
                            return (
                                <mark
                                    key={partIdx}
                                    className={`bd-extraction-highlight ${matchType === 'user' ? 'user-highlight' : 'ai-highlight'}`}
                                    title={`${matchType === 'ai' ? 'AI-detected' : 'User-added'}: ${part}`}
                                >
                                    {part}
                                </mark>
                            );
                        }
                        return <span key={partIdx}>{part}</span>;
                    })}
                </div>
            );
        });
        return { highlightedLines: lines, notFoundItems: notFound };
    }, [sceneText, localAiItems, userItems]);

    if (!isOpen) return null;

    const totalItems = localAiItems.length + userItems.length;
    const totalNotes = notes.length;

    return (
        <>
            {/* Backdrop */}
            <div className="drawer-backdrop" onClick={onClose} />
            
            {/* Drawer */}
            <div className={`breakdown-drawer ${isOpen ? 'open' : ''}`}>
                {/* Header */}
                <div className="bd-header">
                    <div className="bd-title-group">
                        <h3>{categoryTitle}</h3>
                        {sceneNumber && (
                            <span className="bd-subtitle">
                                Scene {sceneNumber}
                                {sceneSetting && ` · ${sceneSetting}`}
                                {pageStart && ` · p.${pageStart}${pageEnd && pageEnd !== pageStart ? `-${pageEnd}` : ''}`}
                            </span>
                        )}
                    </div>
                    <button className="bd-close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                {/* Tabs */}
                <div className="bd-tabs">
                    <button 
                        className={`bd-tab ${activeTab === 'items' ? 'active' : ''}`}
                        onClick={() => setActiveTab('items')}
                    >
                        <Zap size={14} />
                        Items {totalItems > 0 && <span className="bd-tab-count">{totalItems}</span>}
                    </button>
                    <button 
                        className={`bd-tab ${activeTab === 'notes' ? 'active' : ''}`}
                        onClick={() => setActiveTab('notes')}
                    >
                        <MessageSquare size={14} />
                        Notes {totalNotes > 0 && <span className="bd-tab-count">{totalNotes}</span>}
                    </button>
                </div>

                {/* Content */}
                <div className="bd-content">
                    {error && (
                        <div className="bd-error">
                            <AlertCircle size={16} />
                            <span>{error}</span>
                            <button onClick={() => setError(null)}><X size={14} /></button>
                        </div>
                    )}

                    {activeTab === 'items' ? (
                        // ========== ITEMS TAB ==========
                        itemsLoading ? (
                            <div className="bd-loading"><Loader size={24} className="spin" /><span>Loading items...</span></div>
                        ) : (
                            <>
                                {/* Collapsible Script Text with Highlights */}
                                {sceneText && (
                                    <div className="bd-script-text-section">
                                        <div className="bd-script-text-header">
                                            <button
                                                className="bd-script-text-toggle"
                                                onClick={() => setShowScriptText(!showScriptText)}
                                            >
                                                {showScriptText ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                                <FileText size={14} />
                                                <span>Script Text</span>
                                                {(localAiItems.length + userItems.length) > 0 && (
                                                    <span className="bd-highlight-count">
                                                        {localAiItems.length + userItems.length - (notFoundItems?.length || 0)} of {localAiItems.length + userItems.length} found
                                                    </span>
                                                )}
                                            </button>
                                            {showScriptText && (
                                                <button
                                                    className="bd-script-expand-btn"
                                                    onClick={() => setExpandedScriptText(!expandedScriptText)}
                                                    title={expandedScriptText ? 'Collapse' : 'Expand'}
                                                >
                                                    {expandedScriptText ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
                                                </button>
                                            )}
                                        </div>
                                        {showScriptText && (
                                            <div className="bd-script-text-content">
                                                <div className={`bd-script-text-body ${expandedScriptText ? 'expanded' : ''}`}>
                                                    {highlightedLines}
                                                </div>
                                                {/* Not-found items: AI-inferred, not literally in text */}
                                                {notFoundItems && notFoundItems.length > 0 && (
                                                    <div className="bd-not-found-bar">
                                                        <span className="bd-not-found-label">AI-inferred (not in text):</span>
                                                        {notFoundItems.map((item, idx) => (
                                                            <span key={idx} className={`bd-not-found-chip ${item.type}`}>
                                                                {item.name}
                                                            </span>
                                                        ))}
                                                    </div>
                                                )}
                                                {(localAiItems.length > 0 || userItems.length > 0) && (
                                                    <div className="bd-highlight-legend">
                                                        {localAiItems.length > 0 && (
                                                            <span className="bd-legend-item">
                                                                <mark className="bd-extraction-highlight ai-highlight">AI</mark>
                                                                <span>In text</span>
                                                            </span>
                                                        )}
                                                        {userItems.length > 0 && (
                                                            <span className="bd-legend-item">
                                                                <mark className="bd-extraction-highlight user-highlight">User</mark>
                                                                <span>Team-added</span>
                                                            </span>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* All Items — AI items as removable pills */}
                                {localAiItems.length > 0 && (
                                    <div className="bd-ai-items">
                                        {localAiItems.map((item, idx) => {
                                            const name = typeof item === 'string' ? item : item.name || item.item_name || JSON.stringify(item);
                                            return (
                                                <div key={`ai-${idx}`} className="bd-ai-item">
                                                    <span className="bd-ai-name">{name}</span>
                                                    <button
                                                        className="bd-ai-remove"
                                                        onClick={() => handleRemoveAiItem(item)}
                                                        title="Remove item"
                                                    >
                                                        <X size={12} />
                                                    </button>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}

                                {/* User-Added Items (Editable) */}
                                <div className="bd-section">
                                    {userItems.length === 0 && localAiItems.length === 0 ? (
                                        <div className="bd-empty">
                                            <Plus size={32} />
                                            <p>No items yet</p>
                                            <span>Add breakdown items for this category</span>
                                        </div>
                                    ) : userItems.length === 0 ? (
                                        <p className="bd-empty-hint">No team-added items yet</p>
                                    ) : (
                                        <div className="bd-user-items">
                                            {userItems.map(item => {
                                                const statusCfg = STATUS_CONFIG[item.status] || STATUS_CONFIG.pending;
                                                const priorityCfg = PRIORITY_CONFIG[item.priority] || PRIORITY_CONFIG.normal;
                                                const StatusIcon = statusCfg.icon;
                                                const isEditing = editingItem?.id === item.id;

                                                return (
                                                    <div key={item.id} className={`bd-user-item ${item.status === 'complete' ? 'complete' : ''}`}>
                                                        <div className="bd-item-top">
                                                            <button
                                                                className="bd-status-btn"
                                                                onClick={() => handleCycleStatus(item)}
                                                                title={`Status: ${statusCfg.label} (click to cycle)`}
                                                                style={{ color: statusCfg.color }}
                                                            >
                                                                <StatusIcon size={18} />
                                                            </button>

                                                            {isEditing ? (
                                                                <div className="bd-edit-inline">
                                                                    <input
                                                                        type="text"
                                                                        value={editingItem.item_name}
                                                                        onChange={e => setEditingItem(prev => ({ ...prev, item_name: e.target.value }))}
                                                                        className="bd-edit-input"
                                                                        autoFocus
                                                                    />
                                                                    <button className="bd-edit-save" onClick={() => handleUpdateItem(item.id, { item_name: editingItem.item_name, description: editingItem.description })}>
                                                                        <Check size={14} />
                                                                    </button>
                                                                    <button className="bd-edit-cancel" onClick={() => setEditingItem(null)}>
                                                                        <XCircle size={14} />
                                                                    </button>
                                                                </div>
                                                            ) : (
                                                                <span className={`bd-item-name ${item.status === 'complete' ? 'strikethrough' : ''}`}>
                                                                    {item.item_name}
                                                                </span>
                                                            )}

                                                            <div className="bd-item-actions">
                                                                {!isEditing && (
                                                                    <button className="bd-action-btn" onClick={() => setEditingItem({ id: item.id, item_name: item.item_name, description: item.description || '' })} title="Edit">
                                                                        <Edit3 size={14} />
                                                                    </button>
                                                                )}
                                                                <button className="bd-action-btn delete" onClick={() => setDeleteItemConfirm({ id: item.id, name: item.item_name })} title="Delete">
                                                                    <Trash2 size={14} />
                                                                </button>
                                                            </div>
                                                        </div>

                                                        {/* Item meta row */}
                                                        <div className="bd-item-meta">
                                                            <span className="bd-priority-badge" style={{ color: priorityCfg.color, borderColor: priorityCfg.color }}>
                                                                <Flag size={10} />
                                                                {priorityCfg.label}
                                                            </span>
                                                            {item.creator_name && (
                                                                <span className="bd-creator">by {item.creator_name}</span>
                                                            )}
                                                            {item.department_name && (
                                                                <span className="bd-dept-badge" style={{ backgroundColor: `${item.department_color}20`, color: item.department_color }}>
                                                                    {item.department_name}
                                                                </span>
                                                            )}
                                                        </div>

                                                        {/* Description */}
                                                        {isEditing ? (
                                                            <textarea
                                                                className="bd-edit-desc"
                                                                value={editingItem.description}
                                                                onChange={e => setEditingItem(prev => ({ ...prev, description: e.target.value }))}
                                                                placeholder="Add description..."
                                                                rows={2}
                                                            />
                                                        ) : item.description ? (
                                                            <p className="bd-item-desc">{item.description}</p>
                                                        ) : null}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>

                                {/* Add Item Form */}
                                {!showAddItem ? (
                                    <button className="bd-add-trigger" onClick={() => setShowAddItem(true)}>
                                        <Plus size={18} />
                                        Add Item
                                    </button>
                                ) : (
                                    <form className="bd-add-form" onSubmit={handleAddItem}>
                                        <input
                                            type="text"
                                            className="bd-add-input"
                                            placeholder="Item name..."
                                            value={newItemName}
                                            onChange={e => setNewItemName(e.target.value)}
                                            required
                                            autoFocus
                                        />
                                        <textarea
                                            className="bd-add-desc"
                                            placeholder="Description (optional)..."
                                            value={newItemDesc}
                                            onChange={e => setNewItemDesc(e.target.value)}
                                            rows={2}
                                        />
                                        <div className="bd-add-row">
                                            <select 
                                                className="bd-priority-select"
                                                value={newItemPriority}
                                                onChange={e => setNewItemPriority(e.target.value)}
                                            >
                                                <option value="low">Low Priority</option>
                                                <option value="normal">Normal Priority</option>
                                                <option value="high">High Priority</option>
                                            </select>
                                            <div className="bd-form-actions">
                                                <button type="button" className="bd-cancel-btn" onClick={() => { setShowAddItem(false); setNewItemName(''); setNewItemDesc(''); }}>
                                                    Cancel
                                                </button>
                                                <button type="submit" className="bd-submit-btn" disabled={submittingItem || !newItemName.trim()}>
                                                    {submittingItem ? <Loader size={14} className="spin" /> : <Plus size={14} />}
                                                    Add
                                                </button>
                                            </div>
                                        </div>
                                    </form>
                                )}

                                {/* Removed Items (strikethrough tracking) */}
                                {removedItems.length > 0 && (
                                    <div className="bd-removed-section">
                                        <button
                                            className="bd-removed-toggle"
                                            onClick={() => setShowRemoved(!showRemoved)}
                                        >
                                            {showRemoved ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                            <span>Removed ({removedItems.length})</span>
                                        </button>
                                        {showRemoved && (
                                            <div className="bd-removed-list">
                                                {removedItems.map((item, idx) => (
                                                    <div key={item.id || `removed-${idx}`} className="bd-removed-item">
                                                        <span className="bd-removed-name">{item.item_name}</span>
                                                        {item.source_type === 'ai_removed' && (
                                                            <span className="bd-removed-source">was AI-detected</span>
                                                        )}
                                                        {item.creator_name && (
                                                            <span className="bd-removed-by">removed by {item.creator_name}</span>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </>
                        )
                    ) : (
                        // ========== NOTES TAB ==========
                        notesLoading ? (
                            <div className="bd-loading"><Loader size={24} className="spin" /><span>Loading notes...</span></div>
                        ) : (
                            <>
                                <div className="bd-notes-list">
                                    {notes.length === 0 ? (
                                        <div className="bd-empty">
                                            <MessageSquare size={32} />
                                            <p>No notes yet</p>
                                            <span>Add a note to start collaborating</span>
                                        </div>
                                    ) : (
                                        notes.map(note => {
                                            const isResolved = note.status === 'resolved';
                                            const dept = departments.find(d => d.code === note.department_code);
                                            const IconComponent = dept ? getDepartmentIcon(dept.icon) : MessageSquare;
                                            return (
                                                <div key={note.id} className={`bd-note-item ${isResolved ? 'resolved' : ''}`}>
                                                    <div className="bd-note-header">
                                                        <div className="bd-note-author">
                                                            <span className="bd-author-name">{note.creator_name || 'Unknown'}</span>
                                                            {dept && (
                                                                <span className="bd-dept-badge small" style={{ backgroundColor: `${dept.color}20`, color: dept.color }}>
                                                                    <IconComponent size={10} />
                                                                    {dept.name}
                                                                </span>
                                                            )}
                                                        </div>
                                                        <button
                                                            className={`bd-note-status-toggle ${isResolved ? 'resolved' : ''}`}
                                                            onClick={() => handleToggleNoteStatus(note.id, note.status)}
                                                            title={isResolved ? 'Mark as open' : 'Mark as resolved'}
                                                        >
                                                            {isResolved ? <CheckCircle size={18} /> : <Circle size={18} />}
                                                        </button>
                                                    </div>
                                                    <div className="bd-note-time">
                                                        <Clock size={12} />
                                                        {formatDate(note.created_at)}
                                                    </div>
                                                    <p className={`bd-note-content ${isResolved ? 'resolved' : ''}`}>{note.content}</p>

                                                    <div className="bd-note-actions">
                                                        {note.reply_count > 0 && (
                                                            <button className="bd-replies-toggle" onClick={() => setExpandedReplies(prev => ({ ...prev, [note.id]: !prev[note.id] }))}>
                                                                <MessageSquare size={14} />
                                                                {note.reply_count} {note.reply_count === 1 ? 'reply' : 'replies'}
                                                                {expandedReplies[note.id] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                                            </button>
                                                        )}
                                                        <button className="bd-reply-btn" onClick={() => { setReplyingTo(replyingTo === note.id ? null : note.id); setReplyContent(''); }}>
                                                            <Reply size={14} /> Reply
                                                        </button>
                                                        <button className="bd-delete-btn" onClick={() => setDeleteNoteConfirm({ id: note.id, preview: note.content.substring(0, 50) + (note.content.length > 50 ? '...' : '') })}>
                                                            <Trash2 size={14} />
                                                        </button>
                                                    </div>

                                                    {/* Replies */}
                                                    {expandedReplies[note.id] && note.replies && note.replies.length > 0 && (
                                                        <div className="bd-replies-list">
                                                            {note.replies.map(reply => (
                                                                <div key={reply.id} className="bd-reply-item">
                                                                    <div className="bd-reply-header">
                                                                        <span className="bd-reply-author">{reply.creator_name || 'Unknown'}</span>
                                                                        <span className="bd-reply-time">{formatDate(reply.created_at)}</span>
                                                                    </div>
                                                                    <p className="bd-reply-content">{reply.content}</p>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}

                                                    {/* Reply input */}
                                                    {replyingTo === note.id && (
                                                        <div className="bd-reply-input-row">
                                                            <input
                                                                type="text"
                                                                className="bd-reply-input"
                                                                placeholder="Write a reply..."
                                                                value={replyContent}
                                                                onChange={e => setReplyContent(e.target.value)}
                                                                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleReply(note.id); } }}
                                                                autoFocus
                                                            />
                                                            <button className="bd-send-reply" onClick={() => handleReply(note.id)} disabled={submittingReply || !replyContent.trim()}>
                                                                {submittingReply ? <Loader size={14} className="spin" /> : <Send size={14} />}
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })
                                    )}
                                </div>

                                {/* Add Note */}
                                {!showAddNote ? (
                                    <button className="bd-add-trigger" onClick={() => setShowAddNote(true)}>
                                        <Plus size={18} />
                                        Add Note
                                    </button>
                                ) : (
                                    <form className="bd-add-form" onSubmit={handleAddNote}>
                                        <textarea
                                            placeholder="Write your note..."
                                            value={newNoteContent}
                                            onChange={e => setNewNoteContent(e.target.value)}
                                            required
                                            rows={3}
                                            autoFocus
                                        />
                                        <div className="bd-form-actions">
                                            <button type="button" className="bd-cancel-btn" onClick={() => { setShowAddNote(false); setNewNoteContent(''); }}>
                                                Cancel
                                            </button>
                                            <button type="submit" className="bd-submit-btn" disabled={submittingNote || !newNoteContent.trim()}>
                                                {submittingNote ? <Loader size={14} className="spin" /> : <Plus size={14} />}
                                                Add Note
                                            </button>
                                        </div>
                                    </form>
                                )}
                            </>
                        )
                    )}
                </div>
            </div>

            {/* Delete Item Confirmation */}
            {deleteItemConfirm && (
                <div className="bd-confirm-overlay">
                    <div className="bd-confirm-modal">
                        <div className="bd-confirm-icon"><Trash2 size={24} /></div>
                        <h4>Delete Item?</h4>
                        <p className="bd-confirm-name">"{deleteItemConfirm.name}"</p>
                        <p className="bd-confirm-warning">This action cannot be undone.</p>
                        <div className="bd-confirm-actions">
                            <button className="bd-confirm-cancel" onClick={() => setDeleteItemConfirm(null)}>Cancel</button>
                            <button className="bd-confirm-delete" onClick={() => handleDeleteItem(deleteItemConfirm.id)}>
                                <Trash2 size={14} /> Delete
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Delete Note Confirmation */}
            {deleteNoteConfirm && (
                <div className="bd-confirm-overlay">
                    <div className="bd-confirm-modal">
                        <div className="bd-confirm-icon"><Trash2 size={24} /></div>
                        <h4>Delete Note?</h4>
                        <p className="bd-confirm-name">"{deleteNoteConfirm.preview}"</p>
                        <p className="bd-confirm-warning">This action cannot be undone.</p>
                        <div className="bd-confirm-actions">
                            <button className="bd-confirm-cancel" onClick={() => setDeleteNoteConfirm(null)}>Cancel</button>
                            <button className="bd-confirm-delete" onClick={() => handleDeleteNote(deleteNoteConfirm.id)}>
                                <Trash2 size={14} /> Delete
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};

export default BreakdownDrawer;
