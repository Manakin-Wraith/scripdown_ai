-- Script: Safe User Deletion
-- Purpose: Delete a user and all related data from the system
-- Usage: Replace 'USER_EMAIL_HERE' with the actual email address

-- Step 1: Find the user ID
-- SELECT id, email FROM auth.users WHERE email = 'USER_EMAIL_HERE';

-- Step 2: Delete user data (replace USER_ID_HERE with actual UUID)
DO $$
DECLARE
    user_id_to_delete UUID := 'USER_ID_HERE'; -- Replace with actual user ID
BEGIN
    -- Delete email-related data (created_by will be set to NULL automatically)
    -- No need to manually delete due to ON DELETE SET NULL
    
    -- Delete email logs for this user as recipient
    DELETE FROM email_logs WHERE recipient_user_id = user_id_to_delete;
    
    -- Delete scripts and related data (cascades automatically)
    DELETE FROM scripts WHERE user_id = user_id_to_delete;
    
    -- Delete profile (this should cascade to auth.users)
    DELETE FROM profiles WHERE id = user_id_to_delete;
    
    RAISE NOTICE 'User % deleted successfully', user_id_to_delete;
END $$;

-- Step 3: Delete from Supabase Auth (if profile deletion didn't cascade)
-- Go to Supabase Dashboard → Authentication → Users → Find user → Delete

-- ============================================
-- Quick Delete by Email (Alternative Method)
-- ============================================
-- Uncomment and run this block instead:

/*
DO $$
DECLARE
    user_id_to_delete UUID;
BEGIN
    -- Get user ID from email
    SELECT id INTO user_id_to_delete 
    FROM auth.users 
    WHERE email = 'USER_EMAIL_HERE';
    
    IF user_id_to_delete IS NULL THEN
        RAISE NOTICE 'User not found';
        RETURN;
    END IF;
    
    -- Delete email logs
    DELETE FROM email_logs WHERE recipient_user_id = user_id_to_delete;
    
    -- Delete scripts (cascades to scenes, etc.)
    DELETE FROM scripts WHERE user_id = user_id_to_delete;
    
    -- Delete profile
    DELETE FROM profiles WHERE id = user_id_to_delete;
    
    -- Delete from auth (requires admin privileges)
    -- This may need to be done via Supabase Dashboard
    
    RAISE NOTICE 'User % deleted successfully', user_id_to_delete;
END $$;
*/
