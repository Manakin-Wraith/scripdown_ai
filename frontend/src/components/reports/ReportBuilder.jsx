import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
    FileText, Download, Share2, Printer, ChevronRight, 
    Users, MapPin, Package, Shirt, Film, List, BookOpen,
    Loader, Check, Clock, Trash2, ExternalLink,
    UserPlus, Zap, Flame, CalendarDays
} from 'lucide-react';
import { useToast } from '../../context/ToastContext';
import { useScript } from '../../context/ScriptContext';
import { useAuth } from '../../context/AuthContext';
import { 
    getReportTypes, 
    generateReport, 
    getScriptReports,
    deleteReport,
    getReportPdfUrl,
    getReportPrintUrl,
    getScriptMetadata,
    getFilterOptions,
    getFilterPresets,
    saveFilterPreset,
    deleteFilterPreset
} from '../../services/apiService';
import ShareModal from './ShareModal';
import ReportFilterPanel from './ReportFilterPanel';
import { SubscriptionGate } from '../subscription';
import { useSubscription } from '../../hooks/useSubscription';
import './ReportBuilder.css';

const REPORT_ICONS = {
    scene_breakdown: Film,
    day_out_of_days: Users,
    location: MapPin,
    props: Package,
    wardrobe: Shirt,
    one_liner: List,
    full_breakdown: BookOpen,
    extras: UserPlus,
    sfx: Zap,
    special_effects: Zap,
    stunts: Flame
};

