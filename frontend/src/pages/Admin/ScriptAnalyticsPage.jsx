import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  FileText, 
  Users, 
  MapPin,
  TrendingUp,
  Activity,
  AlertCircle,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { getScriptAnalytics } from '../../services/apiService';
import MetricCard from '../../components/admin/MetricCard';
import './ScriptAnalyticsPage.css';

/**
 * Script Analytics Page - Comprehensive script performance metrics
 * Route: /admin/scripts
 */
export default function ScriptAnalyticsPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [sortField, setSortField] = useState('scene_count');
  const [sortDirection, setSortDirection] = useState('desc');

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getScriptAnalytics();
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.error || 'Failed to load script analytics');
      }
    } catch (err) {
      console.error('Failed to load script analytics:', err);
      setError(err.message || 'Failed to load script analytics');
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const getSortedScripts = () => {
    if (!data?.all_scripts) return [];
    
    const scripts = [...data.all_scripts];
    scripts.sort((a, b) => {
      const aVal = a[sortField] || 0;
      const bVal = b[sortField] || 0;
      
      if (sortDirection === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });
    
    return scripts;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="script-analytics-page">
        <div className="page-header">
          <button onClick={() => navigate('/admin')} className="back-button">
            <ArrowLeft size={20} />
          </button>
          <h1>Script Analytics</h1>
        </div>
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading script analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="script-analytics-page">
        <div className="page-header">
          <button onClick={() => navigate('/admin')} className="back-button">
            <ArrowLeft size={20} />
          </button>
          <h1>Script Analytics</h1>
        </div>
        <div className="error-state">
          <AlertCircle size={48} />
          <h2>Failed to Load Analytics</h2>
          <p>{error}</p>
          <button onClick={loadAnalytics} className="btn-primary">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const { overview, scene_distribution, performance } = data || {};
  
  // Format duration for display
  const formatDuration = (seconds) => {
    if (!seconds || seconds === 0) return 'N/A';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${minutes}m ${secs}s`;
  };
  
  // Prepare chart data
  const intExtData = [
    { name: 'Interior', value: scene_distribution?.int_scenes || 0, color: '#6366f1' },
    { name: 'Exterior', value: scene_distribution?.ext_scenes || 0, color: '#10b981' }
  ];

  const dayNightData = [
    { name: 'Day', value: scene_distribution?.day_scenes || 0, color: '#f59e0b' },
    { name: 'Night', value: scene_distribution?.night_scenes || 0, color: '#8b5cf6' }
  ];

  const sortedScripts = getSortedScripts();

  return (
    <div className="script-analytics-page">
      {/* Header */}
      <div className="page-header">
        <button onClick={() => navigate('/admin')} className="back-button">
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1>Script Analytics</h1>
          <p className="subtitle">Performance metrics and insights</p>
        </div>
        <button onClick={loadAnalytics} className="btn-secondary">
          Refresh
        </button>
      </div>

      {/* Overview Cards */}
      <section className="metrics-section">
        <h2 className="section-title">
          <TrendingUp size={20} />
          Overview
        </h2>
        <div className="metrics-grid">
          <MetricCard
            title="Total Scripts"
            value={overview?.total_scripts || 0}
            icon={<FileText size={24} />}
            trend={`${overview?.total_scenes || 0} total scenes`}
            color="indigo"
          />
          <MetricCard
            title="Avg Scenes/Script"
            value={overview?.avg_scenes_per_script || 0}
            icon={<TrendingUp size={24} />}
            trend="Per script average"
            color="blue"
          />
          <MetricCard
            title="Total Characters"
            value={overview?.total_characters || 0}
            icon={<Users size={24} />}
            trend={`${overview?.avg_characters_per_script || 0} avg per script`}
            color="purple"
          />
          <MetricCard
            title="Total Locations"
            value={overview?.total_locations || 0}
            icon={<MapPin size={24} />}
            trend="Unique settings"
            color="green"
          />
        </div>
      </section>

      {/* Performance Metrics */}
      <section className="metrics-section">
        <h2 className="section-title">
          <Activity size={20} />
          Analysis Performance
        </h2>
        <div className="metrics-grid">
          <MetricCard
            title="Avg Analysis Time"
            value={formatDuration(performance?.avg_analysis_time)}
            icon={<Activity size={24} />}
            trend={`Fastest: ${formatDuration(performance?.fastest_analysis)}`}
            color="blue"
          />
          <MetricCard
            title="Success Rate"
            value={`${performance?.success_rate || 0}%`}
            icon={<TrendingUp size={24} />}
            trend={`${performance?.successful_analyses || 0} of ${performance?.total_analyses || 0} scripts`}
            color="green"
          />
          <MetricCard
            title="Total Processed"
            value={performance?.total_analyses || 0}
            icon={<FileText size={24} />}
            trend={`Slowest: ${formatDuration(performance?.slowest_analysis)}`}
            color="purple"
          />
        </div>
      </section>

      {/* Charts Section */}
      <section className="charts-section">
        <h2 className="section-title">Scene Distribution</h2>
        <div className="charts-grid-small">
          {/* INT/EXT Chart */}
          <div className="chart-container">
            <div className="chart-header">
              <h3>Interior vs Exterior</h3>
            </div>
            <div className="chart-body">
              {(intExtData[0].value + intExtData[1].value) > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={intExtData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {intExtData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ 
                        background: 'rgba(0,0,0,0.9)', 
                        border: '1px solid rgba(255,255,255,0.2)',
                        borderRadius: '8px',
                        color: '#fff'
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="chart-empty">
                  <p>No data available</p>
                </div>
              )}
            </div>
          </div>

          {/* Day/Night Chart */}
          <div className="chart-container">
            <div className="chart-header">
              <h3>Day vs Night</h3>
            </div>
            <div className="chart-body">
              {(dayNightData[0].value + dayNightData[1].value) > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={dayNightData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {dayNightData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ 
                        background: 'rgba(0,0,0,0.9)', 
                        border: '1px solid rgba(255,255,255,0.2)',
                        borderRadius: '8px',
                        color: '#fff'
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="chart-empty">
                  <p>No data available</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Scripts Table */}
      <section className="table-section">
        <h2 className="section-title">All Scripts</h2>
        <div className="table-container">
          <table className="scripts-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('title')} className="sortable">
                  Title
                  {sortField === 'title' && (
                    sortDirection === 'asc' ? <ChevronUp size={16} /> : <ChevronDown size={16} />
                  )}
                </th>
                <th onClick={() => handleSort('user_name')} className="sortable">
                  Owner
                  {sortField === 'user_name' && (
                    sortDirection === 'asc' ? <ChevronUp size={16} /> : <ChevronDown size={16} />
                  )}
                </th>
                <th onClick={() => handleSort('scene_count')} className="sortable">
                  Scenes
                  {sortField === 'scene_count' && (
                    sortDirection === 'asc' ? <ChevronUp size={16} /> : <ChevronDown size={16} />
                  )}
                </th>
                <th onClick={() => handleSort('character_count')} className="sortable">
                  Characters
                  {sortField === 'character_count' && (
                    sortDirection === 'asc' ? <ChevronUp size={16} /> : <ChevronDown size={16} />
                  )}
                </th>
                <th onClick={() => handleSort('location_count')} className="sortable">
                  Locations
                  {sortField === 'location_count' && (
                    sortDirection === 'asc' ? <ChevronUp size={16} /> : <ChevronDown size={16} />
                  )}
                </th>
                <th onClick={() => handleSort('analysis_duration')} className="sortable">
                  Analysis Time
                  {sortField === 'analysis_duration' && (
                    sortDirection === 'asc' ? <ChevronUp size={16} /> : <ChevronDown size={16} />
                  )}
                </th>
                <th onClick={() => handleSort('uploaded_at')} className="sortable">
                  Uploaded
                  {sortField === 'uploaded_at' && (
                    sortDirection === 'asc' ? <ChevronUp size={16} /> : <ChevronDown size={16} />
                  )}
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedScripts.map((script) => {
                const duration = script.analysis_duration;
                let durationClass = 'duration-cell';
                if (duration) {
                  if (duration < 120) durationClass += ' duration-fast';
                  else if (duration < 300) durationClass += ' duration-medium';
                  else durationClass += ' duration-slow';
                }
                
                return (
                  <tr key={script.id}>
                    <td className="script-title">{script.title}</td>
                    <td>{script.user_name}</td>
                    <td className="number-cell">{script.scene_count}</td>
                    <td className="number-cell">{script.character_count}</td>
                    <td className="number-cell">{script.location_count}</td>
                    <td className={durationClass}>{formatDuration(duration)}</td>
                    <td className="date-cell">{formatDate(script.uploaded_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {sortedScripts.length === 0 && (
            <div className="empty-state">
              <FileText size={48} />
              <h3>No Scripts Found</h3>
              <p>Upload a script to see analytics</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
