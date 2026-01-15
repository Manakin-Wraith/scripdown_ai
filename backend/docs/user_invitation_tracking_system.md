# User Invitation & Signup Tracking System

## Current State (What We Have)

### auth.users Table (Supabase Auth)
Automatically tracks:
- ✅ `id` - User UUID
- ✅ `email` - User email address
- ✅ `created_at` - When account was created
- ✅ `email_confirmed_at` - When email was verified (NULL if pending)
- ✅ `last_sign_in_at` - Last login timestamp
- ✅ `confirmation_sent_at` - When confirmation email was sent

### What We Can Track NOW (No Schema Changes Needed)

**Query auth.users to see:**
1. **Total signups**: Count of all users
2. **Confirmed users**: Users with `email_confirmed_at` NOT NULL
3. **Pending confirmations**: Users with `email_confirmed_at` IS NULL
4. **Active users**: Users with `last_sign_in_at` NOT NULL
5. **Signup timeline**: Group by `created_at` date

---

## Proposed Enhancement: user_invitations Table

### Schema Design

```sql
CREATE TABLE user_invitations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT NOT NULL,
  invited_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  invited_by TEXT, -- Email of person who invited them
  source TEXT, -- 'waitlist', 'manual', 'referral', 'admin'
  status TEXT DEFAULT 'invited', -- 'invited', 'signed_up', 'confirmed', 'active'
  early_access_sent BOOLEAN DEFAULT FALSE,
  early_access_sent_at TIMESTAMP WITH TIME ZONE,
  user_id UUID REFERENCES auth.users(id), -- Linked after signup
  notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_invitations_email ON user_invitations(email);
CREATE INDEX idx_invitations_status ON user_invitations(status);
CREATE INDEX idx_invitations_user_id ON user_invitations(user_id);
```

### Status Flow

```
invited → signed_up → confirmed → active
   ↓         ↓           ↓          ↓
  (sent)  (created)  (verified)  (logged in)
```

---

## Implementation Plan

### Phase 1: Create Tracking Table (5 min)
1. Run SQL migration in Supabase Dashboard
2. Create indexes for performance

### Phase 2: Update Invitation Scripts (10 min)
1. Modify `invite_three_users.py` to log to `user_invitations`
2. Update status when user signs up
3. Update status when email confirmed

### Phase 3: Create Tracking Dashboard (15 min)
1. Script to view invitation funnel
2. Show conversion rates
3. Export CSV for analysis

### Phase 4: Automate Status Updates (20 min)
1. Database trigger to update status on auth.users changes
2. Webhook to track email opens/clicks (optional)

---

## Quick Tracking Script (No Schema Changes)

```python
# Track invitations using existing auth.users table
def get_invitation_stats():
    users = supabase.auth.admin.list_users()
    
    total = len(users)
    confirmed = sum(1 for u in users if u.email_confirmed_at)
    pending = total - confirmed
    active = sum(1 for u in users if u.last_sign_in_at)
    
    return {
        'total_signups': total,
        'confirmed': confirmed,
        'pending': pending,
        'active': active,
        'confirmation_rate': f"{(confirmed/total*100):.1f}%" if total > 0 else "0%",
        'activation_rate': f"{(active/total*100):.1f}%" if total > 0 else "0%"
    }
```

---

## Immediate Action: Track Recent Invites

### Users Invited Today (2026-01-08)

1. **megganr@moleculemedia.co.za**
   - User ID: beedc5dc-3efb-4d8e-bfed-7cbbe86af182
   - Status: Invited (confirmation pending)
   - Early Access: Sent

2. **andrevanheerden@thevideoagency.co.za**
   - User ID: ebc63e9f-8b24-4f32-81b5-475623dc3846
   - Status: Invited (confirmation pending)
   - Early Access: Sent

3. **ttntshabele@gmail.com** (Thuto)
   - User ID: abbb3465-78f0-4f82-b68e-bad3ea247916
   - Status: Invited (confirmation pending)
   - Early Access: Sent (ID: e7413690-d4c1-4e23-99de-9a24ffeb04b5)

---

## Metrics to Track

### Funnel Metrics
- **Invitation → Signup**: How many invited users create accounts
- **Signup → Confirmation**: How many confirm their email
- **Confirmation → Active**: How many log in after confirming
- **Active → Retained**: How many return after 7 days

### Time Metrics
- **Time to confirm**: created_at → email_confirmed_at
- **Time to first login**: created_at → last_sign_in_at
- **Invitation response time**: invited_at → created_at

### Source Metrics
- **Waitlist conversions**: Waitlist → Signup rate
- **Manual invites**: Admin invited → Signup rate
- **Referrals**: User referred → Signup rate

---

## Next Steps

1. **Immediate (No DB changes)**: Create tracking script using auth.users
2. **Short-term (This week)**: Add user_invitations table
3. **Medium-term (This month)**: Automate status updates with triggers
4. **Long-term (Next quarter)**: Add analytics dashboard in frontend
