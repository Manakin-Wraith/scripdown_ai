-- Migration: Automatic Early Access User Sync Trigger
-- Description: Automatically update early_access_users when a user signs up
-- Date: 2026-01-15

-- Function to sync early access users with auth
CREATE OR REPLACE FUNCTION sync_early_access_signup()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if email exists in early_access_users
    UPDATE early_access_users
    SET 
        user_id = NEW.id,
        status = 'signed_up',
        signed_up_at = NOW(),
        metadata = jsonb_set(
            COALESCE(metadata, '{}'::jsonb),
            '{last_sync_check}',
            to_jsonb(NOW()::text)
        ) || jsonb_build_object('sync_source', 'trigger')
    WHERE 
        email = NEW.email
        AND status = 'invited';
    
    -- Log the sync if a row was updated
    IF FOUND THEN
        RAISE NOTICE 'Early access user synced: %', NEW.email;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger on auth.users insert
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION sync_early_access_signup();

-- Comment for documentation
COMMENT ON FUNCTION sync_early_access_signup() IS 
'Automatically updates early_access_users table when a user signs up via auth.users. 
Updates user_id, status, signed_up_at, and metadata fields for matching email addresses.';

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION sync_early_access_signup() TO service_role;
