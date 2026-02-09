-- Migration 027: ScreenPy Phase 3 — Add transitions + parse_method to scenes table
-- These columns already exist in scene_candidates but were not propagated to the UI-facing scenes table.

-- 1. Add transitions JSONB to scenes (stores CUT TO, DISSOLVE TO, etc.)
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS
    transitions JSONB DEFAULT '[]'::jsonb;

-- 2. Add parse_method to scenes (grammar or regex)
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS
    parse_method TEXT DEFAULT 'regex';

-- 3. Add scene_number_original for display (may already exist from prior migrations)
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS
    scene_number_original TEXT;

-- 4. Comments
COMMENT ON COLUMN scenes.transitions IS
    'Scene transitions detected by ScreenPy grammar parser (e.g., CUT TO, DISSOLVE TO, FADE OUT)';
COMMENT ON COLUMN scenes.parse_method IS
    'How this scene was detected: grammar (ScreenPy) or regex (fallback)';

-- 5. Backfill parse_method from scene_candidates for existing scenes
UPDATE scenes s
SET 
    parse_method = COALESCE(sc.parse_method, 'regex'),
    transitions = COALESCE(sc.transitions, '[]'::jsonb)
FROM scene_candidates sc
WHERE s.script_id = sc.script_id
  AND s.scene_order = sc.scene_order
  AND s.parse_method = 'regex'
  AND sc.parse_method IS NOT NULL;
