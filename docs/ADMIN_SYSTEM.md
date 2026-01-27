# Admin System - Superuser Analytics & Email Management

**Status**: Phase 1 & 2 Complete ✅  
**Date**: January 20, 2026

---

## Overview

Comprehensive admin-only system for monitoring platform health, user activity, and managing email communications. Accessible only to users with `is_superuser = true` flag.

---

## Phase 1: Foundation ✅

### Database Migrations

#### **010_add_superuser_flag.sql**
- Added `is_superuser` boolean column to `profiles` table
- Created index for faster superuser lookups
- Enables admin access control

#### **011_email_management_system.sql**
Comprehensive email system with 3 core tables:

1. **email_templates**
   - Reusable templates with HTML/text versions
   - Variable substitution support (`{{user_name}}`, `{{script_count}}`, etc.)
   - Categories: onboarding, engagement, billing, support, announcement

2. **email_campaigns**
   - Campaign management with audience targeting
   - Status tracking: draft, scheduled, sending, sent, cancelled, failed
   - Performance metrics: sent, delivered, opened, clicked, bounced counts

3. **email_logs**
   - Individual email tracking per recipient
   - Integration with Resend email IDs
   - Detailed status tracking and metadata

4. **email_campaign_stats** (Materialized View)
   - Aggregated campaign performance
   - Open rates, click rates calculated automatically
   - Auto-refreshes on email_logs changes

### Backend Authentication

#### **middleware/auth.py**
- Added `@require_superuser` decorator
- Checks `is_superuser` flag in profiles table
- Returns 403 Forbidden if not superuser
- Dev mode bypass for local development

#### **components/auth/AdminRoute.jsx**
- Frontend route guard for admin pages
- Checks superuser status on mount
- Shows loading state during verification
- Displays access denied page for non-superusers
- Redirects to login if not authenticated

---

## Phase 2: Analytics System ✅

### Backend Services

#### **services/analytics_service.py**
Comprehensive analytics aggregation service with 5 main methods:

**1. `get_global_stats()`**
Returns:
- Total users, active users (last 30 days)
- Total scripts, scripts this month
- Total scenes analyzed
- Analysis job stats (total, completed, failed, success rate)
- Subscription breakdown (trial, active subscribers)

**2. `get_user_activity(days, limit)`**
Returns per-user metrics:
- Name, email, subscription status
- Script count, last active date
- Days since signup
- Trial days remaining

**3. `get_script_stats(days)`**
Returns:
- Scripts uploaded in period
- Total scenes extracted
- Average scenes per script
- Analysis status breakdown
- Average analysis time

**4. `get_performance_metrics()`**
Returns:
- Job type breakdown with success rates
- Average duration per job type
- Error rate and recent errors
- System health indicators

**5. `get_subscription_metrics()`**
Returns:
- Trial/active/expired user counts
- Trial expiring soon (within 3 days)
- Conversion rate (trial → paid)
- Total revenue and successful payments

### Backend API Endpoints

#### **routes/admin_routes.py**
All routes require `@require_auth` + `@require_superuser`

**Analytics Endpoints:**
- `GET /api/admin/analytics/overview` - Global stats + subscriptions
- `GET /api/admin/analytics/users?days=30&limit=100` - User activity
- `GET /api/admin/analytics/scripts?days=30` - Script statistics
- `GET /api/admin/analytics/performance` - System performance
- `GET /api/admin/analytics/subscriptions` - Subscription metrics

**User Management:**
- `GET /api/admin/users?status=trial&limit=50&offset=0` - List users
- `GET /api/admin/users/:userId` - User details with scripts

**System Health:**
- `GET /api/admin/health` - Database health, stuck jobs, recent failures

### Integration

#### **app.py**
- Registered `admin_bp` blueprint
- Routes available at `/api/admin/*`
- CORS configured for admin endpoints

---

## Access Control

### Granting Superuser Access

**Via Supabase Dashboard:**
```sql
UPDATE profiles 
SET is_superuser = TRUE 
WHERE email = 'your-email@example.com';
```

**Via SQL Editor:**
```sql
-- Grant superuser to specific user
UPDATE profiles 
SET is_superuser = TRUE 
WHERE id = 'user-uuid-here';

-- Verify superuser status
SELECT id, email, is_superuser 
FROM profiles 
WHERE is_superuser = TRUE;
```

### Development Mode
- Set `FLASK_ENV=development` in backend `.env`
- Superuser checks bypassed automatically
- Dev user ID: `00000000-0000-0000-0000-000000000001`

---

## Frontend Implementation (Pending)

### Planned Routes
- `/admin` - Main admin dashboard
- `/admin/analytics` - Analytics overview
- `/admin/users` - User management
- `/admin/emails` - Email management (Phase 3+)

### Planned Components

