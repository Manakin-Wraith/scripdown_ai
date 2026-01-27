# Admin Payment Verification Integration

## Overview
Integration plan for adding payment verification to the admin dashboard with optimal UX.

---

## Current Dashboard Structure

### Pages
- `/admin` - Analytics Dashboard (main landing)
- `/admin/users` - User Activity & Management
- `/admin/scripts` - Script Analytics & Performance
- `/admin/payments` - **Payment Verification (NEW)**

### Layout Components
1. **Header** - Title, back button, refresh
2. **Metric Cards** - 4-column grid showing key stats
3. **Charts** - Scripts over time, user growth
4. **Activity Feed** - Recent platform activity
5. **Quick Actions** - Navigation cards to sub-pages

---

## Integration Strategy

### Phase 1: Quick Actions Card (Baseline)
Add payment verification to Quick Actions grid.

**Location:** Quick Actions section (bottom of dashboard)

**Features:**
- Icon: `CreditCard` or `DollarSign`
- Label: "Payment Verification"
- Badge: Shows pending count when > 0
- Click: Navigate to `/admin/payments`

**Code:**
```jsx
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
```

---

### Phase 2: Alert Banner (High Priority)
Add dismissible alert banner when payments are pending.

**Location:** Top of dashboard (below header)

**Features:**
- Only shows when `pendingPayments > 0`
- Warning color (orange/yellow)
- "Review Now" button
- Dismissible (stores in localStorage)

**Code:**
```jsx
{pendingPayments > 0 && !dismissed && (
  <div className="alert-banner warning">
    <AlertCircle size={20} />
    <div className="alert-content">
      <strong>{pendingPayments} payment{pendingPayments > 1 ? 's' : ''} awaiting verification</strong>
      <span>Review and approve payments to activate user credits</span>
    </div>
    <button onClick={() => navigate('/admin/payments')} className="btn-primary">
      Review Now
    </button>
    <button onClick={() => setDismissed(true)} className="btn-ghost">
      Dismiss
    </button>
  </div>
)}
```

---

### Phase 3: Metric Card (Optional)
Add "Pending Payments" to Platform Overview metrics.

**Location:** Platform Overview section (top metrics grid)

**Features:**
- Shows pending count
- Shows total pending amount
- Color: Orange if pending, Green if clear
- Clickable to navigate to payments page

**Code:**
```jsx
<MetricCard
  title="Pending Payments"
  value={pendingPayments || 0}
  icon={<CreditCard size={24} />}
  trend={`R${pendingAmount?.toFixed(2) || '0.00'} total`}
  color={pendingPayments > 0 ? 'orange' : 'green'}
  onClick={() => navigate('/admin/payments')}
  clickable
/>
```

---

## API Integration

### Fetch Pending Payments Count
Add to dashboard data fetch:

```javascript
const loadPaymentStats = async () => {
  try {
    const response = await fetch('/api/admin/payments/pending', {
      headers: {
        'Authorization': `Bearer ${session.access_token}`
      }
    });
    const data = await response.json();
    setPendingPayments(data.count || 0);
    setPendingAmount(data.data?.reduce((sum, p) => sum + p.amount, 0) || 0);
  } catch (err) {
    console.error('Failed to load payment stats:', err);
  }
};

// Call in useEffect
useEffect(() => {
  loadAnalytics();
  loadActivities();
  loadChartData();
  loadPaymentStats(); // NEW
}, []);
```

### Real-time Updates (Optional)
Poll every 30 seconds for new pending payments:

```javascript
useEffect(() => {
  const interval = setInterval(() => {
    loadPaymentStats();
  }, 30000); // 30 seconds

  return () => clearInterval(interval);
}, []);
```

---

## Payment Verification Page Enhancements

### Navigation
Add back button and breadcrumbs:

```jsx
<div className="admin-header">
  <button onClick={() => navigate('/admin')} className="back-button">
    <ArrowLeft size={20} />
  </button>
  <div>
    <h1>Payment Verification</h1>
    <p className="subtitle">Review and approve pending credit purchases</p>
  </div>
</div>
```

