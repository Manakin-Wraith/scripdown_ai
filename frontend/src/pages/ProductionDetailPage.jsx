import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Trash2, Plus, X } from 'lucide-react';
import {
    getProduction, updateProduction, deleteProduction,
    addScriptToProduction, removeScriptFromProduction,
} from '../services/apiService';
import { Spinner } from '../components/ui';
import ProductionScriptPicker from '../components/productions/ProductionScriptPicker';
import './ProductionPages.css';

const STATUSES = ['development', 'prep', 'shooting', 'wrapped', 'archived'];

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
                // Heuristic: PATCH is owner-only; probe cheaply by allowing edit
                // and letting the server 403. Simpler: treat as owner if the
                // list endpoint returned this production. Here we optimistically
                // enable and surface a 403 on save.
                setIsOwner(true);
            })
            .catch((err) => {
                if (err.response?.status === 403) setError('You can view this production but not edit it.');
                else setError(err.response?.data?.error || err.message || 'Failed to load production');
            })
            .finally(() => setLoading(false));
    }, [productionId]);

    useEffect(load, [load]);

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
        await removeScriptFromProduction(productionId, scriptId);
        setScripts((prev) => prev.filter((s) => s.id !== scriptId));
    };

    if (loading) return <div className="production-page-loading"><Spinner size={32} /></div>;
    if (!production) return <p className="production-page-error">{error || 'Not found'}</p>;

    return (
        <div className="production-page">
            <Link to="/productions" className="production-back"><ArrowLeft size={16} /> Productions</Link>

            {error && <p className="production-page-error">{error}</p>}

            <form className="production-overview" onSubmit={save}>
                <label>
                    Title
                    <input value={form.title} disabled={!isOwner}
                        onChange={(e) => setForm({ ...form, title: e.target.value })} />
                </label>
                <label>
                    Status
                    <select value={form.status} disabled={!isOwner}
                        onChange={(e) => setForm({ ...form, status: e.target.value })}>
                        {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                </label>
                <div className="production-date-row">
                    <label>
                        Shoot start
                        <input type="date" value={form.shoot_start_date} disabled={!isOwner}
                            onChange={(e) => setForm({ ...form, shoot_start_date: e.target.value })} />
                    </label>
                    <label>
                        Shoot end
                        <input type="date" value={form.shoot_end_date} disabled={!isOwner}
                            onChange={(e) => setForm({ ...form, shoot_end_date: e.target.value })} />
                    </label>
                </div>
                <label>
                    Notes
                    <textarea value={form.notes} disabled={!isOwner} rows={3}
                        onChange={(e) => setForm({ ...form, notes: e.target.value })} />
                </label>
                {isOwner && (
                    <div className="production-overview-actions">
                        <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
                        <button type="button" className="production-delete-btn" onClick={handleDelete}>
                            <Trash2 size={14} /> Delete production
                        </button>
                    </div>
                )}
            </form>

            <section className="production-scripts">
                <div className="production-scripts-head">
                    <h3>Scripts</h3>
                    {isOwner && (
                        <button onClick={() => setPicking(true)}><Plus size={14} /> Add script</button>
                    )}
                </div>
                {scripts.length === 0 ? (
                    <p className="production-scripts-empty">No scripts attached yet.</p>
                ) : (
                    <ul className="production-scripts-list">
                        {scripts.map((s) => (
                            <li key={s.id}>
                                <Link to={`/scenes/${s.id}`}>{s.title || 'Untitled script'}</Link>
                                {isOwner && (
                                    <button className="production-script-remove"
                                        onClick={() => handleRemove(s.id)} aria-label="Remove script">
                                        <X size={14} />
                                    </button>
                                )}
                            </li>
                        ))}
                    </ul>
                )}
            </section>

            {picking && (
                <ProductionScriptPicker onPick={handlePick} onClose={() => setPicking(false)} />
            )}
        </div>
    );
}
