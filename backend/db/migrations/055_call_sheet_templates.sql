-- Migration 055: Call sheet templates (per-production customization)
-- See docs/superpowers/specs/2026-09-21-call-sheet-customization-design.md
-- Apply manually against the Supabase project (run_migration.py is dead).
-- Everything is additive with defaults.

-- 0. New capability column (mirrors 054's can_edit_call_sheets)
ALTER TABLE production_members
    ADD COLUMN IF NOT EXISTS can_edit_call_sheet_template boolean NOT NULL DEFAULT false;
ALTER TABLE production_invites
    ADD COLUMN IF NOT EXISTS can_edit_call_sheet_template boolean NOT NULL DEFAULT false;

-- Existing admins/coordinators get it, matching the new role presets
-- (presets only apply to members created after this migration).
UPDATE production_members SET can_edit_call_sheet_template = true
    WHERE role IN ('admin', 'coordinator');
UPDATE production_invites SET can_edit_call_sheet_template = true
    WHERE role IN ('admin', 'coordinator') AND status = 'pending';

-- 1. call_sheet_templates -- one per production
CREATE TABLE IF NOT EXISTS call_sheet_templates (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_id UUID NOT NULL UNIQUE REFERENCES productions(id) ON DELETE CASCADE,
    config        JSONB NOT NULL,
    updated_by    UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_call_sheet_templates_updated
    BEFORE UPDATE ON call_sheet_templates
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

ALTER TABLE call_sheet_templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "owner manages call sheet templates"
    ON call_sheet_templates FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = call_sheet_templates.production_id
                  AND p.owner_id = auth.uid())
    );

-- 2. Per-day custom data on call_sheets
ALTER TABLE call_sheets
    ADD COLUMN IF NOT EXISTS general_call    TIME,
    ADD COLUMN IF NOT EXISTS custom_values   JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS dept_overrides  JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS scene_extras    JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS catering        JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS header_values   JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS block_overrides JSONB NOT NULL DEFAULT '{}'::jsonb;

-- 3. Custom column values on roster rows
ALTER TABLE call_sheet_cast
    ADD COLUMN IF NOT EXISTS extra JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE call_sheet_crew
    ADD COLUMN IF NOT EXISTS extra JSONB NOT NULL DEFAULT '{}'::jsonb;
