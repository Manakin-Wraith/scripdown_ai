-- Migration: Add script_analysis table for caching AI analysis results

CREATE TABLE IF NOT EXISTS script_analysis (
    analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER NOT NULL,
    analysis_type TEXT NOT NULL, -- 'characters' or 'locations'
    analysis_data TEXT NOT NULL, -- JSON data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (script_id) REFERENCES scripts(script_id) ON DELETE CASCADE,
    UNIQUE(script_id, analysis_type)
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_script_analysis_lookup 
ON script_analysis(script_id, analysis_type);
