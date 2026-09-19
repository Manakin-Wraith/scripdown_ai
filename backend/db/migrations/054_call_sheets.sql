-- Migration 054: Call sheets (build-sequence step 4)
-- See docs/superpowers/specs/2026-09-18-call-sheets-design.md
-- Apply manually against the Supabase project (run_migration.py is dead).
--
-- Call sheets are anchored to a shooting_day (script-role world) but their
-- content (crew, cast, locations) belongs to the production-role world.
-- Gated by require_production_role, not require_script_role -- see the
-- spec's "permission-system fork" section. production_id is denormalized
-- onto call_sheets at creation time so every permission check afterwards
-- is a single-column lookup, not a join chain.

-- ============================================
-- 0. New capability column on the existing production-role tables
-- ============================================
ALTER TABLE production_members
    ADD COLUMN IF NOT EXISTS can_edit_call_sheets boolean NOT NULL DEFAULT false;
ALTER TABLE production_invites
    ADD COLUMN IF NOT EXISTS can_edit_call_sheets boolean NOT NULL DEFAULT false;

-- ============================================
-- 1. call_sheets -- one per shooting_day (single-unit scope: UNIQUE)
-- ============================================
CREATE TABLE IF NOT EXISTS call_sheets (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_id    UUID NOT NULL REFERENCES productions(id) ON DELETE CASCADE,
    shooting_day_id  UUID NOT NULL UNIQUE REFERENCES shooting_days(id) ON DELETE CASCADE,
    status           TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published')),
    weather          TEXT,
    sunrise_time     TIME,
    sunset_time      TIME,
    breakfast_time   TIME,
    lunch_time       TIME,
    nearest_hospital TEXT,
    parking_notes    TEXT,
    safety_notes     TEXT,
    general_notes    TEXT,
    created_by       UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_call_sheets_production ON call_sheets(production_id);

CREATE TRIGGER trg_call_sheets_updated
    BEFORE UPDATE ON call_sheets
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

-- ============================================
-- 2. call_sheet_locations
-- ============================================
CREATE TABLE IF NOT EXISTS call_sheet_locations (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_sheet_id UUID NOT NULL REFERENCES call_sheets(id) ON DELETE CASCADE,
    location_id   UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    is_primary    BOOLEAN NOT NULL DEFAULT false,
    sort_order    INT NOT NULL DEFAULT 0,
    UNIQUE (call_sheet_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_call_sheet_locations_sheet ON call_sheet_locations(call_sheet_id);

-- ============================================
-- 3. call_sheet_crew
-- ============================================
CREATE TABLE IF NOT EXISTS call_sheet_crew (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_sheet_id UUID NOT NULL REFERENCES call_sheets(id) ON DELETE CASCADE,
    crew_id       UUID NOT NULL REFERENCES production_crew(id) ON DELETE CASCADE,
    call_time     TIME,
    notes         TEXT,
    UNIQUE (call_sheet_id, crew_id)
);

CREATE INDEX IF NOT EXISTS idx_call_sheet_crew_sheet ON call_sheet_crew(call_sheet_id);

-- ============================================
-- 4. call_sheet_cast
-- ============================================
CREATE TABLE IF NOT EXISTS call_sheet_cast (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_sheet_id UUID NOT NULL REFERENCES call_sheets(id) ON DELETE CASCADE,
    casting_id    UUID NOT NULL REFERENCES casting(id) ON DELETE CASCADE,
    call_time     TIME,
    status_code   TEXT,
    notes         TEXT,
    UNIQUE (call_sheet_id, casting_id)
);

CREATE INDEX IF NOT EXISTS idx_call_sheet_cast_sheet ON call_sheet_cast(call_sheet_id);

-- ============================================
-- 5. RLS -- owner-only, direct-client backstop only
-- ============================================
ALTER TABLE call_sheets ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_sheet_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_sheet_crew ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_sheet_cast ENABLE ROW LEVEL SECURITY;

CREATE POLICY "owner manages call sheets"
    ON call_sheets FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = call_sheets.production_id
                  AND p.owner_id = auth.uid())
    );

CREATE POLICY "owner manages call sheet locations"
    ON call_sheet_locations FOR ALL USING (
        EXISTS (SELECT 1 FROM call_sheets cs
                JOIN productions p ON p.id = cs.production_id
                WHERE cs.id = call_sheet_locations.call_sheet_id
                  AND p.owner_id = auth.uid())
    );

CREATE POLICY "owner manages call sheet crew"
    ON call_sheet_crew FOR ALL USING (
        EXISTS (SELECT 1 FROM call_sheets cs
                JOIN productions p ON p.id = cs.production_id
                WHERE cs.id = call_sheet_crew.call_sheet_id
                  AND p.owner_id = auth.uid())
    );

CREATE POLICY "owner manages call sheet cast"
    ON call_sheet_cast FOR ALL USING (
        EXISTS (SELECT 1 FROM call_sheets cs
                JOIN productions p ON p.id = cs.production_id
                WHERE cs.id = call_sheet_cast.call_sheet_id
                  AND p.owner_id = auth.uid())
    );
