-- Migration: Add remaining metadata columns to scripts table
-- Date: 2025-11-21
-- Description: Adds missing cover page metadata fields to the scripts table
-- Note: writer_name, writer_email, writer_phone, draft_version, draft_date already exist

-- Add remaining metadata columns to scripts table
ALTER TABLE scripts ADD COLUMN copyright_info TEXT;
ALTER TABLE scripts ADD COLUMN wga_registration TEXT;
ALTER TABLE scripts ADD COLUMN additional_credits TEXT;
