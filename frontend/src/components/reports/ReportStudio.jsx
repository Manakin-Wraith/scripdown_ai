import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { FileText, LibraryBig, Plus, Download, Printer, Share2 } from 'lucide-react';
import { Spinner, Button } from '../ui';
import { useToast } from '../../context/ToastContext';
import { useConfirmDialog } from '../../context/ConfirmDialogContext';
import { useScript } from '../../context/ScriptContext';
import { useEntitlement } from '../../hooks/useEntitlement';
import { SubscriptionGate } from '../subscription';
import PageHeader from '../layout/PageHeader';
import {
    getReportTypes, generateReport, getScriptReports, deleteReport,
    fetchReportPrintUrl, getScriptMetadata, getFilterOptions, getFilterPresets,
    saveFilterPreset, deleteFilterPreset, previewReportHtml, getSchedules,
} from '../../services/apiService';
import ReportRail from './ReportRail';
import ReportPreviewPane from './ReportPreviewPane';
import ReportLibraryDrawer from './ReportLibraryDrawer';
import ShareModal from './ShareModal';
import './ReportStudio.css';

const EMPTY_FILTERS = {
    locations: [], location_parents: [], characters: [], int_ext: [], time_of_day: [],
    story_days: [], scene_numbers: [], scene_range: { from: '', to: '' },
    timeline_codes: [], categories: [], group_by: 'scene_number',
};

// Pure helper — strip empty values from any filters object. Module scope so it is
// stable across renders (no exhaustive-deps churn in the callbacks that use it).
const computeActiveFilters = (f) => {
    const active = {};
    if (f.locations?.length) active.locations = f.locations;
    if (f.location_parents?.length) active.location_parents = f.location_parents;
    if (f.characters?.length) active.characters = f.characters;
    if (f.int_ext?.length) active.int_ext = f.int_ext;
    if (f.time_of_day?.length) active.time_of_day = f.time_of_day;
    if (f.story_days?.length) active.story_days = f.story_days;
    if (f.scene_numbers?.length) active.scene_numbers = f.scene_numbers;
    if (f.scene_range?.from || f.scene_range?.to) active.scene_range = f.scene_range;
    if (f.timeline_codes?.length) active.timeline_codes = f.timeline_codes;
    return Object.keys(active).length > 0 ? active : null;
};

