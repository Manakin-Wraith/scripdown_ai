-- Fix data types for user profile
-- Run this in Supabase SQL Editor

UPDATE profiles 
SET 
    script_credits = 10::INTEGER,
    total_scripts_purchased = 10::INTEGER,
    is_legacy_beta = TRUE::BOOLEAN,
    is_superuser = TRUE::BOOLEAN
WHERE id = '9da653a2-ab39-495c-9531-a84d396a244f';

-- Verify the update
SELECT 
    id,
    email,
    script_credits,
    total_scripts_purchased,
    is_legacy_beta,
    is_superuser,
    pg_typeof(script_credits) as credits_type,
    pg_typeof(is_legacy_beta) as legacy_type
FROM profiles 
WHERE id = '9da653a2-ab39-495c-9531-a84d396a244f';
