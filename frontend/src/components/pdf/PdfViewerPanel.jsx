import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Worker, Viewer, SpecialZoomLevel } from '@react-pdf-viewer/core';
import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout';
import { pageNavigationPlugin } from '@react-pdf-viewer/page-navigation';
import { 
    FileText, 
    X, 
    ZoomIn, 
    ZoomOut, 
    ChevronLeft, 
    ChevronRight,
    Maximize2,
    Minimize2,
    Loader,
    AlertCircle,
    RefreshCw,
    Link2
} from 'lucide-react';
import { getPdfUrl } from '../../services/apiService';

// Import styles
import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/default-layout/lib/styles/index.css';
import '@react-pdf-viewer/page-navigation/lib/styles/index.css';
import './PdfViewerPanel.css';

/**
 * PdfViewerPanel - Right-side panel for viewing the original PDF script
 * 
 * Features:
 * - Loads PDF from Supabase Storage via signed URL
 * - Syncs to current scene's page when scene changes
 * - Zoom controls
 * - Page navigation
 * - Resizable panel width
 * - Dark theme styling
 */
const PdfViewerPanel = ({ 
    scriptId, 
    isOpen, 
    onClose, 
    currentPage = 1,
    onPageChange
}) => {
    const [pdfUrl, setPdfUrl] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [currentZoom, setCurrentZoom] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [displayPage, setDisplayPage] = useState(currentPage);
    const [isExpanded, setIsExpanded] = useState(false);
    const viewerRef = useRef(null);
    const lastJumpedPage = useRef(null);
    const isJumpingToPage = useRef(false); // Track if we're doing a programmatic jump
    const jumpTimeoutRef = useRef(null);

    // Create page navigation plugin for programmatic page jumping
    const pageNavigationPluginInstance = pageNavigationPlugin();
    const { jumpToPage } = pageNavigationPluginInstance;

    // Create the default layout plugin with custom toolbar
    const defaultLayoutPluginInstance = defaultLayoutPlugin({
        sidebarTabs: () => [], // Hide sidebar tabs
        toolbarPlugin: {
            fullScreenPlugin: {
                onEnterFullScreen: () => {},
                onExitFullScreen: () => {},
            },
        },
        renderToolbar: (Toolbar) => (
            <Toolbar>
                {(slots) => {
                    const {
                        CurrentPageInput,
                        GoToNextPage,
                        GoToPreviousPage,
                        NumberOfPages,
                        ZoomIn: ZoomInBtn,
                        ZoomOut: ZoomOutBtn,
                        Zoom,
                    } = slots;
                    return (
                        <div className="pdf-custom-toolbar">
                            <div className="toolbar-left">
                                <GoToPreviousPage />
                                <CurrentPageInput />
                                <span className="page-separator">/</span>
                                <NumberOfPages />
                                <GoToNextPage />
                            </div>
                            <div className="toolbar-right">
                                <ZoomOutBtn />
                                <Zoom />
                                <ZoomInBtn />
                            </div>
                        </div>
                    );
                }}
            </Toolbar>
        ),
    });

    // Fetch PDF URL on mount
    useEffect(() => {
        if (!scriptId || !isOpen) return;

        const fetchPdfUrl = async () => {
            setLoading(true);
            setError(null);
            
            try {
                const data = await getPdfUrl(scriptId);
                setPdfUrl(data.pdf_url);
            } catch (err) {
                console.error('Failed to load PDF:', err);
                setError(err.message || 'Failed to load PDF');
            } finally {
                setLoading(false);
            }
        };

        fetchPdfUrl();
    }, [scriptId, isOpen]);

    // Jump to page when currentPage prop changes (from scene selection)
    useEffect(() => {
        // Only jump if:
        // 1. We have a valid page number
        // 2. PDF is loaded (totalPages > 0)
        // 3. Page is different from last jumped page (prevent loops)
        if (currentPage && totalPages > 0 && currentPage !== lastJumpedPage.current) {
            const targetPage = Math.min(Math.max(1, currentPage), totalPages);
            console.log(`[PDF] Jumping to page ${targetPage} (requested: ${currentPage})`);
            
            // Set flag to indicate programmatic jump - ignore page change events during this
            isJumpingToPage.current = true;
            
            // Clear any existing timeout
            if (jumpTimeoutRef.current) {
                clearTimeout(jumpTimeoutRef.current);
            }
            
            jumpToPage(targetPage - 1); // 0-indexed
            lastJumpedPage.current = targetPage;
            setDisplayPage(targetPage);
            
            // Reset flag after animation completes (500ms should be enough)
            jumpTimeoutRef.current = setTimeout(() => {
                isJumpingToPage.current = false;
            }, 500);
        }
    }, [currentPage, totalPages, jumpToPage]);
    
    // Cleanup timeout on unmount
    useEffect(() => {
        return () => {
            if (jumpTimeoutRef.current) {
                clearTimeout(jumpTimeoutRef.current);
            }
        };
    }, []);

    // Handle document load
    const handleDocumentLoad = (e) => {
        setTotalPages(e.doc.numPages);
    };

    // Handle page change - only notify parent if it's a user scroll, not a programmatic jump
    const handlePageChange = (e) => {
        const newPage = e.currentPage + 1; // Convert to 1-indexed
        setDisplayPage(newPage);
        
        // Only fire callback if this is a user scroll, not a programmatic jump
        if (onPageChange && !isJumpingToPage.current) {
            console.log(`[PDF] User scrolled to page ${newPage}`);
            onPageChange(newPage);
        }
    };

    // Retry loading PDF
    const handleRetry = () => {
        setPdfUrl(null);
        setError(null);
        setLoading(true);
        
        getPdfUrl(scriptId)
            .then(data => {
                setPdfUrl(data.pdf_url);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message || 'Failed to load PDF');
                setLoading(false);
            });
    };

    if (!isOpen) return null;

    return (
        <div className={`pdf-viewer-panel ${isExpanded ? 'expanded' : ''}`}>
            {/* Panel Header */}
            <div className="pdf-panel-header">
                <div className="header-title">
                    <FileText size={18} />
                    <span>Original Script</span>
                    <span className="sync-indicator" title="Synced with scene list">
                        <Link2 size={14} />
                    </span>
                </div>
                <div className="header-actions">
                    <button 
                        className="panel-btn"
                        onClick={() => setIsExpanded(!isExpanded)}
                        title={isExpanded ? 'Collapse' : 'Expand'}
                    >
                        {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                    </button>
                    <button 
                        className="panel-btn close-btn"
                        onClick={onClose}
                        title="Close PDF Panel"
                    >
                        <X size={18} />
                    </button>
                </div>
            </div>

            {/* PDF Content */}
            <div className="pdf-panel-content">
                {loading && (
                    <div className="pdf-loading">
                        <Loader size={32} className="spin" />
                        <p>Loading PDF...</p>
                    </div>
                )}

                {error && (
                    <div className="pdf-error">
                        <AlertCircle size={32} />
                        <p>{error}</p>
                        <button className="retry-btn" onClick={handleRetry}>
                            <RefreshCw size={16} />
                            Retry
                        </button>
                    </div>
                )}

                {pdfUrl && !loading && !error && (
                    <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
                        <div className="pdf-viewer-container" ref={viewerRef}>
                            <Viewer
                                fileUrl={pdfUrl}
                                plugins={[
                                    defaultLayoutPluginInstance,
                                    pageNavigationPluginInstance
                                ]}
                                defaultScale={SpecialZoomLevel.PageWidth}
                                onDocumentLoad={handleDocumentLoad}
                                onPageChange={handlePageChange}
                                theme="dark"
                            />
                        </div>
                    </Worker>
                )}
            </div>

            {/* Page Indicator */}
            {totalPages > 0 && (
                <div className="pdf-page-indicator">
                    Page {displayPage} of {totalPages}
                </div>
            )}
        </div>
    );
};

export default PdfViewerPanel;
