-- Migration: Remove Superuser Flag for Fresh Signup
-- Date: 2026-01-20
-- Purpose: Reset superuser flag so you can sign up with proper password authentication

-- Remove superuser flag from all users
UPDATE profiles 
SET is_superuser = FALSE;

-- Verify no superusers remain
-- SELECT id, email, is_superuser FROM profiles WHERE is_superuser = TRUE;

-- After you sign up with your new account, run this to grant superuser:
-- UPDATE profiles 
-- SET is_superuser = TRUE 
-- WHERE email = 'your-email@scripdown.ai';
