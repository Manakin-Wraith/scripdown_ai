-- Migration 045: Series / Season grouping (Phase 1 -- grouping layer only)
-- A series groups seasons; a season groups episode scripts. Purely
-- organizational -- no changes to scripts.* analysis/billing columns,
-- and no changes to how an individual script is uploaded or analyzed.
-- scripts.season_id / scripts.episode_number are both nullable: a
-- standalone script (the common case, unchanged) has both NULL.

CREATE TABLE IF NOT EXISTS series (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_series_owner ON series(owner_id);

CREATE TABLE IF NOT EXISTS seasons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    series_id UUID NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    season_number INT NOT NULL,
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (series_id, season_number)
);

CREATE INDEX idx_seasons_series ON seasons(series_id);

ALTER TABLE scripts
    ADD COLUMN IF NOT EXISTS season_id UUID REFERENCES seasons(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS episode_number INT;

CREATE INDEX IF NOT EXISTS idx_scripts_season ON scripts(season_id);

-- RLS: owner-only, matching the existing pattern in
-- 030_shooting_schedules.sql. The backend uses the service-role key and
-- bypasses RLS for all app-layer access (per-episode team access is
-- enforced in Python via get_script_role, not here) -- this is a
-- defense-in-depth backstop for any direct client-side table access.
ALTER TABLE series ENABLE ROW LEVEL SECURITY;
ALTER TABLE seasons ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own series"
    ON series FOR SELECT
    USING (owner_id = auth.uid());

CREATE POLICY "Users can manage their own series"
    ON series FOR ALL
    USING (owner_id = auth.uid());

CREATE POLICY "Users can view seasons of their series"
    ON seasons FOR SELECT
    USING (
        series_id IN (SELECT id FROM series WHERE owner_id = auth.uid())
    );

CREATE POLICY "Users can manage seasons of their series"
    ON seasons FOR ALL
    USING (
        series_id IN (SELECT id FROM series WHERE owner_id = auth.uid())
    );
