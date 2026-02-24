-- Migration 031: Character Aliases for Merge/Dedup System
-- Stores merge history so re-analysis doesn't re-introduce duplicates

CREATE TABLE IF NOT EXISTS character_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    canonical_name TEXT NOT NULL,
    alias TEXT NOT NULL,
    merged_by UUID REFERENCES auth.users(id),
    merged_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(script_id, alias)
);

CREATE INDEX idx_character_aliases_script ON character_aliases(script_id);
CREATE INDEX idx_character_aliases_lookup ON character_aliases(script_id, alias);

-- RLS
ALTER TABLE character_aliases ENABLE ROW LEVEL SECURITY;

-- Script owner can manage aliases
CREATE POLICY "Script owner can manage character aliases"
    ON character_aliases FOR ALL
    USING (
        script_id IN (
            SELECT id FROM scripts WHERE user_id = auth.uid()
        )
    );

-- Team members can read aliases
CREATE POLICY "Team members can read character aliases"
    ON character_aliases FOR SELECT
    USING (
        script_id IN (
            SELECT script_id FROM script_members WHERE user_id = auth.uid()
        )
    );
