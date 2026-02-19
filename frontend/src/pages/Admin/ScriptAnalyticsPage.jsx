import { useState, useEffect, useMemo, Fragment } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  FileText, 
  Users, 
  MapPin,
  TrendingUp,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  BookOpen,
  Cpu,
  BarChart3,
  Calendar,
  Layers,
  Sun,
  Lock,
  Pen,
  MessageSquare,
  CalendarDays,
  Zap
} from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, Legend 
} from 'recharts';
import { getScriptAnalytics } from '../../services/apiService';
import MetricCard from '../../components/admin/MetricCard';
import './ScriptAnalyticsPage.css';

const FEATURE_META = {
  reports:      { label: 'Reports',      icon: FileText,     color: '#6366f1' },
  dept_items:   { label: 'Dept Items',   icon: Layers,       color: '#8b5cf6' },
  dept_notes:   { label: 'Notes',        icon: Pen,          color: '#a78bfa' },
  schedules:    { label: 'Schedules',    icon: CalendarDays,  color: '#f59e0b' },
  team_members: { label: 'Team',         icon: Users,        color: '#10b981' },
  extractions:  { label: 'Extractions',  icon: Zap,          color: '#ec4899' },
  threads:      { label: 'Threads',      icon: MessageSquare, color: '#06b6d4' },
};

const TOOLTIP_STYLE = {
  background: 'rgba(15,20,25,0.95)',
  border: '1px solid rgba(255,255,255,0.15)',
  borderRadius: '8px',
  color: '#fff',
  fontSize: '0.8125rem',
};

/**
 * Script Analytics Page - Comprehensive script performance metrics
 * Route: /admin/scripts
 */
