# Revenue Tracking Verification Guide

## Overview
This document outlines how Total Revenue is calculated and displayed in the admin analytics dashboard after payment approvals.

---

## Revenue Calculation Flow

### 1. Payment Approval Process
When an admin approves a payment in `/admin/payments`:

```
User purchases credits → Payment status: "pending"
↓
Admin approves payment → Payment status: "completed"
↓
Credits added to user account
↓
Revenue metric updates automatically
```

### 2. Backend Revenue Calculation

**File:** `backend/services/analytics_service.py`

**Method:** `get_subscription_metrics()`

```python
# Get completed credit purchases (approved payments)
payments_result = self.supabase.table('script_credit_purchases')\
    .select('id, amount, status')\
    .eq('status', 'completed')\
    .execute()

total_revenue = sum(p.get('amount', 0) for p in payments_result.data or [])
successful_payments = len(payments_result.data or [])
```

**Key Points:**
- Only counts payments with `status = 'completed'`
- Sums the `amount` field from all completed purchases
- Returns total revenue in ZAR (South African Rand)

### 3. Frontend Display

**File:** `frontend/src/pages/Admin/AnalyticsDashboard.jsx`

**Location:** Subscription Metrics section

```jsx
<MetricCard
  title="Total Revenue"
  value={`R${subscription_metrics?.total_revenue || 0}`}
  icon={<TrendingUp size={24} />}
  trend={`${subscription_metrics?.successful_payments || 0} payments`}
  color="green"
/>
```

---

## Testing the Revenue Flow

### Step 1: Check Current Revenue
1. Navigate to `/admin` (Analytics Dashboard)
2. Note the current "Total Revenue" value
3. Note the number of "payments" shown in the trend

### Step 2: Approve a Payment
1. Navigate to `/admin/payments` (Payment Verification)
2. Click "Approve" on a pending payment
3. Fill in optional Yoco reference and notes
4. Submit approval
5. Wait for success toast notification

### Step 3: Verify Revenue Update
1. Navigate back to `/admin` (Analytics Dashboard)
2. Click "Refresh" button in header
3. Verify "Total Revenue" has increased by the payment amount
4. Verify "payments" count has increased by 1

### Example:
```
Before Approval:
- Total Revenue: R1,250.00
- 3 payments

After Approving R390.00 payment:
- Total Revenue: R1,640.00
- 4 payments
```

---

## Database Schema

### script_credit_purchases Table

**Relevant Columns:**
- `id` (UUID) - Primary key
- `amount` (DECIMAL) - Payment amount in ZAR
- `status` (TEXT) - Payment status: 'pending', 'completed', 'failed'
- `credits_purchased` (INTEGER) - Number of credits
- `created_at` (TIMESTAMP) - Purchase timestamp
- `verified_at` (TIMESTAMP) - Approval timestamp
- `verified_by` (UUID) - Admin who approved

**Status Flow:**
```
pending → completed (via admin approval)
pending → failed (via admin rejection)
```

---

## API Endpoints

### Get Analytics Overview
```
GET /api/admin/payments/pending
Authorization: Bearer {token}

Response:
{
  "success": true,
  "global_stats": {...},
  "subscription_metrics": {
    "total_revenue": 1640.00,
    "successful_payments": 4,
    ...
  }
}
```

### Approve Payment
```
POST /api/admin/payments/{purchase_id}/approve
Authorization: Bearer {token}
Content-Type: application/json

Body:
{
  "admin_reference": "YC-123456",
  "notes": "Verified in Yoco dashboard"
}

Response:
{
  "success": true,
  "message": "Payment approved and credits added"
}
```

---

## Troubleshooting

### Revenue Not Updating

**Check 1: Payment Status**
```sql
SELECT id, amount, status, verified_at 
FROM script_credit_purchases 
WHERE id = '{purchase_id}';
```
- Verify status changed to 'completed'
- Verify verified_at timestamp is set

**Check 2: Backend Logs**
```bash
# Check backend logs for errors
tail -f backend/backend.log
```

**Check 3: Manual Refresh**
- Click "Refresh" button in Analytics Dashboard
- Check browser console for API errors
- Verify network request returns updated data

**Check 4: Database Query**
```sql
SELECT 
  COUNT(*) as total_payments,
  SUM(amount) as total_revenue
FROM script_credit_purchases
WHERE status = 'completed';
```

### Common Issues

1. **Revenue shows R0**
   - No completed payments in database
   - Check if payments are stuck in 'pending' status

2. **Revenue not increasing after approval**
   - Backend not restarted after analytics_service.py update
   - Frontend cache not cleared (hard refresh: Cmd+Shift+R)
   - API endpoint returning stale data

3. **Wrong revenue amount**
   - Check currency conversion (should be ZAR)
   - Verify amount field in database matches Yoco payment

---

## Auto-Refresh Mechanism

The Analytics Dashboard automatically refreshes payment stats every 30 seconds:

```javascript
// Auto-refresh payment stats every 30 seconds
const interval = setInterval(() => {
  loadPaymentStats();
}, 30000);
```

**Manual Refresh:**
- Click "Refresh" button in dashboard header
- Navigate away and back to `/admin`

---

## Expected Behavior

✅ **Correct Flow:**
1. Admin approves payment → Status changes to 'completed'
2. Credits added to user account
3. Toast notification: "Payment approved! Credits added to user account."
4. Payment removed from pending list
5. Analytics dashboard shows updated revenue (after refresh)

❌ **Incorrect Behavior:**
- Revenue stays at R0 after approvals
- Revenue decreases after approval
- Payment count doesn't increase
- Old revenue value persists after refresh

---

## Verification Checklist

Before marking this feature as complete, verify:

- [ ] Backend calculates revenue from `script_credit_purchases` table
- [ ] Only `status = 'completed'` payments are counted
- [ ] Frontend displays revenue in correct format (R{amount})
- [ ] Payment count matches number of completed purchases
- [ ] Revenue updates after payment approval
- [ ] Manual refresh button works
- [ ] Auto-refresh updates payment stats every 30 seconds
- [ ] Toast notifications appear on approve/reject
- [ ] Custom modals replace browser dialogs
- [ ] Revenue metric visible in Subscription Metrics section

---

## Related Files

**Backend:**
- `backend/services/analytics_service.py` - Revenue calculation
- `backend/routes/admin_routes.py` - API endpoints
- `backend/db/migrations/018_add_verification_fields.sql` - Database schema

**Frontend:**
- `frontend/src/pages/Admin/AnalyticsDashboard.jsx` - Dashboard display
- `frontend/src/components/admin/PaymentVerification.jsx` - Approval UI
- `frontend/src/components/admin/ApproveModal.jsx` - Approval modal
- `frontend/src/components/admin/Toast.jsx` - Success notifications

---

## Next Steps

1. **Restart Backend:**
   ```bash
   cd backend
   source ../venv/bin/activate
   python3 app.py
   ```

2. **Hard Refresh Frontend:**
   - Press Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows/Linux)

3. **Test Complete Flow:**
   - Approve a pending payment
   - Navigate to analytics dashboard
   - Verify revenue increased by payment amount

4. **Monitor for Issues:**
   - Check backend logs for errors
   - Verify database updates correctly
   - Test with multiple payment approvals

---

Last Updated: January 27, 2026
