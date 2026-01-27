-- Migration: Add Signup Tracking Columns to Profiles
-- Description: Add columns for tracking signup source and plan type for landing page signups
-- Date: 2026-01-27
-- Source: Landing page dev team

-- Add script upload limits and signup source tracking to profiles table
-- This migration supports the free trial allocation system

-- Add columns for script upload tracking
ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS script_upload_limit INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS scripts_uploaded INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS signup_source TEXT DEFAULT 'direct',
ADD COLUMN IF NOT EXISTS signup_plan TEXT DEFAULT NULL;

-- Create index for efficient queries
CREATE INDEX IF NOT EXISTS idx_profiles_signup_source ON profiles(signup_source);
CREATE INDEX IF NOT EXISTS idx_profiles_signup_plan ON profiles(signup_plan);
CREATE INDEX IF NOT EXISTS idx_profiles_script_limits ON profiles(script_upload_limit, scripts_uploaded);

-- Add comment for documentation
COMMENT ON COLUMN profiles.script_upload_limit IS 'Maximum number of scripts user can upload. NULL = unlimited (paid users)';
COMMENT ON COLUMN profiles.scripts_uploaded IS 'Current count of scripts uploaded by user';
COMMENT ON COLUMN profiles.signup_source IS 'Source of user signup (e.g., landing_hero, landing_waitlist, referral)';
COMMENT ON COLUMN profiles.signup_plan IS 'Plan selected during signup (e.g., free_trial, beta_access)';

-- Create function to check if user can upload script
CREATE OR REPLACE FUNCTION can_upload_script(user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
  upload_limit INTEGER;
  uploaded_count INTEGER;
BEGIN
  SELECT script_upload_limit, scripts_uploaded 
  INTO upload_limit, uploaded_count
  FROM profiles
  WHERE id = user_id;
  
  -- NULL limit means unlimited (paid users)
  IF upload_limit IS NULL THEN
    RETURN TRUE;
  END IF;
  
  -- Check if under limit
  RETURN uploaded_count < upload_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create function to increment script upload count
CREATE OR REPLACE FUNCTION increment_script_upload(user_id UUID)
RETURNS VOID AS $$
BEGIN
  UPDATE profiles
  SET scripts_uploaded = scripts_uploaded + 1,
      updated_at = NOW()
  WHERE id = user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION can_upload_script(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION increment_script_upload(UUID) TO authenticated;
