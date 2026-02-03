import React, { useState, useEffect } from 'react';
import { 
    X, 
    FileText, 
    Download, 
    Settings,
    ChevronDown,
    Info
} from 'lucide-react';
import './ExportOptionsModal.css';

const ExportOptionsModal = ({ isOpen, onClose, scriptId, onGenerate }) => {
    const [presets, setPresets] = useState([]);
    const [selectedPreset, setSelectedPreset] = useState('full_breakdown');
    const [customTitle, setCustomTitle] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (isOpen) {
            fetchPresets();
        }
    }, [isOpen]);

    const fetchPresets = async () => {
        try {
            const response = await fetch('/api/report-presets');
            const data = await response.json();
            if (data.success) {
                setPresets(data.presets);
            }
        } catch (err) {
            console.error('Failed to fetch presets:', err);
            setError('Failed to load report presets');
        }
    };

    const handleGenerate = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`/api/scripts/${scriptId}/reports/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    report_type: selectedPreset,
                    title: customTitle || undefined,
                    config: {
                        report_type: selectedPreset
                    }
                })
            });

            const data = await response.json();

            if (data.success) {
                onGenerate(data.report);
                onClose();
            } else {
                setError(data.error || 'Failed to generate report');
            }
        } catch (err) {
            console.error('Failed to generate report:', err);
            setError('Failed to generate report. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const getPresetInfo = () => {
        return presets.find(p => p.name === selectedPreset) || {};
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="export-modal" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className="modal-header">
                    <div className="header-content">
                        <FileText size={24} className="header-icon" />
                        <div>
                            <h2>Export Report</h2>
                            <p className="header-subtitle">Choose a report type and customize options</p>
                        </div>
                    </div>
                    <button className="close-btn" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                {/* Body */}
                <div className="modal-body">
                    {error && (
                        <div className="error-banner">
                            <Info size={16} />
                            <span>{error}</span>
                        </div>
                    )}

                    {/* Preset Selection */}
                    <div className="form-section">
                        <label className="form-label">
                            Report Type
                            <span className="required">*</span>
                        </label>
                        <div className="select-wrapper">
                            <select
                                value={selectedPreset}
                                onChange={(e) => setSelectedPreset(e.target.value)}
                                className="preset-select"
                            >
                                {presets.map((preset) => (
                                    <option key={preset.name} value={preset.name}>
                                        {preset.title}
                                    </option>
                                ))}
                            </select>
                            <ChevronDown size={16} className="select-icon" />
                        </div>
                        {getPresetInfo().description && (
                            <p className="preset-description">
                                {getPresetInfo().description}
                            </p>
                        )}
                    </div>

                    {/* Custom Title */}
                    <div className="form-section">
                        <label className="form-label">
                            Custom Title
                            <span className="optional">(optional)</span>
                        </label>
                        <input
                            type="text"
                            value={customTitle}
                            onChange={(e) => setCustomTitle(e.target.value)}
                            placeholder="Leave blank for default title"
                            className="title-input"
                        />
                    </div>

                    {/* Info Box */}
                    <div className="info-box">
                        <Settings size={16} />
                        <div className="info-content">
                            <strong>What's included:</strong>
                            <ul>
                                {selectedPreset === 'full_breakdown' && (
                                    <>
                                        <li>All breakdown categories</li>
                                        <li>Complete scene details</li>
                                        <li>Summary statistics</li>
                                    </>
                                )}
                                {selectedPreset === 'wardrobe' && (
                                    <>
                                        <li>Wardrobe items by character</li>
                                        <li>Scene cross-references</li>
                                        <li>Continuity notes</li>
                                    </>
                                )}
                                {selectedPreset === 'props' && (
                                    <>
                                        <li>Props list with frequency</li>
                                        <li>Scene appearances</li>
                                        <li>Character associations</li>
                                    </>
                                )}
                                {selectedPreset === 'makeup' && (
                                    <>
                                        <li>Makeup requirements by character</li>
                                        <li>Scene cross-references</li>
                                        <li>Emotional tone context</li>
                                    </>
                                )}
                                {selectedPreset === 'sfx' && (
                                    <>
                                        <li>Special effects breakdown</li>
                                        <li>Technical requirements</li>
                                        <li>Scene references</li>
                                    </>
                                )}
                                {selectedPreset === 'stunts' && (
                                    <>
                                        <li>Stunt requirements</li>
                                        <li>Action descriptions</li>
                                        <li>Safety considerations</li>
                                    </>
                                )}
                                {selectedPreset === 'vehicles' && (
                                    <>
                                        <li>Vehicle requirements</li>
                                        <li>Scene appearances</li>
                                        <li>Usage frequency</li>
                                    </>
                                )}
                                {selectedPreset === 'animals' && (
                                    <>
                                        <li>Animal requirements</li>
                                        <li>Scene appearances</li>
                                        <li>Handler needs</li>
                                    </>
                                )}
                                {selectedPreset === 'extras' && (
                                    <>
                                        <li>Background actor needs</li>
                                        <li>Crowd sizes</li>
                                        <li>Location context</li>
                                    </>
                                )}
                            </ul>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="modal-footer">
                    <button 
                        className="btn-secondary" 
                        onClick={onClose}
                        disabled={loading}
                    >
                        Cancel
                    </button>
                    <button 
                        className="btn-primary" 
                        onClick={handleGenerate}
                        disabled={loading}
                    >
                        {loading ? (
                            <>
                                <span className="spinner"></span>
                                Generating...
                            </>
                        ) : (
                            <>
                                <Download size={16} />
                                Generate Report
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ExportOptionsModal;