**Analytics Dashboard:**
```
/frontend/src/pages/Admin/
  ├── AnalyticsDashboard.jsx       # Main overview
  ├── UserActivityTable.jsx        # User list with filters
  ├── ScriptStatsChart.jsx         # Script analysis charts
  └── PerformanceMetrics.jsx       # System health
```

**Shared Components:**
```
/frontend/src/components/admin/
  ├── MetricCard.jsx               # Stat display card
  ├── StatChart.jsx                # Recharts wrapper
  └── AdminLayout.jsx              # Admin page layout
```

---

## Next Steps

### Phase 3: Email Templates (Pending)
- [ ] Email template CRUD backend service
- [ ] Rich text editor component (TinyMCE/Quill)
- [ ] Variable insertion UI
- [ ] Template preview and test send

### Phase 4: Email Campaigns (Pending)
- [ ] Campaign creation service
- [ ] Audience filtering logic
- [ ] Campaign wizard UI (multi-step)
- [ ] Batch sending with queue

### Phase 5: Email Tracking (Pending)
- [ ] Resend webhook handler
- [ ] Open/click tracking
- [ ] Campaign analytics dashboard
- [ ] Email logs viewer

---

## Usage Examples

### Check Analytics (Backend)
```python
from services.analytics_service import AnalyticsService

analytics = AnalyticsService()

# Get global overview
stats = analytics.get_global_stats()
print(f"Total users: {stats['total_users']}")
print(f"Success rate: {stats['success_rate']}%")

# Get user activity
users = analytics.get_user_activity(days=7, limit=50)
for user in users:
    print(f"{user['name']}: {user['script_count']} scripts")
```

### API Request (Frontend)
```javascript
// Get analytics overview
const response = await fetch('/api/admin/analytics/overview', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const { data } = await response.json();
console.log('Global stats:', data.global_stats);
console.log('Subscriptions:', data.subscription_metrics);
```

---

## Security Considerations

1. **Superuser Flag**: Only set for trusted administrators
2. **JWT Verification**: All admin routes require valid authentication
3. **Double Check**: Both `@require_auth` and `@require_superuser` decorators
4. **Frontend Guard**: `AdminRoute` component prevents UI access
5. **Audit Logging**: Consider adding admin action logs (future)

---

## Monitoring

### Key Metrics to Watch
- **Error Rate**: Should stay below 5%
- **Stuck Jobs**: Should be 0 (indicates worker issues)
- **Trial Conversions**: Track weekly conversion rate
- **Active Users**: Monitor 30-day active user trend

### Alerts to Set Up
- Email when error rate > 10%
- Email when stuck jobs > 5
- Email when trial users expiring in 3 days
- Email on system health check failures

---

## Database Schema Reference

### profiles (extended)
```sql
is_superuser BOOLEAN DEFAULT FALSE
```

### email_templates
```sql
template_id UUID PRIMARY KEY
name TEXT NOT NULL
subject TEXT NOT NULL
body_html TEXT NOT NULL
body_text TEXT
category TEXT
variables JSONB
is_active BOOLEAN
created_at, updated_at TIMESTAMP
created_by UUID REFERENCES profiles
```

### email_campaigns
```sql
campaign_id UUID PRIMARY KEY
name TEXT NOT NULL
template_id UUID REFERENCES email_templates
target_audience JSONB
status TEXT (draft|scheduled|sending|sent|cancelled|failed)
scheduled_at, sent_at TIMESTAMP
total_recipients, sent_count, delivered_count INTEGER
opened_count, clicked_count, bounced_count, failed_count INTEGER
created_at, updated_at TIMESTAMP
created_by UUID REFERENCES profiles
```

### email_logs
```sql
log_id UUID PRIMARY KEY
campaign_id UUID REFERENCES email_campaigns
recipient_email TEXT
recipient_user_id UUID REFERENCES profiles
status TEXT (queued|sent|delivered|opened|clicked|bounced|failed|spam)
resend_email_id TEXT
sent_at, delivered_at, opened_at, clicked_at, bounced_at TIMESTAMP
error_message TEXT
metadata JSONB
created_at TIMESTAMP
```

---

## Troubleshooting

### "Superuser access required" Error
- Verify `is_superuser = TRUE` in database
- Check JWT token is valid
- Ensure both decorators are applied to route

### Analytics Data Not Loading
- Check Supabase connection
- Verify table permissions (RLS policies)
- Check backend logs for errors

### Dev Mode Not Working
- Set `FLASK_ENV=development` in `.env`
- Restart Flask server
- Check `DEV_MODE` variable in `auth.py`

---

## Related Documentation
- [User Authentication System](./USER_AUTH.md)
- [Subscription System](./SUBSCRIPTION_TIERS.md)
- [Email System Guide](./EMAIL_SYSTEM_GUIDE.md)
- [API Documentation](../API_endpoints.md)

---

**Last Updated**: January 20, 2026  
**Version**: 1.0  
**Status**: Phase 1 & 2 Complete, Phase 3-5 Planned
