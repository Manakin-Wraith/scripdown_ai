import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listSeries } from '../services/apiService';
import PageHeader from '../components/layout/PageHeader';
import { Spinner } from '../components/ui';

export default function SeriesListPage() {
    const [series, setSeries] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        listSeries()
            .then((data) => setSeries(data.series || []))
            .catch((err) => setError(err.message || 'Failed to load series'))
            .finally(() => setLoading(false));
    }, []);

    return (
        <div className="series-list-page">
            <PageHeader title="Series" subtitle="Group related episode scripts together" />
            {loading && <Spinner size={32} />}
            {error && <p className="series-list-error">{error}</p>}
            {!loading && !error && series.length === 0 && (
                <p>No series yet. Create one from the upload page.</p>
            )}
            <ul className="series-list">
                {series.map((s) => (
                    <li key={s.id}>
                        <Link to={`/series/${s.id}`}>{s.title}</Link>
                    </li>
                ))}
            </ul>
        </div>
    );
}
