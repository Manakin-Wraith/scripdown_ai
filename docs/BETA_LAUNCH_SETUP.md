# Beta Launch Email - Setup & Usage Guide

## Overview
Complete setup guide for sending beta launch invitation emails to users.

---

## Prerequisites

### 1. Email Service Configuration
Ensure Resend is configured in your `.env` file:

```bash
RESEND_API_KEY=your_resend_api_key_here
RESEND_FROM_EMAIL=hello@slateone.studio  # or your verified domain
FRONTEND_URL=https://slateone.studio
```

### 2. Beta Email Address
Set up **beta@slateone.studio** to receive:
- Referral submissions
- User questions
- Beta feedback

---

## Testing the Email

### Option 1: Test Script (Recommended)

```bash
cd backend
python scripts/test_beta_launch_email.py
```

**Interactive prompts:**
1. Enter test email address
2. Enter test user name
3. Select user status (new/trial/waitlist)

**Example:**
```
🎬 SlateOne Beta Launch Email Test
==================================================

Enter test email address: you@example.com
Enter test user name (default: Test User): John Doe
Select user status:
1. New user (default)
2. Trial user
3. Waitlist user
Enter choice (1-3): 1

📧 Sending beta launch email to: you@example.com
👤 User name: John Doe
📊 User status: new

Sending...
✅ Email sent successfully!
📬 Email ID: abc123xyz
```

### Option 2: Python Script

```python
from services.email_service import send_beta_launch_email

result = send_beta_launch_email(
    to_email="test@example.com",
    user_name="Test User",
    user_status="new"  # 'new', 'trial', or 'waitlist'
)

print(result)
```

---

## API Endpoints

### 1. Send Single Email

**Endpoint:** `POST /api/beta/send-launch-email`

**Request:**
```json
{
  "email": "user@example.com",
  "full_name": "John Doe",
  "user_status": "new"
}
```

**Response:**
```json
{
  "message": "Beta launch email sent successfully",
  "email_id": "abc123xyz"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:5000/api/beta/send-launch-email \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "full_name": "John Doe",
    "user_status": "new"
  }'
```

### 2. Send Bulk Emails

**Endpoint:** `POST /api/beta/send-bulk-launch-emails`

**Request:**
```json
{
  "users": [
    {
      "email": "user1@example.com",
      "full_name": "John Doe",
      "user_status": "new"
    },
    {
      "email": "user2@example.com",
      "full_name": "Jane Smith",
      "user_status": "trial"
    }
  ]
}
```

**Response:**
```json
{
  "message": "Bulk email send complete",
  "sent": 2,
  "failed": 0,
  "total": 2,
  "results": [
    {
      "email": "user1@example.com",
      "status": "sent",
      "email_id": "abc123"
    },
    {
      "email": "user2@example.com",
      "status": "sent",
      "email_id": "xyz789"
    }
  ]
}
```

### 3. Track Referral (Manual)

**Endpoint:** `POST /api/beta/track-referral`

**Request:**
```json
{
  "referrer_email": "referrer@example.com",
  "referred_emails": [
    "friend1@example.com",
    "friend2@example.com",
    "friend3@example.com"
  ]
}
```

**Response:**
```json
{
  "message": "Referral tracked successfully",
  "referrer_email": "referrer@example.com",
  "referred_count": 3,
  "note": "Manual verification required. Email beta@slateone.studio to claim reward."
}
```

---

## Email Variants

### Variant 1: New User
**Greeting:** "SlateOne is officially in beta — and you're invited to be among the first."  
**CTA:** "Get Beta Access - R125"

### Variant 2: Trial User
**Greeting:** "Your trial ends soon — upgrade to beta and keep everything you've built."  
**CTA:** "Upgrade to Beta - Keep Your Scripts"

### Variant 3: Waitlist User
**Greeting:** "You're in! Your early access spot is ready."  
**CTA:** "Claim Your Beta Access"

---

## Sending to Your User List

### Step 1: Export User List from Supabase

```sql
-- Get all users who haven't received beta email yet
SELECT 
  email,
  raw_user_meta_data->>'full_name' as full_name,
  created_at
FROM auth.users
WHERE email NOT IN (
  SELECT email FROM beta_emails_sent  -- Create this tracking table
)
ORDER BY created_at DESC;
```

