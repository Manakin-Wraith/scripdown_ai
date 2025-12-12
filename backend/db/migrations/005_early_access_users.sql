-- Migration: Early Access Users Table
-- Description: Track early access invites for extended trial periods
-- Date: 2024-12-11

-- Early access users table to track invited users with extended trials
CREATE TABLE IF NOT EXISTS early_access_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    first_name TEXT,
    trial_days INTEGER DEFAULT 30,
    status TEXT DEFAULT 'invited' CHECK (status IN ('invited', 'signed_up', 'expired')),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    invited_at TIMESTAMPTZ DEFAULT NOW(),
    signed_up_at TIMESTAMPTZ,
    invite_sent_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_early_access_users_email ON early_access_users(email);
CREATE INDEX IF NOT EXISTS idx_early_access_users_status ON early_access_users(status);
CREATE INDEX IF NOT EXISTS idx_early_access_users_user_id ON early_access_users(user_id);

-- Enable RLS
ALTER TABLE early_access_users ENABLE ROW LEVEL SECURITY;

-- Policy: Service role can do everything
DROP POLICY IF EXISTS "Service role full access" ON early_access_users;
CREATE POLICY "Service role full access" ON early_access_users
    FOR ALL
    USING (auth.role() = 'service_role');

-- Policy: Users can view their own record
DROP POLICY IF EXISTS "Users can view own record" ON early_access_users;
CREATE POLICY "Users can view own record" ON early_access_users
    FOR SELECT
    USING (auth.uid() = user_id);

-- Comment for documentation
COMMENT ON TABLE early_access_users IS 'Tracks early access invites with extended trial periods (30 days instead of 14)';
