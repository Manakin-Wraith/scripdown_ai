import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
    FileText, Download, Share2, Printer, ChevronRight, 
    Users, MapPin, Package, Shirt, Film, List, BookOpen,
    Loader, Check, AlertCircle, Clock, Trash2, ExternalLink
} from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { useScript } from '../../context/ScriptContext';
import { 
    getReportTypes, 
    generateReport, 
    previewReport,
    getScriptReports,
    deleteReport,
    getReportPdfUrl,
    getReportPrintUrl,
    getScriptMetadata
} from '../../services/apiService';
import ShareModal from './ShareModal';
import './ReportBuilder.css';

const REPORT_ICONS = {
    scene_breakdown: Film,
    day_out_of_days: Users,
    location: MapPin,
    props: Package,
    wardrobe: Shirt,
    one_liner: List,
    full_breakdown: BookOpen
};

const ReportBuilder = () => {
    const { scriptId } = useParams();
    const navigate = useNavigate();
    const toast = useToast();
    const { setScript } = useScript();
    
    const [reportTypes, setReportTypes] = useState({});
    const [selectedType, setSelectedType] = useState('scene_breakdown');
    const [customTitle, setCustomTitle] = useState('');
    const [scriptMetadata, setScriptMetadata] = useState(null);
    const [previewData, setPreviewData] = useState(null);
    const [existingReports, setExistingReports] = useState([]);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isLoadingPreview, setIsLoadingPreview] = useState(false);
    const [shareModalReport, setShareModalReport] = useState(null);
    const [loading, setLoading] = useState(true);

    // Fetch initial data
    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                
                // Fetch report types
                const typesRes = await getReportTypes();
                if (typesRes.success) {
                    setReportTypes(typesRes.report_types);
                }
                
                // Fetch script metadata
                try {
                    const metadata = await getScriptMetadata(scriptId);
                    setScriptMetadata(metadata);
                    // Update script context for breadcrumbs
                    setScript({
                        id: scriptId,
                        title: metadata?.title || metadata?.script_name
                    });
                } catch (e) {
                    console.warn('Could not fetch metadata:', e);
                }
                
                // Fetch existing reports
                const reportsRes = await getScriptReports(scriptId);
                if (reportsRes.success) {
                    setExistingReports(reportsRes.reports);
                }
            } catch (error) {
                toast.error('Error', 'Failed to load report data');
            } finally {
                setLoading(false);
            }
        };
        
        fetchData();
    }, [scriptId]);

    // Load preview when type changes
    useEffect(() => {
        const loadPreview = async () => {
            if (!selectedType) return;
            
            setIsLoadingPreview(true);
            try {
                const res = await previewReport(scriptId, selectedType);
                if (res.success) {
                    setPreviewData(res.data);
                }
            } catch (error) {
                console.error('Preview error:', error);
            } finally {
                setIsLoadingPreview(false);
            }
        };
        
        loadPreview();
    }, [scriptId, selectedType]);

    const handleGenerate = async () => {
        setIsGenerating(true);
        try {
            const title = customTitle || null;
            const res = await generateReport(scriptId, selectedType, title);
            
            if (res.success) {
                toast.success('Report Generated', 'Your report is ready!');
                setExistingReports(prev => [res.report, ...prev]);
                setCustomTitle('');
            } else {
                toast.error('Error', res.error || 'Failed to generate report');
            }
        } catch (error) {
            toast.error('Error', error.message || 'Failed to generate report');
        } finally {
            setIsGenerating(false);
        }
    };

    const handleDelete = async (reportId) => {
        if (!window.confirm('Delete this report?')) return;
        
        try {
            await deleteReport(reportId);
            setExistingReports(prev => prev.filter(r => r.id !== reportId));
            toast.success('Deleted', 'Report deleted');
        } catch (error) {
            toast.error('Error', 'Failed to delete report');
        }
    };

    const handlePrint = (reportId) => {
        window.open(getReportPrintUrl(reportId), '_blank');
    };

    const handleDownload = (reportId) => {
        window.open(getReportPdfUrl(reportId), '_blank');
    };

    if (loading) {
        return (
            <div className="report-builder-loading">
                <Loader className="spin" size={32} />
                <p>Loading report builder...</p>
            </div>
        );
    }

    return (
        <div className="report-builder">
            {/* Header */}
            <div className="report-builder-header">
                <h1>
                    <FileText size={24} />
                    Generate Reports
                </h1>
            </div>

            <div className="report-builder-content">
                {/* Report Type Selection */}
                <div className="report-type-section">
                    <h2>Select Report Type</h2>
                    <div className="report-type-grid">
                        {Object.entries(reportTypes).map(([type, info]) => {
                            const Icon = REPORT_ICONS[type] || FileText;
                            const isSelected = selectedType === type;
                            
                            return (
                                <button
                                    key={type}
                                    className={`report-type-card ${isSelected ? 'selected' : ''}`}
                                    onClick={() => setSelectedType(type)}
                                >
                                    <Icon size={24} />
                                    <span className="type-name">{info.name}</span>
                                    <span className="type-desc">{info.description}</span>
                                    {isSelected && <Check size={16} className="check-icon" />}
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Configuration */}
                <div className="report-config-section">
                    <h2>Report Options</h2>
                    <div className="config-form">
                        <div className="form-group">
                            <label htmlFor="customTitle">Custom Title (optional)</label>
                            <input
                                type="text"
                                id="customTitle"
                                value={customTitle}
                                onChange={(e) => setCustomTitle(e.target.value)}
                                placeholder={`${scriptMetadata?.title || 'Script'} - ${reportTypes[selectedType]?.name || 'Report'}`}
                            />
                        </div>
                    </div>
                    
                    <button 
                        className="btn-primary generate-btn"
                        onClick={handleGenerate}
                        disabled={isGenerating}
                    >
                        {isGenerating ? (
                            <>
                                <Loader size={16} className="spin" />
                                Generating...
                            </>
                        ) : (
                            <>
                                <FileText size={16} />
                                Generate Report
                            </>
                        )}
                    </button>
                </div>

                {/* Preview Section */}
                <div className="report-preview-section">
                    <h2>Preview</h2>
                    {isLoadingPreview ? (
                        <div className="preview-loading">
                            <Loader className="spin" size={24} />
                            <span>Loading preview...</span>
                        </div>
                    ) : previewData ? (
                        <div className="preview-content">
                            <div className="preview-stats">
                                <div className="stat-item">
                                    <span className="stat-value">{previewData.summary?.total_scenes || 0}</span>
                                    <span className="stat-label">Scenes</span>
                                </div>
                                <div className="stat-item">
                                    <span className="stat-value">{previewData.summary?.total_characters || 0}</span>
                                    <span className="stat-label">Characters</span>
                                </div>
                                <div className="stat-item">
                                    <span className="stat-value">{previewData.summary?.total_locations || 0}</span>
                                    <span className="stat-label">Locations</span>
                                </div>
                                <div className="stat-item">
                                    <span className="stat-value">{previewData.summary?.total_props || 0}</span>
                                    <span className="stat-label">Props</span>
                                </div>
                            </div>
                            
                            {selectedType === 'day_out_of_days' && previewData.characters && (
                                <div className="preview-table">
                                    <h4>Top Characters</h4>
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>Character</th>
                                                <th>Scenes</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {Object.entries(previewData.characters)
                                                .sort((a, b) => b[1].count - a[1].count)
                                                .slice(0, 5)
                                                .map(([name, info]) => (
                                                    <tr key={name}>
                                                        <td>{name}</td>
                                                        <td>{info.count}</td>
                                                    </tr>
                                                ))
                                            }
                                        </tbody>
                                    </table>
                                </div>
                            )}
                            
                            {selectedType === 'location' && previewData.locations && (
                                <div className="preview-table">
                                    <h4>Top Locations</h4>
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>Location</th>
                                                <th>Scenes</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {Object.entries(previewData.locations)
                                                .sort((a, b) => b[1].count - a[1].count)
                                                .slice(0, 5)
                                                .map(([name, info]) => (
                                                    <tr key={name}>
                                                        <td>{name}</td>
                                                        <td>{info.count}</td>
                                                    </tr>
                                                ))
                                            }
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="preview-empty">
                            <AlertCircle size={24} />
                            <span>No preview available</span>
                        </div>
                    )}
                </div>

                {/* Existing Reports */}
                <div className="existing-reports-section">
                    <h2>Generated Reports</h2>
                    {existingReports.length === 0 ? (
                        <div className="no-reports">
                            <FileText size={32} />
                            <p>No reports generated yet</p>
                        </div>
                    ) : (
                        <div className="reports-list">
                            {existingReports.map(report => {
                                const Icon = REPORT_ICONS[report.report_type] || FileText;
                                const generatedDate = new Date(report.generated_at).toLocaleDateString();
                                
                                return (
                                    <div key={report.id} className="report-item">
                                        <div className="report-item-info">
                                            <Icon size={20} />
                                            <div className="report-details">
                                                <span className="report-title">{report.title}</span>
                                                <span className="report-meta">
                                                    <Clock size={12} />
                                                    {generatedDate}
                                                    {report.is_public && (
                                                        <span className="shared-badge">
                                                            <Share2 size={10} />
                                                            Shared
                                                        </span>
                                                    )}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="report-item-actions">
                                            <button 
                                                className="action-btn"
                                                onClick={() => handlePrint(report.id)}
                                                title="Print"
                                            >
                                                <Printer size={16} />
                                            </button>
                                            <button 
                                                className="action-btn"
                                                onClick={() => handleDownload(report.id)}
                                                title="Download PDF"
                                            >
                                                <Download size={16} />
                                            </button>
                                            <button 
                                                className="action-btn"
                                                onClick={() => setShareModalReport(report)}
                                                title="Share"
                                            >
                                                <Share2 size={16} />
                                            </button>
                                            <button 
                                                className="action-btn danger"
                                                onClick={() => handleDelete(report.id)}
                                                title="Delete"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* Share Modal */}
            {shareModalReport && (
                <ShareModal
                    report={shareModalReport}
                    onClose={() => setShareModalReport(null)}
                    onUpdate={(updatedReport) => {
                        setExistingReports(prev => 
                            prev.map(r => r.id === updatedReport.id ? updatedReport : r)
                        );
                    }}
                />
            )}
        </div>
    );
};

export default ReportBuilder;
