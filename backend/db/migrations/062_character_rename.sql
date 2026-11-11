-- Migration 062: Character rename
-- A rename reuses character_aliases (old name -> new canonical name). This column
-- marks rows created by a rename and records the name as it appears in the script,
-- so the UI can show "originally <name>" even after chained renames.
-- NULL = row came from a merge, not a rename.
-- Apply manually against the Supabase project (run_migration.py is dead).

ALTER TABLE character_aliases
    ADD COLUMN IF NOT EXISTS original_name TEXT;
