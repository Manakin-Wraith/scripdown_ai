-- LangExtract Integration Migration
-- Adds tables and columns for structured extraction with source grounding
-- Date: 2026-02-05

-- ============================================================================
-- 1. CREATE extraction_metadata TABLE
-- ============================================================================
-- Stores all LangExtract extractions with character-level source positions

CREATE TABLE IF NOT EXISTS extraction_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    scene_id UUID REFERENCES scenes(id) ON DELETE CASCADE,
    extraction_class TEXT NOT NULL CHECK (
        extraction_class IN (
            'scene_header', 'character', 'prop', 'wardrobe', 
            'dialogue', 'action', 'emotion', 'relationship',
            'special_fx', 'vehicle', 'sound', 'location_detail',
            'transition', 'makeup_hair'
        )
    ),
    extraction_text TEXT NOT NULL,
    text_start INTEGER NOT NULL CHECK (text_start >= 0),
    text_end INTEGER NOT NULL CHECK (text_end >= text_start),
    attributes JSONB DEFAULT '{}',
    confidence REAL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_extraction_script ON extraction_metadata(script_id);
CREATE INDEX idx_extraction_scene ON extraction_metadata(scene_id);
CREATE INDEX idx_extraction_class ON extraction_metadata(extraction_class);
CREATE INDEX idx_extraction_text_range ON extraction_metadata(script_id, text_start, text_end);

-- Table comment
COMMENT ON TABLE extraction_metadata IS 'LangExtract structured extractions with source grounding. Each row represents one extracted element with character-level text positions.';
COMMENT ON COLUMN extraction_metadata.extraction_class IS 'Type of extraction: scene_header, character, prop, wardrobe, dialogue, action, emotion, relationship, special_fx, vehicle, sound, location_detail, transition, makeup_hair';
COMMENT ON COLUMN extraction_metadata.text_start IS 'Character position in scripts.full_text where extraction starts (0-indexed)';
COMMENT ON COLUMN extraction_metadata.text_end IS 'Character position in scripts.full_text where extraction ends (exclusive)';
COMMENT ON COLUMN extraction_metadata.attributes IS 'Class-specific attributes as JSON (e.g., {"speaker": "JOHN", "line": "Hello"} for dialogue)';
COMMENT ON COLUMN extraction_metadata.confidence IS 'LangExtract confidence score (0.0-1.0), higher is more confident';

-- ============================================================================
-- 2. CREATE extraction_visualizations TABLE
-- ============================================================================
-- Stores generated HTML visualizations from LangExtract

CREATE TABLE IF NOT EXISTS extraction_visualizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    html_content TEXT NOT NULL,
    file_size INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for quick lookup
CREATE INDEX idx_viz_script ON extraction_visualizations(script_id);

-- Table comment
COMMENT ON TABLE extraction_visualizations IS 'Generated HTML visualizations from LangExtract with interactive highlighting and filtering';
COMMENT ON COLUMN extraction_visualizations.html_content IS 'Complete HTML document with embedded JavaScript for interactive visualization';
COMMENT ON COLUMN extraction_visualizations.file_size IS 'Size of HTML content in bytes';

-- ============================================================================
-- 3. EXTEND scenes TABLE
-- ============================================================================
-- Add source grounding columns to track text positions

ALTER TABLE scenes 
ADD COLUMN IF NOT EXISTS text_start INTEGER CHECK (text_start >= 0),
ADD COLUMN IF NOT EXISTS text_end INTEGER CHECK (text_end >= text_start),
ADD COLUMN IF NOT EXISTS extraction_confidence REAL CHECK (extraction_confidence >= 0.0 AND extraction_confidence <= 1.0);

-- Column comments
COMMENT ON COLUMN scenes.text_start IS 'Character position in scripts.full_text where scene starts (0-indexed)';
COMMENT ON COLUMN scenes.text_end IS 'Character position in scripts.full_text where scene ends (exclusive)';
COMMENT ON COLUMN scenes.extraction_confidence IS 'LangExtract confidence score for scene detection (0.0-1.0)';

-- ============================================================================
-- 4. EXTEND scripts TABLE
-- ============================================================================
-- Add visualization tracking flag

ALTER TABLE scripts 
ADD COLUMN IF NOT EXISTS has_visualization BOOLEAN DEFAULT FALSE;

