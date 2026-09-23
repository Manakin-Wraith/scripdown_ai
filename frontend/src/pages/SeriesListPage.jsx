import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Layers, ChevronRight, Plus, Trash2 } from 'lucide-react';
import { listSeries, deleteSeries } from '../services/apiService';
import { useConfirmDialog } from '../context/ConfirmDialogContext';
import { useToast } from '../context/ToastContext';
import PageHeader from '../components/layout/PageHeader';
import { Spinner } from '../components/ui';
import './SeriesPages.css';

export default function SeriesListPage() {
    const [series, setSeries] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [deletingId, setDeletingId] = useState(null);
    const { confirm } = useConfirmDialog();
    const toast = useToast();

    useEffect(() => {
        listSeries()
            .then((data) => setSeries(data.series || []))
            .catch((err) => setError(err.message || 'Failed to load series'))
            .finally(() => setLoading(false));
    }, []);

    const handleDelete = async (s) => {
        const confirmed = await confirm({
            title: `Delete "${s.title}"?`,
            message: 'All of its seasons will be removed. Episode scripts are not deleted — they stay in My Scripts as standalone scripts.',
            variant: 'danger',
        });
        if (!confirmed) return;

        setDeletingId(s.id);
        try {
            await deleteSeries(s.id);
            setSeries((prev) => prev.filter((item) => item.id !== s.id));
            toast.success('Series deleted', `"${s.title}" was removed.`);
        } catch (err) {
            toast.error('Could not delete series', err.response?.data?.error || err.message);
        } finally {
            setDeletingId(null);
        }
    };

    if (loading) {
        return (
            <div className="series-page-loading">
                <Spinner size={32} />
            </div>
        );
    }

    if (error) {
        return <p className="series-page-error">{error}</p>;
    }

    return (
        <div className="series-page">
            <PageHeader title="Series" subtitle="Group related episode scripts together" />

            {series.length === 0 ? (
                <div className="series-empty-state">
                    <div className="series-empty-content">
                        <div className="series-empty-icon-wrapper">
                            <Layers size={28} className="series-empty-icon" />
                        </div>
                        <h2>No series yet</h2>
                        <p>Group related episodes together by assigning a series when you upload a script, or from the "Series" action on an existing script in My Scripts.</p>
                        <Link to="/upload" className="series-empty-cta">
                            <Plus size={16} />
                            Upload a Script
                        </Link>
                    </div>
                </div>
            ) : (
                <div className="series-row-list">
                    {series.map((s) => (
                        <div key={s.id} className="series-row-item">
                            <Link to={`/series/${s.id}`} className="series-row">
                                <div className="series-row-left">
                                    <span className="series-row-badge">
                                        <Layers size={16} />
                                    </span>
                                    <span className="series-row-title">{s.title}</span>
                                </div>
                                <ChevronRight size={18} className="series-row-chevron" />
                            </Link>
                            <button
                                type="button"
                                className="series-row-delete"
                                onClick={() => handleDelete(s)}
                                disabled={deletingId === s.id}
                                aria-label={`Delete series ${s.title}`}
                                title="Delete series"
                            >
                                <Trash2 size={16} />
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
