# Email Tracking & Analytics Guide

## Overview
Complete guide for tracking sent emails, viewing analytics, and monitoring email campaign performance.

---

## 🎯 Where to View Your Emails

### **Method 1: Resend Dashboard (Recommended)**

**Access:** https://resend.com/emails

**What you can see:**
- ✅ All sent emails in real-time
- ✅ Delivery status (sent/delivered/bounced/failed)
- ✅ Open rates (when enabled)
- ✅ Click-through rates
- ✅ Email content preview
- ✅ Recipient information
- ✅ Timestamps and metadata

**How to use:**
1. Login to your Resend account
2. Navigate to "Emails" section
3. Filter by date, status, or recipient
4. Click any email to view details

---

### **Method 2: Your Database (Supabase)**

**Access:** Supabase Dashboard → Table Editor → `email_tracking`

**What you can see:**
- All emails sent through your app
- Custom metadata and user status
- Delivery tracking
- Open/click tracking (when webhooks configured)

**How to query:**
```sql
-- View all beta launch emails
SELECT * FROM email_tracking 
WHERE email_type = 'beta_launch'
ORDER BY sent_at DESC;

-- Check if specific user received email
SELECT * FROM email_tracking 
WHERE recipient_email = 'user@example.com'
AND email_type = 'beta_launch';

-- Get email metrics
SELECT 
  email_type,
  COUNT(*) as total_sent,
  COUNT(CASE WHEN delivery_status = 'delivered' THEN 1 END) as delivered,
  COUNT(CASE WHEN opened_at IS NOT NULL THEN 1 END) as opened,
  COUNT(CASE WHEN clicked_at IS NOT NULL THEN 1 END) as clicked
FROM email_tracking
GROUP BY email_type;
```

---

### **Method 3: API Endpoints**

Use the built-in analytics API to programmatically access email data.

---

## 📊 Analytics API Endpoints

### 1. Get Email Metrics

**Endpoint:** `GET /api/email-analytics/metrics`

**Query Parameters:**
- `email_type` (optional): Filter by type ('beta_launch', 'welcome', etc.)
- `start_date` (optional): ISO date string
- `end_date` (optional): ISO date string

**Example:**
```bash
curl http://localhost:5000/api/email-analytics/metrics?email_type=beta_launch
```

**Response:**
```json
{
  "metrics": {
    "total_sent": 100,
    "delivered": 95,
    "bounced": 5,
    "opened": 30,
    "clicked": 10,
    "delivery_rate": 95.0,
    "open_rate": 31.58,
    "click_rate": 10.53
  },
  "total_emails": 100
}
```

---

### 2. Get Recent Emails

**Endpoint:** `GET /api/email-analytics/recent`

**Query Parameters:**
- `limit` (optional): Number of emails (default: 50, max: 200)

**Example:**
```bash
curl http://localhost:5000/api/email-analytics/recent?limit=20
```

**Response:**
```json
{
  "emails": [
    {
      "id": "uuid",
      "email_type": "beta_launch",
      "recipient_email": "user@example.com",
      "recipient_name": "John Doe",
      "user_status": "new",
      "resend_email_id": "abc123",
      "sent_at": "2025-12-22T10:00:00Z",
      "delivery_status": "delivered",
      "opened_at": "2025-12-22T10:05:00Z",
      "clicked_at": null,
      "metadata": {"source": "manual_send"}
    }
  ],
  "count": 20
}
```

---

### 3. Check if Email Was Sent

**Endpoint:** `POST /api/email-analytics/check-sent`

**Request:**
```json
{
  "recipient_email": "user@example.com",
  "email_type": "beta_launch"
}
```

**Response:**
```json
{
  "already_sent": true,
  "recipient_email": "user@example.com",
  "email_type": "beta_launch"
}
```

**Use case:** Prevent duplicate emails before sending

---

### 4. Get Campaign Summary

**Endpoint:** `GET /api/email-analytics/summary`

**Example:**
```bash
curl http://localhost:5000/api/email-analytics/summary
```

