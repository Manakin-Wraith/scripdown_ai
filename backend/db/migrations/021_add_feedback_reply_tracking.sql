-- Migration 021: Add Email Reply Tracking to Feedback
-- Adds last_reply_sent timestamp to track when admin replies are sent

-- Add last_reply_sent column to feedback_submissions
ALTER TABLE feedback_submissions 
ADD COLUMN IF NOT EXISTS last_reply_sent TIMESTAMPTZ;

-- Create index for filtering feedback with replies
CREATE INDEX IF NOT EXISTS idx_feedback_last_reply_sent 
ON feedback_submissions(last_reply_sent) 
WHERE last_reply_sent IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN feedback_submissions.last_reply_sent IS 'Timestamp of the most recent admin email reply sent to the user';
