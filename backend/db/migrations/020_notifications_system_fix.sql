-- Migration 020 Fix: Add feedback_submitted to valid notification types
-- This fixes the check constraint violation

-- Drop the existing constraint if it exists
ALTER TABLE notifications DROP CONSTRAINT IF EXISTS valid_notification_type;

-- Add the updated constraint with feedback_submitted included
ALTER TABLE notifications ADD CONSTRAINT valid_notification_type 
CHECK (type IN (
    'invite_accepted',
    'member_joined', 
    'script_shared',
    'feedback_submitted'
));
