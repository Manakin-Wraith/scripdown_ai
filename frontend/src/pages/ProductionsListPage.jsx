import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Clapperboard, ChevronRight, Plus } from 'lucide-react';
import { listProductions, createProduction } from '../services/apiService';
import PageHeader from '../components/layout/PageHeader';
import { Spinner } from '../components/ui';
import './ProductionPages.css';

const STATUS_LABELS = {
    development: 'Development', prep: 'Prep', shooting: 'Shooting',
    wrapped: 'Wrapped', archived: 'Archived',
};

export default function ProductionsListPage() {
    const navigate = useNavigate();
    const [productions, setProductions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [creating, setCreating] = useState(false);
    const [newTitle, setNewTitle] = useState('');
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        listProductions()
            .then((data) => setProductions(data.productions || []))
            .catch((err) => setError(err.message || 'Failed to load productions'))
            .finally(() => setLoading(false));
    }, []);

    const handleCreate = async (e) => {
        e.preventDefault();
        const title = newTitle.trim();
        if (!title || submitting) return;
        setSubmitting(true);
        try {
            const { production } = await createProduction({ title });
            navigate(`/productions/${production.id}`);
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Failed to create production');
            setSubmitting(false);
        }
    };

    if (loading) {
        return <div className="production-page-loading"><Spinner size={32} /></div>;
    }
    if (error && !productions.length) {
        return <p className="production-page-error">{error}</p>;
    }

    return (
        <div className="production-page">
            <PageHeader
                title="Productions"
                subtitle="A production groups the scripts you shoot together, with its own crew and schedule"
                actions={
                    <button className="production-new-btn" onClick={() => setCreating((v) => !v)}>
                        <Plus size={16} /> New production
                    </button>
                }
            />

            {creating && (
                <form className="production-create-form" onSubmit={handleCreate}>
                    <input
                        autoFocus
                        type="text"
                        placeholder="Production title"
                        value={newTitle}
                        onChange={(e) => setNewTitle(e.target.value)}
                    />
                    <button type="submit" disabled={submitting || !newTitle.trim()}>
                        {submitting ? 'Creating…' : 'Create'}
                    </button>
                </form>
            )}

            {error && productions.length > 0 && <p className="production-page-error">{error}</p>}

            {productions.length === 0 ? (
                <div className="production-empty-state">
                    <div className="production-empty-content">
                        <div className="production-empty-icon-wrapper">
                            <Clapperboard size={28} className="production-empty-icon" />
                        </div>
                        <h2>No productions yet</h2>
                        <p>Create a production, then attach the scripts you'll shoot under it.</p>
                    </div>
                </div>
            ) : (
                <ul className="production-list">
                    {productions.map((p) => (
                        <li key={p.id}>
                            <Link to={`/productions/${p.id}`} className="production-row">
                                <span className="production-row-title">{p.title}</span>
                                {!p.is_owner && p.member_role && (
                                    <span className="production-role-badge">{p.member_role}</span>
                                )}
                                <span className={`production-row-status status-${p.status}`}>
                                    {STATUS_LABELS[p.status] || p.status}
                                </span>
                                <ChevronRight size={18} className="production-row-chevron" />
                            </Link>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
