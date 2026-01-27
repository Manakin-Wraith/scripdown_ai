-- =====================================================
-- ScripDown AI - Platform Analytics Dashboard Query
-- =====================================================
-- This query provides comprehensive analytics about:
-- - Total scripts analyzed
-- - Total pages, scenes, locations, characters
-- - Average analysis time per script
-- - Total analysis time across all scripts
-- =====================================================

WITH script_stats AS (
  -- Get core script metrics
  SELECT 
    COUNT(*) as total_scripts,
    SUM(total_pages) as total_pages,
    AVG(total_pages) as avg_pages_per_script,
    COUNT(CASE WHEN analysis_status = 'completed' THEN 1 END) as completed_scripts,
    COUNT(CASE WHEN analysis_status = 'pending' THEN 1 END) as pending_scripts,
    COUNT(CASE WHEN analysis_status = 'analyzing' THEN 1 END) as analyzing_scripts,
    COUNT(CASE WHEN analysis_status = 'failed' THEN 1 END) as failed_scripts
  FROM scripts
),

scene_stats AS (
  -- Get scene-level metrics
  SELECT 
    COUNT(*) as total_scenes,
    COUNT(DISTINCT script_id) as scripts_with_scenes,
    COUNT(DISTINCT setting) as unique_locations,
    AVG(CASE 
      WHEN script_id IS NOT NULL 
      THEN (SELECT COUNT(*) FROM scenes s2 WHERE s2.script_id = scenes.script_id)
    END) as avg_scenes_per_script
  FROM scenes
  WHERE (is_omitted = false OR is_omitted IS NULL)
),

character_stats AS (
  -- Get character metrics from scenes
  SELECT 
    COUNT(DISTINCT character_name) as total_unique_characters,
    (SELECT AVG(jsonb_array_length(COALESCE(characters, '[]'::jsonb))) 
     FROM scenes 
     WHERE characters IS NOT NULL 
       AND jsonb_array_length(characters) > 0
       AND (is_omitted = false OR is_omitted IS NULL)
    ) as avg_characters_per_scene
  FROM scenes,
  LATERAL jsonb_array_elements_text(characters) as character_name
  WHERE characters IS NOT NULL 
    AND jsonb_array_length(characters) > 0
    AND (is_omitted = false OR is_omitted IS NULL)
),

analysis_timing AS (
  -- Calculate analysis timing metrics
  SELECT 
    COUNT(*) as total_analysis_jobs,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_jobs,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_jobs,
    COUNT(CASE WHEN status = 'running' THEN 1 END) as running_jobs,
    -- Average time per job in seconds
    AVG(
      CASE 
        WHEN status = 'completed' AND started_at IS NOT NULL AND completed_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (completed_at - started_at))
      END
    ) as avg_analysis_time_seconds,
    -- Total time spent analyzing (in seconds)
    SUM(
      CASE 
        WHEN status = 'completed' AND started_at IS NOT NULL AND completed_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (completed_at - started_at))
        ELSE 0
      END
    ) as total_analysis_time_seconds,
    -- Min and Max analysis times
    MIN(
      CASE 
        WHEN status = 'completed' AND started_at IS NOT NULL AND completed_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (completed_at - started_at))
      END
    ) as min_analysis_time_seconds,
    MAX(
      CASE 
        WHEN status = 'completed' AND started_at IS NOT NULL AND completed_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (completed_at - started_at))
      END
    ) as max_analysis_time_seconds
  FROM analysis_jobs
  WHERE job_type IN ('bulk_scene_analysis', 'scene_enhancement', 'scene_extraction')
),

breakdown_stats AS (
  -- Get breakdown element counts from scenes
  SELECT 
    SUM(jsonb_array_length(COALESCE(props, '[]'::jsonb))) as total_props,
    SUM(jsonb_array_length(COALESCE(wardrobe, '[]'::jsonb))) as total_wardrobe_items,
    SUM(jsonb_array_length(COALESCE(makeup_hair, '[]'::jsonb))) as total_makeup_items,
    SUM(jsonb_array_length(COALESCE(special_fx, '[]'::jsonb))) as total_special_fx,
    SUM(jsonb_array_length(COALESCE(vehicles, '[]'::jsonb))) as total_vehicles,
    AVG(jsonb_array_length(COALESCE(props, '[]'::jsonb))) as avg_props_per_scene,
    AVG(jsonb_array_length(COALESCE(wardrobe, '[]'::jsonb))) as avg_wardrobe_per_scene
  FROM scenes
  WHERE (is_omitted = false OR is_omitted IS NULL)
),

user_stats AS (
  -- Get user engagement metrics
  SELECT 
    COUNT(*) as total_users,
    COUNT(CASE WHEN subscription_status = 'trial' THEN 1 END) as trial_users,
    COUNT(CASE WHEN subscription_status = 'active' THEN 1 END) as active_subscribers,
    COUNT(CASE WHEN subscription_status = 'expired' THEN 1 END) as expired_users,
    COUNT(CASE WHEN is_superuser = true THEN 1 END) as superusers
  FROM profiles
)

