# Free Trial Implementation Guide

## Overview
This document outlines the implementation for allocating 1 script upload to users who sign up via the landing page free trial CTA.

## Architecture

### Frontend (Landing Page)
- **URL**: `https://app.slateone.studio/login?mode=signup&plan=free_trial&source=landing_hero`
- **Parameters**:
  - `mode=signup`: Indicates signup flow
  - `plan=free_trial`: Specifies the free trial plan (1 script upload)
  - `source=landing_hero`: Tracks signup source for analytics

### Backend (app.slateone.studio)
The backend needs to read these URL parameters during signup and configure the user account accordingly.

## Database Schema

### Profiles Table Additions
```sql
-- New columns added via migration: add_script_limits_to_profiles.sql
script_upload_limit INTEGER DEFAULT NULL  -- NULL = unlimited (paid users)
scripts_uploaded INTEGER DEFAULT 0        -- Current upload count
signup_source TEXT DEFAULT 'direct'       -- Source tracking
signup_plan TEXT DEFAULT NULL             -- Plan selected during signup
```

### Helper Functions
```sql
-- Check if user can upload a script
can_upload_script(user_id UUID) RETURNS BOOLEAN

-- Increment upload count after successful upload
increment_script_upload(user_id UUID) RETURNS VOID
```

## Backend Implementation Steps

### 1. Signup Handler (Auth Flow)
```typescript
// In your signup handler (e.g., /api/auth/signup)
async function handleSignup(req: Request) {
  const { email, password } = req.body;
  const { plan, source } = req.query;
  
  // Create auth user
  const { data: authUser, error } = await supabase.auth.signUp({
    email,
    password,
  });
  
  if (error) throw error;
  
  // Determine script upload limit based on plan
  let scriptUploadLimit = null; // null = unlimited
  
  if (plan === 'free_trial') {
    scriptUploadLimit = 1; // Free trial gets 1 script
  }
  
  // Create profile with limits
  await supabase
    .from('profiles')
    .insert({
      id: authUser.user.id,
      email: authUser.user.email,
      script_upload_limit: scriptUploadLimit,
      scripts_uploaded: 0,
      signup_source: source || 'direct',
      signup_plan: plan || null,
      subscription_status: plan === 'free_trial' ? 'trial' : 'active',
    });
  
  return { success: true, user: authUser.user };
}
```

### 2. Script Upload Handler
```typescript
// In your script upload handler (e.g., /api/scripts/upload)
async function handleScriptUpload(req: Request) {
  const userId = req.user.id; // From auth middleware
  const scriptFile = req.file;
  
  // Check if user can upload
  const { data: canUpload } = await supabase
    .rpc('can_upload_script', { user_id: userId });
  
  if (!canUpload) {
    return {
      error: 'Upload limit reached',
      message: 'You have reached your script upload limit. Please upgrade to continue.',
      upgradeUrl: '/pricing'
    };
  }
  
  // Process script upload...
  const script = await processScriptUpload(scriptFile);
  
  // Increment upload count
  await supabase.rpc('increment_script_upload', { user_id: userId });
  
  return { success: true, script };
}
```

### 3. User Dashboard Display
```typescript
// Show upload status in user dashboard
async function getUserUploadStatus(userId: string) {
  const { data: profile } = await supabase
    .from('profiles')
    .select('script_upload_limit, scripts_uploaded')
    .eq('id', userId)
    .single();
  
  const isUnlimited = profile.script_upload_limit === null;
  const remaining = isUnlimited 
    ? 'Unlimited' 
    : profile.script_upload_limit - profile.scripts_uploaded;
  
  return {
    uploaded: profile.scripts_uploaded,
    limit: profile.script_upload_limit,
    remaining,
    isUnlimited,
    canUpload: isUnlimited || profile.scripts_uploaded < profile.script_upload_limit
  };
}
```

## Plan Types

| Plan | script_upload_limit | subscription_status | Notes |
|------|---------------------|---------------------|-------|
| `free_trial` | 1 | `trial` | Landing page signup |
| `beta_access` | NULL | `active` | Beta users (unlimited) |
| Paid plans | NULL | `active` | Paid users (unlimited) |
| No plan | 1 | `trial` | Default fallback |

## UI/UX Considerations

### Upload Limit Reached
When user hits their limit, show:
```
🚫 Upload Limit Reached

You've used your free trial script upload.

Upgrade to unlock:
✓ Unlimited script uploads
✓ Advanced AI analysis
✓ Priority support

[Upgrade Now] [Learn More]
```

### Dashboard Display
```
📊 Your Usage
Scripts uploaded: 1 / 1
Status: Free Trial

[Upgrade to Unlimited →]
```

## Analytics Tracking

### Signup Source Breakdown
```sql
-- Track signup sources
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
-- Track free trial to paid conversion
SELECT 
  COUNT(*) FILTER (WHERE signup_plan = 'free_trial') as free_trial_signups,
  COUNT(*) FILTER (WHERE signup_plan = 'free_trial' AND subscription_status = 'active') as converted_to_paid,
  ROUND(
    COUNT(*) FILTER (WHERE signup_plan = 'free_trial' AND subscription_status = 'active')::NUMERIC / 
    NULLIF(COUNT(*) FILTER (WHERE signup_plan = 'free_trial'), 0) * 100, 
    2
  ) as conversion_rate_percent
FROM profiles;
```

## Testing Checklist

- [ ] Signup with `plan=free_trial` creates profile with `script_upload_limit=1`
- [ ] Signup without plan parameter defaults to appropriate limit
- [ ] User can upload 1 script successfully
- [ ] Second upload attempt is blocked with appropriate error message
- [ ] `can_upload_script()` function returns correct boolean
- [ ] `increment_script_upload()` increments counter correctly
- [ ] Dashboard shows correct upload status
- [ ] Upgrade flow works when limit is reached
- [ ] Analytics queries return expected data

## Migration Steps

1. **Run migration** in SlateOne Supabase project:
   ```bash
   # Apply migration
   supabase db push
   
   # Or run SQL directly in Supabase dashboard
   ```

2. **Deploy backend changes** to app.slateone.studio

3. **Test signup flow** with new URL parameters

4. **Monitor analytics** for signup source tracking

## Future Enhancements

- [ ] Email notification when upload limit is reached
- [ ] Automatic upgrade prompts in UI
- [ ] A/B testing different trial limits (1 vs 3 scripts)
- [ ] Referral program integration
- [ ] Time-based trial expiry (e.g., 7 days)

## Support

For questions or issues, contact the development team or refer to:
- Supabase docs: https://supabase.com/docs
- SlateOne internal wiki: [link]
