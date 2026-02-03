-- Migration: Enhanced Breakdown Fields for PDF Export
-- Date: 2026-02-02
-- Description: Adds missing breakdown categories to scenes table for comprehensive PDF reports

-- ============================================
-- 1. Add Missing Breakdown Category Columns
-- ============================================
-- These JSONB columns store arrays of breakdown items per scene

-- Makeup & Hair requirements
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS makeup JSONB DEFAULT '[]'::jsonb;

-- Special Effects (SFX/VFX) requirements
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS special_effects JSONB DEFAULT '[]'::jsonb;

-- Vehicles in scene
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS vehicles JSONB DEFAULT '[]'::jsonb;

-- Animals in scene
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS animals JSONB DEFAULT '[]'::jsonb;

-- Background actors/extras
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS extras JSONB DEFAULT '[]'::jsonb;

-- Stunt requirements
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS stunts JSONB DEFAULT '[]'::jsonb;

-- ============================================
-- 2. Add Enhanced Scene Description Fields
-- ============================================
-- These TEXT columns provide additional context for reports

-- Summary of action lines (physical action description)
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS action_description TEXT;

-- Emotional tone/mood of the scene
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS emotional_tone TEXT;

-- Technical requirements (camera, lighting, etc.)
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS technical_notes TEXT;

-- Sound/music requirements
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS sound_notes TEXT;

-- ============================================
-- 3. Add Column Comments for Documentation
-- ============================================

COMMENT ON COLUMN scenes.makeup IS 'Makeup and hair requirements (JSONB array of objects or strings)';
COMMENT ON COLUMN scenes.special_effects IS 'SFX/VFX requirements (JSONB array of objects or strings)';
COMMENT ON COLUMN scenes.vehicles IS 'Vehicles appearing in scene (JSONB array of objects or strings)';
COMMENT ON COLUMN scenes.animals IS 'Animals appearing in scene (JSONB array of objects or strings)';
COMMENT ON COLUMN scenes.extras IS 'Background actors/extras requirements (JSONB array of objects or strings)';
COMMENT ON COLUMN scenes.stunts IS 'Stunt requirements and choreography (JSONB array of objects or strings)';
COMMENT ON COLUMN scenes.action_description IS 'Summary of physical action from action lines';
COMMENT ON COLUMN scenes.emotional_tone IS 'Emotional mood/tone of the scene (e.g., Tense, Romantic, Comedic)';
COMMENT ON COLUMN scenes.technical_notes IS 'Technical requirements (camera, lighting, special equipment)';
COMMENT ON COLUMN scenes.sound_notes IS 'Sound effects and music requirements';

-- ============================================
-- 4. Create Indexes for Performance
-- ============================================
-- GIN indexes for JSONB columns to enable efficient querying

CREATE INDEX IF NOT EXISTS idx_scenes_makeup_gin ON scenes USING GIN (makeup);
CREATE INDEX IF NOT EXISTS idx_scenes_special_effects_gin ON scenes USING GIN (special_effects);
CREATE INDEX IF NOT EXISTS idx_scenes_vehicles_gin ON scenes USING GIN (vehicles);
CREATE INDEX IF NOT EXISTS idx_scenes_animals_gin ON scenes USING GIN (animals);
CREATE INDEX IF NOT EXISTS idx_scenes_extras_gin ON scenes USING GIN (extras);
CREATE INDEX IF NOT EXISTS idx_scenes_stunts_gin ON scenes USING GIN (stunts);

-- ============================================
-- 5. Data Structure Examples (Documentation)
-- ============================================

-- Example makeup entry:
-- {
--   "character": "SARAH",
--   "requirements": ["Bruised face", "Cut on forehead"],
--   "notes": "Continuity from Scene 8"
-- }
-- OR simple string: "Blood makeup"

-- Example special_effects entry:
-- {
--   "type": "practical",
--   "effect": "Gunshot squib",
--   "quantity": 3,
--   "notes": "Chest hits"
-- }
-- OR simple string: "Rain effect"

-- Example vehicles entry:
-- {
--   "type": "Police car",
--   "make_model": "Ford Crown Victoria",
--   "hero": true,
--   "notes": "Must be period accurate (1990s)"
-- }
-- OR simple string: "Police car"

-- Example animals entry:
-- {
--   "type": "Dog",
--   "breed": "German Shepherd",
--   "quantity": 1,
--   "notes": "Trained for aggression scenes"
-- }
-- OR simple string: "German Shepherd"

-- Example extras entry:
-- {
--   "type": "Crowd",
--   "quantity": "20-30",
--   "notes": "Period costumes, 1940s"
-- }
-- OR simple string: "Restaurant patrons (8)"

-- Example stunts entry:
-- {
--   "type": "Car crash",
--   "performers": 2,
--   "notes": "Requires stunt coordinator, safety rigging"
-- }
-- OR simple string: "Fight choreography"

-- ============================================
-- 6. Migration Verification Query
-- ============================================

-- Run this query to verify the migration succeeded:
-- SELECT 
--   column_name, 
--   data_type, 
--   column_default,
--   is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'scenes'
-- AND column_name IN ('makeup', 'special_effects', 'vehicles', 'animals', 'extras', 'stunts', 
--                     'action_description', 'emotional_tone', 'technical_notes', 'sound_notes')
-- ORDER BY column_name;