const ReportStudio = () => {
    const { scriptId } = useParams();
    const [searchParams] = useSearchParams();
    const toast = useToast();
    const { confirm } = useConfirmDialog();
    const { setScript } = useScript();
    const { entitlement } = useEntitlement();

    const [reportTypes, setReportTypes] = useState({});
    const [selectedType, setSelectedType] = useState('scene_breakdown');
    const [customTitle, setCustomTitle] = useState('');
    const [existingReports, setExistingReports] = useState([]);
    const [activeReport, setActiveReport] = useState(null);
    const [loading, setLoading] = useState(true);

    const [filterOptions, setFilterOptions] = useState(null);
    const [filterPresets, setFilterPresets] = useState([]);
    const [filters, setFilters] = useState(EMPTY_FILTERS);

    const [scheduleId, setScheduleId] = useState(null);
    const [schedules, setSchedules] = useState([]);

    const [previewHtml, setPreviewHtml] = useState('');
    const [previewCounts, setPreviewCounts] = useState({ match: null, total: null });
    const [previewLoading, setPreviewLoading] = useState(false);
    const [previewError, setPreviewError] = useState(null);

    const [libraryOpen, setLibraryOpen] = useState(false);
    const [shareModalReport, setShareModalReport] = useState(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [previewNonce, setPreviewNonce] = useState(0);

    // Refs mirror the latest config so the (stable) preview fn never reads stale state,
    // even when called synchronously right after setState (e.g. Library reopen).
    const filtersRef = useRef(filters);
    const typeRef = useRef(selectedType);
    const titleRef = useRef(customTitle);
    const scheduleIdRef = useRef(scheduleId);
    filtersRef.current = filters;
    typeRef.current = selectedType;
    titleRef.current = customTitle;
    scheduleIdRef.current = scheduleId;

    // Single refresh trigger: bump the nonce; the effect below runs the render.
    const triggerPreview = useCallback(() => setPreviewNonce((n) => n + 1), []);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                const typesRes = await getReportTypes();
                if (typesRes.success) setReportTypes(typesRes.report_types);
                try {
                    const metadata = await getScriptMetadata(scriptId);
                    setScript({ id: scriptId, title: metadata?.title || metadata?.script_name });
                } catch (e) { console.warn('metadata', e); }
                const reportsRes = await getScriptReports(scriptId);
                if (reportsRes.success) setExistingReports(reportsRes.reports);
                try {
                    const filterRes = await getFilterOptions(scriptId);
                    if (filterRes.success) setFilterOptions(filterRes.options);
                } catch (e) { console.warn('filter options', e); }
                try {
                    const presetsRes = await getFilterPresets(scriptId);
                    if (presetsRes.success) setFilterPresets(presetsRes.presets);
                } catch (e) { console.warn('presets', e); }
                try {
                    const schedRes = await getSchedules(scriptId);
                    setSchedules(schedRes.schedules || []);
                } catch (e) { console.warn('schedules', e); }
            } catch (error) {
                toast.error('Error', 'Failed to load report data');
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [scriptId]);

    // Deep-link: read ?type= and ?schedule= on mount once schedules/report types are loaded.
    useEffect(() => {
        const t = searchParams.get('type');
        const s = searchParams.get('schedule');
        if (t && reportTypes[t]) setSelectedType(t);
        if (s) setScheduleId(s);
        if (t || s) triggerPreview();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [schedules, reportTypes]);

    const buildActiveFilters = useCallback(() => computeActiveFilters(filters), [filters]);

    // Stable ([] deps): always reads the latest config via refs, so it is safe to
    // fire from the button, from onSelectType, or synchronously after a reopen.
    const handleUpdatePreview = useCallback(async () => {
        const f = filtersRef.current;
        const requiresSchedule = reportTypes[typeRef.current]?.requires_schedule;
        if (requiresSchedule && !scheduleIdRef.current) {
            setPreviewHtml('');
            setPreviewError('Select a schedule source to generate this report.');
            setPreviewLoading(false);
            return;
        }
        setPreviewLoading(true);
        setPreviewError(null);
        try {
            const activeFilters = computeActiveFilters(f);
            const groupBy = f.group_by !== 'scene_number' ? f.group_by : null;
            const categories = f.categories?.length > 0 ? f.categories : null;
            const res = await previewReportHtml(scriptId, typeRef.current, activeFilters, groupBy, categories, titleRef.current || null, scheduleIdRef.current);
            if (res.success) {
                setPreviewHtml(res.html);
                setPreviewCounts({ match: res.match_count, total: res.total_count });
            } else {
                setPreviewError(res.error || 'Failed to render preview');
            }
        } catch (e) {
            setPreviewError(e.message || 'Failed to render preview');
        } finally {
            setPreviewLoading(false);
        }
    }, [scriptId]);

    // The one automatic refresh path: runs whenever triggerPreview() bumps the nonce.
    // Refs are already updated (set during render, before this post-commit effect), so
    // handleUpdatePreview reads the current type/filters/title.
    useEffect(() => {
        if (!loading && previewNonce > 0) handleUpdatePreview();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [previewNonce]);

    const handleGenerate = async () => {
        setIsGenerating(true);
        try {
            const activeFilters = buildActiveFilters();
            const groupBy = filters.group_by !== 'scene_number' ? filters.group_by : null;
            const categories = filters.categories?.length > 0 ? filters.categories : null;
            const res = await generateReport(scriptId, selectedType, customTitle || null, null, activeFilters, groupBy, categories, scheduleId);
            if (res.success) {
                toast.success('Report Generated', 'Your report is ready!');
                setExistingReports((prev) => [res.report, ...prev]);
                setActiveReport(res.report);
            } else {
                toast.error('Error', res.error || 'Failed to generate report');
            }
        } catch (error) {
            toast.error('Error', error.message || 'Failed to generate report');
        } finally {
            setIsGenerating(false);
        }
    };

    const handleReopen = (report) => {
        setSelectedType(report.report_type && reportTypes[report.report_type] ? report.report_type : 'scene_breakdown');
        const cfg = report.config || {};
        setFilters({
            ...EMPTY_FILTERS,
            ...(cfg.filters || {}),
            categories: cfg.categories || [],
            group_by: cfg.group_by || 'scene_number',
        });
        setCustomTitle(report.title || '');
        setActiveReport(report);
        setLibraryOpen(false);
        // Refs update during the re-render these setStates cause; the nonce effect then
        // reads the restored config. Works for both same-type and cross-type reopens.
        triggerPreview();
    };

    const openPrintable = async (report) => {
        const win = window.open('', '_blank');
        try {
            const url = await fetchReportPrintUrl(report.id);
            if (win) win.location = url; else window.open(url, '_blank');
            setTimeout(() => URL.revokeObjectURL(url), 60000);
        } catch (e) {
            if (win) win.close();
            toast.error('Error', 'Could not open the report');
        }
    };

    const handleDownload = (report) => openPrintable(report);
    const handlePrint = (report) => openPrintable(report);

    const handleDelete = async (report) => {
        const ok = await confirm({ title: 'Delete Report?', message: 'This report will be permanently deleted.', variant: 'danger' });
        if (!ok) return;
        try {
            await deleteReport(report.id);
            setExistingReports((prev) => prev.filter((r) => r.id !== report.id));
            if (activeReport?.id === report.id) setActiveReport(null);
            toast.success('Deleted', 'Report deleted');
        } catch (error) {
            toast.error('Error', 'Failed to delete report');
        }
    };

    const filterPanelProps = {
        filterOptions,
        filters,
        onFilterChange: setFilters,
        onToggleCollapse: () => {},
        presets: filterPresets,
        onLoadPreset: (preset) => {
            setFilters({
                ...EMPTY_FILTERS,
                ...(preset.filters || {}),
                categories: preset.categories || [],
                group_by: preset.group_by || 'scene_number',
            });
            toast.success('Preset Loaded', `Applied "${preset.name}"`);
        },
        onSavePreset: async (name) => {
            try {
                const res = await saveFilterPreset(scriptId, {
                    name, filters: buildActiveFilters() || {},
                    categories: filters.categories || [], group_by: filters.group_by || 'scene_number',
                });
                if (res.success) {
                    setFilterPresets((prev) => [...prev, res.preset]);
                    toast.success('Preset Saved', `"${name}" saved`);
                }
            } catch (e) { toast.error('Error', 'Failed to save preset'); }
        },
        onDeletePreset: async (presetId) => {
            try {
                await deleteFilterPreset(presetId);
                setFilterPresets((prev) => prev.filter((p) => p.id !== presetId));
                toast.success('Deleted', 'Preset deleted');
            } catch (e) { toast.error('Error', 'Failed to delete preset'); }
        },
    };

    if (loading) {
        return (
            <div className="report-studio-loading">
                <Spinner size={32} />
                <p>Loading report studio…</p>
            </div>
        );
    }

    if (!entitlement?.can_run_breakdown) {
        return (
            <div className="report-studio page-container">
                <PageHeader icon={<FileText size={24} />} title="Reports" />
                <SubscriptionGate feature="reports" showBlur blurAmount={8}>
                    <div className="report-studio-preview">
                        <p>Generate professional reports including scene breakdowns, day-out-of-days, location reports, and more.</p>
                    </div>
                </SubscriptionGate>
            </div>
        );
    }

    const hasActive = Boolean(activeReport);

    return (
        <div className="report-studio">
            <div className="studio-toolbar">
                <div className="studio-title"><FileText size={18} /> Report Studio</div>
                <div className="studio-actions">
                    <Button variant="secondary" onClick={() => setLibraryOpen(true)}>
                        <LibraryBig size={16} /> Library
                    </Button>
                    <Button variant="primary" onClick={handleGenerate} disabled={isGenerating}>
                        {isGenerating ? <Spinner size={16} /> : <Plus size={16} />} Generate
                    </Button>
                    <button className="studio-icon-btn" disabled={!hasActive} onClick={() => hasActive && handleDownload(activeReport)} title="Download"><Download size={16} /></button>
                    <button className="studio-icon-btn" disabled={!hasActive} onClick={() => hasActive && handlePrint(activeReport)} title="Print"><Printer size={16} /></button>
                    <button className="studio-icon-btn" disabled={!hasActive} onClick={() => hasActive && setShareModalReport(activeReport)} title="Share"><Share2 size={16} /></button>
                </div>
            </div>

            <div className="studio-body">
                <div className="studio-rail">
                    <ReportRail
                        reportTypes={reportTypes}
                        selectedType={selectedType}
                        onSelectType={(t) => { setSelectedType(t); triggerPreview(); }}
                        customTitle={customTitle}
                        onTitleChange={setCustomTitle}
                        filterPanelProps={filterPanelProps}
                        schedules={schedules}
                        scheduleId={scheduleId}
                        onScheduleChange={(id) => { setScheduleId(id); triggerPreview(); }}
                    />
                </div>
                <div className="studio-preview">
                    <ReportPreviewPane
                        html={previewHtml}
                        matchCount={previewCounts.match}
                        totalCount={previewCounts.total}
                        loading={previewLoading}
                        error={previewError}
                        onRefresh={triggerPreview}
                    />
                </div>
            </div>

            <ReportLibraryDrawer
                open={libraryOpen}
                reports={existingReports}
                onClose={() => setLibraryOpen(false)}
                onReopen={handleReopen}
                onDownload={handleDownload}
                onShare={(report) => setShareModalReport(report)}
                onDelete={handleDelete}
            />

            {shareModalReport && (
                <ShareModal
                    report={shareModalReport}
                    onClose={() => setShareModalReport(null)}
                    onUpdate={(updated) => {
                        setExistingReports((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
                        if (activeReport?.id === updated.id) setActiveReport(updated);
                    }}
                />
            )}
        </div>
    );
};

export default ReportStudio;
