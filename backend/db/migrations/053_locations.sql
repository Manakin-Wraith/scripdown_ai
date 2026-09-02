-- Migration 053: Locations directory + production locations + photos (build-sequence step 3)
-- See docs/superpowers/specs/2026-09-02-locations-directory-design.md
-- Apply manually against the Supabase project (run_migration.py is dead).
--
-- This is the account-level real-world LOCATIONS directory. It is NOT the
-- creative scene-setting -> canonical-place resolver (scenes.location_canonical,
-- services/location_resolver.py) -- that is a separate, untouched system.
--
-- Delete-user note (013_delete_user_safely.sql deletes scripts then profiles):
-- locations.owner_id is ON DELETE CASCADE and has NO inbound RESTRICT FK
-- (production_locations.location_id and location_photos.location_id are both
-- ON DELETE CASCADE). So the profiles -> locations cascade clears everything
-- with no ordering hazard -- unlike production_crew.contact_id (RESTRICT),
-- which needed an explicit DELETE in 013. No 013 code change required here.

-- ============================================
-- 1. locations -- account-level reusable directory
-- ============================================
CREATE TABLE IF NOT EXISTS locations (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id           UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name               TEXT NOT NULL,
    address            TEXT,
    lat                NUMERIC,
    lng                NUMERIC,
    geocode_status     TEXT CHECK (geocode_status IS NULL
                         OR geocode_status IN ('ok','failed','manual')),
    primary_contact_id UUID REFERENCES contacts(id) ON DELETE SET NULL,
    permit_status      TEXT,
    parking_notes      TEXT,
    loadin_notes       TEXT,
    restrictions       TEXT,
    notes              TEXT,
    created_by         UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_locations_owner ON locations(owner_id);
CREATE INDEX IF NOT EXISTS idx_locations_owner_name ON locations(owner_id, lower(name));

CREATE TRIGGER trg_locations_updated
    BEFORE UPDATE ON locations
    FOR EACH ROW EXECUTE FUNCTION update_shooting_updated_at();

-- ============================================
-- 2. production_locations -- link (production <-> location)
-- ============================================
CREATE TABLE IF NOT EXISTS production_locations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    production_id     UUID NOT NULL REFERENCES productions(id) ON DELETE CASCADE,
    location_id       UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    production_notes  TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (production_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_production_locations_production ON production_locations(production_id);
CREATE INDEX IF NOT EXISTS idx_production_locations_location ON production_locations(location_id);

-- ============================================
-- 3. location_photos -- reference images (mirrors casting_photos)
-- ============================================
CREATE TABLE IF NOT EXISTS location_photos (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    location_id   UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    storage_path  TEXT NOT NULL,
    caption       TEXT,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_location_photos_location ON location_photos(location_id);

-- ============================================
-- 4. RLS -- owner-only, direct-client backstop only
-- ============================================
ALTER TABLE locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE production_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE location_photos ENABLE ROW LEVEL SECURITY;

CREATE POLICY "owner manages locations"
    ON locations FOR ALL USING (owner_id = auth.uid());

CREATE POLICY "owner manages production locations"
    ON production_locations FOR ALL USING (
        EXISTS (SELECT 1 FROM productions p
                WHERE p.id = production_locations.production_id
                  AND p.owner_id = auth.uid())
    );

CREATE POLICY "owner manages location photos"
    ON location_photos FOR ALL USING (
        EXISTS (SELECT 1 FROM locations l
                WHERE l.id = location_photos.location_id
                  AND l.owner_id = auth.uid())
    );
