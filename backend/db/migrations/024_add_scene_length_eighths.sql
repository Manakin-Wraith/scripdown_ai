-- Migration 024: Add Scene Length in Eighths
-- Date: 2026-02-03
-- Purpose: Add industry-standard scene length measurement in eighths (1 page = 8 eighths)

-- Add scene length in eighths column
ALTER TABLE scenes 
ADD COLUMN IF NOT EXISTS page_length_eighths INTEGER;

-- Add comment explaining the column
COMMENT ON COLUMN scenes.page_length_eighths IS 
'Scene length measured in eighths of a page (1 page = 8 eighths). Industry standard for production scheduling. 1/8 page ≈ 1 minute of screen time.';

-- Add index for reporting queries that filter/sort by scene length
CREATE INDEX IF NOT EXISTS idx_scenes_page_length_eighths 
ON scenes(page_length_eighths) WHERE page_length_eighths IS NOT NULL;

-- Add check constraint to ensure reasonable values (minimum 1/8, maximum 80 eighths = 10 pages)
ALTER TABLE scenes 
ADD CONSTRAINT chk_page_length_eighths_range 
CHECK (page_length_eighths IS NULL OR (page_length_eighths >= 1 AND page_length_eighths <= 80));
