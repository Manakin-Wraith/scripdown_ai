-- Migration 029: Report Filter Presets
-- Persistence layer for reusable filter configurations

-- Create the presets table
CREATE TABLE IF NOT EXISTS report_filter_presets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    script_id UUID REFERENCES scripts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    filters JSONB NOT NULL DEFAULT '{}',
    categories JSONB DEFAULT '[]',
    group_by TEXT DEFAULT 'scene_number',
    sort_by TEXT DEFAULT 'scene_number',
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_filter_presets_script ON report_filter_presets(script_id);
CREATE INDEX IF NOT EXISTS idx_filter_presets_user ON report_filter_presets(user_id);
CREATE INDEX IF NOT EXISTS idx_filter_presets_default ON report_filter_presets(is_default) WHERE is_default = TRUE;

-- RLS policies
ALTER TABLE report_filter_presets ENABLE ROW LEVEL SECURITY;

-- Anyone can read default presets
CREATE POLICY "Default presets are readable by all"
    ON report_filter_presets FOR SELECT
    USING (is_default = TRUE);

-- Users can read their own presets
CREATE POLICY "Users can read own presets"
    ON report_filter_presets FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own presets
CREATE POLICY "Users can create own presets"
    ON report_filter_presets FOR INSERT
    WITH CHECK (auth.uid() = user_id AND is_default = FALSE);

-- Users can update their own presets
CREATE POLICY "Users can update own presets"
    ON report_filter_presets FOR UPDATE
    USING (auth.uid() = user_id AND is_default = FALSE);

-- Users can delete their own presets
CREATE POLICY "Users can delete own presets"
    ON report_filter_presets FOR DELETE
    USING (auth.uid() = user_id AND is_default = FALSE);

-- Seed default presets (no user_id, no script_id — global defaults)
INSERT INTO report_filter_presets (name, filters, categories, group_by, is_default) VALUES
(
    'Props Master''s View',
    '{}',
    '["props"]',
    'location',
    TRUE
),
(
    'Wardrobe Supervisor',
    '{}',
    '["wardrobe", "characters"]',
    'character',
    TRUE
),
(
    'Location Manager',
    '{}',
    '[]',
    'location',
    TRUE
),
(
    '1st AD Shooting Block',
    '{}',
    '[]',
    'story_day',
    TRUE
),
(
    'Makeup & Hair HOD',
    '{}',
    '["makeup", "characters"]',
    'character',
    TRUE
),
(
    'Stunt Coordinator',
    '{}',
    '["stunts", "characters"]',
    'scene_number',
    TRUE
),
(
    'VFX Supervisor',
    '{}',
    '["special_effects"]',
    'scene_number',
    TRUE
),
(
    'Transport Captain',
    '{}',
    '["vehicles"]',
    'location',
    TRUE
);
