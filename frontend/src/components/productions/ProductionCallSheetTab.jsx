import { useState, useEffect, useCallback, useMemo } from 'react';
import { getCallSheetTemplate, saveCallSheetTemplate } from '../../services/apiService';
import { Spinner } from '../ui';
import { useToast } from '../../context/ToastContext';
import SectionsPanel from './callSheetTemplate/SectionsPanel';
import FieldListPanel from './callSheetTemplate/FieldListPanel';
import DepartmentsPanel from './callSheetTemplate/DepartmentsPanel';
import KeyValueListPanel from './callSheetTemplate/KeyValueListPanel';
import './ProductionCallSheetTab.css';

export default function ProductionCallSheetTab({ productionId, access }) {
    const toast = useToast();
    const canEdit = access.role === 'owner' || !!access.can_edit_call_sheet_template;
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(null);
    const [saved, setSaved] = useState(null);   // { config, updated_at, is_default, default_config }
    const [draft, setDraft] = useState(null);
    const [saving, setSaving] = useState(false);
    const [errors, setErrors] = useState([]);

    const load = useCallback(async () => {
        setLoading(true);
        setLoadError(null);
        try {
            const { template } = await getCallSheetTemplate(productionId);
            setSaved(template);
            setDraft(template.config);
            setErrors([]);
        } catch (err) {
            console.error('Failed to load call sheet template:', err);
            setLoadError('Could not load the call sheet template.');
        } finally {
            setLoading(false);
        }
    }, [productionId]);

    useEffect(() => { load(); }, [load]);

    const dirty = useMemo(
        () => !!draft && !!saved && JSON.stringify(draft) !== JSON.stringify(saved.config),
        [draft, saved],
    );

    const part = (name) => (value) => setDraft((d) => ({ ...d, [name]: value }));

    const save = async () => {
        setSaving(true);
        setErrors([]);
        try {
            const res = await saveCallSheetTemplate(productionId, draft, saved.updated_at);
            setSaved({ ...saved, ...res.template });
            setDraft(res.template.config);
            toast.success('Template saved', 'New call sheets and PDFs will use it.');
        } catch (err) {
            const status = err.response?.status;
            if (status === 400) {
                setErrors(err.response.data.details || []);
                toast.error('Fix the highlighted fields', 'The template was not saved.');
            } else if (status === 409) {
                toast.warning('Template changed', 'Someone else saved a newer version. Reloading it now.');
                await load();
            } else {
                toast.error('Save failed', 'Could not save the template.');
            }
        } finally {
            setSaving(false);
        }
    };

    const resetToDefault = () => {
        if (saved?.default_config) {
            setDraft(saved.default_config);
            setErrors([]);
        }
    };

    if (loading) return <Spinner />;
    if (loadError || !draft) return <p className="cst-error">{loadError || 'No template.'}</p>;

    return (
        <div className="cst-tab">
            <div className="cst-toolbar">
                <p className="cst-intro">
                    This template controls what every call sheet and PDF for this production contains.
                    {saved.is_default && ' Using the standard layout; save to customize.'}
                </p>
                {canEdit ? (
                    <div className="cst-toolbar-actions">
                        {dirty && <span className="cst-dirty">Unsaved changes</span>}
                        <button type="button" onClick={resetToDefault} disabled={saving}>Reset to default</button>
                        <button type="button" className="cst-primary" onClick={save} disabled={saving || !dirty}>
                            {saving ? 'Saving…' : 'Save template'}
                        </button>
                    </div>
                ) : (
                    <span className="cst-hint">Read-only: you don&rsquo;t have permission to edit the template.</span>
                )}
            </div>

            <SectionsPanel sections={draft.sections} onChange={part('sections')} canEdit={canEdit} errors={errors} />
            <FieldListPanel title="Day fields" hint="Built-ins can be hidden or renamed. Add your own (wind, base camp, wrap…)."
                            items={draft.day_fields} onChange={part('day_fields')} mode="day" canEdit={canEdit}
                            errors={errors} errorPrefix="day_fields" />
            <KeyValueListPanel title="Key crew (header)" hint="Producer, director, DoP… shown in the header block."
                               items={draft.key_crew} onChange={part('key_crew')} valueField="value"
                               canEdit={canEdit} errors={errors} errorPrefix="key_crew" addLabel="Add person" />
            <FieldListPanel title="Cast columns" hint="Extra columns on the cast table (P/U, costume, M-UP&H, mic'ing…)."
                            items={draft.cast_columns} onChange={part('cast_columns')} mode="column" canEdit={canEdit}
                            errors={errors} errorPrefix="cast_columns" />
            <FieldListPanel title="Crew columns" hint="Extra columns on the crew table."
                            items={draft.crew_columns} onChange={part('crew_columns')} mode="column" canEdit={canEdit}
                            errors={errors} errorPrefix="crew_columns" />
            <FieldListPanel title="Scene columns" hint="Extra columns on the scene table (story day, story time, BG…)."
                            items={draft.scene_columns} onChange={part('scene_columns')} mode="column" canEdit={canEdit}
                            errors={errors} errorPrefix="scene_columns" />
            <DepartmentsPanel items={draft.departments} onChange={part('departments')} canEdit={canEdit} errors={errors} />
            <KeyValueListPanel title="Boilerplate blocks" hint="Standing notices (safety, no-photos, water bottles…). Each day can override."
                               items={draft.blocks} onChange={part('blocks')} valueField="body" multiline
                               canEdit={canEdit} errors={errors} errorPrefix="blocks" addLabel="Add block" />
        </div>
    );
}
