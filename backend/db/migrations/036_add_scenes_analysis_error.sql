-- Failed-scene detail: friendly message + machine category for the UI.
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS analysis_error text;
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS analysis_error_category text;
