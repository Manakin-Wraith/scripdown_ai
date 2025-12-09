import React, { useState, useEffect } from 'react';
import { 
    MessageSquare, 
    Plus, 
    ChevronDown, 
    ChevronRight,
    Trash2,
    Edit3,
    Clock,
    AlertCircle,
    CheckCircle,
    Loader,
    X,
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
import { getSceneNotes, getDepartments, createNote, deleteNote, updateNote } from '../../services/apiService';
import './DepartmentNotesSection.css';

// Icon mapping for departments
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

const DepartmentNotesSection = ({ sceneId, scriptId }) => {
    const [notes, setNotes] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedDepts, setExpandedDepts] = useState({});
    const [showAddNote, setShowAddNote] = useState(false);
    const [newNote, setNewNote] = useState({
        department_code: '',
        content: '',
        title: '',
        priority: 'normal'
    });
    const [submitting, setSubmitting] = useState(false);

    // Fetch departments and notes
    useEffect(() => {
        const fetchData = async () => {
            if (!sceneId) return;
            
            setLoading(true);
            setError(null);
            
            try {
                const [deptResponse, notesResponse] = await Promise.all([
                    getDepartments(),
                    getSceneNotes(sceneId)
                ]);
                
                setDepartments(deptResponse.departments || []);
                setNotes(notesResponse.departments || []);
                
                // Auto-expand departments with notes
                const expanded = {};
                (notesResponse.departments || []).forEach(dept => {
                    if (dept.notes && dept.notes.length > 0) {
                        expanded[dept.department_code] = true;
                    }
                });
                setExpandedDepts(expanded);
                
            } catch (err) {
                console.error('Error fetching notes:', err);
                setError('Failed to load notes');
            } finally {
                setLoading(false);
            }
        };
        
        fetchData();
    }, [sceneId]);

    const toggleDepartment = (deptCode) => {
        setExpandedDepts(prev => ({
            ...prev,
            [deptCode]: !prev[deptCode]
        }));
    };

    const handleAddNote = async (e) => {
        e.preventDefault();
        if (!newNote.department_code || !newNote.content.trim()) return;
        
        setSubmitting(true);
        try {
            const created = await createNote(scriptId, {
                ...newNote,
                scene_id: sceneId
            });
            
            // Refresh notes
            const notesResponse = await getSceneNotes(sceneId);
            setNotes(notesResponse.departments || []);
            
            // Reset form
            setNewNote({ department_code: '', content: '', title: '', priority: 'normal' });
            setShowAddNote(false);
            
            // Expand the department we just added to
            setExpandedDepts(prev => ({
                ...prev,
                [created.department_code]: true
            }));
            
        } catch (err) {
            console.error('Error creating note:', err);
            setError('Failed to create note');
        } finally {
            setSubmitting(false);
        }
    };

    const handleDeleteNote = async (noteId) => {
        if (!window.confirm('Delete this note?')) return;
        
        try {
            await deleteNote(noteId);
            // Refresh notes
            const notesResponse = await getSceneNotes(sceneId);
            setNotes(notesResponse.departments || []);
        } catch (err) {
            console.error('Error deleting note:', err);
            setError('Failed to delete note');
        }
    };

    const getDepartmentIcon = (iconName) => {
        const IconComponent = DEPARTMENT_ICONS[iconName] || MessageSquare;
        return IconComponent;
    };

    const getPriorityBadge = (priority) => {
        const styles = {
            low: { bg: '#E0E7FF', color: '#4338CA' },
            normal: { bg: '#E5E7EB', color: '#374151' },
            high: { bg: '#FEF3C7', color: '#D97706' },
            urgent: { bg: '#FEE2E2', color: '#DC2626' }
        };
        return styles[priority] || styles.normal;
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

    const totalNotes = notes.reduce((sum, dept) => sum + (dept.notes?.length || 0), 0);

    if (loading) {
        return (
            <div className="notes-section loading">
                <Loader size={20} className="spin" />
                <span>Loading notes...</span>
            </div>
        );
    }

    return (
        <div className="department-notes-section">
            {/* Header */}
            <div className="notes-header">
                <div className="notes-title">
                    <MessageSquare size={18} />
                    <span>Department Notes</span>
                    {totalNotes > 0 && (
                        <span className="notes-count">{totalNotes}</span>
                    )}
                </div>
                <button 
                    className="add-note-btn"
                    onClick={() => setShowAddNote(!showAddNote)}
                >
                    {showAddNote ? <X size={16} /> : <Plus size={16} />}
                    {showAddNote ? 'Cancel' : 'Add Note'}
                </button>
            </div>

            {/* Error */}
            {error && (
                <div className="notes-error">
                    <AlertCircle size={16} />
                    <span>{error}</span>
                </div>
            )}

            {/* Add Note Form */}
            {showAddNote && (
                <form className="add-note-form" onSubmit={handleAddNote}>
                    <div className="form-row">
                        <select
                            value={newNote.department_code}
                            onChange={(e) => setNewNote(prev => ({ ...prev, department_code: e.target.value }))}
                            required
                        >
                            <option value="">Select Department</option>
                            {departments.map(dept => (
                                <option key={dept.code} value={dept.code}>
                                    {dept.name}
                                </option>
                            ))}
                        </select>
                        <select
                            value={newNote.priority}
                            onChange={(e) => setNewNote(prev => ({ ...prev, priority: e.target.value }))}
                        >
                            <option value="low">Low</option>
                            <option value="normal">Normal</option>
                            <option value="high">High</option>
                            <option value="urgent">Urgent</option>
                        </select>
                    </div>
                    <input
                        type="text"
                        placeholder="Note title (optional)"
                        value={newNote.title}
                        onChange={(e) => setNewNote(prev => ({ ...prev, title: e.target.value }))}
                    />
                    <textarea
                        placeholder="Write your note..."
                        value={newNote.content}
                        onChange={(e) => setNewNote(prev => ({ ...prev, content: e.target.value }))}
                        required
                        rows={3}
                    />
                    <button type="submit" disabled={submitting}>
                        {submitting ? <Loader size={16} className="spin" /> : <Plus size={16} />}
                        {submitting ? 'Adding...' : 'Add Note'}
                    </button>
                </form>
            )}

            {/* Notes by Department */}
            <div className="notes-list">
                {notes.length === 0 ? (
                    <div className="no-notes">
                        <MessageSquare size={24} />
                        <p>No notes yet</p>
                        <span>Add a note to start collaborating</span>
                    </div>
                ) : (
                    notes.map(dept => {
                        const IconComponent = getDepartmentIcon(dept.department_icon);
                        const isExpanded = expandedDepts[dept.department_code];
                        
                        return (
                            <div key={dept.department_code} className="department-group">
                                <button 
                                    className="department-header"
                                    onClick={() => toggleDepartment(dept.department_code)}
                                    style={{ '--dept-color': dept.department_color }}
                                >
                                    <div className="dept-info">
                                        <span 
                                            className="dept-icon"
                                            style={{ backgroundColor: `${dept.department_color}20`, color: dept.department_color }}
                                        >
                                            <IconComponent size={14} />
                                        </span>
                                        <span className="dept-name">{dept.department_name}</span>
                                        <span className="dept-count">{dept.notes?.length || 0}</span>
                                    </div>
                                    {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                </button>
                                
                                {isExpanded && (
                                    <div className="department-notes">
                                        {dept.notes?.map(note => {
                                            const priorityStyle = getPriorityBadge(note.priority);
                                            
                                            return (
                                                <div key={note.id} className="note-card">
                                                    <div className="note-header">
                                                        {note.title && <h4>{note.title}</h4>}
                                                        <div className="note-meta">
                                                            {note.priority !== 'normal' && (
                                                                <span 
                                                                    className="priority-badge"
                                                                    style={{ 
                                                                        backgroundColor: priorityStyle.bg, 
                                                                        color: priorityStyle.color 
                                                                    }}
                                                                >
                                                                    {note.priority}
                                                                </span>
                                                            )}
                                                            <span className="note-date">
                                                                <Clock size={12} />
                                                                {formatDate(note.created_at)}
                                                            </span>
                                                        </div>
                                                    </div>
                                                    <p className="note-content">{note.content}</p>
                                                    <div className="note-actions">
                                                        <button 
                                                            className="action-btn delete"
                                                            onClick={() => handleDeleteNote(note.id)}
                                                            title="Delete note"
                                                        >
                                                            <Trash2 size={14} />
                                                        </button>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
};

export default DepartmentNotesSection;
