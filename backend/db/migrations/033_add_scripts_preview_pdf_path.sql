-- Migration 033: Add scripts.preview_pdf_path for FDX script preview
-- FDX-uploaded scripts store the original file as XML, which the PDF viewer
-- cannot render. The FDX preview feature generates a screenplay-formatted PDF
-- and stores its storage path here; get_pdf_url serves preview_pdf_path when
-- present (else file_path). NULL for PDF-sourced scripts and un-generated FDX.

ALTER TABLE scripts ADD COLUMN IF NOT EXISTS preview_pdf_path TEXT;
