-- Rollback Migration 025: Email Campaigns System
-- Run this to clean up any partial migration state

-- Drop triggers first
DROP TRIGGER IF EXISTS trigger_update_campaign_stats ON email_campaign_recipients;

-- Drop functions
DROP FUNCTION IF EXISTS update_campaign_stats();

-- Drop tables (cascade will remove foreign keys)
DROP TABLE IF EXISTS email_campaign_clicks CASCADE;
DROP TABLE IF EXISTS email_campaign_recipients CASCADE;
DROP TABLE IF EXISTS email_campaigns CASCADE;
DROP TABLE IF EXISTS email_templates CASCADE;

-- Drop any orphaned indexes (just in case)
DROP INDEX IF EXISTS idx_email_templates_category;
DROP INDEX IF EXISTS idx_email_templates_active;
DROP INDEX IF EXISTS idx_campaigns_status;
DROP INDEX IF EXISTS idx_campaigns_scheduled_at;
DROP INDEX IF EXISTS idx_campaigns_created_by;
DROP INDEX IF EXISTS idx_campaign_recipients_campaign;
DROP INDEX IF EXISTS idx_campaign_recipients_user;
DROP INDEX IF EXISTS idx_campaign_recipients_status;
DROP INDEX IF EXISTS idx_campaign_recipients_email;
DROP INDEX IF EXISTS idx_campaign_clicks_recipient;
DROP INDEX IF EXISTS idx_campaign_clicks_campaign;
DROP INDEX IF EXISTS idx_campaign_clicks_clicked_at;
