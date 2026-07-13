-- Migration 039: nesting support.
-- A nullable set_name on location_aliases turns a parent remap into a NEST:
-- when present, re-analysis rewrites the base to "{canonical_place} - {set_name}"
-- and keeps location_canonical = canonical_place (the parent base).
-- Existing rows keep set_name NULL and behave exactly as before.

ALTER TABLE location_aliases ADD COLUMN IF NOT EXISTS set_name TEXT;
