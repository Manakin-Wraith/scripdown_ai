import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link, Navigate, useSearchParams } from 'react-router-dom';
import {
    getProduction, updateProduction, deleteProduction,
    addScriptToProduction, removeScriptFromProduction, listProductionMembers,
} from '../services/apiService';
import { Spinner } from '../components/ui';
import { announceProductionUpdated } from '../hooks/useScriptProduction';
import ProductionOverviewTab from '../components/productions/ProductionOverviewTab';
import ProductionCrewTab from '../components/productions/ProductionCrewTab';
import ProductionLocationsTab from '../components/productions/ProductionLocationsTab';
import ProductionMembersTab from '../components/productions/ProductionMembersTab';
import ProductionCallSheetTab from '../components/productions/ProductionCallSheetTab';
import ProductionCastTab from '../components/productions/ProductionCastTab';
import DetachScriptModal from '../components/productions/DetachScriptModal';
import './ProductionPages.css';

const NO_ACCESS = {
    role: null, can_view_sensitive: false, can_edit_crew: false,
    can_manage_members: false, can_edit_production: false, can_edit_call_sheet_template: false,
    script_access: 'none',
};

const TAB_IDS = ['overview', 'crew', 'cast', 'locations', 'callsheet', 'members'];

export default function ProductionDetailPage() {
    const { productionId, tab, subId } = useParams();
    const navigate = useNavigate();

    const [production, setProduction] = useState(null);
    const [scripts, setScripts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [form, setForm] = useState(null);
    const [saving, setSaving] = useState(false);
    const [picking, setPicking] = useState(false);
    const [access, setAccess] = useState(NO_ACCESS);
    const [searchParams] = useSearchParams();
    const activeTab = tab || 'overview';
    const [detaching, setDetaching] = useState(null);

    const isOwner = access.role === 'owner';
    const canManageMembers = isOwner || access.can_manage_members;
    const isMember = isOwner || access.role !== null;

    const load = useCallback(() => {
        getProduction(productionId)
            .then((data) => {
                setProduction(data.production);
                setScripts(data.scripts || []);
                setForm({
                    title: data.production.title || '',
                    status: data.production.status || 'development',
                    shoot_start_date: data.production.shoot_start_date || '',
                    shoot_end_date: data.production.shoot_end_date || '',
                    notes: data.production.notes || '',
                });
                setAccess(data.production_access || NO_ACCESS);
            })
            .catch((err) => {
                if (err.response?.status === 403) setError('You can view this production but not edit it.');
                else setError(err.response?.data?.error || err.message || 'Failed to load production');
            })
            .finally(() => setLoading(false));
    }, [productionId]);

    useEffect(load, [load]);

    // Legacy links used /productions/:id?tab=crew; send them to the tab's own URL.
    const legacyTab = searchParams.get('tab');
    useEffect(() => {
        if (!tab && TAB_IDS.includes(legacyTab)) {
            navigate(`/productions/${productionId}/${legacyTab}`, { replace: true });
        }
    }, [tab, legacyTab, productionId, navigate]);

    const save = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            const payload = {
                ...form,
                shoot_start_date: form.shoot_start_date || null,
                shoot_end_date: form.shoot_end_date || null,
            };
            const { production: updated } = await updateProduction(productionId, payload);
            setProduction(updated);
            announceProductionUpdated(updated);
            setError(null);
        } catch (err) {
            if (err.response?.status === 403) setError('You do not have permission to edit this.');
            else setError(err.response?.data?.error || 'Save failed');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        let memberCount = 0;
        try {
            const d = await listProductionMembers(productionId);
            memberCount = (d.members || []).length;
        } catch {
            // Count is only for the warning copy; proceed without it.
        }
        const warn = memberCount > 0
            ? ` ${memberCount} member${memberCount === 1 ? '' : 's'} will lose access to its ${scripts.length} script${scripts.length === 1 ? '' : 's'}.`
            : '';
        if (!window.confirm(`Delete this production? Its scripts are kept and just unlinked.${warn}`)) return;
        try {
            await deleteProduction(productionId);
            navigate('/productions');
        } catch (err) {
            setError(err.response?.data?.error || 'Delete failed');
        }
    };

    const handlePick = async (scriptId, membersAction = null) => {
        await addScriptToProduction(productionId, scriptId, membersAction);
        setPicking(false);
        load();
    };

    const handleRemove = (script) => setDetaching(script);

    const confirmDetach = async (keepUserIds) => {
        await removeScriptFromProduction(productionId, detaching.id, keepUserIds);
        setScripts((prev) => prev.filter((s) => s.id !== detaching.id));
        setDetaching(null);
        setError(null);
    };

    if (loading) return <div className="production-page-loading"><Spinner size={32} /></div>;
    if (!production) return <p className="production-page-error">{error || 'Not found'}</p>;

    const tabs = [{ id: 'overview', label: 'Overview' }];
    if (isMember) tabs.push({ id: 'crew', label: 'Crew' });
    if (isMember) tabs.push({ id: 'cast', label: 'Cast' });
    if (isMember) tabs.push({ id: 'locations', label: 'Locations' });
    if (isMember) tabs.push({ id: 'callsheet', label: 'Call Sheet' });
    if (canManageMembers) tabs.push({ id: 'members', label: 'Members' });

    // Unknown tab, or one this viewer may not see: back to Overview.
    if (tab && !tabs.some((t) => t.id === tab)) {
        return <Navigate to={`/productions/${productionId}`} replace />;
    }

    return (
        <div className="production-page">
            {error && <p className="production-page-error">{error}</p>}

            <div className="production-tabs">
                {tabs.map((t) => (
                    <Link
                        key={t.id}
                        to={t.id === 'overview' ? `/productions/${productionId}` : `/productions/${productionId}/${t.id}`}
                        className={`production-tab ${activeTab === t.id ? 'active' : ''}`}
                    >
                        {t.label}
                    </Link>
                ))}
            </div>

            {activeTab === 'overview' && (
                <ProductionOverviewTab
                    production={production}
                    scripts={scripts}
                    form={form}
                    setForm={setForm}
                    isOwner={access.can_edit_production}
                    canDelete={isOwner}
                    saving={saving}
                    onSave={save}
                    onDelete={handleDelete}
                    onPick={handlePick}
                    onRemove={handleRemove}
                    picking={picking}
                    setPicking={setPicking}
                />
            )}
            {activeTab === 'crew' && isMember && (
                <ProductionCrewTab productionId={productionId} access={access} />
            )}
            {activeTab === 'cast' && isMember && (
                <ProductionCastTab productionId={productionId} scripts={scripts} scriptId={subId} />
            )}
            {activeTab === 'locations' && isMember && (
                <ProductionLocationsTab productionId={productionId} access={access} />
            )}
            {activeTab === 'callsheet' && isMember && (
                <ProductionCallSheetTab productionId={productionId} access={access} />
            )}
            {activeTab === 'members' && canManageMembers && (
                <ProductionMembersTab productionId={productionId} access={access} scriptCount={scripts.length} />
            )}

            {detaching && (
                <DetachScriptModal
                    productionId={productionId}
                    script={detaching}
                    onConfirm={confirmDetach}
                    onClose={() => setDetaching(null)}
                />
            )}
        </div>
    );
}
