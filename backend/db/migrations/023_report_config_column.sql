-- Migration: Add config column to reports table
-- Description: Adds JSONB config column to store report configuration (filters, presets, options)
-- Date: 2026-02-03

-- Add config column to reports table
ALTER TABLE reports 
ADD COLUMN IF NOT EXISTS config JSONB DEFAULT '{}'::jsonb;

-- Add GIN index for efficient JSONB queries
CREATE INDEX IF NOT EXISTS idx_reports_config_gin 
ON reports USING GIN (config);

-- Add comment for documentation
COMMENT ON COLUMN reports.config IS 'Report configuration including report_type, filters, categories, and display options';

-- Example queries:
-- Find all wardrobe reports:
-- SELECT * FROM reports WHERE config->>'report_type' = 'wardrobe';
--
-- Find reports with cross-references enabled:
-- SELECT * FROM reports WHERE config->>'show_cross_references' = 'true';
--
-- Find reports for specific categories:
-- SELECT * FROM reports WHERE config->'include_categories' @> '["wardrobe"]'::jsonb;
