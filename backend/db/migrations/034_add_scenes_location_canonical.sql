-- Migration 034: Canonical base-place column for location dedup
-- Populated at write-time; grouping key for all location aggregation.

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS location_canonical TEXT;

CREATE INDEX IF NOT EXISTS idx_scenes_location_canonical
    ON scenes(script_id, location_canonical);
