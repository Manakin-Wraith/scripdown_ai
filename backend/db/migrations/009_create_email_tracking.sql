-- Email tracking table for beta launch and other campaigns
CREATE TABLE IF NOT EXISTS email_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_type VARCHAR(50) NOT NULL,  -- 'beta_launch', 'welcome', 'reminder', etc.
    recipient_email VARCHAR(255) NOT NULL,
    recipient_name VARCHAR(255),
    user_status VARCHAR(50),  -- 'new', 'trial', 'waitlist'
    resend_email_id VARCHAR(255),  -- ID from Resend API
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    delivery_status VARCHAR(50) DEFAULT 'sent',  -- 'sent', 'delivered', 'bounced', 'failed'
    opened_at TIMESTAMP WITH TIME ZONE,
    clicked_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB,  -- Store additional data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster queries
CREATE INDEX idx_email_tracking_recipient ON email_tracking(recipient_email);
CREATE INDEX idx_email_tracking_type ON email_tracking(email_type);
CREATE INDEX idx_email_tracking_sent_at ON email_tracking(sent_at DESC);
CREATE INDEX idx_email_tracking_resend_id ON email_tracking(resend_email_id);

-- Enable RLS
ALTER TABLE email_tracking ENABLE ROW LEVEL SECURITY;

-- Policy: Only authenticated users can view email tracking
CREATE POLICY "Authenticated users can view email tracking"
    ON email_tracking
    FOR SELECT
    TO authenticated
    USING (true);

-- Policy: Only service role can insert/update
CREATE POLICY "Service role can manage email tracking"
    ON email_tracking
    FOR ALL
    TO service_role
    USING (true);

COMMENT ON TABLE email_tracking IS 'Tracks all sent emails for analytics and debugging';
