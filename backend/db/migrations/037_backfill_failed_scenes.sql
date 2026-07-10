-- Flip historically-poisoned scenes (masked as complete with the raw error in
-- description) to the real failed state so they surface and become retryable.
UPDATE scenes
SET analysis_status = 'failed',
    analysis_error_category = 'unknown',
    analysis_error = 'Analysis couldn''t complete for this scene. Click Re-analyze to try again.',
    description = ''
WHERE analysis_status = 'complete'
  AND description LIKE 'Analysis failed:%';
