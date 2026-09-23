-- 056: production membership grants script access.
-- Spec: docs/superpowers/specs/2026-09-23-production-script-access-design.md
-- Manual apply (run_migration.py is dead).

ALTER TABLE production_members
  ADD COLUMN IF NOT EXISTS script_access text NOT NULL DEFAULT 'none'
  CHECK (script_access IN ('none','view','edit'));

ALTER TABLE production_invites
  ADD COLUMN IF NOT EXISTS script_access text NOT NULL DEFAULT 'none'
  CHECK (script_access IN ('none','view','edit'));

-- Backfill from role presets (admin/coordinator → edit, viewer → view).
UPDATE production_members SET script_access = 'edit'
  WHERE role IN ('admin','coordinator');
UPDATE production_members SET script_access = 'view'
  WHERE role = 'viewer';
UPDATE production_invites SET script_access = 'edit'
  WHERE role IN ('admin','coordinator') AND status = 'pending';
UPDATE production_invites SET script_access = 'view'
  WHERE role = 'viewer' AND status = 'pending';