-- Column comment
COMMENT ON COLUMN scripts.has_visualization IS 'True if LangExtract HTML visualization has been generated for this script';

-- ============================================================================
-- 5. ENABLE ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE extraction_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE extraction_visualizations ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 6. CREATE RLS POLICIES
-- ============================================================================

-- extraction_metadata policies
CREATE POLICY "Users can view their script extractions"
ON extraction_metadata FOR SELECT
USING (
    script_id IN (
        SELECT id FROM scripts WHERE user_id = auth.uid()
    )
    OR
    -- Allow script members to view extractions
    script_id IN (
        SELECT script_id FROM script_members WHERE user_id = auth.uid()
    )
);

CREATE POLICY "Users can create extractions for their scripts"
ON extraction_metadata FOR INSERT
WITH CHECK (
    script_id IN (
        SELECT id FROM scripts WHERE user_id = auth.uid()
    )
);

CREATE POLICY "Users can delete their script extractions"
ON extraction_metadata FOR DELETE
USING (
    script_id IN (
        SELECT id FROM scripts WHERE user_id = auth.uid()
    )
);

-- extraction_visualizations policies
CREATE POLICY "Users can view their script visualizations"
ON extraction_visualizations FOR SELECT
USING (
    script_id IN (
        SELECT id FROM scripts WHERE user_id = auth.uid()
    )
    OR
    -- Allow script members to view visualizations
    script_id IN (
        SELECT script_id FROM script_members WHERE user_id = auth.uid()
    )
);

CREATE POLICY "Users can create visualizations for their scripts"
ON extraction_visualizations FOR INSERT
WITH CHECK (
    script_id IN (
        SELECT id FROM scripts WHERE user_id = auth.uid()
    )
);

CREATE POLICY "Users can delete their script visualizations"
ON extraction_visualizations FOR DELETE
USING (
    script_id IN (
        SELECT id FROM scripts WHERE user_id = auth.uid()
    )
);

-- ============================================================================
-- 7. CREATE HELPER FUNCTIONS
-- ============================================================================

-- Function to get extraction statistics for a script
CREATE OR REPLACE FUNCTION get_extraction_stats(p_script_id UUID)
RETURNS TABLE (
    extraction_class TEXT,
    count BIGINT,
    avg_confidence REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        em.extraction_class,
        COUNT(*) as count,
        AVG(em.confidence)::REAL as avg_confidence
    FROM extraction_metadata em
    WHERE em.script_id = p_script_id
    GROUP BY em.extraction_class
    ORDER BY count DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_extraction_stats IS 'Returns extraction statistics grouped by class for a given script';

-- Function to get extractions within a text range
CREATE OR REPLACE FUNCTION get_extractions_in_range(
    p_script_id UUID,
    p_start INTEGER,
    p_end INTEGER
)
RETURNS SETOF extraction_metadata AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM extraction_metadata
    WHERE script_id = p_script_id
    AND text_start >= p_start
    AND text_end <= p_end
    ORDER BY text_start;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_extractions_in_range IS 'Returns all extractions within a specified text range (useful for scene-level queries)';

-- ============================================================================
-- 8. CREATE VIEWS
-- ============================================================================

-- View for extraction summary by script
CREATE OR REPLACE VIEW extraction_summary AS
SELECT 
    s.id as script_id,
    s.title as script_title,
    s.user_id,
    COUNT(DISTINCT em.id) as total_extractions,
    COUNT(DISTINCT em.extraction_class) as unique_classes,
    AVG(em.confidence) as avg_confidence,
    s.has_visualization,
    MAX(em.created_at) as last_extraction_at
FROM scripts s
LEFT JOIN extraction_metadata em ON s.id = em.script_id
GROUP BY s.id, s.title, s.user_id, s.has_visualization;

COMMENT ON VIEW extraction_summary IS 'Summary view of extraction statistics per script';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Verify tables were created
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'extraction_metadata') THEN
        RAISE NOTICE 'extraction_metadata table created successfully';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'extraction_visualizations') THEN
        RAISE NOTICE 'extraction_visualizations table created successfully';
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'scenes' AND column_name = 'text_start'
    ) THEN
        RAISE NOTICE 'scenes table extended successfully';
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'scripts' AND column_name = 'has_visualization'
    ) THEN
        RAISE NOTICE 'scripts table extended successfully';
    END IF;
    
    RAISE NOTICE 'LangExtract integration migration completed successfully!';
END $$;