### Features to Add
1. **Bulk Actions** - Approve multiple payments at once
2. **Filters** - By date, amount, user
3. **Search** - By email or reference number
4. **Export** - Download pending payments as CSV
5. **Auto-refresh** - Poll every 30s for new payments

---

## Notification System (Future)

### Email Alerts for Admin
Send email when new payment is pending:

**Trigger:** New purchase created with `status = 'pending'`

**Email:**
```
Subject: New Payment Awaiting Verification

A new credit purchase is awaiting verification:
- User: user@example.com
- Package: 5 Scripts
- Amount: R220
- Time: 2 minutes ago

Review now: https://app.slateone.studio/admin/payments
```

### Browser Notifications
Use Web Push API for real-time alerts when admin is online.

---

## Styling Guidelines

### Alert Banner
```css
.alert-banner {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.5rem;
  background: var(--warning-50);
  border: 1px solid var(--warning-200);
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.alert-banner.warning {
  background: #fff7ed;
  border-color: #fed7aa;
  color: #c2410c;
}

.alert-banner .btn-primary {
  background: var(--warning-600);
  color: white;
}
```

### Badge Styles
```css
.badge.urgent {
  background: var(--error-500);
  color: white;
  font-weight: 700;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
```

---

## User Flow

### Admin Workflow
1. Admin logs in → Sees dashboard
2. Alert banner shows "3 payments awaiting verification"
3. Clicks "Review Now" → Navigates to `/admin/payments`
4. Sees table of pending payments
5. Opens Yoco dashboard in new tab
6. Matches payment by email + amount
7. Clicks "Approve" → Enters Yoco reference
8. Credits added to user account
9. User gets email notification
10. Payment removed from pending list

### Fallback Workflow
If admin misses alert:
1. Sees "Payment Verification" in Quick Actions
2. Badge shows "3" pending
3. Clicks card → Goes to payments page

---

## Metrics to Track

### Dashboard Metrics
- Pending payment count
- Total pending amount (ZAR)
- Average verification time
- Payments verified today

### Analytics
- Payment approval rate
- Average time to verify
- Peak payment times
- Rejection reasons

---

## Implementation Checklist

### Phase 1: Basic Integration
- [ ] Add payment stats API call to dashboard
- [ ] Add "Payment Verification" to Quick Actions
- [ ] Add pending count badge
- [ ] Test navigation to payments page

### Phase 2: Enhanced UX
- [ ] Add alert banner for pending payments
- [ ] Add dismiss functionality with localStorage
- [ ] Add auto-refresh (30s polling)
- [ ] Add loading states

### Phase 3: Advanced Features
- [ ] Add metric card to Platform Overview
- [ ] Add bulk approve functionality
- [ ] Add filters and search
- [ ] Add CSV export

### Phase 4: Notifications
- [ ] Email alerts for new payments
- [ ] Browser push notifications
- [ ] Slack/Discord webhooks (optional)

---

## Testing Checklist

- [ ] Dashboard loads payment stats correctly
- [ ] Badge shows correct pending count
- [ ] Alert banner appears when payments pending
- [ ] Alert banner dismisses and stays dismissed
- [ ] Quick action navigates to payments page
- [ ] Auto-refresh updates count every 30s
- [ ] Metric card (if added) shows correct data
- [ ] All features work for superusers only

---

## Security Considerations

1. **Authorization** - Only superusers can access
2. **Audit Trail** - Log all approve/reject actions
3. **Rate Limiting** - Prevent spam approvals
4. **CSRF Protection** - Secure POST requests
5. **Session Validation** - Verify admin session on each action

---

## Performance Optimization

1. **Caching** - Cache pending count for 30s
2. **Lazy Loading** - Only load payment stats when needed
3. **Debouncing** - Debounce auto-refresh calls
4. **Pagination** - Paginate pending payments list
5. **Indexing** - Database index on `status = 'pending'`

---

## Future Enhancements

1. **Payment Analytics** - Revenue charts, conversion rates
2. **Automated Verification** - Yoco API integration (if available)
3. **Payment History** - View all past payments
4. **Refund Management** - Handle refunds and disputes
5. **Multi-currency** - Support USD, EUR, etc.
