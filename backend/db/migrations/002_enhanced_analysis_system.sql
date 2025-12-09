-- Migration: Enhanced Analysis System for Full Script Support
-- Date: 2024-12-02

-- ============================================
-- 1. Analysis Jobs Queue Table
-- ============================================
CREATE TABLE IF NOT EXISTS analysis_jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER NOT NULL,
    job_type TEXT NOT NULL,           -- 'overview', 'story_arc', 'characters', 'character_detail', 'locations'
    target_id TEXT,                   -- character name or location for specific analyses (NULL for global)
    priority INTEGER DEFAULT 5,       -- 1=highest, 10=lowest
    status TEXT DEFAULT 'queued',     -- 'queued', 'processing', 'completed', 'failed', 'cancelled'
    progress INTEGER DEFAULT 0,       -- 0-100
    result_summary TEXT,              -- Brief summary of result
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (script_id) REFERENCES scripts(script_id) ON DELETE CASCADE
);

-- Index for queue processing (get next job)
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_queue 
ON analysis_jobs(status, priority, created_at);

-- Index for script-specific lookups
CREATE INDEX IF NOT EXISTS idx_analysis_jobs_script 
ON analysis_jobs(script_id, job_type, status);

-- ============================================
-- 2. Add Analysis Status to Scripts Table
-- ============================================
-- Note: SQLite doesn't support ADD COLUMN IF NOT EXISTS, so we use a workaround

-- Check if column exists and add if not (handled in Python migration runner)
ALTER TABLE scripts ADD COLUMN analysis_status TEXT DEFAULT 'pending';
-- Values: 'pending', 'queued', 'in_progress', 'partial', 'complete', 'failed'

ALTER TABLE scripts ADD COLUMN analysis_progress INTEGER DEFAULT 0;
-- 0-100 overall progress

ALTER TABLE scripts ADD COLUMN analysis_started_at TIMESTAMP;
ALTER TABLE scripts ADD COLUMN analysis_completed_at TIMESTAMP;

-- ============================================
-- 3. Character Analysis Cache Table
-- ============================================
CREATE TABLE IF NOT EXISTS character_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER NOT NULL,
    character_name TEXT NOT NULL,
    role_type TEXT,                   -- 'Lead', 'Supporting', 'Minor'
    description TEXT,
    traits TEXT,                      -- JSON array
    backstory TEXT,
    motivation TEXT,
    arc_summary TEXT,
    scene_breakdown TEXT,             -- JSON object: {scene_num: {emotion, intensity, ...}}
    relationships TEXT,               -- JSON array
    scenes_analyzed TEXT,             -- JSON array of scene numbers analyzed
    is_complete INTEGER DEFAULT 0,    -- 0 or 1
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(script_id, character_name),
    FOREIGN KEY (script_id) REFERENCES scripts(script_id) ON DELETE CASCADE
);

-- Index for character lookups
CREATE INDEX IF NOT EXISTS idx_character_analysis_lookup 
ON character_analysis(script_id, character_name);

-- ============================================
-- 4. Location Analysis Cache Table
-- ============================================
CREATE TABLE IF NOT EXISTS location_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER NOT NULL,
    location_name TEXT NOT NULL,
    location_type TEXT,               -- 'INT', 'EXT', 'INT/EXT'
    time_of_day TEXT,                 -- 'DAY', 'NIGHT', 'VARIOUS'
    mood TEXT,
    description TEXT,
    scene_count INTEGER DEFAULT 0,
    scenes TEXT,                      -- JSON array of scene numbers
    production_notes TEXT,
    is_complete INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(script_id, location_name),
    FOREIGN KEY (script_id) REFERENCES scripts(script_id) ON DELETE CASCADE
);

-- Index for location lookups
CREATE INDEX IF NOT EXISTS idx_location_analysis_lookup 
ON location_analysis(script_id, location_name);

-- ============================================
-- 5. Story Arc Analysis Cache Table
-- ============================================
CREATE TABLE IF NOT EXISTS story_arc_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER NOT NULL UNIQUE,
    theme TEXT,
    tone TEXT,
    conflict_type TEXT,
    setting_mood TEXT,
    protagonist TEXT,
    antagonist TEXT,
    is_ensemble INTEGER DEFAULT 0,
    narrative_style TEXT,
    act_structure TEXT,               -- JSON: {act1: {...}, act2: {...}, act3: {...}}
    key_plot_points TEXT,             -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (script_id) REFERENCES scripts(script_id) ON DELETE CASCADE
);

-- ============================================
-- 6. Analysis Metrics Table (for monitoring)
-- ============================================
CREATE TABLE IF NOT EXISTS analysis_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER NOT NULL,
    total_scenes INTEGER DEFAULT 0,
    total_characters INTEGER DEFAULT 0,
    total_locations INTEGER DEFAULT 0,
    scenes_analyzed INTEGER DEFAULT 0,
    characters_analyzed INTEGER DEFAULT 0,
    locations_analyzed INTEGER DEFAULT 0,
    api_calls_made INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    total_duration_seconds REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (script_id) REFERENCES scripts(script_id) ON DELETE CASCADE
);
