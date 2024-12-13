-- SQL script for creating database tables

-- Table: scripts
CREATE TABLE scripts (
    script_id SERIAL PRIMARY KEY,
    script_name VARCHAR(255) NOT NULL,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    script_text TEXT, -- Store the parsed script text
    user_id INT  -- Foreign key relating to the user
);

-- Table: scenes
CREATE TABLE scenes (
    scene_id SERIAL PRIMARY KEY,
    script_id INT REFERENCES scripts(script_id),
    scene_number INT NOT NULL,
    setting TEXT,
    description TEXT,
    characters TEXT,
    props TEXT,
    notes TEXT
);

-- Table: director_notes
CREATE TABLE director_notes (
    scene_id INT REFERENCES scenes(scene_id),
    scene_summary TEXT,
    emotional_beats TEXT,
    shot_suggestions TEXT,
    PRIMARY KEY (scene_id)
);

-- Table: producer_notes
CREATE TABLE producer_notes (
    scene_id INT REFERENCES scenes(scene_id),
    budget_estimation JSONB,
    scheduling_assistance JSONB,
    progress_tracking JSONB,
    PRIMARY KEY (scene_id)
);

-- Table: dop_notes
CREATE TABLE dop_notes (
    scene_id INT REFERENCES scenes(scene_id),
    lighting_visual_cues TEXT,
    scene_analytics TEXT,
    equipment_needs TEXT,
    PRIMARY KEY (scene_id)
);

-- Table: production_designer_notes
CREATE TABLE production_designer_notes (
    scene_id INT REFERENCES scenes(scene_id),
    set_dressing_requirements TEXT,
    props_and_wardrobe TEXT,
    collaboration TEXT,
    PRIMARY KEY (scene_id)
);

-- Table: costume_designer_notes
CREATE TABLE costume_designer_notes (
   scene_id INT REFERENCES scenes(scene_id),
    wardrobe_breakdown TEXT,
    continuity_management TEXT,
    PRIMARY KEY (scene_id)
);

-- Table: casting_director_notes
CREATE TABLE casting_director_notes (
   scene_id INT REFERENCES scenes(scene_id),
    character_breakdown JSONB,
    dialogue_analytics JSONB,
     PRIMARY KEY (scene_id)
);


-- Table: location_manager_notes
CREATE TABLE location_manager_notes (
    scene_id INT REFERENCES scenes(scene_id),
    location_breakdown TEXT,
    logistics_planning TEXT,
    PRIMARY KEY (scene_id)
);

-- Table: vfx_supervisor_notes
CREATE TABLE vfx_supervisor_notes (
    scene_id INT REFERENCES scenes(scene_id),
    vfx_requirements TEXT,
    budget_inputs TEXT,
    PRIMARY KEY (scene_id)
);

-- Table: sound_department_notes
CREATE TABLE sound_department_notes (
    scene_id INT REFERENCES scenes(scene_id),
    sound_breakdown TEXT,
    music_cues TEXT,
    PRIMARY KEY (scene_id)
);

-- Table: makeup_and_hair_notes
CREATE TABLE makeup_and_hair_notes (
    scene_id INT REFERENCES scenes(scene_id),
    character_profiles TEXT,
    scene_consistency TEXT,
    PRIMARY KEY (scene_id)
);

-- Table: script_writer_notes
CREATE TABLE script_writer_notes (
    scene_id INT REFERENCES scenes(scene_id),
    writer_notes TEXT,
    version_history JSONB,
    PRIMARY KEY (scene_id)
);

-- Table: actor_notes
CREATE TABLE actor_notes (
    scene_id INT REFERENCES scenes(scene_id),
    character_name TEXT,
    actor_notes TEXT,
    performance_notes TEXT,
    PRIMARY KEY (scene_id)
);


-- Table: users
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(50),
    last_name VARCHAR(50)
);

-- Table: user_roles
CREATE TABLE user_roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE
);

-- Table: users_user_roles (junction table)
CREATE TABLE users_user_roles (
    user_id INT REFERENCES users(user_id),
    role_id INT REFERENCES user_roles(role_id),
     PRIMARY KEY (user_id, role_id)
);

-- Insert default roles
INSERT INTO user_roles (role_name) VALUES
('Director'),
('Producer'),
('DoP'),
('Production_Designer'),
('Costume_Designer'),
('Casting_Director'),
('Location_Manager'),
('VFX_Supervisor'),
('Sound_Department'),
('Makeup_and_Hair'),
('Script_Writer'),
('Actor');
