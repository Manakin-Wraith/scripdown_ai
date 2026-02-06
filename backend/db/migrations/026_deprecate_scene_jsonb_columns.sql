-- ============================================================================
-- Migration 026: Deprecate scenes JSONB breakdown columns
-- ============================================================================
-- 
-- STATUS: STAGED — DO NOT APPLY until all consumers are migrated.
--
-- CONTEXT:
--   extraction_metadata is now the single source of truth (SSoT) for all
--   breakdown data. The scenes table JSONB columns below are no longer
--   written to (aggregate_extractions_to_scenes() was removed).
--
-- PREREQUISITE: Migrate these remaining consumers BEFORE running this:
--
--   Frontend (still read scene.characters / scene.props / etc.):
--     - SharedReportView.jsx
--     - Stripboard.jsx
--     - ShootingScriptPreview.jsx
--     - FilteredSceneList.jsx
--     - CharacterDashboard.jsx
--     - LocationDashboard.jsx
--     - SceneCard.jsx
--
--   Backend (still read scene.get('characters') / etc.):
--     - report_service.py  (aggregate_scene_data — fallback path)
--     - supabase_routes.py (character_count, prop_count, merge logic)
--
-- See docs/rich_update.md for full details.
-- ============================================================================

-- Step 1: Add deprecation comments to columns (safe, non-breaking)
COMMENT ON COLUMN scenes.characters IS 'DEPRECATED — use extraction_metadata table instead';
COMMENT ON COLUMN scenes.props IS 'DEPRECATED — use extraction_metadata table instead';
COMMENT ON COLUMN scenes.wardrobe IS 'DEPRECATED — use extraction_metadata table instead';
COMMENT ON COLUMN scenes.special_fx IS 'DEPRECATED — use extraction_metadata table instead';
COMMENT ON COLUMN scenes.vehicles IS 'DEPRECATED — use extraction_metadata table instead';
COMMENT ON COLUMN scenes.sound IS 'DEPRECATED — use extraction_metadata table instead';
COMMENT ON COLUMN scenes.makeup_hair IS 'DEPRECATED — use extraction_metadata table instead';
COMMENT ON COLUMN scenes.animals IS 'DEPRECATED — use extraction_metadata table instead';
COMMENT ON COLUMN scenes.extras IS 'DEPRECATED — use extraction_metadata table instead';
COMMENT ON COLUMN scenes.stunts IS 'DEPRECATED — use extraction_metadata table instead';

-- Step 2: Drop columns (UNCOMMENT only after all consumers are migrated)
-- ALTER TABLE scenes DROP COLUMN IF EXISTS characters;
-- ALTER TABLE scenes DROP COLUMN IF EXISTS props;
-- ALTER TABLE scenes DROP COLUMN IF EXISTS wardrobe;
-- ALTER TABLE scenes DROP COLUMN IF EXISTS special_fx;
-- ALTER TABLE scenes DROP COLUMN IF EXISTS vehicles;
-- ALTER TABLE scenes DROP COLUMN IF EXISTS sound;
-- ALTER TABLE scenes DROP COLUMN IF EXISTS makeup_hair;
-- ALTER TABLE scenes DROP COLUMN IF EXISTS animals;
-- ALTER TABLE scenes DROP COLUMN IF EXISTS extras;
-- ALTER TABLE scenes DROP COLUMN IF EXISTS stunts;
