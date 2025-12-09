-- Database Schema for ScripDown AI (SQLite)

-- Users and Roles
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    first_name TEXT,
    last_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_roles (
    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users_user_roles (
    user_id INTEGER,
    role_id INTEGER,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES user_roles(role_id) ON DELETE CASCADE
);

-- Scripts
CREATE TABLE IF NOT EXISTS scripts (
    script_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    script_name TEXT NOT NULL,
    script_text TEXT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

-- Scenes
CREATE TABLE IF NOT EXISTS scenes (
    scene_id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER NOT NULL,
    scene_number INTEGER NOT NULL,
    setting TEXT,
    description TEXT,
    characters TEXT, -- JSON array
    props TEXT,      -- JSON array
    special_fx TEXT, -- JSON array for visual/practical effects
    wardrobe TEXT,   -- JSON array for costume notes
    makeup_hair TEXT, -- JSON array for makeup/hair notes
    vehicles TEXT,   -- JSON array for vehicles
    atmosphere TEXT, -- String for lighting/mood description
    notes TEXT,
    FOREIGN KEY (script_id) REFERENCES scripts(script_id) ON DELETE CASCADE
);

-- HOD Notes Tables

-- Director
CREATE TABLE IF NOT EXISTS director_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id INTEGER NOT NULL,
    scene_summary TEXT,
    emotional_beats TEXT,
    shot_suggestions TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Producer
CREATE TABLE IF NOT EXISTS producer_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id INTEGER NOT NULL,
    budget_estimation TEXT,
    scheduling_assistance TEXT,
    progress_tracking TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- DoP (Director of Photography)
CREATE TABLE IF NOT EXISTS dop_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id INTEGER NOT NULL,
    lighting_visual_cues TEXT,
    scene_analytics TEXT,
    equipment_needs TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Production Designer
CREATE TABLE IF NOT EXISTS production_designer_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id INTEGER NOT NULL,
    set_dressing_requirements TEXT,
    props_and_wardrobe TEXT,
    collaboration TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Costume Designer
CREATE TABLE IF NOT EXISTS costume_designer_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id INTEGER NOT NULL,
    wardrobe_breakdown TEXT,
    continuity_management TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Casting Director
CREATE TABLE IF NOT EXISTS casting_director_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id INTEGER NOT NULL,
    character_breakdown TEXT,
    dialogue_analytics TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Location Manager
CREATE TABLE IF NOT EXISTS location_manager_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id INTEGER NOT NULL,
    location_breakdown TEXT,
    logistics_planning TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- VFX Supervisor
CREATE TABLE IF NOT EXISTS vfx_supervisor_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id INTEGER NOT NULL,
    vfx_requirements TEXT,
    budget_inputs TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Sound Department
CREATE TABLE IF NOT EXISTS sound_department_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id INTEGER NOT NULL,
    sound_breakdown TEXT,
    music_cues TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Makeup and Hair
CREATE TABLE IF NOT EXISTS makeup_and_hair_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id INTEGER NOT NULL,
    character_profiles TEXT,
    scene_consistency TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Script Writer
CREATE TABLE IF NOT EXISTS script_writer_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id INTEGER NOT NULL,
    writer_notes TEXT,
    version_history TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Actor
CREATE TABLE IF NOT EXISTS actor_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id INTEGER NOT NULL,
    character_name TEXT,
    actor_notes TEXT,
    performance_notes TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);
