import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  BarChart3, 
  Users, 
  FileText, 
  TrendingUp, 
  Activity,
  AlertCircle,
  ArrowLeft,
  CreditCard,
  X
} from 'lucide-react';
import { supabase } from '../../lib/supabase';
import { getAnalyticsOverview, getRecentActivity, getChartData } from '../../services/apiService';
import MetricCard from '../../components/admin/MetricCard';
import ActivityFeed from '../../components/admin/ActivityFeed';
import ScriptsChart from '../../components/admin/ScriptsChart';
import UserGrowthChart from '../../components/admin/UserGrowthChart';
import RevenueBreakdownModal from '../../components/admin/RevenueBreakdownModal';
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
  const [alertDismissed, setAlertDismissed] = useState(() => {
    return localStorage.getItem('admin_payment_alert_dismissed') === 'true';
  });
  const [revenueModalOpen, setRevenueModalOpen] = useState(false);

  useEffect(() => {
    loadAnalytics();
    loadActivities();
    loadChartData();
    loadPaymentStats();
    
    // Auto-refresh payment stats every 30 seconds
    const interval = setInterval(() => {
      loadPaymentStats();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getAnalyticsOverview();
      setData(response.data);
    } catch (err) {
      console.error('Failed to load analytics:', err);
      setError(err.response?.data?.error || 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  const loadActivities = async () => {
    try {
      setActivitiesLoading(true);
      const response = await getRecentActivity(20);
      if (response.success) {
        setActivities(response.data || []);
      }
    } catch (err) {
      console.error('Failed to load activities:', err);
    } finally {
      setActivitiesLoading(false);
    }
  };

  const loadChartData = async () => {
    try {
      setChartsLoading(true);
      const response = await getChartData(30);
      if (response.success) {
        setChartData(response.data || { scripts_over_time: [], user_growth: [] });
      }
    } catch (err) {
      console.error('Failed to load chart data:', err);
    } finally {
      setChartsLoading(false);
    }
  };

  const loadPaymentStats = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;
      
      const response = await fetch(`${API_BASE_URL}/api/admin/payments/pending`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setPendingPayments(data.count || 0);
      }
    } catch (err) {
      console.error('Failed to load payment stats:', err);
    }
  };

  const dismissAlert = () => {
    setAlertDismissed(true);
    localStorage.setItem('admin_payment_alert_dismissed', 'true');
  };

  const clearDismissal = () => {
    setAlertDismissed(false);
    localStorage.removeItem('admin_payment_alert_dismissed');
  };

  if (loading) {
    return (
      <div className="admin-dashboard">
        <div className="admin-header">
          <h1>Analytics Dashboard</h1>
        </div>
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-dashboard">
        <div className="admin-header">
          <h1>Analytics Dashboard</h1>
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

  const { global_stats, subscription_metrics } = data || {};

  return (
    <div className="admin-dashboard">
      {/* Header */}
      <div className="admin-header">
        <button 
          onClick={() => navigate('/scripts')} 
          className="back-button"
          title="Back to Scripts"
        >
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1>Analytics Dashboard</h1>
          <p className="subtitle">Platform overview and key metrics</p>
        </div>
        <button onClick={loadAnalytics} className="btn-secondary">
          Refresh
        </button>
      </div>

      {/* Payment Alert Banner */}
      {pendingPayments > 0 && !alertDismissed && (
        <div className="alert-banner warning">
          <AlertCircle size={20} />
          <div className="alert-content">
            <strong>{pendingPayments} payment{pendingPayments > 1 ? 's' : ''} awaiting verification</strong>
            <span>Review and approve payments to activate user credits</span>
          </div>
          <button 
            onClick={() => navigate('/admin/payments')} 
            className="btn-primary"
          >
            Review Now
          </button>
          <button 
            onClick={dismissAlert} 
            className="btn-ghost"
            title="Dismiss"
          >
            <X size={18} />
          </button>
        </div>
      )}

      {/* Global Stats Grid */}
      <section className="metrics-section">
        <h2 className="section-title">
          <Activity size={20} />
          Platform Overview
        </h2>
        <div className="metrics-grid">
          <MetricCard
            title="Total Users"
            value={global_stats?.total_users || 0}
            icon={<Users size={24} />}
            trend={`${global_stats?.active_users || 0} active`}
            color="blue"
          />
          <MetricCard
            title="Total Scripts"
            value={global_stats?.total_scripts || 0}
            icon={<FileText size={24} />}
            trend={`${global_stats?.scripts_this_month || 0} this month`}
            color="indigo"
          />
          <MetricCard
            title="Scenes Analyzed"
            value={global_stats?.total_scenes || 0}
            icon={<BarChart3 size={24} />}
            trend={`${global_stats?.total_analysis_jobs || 0} jobs`}
            color="purple"
          />
          <MetricCard
            title="Success Rate"
            value={`${global_stats?.success_rate || 0}%`}
            icon={<TrendingUp size={24} />}
            trend={`${global_stats?.failed_jobs || 0} failures`}
            color={global_stats?.success_rate >= 95 ? 'green' : 'orange'}
          />
        </div>
      </section>

      {/* Subscription Metrics */}
      <section className="metrics-section">
        <h2 className="section-title">
          <TrendingUp size={20} />
          Subscription Metrics
        </h2>
        <div className="metrics-grid">
          <MetricCard
            title="Trial Users"
            value={subscription_metrics?.trial_users || 0}
            icon={<Users size={24} />}
            trend={`${subscription_metrics?.trial_expiring_soon || 0} expiring soon`}
            color="yellow"
          />
          <MetricCard
            title="Active Subscribers"
            value={subscription_metrics?.active_subscribers || 0}
            icon={<Users size={24} />}
            trend={`${subscription_metrics?.conversion_rate || 0}% conversion`}
            color="green"
          />
          <MetricCard
            title="Total Revenue"
            value={`R${subscription_metrics?.total_revenue || 0}`}
            icon={<TrendingUp size={24} />}
            trend={`${subscription_metrics?.successful_payments || 0} payments`}
            color="emerald"
            onClick={() => setRevenueModalOpen(true)}
            tooltip="Click to view detailed revenue breakdown"
          />
          <MetricCard
            title="Expired Users"
            value={subscription_metrics?.expired_users || 0}
            icon={<Users size={24} />}
            trend="Need re-engagement"
            color="red"
          />
        </div>
      </section>

      {/* Charts Section */}
      <section className="charts-section">
        <h2 className="section-title">
          <BarChart3 size={20} />
          Analytics Trends
        </h2>
        <div className="charts-grid">
          <ScriptsChart 
            data={chartData.scripts_over_time} 
            loading={chartsLoading}
          />
          <UserGrowthChart 
            data={chartData.user_growth} 
            loading={chartsLoading}
          />
        </div>
      </section>

      {/* Recent Activity Feed */}
      <section className="activity-section">
        <ActivityFeed 
          activities={activities}
          loading={activitiesLoading}
          onRefresh={loadActivities}
          autoRefresh={true}
        />
      </section>

      {/* Quick Actions */}
      <section className="quick-actions">
        <h2 className="section-title">Quick Actions</h2>
        <div className="action-grid">
          <button 
            onClick={() => navigate('/admin/users')} 
            className="action-card"
          >
            <Users size={24} />
            <span>View Users</span>
          </button>
          <button 
            onClick={() => navigate('/admin/scripts')} 
            className="action-card"
          >
            <FileText size={24} />
            <span>Script Analytics</span>
          </button>
          <button 
            onClick={() => navigate('/admin/payments')} 
            className="action-card"
          >
            <CreditCard size={24} />
            <span>Payment Verification</span>
            {pendingPayments > 0 && (
              <span className="badge urgent">{pendingPayments}</span>
            )}
          </button>
          <button 
            onClick={() => navigate('/admin/performance')} 
            className="action-card"
          >
            <Activity size={24} />
            <span>System Health</span>
          </button>
          <button 
            onClick={() => navigate('/admin/emails')} 
            className="action-card"
            disabled
          >
            <BarChart3 size={24} />
            <span>Email Campaigns</span>
            <span className="badge">Coming Soon</span>
          </button>
        </div>
      </section>

      {/* Revenue Breakdown Modal */}
      <RevenueBreakdownModal
        isOpen={revenueModalOpen}
        onClose={() => setRevenueModalOpen(false)}
      />
    </div>
  );
}
