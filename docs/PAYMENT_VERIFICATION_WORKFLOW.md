# Payment Verification Workflow

## Overview
Manual admin verification system for credit purchases since Yoco doesn't provide webhooks.

---

## User Experience

### 1. Purchase Flow
1. User clicks "Buy Now" on credit package
2. System creates purchase record with `status = 'pending'`
3. User redirected to Yoco payment link
4. After payment, user returns to app
5. Sees message: **"Payment submitted! Your credits will be activated within 1 hour once verified."**

### 2. Notification
- User receives email when admin approves payment
- Credits appear immediately in account
- User can continue uploading scripts

---

## Admin Workflow

### 1. Access Admin Panel
- Navigate to `/admin/payments` (superuser only)
- View list of pending payments

### 2. Verify Payment
1. Open **Yoco Dashboard**: https://portal.yoco.com/online/payments
2. Match payment by:
   - User email
   - Amount (R49, R220, R390, R860)
   - Timestamp
3. Copy Yoco reference number (optional)

### 3. Approve Payment
1. Click **"Approve"** button in SlateOne admin panel
2. Enter Yoco reference number (optional)
3. Add verification notes (optional)
4. Confirm approval
5. **Credits instantly added to user account**
6. User receives email notification

### 4. Reject Payment (if needed)
1. Click **"Reject"** button
2. Enter rejection reason
3. Confirm rejection
4. User receives email notification

---

## Database Schema

### New Fields in `script_credit_purchases`
```sql
verified_by UUID          -- Admin who verified
verified_at TIMESTAMPTZ   -- When verified
verification_notes TEXT   -- Admin notes
admin_reference TEXT      -- Yoco reference number
```

---

## API Endpoints

### Admin Endpoints (Superuser Only)

#### Get Pending Payments
```
GET /api/admin/payments/pending
Response: List of pending purchases
```

#### Approve Payment
```
POST /api/admin/payments/{purchase_id}/approve
Body: {
  admin_reference: "yoco_ref_123",  // optional
  notes: "Verified in Yoco dashboard"  // optional
}
Response: Success + credits added count
```

#### Reject Payment
```
POST /api/admin/payments/{purchase_id}/reject
Body: {
  reason: "Payment not found in Yoco"
}
Response: Success message
```

---

## Implementation Files

### Backend
- `backend/db/migrations/017_fix_payment_reference_constraint.sql` - Fix NULL constraint
- `backend/db/migrations/018_add_verification_fields.sql` - Add verification tracking
- `backend/routes/admin_routes.py` - Admin API endpoints (lines 333-476)
- `backend/services/credit_service.py` - Payment completion logic

### Frontend
- `frontend/src/components/admin/PaymentVerification.jsx` - Admin UI
- `frontend/src/components/admin/PaymentVerification.css` - Styling

---

## Setup Instructions

### 1. Apply Database Migrations
Run in Supabase SQL Editor:

```sql
-- Migration 017: Fix payment_reference constraint
ALTER TABLE script_credit_purchases 
DROP CONSTRAINT IF EXISTS unique_payment_reference;

CREATE UNIQUE INDEX IF NOT EXISTS unique_payment_reference_not_null 
ON script_credit_purchases(payment_reference) 
WHERE payment_reference IS NOT NULL;

-- Migration 018: Add verification fields
ALTER TABLE script_credit_purchases 
ADD COLUMN IF NOT EXISTS verified_by UUID REFERENCES auth.users(id),
ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS verification_notes TEXT,
ADD COLUMN IF NOT EXISTS admin_reference TEXT;

CREATE INDEX IF NOT EXISTS idx_credit_purchases_pending 
ON script_credit_purchases(status, created_at) 
WHERE status = 'pending';
```

### 2. Add Admin Route to Frontend
Add to your admin dashboard router:
```jsx
import PaymentVerification from './components/admin/PaymentVerification';

// In your admin routes
<Route path="/admin/payments" element={<PaymentVerification />} />
```

### 3. Test Flow
1. Create test purchase (don't actually pay)
2. Check it appears in admin panel
3. Approve it manually
4. Verify credits added to user account

---

## Email Notifications (TODO)

Add email notifications in `backend/services/email_service.py`:

### Approval Email
```python
def send_credits_approved_email(user_email, credits_added):
    """Send email when credits are approved"""
    subject = "Your Credits Have Been Activated!"
    html = f"""
    <h2>Payment Confirmed</h2>
    <p>{credits_added} credits have been added to your account.</p>
    <p>You can now upload scripts!</p>
    <a href="{FRONTEND_URL}/upload">Upload Script</a>
    """
    # Send via Resend
```

### Rejection Email
```python
def send_payment_rejected_email(user_email, reason):
    """Send email when payment is rejected"""
    subject = "Payment Verification Issue"
    html = f"""
    <h2>Payment Could Not Be Verified</h2>
    <p>Reason: {reason}</p>
    <p>Please contact support if you believe this is an error.</p>
    """
    # Send via Resend
```

---

## Best Practices

### For Admin Team
1. **Check Yoco daily** (or set up email alerts)
2. **Verify within 1 hour** of purchase
3. **Always add Yoco reference** for audit trail
4. **Add notes** if anything unusual
5. **Double-check email match** before approving

### For Users
- Clear messaging about verification time
- Email confirmation when approved
- Support contact if delayed

---

## Future Enhancements

### Phase 2 (Optional)
1. **Yoco API Integration** (if they add API support)
   - Automatic verification via API polling
   - Reduce admin workload to 0%

2. **Email Alerts for Admin**
   - Send email to admin when new payment pending
   - Include direct approval link

3. **Analytics Dashboard**
   - Average verification time
   - Pending payment alerts
   - Revenue tracking

4. **Bulk Actions**
   - Approve multiple payments at once
   - Export pending payments to CSV

---

## Troubleshooting

### Payment Not Appearing in Admin Panel
- Check purchase was created (status = 'pending')
- Verify admin has superuser role
- Check browser console for API errors

### Credits Not Added After Approval
- Check `script_credit_purchases` status changed to 'completed'
- Verify `profiles.script_credits` increased
- Check backend logs for errors

### User Says They Paid But No Record
- Check Yoco dashboard for payment
- Search by email in database
- May need to manually create purchase record

---

## Support Contacts

- **Yoco Support**: support@yoco.com
- **Yoco Portal**: https://portal.yoco.com
- **SlateOne Admin**: /admin/payments

---

## Metrics to Track

- Average verification time
- Pending payment count
- Approval rate
- Rejection reasons
- User complaints about delays

**Target SLA**: Verify within 1 hour during business hours
