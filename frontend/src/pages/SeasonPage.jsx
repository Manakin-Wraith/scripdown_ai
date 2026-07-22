import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { listSeasons, listEpisodes, getSeasonCast } from '../services/apiService';
import PageHeader from '../components/layout/PageHeader';
import { Spinner } from '../components/ui';

export default function SeasonPage() {
    const { seriesId, seasonId } = useParams();
    const [season, setSeason] = useState(null);
    const [episodes, setEpisodes] = useState([]);
    const [cast, setCast] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        Promise.all([
            listSeasons(seriesId),
            listEpisodes(seasonId),
            getSeasonCast(seasonId),
        ])
            .then(([seasonsData, episodesData, castData]) => {
                const match = (seasonsData.seasons || []).find((s) => s.id === seasonId);
                setSeason(match || null);
                setEpisodes(episodesData.episodes || []);
                setCast(castData.cast || []);
            })
            .catch((err) => setError(err.message || 'Failed to load season'))
            .finally(() => setLoading(false));
    }, [seriesId, seasonId]);

    if (loading) return <Spinner size={32} />;
    if (error) return <p className="season-page-error">{error}</p>;

    return (
        <div className="season-page">
            <PageHeader
                title={season?.title || `Season ${season?.season_number ?? ''}`}
                subtitle={`${episodes.length} episode${episodes.length === 1 ? '' : 's'}`}
            />

            <section className="season-episodes">
                <h2>Episodes</h2>
                <ol>
                    {episodes.map((ep) => (
                        <li key={ep.id}>
                            <Link to={`/scenes/${ep.id}`}>
                                Episode {ep.episode_number}: {ep.title}
                            </Link>
                        </li>
                    ))}
                </ol>
            </section>

            <section className="season-cast">
                <h2>Combined Cast</h2>
                <table>
                    <thead>
                        <tr><th>Character</th><th>Appears In</th></tr>
                    </thead>
                    <tbody>
                        {cast.map((row) => (
                            <tr key={row.name}>
                                <td>{row.name}</td>
                                <td>{row.episodes.join(', ')}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </section>
        </div>
    );
}
