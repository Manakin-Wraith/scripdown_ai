-- Migration 049: Cast tab v2 — tiers, photo gallery, background groups, conflict acknowledge.
-- See docs/superpowers/specs/2026-08-29-cast-tab-v2-design.md §2.
-- Apply manually against the Supabase project (run_migration.py is dead).

-- ============================================
-- 1. casting.tier  (NOT NULL DEFAULT backfills every existing row to 'supporting')
-- ============================================
ALTER TABLE casting
    ADD COLUMN IF NOT EXISTS tier TEXT NOT NULL DEFAULT 'supporting'
        CHECK (tier IN ('lead','supporting','featured','background'));

-- ============================================
-- 2. casting_photos — additional images beyond the primary headshot_path
-- ============================================
CREATE TABLE IF NOT EXISTS casting_photos (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    casting_id UUID NOT NULL REFERENCES casting(id) ON DELETE CASCADE,
    path       TEXT NOT NULL,
    kind       TEXT NOT NULL CHECK (kind IN ('headshot','full_body','other')),
    caption    TEXT,
    sort_order INT  NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_casting_photos_casting ON casting_photos(casting_id);

-- ============================================
-- 3. casting_groups — anonymous background booked by headcount
-- ============================================
CREATE TABLE IF NOT EXISTS casting_groups (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id  UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    label      TEXT NOT NULL,
    headcount  INT  NOT NULL DEFAULT 1 CHECK (headcount > 0),
    status     TEXT NOT NULL DEFAULT 'wishlist'
                 CHECK (status IN ('wishlist','offer','booked','declined','released')),
    day_rate   NUMERIC(10,2),
    notes      TEXT,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_casting_groups_script ON casting_groups(script_id);

CREATE TRIGGER trg_casting_groups_updated
    BEFORE UPDATE ON casting_groups
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();  -- shared fn from migration 030

-- ============================================
-- 4. casting_group_scenes — which scenes a group appears in
-- ============================================
CREATE TABLE IF NOT EXISTS casting_group_scenes (
    id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES casting_groups(id) ON DELETE CASCADE,
    scene_id UUID NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    UNIQUE (group_id, scene_id)
);
CREATE INDEX IF NOT EXISTS idx_casting_group_scenes_group ON casting_group_scenes(group_id);
CREATE INDEX IF NOT EXISTS idx_casting_group_scenes_scene ON casting_group_scenes(scene_id);

-- ============================================
-- 5. shooting_day_scenes — conflict acknowledge
-- ============================================
ALTER TABLE shooting_day_scenes
    ADD COLUMN IF NOT EXISTS conflict_ack        BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS conflict_ack_reason TEXT,
    ADD COLUMN IF NOT EXISTS conflict_ack_at     TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS conflict_ack_by     UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- Clear a stale acknowledgement when the day's shoot_date changes.
CREATE OR REPLACE FUNCTION clear_conflict_ack_on_date_change()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.shoot_date IS DISTINCT FROM OLD.shoot_date THEN
        UPDATE shooting_day_scenes
           SET conflict_ack = false, conflict_ack_reason = NULL,
               conflict_ack_at = NULL, conflict_ack_by = NULL
         WHERE shooting_day_id = NEW.id AND conflict_ack = true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_shooting_days_clear_ack
    AFTER UPDATE ON shooting_days
    FOR EACH ROW EXECUTE FUNCTION clear_conflict_ack_on_date_change();

-- ============================================
-- 6. RLS — mirror migration 048 (casting): member select, owner-or-admin write
-- ============================================
ALTER TABLE casting_photos        ENABLE ROW LEVEL SECURITY;
ALTER TABLE casting_groups        ENABLE ROW LEVEL SECURITY;
ALTER TABLE casting_group_scenes  ENABLE ROW LEVEL SECURITY;

CREATE POLICY "casting_photos select for script members" ON casting_photos FOR SELECT
    USING (casting_id IN (
        SELECT c.id FROM casting c
        WHERE c.script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
           OR c.script_id IN (SELECT script_id FROM script_members WHERE user_id = auth.uid())));
CREATE POLICY "casting_photos write for owner or admin" ON casting_photos FOR ALL
    USING (casting_id IN (
        SELECT c.id FROM casting c
        WHERE c.script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
           OR c.script_id IN (SELECT script_id FROM script_members
                              WHERE user_id = auth.uid() AND role = 'admin')));

CREATE POLICY "casting_groups select for script members" ON casting_groups FOR SELECT
    USING (script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
        OR script_id IN (SELECT script_id FROM script_members WHERE user_id = auth.uid()));
CREATE POLICY "casting_groups write for owner or admin" ON casting_groups FOR ALL
    USING (script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
        OR script_id IN (SELECT script_id FROM script_members
                         WHERE user_id = auth.uid() AND role = 'admin'));

CREATE POLICY "casting_group_scenes select for script members" ON casting_group_scenes FOR SELECT
    USING (group_id IN (
        SELECT g.id FROM casting_groups g
        WHERE g.script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
           OR g.script_id IN (SELECT script_id FROM script_members WHERE user_id = auth.uid())));
CREATE POLICY "casting_group_scenes write for owner or admin" ON casting_group_scenes FOR ALL
    USING (group_id IN (
        SELECT g.id FROM casting_groups g
        WHERE g.script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
           OR g.script_id IN (SELECT script_id FROM script_members
                              WHERE user_id = auth.uid() AND role = 'admin')));
