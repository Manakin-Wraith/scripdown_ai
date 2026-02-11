-- Migration: 028_story_days.sql
-- Story Days Phase 1: Add story day columns to scenes + total_story_days to scripts
-- Spec: docs/STORY_DAYS_BRAINSTORM.md (Option C Enhanced)

-- ============================================
-- 1. Add story day columns to scenes
-- ============================================

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS story_day INTEGER;
-- Nullable: NULL = not yet determined or timeless/abstract scene.
-- 1-based numbering for present-timeline scenes.

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS story_day_label TEXT;
-- Human-readable label, e.g., "Day 1", "Flashback — Day 3", "Dream Sequence"

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS time_transition TEXT;
-- AI-extracted transition cue from previous scene.
-- e.g., "THE NEXT MORNING", "CONTINUOUS", "THREE MONTHS LATER", ""

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS is_new_story_day BOOLEAN DEFAULT FALSE;
-- AI-determined: does this scene start a new narrative day?
-- Used by recalculate_story_days() to increment the day counter.

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS story_day_confidence FLOAT DEFAULT 0.0;
-- AI confidence in the is_new_story_day determination (0.0-1.0)

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS story_day_is_manual BOOLEAN DEFAULT FALSE;
-- Whether the user manually set is_new_story_day (overrides AI)

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS story_day_is_locked BOOLEAN DEFAULT FALSE;
-- Whether the user locked this scene's story_day number.
-- recalculate_story_days() respects locked values and resets its counter.

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS timeline_code VARCHAR(20) DEFAULT 'PRESENT';
-- PRESENT | FLASHBACK | DREAM | FANTASY | MONTAGE | TITLE_CARD
-- Determines how story_day is interpreted and displayed.

-- ============================================
-- 2. Indexes
-- ============================================

CREATE INDEX IF NOT EXISTS idx_scenes_story_day ON scenes(script_id, story_day);
CREATE INDEX IF NOT EXISTS idx_scenes_timeline ON scenes(script_id, timeline_code);

-- ============================================
-- 3. Script-level metadata
-- ============================================

ALTER TABLE scripts ADD COLUMN IF NOT EXISTS total_story_days INTEGER DEFAULT 0;

-- ============================================
-- 4. Comments
-- ============================================

COMMENT ON COLUMN scenes.story_day IS 'Narrative day number (1-based). NULL = not yet determined or timeless.';
COMMENT ON COLUMN scenes.story_day_label IS 'Human-readable day label (e.g., "Day 1", "Flashback — Day 3")';
COMMENT ON COLUMN scenes.time_transition IS 'Time transition cue from previous scene (AI-extracted)';
COMMENT ON COLUMN scenes.is_new_story_day IS 'Whether this scene starts a new narrative day (AI or manual)';
COMMENT ON COLUMN scenes.story_day_confidence IS 'AI confidence in is_new_story_day (0.0-1.0)';
COMMENT ON COLUMN scenes.story_day_is_manual IS 'Whether is_new_story_day was manually set by user';
COMMENT ON COLUMN scenes.story_day_is_locked IS 'Whether story_day number is locked (recalculate respects this)';
COMMENT ON COLUMN scenes.timeline_code IS 'Timeline type: PRESENT, FLASHBACK, DREAM, FANTASY, MONTAGE, TITLE_CARD';
COMMENT ON COLUMN scripts.total_story_days IS 'Total unique story days in script';
