-- 040_timeline_segments.sql
-- Off-timeline flashback/montage grouping. See
-- docs/superpowers/specs/2026-07-14-timeline-segments-design.md

CREATE TABLE IF NOT EXISTS timeline_segments (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id     uuid NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    name          text NOT NULL,
    segment_type  text NOT NULL DEFAULT 'FLASHBACK',
    display_order integer NOT NULL DEFAULT 0,
    color         text,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_timeline_segments_script
    ON timeline_segments(script_id);

ALTER TABLE scenes
    ADD COLUMN IF NOT EXISTS segment_id uuid
    REFERENCES timeline_segments(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_scenes_segment
    ON scenes(segment_id);
