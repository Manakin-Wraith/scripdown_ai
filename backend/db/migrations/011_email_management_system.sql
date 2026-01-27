-- Migration: Email Management System
-- Date: 2026-01-20
-- Purpose: Enable email template management, campaigns, and tracking for superuser

-- ============================================
-- 1. Email Templates Table
-- ============================================
CREATE TABLE IF NOT EXISTS email_templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    subject TEXT NOT NULL,
    body_html TEXT NOT NULL,
    body_text TEXT,
    category TEXT CHECK (category IN ('onboarding', 'engagement', 'billing', 'support', 'announcement')),
    variables JSONB DEFAULT '{}', -- Available variables: {user_name, script_count, days_remaining, etc}
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES profiles(id) ON DELETE SET NULL
);

-- Index for template lookups
CREATE INDEX IF NOT EXISTS idx_email_templates_category 
ON email_templates(category, is_active);

CREATE INDEX IF NOT EXISTS idx_email_templates_created 
ON email_templates(created_at DESC);

-- ============================================
-- 2. Email Campaigns Table
-- ============================================
CREATE TABLE IF NOT EXISTS email_campaigns (
    campaign_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    template_id UUID REFERENCES email_templates(template_id) ON DELETE SET NULL,
    target_audience JSONB NOT NULL, -- Filter criteria: {subscription_status: [], days_since_signup: {}, etc}
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'scheduled', 'sending', 'sent', 'cancelled', 'failed')),
    scheduled_at TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    total_recipients INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    delivered_count INTEGER DEFAULT 0,
    opened_count INTEGER DEFAULT 0,
    clicked_count INTEGER DEFAULT 0,
    bounced_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES profiles(id) ON DELETE SET NULL
);

-- Indexes for campaign management
CREATE INDEX IF NOT EXISTS idx_email_campaigns_status 
ON email_campaigns(status, scheduled_at);

CREATE INDEX IF NOT EXISTS idx_email_campaigns_created 
ON email_campaigns(created_at DESC);

-- ============================================
-- 3. Email Logs Table
-- ============================================
CREATE TABLE IF NOT EXISTS email_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES email_campaigns(campaign_id) ON DELETE CASCADE,
    recipient_email TEXT NOT NULL,
    recipient_user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'queued' CHECK (status IN ('queued', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'failed', 'spam')),
    resend_email_id TEXT, -- Resend's email ID for tracking
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    opened_at TIMESTAMP WITH TIME ZONE,
    clicked_at TIMESTAMP WITH TIME ZONE,
    bounced_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB DEFAULT '{}', -- {links_clicked: [], user_agent: '', ip_address: ''}
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for email tracking
CREATE INDEX IF NOT EXISTS idx_email_logs_campaign 
ON email_logs(campaign_id, status);

CREATE INDEX IF NOT EXISTS idx_email_logs_recipient 
ON email_logs(recipient_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_email_logs_status 
ON email_logs(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_email_logs_resend 
ON email_logs(resend_email_id) WHERE resend_email_id IS NOT NULL;

-- ============================================
-- 4. Email Analytics Summary (Materialized View)
-- ============================================
CREATE MATERIALIZED VIEW IF NOT EXISTS email_campaign_stats AS
SELECT 
    c.campaign_id,
    c.name,
    c.status,
    c.sent_at,
    c.total_recipients,
    COUNT(l.log_id) as total_sent,
    COUNT(CASE WHEN l.status = 'delivered' THEN 1 END) as delivered,
    COUNT(CASE WHEN l.status = 'opened' THEN 1 END) as opened,
    COUNT(CASE WHEN l.status = 'clicked' THEN 1 END) as clicked,
    COUNT(CASE WHEN l.status = 'bounced' THEN 1 END) as bounced,
    COUNT(CASE WHEN l.status = 'failed' THEN 1 END) as failed,
    CASE 
        WHEN COUNT(l.log_id) > 0 
        THEN ROUND((COUNT(CASE WHEN l.status = 'opened' THEN 1 END)::NUMERIC / COUNT(l.log_id)::NUMERIC) * 100, 2)
        ELSE 0 
    END as open_rate,
    CASE 
        WHEN COUNT(l.log_id) > 0 
        THEN ROUND((COUNT(CASE WHEN l.status = 'clicked' THEN 1 END)::NUMERIC / COUNT(l.log_id)::NUMERIC) * 100, 2)
        ELSE 0 
    END as click_rate
FROM email_campaigns c
LEFT JOIN email_logs l ON c.campaign_id = l.campaign_id
GROUP BY c.campaign_id, c.name, c.status, c.sent_at, c.total_recipients;

-- Unique index on materialized view (MUST exist before CONCURRENTLY refresh)
-- Drop and recreate to ensure it's truly unique
DROP INDEX IF EXISTS idx_email_campaign_stats_campaign;
CREATE UNIQUE INDEX idx_email_campaign_stats_campaign 
ON email_campaign_stats(campaign_id);

-- ============================================
-- 5. Update Triggers
-- ============================================

-- Trigger to update email_templates.updated_at
CREATE OR REPLACE FUNCTION update_email_template_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_email_template_timestamp ON email_templates;
CREATE TRIGGER trigger_update_email_template_timestamp
BEFORE UPDATE ON email_templates
FOR EACH ROW
EXECUTE FUNCTION update_email_template_timestamp();

-- Trigger to update email_campaigns.updated_at
CREATE OR REPLACE FUNCTION update_email_campaign_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_email_campaign_timestamp ON email_campaigns;
CREATE TRIGGER trigger_update_email_campaign_timestamp
BEFORE UPDATE ON email_campaigns
FOR EACH ROW
EXECUTE FUNCTION update_email_campaign_timestamp();

-- Trigger to update campaign stats when email logs change
-- Note: Using non-concurrent refresh to avoid locking issues during user deletion
CREATE OR REPLACE FUNCTION refresh_email_campaign_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- Use non-concurrent refresh during deletions to avoid unique index requirement
    -- This briefly locks the view but ensures reliability
    REFRESH MATERIALIZED VIEW email_campaign_stats;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_refresh_campaign_stats ON email_logs;
CREATE TRIGGER trigger_refresh_campaign_stats
AFTER INSERT OR UPDATE OR DELETE ON email_logs
FOR EACH STATEMENT
EXECUTE FUNCTION refresh_email_campaign_stats();

-- ============================================
-- 6. Comments for Documentation
-- ============================================
COMMENT ON TABLE email_templates IS 'Reusable email templates with variable substitution';
COMMENT ON TABLE email_campaigns IS 'Email campaigns with audience targeting and tracking';
COMMENT ON TABLE email_logs IS 'Individual email delivery and engagement tracking';
COMMENT ON MATERIALIZED VIEW email_campaign_stats IS 'Aggregated campaign performance metrics';
