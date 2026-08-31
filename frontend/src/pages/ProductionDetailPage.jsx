import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import {
    getProduction, updateProduction, deleteProduction,
    addScriptToProduction, removeScriptFromProduction,
} from '../services/apiService';
import { Spinner } from '../components/ui';
import ProductionOverviewTab from '../components/productions/ProductionOverviewTab';
import ProductionCrewTab from '../components/productions/ProductionCrewTab';
import './ProductionPages.css';

export default function ProductionDetailPage() {
    const { productionId } = useParams();
    const navigate = useNavigate();

    const [production, setProduction] = useState(null);
    const [scripts, setScripts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [form, setForm] = useState(null);
    const [saving, setSaving] = useState(false);
    const [picking, setPicking] = useState(false);
    const [isOwner, setIsOwner] = useState(false);
    const [activeTab, setActiveTab] = useState('overview');

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
                setIsOwner(!!data.is_owner);
            })
            .catch((err) => {
                if (err.response?.status === 403) setError('You can view this production but not edit it.');
                else setError(err.response?.data?.error || err.message || 'Failed to load production');
            })
            .finally(() => setLoading(false));
    }, [productionId]);

    useEffect(load, [load]);

    useEffect(() => {
        if (!isOwner && activeTab === 'crew') setActiveTab('overview');
    }, [isOwner, activeTab]);

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
            setError(null);
        } catch (err) {
            if (err.response?.status === 403) { setIsOwner(false); setError('Only the production owner can edit this.'); }
            else setError(err.response?.data?.error || 'Save failed');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!window.confirm('Delete this production? Its scripts are kept and just unlinked.')) return;
        try {
            await deleteProduction(productionId);
            navigate('/productions');
        } catch (err) {
            setError(err.response?.data?.error || 'Delete failed');
        }
    };

    const handlePick = async (scriptId) => {
        await addScriptToProduction(productionId, scriptId);
        setPicking(false);
        load();
    };

    const handleRemove = async (scriptId) => {
        try {
            await removeScriptFromProduction(productionId, scriptId);
            setScripts((prev) => prev.filter((s) => s.id !== scriptId));
            setError(null);
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Failed to remove script');
        }
    };

    if (loading) return <div className="production-page-loading"><Spinner size={32} /></div>;
    if (!production) return <p className="production-page-error">{error || 'Not found'}</p>;

    const tabs = [{ id: 'overview', label: 'Overview' }];
    if (isOwner) tabs.push({ id: 'crew', label: 'Crew' });

    return (
        <div className="production-page">
            <Link to="/productions" className="production-back"><ArrowLeft size={16} /> Productions</Link>

            {error && <p className="production-page-error">{error}</p>}

            <div className="production-tabs">
                {tabs.map((t) => (
                    <button
                        key={t.id}
                        className={`production-tab ${activeTab === t.id ? 'active' : ''}`}
                        onClick={() => setActiveTab(t.id)}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            {activeTab === 'overview' && (
                <ProductionOverviewTab
                    production={production}
                    scripts={scripts}
                    form={form}
                    setForm={setForm}
                    isOwner={isOwner}
                    saving={saving}
                    onSave={save}
                    onDelete={handleDelete}
                    onPick={handlePick}
                    onRemove={handleRemove}
                    picking={picking}
                    setPicking={setPicking}
                />
            )}
            {activeTab === 'crew' && isOwner && <ProductionCrewTab productionId={productionId} />}
        </div>
    );
}
