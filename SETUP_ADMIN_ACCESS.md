# Setting Up Admin Access - Step by Step

## Current Situation
You need to sign up with a proper password-protected account before granting yourself superuser access.

---

## Step 1: Remove Existing Superuser Flags

**Run in Supabase SQL Editor:**
```sql
-- Remove superuser from all existing accounts
UPDATE profiles 
SET is_superuser = FALSE;

-- Verify it worked
SELECT id, email, is_superuser 
FROM profiles 
WHERE is_superuser = TRUE;
-- Should return 0 rows
```

---

## Step 2: Sign Up Properly

1. **Go to your app**: `http://localhost:5173/login` (or production URL)
2. **Click "Sign Up"**
3. **Enter your details**:
   - Email: `your-email@scripdown.ai`
   - Password: (choose a strong password)
   - Full Name: Your Name
4. **Verify email** (check inbox for Supabase confirmation email)
5. **Log in** with your new credentials

---

## Step 3: Grant Yourself Superuser Access

**After you've signed up and logged in, run in Supabase SQL Editor:**

```sql
-- Grant superuser to your account
UPDATE profiles 
SET is_superuser = TRUE 
WHERE email = 'your-email@scripdown.ai';

-- Verify it worked
SELECT id, email, full_name, is_superuser 
FROM profiles 
WHERE email = 'your-email@scripdown.ai';
-- Should show is_superuser = TRUE
```

---

## Step 4: Test Admin Access

**Test the API:**
```bash
# Get your JWT token from browser localStorage or network tab
# Then test admin endpoint:

curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:5000/api/admin/analytics/overview
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "global_stats": { ... },
    "subscription_metrics": { ... }
  }
}
```

---

## Step 5: Run Database Migrations (If Not Done Yet)

**In Supabase SQL Editor, run these in order:**

1. **Superuser Flag Migration:**
```sql
-- From: backend/db/migrations/010_add_superuser_flag.sql
ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_profiles_superuser 
ON profiles(is_superuser) WHERE is_superuser = TRUE;
```

2. **Email System Migration:**
```sql
-- From: backend/db/migrations/011_email_management_system.sql
-- (Copy and paste the entire file)
```

---

## Troubleshooting

### "User already exists" Error
If you already have an account:
1. Use "Forgot Password" to reset it
2. Or delete the old account in Supabase Dashboard → Authentication → Users
3. Then sign up fresh

### "Superuser access required" After Granting
1. Log out completely
2. Clear browser localStorage
3. Log back in (this refreshes your JWT token with new claims)

### Email Confirmation Not Received
1. Check Supabase Dashboard → Authentication → Email Templates
2. Verify SMTP settings are configured
3. Check spam folder
4. Or manually confirm in Supabase Dashboard → Authentication → Users → Click user → Confirm email

### Dev Mode Testing (Skip Auth)
If you just want to test locally without auth:
1. Set `FLASK_ENV=development` in `backend/.env`
2. Restart Flask server
3. All superuser checks will be bypassed

---

## Security Notes

⚠️ **Important:**
- Only grant superuser to trusted accounts
- Use a strong password for your admin account
- Never commit superuser credentials to git
- In production, consider 2FA for admin accounts
- Regularly audit who has superuser access:
  ```sql
  SELECT id, email, full_name, created_at 
  FROM profiles 
  WHERE is_superuser = TRUE;
  ```

---

## Next Steps After Setup

Once you have admin access:
1. Test analytics endpoints
2. Monitor user activity
3. Check system health
4. Plan email campaigns (Phase 3)

---

**Questions?** Check `docs/ADMIN_SYSTEM.md` for full documentation.
