-- Add missing film-crew departments and fold Producer into Production.
-- Icons reuse names the UI already maps (briefcase/palette/users/user/sparkles).
INSERT INTO departments (code, name, color, icon, sort_order) VALUES
    ('grip_electric',     'Grip & Electric',   '#EAB308', 'sparkles',  13),
    ('art',               'Art Department',    '#D946EF', 'palette',   14),
    ('script_supervisor', 'Script Supervisor', '#0EA5E9', 'pen-tool',  15),
    ('stunts',            'Stunts',            '#DC2626', 'user',      16),
    ('safety',            'Safety & Medic',    '#16A34A', 'briefcase', 17),
    ('transport',         'Transport',         '#78716C', 'briefcase', 18),
    ('catering',          'Catering',          '#F43F5E', 'users',     19),
    ('post_production',   'Post Production',   '#06B6D4', 'sparkles',  20)
ON CONFLICT (code) DO NOTHING;

-- Producer is a role within Production, not its own department. Re-point any
-- references, then drop it (verified unused at the time of writing).
UPDATE production_crew SET department_code = 'production' WHERE department_code = 'producer';
UPDATE script_members  SET department_code = 'production' WHERE department_code = 'producer';
UPDATE script_invites  SET department_code = 'production' WHERE department_code = 'producer';
DELETE FROM departments WHERE code = 'producer';
