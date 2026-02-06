import React, { useState, useEffect } from 'react';
import { 
    Download, 
    Printer, 
    Loader, 
    X, 
    CheckSquare, 
    Square,
    Highlighter,
    AlertCircle
} from 'lucide-react';
import { getHighlightClasses, downloadHighlightedPdf, openHighlightedHtml } from '../../services/apiService';
import './HighlightedPdfModal.css';

/**
 * HighlightedPdfModal - Modal for generating highlighted script PDFs
 * 
 * Allows users to:
 * - See available extraction classes with counts
 * - Toggle individual classes on/off
 * - Download as PDF or open printable HTML
 */
const HighlightedPdfModal = ({ scriptId, isOpen, onClose }) => {
    const [classes, setClasses] = useState([]);
    const [totalExtractions, setTotalExtractions] = useState(0);
    const [selectedClasses, setSelectedClasses] = useState(new Set());
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(null); // 'pdf' | 'html' | null
    const [error, setError] = useState(null);

    // Fetch available classes when modal opens
    useEffect(() => {
        if (!isOpen || !scriptId) return;

        const fetchClasses = async () => {
            setLoading(true);
            setError(null);
            try {
                const data = await getHighlightClasses(scriptId);
                setClasses(data.classes || []);
                setTotalExtractions(data.total || 0);
                // Select all by default
                setSelectedClasses(new Set((data.classes || []).map(c => c.class)));
            } catch (err) {
                setError(err.response?.data?.error || 'Failed to load extraction data');
            } finally {
                setLoading(false);
            }
        };

        fetchClasses();
    }, [isOpen, scriptId]);

    const toggleClass = (cls) => {
        setSelectedClasses(prev => {
            const next = new Set(prev);
            if (next.has(cls)) {
                next.delete(cls);
            } else {
                next.add(cls);
            }
            return next;
        });
    };

    const selectAll = () => {
        setSelectedClasses(new Set(classes.map(c => c.class)));
    };

    const selectNone = () => {
        setSelectedClasses(new Set());
    };

    const handleDownloadPdf = async () => {
        if (selectedClasses.size === 0) return;

        setGenerating('pdf');
        setError(null);
        try {
            const filterClasses = selectedClasses.size === classes.length 
                ? null  // all selected = no filter
                : Array.from(selectedClasses);
            await downloadHighlightedPdf(scriptId, filterClasses);
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to generate PDF');
        } finally {
            setGenerating(null);
        }
    };

    const handlePrintHtml = async () => {
        if (selectedClasses.size === 0) return;

        setGenerating('html');
        setError(null);
        try {
            const filterClasses = selectedClasses.size === classes.length 
                ? null 
                : Array.from(selectedClasses);
            await openHighlightedHtml(scriptId, filterClasses);
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to generate HTML');
        } finally {
            setGenerating(null);
        }
    };

    if (!isOpen) return null;

    const selectedCount = classes.filter(c => selectedClasses.has(c.class))
        .reduce((sum, c) => sum + c.count, 0);

    return (
        <div className="hlpdf-overlay" onClick={onClose}>
            <div className="hlpdf-modal" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="hlpdf-header">
                    <div className="hlpdf-header-title">
                        <Highlighter size={20} />
                        <h2>Highlighted Script PDF</h2>
                    </div>
                    <button className="hlpdf-close" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                {/* Description */}
                <p className="hlpdf-desc">
                    Generate a PDF of the original script with color-coded highlights 
                    for each extraction type. Select which categories to include.
                </p>

                {/* Content */}
                <div className="hlpdf-body">
                    {loading && (
                        <div className="hlpdf-loading">
                            <Loader size={24} className="spin" />
                            <span>Loading extraction data...</span>
                        </div>
                    )}

                    {error && (
                        <div className="hlpdf-error">
                            <AlertCircle size={18} />
                            <span>{error}</span>
                        </div>
                    )}

                    {!loading && classes.length === 0 && !error && (
                        <div className="hlpdf-empty">
                            <p>No extractions found for this script.</p>
                            <p className="hlpdf-hint">Run LangExtract analysis first to generate extraction data.</p>
                        </div>
                    )}

                    {!loading && classes.length > 0 && (
                        <>
                            {/* Quick actions */}
                            <div className="hlpdf-quick-actions">
                                <button className="hlpdf-link-btn" onClick={selectAll}>Select All</button>
                                <span className="hlpdf-divider">|</span>
                                <button className="hlpdf-link-btn" onClick={selectNone}>Select None</button>
                                <span className="hlpdf-selection-count">
                                    {selectedClasses.size}/{classes.length} categories · {selectedCount} extractions
                                </span>
                            </div>

                            {/* Class list */}
                            <div className="hlpdf-class-list">
                                {classes.map(cls => (
                                    <button
                                        key={cls.class}
                                        className={`hlpdf-class-item ${selectedClasses.has(cls.class) ? 'selected' : ''}`}
                                        onClick={() => toggleClass(cls.class)}
                                    >
                                        <span className="hlpdf-class-check">
                                            {selectedClasses.has(cls.class) 
                                                ? <CheckSquare size={16} /> 
                                                : <Square size={16} />
                                            }
                                        </span>
                                        <span 
                                            className="hlpdf-class-swatch"
                                            style={{ backgroundColor: cls.color }}
                                        />
                                        <span className="hlpdf-class-label">{cls.label}</span>
                                        <span className="hlpdf-class-count">{cls.count}</span>
                                    </button>
                                ))}
                            </div>
                        </>
                    )}
                </div>

                {/* Footer actions */}
                {!loading && classes.length > 0 && (
                    <div className="hlpdf-footer">
                        <button 
                            className="hlpdf-btn secondary"
                            onClick={handlePrintHtml}
                            disabled={selectedClasses.size === 0 || generating !== null}
                        >
                            {generating === 'html' 
                                ? <><Loader size={16} className="spin" /> Generating...</>
                                : <><Printer size={16} /> Print Preview</>
                            }
                        </button>
                        <button 
                            className="hlpdf-btn primary"
                            onClick={handleDownloadPdf}
                            disabled={selectedClasses.size === 0 || generating !== null}
                        >
                            {generating === 'pdf' 
                                ? <><Loader size={16} className="spin" /> Generating PDF...</>
                                : <><Download size={16} /> Download PDF</>
                            }
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default HighlightedPdfModal;
