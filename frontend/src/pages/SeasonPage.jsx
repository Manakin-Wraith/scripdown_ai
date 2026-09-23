import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Film, ChevronRight, Trash2 } from 'lucide-react';
import { listSeries, listSeasons, listEpisodes, getSeasonCast, deleteSeason } from '../services/apiService';
import { useConfirmDialog } from '../context/ConfirmDialogContext';
import { useToast } from '../context/ToastContext';
import PageHeader from '../components/layout/PageHeader';
import { Button, Spinner } from '../components/ui';
import './SeriesPages.css';

export default function SeasonPage() {
    const { seriesId, seasonId } = useParams();
    const [season, setSeason] = useState(null);
    const [episodes, setEpisodes] = useState([]);
    const [cast, setCast] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [deleting, setDeleting] = useState(false);
    // Only the series owner can delete; team members reach this page via
    // shared episode access. listSeries is owner-scoped, so a match = owner.
    const [isOwner, setIsOwner] = useState(false);
    const navigate = useNavigate();
    const { confirm } = useConfirmDialog();
    const toast = useToast();

    useEffect(() => {
        Promise.all([
            listSeries(),
            listSeasons(seriesId),
            listEpisodes(seasonId),
            getSeasonCast(seasonId),
        ])
            .then(([seriesData, seasonsData, episodesData, castData]) => {
                setIsOwner((seriesData.series || []).some((s) => s.id === seriesId));
                const match = (seasonsData.seasons || []).find((s) => s.id === seasonId);
                setSeason(match || null);
                setEpisodes(episodesData.episodes || []);
                setCast(castData.cast || []);
            })
            .catch((err) => setError(err.message || 'Failed to load season'))
            .finally(() => setLoading(false));
    }, [seriesId, seasonId]);

    const handleDelete = async () => {
        const label = season?.title || `Season ${season?.season_number ?? ''}`;
        const episodeCount = `${episodes.length} episode script${episodes.length === 1 ? '' : 's'}`;
        const confirmed = await confirm({
            title: `Delete ${label}?`,
            message: `The ${episodeCount} in this season will not be deleted — they stay in My Scripts as standalone scripts.`,
            variant: 'danger',
        });
        if (!confirmed) return;

        setDeleting(true);
        try {
            await deleteSeason(seasonId);
            toast.success('Season deleted', `${label} was removed.`);
            navigate(`/series/${seriesId}`);
        } catch (err) {
            toast.error('Could not delete season', err.response?.data?.error || err.message);
            setDeleting(false);
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
                title={season?.title || `Season ${season?.season_number ?? ''}`}
                subtitle={`${episodes.length} episode${episodes.length === 1 ? '' : 's'}`}
                actions={season && isOwner && (
                    <Button
                        variant="secondary"
                        size="sm"
                        icon={Trash2}
                        onClick={handleDelete}
                        loading={deleting}
                    >
                        Delete season
                    </Button>
                )}
            />

            <section>
                <h2 className="series-section-title">Episodes</h2>
                {episodes.length === 0 ? (
                    <div className="series-empty-state">
                        <div className="series-empty-content">
                            <div className="series-empty-icon-wrapper">
                                <Film size={28} className="series-empty-icon" />
                            </div>
                            <h2>No episodes yet</h2>
                            <p>Assign a script to this season from My Scripts to see it here.</p>
                        </div>
                    </div>
                ) : (
                    <div className="series-row-list">
                        {episodes.map((ep) => (
                            <Link key={ep.id} to={`/scenes/${ep.id}`} className="series-row">
                                <div className="series-row-left">
                                    <span className="series-row-badge">
                                        <span className="series-row-num">{ep.episode_number}</span>
                                    </span>
                                    <span className="series-row-title">{ep.title}</span>
                                </div>
                                <ChevronRight size={18} className="series-row-chevron" />
                            </Link>
                        ))}
                    </div>
                )}
            </section>

            <section>
                <h2 className="series-section-title">Combined Cast</h2>
                {cast.length === 0 ? (
                    <p className="series-row-meta">
                        No cast data yet — run AI analysis on this season's episodes to see characters here.
                    </p>
                ) : (
                    <table className="series-cast-table">
                        <thead>
                            <tr><th>Character</th><th>Appears In</th></tr>
                        </thead>
                        <tbody>
                            {cast.map((row) => (
                                <tr key={row.name}>
                                    <td>{row.name}</td>
                                    <td>
                                        {row.episodes.map((title) => (
                                            <span key={title} className="series-episode-tag">{title}</span>
                                        ))}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </section>
        </div>
    );
}
