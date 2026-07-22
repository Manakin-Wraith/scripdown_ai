import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Layers, ChevronRight, Plus } from 'lucide-react';
import { listSeries } from '../services/apiService';
import PageHeader from '../components/layout/PageHeader';
import { Spinner } from '../components/ui';
import './SeriesPages.css';

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
                        <Link key={s.id} to={`/series/${s.id}`} className="series-row">
                            <div className="series-row-left">
                                <span className="series-row-badge">
                                    <Layers size={16} />
                                </span>
                                <span className="series-row-title">{s.title}</span>
                            </div>
                            <ChevronRight size={18} className="series-row-chevron" />
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}
