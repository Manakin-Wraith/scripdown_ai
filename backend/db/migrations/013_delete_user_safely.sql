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

    -- Delete crew assignments referencing this user's contacts. production_crew.contact_id
    -- is ON DELETE RESTRICT, so the profiles -> contacts cascade below would raise 23503
    -- unless these rows are gone first. Explicit delete = ordering-independent (see
    -- migration 051 header note re: pg_restore constraint reordering).
    DELETE FROM production_crew
     WHERE contact_id IN (SELECT id FROM contacts WHERE owner_id = user_id_to_delete);
    -- locations (053) needs no explicit delete here: profiles -> locations is
    -- ON DELETE CASCADE and nothing references locations with RESTRICT.

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

    -- Delete crew assignments before the profiles -> contacts cascade (RESTRICT FK)
    DELETE FROM production_crew
     WHERE contact_id IN (SELECT id FROM contacts WHERE owner_id = user_id_to_delete);
    -- locations (053) needs no explicit delete here: profiles -> locations is
    -- ON DELETE CASCADE and nothing references locations with RESTRICT.

    -- Delete scripts (cascades to scenes, etc.)
    DELETE FROM scripts WHERE user_id = user_id_to_delete;
    
    -- Delete profile
    DELETE FROM profiles WHERE id = user_id_to_delete;
    
    -- Delete from auth (requires admin privileges)
    -- This may need to be done via Supabase Dashboard
    
    RAISE NOTICE 'User % deleted successfully', user_id_to_delete;
END $$;
*/
