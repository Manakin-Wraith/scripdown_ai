-- Migration 026: ScreenPy Grammar Parser Integration
--
-- 1. Creates scene_candidates table (pre-AI detection, never existed in Supabase)
-- 2. Extends scenes table with ScreenPy enrichment columns
--
-- See docs/SCREENPY_BRAINSTORM.md §8 for full schema spec.

-- =============================================
-- 1. CREATE scene_candidates table
--    This table stores pre-AI scene detection results.
--    It was previously SQLite-only; now promoted to Supabase.
-- =============================================

CREATE TABLE IF NOT EXISTS scene_candidates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id       UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    scene_number_original TEXT,
    scene_order     INTEGER,
    int_ext         TEXT,
    setting         TEXT,
    time_of_day     TEXT,
    page_start      INTEGER,
    page_end        INTEGER,
    text_start      INTEGER,
    text_end        INTEGER,
    content_hash    TEXT,
    status          TEXT DEFAULT 'pending',
    error_message   TEXT,

    -- ScreenPy enrichment columns (Phase 1)
    location_hierarchy JSONB DEFAULT '[]'::jsonb,
    speaker_list       JSONB DEFAULT '{}'::jsonb,
    shot_type          TEXT,
    transitions        JSONB DEFAULT '[]'::jsonb,
    parse_method       TEXT DEFAULT 'regex',

    created_at      TIMESTAMPTZ DEFAULT now(),
    processed_at    TIMESTAMPTZ
);

-- =============================================
-- 2. Indexes on scene_candidates
-- =============================================

CREATE INDEX IF NOT EXISTS idx_scene_candidates_script_status
    ON scene_candidates(script_id, status);

CREATE INDEX IF NOT EXISTS idx_scene_candidates_content_hash
    ON scene_candidates(script_id, content_hash);

CREATE INDEX IF NOT EXISTS idx_scene_candidates_parse_method
    ON scene_candidates(parse_method);

-- =============================================
-- 3. Extend scenes with ScreenPy enrichment
-- =============================================

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS
    location_parent TEXT;

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS
    location_specific TEXT;

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS
    location_hierarchy JSONB DEFAULT '[]'::jsonb;

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS
    shot_type TEXT;

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS
    speakers JSONB DEFAULT '[]'::jsonb;

-- =============================================
-- 4. Indexes on scenes
-- =============================================

CREATE INDEX IF NOT EXISTS idx_scenes_location_parent
    ON scenes(location_parent) WHERE location_parent IS NOT NULL;

-- =============================================
-- 5. RLS — match project convention (disabled for dev)
-- =============================================

ALTER TABLE scene_candidates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "scene_candidates_all_access" ON scene_candidates
    FOR ALL USING (true) WITH CHECK (true);

-- =============================================
-- 6. Comments for documentation
-- =============================================

COMMENT ON TABLE scene_candidates IS
    'Pre-AI scene detection results from grammar or regex parser. Created during upload Phase 1.';
COMMENT ON COLUMN scene_candidates.parse_method IS
    'Parser that detected this scene: grammar or regex';
COMMENT ON COLUMN scene_candidates.speaker_list IS
    'Speaker names and dialogue counts extracted by ScreenPy grammar parser';
COMMENT ON COLUMN scene_candidates.location_hierarchy IS
    'Hierarchical location parts parsed from scene header (e.g., ["BURGER JOINT", "KITCHEN"])';
COMMENT ON COLUMN scenes.location_parent IS
    'Parent location from header (e.g., BURGER JOINT from INT. BURGER JOINT - KITCHEN)';
COMMENT ON COLUMN scenes.location_specific IS
    'Specific sub-location (e.g., KITCHEN from INT. BURGER JOINT - KITCHEN)';
COMMENT ON COLUMN scenes.speakers IS
    'Pre-extracted speaker names from dialogue parsing (ScreenPy). Supplements AI character extraction.';
COMMENT ON COLUMN scenes.shot_type IS
    'Shot type detected by grammar parser (CLOSE, WIDE, POV, etc.)';
