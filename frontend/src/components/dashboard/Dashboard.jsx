import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getStats } from '../../services/apiService';
import { Plus, FileText, Film, CheckCircle2, Clock } from 'lucide-react';
import ScriptTable from '../scripts/ScriptTable';
import EmptyLibrary from '../scripts/EmptyLibrary';
import { SubscriptionBanner } from '../subscription';
import { useSubscription } from '../../hooks/useSubscription';
import './Dashboard.css';

const Dashboard = () => {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        fetchStats();
    }, []);

    const fetchStats = async () => {
        try {
            setLoading(true);
            const data = await getStats();
            setStats(data);
            setError('');
        } catch (err) {
            console.error('Failed to fetch stats:', err);
            setError('Failed to load dashboard');
        } finally {
            setLoading(false);
        }
    };

    const handleViewScript = (scriptId) => {
        navigate(`/scenes/${scriptId}`);
    };

    // Dashboard doesn't support delete/reanalyze directly yet, passing dummy handlers
    // or we could navigate to Library
    const handleNavigateToLibrary = () => navigate('/scripts');

    if (loading) {
        return (
            <div className="dashboard-container">
                <div className="loading">
                    <div className="spinner"></div>
                    <p>Loading dashboard...</p>
                </div>
            </div>
        );
    }

    const hasScripts = stats && stats.total_scripts > 0;

    return (
        <div className="dashboard-container">
            <SubscriptionBanner />
            
            <div className="dashboard-header">
                <h1>Welcome back! 👋</h1>
                <p className="dashboard-subtitle">
                    {hasScripts
                        ? 'Here\'s an overview of your script breakdowns'
                        : 'Get started by uploading your first script'}
                </p>
            </div>

            {error && <div className="error-message">{error}</div>}

            {hasScripts ? (
                <>
                    {/* Quick Stats */}
                    <div className="stats-section">
                        <h2 className="section-title">📊 Quick Stats</h2>
                        <div className="stats-grid">
                            <div className="stat-card">
                                <div className="stat-icon"><FileText size={24} /></div>
                                <div className="stat-value">{stats.total_scripts}</div>
                                <div className="stat-label">Total Scripts</div>
                            </div>

                            <div className="stat-card">
                                <div className="stat-icon"><Film size={24} /></div>
                                <div className="stat-value">{stats.total_scenes}</div>
                                <div className="stat-label">Scenes Analyzed</div>
                            </div>

                            <div className="stat-card">
                                <div className="stat-icon"><CheckCircle2 size={24} /></div>
                                <div className="stat-value">{stats.analyzed_scripts}</div>
                                <div className="stat-label">Completed</div>
                            </div>

                            <div className="stat-card">
                                <div className="stat-icon"><Clock size={24} /></div>
                                <div className="stat-value">{stats.pending_scripts}</div>
                                <div className="stat-label">Pending</div>
                            </div>
                        </div>
                    </div>

                    {/* Recent Scripts */}
                    {stats.recent_scripts && stats.recent_scripts.length > 0 && (
                        <div className="recent-section">
                            <div className="section-header">
                                <h2 className="section-title">📝 Recent Scripts</h2>
                                <button
                                    className="view-all-btn"
                                    onClick={handleNavigateToLibrary}
                                >
                                    View All →
                                </button>
                            </div>

                            {/* Reuse ScriptTable for consistent look, but simplified props */}
                            <ScriptTable 
                                scripts={stats.recent_scripts}
                                onView={handleViewScript}
                                onReanalyze={() => handleNavigateToLibrary()} 
                                onDelete={() => handleNavigateToLibrary()}
                                reanalyzingId={null}
                            />
                        </div>
                    )}

                    {/* Quick Actions */}
                    <div className="actions-section">
                        <h2 className="section-title">🚀 Quick Actions</h2>
                        <div className="actions-grid">
                            <button
                                className="action-card primary"
                                onClick={() => navigate('/upload')}
                            >
                                <Plus size={24} />
                                <span className="action-label">Upload New Script</span>
                            </button>

                            <button
                                className="action-card secondary"
                                onClick={() => navigate('/scripts')}
                            >
                                <FileText size={24} />
                                <span className="action-label">View All Scripts</span>
                            </button>
                        </div>
                    </div>
                </>
            ) : (
                <EmptyLibrary />
            )}
        </div>
    );
};

export default Dashboard;