**Response:**
```json
{
  "campaigns": [
    {
      "email_type": "beta_launch",
      "total_sent": 100,
      "delivered": 95,
      "bounced": 5,
      "opened": 30,
      "clicked": 10,
      "delivery_rate": 95.0,
      "open_rate": 31.58,
      "click_rate": 10.53
    },
    {
      "email_type": "welcome",
      "total_sent": 50,
      "delivery_rate": 98.0,
      "open_rate": 45.0,
      "click_rate": 15.0
    }
  ],
  "total_campaigns": 2
}
```

---

## 🔧 Setup Instructions

### Step 1: Run Database Migration

```bash
cd backend
psql -h your-supabase-host -U postgres -d postgres -f db/migrations/create_email_tracking.sql
```

Or via Supabase Dashboard:
1. Go to SQL Editor
2. Copy contents of `backend/db/migrations/create_email_tracking.sql`
3. Run the query

### Step 2: Verify Table Created

```sql
SELECT * FROM email_tracking LIMIT 1;
```

### Step 3: Test Email Tracking

Send a test email and verify it's logged:

```bash
python backend/scripts/test_beta_launch_email.py
```

Then check:
```sql
SELECT * FROM email_tracking ORDER BY sent_at DESC LIMIT 1;
```

---

## 📈 Understanding Email Metrics

### Delivery Rate
**Formula:** `(Delivered / Total Sent) × 100`

**Industry Benchmark:** >95%

**What it means:**
- Percentage of emails successfully delivered to recipient's inbox
- Low rate indicates email list quality issues or domain reputation problems

---

### Open Rate
**Formula:** `(Opened / Delivered) × 100`

**Industry Benchmark:** 
- Cold emails: 15-25%
- Warm emails: 25-40%
- Beta launch: 30-50%

**What it means:**
- Percentage of delivered emails that were opened
- Affected by subject line, sender name, timing

**Note:** Open tracking requires pixel tracking (may not be 100% accurate due to privacy features)

---

### Click Rate
**Formula:** `(Clicked / Delivered) × 100`

**Industry Benchmark:** 2-5%

**What it means:**
- Percentage of delivered emails where a link was clicked
- Indicates email content engagement and CTA effectiveness

---

### Bounce Rate
**Formula:** `(Bounced / Total Sent) × 100`

**Industry Benchmark:** <2%

**Types:**
- **Hard Bounce:** Invalid email address (remove from list)
- **Soft Bounce:** Temporary issue (retry later)

---

## 🔍 Monitoring Best Practices

### Daily Checks
- [ ] Check Resend dashboard for bounces/complaints
- [ ] Review delivery rate (should be >95%)
- [ ] Monitor beta@slateone.studio for responses

### Weekly Analysis
- [ ] Compare open rates across campaigns
- [ ] Identify best-performing subject lines
- [ ] Track conversion rate (signups from emails)
- [ ] Review referral submissions

### Monthly Review
- [ ] Calculate ROI per campaign
- [ ] A/B test results analysis
- [ ] Clean email list (remove bounces)
- [ ] Update email templates based on performance

---

## 🚨 Troubleshooting

### Email Not Showing in Database

**Check:**
1. Migration ran successfully
2. Email actually sent (check Resend dashboard)
3. Backend logs for errors

**Debug:**
```python
from services.email_tracking_service import log_email_sent

result = log_email_sent(
    email_type='test',
    recipient_email='test@example.com',
    recipient_name='Test User',
    resend_email_id='test123'
)

print(result)  # Should show success: True
```

---

### Metrics Not Updating

**Possible causes:**
1. Webhooks not configured (for open/click tracking)
2. Database connection issues
3. Resend API delays

**Solution:**
- Open/click tracking requires Resend webhooks (see below)
- Delivery status updates automatically via Resend

---

### High Bounce Rate

**Actions:**
1. Verify email addresses before sending
2. Remove hard bounces immediately
3. Check domain reputation (mail-tester.com)
4. Warm up new sending domain gradually

---

## 🔗 Setting Up Webhooks (Optional)

To track opens and clicks automatically, configure Resend webhooks:

### Step 1: Create Webhook Endpoint

