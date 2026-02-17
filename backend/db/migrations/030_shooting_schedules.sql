-- Migration 030: Shooting Schedules
-- Allows users to create multiple shooting schedules per script,
-- organize scenes into shooting days, and reorder within days.

-- ============================================
-- 1. shooting_schedules — Named schedule per script
-- ============================================
CREATE TABLE IF NOT EXISTS shooting_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    name TEXT NOT NULL DEFAULT 'Schedule 1',
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'archived')),
    start_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_shooting_schedules_script ON shooting_schedules(script_id);
CREATE INDEX idx_shooting_schedules_user ON shooting_schedules(created_by);

-- ============================================
-- 2. shooting_days — A day within a schedule
-- ============================================
CREATE TABLE IF NOT EXISTS shooting_days (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID NOT NULL REFERENCES shooting_schedules(id) ON DELETE CASCADE,
    day_number INT NOT NULL DEFAULT 1,
    shoot_date DATE,
    notes TEXT,
    color_label TEXT DEFAULT 'default',
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'confirmed', 'wrapped')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (schedule_id, day_number)
);

CREATE INDEX idx_shooting_days_schedule ON shooting_days(schedule_id);

-- ============================================
-- 3. shooting_day_scenes — Scenes assigned to a day
-- ============================================
CREATE TABLE IF NOT EXISTS shooting_day_scenes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shooting_day_id UUID NOT NULL REFERENCES shooting_days(id) ON DELETE CASCADE,
    scene_id UUID NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (shooting_day_id, scene_id)
);

CREATE INDEX idx_shooting_day_scenes_day ON shooting_day_scenes(shooting_day_id);
CREATE INDEX idx_shooting_day_scenes_scene ON shooting_day_scenes(scene_id);

-- ============================================
-- 4. RLS Policies
-- ============================================
ALTER TABLE shooting_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE shooting_days ENABLE ROW LEVEL SECURITY;
ALTER TABLE shooting_day_scenes ENABLE ROW LEVEL SECURITY;

-- Schedules: owner of the script can CRUD
CREATE POLICY "Users can view schedules for their scripts"
    ON shooting_schedules FOR SELECT
    USING (
        script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can create schedules for their scripts"
    ON shooting_schedules FOR INSERT
    WITH CHECK (
        script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can update their schedules"
    ON shooting_schedules FOR UPDATE
    USING (
        script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can delete their schedules"
    ON shooting_schedules FOR DELETE
    USING (
        script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
    );

-- Shooting days: accessible if schedule is accessible
CREATE POLICY "Users can view shooting days"
    ON shooting_days FOR SELECT
    USING (
        schedule_id IN (
            SELECT id FROM shooting_schedules 
            WHERE script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
        )
    );

CREATE POLICY "Users can manage shooting days"
    ON shooting_days FOR ALL
    USING (
        schedule_id IN (
            SELECT id FROM shooting_schedules 
            WHERE script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
        )
    );

-- Day scenes: accessible if day is accessible
CREATE POLICY "Users can view day scenes"
    ON shooting_day_scenes FOR SELECT
    USING (
        shooting_day_id IN (
            SELECT sd.id FROM shooting_days sd
            JOIN shooting_schedules ss ON sd.schedule_id = ss.id
            WHERE ss.script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
        )
    );

CREATE POLICY "Users can manage day scenes"
    ON shooting_day_scenes FOR ALL
    USING (
        shooting_day_id IN (
            SELECT sd.id FROM shooting_days sd
            JOIN shooting_schedules ss ON sd.schedule_id = ss.id
            WHERE ss.script_id IN (SELECT id FROM scripts WHERE user_id = auth.uid())
        )
    );

-- ============================================
-- 5. Updated_at trigger
-- ============================================
CREATE OR REPLACE FUNCTION update_shooting_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_shooting_schedules_updated
    BEFORE UPDATE ON shooting_schedules
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

CREATE TRIGGER trg_shooting_days_updated
    BEFORE UPDATE ON shooting_days
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();
