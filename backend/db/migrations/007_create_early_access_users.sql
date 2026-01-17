-- Migration: Create early_access_users table (Safe version - handles existing objects)
-- Description: Table to track early access invitations and signups
-- Date: 2026-01-15

-- Create table if it doesn't exist
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
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes (IF NOT EXISTS)
CREATE INDEX IF NOT EXISTS idx_early_access_users_email ON early_access_users(email);
CREATE INDEX IF NOT EXISTS idx_early_access_users_status ON early_access_users(status);
CREATE INDEX IF NOT EXISTS idx_early_access_users_user_id ON early_access_users(user_id);

-- Enable RLS
ALTER TABLE early_access_users ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist, then recreate
DROP POLICY IF EXISTS "Service role has full access to early_access_users" ON early_access_users;
DROP POLICY IF EXISTS "Users can read their own early_access record" ON early_access_users;

-- Create policies
CREATE POLICY "Service role has full access to early_access_users"
    ON early_access_users
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Users can read their own early_access record"
    ON early_access_users
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- Add comments
COMMENT ON TABLE early_access_users IS 'Tracks early access invitations and user signup status';
COMMENT ON COLUMN early_access_users.status IS 'User status: invited, signed_up, or expired';
COMMENT ON COLUMN early_access_users.user_id IS 'Links to auth.users after signup';
COMMENT ON COLUMN early_access_users.metadata IS 'JSON field for tracking sync info and additional data';
