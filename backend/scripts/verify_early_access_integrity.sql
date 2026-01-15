-- Data Integrity Verification Queries for Early Access Users
-- Run these queries to check the accuracy of early_access_users data

-- ============================================================================
-- 1. Find users marked 'invited' but actually signed up
-- ============================================================================
-- These users should be synced to 'signed_up' status
SELECT 
    ea.id,
    ea.email,
    ea.status as current_status,
    ea.user_id,
    u.id as auth_user_id,
    u.created_at as auth_signup_date,
    ea.invited_at
FROM early_access_users ea
JOIN auth.users u ON ea.email = u.email
WHERE ea.status = 'invited'
ORDER BY u.created_at DESC;

-- ============================================================================
-- 2. Find users marked 'signed_up' but no auth record
-- ============================================================================
-- These might indicate data inconsistency or deleted auth accounts
SELECT 
    ea.id,
    ea.email,
    ea.status,
    ea.user_id,
    ea.signed_up_at
FROM early_access_users ea
LEFT JOIN auth.users u ON ea.email = u.email
WHERE ea.status = 'signed_up' AND u.id IS NULL
ORDER BY ea.signed_up_at DESC;

-- ============================================================================
-- 3. Find users with mismatched user_id
-- ============================================================================
-- user_id in early_access_users doesn't match auth.users
SELECT 
    ea.id,
    ea.email,
    ea.user_id as ea_user_id,
    u.id as auth_user_id,
    ea.status
FROM early_access_users ea
JOIN auth.users u ON ea.email = u.email
WHERE ea.user_id IS NOT NULL 
  AND ea.user_id != u.id
ORDER BY ea.email;

-- ============================================================================
-- 4. Conversion rate statistics
-- ============================================================================
SELECT 
    COUNT(*) as total_users,
    COUNT(*) FILTER (WHERE status = 'invited') as invited,
    COUNT(*) FILTER (WHERE status = 'signed_up') as signed_up,
    COUNT(*) FILTER (WHERE status = 'expired') as expired,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'signed_up') / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct
FROM early_access_users;

-- ============================================================================
-- 5. Time to signup analysis
-- ============================================================================
-- How long it takes users to sign up after being invited
SELECT 
    ea.email,
    ea.invited_at,
    ea.signed_up_at,
    EXTRACT(EPOCH FROM (ea.signed_up_at - ea.invited_at))/3600 as hours_to_signup,
    EXTRACT(DAY FROM (ea.signed_up_at - ea.invited_at)) as days_to_signup
FROM early_access_users ea
WHERE ea.status = 'signed_up'
  AND ea.invited_at IS NOT NULL
  AND ea.signed_up_at IS NOT NULL
ORDER BY hours_to_signup ASC;

-- ============================================================================
-- 6. Recent signups (last 7 days)
-- ============================================================================
SELECT 
    ea.email,
    ea.first_name,
    ea.signed_up_at,
    ea.metadata->>'sync_source' as sync_source
FROM early_access_users ea
WHERE ea.status = 'signed_up'
  AND ea.signed_up_at > NOW() - INTERVAL '7 days'
ORDER BY ea.signed_up_at DESC;

-- ============================================================================
-- 7. Users invited but not yet signed up (with days since invite)
-- ============================================================================
SELECT 
    ea.email,
    ea.first_name,
    ea.invited_at,
    EXTRACT(DAY FROM (NOW() - ea.invited_at)) as days_since_invite,
    ea.invite_sent_at,
    CASE 
        WHEN ea.invite_sent_at IS NULL THEN 'No reminder sent'
        ELSE EXTRACT(DAY FROM (NOW() - ea.invite_sent_at))::text || ' days since reminder'
    END as reminder_status
FROM early_access_users ea
WHERE ea.status = 'invited'
ORDER BY ea.invited_at ASC;

-- ============================================================================
-- 8. Sync metadata analysis
-- ============================================================================
-- Check how users were synced (trigger vs script vs manual)
SELECT 
    metadata->>'sync_source' as sync_source,
    COUNT(*) as count,
    MIN(signed_up_at) as earliest_signup,
    MAX(signed_up_at) as latest_signup
FROM early_access_users
WHERE status = 'signed_up'
  AND metadata IS NOT NULL
GROUP BY metadata->>'sync_source'
ORDER BY count DESC;

-- ============================================================================
-- 9. Duplicate email check
-- ============================================================================
-- Should return 0 rows (email is unique constraint)
SELECT 
    email,
    COUNT(*) as count
FROM early_access_users
GROUP BY email
HAVING COUNT(*) > 1;

-- ============================================================================
-- 10. Overall health check
-- ============================================================================
SELECT 
    'Total Users' as metric,
    COUNT(*)::text as value
FROM early_access_users
UNION ALL
SELECT 
    'Invited (Not Signed Up)',
    COUNT(*)::text
FROM early_access_users
WHERE status = 'invited'
UNION ALL
SELECT 
    'Signed Up',
    COUNT(*)::text
FROM early_access_users
WHERE status = 'signed_up'
UNION ALL
SELECT 
    'Expired',
    COUNT(*)::text
FROM early_access_users
WHERE status = 'expired'
UNION ALL
SELECT 
    'Missing user_id (signed_up)',
    COUNT(*)::text
FROM early_access_users
WHERE status = 'signed_up' AND user_id IS NULL
UNION ALL
SELECT 
    'Conversion Rate',
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'signed_up') / NULLIF(COUNT(*), 0), 2)::text || '%'
FROM early_access_users;
