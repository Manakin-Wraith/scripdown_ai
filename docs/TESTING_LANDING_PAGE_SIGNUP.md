# Testing Landing Page Signup - 1 Credit Implementation

## Quick Test Guide

### Test 1: Landing Page Signup (1 Credit Only)

**URL to test:**
```
http://localhost:3000/login?mode=signup&plan=free_trial&source=landing_hero
```

**Expected Behavior:**
1. Signup form opens
2. User enters: email, password, name
3. Verification email sent
4. User clicks verification link
5. Profile created with:
   - `script_upload_limit = 1`
   - `subscription_expires_at = NULL` (no time limit)
   - `signup_plan = 'free_trial'`
   - `signup_source = 'landing_hero'`
6. User can upload 1 script
7. Second upload attempt shows upgrade modal

**Console Logs to Verify:**
```
Profile created: 1 script upload, plan=free_trial, source=landing_hero
```

---

### Test 2: Direct App Signup (14-Day Trial)

**URL to test:**
```
http://localhost:3000/login?mode=signup
```

**Expected Behavior:**
1. Signup form opens
2. User enters: email, password, name
3. Verification email sent
4. User clicks verification link
5. Profile created with:
   - `script_upload_limit = 1`
   - `subscription_expires_at = NOW() + 14 days`
   - `signup_plan = NULL`
   - `signup_source = 'direct'`
6. User can upload 1 script within 14 days

**Console Logs to Verify:**
```
Profile created: 14 days trial with 1 script, plan=null, source=direct
```

---

### Test 3: Invalid Plan Parameter (Security)

**URL to test:**
```
http://localhost:3000/login?mode=signup&plan=unlimited&source=hacker
```

**Expected Behavior:**
1. Backend validates plan parameter
2. Invalid plan rejected, defaults to standard trial
3. Profile created with default 14-day trial settings

**Backend Logs to Verify:**
```
Warning: Invalid plan 'unlimited' provided, defaulting to None
Profile created/updated for user@example.com: plan=None, source=hacker, limit=1
```

---

## Database Verification Queries

### Check Profile After Signup

```sql
SELECT 
  email,
  full_name,
  script_upload_limit,
  scripts_uploaded,
  signup_plan,
  signup_source,
  subscription_status,
  subscription_expires_at,
  created_at
FROM profiles
WHERE email = 'test@example.com';
```

**Expected for Landing Page Signup:**
```
email: test@example.com
script_upload_limit: 1
scripts_uploaded: 0
signup_plan: free_trial
signup_source: landing_hero
subscription_status: trial
subscription_expires_at: NULL
```

**Expected for Direct Signup:**
```
email: test@example.com
script_upload_limit: 1
scripts_uploaded: 0
signup_plan: NULL
signup_source: direct
subscription_status: trial
subscription_expires_at: 2026-02-10T... (14 days from now)
```

---

## API Endpoint Testing

### Test /set-plan Endpoint Directly

**Request:**
```bash
curl -X POST http://localhost:5000/api/auth/set-plan \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-uuid-here",
    "email": "test@example.com",
    "full_name": "Test User",
    "plan": "free_trial",
    "source": "landing_hero"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "profile": {
    "id": "test-uuid-here",
    "email": "test@example.com",
    "script_upload_limit": 1,
    "signup_plan": "free_trial",
    "signup_source": "landing_hero"
  },
  "script_limit": 1,
  "trial_message": "1 script upload",
  "plan": "free_trial",
  "source": "landing_hero"
}
```

---

## Frontend Testing

### Check localStorage After Signup

**Before Email Verification:**
```javascript
localStorage.getItem('pending_profile_name')    // "Test User"
localStorage.getItem('pending_profile_email')   // "test@example.com"
localStorage.getItem('pending_profile_plan')    // "free_trial"
localStorage.getItem('pending_profile_source')  // "landing_hero"
```

**After Email Verification:**
All localStorage items should be cleared.

---

## Upload Limit Testing

### Test Script Upload Limit

1. **First Upload:**
   - Should succeed
   - `scripts_uploaded` increments to 1

2. **Second Upload Attempt:**
   - Should be blocked
   - Error message: "Trial users can only upload 1 script. Upgrade for unlimited scripts."
   - Upgrade modal shown

**API Call to Test:**
```bash
curl -X POST http://localhost:5000/api/auth/can-upload-script \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-uuid-here"
  }'
```

**Expected Response (After 1 Upload):**
```json
{
  "can_upload": false,
  "message": "Trial users can only upload 1 script. Upgrade for unlimited scripts.",
  "upgrade_url": "https://pay.yoco.com/r/mEDpxp"
}
```

---

## Analytics Testing

### Verify Signup Source Tracking

```sql
-- Count signups by source
SELECT 
  signup_source,
  signup_plan,
  COUNT(*) as count
FROM profiles
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY signup_source, signup_plan
ORDER BY count DESC;
```

**Expected Results:**
```
signup_source    | signup_plan  | count
-----------------|--------------|------
landing_hero     | free_trial   | 5
direct           | NULL         | 3
```

---

## Error Scenarios to Test

### 1. Backend Unavailable
- Frontend should fallback to direct Supabase profile creation
- User still gets basic profile (without plan-specific limits)

### 2. Invalid User ID
- Backend returns 400 error
- Frontend shows error message

### 3. Duplicate Profile Creation
- Upsert should update existing profile
- No duplicate entries created

### 4. Missing URL Parameters
- Should default to standard trial
- No errors thrown

---

## Production Deployment Checklist

- [ ] Backend deployed with `/set-plan` endpoint
- [ ] Frontend deployed with updated AuthContext
- [ ] Landing page updated with new URL:
  ```
  https://app.slateone.studio/login?mode=signup&plan=free_trial&source=landing_hero
  ```
- [ ] Test signup flow end-to-end in production
- [ ] Verify analytics tracking in database
- [ ] Monitor error logs for first 24 hours
- [ ] Create test account from landing page
- [ ] Verify upgrade flow works correctly

---

## Rollback Plan

If issues occur:

1. **Quick Fix:** Update landing page to remove URL parameters
   - Users will get default 14-day trial instead
   
2. **Backend Rollback:** Disable `/set-plan` endpoint
   - AuthContext will fallback to direct Supabase profile creation
   
3. **Full Rollback:** Revert both frontend and backend changes
   - All users get default trial behavior

---

## Success Metrics

After 1 week, verify:

- [ ] Landing page signups have `signup_plan='free_trial'`
- [ ] Direct signups have `signup_plan=NULL`
- [ ] No errors in backend logs related to `/set-plan`
- [ ] Conversion rate from landing page signups tracked
- [ ] Upgrade prompts shown correctly to 1-credit users