const ReportBuilder = () => {
    const { scriptId } = useParams();
    const navigate = useNavigate();
    const toast = useToast();
    const { setScript } = useScript();
    const { canAccess, status, daysRemaining } = useSubscription();
    
    const [reportTypes, setReportTypes] = useState({});
    const [selectedType, setSelectedType] = useState('scene_breakdown');
    const [customTitle, setCustomTitle] = useState('');
    const [scriptMetadata, setScriptMetadata] = useState(null);
    const [existingReports, setExistingReports] = useState([]);
    const [isGenerating, setIsGenerating] = useState(false);
    const [shareModalReport, setShareModalReport] = useState(null);
    const [loading, setLoading] = useState(true);
    
    // Filter state
    const [filterOptions, setFilterOptions] = useState(null);
    const [filterPresets, setFilterPresets] = useState([]);
    const [filterPanelCollapsed, setFilterPanelCollapsed] = useState(false);
    const [filters, setFilters] = useState({
        locations: [],
        location_parents: [],
        characters: [],
        int_ext: [],
        time_of_day: [],
        story_days: [],
        scene_numbers: [],
        scene_range: { from: '', to: '' },
        timeline_codes: [],
        categories: [],
        group_by: 'scene_number'
    });

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
                
                // Fetch filter options and presets
                try {
                    const filterRes = await getFilterOptions(scriptId);
                    if (filterRes.success) {
                        setFilterOptions(filterRes.options);
                    }
                } catch (e) {
                    console.warn('Could not fetch filter options:', e);
                }
                
                try {
                    const presetsRes = await getFilterPresets(scriptId);
                    if (presetsRes.success) {
                        setFilterPresets(presetsRes.presets);
                    }
                } catch (e) {
                    console.warn('Could not fetch filter presets:', e);
                }
            } catch (error) {
                toast.error('Error', 'Failed to load report data');
            } finally {
                setLoading(false);
            }
        };
        
        fetchData();
    }, [scriptId]);

    // Build clean filters object (strip empty values)
    const buildActiveFilters = useCallback(() => {
        const active = {};
        if (filters.locations?.length) active.locations = filters.locations;
        if (filters.location_parents?.length) active.location_parents = filters.location_parents;
        if (filters.characters?.length) active.characters = filters.characters;
        if (filters.int_ext?.length) active.int_ext = filters.int_ext;
        if (filters.time_of_day?.length) active.time_of_day = filters.time_of_day;
        if (filters.story_days?.length) active.story_days = filters.story_days;
        if (filters.scene_numbers?.length) active.scene_numbers = filters.scene_numbers;
        if (filters.scene_range?.from || filters.scene_range?.to) active.scene_range = filters.scene_range;
        if (filters.timeline_codes?.length) active.timeline_codes = filters.timeline_codes;
        return Object.keys(active).length > 0 ? active : null;
    }, [filters]);

    const handleGenerate = async () => {
        setIsGenerating(true);
        try {
            const title = customTitle || null;
            const activeFilters = buildActiveFilters();
            const groupBy = filters.group_by !== 'scene_number' ? filters.group_by : null;
            const categories = filters.categories?.length > 0 ? filters.categories : null;
            const res = await generateReport(scriptId, selectedType, title, null, activeFilters, groupBy, categories);
            
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

    if (loading) {
        return (
            <div className="report-builder-loading">
                <Loader className="spin" size={32} />
                <p>Loading report builder...</p>
            </div>
        );
    }

    // Check if user has access to reports feature
    const hasReportAccess = canAccess('reports');

    // If no access, show gated preview
    if (!hasReportAccess) {
        return (
            <div className="report-builder">
                <div className="report-builder-header">
                    <h1>
                        <FileText size={24} />
                        Generate Reports
                    </h1>
                </div>
                <SubscriptionGate 
                    feature="reports"
                    showBlur={true}
                    blurAmount={8}
                >
                    <div className="report-builder-preview">
                        <p>Generate professional reports including scene breakdowns, day-out-of-days, location reports, and more.</p>
                    </div>
                </SubscriptionGate>
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

            {/* Report Type Selection — Full Width */}
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

            {/* Two-Column: Filters (left) | Config + Reports (right) */}
            <div className="report-builder-layout">
                {/* Filter Panel */}
                <ReportFilterPanel
                    filterOptions={filterOptions}
                    filters={filters}
                    onFilterChange={setFilters}
                    isCollapsed={filterPanelCollapsed}
                    onToggleCollapse={() => setFilterPanelCollapsed(!filterPanelCollapsed)}
                    presets={filterPresets}
                    onLoadPreset={(preset) => {
                        const newFilters = {
                            locations: [],
                            location_parents: [],
                            characters: [],
                            int_ext: [],
                            time_of_day: [],
                            story_days: [],
                            scene_numbers: [],
                            scene_range: { from: '', to: '' },
                            timeline_codes: [],
                            ...(preset.filters || {}),
                            categories: preset.categories || [],
                            group_by: preset.group_by || 'scene_number'
                        };
                        setFilters(newFilters);
                        toast.success('Preset Loaded', `Applied "${preset.name}"`);
                    }}
                    onSavePreset={async (name) => {
                        try {
                            const activeFilters = buildActiveFilters();
                            const res = await saveFilterPreset(scriptId, {
                                name,
                                filters: activeFilters || {},
                                categories: filters.categories || [],
                                group_by: filters.group_by || 'scene_number'
                            });
                            if (res.success) {
                                setFilterPresets(prev => [...prev, res.preset]);
                                toast.success('Preset Saved', `"${name}" saved`);
                            }
                        } catch (e) {
                            toast.error('Error', 'Failed to save preset');
                        }
                    }}
                    onDeletePreset={async (presetId) => {
                        try {
                            await deleteFilterPreset(presetId);
                            setFilterPresets(prev => prev.filter(p => p.id !== presetId));
                            toast.success('Deleted', 'Preset deleted');
                        } catch (e) {
                            toast.error('Error', 'Failed to delete preset');
                        }
                    }}
                />

                {/* Right Column: Config + Generated Reports */}
                <div className="report-builder-sidebar">
                    {/* Compact Config Bar */}
                    <div className="report-config-section">
                        <div className="config-inline">
                            <input
                                type="text"
                                id="customTitle"
                                value={customTitle}
                                onChange={(e) => setCustomTitle(e.target.value)}
                                placeholder={`Custom title (optional)`}
                                className="config-title-input"
                            />
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
                                                    title="Download/Print"
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
