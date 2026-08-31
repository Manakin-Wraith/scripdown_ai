-- Migration 050: Productions (build-sequence step 1 -- "the spine")
-- A production is a physical-shoot container that holds one or more
-- scripts. Independent axis from series/seasons. See
-- docs/superpowers/specs/2026-08-31-production-spine-design.md
-- Apply manually against the Supabase project (run_migration.py is dead).

-- ============================================
-- 1. productions
-- ============================================
CREATE TABLE IF NOT EXISTS productions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- ON DELETE CASCADE is load-bearing: 013_delete_user_safely.sql deletes
    -- the profile and relies on this cascade to clean up productions+units.
    -- Do NOT soften this to SET NULL.
    owner_id          UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title             TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'development'
                        CHECK (status IN ('development','prep','shooting','wrapped','archived')),
    shoot_start_date  DATE,
    shoot_end_date    DATE,
    notes             TEXT,
    created_by        UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (shoot_end_date IS NULL OR shoot_start_date IS NULL
           OR shoot_end_date >= shoot_start_date)
);

CREATE INDEX IF NOT EXISTS idx_productions_owner ON productions(owner_id);

-- reuse the updated_at trigger fn from migration 030
CREATE TRIGGER trg_productions_updated
    BEFORE UPDATE ON productions
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

-- ============================================
-- 2. units -- one "Main Unit" auto-created per production by the service layer
-- ============================================
CREATE TABLE IF NOT EXISTS units (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_id UUID NOT NULL REFERENCES productions(id) ON DELETE CASCADE,
    name          TEXT NOT NULL DEFAULT 'Main Unit',
    sort_order    INT NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_units_production ON units(production_id);

-- ============================================
-- 3. scripts.production_id -- a script belongs to <=1 production
-- ============================================
ALTER TABLE scripts
    ADD COLUMN IF NOT EXISTS production_id UUID REFERENCES productions(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_scripts_production ON scripts(production_id);

-- ============================================
-- 4. RLS -- owner-only backstop (backend uses service-role key; real
--    access control is app-layer in production_service.py). Intentionally
--    narrower than the app: GET /api/productions/:id also serves team
--    members with a script role, same as series.
-- ============================================
ALTER TABLE productions ENABLE ROW LEVEL SECURITY;
ALTER TABLE units ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage their own productions"
    ON productions FOR ALL USING (owner_id = auth.uid());

CREATE POLICY "Users view units of their productions"
    ON units FOR SELECT USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = units.production_id AND p.owner_id = auth.uid())
    );
CREATE POLICY "Users manage units of their productions"
    ON units FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = units.production_id AND p.owner_id = auth.uid())
    );
