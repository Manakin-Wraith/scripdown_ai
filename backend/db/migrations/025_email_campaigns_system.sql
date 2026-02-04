-- Migration 025: Email Campaigns System
-- Creates tables for managing email campaigns, templates, and tracking

-- ============================================
-- Email Templates Table
-- ============================================
CREATE TABLE IF NOT EXISTS email_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body_html TEXT NOT NULL,
    body_text TEXT,
    category VARCHAR(100), -- 'marketing', 'transactional', 'notification'
    variables JSONB DEFAULT '[]'::jsonb, -- Array of variable names like ["user_name", "trial_days_left"]
    is_active BOOLEAN DEFAULT true,
    created_by UUID, -- References auth.users(id) but without FK constraint
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_template_name UNIQUE(name)
);

-- Index for quick template lookups
CREATE INDEX IF NOT EXISTS idx_email_templates_category ON email_templates(category);
CREATE INDEX IF NOT EXISTS idx_email_templates_active ON email_templates(is_active);

-- ============================================
-- Email Campaigns Table
-- ============================================
CREATE TABLE IF NOT EXISTS email_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_id UUID REFERENCES email_templates(id) ON DELETE SET NULL,
    
    -- Audience segmentation
    audience_filter JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Example: {"subscription_status": ["trial", "expired"], "min_scripts": 0, "max_scripts": 1}
    
    -- Scheduling
    status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'scheduled', 'sending', 'sent', 'paused', 'cancelled'
    scheduled_at TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    created_by UUID, -- References auth.users(id) but without FK constraint
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Statistics (updated as campaign progresses)
    total_recipients INTEGER DEFAULT 0,
    emails_sent INTEGER DEFAULT 0,
    emails_delivered INTEGER DEFAULT 0,
    emails_opened INTEGER DEFAULT 0,
    emails_clicked INTEGER DEFAULT 0,
    emails_bounced INTEGER DEFAULT 0,
    emails_failed INTEGER DEFAULT 0
);

-- Indexes for campaign management
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON email_campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_scheduled_at ON email_campaigns(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_campaigns_created_by ON email_campaigns(created_by);

-- ============================================
-- Campaign Recipients Table
-- ============================================
CREATE TABLE IF NOT EXISTS email_campaign_recipients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES email_campaigns(id) ON DELETE CASCADE,
    user_id UUID NOT NULL, -- References auth.users(id) but without FK constraint
    email VARCHAR(255) NOT NULL,
    
    -- Sending status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'failed'
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    opened_at TIMESTAMP WITH TIME ZONE,
    clicked_at TIMESTAMP WITH TIME ZONE,
    bounced_at TIMESTAMP WITH TIME ZONE,
    
    -- Tracking
    open_count INTEGER DEFAULT 0,
    click_count INTEGER DEFAULT 0,
    
    -- Error handling
    error_message TEXT,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_campaign_recipient UNIQUE(campaign_id, user_id)
);

-- Indexes for recipient tracking
CREATE INDEX IF NOT EXISTS idx_campaign_recipients_campaign ON email_campaign_recipients(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_recipients_user ON email_campaign_recipients(user_id);
CREATE INDEX IF NOT EXISTS idx_campaign_recipients_status ON email_campaign_recipients(status);
CREATE INDEX IF NOT EXISTS idx_campaign_recipients_email ON email_campaign_recipients(email);

-- ============================================
-- Campaign Click Tracking Table
-- ============================================
CREATE TABLE IF NOT EXISTS email_campaign_clicks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_id UUID NOT NULL REFERENCES email_campaign_recipients(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES email_campaigns(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    clicked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_agent TEXT,
    ip_address INET
);

-- Index for click analytics
CREATE INDEX IF NOT EXISTS idx_campaign_clicks_recipient ON email_campaign_clicks(recipient_id);
CREATE INDEX IF NOT EXISTS idx_campaign_clicks_campaign ON email_campaign_clicks(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_clicks_clicked_at ON email_campaign_clicks(clicked_at);

-- ============================================
-- Row Level Security (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE email_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_campaign_recipients ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_campaign_clicks ENABLE ROW LEVEL SECURITY;

-- Policies: Only superusers can manage campaigns
CREATE POLICY "Superusers can manage email templates"
    ON email_templates
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE profiles.id = auth.uid()
            AND profiles.is_superuser = true
        )
    );

CREATE POLICY "Superusers can manage email campaigns"
    ON email_campaigns
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE profiles.id = auth.uid()
            AND profiles.is_superuser = true
        )
    );

