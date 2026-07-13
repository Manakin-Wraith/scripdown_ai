-- Migration 038: Sub-Location Aliases for sticky sub-location renames.
-- Parent-scoped analogue of location_aliases: keeps a sub-location rename
-- (e.g. POOL -> SWIMMING POOL under VILLA) from reverting on re-analysis.

CREATE TABLE IF NOT EXISTS sub_location_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    parent_place TEXT NOT NULL,
    alias_sub TEXT NOT NULL,
    canonical_sub TEXT NOT NULL,
    renamed_by UUID REFERENCES auth.users(id),
    renamed_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(script_id, parent_place, alias_sub)
);

CREATE INDEX idx_sub_location_aliases_script ON sub_location_aliases(script_id);
CREATE INDEX idx_sub_location_aliases_lookup
    ON sub_location_aliases(script_id, parent_place, alias_sub);

ALTER TABLE sub_location_aliases ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Script owner can manage sub location aliases"
    ON sub_location_aliases FOR ALL
    USING (
        script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
    );

CREATE POLICY "Team members can read sub location aliases"
    ON sub_location_aliases FOR SELECT
    USING (
        script_id IN (SELECT script_id FROM script_members WHERE user_id = auth.uid())
    );
