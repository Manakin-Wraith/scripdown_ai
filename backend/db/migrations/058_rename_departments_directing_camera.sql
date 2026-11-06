-- Display-name fix: these are departments, not single roles. Codes unchanged
-- (script_members, department_notes etc. reference departments by code).
UPDATE departments SET name = 'Directing' WHERE code = 'director';
UPDATE departments SET name = 'Camera'    WHERE code = 'dop';
