-- ⚠️ ⚠️ ⚠️ DEPRECATED - DO NOT USE ⚠️ ⚠️ ⚠️
-- This MySQL schema is NOT used in production
-- Production uses Supabase (PostgreSQL)
-- For current schema, see Supabase Dashboard or migrations in backend/db/migrations/
-- This file is kept for historical reference only
-- ⚠️ ⚠️ ⚠️ DEPRECATED - DO NOT USE ⚠️ ⚠️ ⚠️

-- Database Schema for ScripDown AI (LEGACY - MySQL)

CREATE DATABASE IF NOT EXISTS script_breakdown;
USE script_breakdown;

-- Users and Roles
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_roles (
    role_id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users_user_roles (
    user_id INT,
    role_id INT,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES user_roles(role_id) ON DELETE CASCADE
);

-- Scripts
CREATE TABLE IF NOT EXISTS scripts (
    script_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    script_name VARCHAR(255) NOT NULL,
    script_text LONGTEXT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

-- Scenes
CREATE TABLE IF NOT EXISTS scenes (
    scene_id INT AUTO_INCREMENT PRIMARY KEY,
    script_id INT NOT NULL,
    scene_number INT NOT NULL,
    setting VARCHAR(255),
    description TEXT,
    characters JSON, -- Storing list of characters as JSON
    props JSON,      -- Storing list of props as JSON
    notes TEXT,
    FOREIGN KEY (script_id) REFERENCES scripts(script_id) ON DELETE CASCADE
);

-- HOD Notes Tables

-- Director
CREATE TABLE IF NOT EXISTS director_notes (
    note_id INT AUTO_INCREMENT PRIMARY KEY,
    scene_id INT NOT NULL,
    scene_summary TEXT,
    emotional_beats TEXT,
    shot_suggestions TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Producer
CREATE TABLE IF NOT EXISTS producer_notes (
    note_id INT AUTO_INCREMENT PRIMARY KEY,
    scene_id INT NOT NULL,
    budget_estimation JSON,
    scheduling_assistance JSON,
    progress_tracking JSON,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- DoP (Director of Photography)
CREATE TABLE IF NOT EXISTS dop_notes (
    note_id INT AUTO_INCREMENT PRIMARY KEY,
    scene_id INT NOT NULL,
    lighting_visual_cues TEXT,
    scene_analytics TEXT,
    equipment_needs TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Production Designer
CREATE TABLE IF NOT EXISTS production_designer_notes (
    note_id INT AUTO_INCREMENT PRIMARY KEY,
    scene_id INT NOT NULL,
    set_dressing_requirements TEXT,
    props_and_wardrobe TEXT,
    collaboration TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Costume Designer
CREATE TABLE IF NOT EXISTS costume_designer_notes (
    note_id INT AUTO_INCREMENT PRIMARY KEY,
    scene_id INT NOT NULL,
    wardrobe_breakdown TEXT,
    continuity_management TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Casting Director
CREATE TABLE IF NOT EXISTS casting_director_notes (
    note_id INT AUTO_INCREMENT PRIMARY KEY,
    scene_id INT NOT NULL,
    character_breakdown JSON,
    dialogue_analytics JSON,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Location Manager
CREATE TABLE IF NOT EXISTS location_manager_notes (
    note_id INT AUTO_INCREMENT PRIMARY KEY,
    scene_id INT NOT NULL,
    location_breakdown TEXT,
    logistics_planning TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- VFX Supervisor
CREATE TABLE IF NOT EXISTS vfx_supervisor_notes (
    note_id INT AUTO_INCREMENT PRIMARY KEY,
    scene_id INT NOT NULL,
    vfx_requirements TEXT,
    budget_inputs TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Sound Department
CREATE TABLE IF NOT EXISTS sound_department_notes (
    note_id INT AUTO_INCREMENT PRIMARY KEY,
    scene_id INT NOT NULL,
    sound_breakdown TEXT,
    music_cues TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Makeup and Hair
CREATE TABLE IF NOT EXISTS makeup_and_hair_notes (
    note_id INT AUTO_INCREMENT PRIMARY KEY,
    scene_id INT NOT NULL,
    character_profiles TEXT,
    scene_consistency TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Script Writer
CREATE TABLE IF NOT EXISTS script_writer_notes (
    note_id INT AUTO_INCREMENT PRIMARY KEY,
    scene_id INT NOT NULL,
    writer_notes TEXT,
    version_history JSON,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);

-- Actor
CREATE TABLE IF NOT EXISTS actor_notes (
    note_id INT AUTO_INCREMENT PRIMARY KEY,
    scene_id INT NOT NULL,
    character_name VARCHAR(255),
    actor_notes TEXT,
    performance_notes TEXT,
    FOREIGN KEY (scene_id) REFERENCES scenes(scene_id) ON DELETE CASCADE
);