-- Final aggregated output
SELECT 
  -- SCRIPT METRICS
  '📊 SCRIPT METRICS' as category,
  ss.total_scripts as "Total Scripts Uploaded",
  ss.completed_scripts as "Scripts Analyzed",
  ss.pending_scripts as "Scripts Pending",
  ss.analyzing_scripts as "Scripts Currently Analyzing",
  ss.failed_scripts as "Failed Scripts",
  ss.total_pages as "Total Pages Processed",
  ROUND(ss.avg_pages_per_script::numeric, 2) as "Avg Pages per Script",
  
  -- SCENE METRICS
  scs.total_scenes as "Total Scenes",
  ROUND(scs.avg_scenes_per_script::numeric, 2) as "Avg Scenes per Script",
  scs.unique_locations as "Unique Locations",
  
  -- CHARACTER METRICS
  cs.total_unique_characters as "Total Unique Characters",
  ROUND(cs.avg_characters_per_scene::numeric, 2) as "Avg Characters per Scene",
  
  -- BREAKDOWN METRICS
  bs.total_props as "Total Props",
  bs.total_wardrobe_items as "Total Wardrobe Items",
  bs.total_makeup_items as "Total Makeup Items",
  bs.total_special_fx as "Total Special FX",
  bs.total_vehicles as "Total Vehicles",
  ROUND(bs.avg_props_per_scene::numeric, 2) as "Avg Props per Scene",
  
  -- ANALYSIS TIMING METRICS
  at.total_analysis_jobs as "Total Analysis Jobs",
  at.completed_jobs as "Completed Jobs",
  at.failed_jobs as "Failed Jobs",
  at.running_jobs as "Currently Running Jobs",
  
  -- Time metrics in human-readable format
  CONCAT(
    FLOOR(at.avg_analysis_time_seconds / 60), 'm ',
    ROUND(at.avg_analysis_time_seconds % 60), 's'
  ) as "Avg Analysis Time per Script",
  
  CONCAT(
    FLOOR(at.total_analysis_time_seconds / 3600), 'h ',
    FLOOR((at.total_analysis_time_seconds % 3600) / 60), 'm ',
    ROUND(at.total_analysis_time_seconds % 60), 's'
  ) as "Total Analysis Time (All Scripts)",
  
  CONCAT(
    FLOOR(at.min_analysis_time_seconds / 60), 'm ',
    ROUND(at.min_analysis_time_seconds % 60), 's'
  ) as "Fastest Analysis Time",
  
  CONCAT(
    FLOOR(at.max_analysis_time_seconds / 60), 'm ',
    ROUND(at.max_analysis_time_seconds % 60), 's'
  ) as "Slowest Analysis Time",
  
  -- USER METRICS
  us.total_users as "Total Users",
  us.trial_users as "Trial Users",
  us.active_subscribers as "Active Subscribers",
  us.expired_users as "Expired Users",
  us.superusers as "Superusers"

FROM script_stats ss
CROSS JOIN scene_stats scs
CROSS JOIN character_stats cs
CROSS JOIN analysis_timing at
CROSS JOIN breakdown_stats bs
CROSS JOIN user_stats us;


-- =====================================================
-- ALTERNATIVE: Vertical Layout (Better for Dashboard Display)
-- =====================================================
-- Uncomment this section if you prefer a vertical list format

/*
SELECT 
  metric_name,
  metric_value,
  metric_category
FROM (
  SELECT '📊 Scripts' as metric_category, 'Total Scripts Uploaded' as metric_name, total_scripts::text as metric_value, 1 as sort_order FROM script_stats
  UNION ALL
  SELECT '📊 Scripts', 'Scripts Analyzed', completed_scripts::text, 2 FROM script_stats
  UNION ALL
  SELECT '📊 Scripts', 'Total Pages Processed', total_pages::text, 3 FROM script_stats
  UNION ALL
  SELECT '📊 Scripts', 'Avg Pages per Script', ROUND(avg_pages_per_script::numeric, 2)::text, 4 FROM script_stats
  UNION ALL
  SELECT '🎬 Scenes', 'Total Scenes', total_scenes::text, 10 FROM scene_stats
  UNION ALL
  SELECT '🎬 Scenes', 'Avg Scenes per Script', ROUND(avg_scenes_per_script::numeric, 2)::text, 11 FROM scene_stats
  UNION ALL
  SELECT '🎬 Scenes', 'Unique Locations', unique_locations::text, 12 FROM scene_stats
  UNION ALL
  SELECT '👥 Characters', 'Total Unique Characters', total_unique_characters::text, 20 FROM character_stats
  UNION ALL
  SELECT '👥 Characters', 'Avg Characters per Scene', ROUND(avg_characters_per_scene::numeric, 2)::text, 21 FROM character_stats
  UNION ALL
  SELECT '⏱️ Analysis Time', 'Avg Time per Script', 
    CONCAT(FLOOR(avg_analysis_time_seconds / 60), 'm ', ROUND(avg_analysis_time_seconds % 60), 's'), 30 
  FROM analysis_timing
  UNION ALL
  SELECT '⏱️ Analysis Time', 'Total Time (All Scripts)', 
    CONCAT(FLOOR(total_analysis_time_seconds / 3600), 'h ', FLOOR((total_analysis_time_seconds % 3600) / 60), 'm'), 31 
  FROM analysis_timing
  UNION ALL
  SELECT '👤 Users', 'Total Users', total_users::text, 40 FROM user_stats
  UNION ALL
  SELECT '👤 Users', 'Active Subscribers', active_subscribers::text, 41 FROM user_stats
) metrics
ORDER BY sort_order;
*/
