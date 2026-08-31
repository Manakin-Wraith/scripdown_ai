-- Migration 051: Contacts directory + production crew (build-sequence step 2a)
-- See docs/superpowers/specs/2026-08-31-crew-contacts-design.md
-- Apply manually against the Supabase project (run_migration.py is dead).
--
-- Delete-user ordering note (013_delete_user_safely.sql deletes scripts then
-- profiles): when profiles is deleted, Postgres fires the two FK cascades from
-- profiles (-> productions via 050, -> contacts via this migration) in
-- constraint-creation order. Today 050 runs before 051, so productions (and its
-- ON DELETE CASCADE to production_crew.production_id) is cleared before the
-- profiles -> contacts cascade reaches production_crew.contact_id (ON DELETE
-- RESTRICT). This ordering is NOT guaranteed: a pg_dump / pg_restore
-- alphabetises constraints ("contacts" before "productions"), which inverts the
-- order and produces a 23503 RESTRICT violation on user deletion. The durable
-- fix is the explicit `DELETE FROM production_crew ...` added to
-- 013_delete_user_safely.sql before the profiles row is deleted; do not rely on
-- cascade ordering here.

-- ============================================
-- 1. contacts -- account-level reusable directory
-- ============================================
CREATE TABLE IF NOT EXISTS contacts (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id       UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    kind           TEXT NOT NULL DEFAULT 'person'
                     CHECK (kind IN ('person','company')),
    name           TEXT NOT NULL,
    company_name   TEXT,
    role_tags      TEXT[] NOT NULL DEFAULT '{}'::TEXT[],
    phone          TEXT,
    email          TEXT,
    agent_contact  TEXT,
    standard_rate  NUMERIC,
    rate_unit      TEXT CHECK (rate_unit IS NULL OR rate_unit IN ('day','week','flat')),
    notes          TEXT,
    created_by     UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_contacts_owner ON contacts(owner_id);
CREATE INDEX IF NOT EXISTS idx_contacts_owner_email
    ON contacts(owner_id, lower(email)) WHERE email IS NOT NULL;

CREATE TRIGGER trg_contacts_updated
    BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

-- ============================================
-- 2. production_crew -- assignment (production <-> contact)
-- ============================================
CREATE TABLE IF NOT EXISTS production_crew (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_id   UUID NOT NULL REFERENCES productions(id) ON DELETE CASCADE,
    contact_id      UUID NOT NULL REFERENCES contacts(id) ON DELETE RESTRICT,
    role            TEXT,
    department_code TEXT,   -- soft ref to the departments list; validated in Python
    job_rate        NUMERIC,
    job_rate_unit   TEXT CHECK (job_rate_unit IS NULL OR job_rate_unit IN ('day','week','flat')),
    start_date      DATE,
    end_date        DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_production_crew_production ON production_crew(production_id);
CREATE INDEX IF NOT EXISTS idx_production_crew_contact ON production_crew(contact_id);

CREATE TRIGGER trg_production_crew_updated
    BEFORE UPDATE ON production_crew
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

-- ============================================
-- 3. RLS -- owner-only, direct-client backstop only
-- ============================================
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE production_crew ENABLE ROW LEVEL SECURITY;

CREATE POLICY "owner manages contacts"
    ON contacts FOR ALL USING (owner_id = auth.uid());

CREATE POLICY "owner manages production crew"
    ON production_crew FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = production_crew.production_id
                  AND p.owner_id = auth.uid())
    );
