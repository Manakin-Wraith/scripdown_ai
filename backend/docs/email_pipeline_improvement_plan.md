# Email Pipeline Improvement Plan

## Current Problem

**Issue:** Waitlist emails from `www.slateone.studio` are not being sent automatically.

**Current Setup:**
- Marketing site: `www.slateone.studio` (separate from main app)
- Waitlist form captures emails → Supabase Notel project (different database)
- No automated email sending configured
- Result: Users join waitlist but never receive early access emails

---

## Immediate Solution (For 3 Current Users)

### Step 1: Add Notel Supabase Credentials

Add to `backend/.env`:
```bash
# Notel Supabase Project (for waitlist)
NOTEL_SUPABASE_URL=https://your-notel-project.supabase.co
NOTEL_SUPABASE_SERVICE_KEY=your-notel-service-key
```

### Step 2: Run Waitlist Script

```bash
cd backend
python scripts/send_waitlist_early_access.py
```

**What it does:**
1. Fetches users from Notel `waitlist` table
2. Registers them in main SlateOne `early_access_users` table
3. Sends enhanced early access emails (10/10 spam score + 3-decision framework)

**Manual Mode:** If Notel credentials aren't available, script allows manual email entry.

---

## Long-Term Pipeline Architecture

### Option 1: Unified Database (Recommended)

**Move waitlist to main SlateOne Supabase project**

**Pros:**
- Single source of truth
- Easier to manage
- No cross-project complexity
- Automated workflows possible

**Cons:**
- Requires updating marketing site form
- One-time migration needed

**Implementation:**
```
1. Create waitlist table in main Supabase project
2. Update www.slateone.studio form to use main Supabase
3. Set up Supabase Edge Function to auto-send emails on insert
4. Migrate existing 3 users
```

---

### Option 2: Cross-Project Sync

**Keep separate databases, sync via webhook**

**Pros:**
- Marketing site stays independent
- No form changes needed

**Cons:**
- More complex architecture
- Two databases to maintain
- Potential sync issues

**Implementation:**
```
1. Set up webhook on Notel waitlist table insert
2. Webhook calls SlateOne API endpoint
3. API registers user + sends email
4. Requires webhook endpoint security
```

---

### Option 3: Scheduled Sync Job

**Periodic script checks Notel for new users**

**Pros:**
- Simple to implement
- No real-time dependencies

**Cons:**
- Delayed email sending
- Requires cron job setup
- Not ideal for user experience

**Implementation:**
```
1. Deploy send_waitlist_early_access.py as cron job
2. Runs every hour/day
3. Checks for new waitlist users
4. Sends emails to unprocessed users
```

---

## Recommended Approach

### Phase 1: Immediate (Today)
1. ✅ Add Notel credentials to `.env`
2. ✅ Run `send_waitlist_early_access.py` for 3 current users
3. ✅ Verify emails delivered

### Phase 2: Short-term (This Week)
1. **Create waitlist table in main Supabase:**
   ```sql
   CREATE TABLE waitlist (
     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
     email TEXT UNIQUE NOT NULL,
     first_name TEXT,
     source TEXT DEFAULT 'website',
     status TEXT DEFAULT 'pending',
     created_at TIMESTAMPTZ DEFAULT NOW(),
     email_sent_at TIMESTAMPTZ
   );
   ```

2. **Set up Supabase Edge Function:**
   ```typescript
   // On waitlist insert → send email
   supabase
     .channel('waitlist-emails')
     .on('postgres_changes', {
       event: 'INSERT',
       schema: 'public',
       table: 'waitlist'
     }, async (payload) => {
       await sendEarlyAccessEmail(payload.new.email, payload.new.first_name);
     })
     .subscribe();
   ```

3. **Update marketing site form:**
   - Point to main Supabase project
   - Use Supabase client-side SDK
   - Or create API endpoint in SlateOne backend

### Phase 3: Long-term (Next Sprint)
1. **Automated email sequences:**
   - Welcome email (immediate)
   - Reminder email (3 days later if no signup)
   - Feature updates (weekly)

2. **Email tracking:**
   - Track opens/clicks
   - A/B test subject lines
   - Monitor spam rates

3. **Unsubscribe handling:**
   - Create `/unsubscribe` page
   - Update database on unsubscribe
   - Respect unsubscribe preferences

---

## Email Pipeline Best Practices

### 1. Single Source of Truth
- All email addresses in one database
- Clear status tracking (pending, invited, signed_up, unsubscribed)

### 2. Automated Triggers
- Use database triggers or Edge Functions
- Send emails immediately on user action
- No manual intervention needed

### 3. Email Service Abstraction
```python
# Good: Centralized email service
from services.email_service import send_early_access_reminder

# Bad: Direct Resend calls scattered everywhere
resend.Emails.send(...)
```

### 4. Error Handling & Retry
```python
# Track email send status
{
  'email_sent': True/False,
  'email_sent_at': timestamp,
  'email_error': error_message,
  'retry_count': 0
}
```

### 5. Rate Limiting
- Respect Resend limits (2 req/sec)
- Batch processing with delays
- Queue system for large volumes

---

## Migration Checklist

### Immediate Actions
- [ ] Add Notel credentials to `.env`
- [ ] Run waitlist script for 3 users
- [ ] Verify email delivery

### This Week
- [ ] Create waitlist table in main Supabase
- [ ] Set up automated email trigger
- [ ] Update marketing site form
- [ ] Migrate existing waitlist users
- [ ] Test end-to-end flow

### Next Sprint
- [ ] Implement email sequences
- [ ] Add email tracking
- [ ] Create unsubscribe page
- [ ] Set up monitoring/alerts

---

## Testing Plan

### Test 1: Manual Send (Today)
```bash
python scripts/send_waitlist_early_access.py
# Enter test email
# Verify delivery
```

### Test 2: Form Submission (After Migration)
```
1. Submit form on www.slateone.studio
2. Check main Supabase waitlist table
3. Verify email received within 1 minute
4. Check email_sent_at timestamp updated
```

### Test 3: Error Handling
```
1. Submit invalid email
2. Verify error logged
3. Submit duplicate email
4. Verify no duplicate email sent
```

---

## Monitoring & Alerts

### Key Metrics
- Waitlist signups per day
- Email delivery rate
- Email open rate
- Signup conversion rate (waitlist → active user)

### Alerts
- Email send failures > 5%
- Waitlist form errors
- Resend API errors
- Database connection issues

---

## Files Created

1. **`backend/scripts/send_waitlist_early_access.py`**
   - Immediate solution for 3 current users
   - Supports both Notel fetch and manual entry
   - Registers users in main project
   - Sends enhanced early access emails

2. **`backend/docs/email_pipeline_improvement_plan.md`** (this file)
   - Complete architecture analysis
   - Recommended approach
   - Migration checklist
   - Testing plan

---

## Next Steps

1. **Run the script now:**
   ```bash
   cd backend
   python scripts/send_waitlist_early_access.py
   ```

2. **Choose architecture:**
   - Recommended: Option 1 (Unified Database)
   - Implement this week

3. **Set up monitoring:**
   - Track email delivery
   - Monitor conversion rates

4. **Document process:**
   - Update README with waitlist flow
   - Add to onboarding docs