```python
# backend/routes/webhooks.py
from flask import Blueprint, request, jsonify
from services.email_tracking_service import update_email_status

webhook_bp = Blueprint('webhooks', __name__, url_prefix='/api/webhooks')

@webhook_bp.route('/resend', methods=['POST'])
def resend_webhook():
    """Handle Resend webhook events."""
    data = request.get_json()
    
    event_type = data.get('type')
    email_data = data.get('data', {})
    email_id = email_data.get('email_id')
    
    if event_type == 'email.delivered':
        update_email_status(email_id, 'delivered')
    
    elif event_type == 'email.opened':
        update_email_status(
            email_id, 
            'delivered',
            opened_at=email_data.get('created_at')
        )
    
    elif event_type == 'email.clicked':
        update_email_status(
            email_id,
            'delivered',
            clicked_at=email_data.get('created_at')
        )
    
    elif event_type == 'email.bounced':
        update_email_status(email_id, 'bounced')
    
    return jsonify({'status': 'received'}), 200
```

### Step 2: Register Webhook in Resend

1. Go to Resend Dashboard → Webhooks
2. Add endpoint: `https://your-domain.com/api/webhooks/resend`
3. Select events: `email.delivered`, `email.opened`, `email.clicked`, `email.bounced`
4. Save webhook

---

## 📱 Building a Dashboard (Future)

### Frontend Component Example

```jsx
// frontend/src/pages/EmailAnalytics.jsx
import { useState, useEffect } from 'react';
import axios from 'axios';

export default function EmailAnalytics() {
  const [metrics, setMetrics] = useState(null);
  const [recentEmails, setRecentEmails] = useState([]);
  
  useEffect(() => {
    // Fetch metrics
    axios.get('/api/email-analytics/metrics?email_type=beta_launch')
      .then(res => setMetrics(res.data.metrics));
    
    // Fetch recent emails
    axios.get('/api/email-analytics/recent?limit=20')
      .then(res => setRecentEmails(res.data.emails));
  }, []);
  
  if (!metrics) return <div>Loading...</div>;
  
  return (
    <div className="email-analytics">
      <h1>Email Analytics</h1>
      
      <div className="metrics-grid">
        <MetricCard title="Total Sent" value={metrics.total_sent} />
        <MetricCard title="Delivery Rate" value={`${metrics.delivery_rate}%`} />
        <MetricCard title="Open Rate" value={`${metrics.open_rate}%`} />
        <MetricCard title="Click Rate" value={`${metrics.click_rate}%`} />
      </div>
      
      <div className="recent-emails">
        <h2>Recent Emails</h2>
        <table>
          <thead>
            <tr>
              <th>Recipient</th>
              <th>Type</th>
              <th>Status</th>
              <th>Sent At</th>
            </tr>
          </thead>
          <tbody>
            {recentEmails.map(email => (
              <tr key={email.id}>
                <td>{email.recipient_email}</td>
                <td>{email.email_type}</td>
                <td>{email.delivery_status}</td>
                <td>{new Date(email.sent_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

---

## 🎯 Quick Reference

### View All Beta Launch Emails
```bash
curl http://localhost:5000/api/email-analytics/metrics?email_type=beta_launch
```

### Check Recent 10 Emails
```bash
curl http://localhost:5000/api/email-analytics/recent?limit=10
```

### Verify Email Sent to User
```bash
curl -X POST http://localhost:5000/api/email-analytics/check-sent \
  -H "Content-Type: application/json" \
  -d '{"recipient_email": "user@example.com", "email_type": "beta_launch"}'
```

### View in Supabase
```sql
SELECT 
  recipient_email,
  email_type,
  delivery_status,
  sent_at,
  opened_at
FROM email_tracking
ORDER BY sent_at DESC
LIMIT 50;
```

---

## 📚 Related Documentation

- `docs/BETA_LAUNCH_SETUP.md` - Beta email setup guide
- `docs/EMAIL_SYSTEM_GUIDE.md` - Email system overview
- Resend Dashboard: https://resend.com/emails
- Supabase Dashboard: Your project URL

---

*Last Updated: December 22, 2025*
