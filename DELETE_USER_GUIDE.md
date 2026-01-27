# How to Delete a User from Supabase

## Problem
After adding the email management system, users with foreign key references cannot be deleted easily from the Supabase Dashboard.

---

## Solution 1: Via Supabase Dashboard (Easiest)

### Step 1: Delete from Authentication First
1. Go to **Supabase Dashboard** → **Authentication** → **Users**
2. Find the user by email
3. Click the **trash icon** to delete
4. Confirm deletion

### Step 2: Clean Up Orphaned Profile (If Needed)
If the profile wasn't auto-deleted, run in SQL Editor:
```sql
-- Find orphaned profiles (users deleted from auth but profile remains)
SELECT p.id, p.email, p.full_name 
FROM profiles p
LEFT JOIN auth.users u ON p.id = u.id
WHERE u.id IS NULL;

-- Delete orphaned profiles
DELETE FROM profiles 
WHERE id NOT IN (SELECT id FROM auth.users);
```

---

## Solution 2: Via SQL (Complete Cleanup)

### Method A: Delete by Email
```sql
DO $$
DECLARE
    user_id_to_delete UUID;
BEGIN
    -- Get user ID from email
    SELECT id INTO user_id_to_delete 
    FROM auth.users 
    WHERE email = 'user@example.com'; -- Replace with actual email
    
    IF user_id_to_delete IS NULL THEN
        RAISE NOTICE 'User not found';
        RETURN;
    END IF;
    
    RAISE NOTICE 'Deleting user: %', user_id_to_delete;
    
    -- Delete email logs where user is recipient
    DELETE FROM email_logs WHERE recipient_user_id = user_id_to_delete;
    RAISE NOTICE 'Deleted email logs';
    
    -- Delete scripts (cascades to scenes, analysis_jobs, etc.)
    DELETE FROM scripts WHERE user_id = user_id_to_delete;
    RAISE NOTICE 'Deleted scripts';
    
    -- Delete profile
    DELETE FROM profiles WHERE id = user_id_to_delete;
    RAISE NOTICE 'Deleted profile';
    
    RAISE NOTICE 'User deleted successfully. Now delete from Authentication UI.';
END $$;
```

### Method B: Delete by User ID
```sql
DO $$
DECLARE
    user_id_to_delete UUID := 'paste-user-id-here'; -- Replace with actual UUID
BEGIN
    -- Delete in order to respect foreign keys
    DELETE FROM email_logs WHERE recipient_user_id = user_id_to_delete;
    DELETE FROM scripts WHERE user_id = user_id_to_delete;
    DELETE FROM profiles WHERE id = user_id_to_delete;
    
    RAISE NOTICE 'User % deleted successfully', user_id_to_delete;
END $$;
```

---

## Solution 3: Reset Everything (Nuclear Option)

If you just want to start fresh for development:

```sql
-- ⚠️ WARNING: This deletes ALL users and data! Only use in development!

-- Delete all email data
TRUNCATE email_logs CASCADE;
TRUNCATE email_campaigns CASCADE;
TRUNCATE email_templates CASCADE;

-- Delete all scripts and scenes
TRUNCATE scripts CASCADE;
TRUNCATE scenes CASCADE;

-- Delete all profiles (except superusers if you want to keep them)
DELETE FROM profiles WHERE is_superuser = FALSE;

-- Then go to Authentication UI and delete all users manually
```

---

## Why This Happens

The new email management tables have foreign keys to `profiles`:
- `email_templates.created_by` → `profiles(id)`
- `email_campaigns.created_by` → `profiles(id)`
- `email_logs.recipient_user_id` → `profiles(id)`

These use `ON DELETE SET NULL`, which means:
- When you delete a user, these fields are set to NULL (not deleted)
- The user can still be deleted, but Supabase Dashboard might show an error

---

## Prevention: Cascade Deletes (Optional)

If you want automatic cleanup, modify the foreign keys:

```sql
-- Drop existing constraints
ALTER TABLE email_templates 
DROP CONSTRAINT IF EXISTS email_templates_created_by_fkey;

ALTER TABLE email_campaigns 
DROP CONSTRAINT IF EXISTS email_campaigns_created_by_fkey;

ALTER TABLE email_logs 
DROP CONSTRAINT IF EXISTS email_logs_recipient_user_id_fkey;

-- Add new constraints with CASCADE
ALTER TABLE email_templates 
ADD CONSTRAINT email_templates_created_by_fkey 
FOREIGN KEY (created_by) REFERENCES profiles(id) ON DELETE CASCADE;

ALTER TABLE email_campaigns 
ADD CONSTRAINT email_campaigns_created_by_fkey 
FOREIGN KEY (created_by) REFERENCES profiles(id) ON DELETE CASCADE;

ALTER TABLE email_logs 
ADD CONSTRAINT email_logs_recipient_user_id_fkey 
FOREIGN KEY (recipient_user_id) REFERENCES profiles(id) ON DELETE CASCADE;
```

**Note:** This will delete all email logs when a user is deleted, which may not be desired for audit purposes.

---

## Recommended Workflow

For development:
1. Delete from **Authentication UI** first
2. Run cleanup SQL if needed
3. Verify with: `SELECT * FROM profiles;`

For production:
1. Consider soft deletes (add `deleted_at` column)
2. Keep email logs for audit trail
3. Use `ON DELETE SET NULL` (current setup)

---

## Troubleshooting

### "Cannot delete user" Error
- Check if user has active email campaigns
- Check if user created email templates
- Run the SQL cleanup script first

### Profile Still Exists After Auth Deletion
- This is normal with `ON DELETE SET NULL`
- Run: `DELETE FROM profiles WHERE id = 'user-id';`

### Want to Keep Email History
- Current setup (`ON DELETE SET NULL`) preserves email logs
- User data is anonymized but logs remain for analytics

---

## Quick Reference

**Find user ID:**
```sql
SELECT id, email FROM auth.users WHERE email = 'user@example.com';
```

**Check what's blocking deletion:**
```sql
SELECT 
    'email_templates' as table_name, 
    COUNT(*) as count 
FROM email_templates 
WHERE created_by = 'user-id-here'
UNION ALL
SELECT 'email_campaigns', COUNT(*) FROM email_campaigns WHERE created_by = 'user-id-here'
UNION ALL
SELECT 'email_logs', COUNT(*) FROM email_logs WHERE recipient_user_id = 'user-id-here'
UNION ALL
SELECT 'scripts', COUNT(*) FROM scripts WHERE user_id = 'user-id-here';
```

---

**Need help?** Check the migration file: `backend/db/migrations/011_email_management_system.sql`
