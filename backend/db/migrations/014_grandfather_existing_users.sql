-- Migration: Grandfather Existing Users with Legacy Credits
-- Description: Grant 10 free credits to all active users before credit system launch
-- Date: 2026-01-27
-- Run this AFTER migration 005_script_credits_system.sql

-- ============================================
-- Grant 10 Free Credits to Existing Active Users
-- ============================================

-- Update all users who:
-- 1. Have active or trial subscription status
-- 2. Were created before the credit system launch (Feb 1, 2026)
-- 3. Currently have 0 credits (haven't been migrated yet)

UPDATE profiles 
SET 
    script_credits = 10,
    total_scripts_purchased = 10,
    is_legacy_beta = TRUE
WHERE 
    subscription_status IN ('active', 'trial')
    AND created_at < '2026-02-01'
    AND script_credits = 0;

-- ============================================
-- Verification Query
-- ============================================

-- Run this to verify the migration worked:
-- SELECT 
--     COUNT(*) as total_legacy_users,
--     SUM(script_credits) as total_credits_granted
-- FROM profiles 
-- WHERE is_legacy_beta = TRUE;

-- Expected result: All existing active users should have:
-- - script_credits = 10
-- - total_scripts_purchased = 10
-- - is_legacy_beta = TRUE
