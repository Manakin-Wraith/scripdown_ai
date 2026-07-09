-- Migration 035: Location Aliases for Merge/Dedup System
-- Stores merge history so re-analysis doesn't re-introduce duplicates.

CREATE TABLE IF NOT EXISTS location_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    canonical_place TEXT NOT NULL,
    alias_place TEXT NOT NULL,
    merged_by UUID REFERENCES auth.users(id),
    merged_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(script_id, alias_place)
);

CREATE INDEX idx_location_aliases_script ON location_aliases(script_id);
CREATE INDEX idx_location_aliases_lookup ON location_aliases(script_id, alias_place);

-- RLS
ALTER TABLE location_aliases ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Script owner can manage location aliases"
    ON location_aliases FOR ALL
    USING (
        script_id IN (
            SELECT id FROM scripts WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Team members can read location aliases"
    ON location_aliases FOR SELECT
    USING (
        script_id IN (
            SELECT script_id FROM script_members WHERE user_id = auth.uid()
        )
    );
