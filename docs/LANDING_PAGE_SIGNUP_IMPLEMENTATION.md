# Landing Page Signup Implementation - 1 Credit Limit

## Overview
Users who sign up from the landing page get **1 script upload credit only** (no time-based trial), while direct app signups get the default 14-day trial with 1 script.

## Implementation: Strategy 1 - URL Parameter-Based Plan Selection

### Landing Page URL
```
https://app.slateone.studio/login?mode=signup&plan=free_trial&source=landing_hero
```

**Parameters:**
- `mode=signup` - Opens signup form
- `plan=free_trial` - Triggers 1-credit-only plan
- `source=landing_hero` - Tracks signup source for analytics

### Direct App Signup URL
```
https://app.slateone.studio/login?mode=signup
```
(No plan parameter = default 14-day trial with 1 script)

---

## Architecture

### Frontend Flow

1. **User clicks CTA on landing page** → Redirected to app with URL parameters
2. **User fills signup form** → `AuthContext.signup()` extracts URL params
3. **Supabase auth creates user** → Email verification sent
4. **User verifies email** → `SIGNED_IN` event fires
5. **AuthContext calls `/api/auth/set-plan`** → Backend creates profile with plan-specific limits
6. **Profile created** → User redirected to dashboard

### Backend Flow

**Endpoint:** `POST /api/auth/set-plan`

**Request Body:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "plan": "free_trial",
  "source": "landing_hero"
}
```

**Plan Logic:**
```python
if plan == 'free_trial':
    # Landing page signup
    script_upload_limit = 1
    subscription_status = 'trial'
    subscription_expires_at = None  # No time expiry
    
elif plan == 'early_access':
    # Early access users (30-day trial)
    script_upload_limit = 1
    subscription_expires_at = now + 30 days
    
else:
    # Default signup (14-day trial)
    script_upload_limit = 1
    subscription_expires_at = now + 14 days
```

**Response:**
```json
{
  "success": true,
  "profile": {...},
  "script_limit": 1,
  "trial_message": "1 script upload",
  "plan": "free_trial",
  "source": "landing_hero"
}
```

---

## Database Schema

### Profiles Table
```sql
CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  email TEXT NOT NULL,
  full_name TEXT,
  
  -- Script limits
  script_upload_limit INTEGER DEFAULT 1,
  scripts_uploaded INTEGER DEFAULT 0,
  
  -- Signup tracking
  signup_source TEXT DEFAULT 'direct',
  signup_plan TEXT,
  
  -- Subscription
  subscription_status TEXT DEFAULT 'trial',
  subscription_expires_at TIMESTAMPTZ,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Files Modified

### Backend
- **`backend/routes/auth_routes.py`**
  - Added `POST /api/auth/set-plan` endpoint
  - Validates plan parameter (only allows: `free_trial`, `early_access`, `null`)
  - Creates profile with plan-specific limits

### Frontend
- **`frontend/src/context/AuthContext.jsx`**
  - `signup()` - Extracts `plan` and `source` from URL params, stores in localStorage
  - `onAuthStateChange` - Calls `/set-plan` after email verification with stored params
  - Fallback to direct Supabase profile creation if backend fails

---

## Plan Comparison

| Plan Type | URL Parameter | Script Limit | Time Limit | Use Case |
|-----------|---------------|--------------|------------|----------|
| **Landing Page** | `plan=free_trial` | 1 script | None | Landing page CTA signups |
| **Early Access** | `plan=early_access` | 1 script | 30 days | Invited beta testers |
| **Default** | No parameter | 1 script | 14 days | Direct app signups |

---

## Security & Validation

### Parameter Validation
```python
VALID_PLANS = ['free_trial', 'early_access', None]
if plan not in VALID_PLANS:
    print(f"Warning: Invalid plan '{plan}' provided, defaulting to None")
    plan = None
```

### Attack Vectors Mitigated
1. **URL Manipulation** - Backend validates plan parameter against whitelist
2. **Unlimited Scripts** - Plan parameter cannot set `script_upload_limit > 1` for free users
3. **Invalid Plans** - Unknown plan types default to standard trial

---

## Analytics Tracking