### Step 2: Prepare CSV

Create `beta_users.csv`:
```csv
email,full_name,user_status
user1@example.com,John Doe,new
user2@example.com,Jane Smith,trial
user3@example.com,Bob Wilson,waitlist
```

### Step 3: Send via Script

```python
import csv
from services.email_service import send_beta_launch_email

with open('beta_users.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        result = send_beta_launch_email(
            to_email=row['email'],
            user_name=row['full_name'],
            user_status=row['user_status']
        )
        print(f"Sent to {row['email']}: {result}")
```

---

## Referral Tracking (Manual Process)

### Current Implementation
- Users forward email to 3 friends
- Friends sign up
- User emails **beta@slateone.studio** with:
  - Their email
  - Friends' emails who signed up
- You manually verify and add 1 month to their account

### Verification Process
1. Check beta@slateone.studio inbox
2. Verify referred users actually signed up
3. Update user's subscription in Supabase:
   ```sql
   UPDATE profiles
   SET subscription_end_date = subscription_end_date + INTERVAL '1 month'
   WHERE email = 'referrer@example.com';
   ```

### Future: Automated Referral System
When ready to automate:
1. Create `referrals` table
2. Generate unique referral codes per user
3. Track sign-ups via referral code
4. Auto-apply rewards at milestones (3, 5, 10 referrals)

---

## Best Practices

### Timing
- **Avoid:** Late Friday, weekends, major holidays
- **Best:** Tuesday-Thursday, 10am-2pm user's timezone
- **Current:** December 23, 2025 - Holiday season, so expect lower open rates

### Segmentation
1. **Trial Users (Urgent)**: Send first - they're already engaged
2. **Waitlist Users**: Send second - they're expecting it
3. **New/Cold Users**: Send last - lowest priority

### Rate Limiting
- Resend free tier: 100 emails/day
- Resend paid tier: 50,000 emails/month
- Recommended: Send in batches of 50-100 per hour

### Testing Checklist
- [ ] Test email renders in Gmail
- [ ] Test email renders in Outlook
- [ ] Test email renders on mobile
- [ ] Verify all links work (slateone.studio)
- [ ] Check spam score (mail-tester.com)
- [ ] Send to test group (10-20 users) first

---

## Monitoring & Metrics

### Track These Metrics
1. **Delivery Rate**: % of emails successfully delivered
2. **Open Rate**: Target >25% (industry avg: 21%)
3. **Click Rate**: Target >8% (industry avg: 2.6%)
4. **Conversion Rate**: Target >3% (beta launch avg: 2-5%)
5. **Referrals**: Track manual submissions to beta@slateone.studio

### Resend Dashboard
- View sent emails: https://resend.com/emails
- Check delivery status
- Monitor bounces and complaints
- Track click-through rates

---

## Troubleshooting

### Email Not Sending
```python
from services.email_service import is_configured

if not is_configured():
    print("❌ RESEND_API_KEY not set in .env")
else:
    print("✅ Email service configured")
```

### Email Goes to Spam
1. Verify SPF, DKIM, DMARC records in Resend dashboard
2. Use verified domain (hello@slateone.studio, not @resend.dev)
3. Test with mail-tester.com
4. Warm up domain gradually (start with small batches)

### Wrong Email Variant Sent
Check `user_status` parameter:
- Must be exactly: `'new'`, `'trial'`, or `'waitlist'`
- Case-sensitive
- Default is `'new'` if not specified

---

## Next Steps After Launch

1. **Monitor Responses**
   - Check beta@slateone.studio daily
   - Respond to questions within 24 hours
   - Track referral submissions

2. **Follow-Up Sequence** (Optional)
   - Day 3: Reminder email for non-openers
   - Day 7: Last chance email
   - Day 14: Survey for non-converters

3. **Automate Referrals**
   - Build referral tracking system
   - Create referral dashboard
   - Auto-apply rewards

4. **A/B Testing**
   - Test different subject lines
   - Test different CTAs
   - Test different pricing presentations

---

## Support

- **Email Issues**: Check Resend dashboard or contact Resend support
- **API Issues**: Check backend logs at `backend/logs/`
- **Questions**: Email beta@slateone.studio

---

*Last Updated: December 22, 2025*
