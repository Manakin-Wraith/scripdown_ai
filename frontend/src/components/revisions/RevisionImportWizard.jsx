import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { 
    X, Upload, FileText, AlertCircle, CheckCircle, 
    Plus, Minus, RefreshCw, ArrowRight, Loader2 
} from 'lucide-react';
import { importRevision } from '../../services/apiService';
import './RevisionImportWizard.css';

const REVISION_COLORS = [
    { name: 'White', value: 'white', hex: '#FFFFFF' },
    { name: 'Blue', value: 'blue', hex: '#ADD8E6' },
    { name: 'Pink', value: 'pink', hex: '#FFB6C1' },
    { name: 'Yellow', value: 'yellow', hex: '#FFFF99' },
    { name: 'Green', value: 'green', hex: '#90EE90' },
    { name: 'Goldenrod', value: 'goldenrod', hex: '#DAA520' },
    { name: 'Buff', value: 'buff', hex: '#F0DC82' },
    { name: 'Salmon', value: 'salmon', hex: '#FA8072' },
    { name: 'Cherry', value: 'cherry', hex: '#DE3163' },
    { name: 'Tan', value: 'tan', hex: '#D2B48C' }
];

const RevisionImportWizard = ({ isOpen, onClose, scriptId, scriptTitle, onImportComplete }) => {
    const [step, setStep] = useState(1);
    const [file, setFile] = useState(null);
    const [revisionColor, setRevisionColor] = useState('blue');
    const [notes, setNotes] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [previewData, setPreviewData] = useState(null);
    const [importResult, setImportResult] = useState(null);

    const onDrop = useCallback((acceptedFiles) => {
        if (acceptedFiles.length > 0) {
            const selectedFile = acceptedFiles[0];
            if (selectedFile.type === 'application/pdf') {
                setFile(selectedFile);
                setError(null);
            } else {
                setError('Please upload a PDF file');
            }
        }
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'application/pdf': ['.pdf'] },
        multiple: false
    });

    const handlePreview = async () => {
        if (!file) {
            setError('Please select a PDF file');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const result = await importRevision(scriptId, file, revisionColor, notes, false);
            setPreviewData(result);
            setStep(2);
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to analyze revision');
        } finally {
            setLoading(false);
        }
    };

    const handleImport = async () => {
        setLoading(true);
        setError(null);

        try {
            const result = await importRevision(scriptId, file, revisionColor, notes, true);
            setImportResult(result);
            setStep(3);
            if (onImportComplete) {
                onImportComplete(result);
            }
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to import revision');
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        setStep(1);
        setFile(null);
        setRevisionColor('blue');
        setNotes('');
        setError(null);
        setPreviewData(null);
        setImportResult(null);
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={handleClose}>
            <div className="revision-wizard" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className="wizard-header">
                    <div className="wizard-title">
                        <Upload size={24} />
                        <h2>Import Revision</h2>
                    </div>
                    <button className="close-btn" onClick={handleClose}>
                        <X size={20} />
                    </button>
                </div>

                {/* Progress Steps */}
                <div className="wizard-steps">
                    <div className={`step ${step >= 1 ? 'active' : ''} ${step > 1 ? 'completed' : ''}`}>
                        <span className="step-number">1</span>
                        <span className="step-label">Upload</span>
                    </div>
                    <div className="step-connector" />
                    <div className={`step ${step >= 2 ? 'active' : ''} ${step > 2 ? 'completed' : ''}`}>
                        <span className="step-number">2</span>
                        <span className="step-label">Review</span>
                    </div>
                    <div className="step-connector" />
                    <div className={`step ${step >= 3 ? 'active' : ''}`}>
                        <span className="step-number">3</span>
                        <span className="step-label">Complete</span>
                    </div>
                </div>

                {/* Content */}
                <div className="wizard-content">
                    {error && (
                        <div className="error-banner">
                            <AlertCircle size={18} />
                            <span>{error}</span>
                        </div>
                    )}

                    {/* Step 1: Upload */}
                    {step === 1 && (
                        <div className="step-content">
                            <p className="step-description">
                                Upload a new revision of <strong>{scriptTitle}</strong>. 
                                The system will compare it with the current version and show you what changed.
                            </p>

                            {/* Dropzone */}
                            <div 
                                {...getRootProps()} 
                                className={`dropzone ${isDragActive ? 'active' : ''} ${file ? 'has-file' : ''}`}
                            >
                                <input {...getInputProps()} />
                                {file ? (
                                    <div className="file-preview">
                                        <FileText size={40} />
                                        <div className="file-info">
                                            <span className="file-name">{file.name}</span>
                                            <span className="file-size">
                                                {(file.size / 1024 / 1024).toFixed(2)} MB
                                            </span>
                                        </div>
                                        <button 
                                            className="remove-file"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setFile(null);
                                            }}
                                        >
                                            <X size={16} />
                                        </button>
                                    </div>
                                ) : (
                                    <div className="dropzone-content">
                                        <Upload size={40} />
                                        <p>Drag & drop your revised PDF here</p>
                                        <span>or click to browse</span>
                                    </div>
                                )}
                            </div>

                            {/* Revision Color */}
                            <div className="form-group">
                                <label>Revision Color</label>
                                <p className="form-hint">
                                    Select the color for this revision. Industry standard follows: 
                                    White → Blue → Pink → Yellow → Green...
                                </p>
                                <div className="color-picker">
                                    {REVISION_COLORS.map((color) => (
                                        <button
                                            key={color.value}
                                            className={`color-btn ${revisionColor === color.value ? 'selected' : ''}`}
                                            style={{ backgroundColor: color.hex }}
                                            onClick={() => setRevisionColor(color.value)}
                                            title={color.name}
                                        >
                                            {revisionColor === color.value && <CheckCircle size={16} />}
                                        </button>
                                    ))}
                                </div>
                                <span className="selected-color">
                                    {REVISION_COLORS.find(c => c.value === revisionColor)?.name}
                                </span>
                            </div>

                            {/* Notes */}
                            <div className="form-group">
                                <label>Revision Notes (Optional)</label>
                                <textarea
                                    value={notes}
                                    onChange={(e) => setNotes(e.target.value)}
                                    placeholder="e.g., 'Added new scene 12A, revised dialogue in scene 5'"
                                    rows={3}
                                />
                            </div>
                        </div>
                    )}

                    {/* Step 2: Review Changes */}
                    {step === 2 && previewData && (
                        <div className="step-content">
                            <p className="step-description">
                                Review the changes detected in this revision before applying them.
                            </p>

                            {/* Summary Stats */}
                            <div className="diff-summary">
                                <div className="stat added">
                                    <Plus size={20} />
                                    <span className="stat-value">{previewData.diff_summary?.added || 0}</span>
                                    <span className="stat-label">Added</span>
                                </div>
                                <div className="stat modified">
                                    <RefreshCw size={20} />
                                    <span className="stat-value">{previewData.diff_summary?.modified || 0}</span>
                                    <span className="stat-label">Modified</span>
                                </div>
                                <div className="stat removed">
                                    <Minus size={20} />
                                    <span className="stat-value">{previewData.diff_summary?.removed || 0}</span>
                                    <span className="stat-label">Removed</span>
                                </div>
                                <div className="stat unchanged">
                                    <CheckCircle size={20} />
                                    <span className="stat-value">{previewData.diff_summary?.unchanged || 0}</span>
                                    <span className="stat-label">Unchanged</span>
                                </div>
                            </div>

                            {/* Diff List */}
                            <div className="diff-list">
                                {previewData.diffs?.filter(d => d.change_type !== 'unchanged').map((diff, index) => (
                                    <div key={index} className={`diff-item ${diff.change_type}`}>
                                        <div className="diff-badge">
                                            {diff.change_type === 'added' && <Plus size={14} />}
                                            {diff.change_type === 'modified' && <RefreshCw size={14} />}
                                            {diff.change_type === 'removed' && <Minus size={14} />}
                                            <span>{diff.change_type}</span>
                                        </div>
                                        <div className="diff-scene">
                                            <span className="scene-number">Scene {diff.scene_number}</span>
                                            <span className="scene-setting">
                                                {diff.new_scene?.setting || diff.old_scene?.setting}
                                            </span>
                                        </div>
                                        {diff.changes?.length > 0 && (
                                            <ul className="diff-changes">
                                                {diff.changes.map((change, i) => (
                                                    <li key={i}>{change}</li>
                                                ))}
                                            </ul>
                                        )}
                                    </div>
                                ))}
                                
                                {previewData.diffs?.filter(d => d.change_type !== 'unchanged').length === 0 && (
                                    <div className="no-changes">
                                        <CheckCircle size={40} />
                                        <p>No changes detected between versions</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Step 3: Complete */}
                    {step === 3 && importResult && (
                        <div className="step-content complete">
                            <div className="success-icon">
                                <CheckCircle size={60} />
                            </div>
                            <h3>Revision Imported Successfully!</h3>
                            <p>{importResult.message}</p>
                            
                            <div className="import-stats">
                                <div className="stat">
                                    <span className="stat-value">{importResult.applied_stats?.added || 0}</span>
                                    <span className="stat-label">Scenes Added</span>
                                </div>
                                <div className="stat">
                                    <span className="stat-value">{importResult.applied_stats?.modified || 0}</span>
                                    <span className="stat-label">Scenes Modified</span>
                                </div>
                                <div className="stat">
                                    <span className="stat-value">{importResult.applied_stats?.removed || 0}</span>
                                    <span className="stat-label">Scenes Removed</span>
                                </div>
                            </div>

                            {importResult.version && (
                                <div className="version-info">
                                    <span>Version {importResult.version.version_number}</span>
                                    <span className="revision-badge" style={{ 
                                        backgroundColor: REVISION_COLORS.find(c => c.value === importResult.version.revision_color)?.hex 
                                    }}>
                                        {importResult.version.revision_color?.toUpperCase()}
                                    </span>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="wizard-footer">
                    {step === 1 && (
                        <>
                            <button className="btn-secondary" onClick={handleClose}>
                                Cancel
                            </button>
                            <button 
                                className="btn-primary" 
                                onClick={handlePreview}
                                disabled={!file || loading}
                            >
                                {loading ? (
                                    <>
                                        <Loader2 size={18} className="spin" />
                                        Analyzing...
                                    </>
                                ) : (
                                    <>
                                        Preview Changes
                                        <ArrowRight size={18} />
                                    </>
                                )}
                            </button>
                        </>
                    )}

                    {step === 2 && (
                        <>
                            <button className="btn-secondary" onClick={() => setStep(1)}>
                                Back
                            </button>
                            <button 
                                className="btn-primary" 
                                onClick={handleImport}
                                disabled={loading}
                            >
                                {loading ? (
                                    <>
                                        <Loader2 size={18} className="spin" />
                                        Importing...
                                    </>
                                ) : (
                                    <>
                                        Apply Changes
                                        <CheckCircle size={18} />
                                    </>
                                )}
                            </button>
                        </>
                    )}

                    {step === 3 && (
                        <button className="btn-primary" onClick={handleClose}>
                            Done
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default RevisionImportWizard;