### Signup Source Breakdown
```sql
SELECT 
  signup_source,
  signup_plan,
  COUNT(*) as signups,
  AVG(scripts_uploaded) as avg_scripts
FROM profiles
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY signup_source, signup_plan
ORDER BY signups DESC;
```

### Conversion Funnel
```sql
SELECT 
  signup_plan,
  COUNT(*) as total_signups,
  COUNT(*) FILTER (WHERE subscription_status = 'active') as converted,
  ROUND(
    COUNT(*) FILTER (WHERE subscription_status = 'active')::NUMERIC / 
    NULLIF(COUNT(*), 0) * 100, 
    2
  ) as conversion_rate_percent
FROM profiles
GROUP BY signup_plan;
```

---

## Testing Checklist

- [ ] **Landing page signup** (`?plan=free_trial&source=landing_hero`)
  - [ ] Profile created with `script_upload_limit=1`
  - [ ] `subscription_expires_at` is `NULL`
  - [ ] `signup_source='landing_hero'`
  - [ ] `signup_plan='free_trial'`
  - [ ] User can upload 1 script
  - [ ] Second upload blocked with upgrade prompt

- [ ] **Direct app signup** (no parameters)
  - [ ] Profile created with `script_upload_limit=1`
  - [ ] `subscription_expires_at` is 14 days from now
  - [ ] `signup_source='direct'`
  - [ ] `signup_plan=NULL`
  - [ ] User can upload 1 script within 14 days

- [ ] **Early access signup** (`?plan=early_access`)
  - [ ] If email in `early_access_users` table: 30-day trial
  - [ ] If not: defaults to 14-day trial

- [ ] **Invalid plan parameter** (`?plan=unlimited`)
  - [ ] Defaults to standard 14-day trial
  - [ ] Warning logged in backend

- [ ] **Analytics queries** return expected data

---

## User Experience

### Landing Page User Journey
1. Clicks "Start Free Trial" on landing page
2. Redirected to signup form
3. Enters email, password, name
4. Receives verification email
5. Clicks verification link
6. Redirected to dashboard
7. Sees "1 script upload available"
8. Uploads script → Success
9. Tries to upload second script → Blocked with upgrade modal

### Upgrade Prompt
```
🚫 Upload Limit Reached

You've used your free trial script upload.

Upgrade to unlock:
✓ Unlimited script uploads
✓ Advanced AI analysis
✓ Team collaboration
✓ Priority support

[Upgrade Now - R125 for 6 months]
```

---

## Deployment Steps

1. ✅ Backend changes deployed to production
2. ✅ Frontend changes deployed to production
3. 🔄 Update landing page CTA link with new URL parameters
4. 🔄 Test signup flow end-to-end
5. 🔄 Monitor analytics for signup source tracking

---

## Future Enhancements

- [ ] A/B test different credit limits (1 vs 3 scripts)
- [ ] Email notification when upload limit reached
- [ ] Automatic upgrade prompts in UI
- [ ] Referral program integration
- [ ] Custom landing page variants with different plans

---

## Support & Troubleshooting

### Common Issues

**Issue:** User signed up from landing page but got 14-day trial
- **Cause:** URL parameters not passed correctly
- **Fix:** Verify landing page link includes `?plan=free_trial&source=landing_hero`

**Issue:** Profile not created after email verification
- **Cause:** Backend `/set-plan` endpoint error
- **Fix:** Check backend logs, fallback creates basic profile via Supabase

**Issue:** Analytics showing wrong signup source
- **Cause:** `source` parameter missing or incorrect
- **Fix:** Ensure landing page link includes `&source=landing_hero`

### Debug Queries

**Check user's plan:**
```sql
SELECT 
  email,
  signup_plan,
  signup_source,
  script_upload_limit,
  scripts_uploaded,
  subscription_status,
  subscription_expires_at
FROM profiles
WHERE email = 'user@example.com';
```

**Recent landing page signups:**
```sql
SELECT *
FROM profiles
WHERE signup_plan = 'free_trial'
  AND signup_source = 'landing_hero'
ORDER BY created_at DESC
LIMIT 10;
```

---

## Contact

For questions or issues:
- Development team: dev@slateone.studio
- Documentation: `/docs/free-trial-implementation.md`
