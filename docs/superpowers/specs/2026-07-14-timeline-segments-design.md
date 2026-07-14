# Timeline Segments — Off-Timeline Flashbacks & Montages

**Date:** 2026-07-14
**Status:** Design — pending implementation plan

## Problem

Story days are a **sequential continuity timeline**: `story_day_service.recalculate_story_days`
walks scenes in `scene_order` and increments a counter on `is_new_story_day`, producing
`Day 1 → Day 2 → Day 3 …`. This drives the "total story days" count, the story-day views,
and story-day grouping in scheduling.

Flashbacks and montages don't belong on that continuity timeline, but today they're forced
onto it: a `FLASHBACK` scene still inherits the running day counter and just gets a prefixed
label (`"Flashback — Day 2"`). Consequences:

- They **inflate** `total_story_days` and distort `scenes_per_day`.
- They have **no identity of their own** — two unrelated flashbacks are indistinguishable,
  and the scenes of one flashback aren't grouped together.

## Goal

Let a user manually group scenes into a named **timeline segment** (a flashback, montage,
dream, etc.) that:

1. Has its **own identity** (name, type), independent of the numeric Day-N timeline.
2. Is **excluded from the continuity count** — its scenes get no `story_day` number and
   don't contribute to `total_story_days`.
3. Remains **fully schedulable** — segment scenes still appear as normal shootable strips on
   the board/schedule, labeled with the segment name instead of "Day N".

Non-adjacent scenes may belong to the same segment (e.g. a recurring "Wedding Flashback").

## Non-Goals (v1)

- **No AI auto-detection or auto-naming of segments.** The AI keeps emitting per-scene
  `timeline_code` as it does today; grouping into segments is **fully manual**.
- No separate schedule "block" for segments — they render as ordinary strips (see Q4-A).
- No nesting of segments, no cross-script shared segments.

## Data Model

### New table: `timeline_segments`

| column          | type        | notes                                                        |
|-----------------|-------------|--------------------------------------------------------------|
| `id`            | uuid PK     |                                                              |
| `script_id`     | uuid FK     | → `scripts.id`, `ON DELETE CASCADE`, indexed                 |
| `name`          | text        | user-supplied, e.g. "Training Montage"                       |
| `segment_type`  | text        | one of the existing timeline codes: `FLASHBACK`, `DREAM`, `FANTASY`, `MONTAGE`, `TITLE_CARD` (default `FLASHBACK`) |
| `display_order` | int         | ordering among segments within the script                    |
| `color`         | text        | optional hex for board/label chip; nullable                  |
| `created_at`    | timestamptz | default `now()`                                              |

### `scenes` — new column

| column       | type    | notes                                                            |
|--------------|---------|------------------------------------------------------------------|
| `segment_id` | uuid FK | → `timeline_segments.id`, `ON DELETE SET NULL`, nullable, indexed |

**Invariant:** a scene belongs to the numeric story-day timeline **or** to a segment, never
both. When `segment_id IS NOT NULL`, the scene's `story_day` is `NULL`.

Access is via the service-role key (RLS bypassed), consistent with the rest of the backend;
scoping to the owner is enforced at the route layer like other script-scoped resources.

## Behavior Changes

### 1. Recalc — `story_day_service.recalculate_story_days`

In the sequential pass, a scene with `segment_id IS NOT NULL` is **skipped by the counter**:

- It does **not** increment `current_day`.
- Its `story_day` is set to `NULL`.
- Its `story_day_label` is set to the segment's `name`.
- It is **excluded** from the `total_days` set and from `scenes_per_day`.

The counter simply carries over the previous present-day scene's value, so a segment sitting
between Day 3 and the next present scene doesn't disturb the sequence. Whether the scene
*after* a segment resumes the same day or starts a new one remains the user's call via
`is_new_story_day` on that later scene (unchanged behavior).

`get_story_day_summary` gains a `segment_scene_count` (scenes currently in any segment) and
continues to report `unassigned_count` only for genuinely unassigned present-day scenes.

### 2. Membership transitions (Q5 — defaults)

- **Joining a segment:** clear the scene's `is_new_story_day` flag and `story_day_is_locked`
  (they're meaningless off-timeline), null its `story_day`, then trigger recalc from that
  scene's order onward.
- **Leaving a segment:** null `segment_id` and let normal recalc reassign a numeric day from
  its position. No memory of any prior manual day.

Both transitions reuse the existing "recalc from `start_from_order`" optimization.

### 3. Scheduling / stripboard

Segment scenes render as normal strips. Where a strip currently shows "Day N", a segment
scene shows its segment `name` (and optional `color` chip). They are **not** grouped into a
separate board block — shoot-day grouping and normal scheduling treat them like any other
schedulable scene.

## API Surface (backend — new `segment_routes` blueprint, registered in `app.py`)

Story-day continuity already lives near scheduling, so a small dedicated blueprint keeps the
segment CRUD isolated and testable rather than swelling `schedule_routes`.

- `POST   /scripts/:id/segments` — create `{ name, segment_type, color? }`.
- `PATCH  /segments/:id` — rename / recolor / retype.
- `DELETE /segments/:id` — deletes the segment; member scenes fall back to the timeline via
  `ON DELETE SET NULL` + a recalc.
- `POST   /segments/:id/scenes` — attach `{ scene_ids: [...] }` (triggers join transition +
  recalc).
- `DELETE /segments/:id/scenes/:scene_id` — detach one scene (triggers leave transition +
  recalc).
- `GET    /scripts/:id/segments` — list segments with member scene ids (for the UI).

Every mutation ends by calling `recalculate_story_days(script_id, start_from_order=…)` and
returning the refreshed summary, so the frontend can `notifyStoryDayChange` and all views
resync (existing `StoryDayContext` mechanism — no changes there).

## Frontend

- **Grouping UI** lives in the story-day-oriented views (SceneManager / SceneViewer): select
  one or more scenes → "Group into segment" → name it + pick type. Existing segments appear in
  a picker so scenes can be added to one already created.
- Segment scenes display the segment name in place of "Day N" across SceneList, SceneDetail,
  StripCard, ScheduleSceneCard, and reports (Stripboard, SharedReportView).
- A lightweight **segments panel** (list, rename, delete, reorder via `display_order`) — scope
  minimally for v1; reorder can be a follow-up if it adds risk.
- All backend calls go through `apiService.js` (no new axios instance).

## Testing

- **`story_day_service`**: segment scenes get `story_day = NULL`, don't advance the counter,
  are excluded from `total_days`/`scenes_per_day`; a segment between Day 3 and Day 4 leaves the
  numbering intact; join clears manual flags; leave restores a numeric day. (Extends
  `test_story_day_completion_recalc.py`.)
- **Route tests**: create/rename/delete segment; attach/detach scenes; delete-segment falls
  member scenes back onto the timeline. (Extends `test_schedule_reports.py`.)
- **Frontend**: gate on `npm run build` (repo lint is known-broken).

## Migration

- Additive migration: create `timeline_segments`, add `scenes.segment_id`, add indexes.
  No backfill — existing flashback/montage scenes keep their current numeric days until a user
  chooses to group them. Fully backward compatible.
