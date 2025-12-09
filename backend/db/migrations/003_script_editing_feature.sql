-- Migration: Script Editing & Revision Tracking Feature (Phase 1)
-- Date: 2025-01-09
-- Description: Adds tables and columns for scene management, revision tracking, and shooting script export

-- ============================================
-- 1. Script Versions Table (Revision Tracking)
-- ============================================
-- Tracks different versions/revisions of a script

CREATE TABLE IF NOT EXISTS script_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    revision_color VARCHAR(20) DEFAULT 'white',
    -- Colors: white, blue, pink, yellow, green, goldenrod, buff, salmon, cherry
    pdf_path TEXT,                          -- Storage path for this version's PDF
    imported_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT,
    is_locked BOOLEAN DEFAULT FALSE,
    locked_at TIMESTAMPTZ,
    locked_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(script_id, version_number)
);

-- Index for version lookups
CREATE INDEX IF NOT EXISTS idx_script_versions_script 
ON script_versions(script_id, version_number);

-- ============================================
-- 2. Scene History Table (Change Tracking)
-- ============================================
-- Tracks changes to scenes for audit trail

CREATE TABLE IF NOT EXISTS scene_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scene_id UUID NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    version_id UUID REFERENCES script_versions(id),
    change_type VARCHAR(20) NOT NULL,
    -- Types: created, modified, omitted, split, merged, reordered
    previous_data JSONB,                    -- Snapshot before change
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    changed_by UUID REFERENCES auth.users(id)
);

-- Index for history lookups
CREATE INDEX IF NOT EXISTS idx_scene_history_scene 
ON scene_history(scene_id);

CREATE INDEX IF NOT EXISTS idx_scene_history_version 
ON scene_history(version_id);

-- ============================================
-- 3. Extend Scenes Table
-- ============================================
-- Add columns for scene management features

-- Scene omission tracking
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS is_omitted BOOLEAN DEFAULT FALSE;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS omitted_at TIMESTAMPTZ;

-- Scene numbering for locked scripts
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS original_scene_number VARCHAR(10);
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS locked_scene_number VARCHAR(10);

-- Revision tracking
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS revision_number INT DEFAULT 0;

-- Scene relationships (for split/merge)
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS parent_scene_id UUID REFERENCES scenes(id);
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS merged_into_scene_id UUID REFERENCES scenes(id);

-- Ensure scene_order column exists (may already exist)
-- ALTER TABLE scenes ADD COLUMN IF NOT EXISTS scene_order INT;

-- ============================================
-- 4. Extend Scripts Table
-- ============================================
-- Add columns for script locking and revision state

ALTER TABLE scripts ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT FALSE;
ALTER TABLE scripts ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ;
ALTER TABLE scripts ADD COLUMN IF NOT EXISTS locked_by UUID REFERENCES auth.users(id);
ALTER TABLE scripts ADD COLUMN IF NOT EXISTS current_revision_color VARCHAR(20) DEFAULT 'white';
ALTER TABLE scripts ADD COLUMN IF NOT EXISTS current_version_id UUID REFERENCES script_versions(id);

-- ============================================
-- 5. Enable Row Level Security
-- ============================================

ALTER TABLE script_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE scene_history ENABLE ROW LEVEL SECURITY;

-- ============================================
-- 6. RLS Policies for script_versions
-- ============================================

-- Users can view versions of scripts they own or are members of
CREATE POLICY "Users can view script versions" ON script_versions
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM scripts s 
            WHERE s.id = script_versions.script_id 
            AND (s.user_id = auth.uid() OR s.user_id IS NULL)
        )
        OR
        EXISTS (
            SELECT 1 FROM script_members sm 
            WHERE sm.script_id = script_versions.script_id 
            AND sm.user_id = auth.uid()
        )
    );

-- Users can insert versions for scripts they own
CREATE POLICY "Users can create script versions" ON script_versions
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM scripts s 
            WHERE s.id = script_versions.script_id 
            AND (s.user_id = auth.uid() OR s.user_id IS NULL)
        )
    );

-- Users can update versions for scripts they own
CREATE POLICY "Users can update script versions" ON script_versions
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM scripts s 
            WHERE s.id = script_versions.script_id 
            AND (s.user_id = auth.uid() OR s.user_id IS NULL)
        )
    );

-- ============================================
-- 7. RLS Policies for scene_history
-- ============================================

-- Users can view history of scenes in scripts they have access to
CREATE POLICY "Users can view scene history" ON scene_history
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM scenes sc
            JOIN scripts s ON s.id = sc.script_id
            WHERE sc.id = scene_history.scene_id 
            AND (s.user_id = auth.uid() OR s.user_id IS NULL)
        )
        OR
        EXISTS (
            SELECT 1 FROM scenes sc
            JOIN script_members sm ON sm.script_id = sc.script_id
            WHERE sc.id = scene_history.scene_id 
            AND sm.user_id = auth.uid()
        )
    );

-- Users can insert history for scenes in scripts they own
CREATE POLICY "Users can create scene history" ON scene_history
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM scenes sc
            JOIN scripts s ON s.id = sc.script_id
            WHERE sc.id = scene_history.scene_id 
            AND (s.user_id = auth.uid() OR s.user_id IS NULL)
        )
    );

-- ============================================
-- 8. Helper Function: Get Next Scene Order
-- ============================================

CREATE OR REPLACE FUNCTION get_next_scene_order(p_script_id UUID)
RETURNS INT AS $$
DECLARE
    max_order INT;
BEGIN
    SELECT COALESCE(MAX(scene_order), 0) INTO max_order
    FROM scenes
    WHERE script_id = p_script_id;
    
    RETURN max_order + 1;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 9. Helper Function: Reorder Scenes
-- ============================================

CREATE OR REPLACE FUNCTION reorder_scenes(
    p_script_id UUID,
    p_scene_ids UUID[]
)
RETURNS VOID AS $$
DECLARE
    i INT;
    scene_id UUID;
BEGIN
    -- Update scene_order for each scene in the array
    FOR i IN 1..array_length(p_scene_ids, 1) LOOP
        scene_id := p_scene_ids[i];
        
        UPDATE scenes
        SET scene_order = i
        WHERE id = scene_id AND script_id = p_script_id;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 10. Revision Color Sequence Reference
-- ============================================
-- Industry-standard revision page colors:
-- 1. White (initial)
-- 2. Blue
-- 3. Pink
-- 4. Yellow
-- 5. Green
-- 6. Goldenrod
-- 7. Buff
-- 8. Salmon
-- 9. Cherry
-- 10+ Double White, Double Blue, etc.

COMMENT ON TABLE script_versions IS 'Tracks different versions/revisions of a script for revision management';
COMMENT ON TABLE scene_history IS 'Audit trail for scene changes (reorder, omit, split, merge)';
COMMENT ON COLUMN scripts.is_locked IS 'When true, scene numbers are frozen for production';
COMMENT ON COLUMN scripts.current_revision_color IS 'Current revision color (white, blue, pink, etc.)';
COMMENT ON COLUMN scenes.is_omitted IS 'Scene marked as OMITTED but keeps its number';
COMMENT ON COLUMN scenes.locked_scene_number IS 'Scene number assigned when script was locked';
