-- Migration: Add Superuser Flag to Profiles
-- Date: 2026-01-20
-- Purpose: Enable admin-only access to analytics and email management

-- Add is_superuser column to profiles table (only if it doesn't exist)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'profiles' 
        AND column_name = 'is_superuser'
    ) THEN
        ALTER TABLE profiles 
        ADD COLUMN is_superuser BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- Create index for faster superuser lookups
CREATE INDEX IF NOT EXISTS idx_profiles_superuser 
ON profiles(is_superuser) WHERE is_superuser = TRUE;

-- Add comment for documentation
COMMENT ON COLUMN profiles.is_superuser IS 'Flag indicating if user has superuser/admin privileges for analytics and email management';
