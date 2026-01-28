-- Migration 018: Feedback System
-- Creates tables and policies for user feedback submission and management

-- Create feedback_submissions table
CREATE TABLE IF NOT EXISTS feedback_submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Feedback classification
    category TEXT NOT NULL CHECK (category IN ('bug', 'feature', 'ui_ux', 'general')),
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    status TEXT DEFAULT 'new' CHECK (status IN ('new', 'in_progress', 'resolved', 'dismissed')),
    
    -- Feedback content
    subject TEXT NOT NULL CHECK (char_length(subject) <= 200),
    description TEXT NOT NULL CHECK (char_length(description) <= 2000),
    screenshot_url TEXT,
    
    -- Context capture
    page_context JSONB DEFAULT '{}'::jsonb,
    -- Expected structure: { "url": "string", "route": "string", "script_id": "uuid|null", "user_agent": "string", "viewport": "string" }
    
    -- Admin management
    admin_notes TEXT,
    resolved_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    resolved_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback_submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback_submissions(status);
CREATE INDEX IF NOT EXISTS idx_feedback_category ON feedback_submissions(category);
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback_submissions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_priority ON feedback_submissions(priority);

-- Composite index for common admin queries
CREATE INDEX IF NOT EXISTS idx_feedback_status_category ON feedback_submissions(status, category);

-- GIN index for JSONB page_context searches
CREATE INDEX IF NOT EXISTS idx_feedback_page_context ON feedback_submissions USING GIN (page_context);

-- Full-text search index on subject and description
CREATE INDEX IF NOT EXISTS idx_feedback_search ON feedback_submissions USING GIN (
    to_tsvector('english', subject || ' ' || description)
);

-- Enable Row Level Security
ALTER TABLE feedback_submissions ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can view their own feedback
CREATE POLICY "Users can view own feedback"
    ON feedback_submissions
    FOR SELECT
    USING (auth.uid() = user_id);

-- RLS Policy: Users can insert their own feedback
CREATE POLICY "Users can insert own feedback"
    ON feedback_submissions
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- RLS Policy: Users can update their own feedback (only before admin has touched it)
CREATE POLICY "Users can update own unprocessed feedback"
    ON feedback_submissions
    FOR UPDATE
    USING (
        auth.uid() = user_id 
        AND status = 'new'
        AND resolved_by IS NULL
    )
    WITH CHECK (
        auth.uid() = user_id 
        AND status = 'new'
    );

-- RLS Policy: Superusers can view all feedback
CREATE POLICY "Superusers can view all feedback"
    ON feedback_submissions
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.is_superuser = true
        )
    );

-- RLS Policy: Superusers can update all feedback
CREATE POLICY "Superusers can update all feedback"
    ON feedback_submissions
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.is_superuser = true
        )
    );

-- RLS Policy: Superusers can delete feedback (for spam/abuse)
CREATE POLICY "Superusers can delete feedback"
    ON feedback_submissions
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.is_superuser = true
        )
    );

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_feedback_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for updated_at
DROP TRIGGER IF EXISTS trigger_feedback_updated_at ON feedback_submissions;
CREATE TRIGGER trigger_feedback_updated_at
    BEFORE UPDATE ON feedback_submissions
    FOR EACH ROW
    EXECUTE FUNCTION update_feedback_updated_at();

-- Create function to auto-set resolved_at when status changes to resolved
CREATE OR REPLACE FUNCTION set_feedback_resolved_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'resolved' AND OLD.status != 'resolved' THEN
        NEW.resolved_at = NOW();
        IF NEW.resolved_by IS NULL THEN
            NEW.resolved_by = auth.uid();
        END IF;
    ELSIF NEW.status != 'resolved' THEN
        NEW.resolved_at = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for resolved_at
DROP TRIGGER IF EXISTS trigger_feedback_resolved_at ON feedback_submissions;
CREATE TRIGGER trigger_feedback_resolved_at
    BEFORE UPDATE ON feedback_submissions
    FOR EACH ROW
    EXECUTE FUNCTION set_feedback_resolved_at();

-- Create view for admin dashboard (aggregated stats)
CREATE OR REPLACE VIEW feedback_stats AS
SELECT
    COUNT(*) FILTER (WHERE status = 'new') as new_count,
    COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress_count,
    COUNT(*) FILTER (WHERE status = 'resolved') as resolved_count,
    COUNT(*) FILTER (WHERE status = 'dismissed') as dismissed_count,
    COUNT(*) FILTER (WHERE category = 'bug') as bug_count,
    COUNT(*) FILTER (WHERE category = 'feature') as feature_count,
    COUNT(*) FILTER (WHERE category = 'ui_ux') as ui_ux_count,
    COUNT(*) FILTER (WHERE category = 'general') as general_count,
    COUNT(*) FILTER (WHERE priority = 'high') as high_priority_count,
    COUNT(*) FILTER (WHERE priority = 'medium') as medium_priority_count,
    COUNT(*) FILTER (WHERE priority = 'low') as low_priority_count,
    COUNT(*) as total_count,
    AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600) FILTER (WHERE resolved_at IS NOT NULL) as avg_resolution_hours
FROM feedback_submissions;

-- Grant access to the view for authenticated users
GRANT SELECT ON feedback_stats TO authenticated;

-- Create materialized view for user feedback history (performance optimization)
CREATE MATERIALIZED VIEW IF NOT EXISTS user_feedback_summary AS
SELECT
    user_id,
    COUNT(*) as total_submissions,
    COUNT(*) FILTER (WHERE status = 'resolved') as resolved_count,
    COUNT(*) FILTER (WHERE category = 'bug') as bug_reports,
    COUNT(*) FILTER (WHERE category = 'feature') as feature_requests,
    MAX(created_at) as last_submission_at,
    MIN(created_at) as first_submission_at
FROM feedback_submissions
GROUP BY user_id;

-- Create index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_feedback_summary_user_id ON user_feedback_summary(user_id);

-- Grant access to materialized view
GRANT SELECT ON user_feedback_summary TO authenticated;

-- Function to refresh materialized view (can be called by cron job)
CREATE OR REPLACE FUNCTION refresh_user_feedback_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY user_feedback_summary;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Comments for documentation
COMMENT ON TABLE feedback_submissions IS 'Stores user feedback submissions including bug reports, feature requests, and general feedback';
COMMENT ON COLUMN feedback_submissions.category IS 'Type of feedback: bug, feature, ui_ux, or general';
COMMENT ON COLUMN feedback_submissions.priority IS 'User-assigned priority: low, medium, or high';
COMMENT ON COLUMN feedback_submissions.status IS 'Admin workflow status: new, in_progress, resolved, or dismissed';
COMMENT ON COLUMN feedback_submissions.page_context IS 'JSON object containing URL, route, script_id, user_agent, and viewport information';
COMMENT ON COLUMN feedback_submissions.screenshot_url IS 'URL to screenshot stored in Supabase Storage (feedback-screenshots bucket)';
COMMENT ON VIEW feedback_stats IS 'Aggregated statistics for admin dashboard';
COMMENT ON MATERIALIZED VIEW user_feedback_summary IS 'Per-user feedback submission summary for performance';
