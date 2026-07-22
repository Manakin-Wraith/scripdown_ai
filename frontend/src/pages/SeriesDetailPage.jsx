import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Layers, ChevronRight } from 'lucide-react';
import { listSeries, listSeasons } from '../services/apiService';
import PageHeader from '../components/layout/PageHeader';
import { Spinner } from '../components/ui';
import './SeriesPages.css';

export default function SeriesDetailPage() {
    const { seriesId } = useParams();
    const [series, setSeries] = useState(null);
    const [seasons, setSeasons] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

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
            <PageHeader title={series?.title || 'Series'} subtitle="Seasons" />

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
                        <Link
                            key={season.id}
                            to={`/series/${seriesId}/seasons/${season.id}`}
                            className="series-row"
                        >
                            <div className="series-row-left">
                                <span className="series-row-badge">
                                    <span className="series-row-num">{season.season_number}</span>
                                </span>
                                <span className="series-row-title">
                                    {season.title || `Season ${season.season_number}`}
                                </span>
                            </div>
                            <ChevronRight size={18} className="series-row-chevron" />
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}