export default function ScriptAnalyticsPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [sortField, setSortField] = useState('uploaded_at');
  const [sortDirection, setSortDirection] = useState('desc');
  const [expandedScript, setExpandedScript] = useState(null);

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
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedScripts = useMemo(() => {
    if (!data?.all_scripts) return [];
    const scripts = [...data.all_scripts];
    scripts.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();
      aVal = aVal ?? '';
      bVal = bVal ?? '';
      if (sortDirection === 'asc') return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
      return aVal < bVal ? 1 : aVal > bVal ? -1 : 0;
    });
    return scripts;
  }, [data, sortField, sortDirection]);

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-ZA', { 
      day: 'numeric', month: 'short', year: 'numeric' 
    });
  };

  // ── Loading / Error ──
  if (loading) {
    return (
      <div className="sa-page">
        <div className="sa-header">
          <button onClick={() => navigate('/admin')} className="sa-back"><ArrowLeft size={20} /></button>
          <h1>Script Analytics</h1>
        </div>
        <div className="sa-loading"><div className="sa-spinner" /><p>Loading analytics...</p></div>
      </div>
    );
  }
  if (error) {
    return (
      <div className="sa-page">
        <div className="sa-header">
          <button onClick={() => navigate('/admin')} className="sa-back"><ArrowLeft size={20} /></button>
          <h1>Script Analytics</h1>
        </div>
        <div className="sa-error">
          <AlertCircle size={48} />
          <h2>Failed to Load</h2>
          <p>{error}</p>
          <button onClick={loadAnalytics} className="sa-btn-primary">Try Again</button>
        </div>
      </div>
    );
  }

  const { overview = {}, scene_distribution = {}, parser_quality = {}, 
          upload_timeline = [], feature_adoption = {}, all_scripts = [] } = data || {};

  // ── Chart data ──
  const intExtData = [
    { name: 'INT', value: scene_distribution.int_scenes || 0, color: '#6366f1' },
    { name: 'EXT', value: scene_distribution.ext_scenes || 0, color: '#10b981' },
    { name: 'INT/EXT', value: scene_distribution.int_ext_scenes || 0, color: '#f59e0b' },
  ].filter(d => d.value > 0);

  const timeData = [
    { name: 'Day', value: scene_distribution.day_scenes || 0, color: '#fbbf24' },
    { name: 'Night', value: scene_distribution.night_scenes || 0, color: '#8b5cf6' },
    { name: 'Other', value: scene_distribution.other_time_scenes || 0, color: '#64748b' },
  ].filter(d => d.value > 0);

  const parserBarData = all_scripts
    .filter(s => s.scene_count > 0)
    .sort((a, b) => b.scene_count - a.scene_count)
    .map(s => ({
      name: s.title.length > 20 ? s.title.slice(0, 18) + '…' : s.title,
      grammar: s.grammar_scenes,
      regex: s.regex_scenes,
    }));

  const timelineBarData = upload_timeline.map(t => ({
    date: new Date(t.date).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' }),
    scripts: t.count,
    pages: t.pages,
  }));

  const scriptSizeData = all_scripts
    .filter(s => s.total_pages > 0)
    .sort((a, b) => b.total_pages - a.total_pages)
    .map(s => ({
      name: s.title.length > 22 ? s.title.slice(0, 20) + '…' : s.title,
      pages: s.total_pages,
      scenes: s.scene_count,
    }));

  const SortIcon = ({ field }) => {
    if (sortField !== field) return null;
    return <ChevronDown size={14} className={`sa-sort-icon ${sortDirection === 'asc' ? 'sa-sort-asc' : ''}`} />;
  };

  const renderDonutLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, name, value }) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    return (
      <text x={x} y={y} fill="#fff" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={600}>
        {value}
      </text>
    );
  };

  return (
    <div className="sa-page">
      {/* ── Header ── */}
      <div className="sa-header">
        <button onClick={() => navigate('/admin')} className="sa-back"><ArrowLeft size={20} /></button>
        <div className="sa-header-text">
          <h1>Script Analytics</h1>
          <p>Platform-wide script intelligence &amp; feature adoption</p>
        </div>
        <button onClick={loadAnalytics} className="sa-btn-refresh"><RefreshCw size={16} /> Refresh</button>
      </div>

      {/* ── Hero Metrics ── */}
      <section className="sa-hero">
        <MetricCard title="Total Scripts" value={overview.total_scripts || 0} icon={<FileText size={22} />} 
          trend={`${overview.scripts_this_month || 0} this month`} color="indigo" />
        <MetricCard title="Total Pages" value={(overview.total_pages || 0).toLocaleString()} icon={<BookOpen size={22} />} 
          trend={`Avg ${overview.avg_pages_per_script || 0} per script`} color="blue" />
        <MetricCard title="Scenes Detected" value={(overview.total_scenes || 0).toLocaleString()} icon={<Layers size={22} />} 
          trend={`Avg ${overview.avg_scenes_per_script || 0} per script`} color="purple" />
        <MetricCard title="Unique Uploaders" value={overview.unique_uploaders || 0} icon={<Users size={22} />} 
          trend="Distinct users" color="green" />
        <MetricCard title="ScreenPy Rate" value={`${overview.grammar_parse_rate || 0}%`} icon={<Cpu size={22} />} 
          trend={`${parser_quality.total_grammar || 0} grammar scenes`} color="emerald" />
        <MetricCard title="Characters" value={(overview.total_characters || 0).toLocaleString()} icon={<Users size={22} />} 
          trend={`${overview.total_locations || 0} locations`} color="orange" />
      </section>

      {/* ── Upload Timeline ── */}
      {timelineBarData.length > 0 && (
        <section className="sa-card">
          <div className="sa-card-header">
            <Calendar size={18} />
            <h2>Upload Activity</h2>
            <span className="sa-card-badge">{upload_timeline.length} days</span>
          </div>
          <div className="sa-chart-body" style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={timelineBarData} barSize={28}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }} />
                <YAxis tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }} allowDecimals={false} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Bar dataKey="scripts" fill="#6366f1" radius={[4,4,0,0]} name="Scripts" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {/* ── Charts Row ── */}
      <div className="sa-charts-row">
        {/* Scene Composition: INT/EXT */}
        <section className="sa-card sa-card-half">
          <div className="sa-card-header">
            <MapPin size={18} />
            <h2>INT / EXT</h2>
          </div>
          <div className="sa-chart-body" style={{ height: 240 }}>
            {intExtData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={intExtData} cx="50%" cy="50%" innerRadius={50} outerRadius={85}
                    dataKey="value" label={renderDonutLabel} labelLine={false}>
                    {intExtData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                  </Pie>
                  <Legend verticalAlign="bottom" iconType="circle" 
                    formatter={(val) => <span style={{ color: 'rgba(255,255,255,0.8)', fontSize: 12 }}>{val}</span>} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                </PieChart>
              </ResponsiveContainer>
            ) : <div className="sa-chart-empty">No scene data</div>}
          </div>
        </section>

        {/* Scene Composition: Time of Day */}
        <section className="sa-card sa-card-half">
          <div className="sa-card-header">
            <Sun size={18} />
            <h2>Time of Day</h2>
          </div>
          <div className="sa-chart-body" style={{ height: 240 }}>
            {timeData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={timeData} cx="50%" cy="50%" innerRadius={50} outerRadius={85}
                    dataKey="value" label={renderDonutLabel} labelLine={false}>
                    {timeData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                  </Pie>
                  <Legend verticalAlign="bottom" iconType="circle" 
                    formatter={(val) => <span style={{ color: 'rgba(255,255,255,0.8)', fontSize: 12 }}>{val}</span>} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                </PieChart>
              </ResponsiveContainer>
            ) : <div className="sa-chart-empty">No scene data</div>}
          </div>
        </section>
      </div>

      {/* ── Parser Quality per Script ── */}
      {parserBarData.length > 0 && (
        <section className="sa-card">
          <div className="sa-card-header">
            <Cpu size={18} />
            <h2>Parser Quality by Script</h2>
            <span className="sa-card-badge screenpy">{overview.grammar_parse_rate || 0}% ScreenPy</span>
          </div>
          <div className="sa-chart-body" style={{ height: Math.max(200, parserBarData.length * 32 + 40) }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={parserBarData} layout="vertical" barSize={18}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis type="number" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }} allowDecimals={false} />
                <YAxis type="category" dataKey="name" tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 11 }} width={160} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Bar dataKey="grammar" stackId="a" fill="#10b981" name="ScreenPy Grammar" radius={[0,0,0,0]} />
                <Bar dataKey="regex" stackId="a" fill="#64748b" name="Regex Fallback" radius={[0,4,4,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {/* ── Script Size Distribution ── */}
      {scriptSizeData.length > 0 && (
        <section className="sa-card">
          <div className="sa-card-header">
            <BarChart3 size={18} />
            <h2>Script Size Distribution</h2>
            <span className="sa-card-badge">{overview.total_pages || 0} total pages</span>
          </div>
          <div className="sa-chart-body" style={{ height: Math.max(200, scriptSizeData.length * 32 + 40) }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={scriptSizeData} layout="vertical" barSize={18}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis type="number" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }} allowDecimals={false} />
                <YAxis type="category" dataKey="name" tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 11 }} width={160} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Bar dataKey="pages" fill="#6366f1" name="Pages" radius={[0,4,4,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {/* ── Feature Adoption ── */}
      <section className="sa-card">
        <div className="sa-card-header">
          <TrendingUp size={18} />
          <h2>Feature Adoption</h2>
        </div>
        <div className="sa-features-grid">
          {Object.entries(FEATURE_META).map(([key, meta]) => {
            const stats = feature_adoption[key] || { total_usage: 0, scripts_using: 0, adoption_rate: 0 };
            const Icon = meta.icon;
            return (
              <div key={key} className={`sa-feature-card ${stats.total_usage > 0 ? 'active' : 'inactive'}`}>
                <div className="sa-feature-icon" style={{ background: stats.total_usage > 0 ? meta.color : undefined }}>
                  <Icon size={18} />
                </div>
                <div className="sa-feature-info">
                  <span className="sa-feature-label">{meta.label}</span>
                  <span className="sa-feature-count">{stats.total_usage} uses</span>
                </div>
                <div className="sa-feature-rate">
                  <span className="sa-feature-pct">{stats.adoption_rate}%</span>
                  <span className="sa-feature-sub">{stats.scripts_using}/{overview.total_scripts || 0} scripts</span>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Scripts Table ── */}
      <section className="sa-card sa-table-section">
        <div className="sa-card-header">
          <FileText size={18} />
          <h2>All Scripts</h2>
          <span className="sa-card-badge">{all_scripts.length}</span>
        </div>
        <div className="sa-table-wrap">
          <table className="sa-table">
            <thead>
              <tr>
                <th style={{ width: 32 }}></th>
                <th onClick={() => handleSort('title')} className="sa-th-sort">Title <SortIcon field="title" /></th>
                <th onClick={() => handleSort('owner_name')} className="sa-th-sort">Owner <SortIcon field="owner_name" /></th>
                <th onClick={() => handleSort('total_pages')} className="sa-th-sort sa-th-num">Pages <SortIcon field="total_pages" /></th>
                <th onClick={() => handleSort('scene_count')} className="sa-th-sort sa-th-num">Scenes <SortIcon field="scene_count" /></th>
                <th onClick={() => handleSort('grammar_rate')} className="sa-th-sort sa-th-num">ScreenPy <SortIcon field="grammar_rate" /></th>
                <th onClick={() => handleSort('features_used')} className="sa-th-sort sa-th-num">Features <SortIcon field="features_used" /></th>
                <th onClick={() => handleSort('uploaded_at')} className="sa-th-sort">Uploaded <SortIcon field="uploaded_at" /></th>
              </tr>
            </thead>
            <tbody>
              {sortedScripts.map((script) => {
                const isExpanded = expandedScript === script.id;
                return (
                  <Fragment key={script.id}>
                    <tr className={`sa-tr ${isExpanded ? 'sa-tr-expanded' : ''}`} 
                        onClick={() => setExpandedScript(isExpanded ? null : script.id)}>
                      <td className="sa-td-expand">
                        <ChevronRight size={14} className={`sa-expand-icon ${isExpanded ? 'open' : ''}`} />
                      </td>
                      <td className="sa-td-title">
                        <span>{script.title}</span>
                        {script.is_locked && <Lock size={12} className="sa-lock-icon" />}
                      </td>
                      <td className="sa-td-owner">
                        <span className="sa-owner-name">{script.owner_name || 'Unknown'}</span>
                        <span className={`sa-sub-badge sa-sub-${script.subscription_status}`}>
                          {script.subscription_status}
                        </span>
                      </td>
                      <td className="sa-td-num">{script.total_pages || '—'}</td>
                      <td className="sa-td-num">{script.scene_count}</td>
                      <td className="sa-td-num">
                        {script.scene_count > 0 ? (
                          <span className={`sa-parser-pill ${script.grammar_rate > 0 ? 'grammar' : 'regex'}`}>
                            {script.grammar_rate > 0 ? `${script.grammar_rate}%` : 'Regex'}
                          </span>
                        ) : '—'}
                      </td>
                      <td className="sa-td-num">
                        <span className={`sa-feat-count ${script.features_used > 0 ? 'has-features' : ''}`}>
                          {script.features_used}/7
                        </span>
                      </td>
                      <td className="sa-td-date">{formatDate(script.uploaded_at)}</td>
                    </tr>
                    {isExpanded && (
                      <tr className="sa-tr-detail">
                        <td colSpan={8}>
                          <div className="sa-detail-grid">
                            {/* Metadata */}
                            <div className="sa-detail-section">
                              <h4>Metadata</h4>
                              <div className="sa-detail-pairs">
                                <span className="sa-dl">Writer</span>
                                <span className="sa-dv">{script.writer_name || '—'}</span>
                                <span className="sa-dl">Genre</span>
                                <span className="sa-dv">{script.genre || '—'}</span>
                                <span className="sa-dl">Story Days</span>
                                <span className="sa-dv">{script.story_days || '—'}</span>
                                <span className="sa-dl">Owner Email</span>
                                <span className="sa-dv">{script.owner_email || '—'}</span>
                                <span className="sa-dl">Revision</span>
                                <span className="sa-dv" style={{ textTransform: 'capitalize' }}>
                                  {script.revision_color || 'white'}
                                </span>
                              </div>
                            </div>
                            {/* Scene Composition */}
                            <div className="sa-detail-section">
                              <h4>Scene Composition</h4>
                              <div className="sa-comp-bars">
                                <div className="sa-comp-row">
                                  <span className="sa-comp-label">INT</span>
                                  <div className="sa-comp-bar">
                                    <div className="sa-comp-fill int" style={{ width: `${script.scene_count ? (script.int_scenes / script.scene_count * 100) : 0}%` }} />
                                  </div>
                                  <span className="sa-comp-val">{script.int_scenes}</span>
                                </div>
                                <div className="sa-comp-row">
                                  <span className="sa-comp-label">EXT</span>
                                  <div className="sa-comp-bar">
                                    <div className="sa-comp-fill ext" style={{ width: `${script.scene_count ? (script.ext_scenes / script.scene_count * 100) : 0}%` }} />
                                  </div>
                                  <span className="sa-comp-val">{script.ext_scenes}</span>
                                </div>
                                <div className="sa-comp-row">
                                  <span className="sa-comp-label">DAY</span>
                                  <div className="sa-comp-bar">
                                    <div className="sa-comp-fill day" style={{ width: `${script.scene_count ? (script.day_scenes / script.scene_count * 100) : 0}%` }} />
                                  </div>
                                  <span className="sa-comp-val">{script.day_scenes}</span>
                                </div>
                                <div className="sa-comp-row">
                                  <span className="sa-comp-label">NIGHT</span>
                                  <div className="sa-comp-bar">
                                    <div className="sa-comp-fill night" style={{ width: `${script.scene_count ? (script.night_scenes / script.scene_count * 100) : 0}%` }} />
                                  </div>
                                  <span className="sa-comp-val">{script.night_scenes}</span>
                                </div>
                              </div>
                            </div>
                            {/* Feature Usage */}
                            <div className="sa-detail-section">
                              <h4>Feature Usage</h4>
                              <div className="sa-detail-features">
                                {Object.entries(FEATURE_META).map(([key, meta]) => {
                                  const count = script.features?.[key] || 0;
                                  const Icon = meta.icon;
                                  return (
                                    <div key={key} className={`sa-df-item ${count > 0 ? 'used' : ''}`}>
                                      <Icon size={14} />
                                      <span>{meta.label}</span>
                                      {count > 0 && <span className="sa-df-count">{count}</span>}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
          {sortedScripts.length === 0 && (
            <div className="sa-empty">
              <FileText size={40} />
              <p>No scripts uploaded yet</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
