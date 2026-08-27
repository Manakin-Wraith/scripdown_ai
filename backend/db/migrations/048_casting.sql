-- Migration 048: Cast & Casting (v1)
-- Per-script casting record (one row per character) + blackout date ranges.
-- See docs/superpowers/specs/2026-08-27-cast-casting-v1-design.md §4.
-- Apply manually against the Supabase project (run_migration.py is dead).

-- ============================================
-- 1. casting — one row per character per script
-- ============================================
CREATE TABLE IF NOT EXISTS casting (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id      UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    character_name TEXT NOT NULL,
    actor_name     TEXT,
    status         TEXT NOT NULL DEFAULT 'wishlist'
                     CHECK (status IN ('wishlist','offer','booked','declined','released')),
    contact_phone  TEXT,
    contact_email  TEXT,
    agent_contact  TEXT,
    headshot_path  TEXT,
    notes          TEXT,
    created_by     UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (script_id, character_name)
);

CREATE INDEX IF NOT EXISTS idx_casting_script ON casting(script_id);

-- ============================================
-- 2. casting_unavailability — 0..n blackout ranges per casting row
-- ============================================
CREATE TABLE IF NOT EXISTS casting_unavailability (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    casting_id UUID NOT NULL REFERENCES casting(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date   DATE NOT NULL,
    reason     TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_casting_unavail_casting
    ON casting_unavailability(casting_id);

-- ============================================
-- 3. updated_at trigger (reuses the fn from migration 030)
-- ============================================
CREATE TRIGGER trg_casting_updated
    BEFORE UPDATE ON casting
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

-- ============================================
-- 4. RLS
-- ============================================
ALTER TABLE casting ENABLE ROW LEVEL SECURITY;
ALTER TABLE casting_unavailability ENABLE ROW LEVEL SECURITY;

CREATE POLICY "casting select for script members"
    ON casting FOR SELECT
    USING (
        script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
        OR script_id IN (SELECT script_id FROM script_members WHERE user_id = auth.uid())
    );

CREATE POLICY "casting write for owner or admin"
    ON casting FOR ALL
    USING (
        script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
        OR script_id IN (
            SELECT script_id FROM script_members
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "casting_unavailability select for script members"
    ON casting_unavailability FOR SELECT
    USING (
        casting_id IN (
            SELECT c.id FROM casting c
            WHERE c.script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
               OR c.script_id IN (SELECT script_id FROM script_members WHERE user_id = auth.uid())
        )
    );

CREATE POLICY "casting_unavailability write for owner or admin"
    ON casting_unavailability FOR ALL
    USING (
        casting_id IN (
            SELECT c.id FROM casting c
            WHERE c.script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
               OR c.script_id IN (
                   SELECT script_id FROM script_members
                   WHERE user_id = auth.uid() AND role = 'admin'
               )
        )
    );