CREATE POLICY "Superusers can view campaign recipients"
    ON email_campaign_recipients
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE profiles.id = auth.uid()
            AND profiles.is_superuser = true
        )
    );

CREATE POLICY "Superusers can view campaign clicks"
    ON email_campaign_clicks
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE profiles.id = auth.uid()
            AND profiles.is_superuser = true
        )
    );

-- ============================================
-- Default Email Templates
-- ============================================

-- Insert default templates for common use cases
INSERT INTO email_templates (name, subject, body_html, body_text, category, variables) VALUES
(
    'Trial Expiring Soon',
    'Your ScripDown AI trial expires in {{days_left}} days',
    '<html><body><h1>Hi {{user_name}},</h1><p>Your trial expires in <strong>{{days_left}} days</strong>.</p><p>Upgrade now to continue using all features!</p><a href="{{upgrade_url}}">Upgrade Now</a></body></html>',
    'Hi {{user_name}}, Your trial expires in {{days_left}} days. Upgrade now: {{upgrade_url}}',
    'marketing',
    '["user_name", "days_left", "upgrade_url"]'::jsonb
),
(
    'Welcome New User',
    'Welcome to ScripDown AI!',
    '<html><body><h1>Welcome {{user_name}}!</h1><p>Thanks for joining ScripDown AI. Get started by uploading your first script.</p><a href="{{app_url}}">Get Started</a></body></html>',
    'Welcome {{user_name}}! Thanks for joining ScripDown AI. Get started: {{app_url}}',
    'transactional',
    '["user_name", "app_url"]'::jsonb
),
(
    'Inactive User Re-engagement',
    'We miss you at ScripDown AI',
    '<html><body><h1>Hi {{user_name}},</h1><p>It''s been {{days_inactive}} days since your last visit. Check out what''s new!</p><a href="{{app_url}}">Come Back</a></body></html>',
    'Hi {{user_name}}, It''s been {{days_inactive}} days since your last visit. Come back: {{app_url}}',
    'marketing',
    '["user_name", "days_inactive", "app_url"]'::jsonb
),
(
    'Feature Announcement',
    'New Feature: {{feature_name}}',
    '<html><body><h1>Hi {{user_name}},</h1><p>We just launched a new feature: <strong>{{feature_name}}</strong></p><p>{{feature_description}}</p><a href="{{feature_url}}">Learn More</a></body></html>',
    'Hi {{user_name}}, New feature: {{feature_name}}. {{feature_description}} Learn more: {{feature_url}}',
    'notification',
    '["user_name", "feature_name", "feature_description", "feature_url"]'::jsonb
);

-- ============================================
-- Helper Functions
-- ============================================

-- Function to update campaign statistics
CREATE OR REPLACE FUNCTION update_campaign_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- Update campaign statistics when recipient status changes
    UPDATE email_campaigns
    SET
        emails_sent = (SELECT COUNT(*) FROM email_campaign_recipients WHERE campaign_id = NEW.campaign_id AND status IN ('sent', 'delivered', 'opened', 'clicked')),
        emails_delivered = (SELECT COUNT(*) FROM email_campaign_recipients WHERE campaign_id = NEW.campaign_id AND status IN ('delivered', 'opened', 'clicked')),
        emails_opened = (SELECT COUNT(*) FROM email_campaign_recipients WHERE campaign_id = NEW.campaign_id AND status IN ('opened', 'clicked')),
        emails_clicked = (SELECT COUNT(*) FROM email_campaign_recipients WHERE campaign_id = NEW.campaign_id AND status = 'clicked'),
        emails_bounced = (SELECT COUNT(*) FROM email_campaign_recipients WHERE campaign_id = NEW.campaign_id AND status = 'bounced'),
        emails_failed = (SELECT COUNT(*) FROM email_campaign_recipients WHERE campaign_id = NEW.campaign_id AND status = 'failed'),
        updated_at = NOW()
    WHERE id = NEW.campaign_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update campaign stats
CREATE TRIGGER trigger_update_campaign_stats
    AFTER INSERT OR UPDATE ON email_campaign_recipients
    FOR EACH ROW
    EXECUTE FUNCTION update_campaign_stats();

-- ============================================
-- Comments
-- ============================================

COMMENT ON TABLE email_templates IS 'Reusable email templates with variable substitution';
COMMENT ON TABLE email_campaigns IS 'Email campaigns with audience targeting and scheduling';
COMMENT ON TABLE email_campaign_recipients IS 'Individual recipients for each campaign with tracking';
COMMENT ON TABLE email_campaign_clicks IS 'Click tracking for campaign links';
