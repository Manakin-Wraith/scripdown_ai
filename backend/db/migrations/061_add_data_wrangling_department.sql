-- DIT / data wranglers sit under their own department (role stays free text).
INSERT INTO departments (code, name, color, icon, sort_order)
VALUES ('data_wrangling', 'Data Wrangling', '#2DD4BF', 'sparkles', 21)
ON CONFLICT (code) DO NOTHING;
