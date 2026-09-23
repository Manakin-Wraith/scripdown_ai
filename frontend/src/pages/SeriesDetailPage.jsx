import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Layers, ChevronRight, Trash2 } from 'lucide-react';
import { listSeries, listSeasons, deleteSeries, deleteSeason } from '../services/apiService';
import { useConfirmDialog } from '../context/ConfirmDialogContext';
import { useToast } from '../context/ToastContext';
import PageHeader from '../components/layout/PageHeader';
import { Button, Spinner } from '../components/ui';
import './SeriesPages.css';

export default function SeriesDetailPage() {
    const { seriesId } = useParams();
    const [series, setSeries] = useState(null);
    const [seasons, setSeasons] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [deletingId, setDeletingId] = useState(null);
    const navigate = useNavigate();
    const { confirm } = useConfirmDialog();
    const toast = useToast();

    useEffect(() => {
        Promise.all([
            listSeries(),
            listSeasons(seriesId),
        ])
            .then(([seriesData, seasonsData]) => {
                const match = (seriesData.series || []).find((s) => s.id === seriesId);
                setSeries(match || null);
                setSeasons(seasonsData.seasons || []);
            })
            .catch((err) => setError(err.message || 'Failed to load series'))
            .finally(() => setLoading(false));
    }, [seriesId]);

    // `series` is only found when the caller owns it (listSeries is
    // owner-scoped), so it doubles as the gate for the delete actions.
    const seasonLabel = (season) => season.title || `Season ${season.season_number}`;

    const handleDeleteSeries = async () => {
        const title = series?.title || 'this series';
        const seasonCount = `${seasons.length} season${seasons.length === 1 ? '' : 's'}`;
        const confirmed = await confirm({
            title: `Delete "${title}"?`,
            message: `Its ${seasonCount} will be removed. Episode scripts are not deleted — they stay in My Scripts as standalone scripts.`,
            variant: 'danger',
        });
        if (!confirmed) return;

        setDeletingId(seriesId);
        try {
            await deleteSeries(seriesId);
            toast.success('Series deleted', `"${title}" was removed.`);
            navigate('/series');
        } catch (err) {
            toast.error('Could not delete series', err.response?.data?.error || err.message);
            setDeletingId(null);
        }
    };

    const handleDeleteSeason = async (season) => {
        const confirmed = await confirm({
            title: `Delete ${seasonLabel(season)}?`,
            message: 'Episode scripts in this season are not deleted — they stay in My Scripts as standalone scripts.',
            variant: 'danger',
        });
        if (!confirmed) return;

        setDeletingId(season.id);
        try {
            await deleteSeason(season.id);
            setSeasons((prev) => prev.filter((item) => item.id !== season.id));
            toast.success('Season deleted', `${seasonLabel(season)} was removed.`);
        } catch (err) {
            toast.error('Could not delete season', err.response?.data?.error || err.message);
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
            <PageHeader
                title={series?.title || 'Series'}
                subtitle="Seasons"
                actions={series && (
                    <Button
                        variant="secondary"
                        size="sm"
                        icon={Trash2}
                        onClick={handleDeleteSeries}
                        loading={deletingId === seriesId}
                    >
                        Delete series
                    </Button>
                )}
            />

            {seasons.length === 0 ? (
                <div className="series-empty-state">
                    <div className="series-empty-content">
                        <div className="series-empty-icon-wrapper">
                            <Layers size={28} className="series-empty-icon" />
                        </div>
                        <h2>No seasons yet</h2>
                        <p>This series doesn't have any seasons yet. Assign an episode to it from My Scripts to create one.</p>
                        <Link to="/series" className="series-empty-cta">
                            Back to Series
                        </Link>
                    </div>
                </div>
            ) : (
                <div className="series-row-list">
                    {seasons.map((season) => (
                        <div key={season.id} className="series-row-item">
                            <Link
                                to={`/series/${seriesId}/seasons/${season.id}`}
                                className="series-row"
                            >
                                <div className="series-row-left">
                                    <span className="series-row-badge">
                                        <span className="series-row-num">{season.season_number}</span>
                                    </span>
                                    <span className="series-row-title">{seasonLabel(season)}</span>
                                </div>
                                <ChevronRight size={18} className="series-row-chevron" />
                            </Link>
                            {series && (
                                <button
                                    type="button"
                                    className="series-row-delete"
                                    onClick={() => handleDeleteSeason(season)}
                                    disabled={deletingId === season.id}
                                    aria-label={`Delete ${seasonLabel(season)}`}
                                    title="Delete season"
                                >
                                    <Trash2 size={16} />
                                </button>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
