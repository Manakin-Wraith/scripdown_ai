import React, { useState, useEffect } from 'react';
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
    User
} from 'lucide-react';
import { getScriptNotes, getDepartments, createNote, deleteNote, updateNoteStatus, createReply } from '../../services/apiService';
import './NoteDrawer.css';

// Category to department mapping
const CATEGORY_DEPARTMENTS = {
    characters: ['director', 'casting', 'actor'],
    props: ['production_design', 'director'],
    wardrobe: ['costume', 'director'],
    makeup_hair: ['makeup_hair', 'director'],
    special_fx: ['vfx', 'director'],
    vehicles: ['locations', 'director', 'production_design'],
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

const NoteDrawer = ({ 
    isOpen, 
    onClose, 
    category,
    categoryTitle,
    sceneId, 
    scriptId,
    sceneNumber,
    sceneSetting,
    pageStart,
    pageEnd
}) => {
    const [notes, setNotes] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showAddForm, setShowAddForm] = useState(false);
    const [newNote, setNewNote] = useState({
        content: ''
    });
    const [submitting, setSubmitting] = useState(false);
    const [deleteConfirm, setDeleteConfirm] = useState(null); // { noteId, noteName }
    const [expandedReplies, setExpandedReplies] = useState({}); // { noteId: boolean }
    const [replyingTo, setReplyingTo] = useState(null); // noteId being replied to
    const [replyContent, setReplyContent] = useState('');
    const [submittingReply, setSubmittingReply] = useState(false);

    // Fetch departments and notes when drawer opens
    useEffect(() => {
        if (!isOpen || !sceneId) return;

        const fetchData = async () => {
            setLoading(true);
            setError(null);

            try {
                // Fetch all departments (for displaying badges)
                const deptResponse = await getDepartments();
                const allDepts = deptResponse.departments || [];
                setDepartments(allDepts);

                // Fetch notes for this scene and category
                const notesResponse = await getScriptNotes(scriptId, { scene_id: sceneId });
                
                // Filter notes by note_type (category)
                const filteredNotes = (notesResponse.notes || []).filter(note => 
                    note.note_type === category
                );
                setNotes(filteredNotes);

            } catch (err) {
                console.error('Error fetching data:', err);
                setError('Failed to load notes');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [isOpen, sceneId, scriptId, category]);

    const handleAddNote = async (e) => {
        e.preventDefault();
        if (!newNote.content.trim()) return;

        setSubmitting(true);
        try {
            // Backend will auto-detect user's department from script_members
            await createNote(scriptId, {
                content: newNote.content,
                scene_id: sceneId,
                note_type: category // Store the category as note_type (characters, props, etc.)
            });

            // Refresh notes - show all notes for this category
            const notesResponse = await getScriptNotes(scriptId, { scene_id: sceneId });
            const filteredNotes = (notesResponse.notes || []).filter(note => 
                note.note_type === category
            );
            setNotes(filteredNotes);

            // Reset form
            setNewNote({ content: '' });
            setShowAddForm(false);

        } catch (err) {
            console.error('Error creating note:', err);
            setError('Failed to create note');
        } finally {
            setSubmitting(false);
        }
    };

    const handleDeleteNote = async (noteId) => {
        try {
            await deleteNote(noteId);
            setNotes(prev => prev.filter(n => n.id !== noteId));
            setDeleteConfirm(null);
        } catch (err) {
            console.error('Error deleting note:', err);
            setError('Failed to delete note');
            setDeleteConfirm(null);
        }
    };

    const handleToggleStatus = async (noteId, currentStatus) => {
        const newStatus = currentStatus === 'resolved' ? 'open' : 'resolved';
        try {
            const updatedNote = await updateNoteStatus(noteId, newStatus);
            setNotes(prev => prev.map(n => 
                n.id === noteId ? { ...n, status: updatedNote.status } : n
            ));
        } catch (err) {
            console.error('Error updating note status:', err);
            setError('Failed to update note status');
        }
    };

    const toggleReplies = (noteId) => {
        setExpandedReplies(prev => ({
            ...prev,
            [noteId]: !prev[noteId]
        }));
    };

    const handleReply = async (noteId) => {
        if (!replyContent.trim()) return;
        
        setSubmittingReply(true);
        try {
            const newReply = await createReply(noteId, replyContent);
            
            // Add reply to the note's replies array
            setNotes(prev => prev.map(n => {
                if (n.id === noteId) {
                    return {
                        ...n,
                        replies: [...(n.replies || []), newReply],
                        reply_count: (n.reply_count || 0) + 1
                    };
                }
                return n;
            }));
            
            // Clear reply state and expand replies
            setReplyContent('');
            setReplyingTo(null);
            setExpandedReplies(prev => ({ ...prev, [noteId]: true }));
        } catch (err) {
            console.error('Error creating reply:', err);
            setError('Failed to create reply');
        } finally {
            setSubmittingReply(false);
        }
    };

    const getDepartmentIcon = (iconName) => {
        const IconComponent = DEPARTMENT_ICONS[iconName] || MessageSquare;
        return IconComponent;
    };

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    if (!isOpen) return null;

    return (
        <>
            {/* Backdrop */}
            <div className="drawer-backdrop" onClick={onClose} />
            
            {/* Drawer */}
            <div className={`note-drawer ${isOpen ? 'open' : ''}`}>
                {/* Header */}
                <div className="drawer-header">
                    <div className="drawer-title-group">
                        <h3>{categoryTitle} Notes</h3>
                        {sceneNumber && (
                            <span className="drawer-subtitle">
                                Scene {sceneNumber}
                                {sceneSetting && ` • ${sceneSetting}`}
                                {pageStart && ` • p.${pageStart}${pageEnd && pageEnd !== pageStart ? `-${pageEnd}` : ''}`}
                            </span>
                        )}
                    </div>
                    <button className="close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="drawer-content">
                    {loading ? (
                        <div className="drawer-loading">
                            <Loader size={24} className="spin" />
                            <span>Loading notes...</span>
                        </div>
                    ) : error ? (
                        <div className="drawer-error">
                            <AlertCircle size={20} />
                            <span>{error}</span>
                        </div>
                    ) : (
                        <>
                            {/* Notes List */}
                            <div className="notes-list">
                                {notes.length === 0 ? (
                                    <div className="no-notes">
                                        <MessageSquare size={32} />
                                        <p>No notes yet</p>
                                        <span>Add a note to start collaborating</span>
                                    </div>
                                ) : (
                                    notes.map(note => {
                                        const isResolved = note.status === 'resolved';
                                        // Get department info for the badge
                                        const dept = departments.find(d => d.code === note.department_code);
                                        const IconComponent = dept ? getDepartmentIcon(dept.icon) : MessageSquare;
                                        return (
                                            <div key={note.id} className={`note-item ${isResolved ? 'resolved' : ''}`}>
                                                <div className="note-header">
                                                    <div className="note-author">
                                                        <span className="author-name">
                                                            {note.creator_name || 'Unknown'}
                                                        </span>
                                                        {dept && (
                                                            <span 
                                                                className="dept-badge small"
                                                                style={{ 
                                                                    backgroundColor: `${dept.color}20`,
                                                                    color: dept.color 
                                                                }}
                                                            >
                                                                <IconComponent size={10} />
                                                                {dept.name}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <button 
                                                        className={`status-toggle ${isResolved ? 'resolved' : ''}`}
                                                        onClick={() => handleToggleStatus(note.id, note.status)}
                                                        title={isResolved ? 'Mark as open' : 'Mark as resolved'}
                                                    >
                                                        {isResolved ? (
                                                            <CheckCircle size={18} />
                                                        ) : (
                                                            <Circle size={18} />
                                                        )}
                                                    </button>
                                                </div>
                                                <div className="note-meta">
                                                    <span className="note-time">
                                                        <Clock size={12} />
                                                        {formatDate(note.created_at)}
                                                    </span>
                                                </div>
                                                <p className={`note-content ${isResolved ? 'resolved' : ''}`}>{note.content}</p>
                                                
                                                {/* Note Actions: Reply count, Reply button, Delete */}
                                                <div className="note-actions">
                                                    {note.reply_count > 0 && (
                                                        <button 
                                                            className="replies-toggle"
                                                            onClick={() => toggleReplies(note.id)}
                                                        >
                                                            <MessageSquare size={14} />
                                                            {note.reply_count} {note.reply_count === 1 ? 'reply' : 'replies'}
                                                            {expandedReplies[note.id] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                                        </button>
                                                    )}
                                                    <button 
                                                        className="reply-btn"
                                                        onClick={() => {
                                                            setReplyingTo(replyingTo === note.id ? null : note.id);
                                                            setReplyContent('');
                                                        }}
                                                    >
                                                        <Reply size={14} />
                                                        Reply
                                                    </button>
                                                    <button 
                                                        className="delete-btn"
                                                        onClick={() => setDeleteConfirm({ 
                                                            noteId: note.id, 
                                                            preview: note.content.substring(0, 50) + (note.content.length > 50 ? '...' : '')
                                                        })}
                                                    >
                                                        <Trash2 size={14} />
                                                    </button>
                                                </div>

                                                {/* Replies Section */}
                                                {expandedReplies[note.id] && note.replies && note.replies.length > 0 && (
                                                    <div className="replies-list">
                                                        {note.replies.map(reply => (
                                                            <div key={reply.id} className="reply-item">
                                                                <div className="reply-header">
                                                                    <span className="reply-author">{reply.creator_name || 'Unknown'}</span>
                                                                    <span className="reply-time">{formatDate(reply.created_at)}</span>
                                                                </div>
                                                                <p className="reply-content">{reply.content}</p>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}

                                                {/* Reply Input */}
                                                {replyingTo === note.id && (
                                                    <div className="reply-input-container">
                                                        <input
                                                            type="text"
                                                            className="reply-input"
                                                            placeholder="Write a reply..."
                                                            value={replyContent}
                                                            onChange={(e) => setReplyContent(e.target.value)}
                                                            onKeyDown={(e) => {
                                                                if (e.key === 'Enter' && !e.shiftKey) {
                                                                    e.preventDefault();
                                                                    handleReply(note.id);
                                                                }
                                                            }}
                                                            autoFocus
                                                        />
                                                        <button 
                                                            className="send-reply-btn"
                                                            onClick={() => handleReply(note.id)}
                                                            disabled={submittingReply || !replyContent.trim()}
                                                        >
                                                            {submittingReply ? <Loader size={14} className="spin" /> : <Send size={14} />}
                                                        </button>
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })
                                )}
                            </div>

                            {/* Add Note Section */}
                            {!showAddForm ? (
                                <button 
                                    className="add-note-trigger"
                                    onClick={() => setShowAddForm(true)}
                                >
                                    <Plus size={18} />
                                    Add Note
                                </button>
                            ) : (
                                <form className="add-note-form simplified" onSubmit={handleAddNote}>
                                    <textarea
                                        placeholder="Write your note..."
                                        value={newNote.content}
                                        onChange={(e) => setNewNote(prev => ({ 
                                            ...prev, 
                                            content: e.target.value 
                                        }))}
                                        required
                                        rows={2}
                                        autoFocus
                                    />
                                    <div className="form-actions">
                                        <button 
                                            type="button" 
                                            className="cancel-btn"
                                            onClick={() => setShowAddForm(false)}
                                        >
                                            Cancel
                                        </button>
                                        <button 
                                            type="submit" 
                                            className="submit-btn"
                                            disabled={submitting || !newNote.content.trim()}
                                        >
                                            {submitting ? (
                                                <Loader size={16} className="spin" />
                                            ) : (
                                                <Plus size={16} />
                                            )}
                                            {submitting ? 'Adding...' : 'Add Note'}
                                        </button>
                                    </div>
                                </form>
                            )}
                        </>
                    )}
                </div>
            </div>

            {/* Delete Confirmation Modal */}
            {deleteConfirm && (
                <div className="confirm-overlay">
                    <div className="confirm-modal">
                        <div className="confirm-icon">
                            <Trash2 size={24} />
                        </div>
                        <h4>Delete Note?</h4>
                        <p className="confirm-preview">"{deleteConfirm.preview}"</p>
                        <p className="confirm-warning">This action cannot be undone.</p>
                        <div className="confirm-actions">
                            <button 
                                className="confirm-cancel"
                                onClick={() => setDeleteConfirm(null)}
                            >
                                Cancel
                            </button>
                            <button 
                                className="confirm-delete"
                                onClick={() => handleDeleteNote(deleteConfirm.noteId)}
                            >
                                <Trash2 size={14} />
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};

export default NoteDrawer;
