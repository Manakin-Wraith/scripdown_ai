import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { listSeries, listSeasons } from '../services/apiService';
import PageHeader from '../components/layout/PageHeader';
import { Spinner } from '../components/ui';

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

    if (loading) return <Spinner size={32} />;
    if (error) return <p className="series-detail-error">{error}</p>;

    return (
        <div className="series-detail-page">
            <PageHeader title={series?.title || 'Series'} subtitle="Seasons" />

            {seasons.length === 0 && (
                <p>No seasons yet for this series.</p>
            )}

            <ul className="series-detail-seasons">
                {seasons.map((season) => (
                    <li key={season.id}>
                        <Link to={`/series/${seriesId}/seasons/${season.id}`}>
                            {season.title || `Season ${season.season_number}`}
                        </Link>
                    </li>
                ))}
            </ul>
        </div>
    );
}
