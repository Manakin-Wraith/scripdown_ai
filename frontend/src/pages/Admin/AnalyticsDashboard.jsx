import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  FileText,
  TrendingUp,
  AlertCircle,
  CreditCard,
  X,
  RefreshCw,
  ArrowUpRight,
  Clock,
  CheckCircle2,
  UserCheck,
  UserX,
  ChevronRight,
  BarChart2,
  Zap
} from 'lucide-react';
import { supabase } from '../../lib/supabase';
import { getAnalyticsOverview, getRecentActivity, getChartData } from '../../services/apiService';
import AdminLayout from '../../components/admin/AdminLayout';
import ScriptsChart from '../../components/admin/ScriptsChart';
import UserGrowthChart from '../../components/admin/UserGrowthChart';
import RevenueBreakdownModal from '../../components/admin/RevenueBreakdownModal';
import ActivityFeed from '../../components/admin/ActivityFeed';
import './AnalyticsDashboard.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

/**
 * Main Analytics Dashboard - Overview of platform metrics
 * Route: /admin
 */
export default function AnalyticsDashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [activities, setActivities] = useState([]);
  const [activitiesLoading, setActivitiesLoading] = useState(false);
  const [chartData, setChartData] = useState({ scripts_over_time: [], user_growth: [] });
  const [chartsLoading, setChartsLoading] = useState(false);
  const [pendingPayments, setPendingPayments] = useState(0);
  const [alertDismissed, setAlertDismissed] = useState(() =>
    localStorage.getItem('admin_payment_alert_dismissed') === 'true'
  );
  const [revenueModalOpen, setRevenueModalOpen] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const loadPaymentStats = useCallback(async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;
      const response = await fetch(`${API_BASE_URL}/api/admin/payments/pending`, {
        headers: { 'Authorization': `Bearer ${session.access_token}` }
      });
      if (response.ok) {
        const result = await response.json();
        setPendingPayments(result.count || 0);
      }
    } catch (err) {
      console.error('Failed to load payment stats:', err);
    }
  }, []);

  const loadAll = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true);
    try {
      setError(null);
      const [overviewRes, activityRes, chartRes] = await Promise.allSettled([
        getAnalyticsOverview(),
        getRecentActivity(20),
        getChartData(30),
      ]);

      if (overviewRes.status === 'fulfilled') setData(overviewRes.value.data);
      else setError(overviewRes.reason?.response?.data?.error || 'Failed to load analytics');

      if (activityRes.status === 'fulfilled' && activityRes.value.success)
        setActivities(activityRes.value.data || []);

      if (chartRes.status === 'fulfilled' && chartRes.value.success)
        setChartData(chartRes.value.data || { scripts_over_time: [], user_growth: [] });

      await loadPaymentStats();
    } finally {
      setLoading(false);
      setChartsLoading(false);
      setActivitiesLoading(false);
      if (showRefreshing) setTimeout(() => setRefreshing(false), 400);
    }
  }, [loadPaymentStats]);

  useEffect(() => {
    setChartsLoading(true);
    setActivitiesLoading(true);
    loadAll();

    const interval = setInterval(loadPaymentStats, 30000);
    return () => clearInterval(interval);
  }, [loadAll, loadPaymentStats]);

  const { global_stats, subscription_metrics } = data || {};

  const conversionRate = subscription_metrics
    ? Math.round(
        ((subscription_metrics.active_subscribers || 0) /
          Math.max((subscription_metrics.trial_users || 0) + (subscription_metrics.active_subscribers || 0), 1)) *
          100
      )
    : 0;

  if (loading) {
    return (
      <AdminLayout pendingPayments={pendingPayments}>
        <div className="adash-loading">
          <div className="adash-spinner" />
          <p>Loading analytics…</p>
        </div>
      </AdminLayout>
    );
  }

  if (error) {
    return (
      <AdminLayout pendingPayments={pendingPayments}>
        <div className="adash-error">
          <AlertCircle size={40} />
          <h2>Failed to load analytics</h2>
          <p>{error}</p>
          <button onClick={() => loadAll()} className="adash-btn-primary">Try Again</button>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout pendingPayments={pendingPayments}>
      <div className="adash">

        {/* ── Page Header ── */}
        <header className="adash-header">
          <div className="adash-header__left">
            <h1>Overview</h1>
            <p className="adash-header__sub">Platform health at a glance</p>
          </div>
          <button
            className={`adash-refresh-btn ${refreshing ? 'adash-refresh-btn--spinning' : ''}`}
            onClick={() => loadAll(true)}
            disabled={refreshing}
            title="Refresh data"
          >
            <RefreshCw size={16} />
            <span>Refresh</span>
          </button>
        </header>

        {/* ── Pending Payment Alert ── */}
        {pendingPayments > 0 && !alertDismissed && (
          <div className="adash-alert">
            <AlertCircle size={18} />
            <div className="adash-alert__body">
              <strong>{pendingPayments} payment{pendingPayments > 1 ? 's' : ''} awaiting verification</strong>
              <span>Approve to activate user credits</span>
            </div>
            <button className="adash-btn-primary adash-btn-sm" onClick={() => navigate('/admin/payments')}>
              Review <ChevronRight size={14} />
            </button>
            <button
              className="adash-icon-btn"
              onClick={() => {
                setAlertDismissed(true);
                localStorage.setItem('admin_payment_alert_dismissed', 'true');
              }}
            >
              <X size={16} />
            </button>
          </div>
        )}

        {/* ── Hero KPI Row ── */}
        <section className="adash-kpis">
          {/* Total Users */}
          <button className="adash-kpi adash-kpi--blue" onClick={() => navigate('/admin/users')}>
            <div className="adash-kpi__icon"><Users size={20} /></div>
            <div className="adash-kpi__body">
              <span className="adash-kpi__label">Total Users</span>
              <span className="adash-kpi__value">{global_stats?.total_users ?? 0}</span>
              <span className="adash-kpi__sub">
                {global_stats?.new_users_this_month ?? 0} this month
              </span>
            </div>
            <ArrowUpRight size={16} className="adash-kpi__arrow" />
          </button>

          {/* Active Subscribers */}
          <button className="adash-kpi adash-kpi--green" onClick={() => navigate('/admin/users')}>
            <div className="adash-kpi__icon"><UserCheck size={20} /></div>
            <div className="adash-kpi__body">
              <span className="adash-kpi__label">Active Subscribers</span>
              <span className="adash-kpi__value">{subscription_metrics?.active_subscribers ?? 0}</span>
              <span className="adash-kpi__sub">{conversionRate}% conversion rate</span>
            </div>
            <ArrowUpRight size={16} className="adash-kpi__arrow" />
          </button>

          {/* Total Scripts */}
          <button className="adash-kpi adash-kpi--indigo" onClick={() => navigate('/admin/scripts')}>
            <div className="adash-kpi__icon"><FileText size={20} /></div>
            <div className="adash-kpi__body">
              <span className="adash-kpi__label">Scripts Uploaded</span>
              <span className="adash-kpi__value">{global_stats?.total_scripts ?? 0}</span>
              <span className="adash-kpi__sub">
                {global_stats?.scripts_this_month ?? 0} this month
              </span>
            </div>
            <ArrowUpRight size={16} className="adash-kpi__arrow" />
          </button>

          {/* Revenue */}
          <button className="adash-kpi adash-kpi--emerald" onClick={() => setRevenueModalOpen(true)}>
            <div className="adash-kpi__icon"><TrendingUp size={20} /></div>
            <div className="adash-kpi__body">
              <span className="adash-kpi__label">Total Revenue</span>
              <span className="adash-kpi__value">R{subscription_metrics?.total_revenue ?? 0}</span>
              <span className="adash-kpi__sub">
                {subscription_metrics?.successful_payments ?? 0} payments
              </span>
            </div>
            <ArrowUpRight size={16} className="adash-kpi__arrow" />
          </button>
        </section>

        {/* ── Secondary Stats Row ── */}
        <section className="adash-stats-row">
          <div className="adash-stat">
            <Clock size={15} />
            <span className="adash-stat__label">Trial Users</span>
            <span className="adash-stat__value adash-stat__value--yellow">
              {subscription_metrics?.trial_users ?? 0}
            </span>
            {(subscription_metrics?.trial_expiring_soon ?? 0) > 0 && (
              <span className="adash-stat__badge adash-stat__badge--warn">
                {subscription_metrics.trial_expiring_soon} expiring soon
              </span>
            )}
          </div>

          <div className="adash-stat-divider" />

          <div className="adash-stat">
            <UserX size={15} />
            <span className="adash-stat__label">Expired</span>
            <span className="adash-stat__value adash-stat__value--red">
              {subscription_metrics?.expired_users ?? 0}
            </span>
          </div>

          <div className="adash-stat-divider" />

          <div className="adash-stat">
            <Zap size={15} />
            <span className="adash-stat__label">Scenes Parsed</span>
            <span className="adash-stat__value">
              {(global_stats?.total_scenes ?? 0).toLocaleString()}
            </span>
          </div>

          <div className="adash-stat-divider" />

          <div className="adash-stat">
            <CheckCircle2 size={15} />
            <span className="adash-stat__label">Analysis Success</span>
            <span className={`adash-stat__value ${(global_stats?.success_rate ?? 0) >= 95 ? 'adash-stat__value--green' : 'adash-stat__value--orange'}`}>
              {global_stats?.success_rate ?? 0}%
            </span>
          </div>

          <div className="adash-stat-divider" />

          <div className="adash-stat">
            <CreditCard size={15} />
            <span className="adash-stat__label">Pending Payments</span>
            <span className={`adash-stat__value ${pendingPayments > 0 ? 'adash-stat__value--red' : ''}`}>
              {pendingPayments}
            </span>
            {pendingPayments > 0 && (
              <button className="adash-stat__link" onClick={() => navigate('/admin/payments')}>
                Review
              </button>
            )}
          </div>
        </section>

        {/* ── Charts + Activity ── */}
        <section className="adash-content-grid">
          <div className="adash-charts">
            <div className="adash-panel">
              <div className="adash-panel__header">
                <BarChart2 size={16} />
                <h3>User Growth</h3>
                <span className="adash-panel__sub">Cumulative signups</span>
              </div>
              <UserGrowthChart data={chartData.user_growth} loading={chartsLoading} />
            </div>
            <div className="adash-panel">
              <div className="adash-panel__header">
                <FileText size={16} />
                <h3>Scripts Over Time</h3>
                <span className="adash-panel__sub">Last 30 days</span>
              </div>
              <ScriptsChart data={chartData.scripts_over_time} loading={chartsLoading} />
            </div>
          </div>

          <div className="adash-activity-col">
            <div className="adash-panel adash-panel--full">
              <ActivityFeed
                activities={activities}
                loading={activitiesLoading}
                onRefresh={() => getRecentActivity(20).then(r => r.success && setActivities(r.data || []))}
                autoRefresh={true}
              />
            </div>
          </div>
        </section>

      </div>

      {/* Revenue Breakdown Modal */}
      <RevenueBreakdownModal
        isOpen={revenueModalOpen}
        onClose={() => setRevenueModalOpen(false)}
      />
    </AdminLayout>
  );
}
