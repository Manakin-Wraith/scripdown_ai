import React, { useState } from 'react';
import { Lock, Unlock, X, AlertTriangle, Loader, CheckCircle } from 'lucide-react';
import { lockScript, unlockScript } from '../../services/apiService';
import { useToast } from '../../context/ToastContext';
import './LockScriptModal.css';

/**
 * LockScriptModal - Modal for locking/unlocking a script
 * 
 * Locking a script:
 * - Freezes scene numbers for production
 * - Prevents reordering, splitting, merging, adding scenes
 * - Enables shooting script export
 */
const LockScriptModal = ({ isOpen, onClose, script, onSuccess }) => {
    const toast = useToast();
    const [loading, setLoading] = useState(false);
    const [revisionColor, setRevisionColor] = useState('WHITE');
    
    if (!isOpen || !script) return null;
    
    const isLocked = script.is_locked;
    
    // Industry standard revision colors
    const revisionColors = [
        { value: 'WHITE', label: 'White', color: '#ffffff' },
        { value: 'BLUE', label: 'Blue', color: '#93c5fd' },
        { value: 'PINK', label: 'Pink', color: '#f9a8d4' },
        { value: 'YELLOW', label: 'Yellow', color: '#fde047' },
        { value: 'GREEN', label: 'Green', color: '#86efac' },
        { value: 'GOLDENROD', label: 'Goldenrod', color: '#fbbf24' },
        { value: 'BUFF', label: 'Buff', color: '#fcd34d' },
        { value: 'SALMON', label: 'Salmon', color: '#fca5a5' },
        { value: 'CHERRY', label: 'Cherry', color: '#f87171' },
        { value: 'TAN', label: 'Tan', color: '#d4a574' }
    ];
    
    const handleLock = async () => {
        try {
            setLoading(true);
            await lockScript(script.id, revisionColor);
            toast.success('Script Locked', 'Scene numbers are now frozen for production');
            onSuccess?.();
            onClose();
        } catch (error) {
            console.error('Error locking script:', error);
            toast.error('Error', error.response?.data?.error || 'Failed to lock script');
        } finally {
            setLoading(false);
        }
    };
    
    const handleUnlock = async () => {
        try {
            setLoading(true);
            await unlockScript(script.id);
            toast.success('Script Unlocked', 'Script is now a working draft again');
            onSuccess?.();
            onClose();
        } catch (error) {
            console.error('Error unlocking script:', error);
            toast.error('Error', error.response?.data?.error || 'Failed to unlock script');
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="lock-modal" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="modal-header">
                    <div className="modal-title">
                        {isLocked ? <Unlock size={20} /> : <Lock size={20} />}
                        <h2>{isLocked ? 'Unlock Script' : 'Lock Script'}</h2>
                    </div>
                    <button className="modal-close" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>
                
                {/* Content */}
                <div className="modal-content">
                    {isLocked ? (
                        // Unlock Mode
                        <>
                            <div className="warning-banner">
                                <AlertTriangle size={20} />
                                <div>
                                    <strong>Warning: Unlocking Script</strong>
                                    <p>
                                        This will revert the script to a working draft. 
                                        Scene numbers will no longer be locked.
                                    </p>
                                </div>
                            </div>
                            
                            <div className="current-status">
                                <div className="status-item">
                                    <span className="label">Current Status:</span>
                                    <span className="value locked">
                                        <Lock size={14} /> Locked
                                    </span>
                                </div>
                                <div className="status-item">
                                    <span className="label">Revision Color:</span>
                                    <span 
                                        className="color-badge"
                                        style={{ 
                                            backgroundColor: revisionColors.find(
                                                c => c.value === script.current_revision_color
                                            )?.color || '#fff'
                                        }}
                                    >
                                        {script.current_revision_color || 'WHITE'}
                                    </span>
                                </div>
                                {script.locked_at && (
                                    <div className="status-item">
                                        <span className="label">Locked At:</span>
                                        <span className="value">
                                            {new Date(script.locked_at).toLocaleDateString()}
                                        </span>
                                    </div>
                                )}
                            </div>
                        </>
                    ) : (
                        // Lock Mode
                        <>
                            <div className="info-section">
                                <h3>What happens when you lock a script?</h3>
                                <ul className="lock-effects">
                                    <li>
                                        <CheckCircle size={16} className="check" />
                                        Scene numbers become permanent
                                    </li>
                                    <li>
                                        <CheckCircle size={16} className="check" />
                                        No more reordering, splitting, or merging
                                    </li>
                                    <li>
                                        <CheckCircle size={16} className="check" />
                                        Ready for shooting script export
                                    </li>
                                    <li>
                                        <CheckCircle size={16} className="check" />
                                        Revision tracking enabled
                                    </li>
                                </ul>
                            </div>
                            
                            <div className="color-selector">
                                <label>Revision Color</label>
                                <p className="color-hint">
                                    First draft is typically WHITE. Future revisions use different colors.
                                </p>
                                <div className="color-grid">
                                    {revisionColors.map(color => (
                                        <button
                                            key={color.value}
                                            className={`color-option ${revisionColor === color.value ? 'selected' : ''}`}
                                            style={{ backgroundColor: color.color }}
                                            onClick={() => setRevisionColor(color.value)}
                                            title={color.label}
                                        >
                                            {revisionColor === color.value && (
                                                <CheckCircle size={16} />
                                            )}
                                        </button>
                                    ))}
                                </div>
                                <span className="selected-color">{revisionColor}</span>
                            </div>
                        </>
                    )}
                </div>
                
                {/* Footer */}
                <div className="modal-footer">
                    <button className="btn-cancel" onClick={onClose} disabled={loading}>
                        Cancel
                    </button>
                    {isLocked ? (
                        <button 
                            className="btn-unlock" 
                            onClick={handleUnlock} 
                            disabled={loading}
                        >
                            {loading ? (
                                <>
                                    <Loader size={16} className="spin" />
                                    Unlocking...
                                </>
                            ) : (
                                <>
                                    <Unlock size={16} />
                                    Unlock Script
                                </>
                            )}
                        </button>
                    ) : (
                        <button 
                            className="btn-lock" 
                            onClick={handleLock} 
                            disabled={loading}
                        >
                            {loading ? (
                                <>
                                    <Loader size={16} className="spin" />
                                    Locking...
                                </>
                            ) : (
                                <>
                                    <Lock size={16} />
                                    Lock Script
                                </>
                            )}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default LockScriptModal;
