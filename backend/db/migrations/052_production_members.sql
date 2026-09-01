-- Migration 052: production_members + production_invites (build-sequence step 2b)
--
-- Additive permission layer for the production axis. Governs production-level
-- surfaces only (crew now; locations / schedule / call sheets / DPR later,
-- each adding its own capability column here). Does NOT touch script_members
-- or any script-scoped access.
--
-- Apply manually in the Supabase SQL editor (run_migration.py is dead).
--
-- DELETE-USER ORDERING (load-bearing, see 013_delete_user_safely.sql):
--   * A deleted OWNER: productions.owner_id ON DELETE CASCADE removes their
--     productions, which cascades production_members / production_invites /
--     production_crew via production_id ON DELETE CASCADE.
--   * A deleted MEMBER of someone else's production: production_members.user_id
--     ON DELETE CASCADE clears their membership rows; invited_by ON DELETE SET
--     NULL detaches invites they sent. No FK error in either direction.

CREATE TABLE IF NOT EXISTS production_members (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    production_id         uuid NOT NULL REFERENCES productions(id) ON DELETE CASCADE,
    user_id              uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role                 text NOT NULL CHECK (role IN ('admin','coordinator','viewer')),
    can_view_sensitive   boolean NOT NULL DEFAULT false,
    can_edit_crew        boolean NOT NULL DEFAULT false,
    can_manage_members   boolean NOT NULL DEFAULT false,
    can_edit_production  boolean NOT NULL DEFAULT false,
    invited_by           uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now(),
    UNIQUE (production_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_production_members_production ON production_members(production_id);
CREATE INDEX IF NOT EXISTS idx_production_members_user ON production_members(user_id);

CREATE TABLE IF NOT EXISTS production_invites (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    production_id         uuid NOT NULL REFERENCES productions(id) ON DELETE CASCADE,
    email                text NOT NULL,
    role                 text NOT NULL CHECK (role IN ('admin','coordinator','viewer')),
    can_view_sensitive   boolean NOT NULL DEFAULT false,
    can_edit_crew        boolean NOT NULL DEFAULT false,
    can_manage_members   boolean NOT NULL DEFAULT false,
    can_edit_production  boolean NOT NULL DEFAULT false,
    token                text NOT NULL UNIQUE,
    status               text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','accepted','revoked')),
    invited_by           uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    expires_at           timestamptz NOT NULL,
    created_at           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_production_invites_token ON production_invites(token);
CREATE INDEX IF NOT EXISTS idx_production_invites_production_status ON production_invites(production_id, status);
CREATE INDEX IF NOT EXISTS idx_production_invites_email ON production_invites(lower(email));
CREATE UNIQUE INDEX IF NOT EXISTS uq_production_invites_pending
    ON production_invites(production_id, lower(email)) WHERE status = 'pending';

-- updated_at trigger (reuses update_shooting_updated_at() from migration 030)
DROP TRIGGER IF EXISTS trg_production_members_updated_at ON production_members;
CREATE TRIGGER trg_production_members_updated_at
    BEFORE UPDATE ON production_members
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

-- RLS: direct-client backstop only. Real enforcement is Python + service key.
ALTER TABLE production_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE production_invites ENABLE ROW LEVEL SECURITY;

CREATE POLICY "owner manages production members"
    ON production_members FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = production_members.production_id
                  AND p.owner_id = auth.uid())
    );

CREATE POLICY "member reads own membership row"
    ON production_members FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "owner manages production invites"
    ON production_invites FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = production_invites.production_id
                  AND p.owner_id = auth.uid())
    );
