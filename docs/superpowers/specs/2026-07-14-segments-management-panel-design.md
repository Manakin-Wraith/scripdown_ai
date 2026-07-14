# Segments Management Panel

**Date:** 2026-07-14
**Status:** Design — pending implementation plan
**Builds on:** [timeline-segments](2026-07-14-timeline-segments-design.md)

## Problem

Timeline segments can be created and assigned per-scene from `SceneDetail`, but there is
no way to manage the segments themselves: rename them, change their colour/type, reorder
them, or delete one. The backend already exposes `updateSegment`/`deleteSegment` and a
`display_order` column; only a UI plus one backend refinement is missing.

Two latent issues to close while here:

1. **Rename staleness.** `update_segment` (PATCH) does not recalculate story days, so a scene's
   `story_day_label` (which holds the segment name) stays stale after a rename until some other
   recalc runs.
2. **Colour invisibility.** Segment chips outside the `SceneDetail` picker (SceneList,
   StripCard, ScheduleSceneCard, reports) are a fixed amber because the scene payload carries
   `segment_id` but not `segment_type`. So changing a segment's type/colour would not show
   anywhere except the picker.

## Goal

A **Segments** panel, opened from the Scenes-tab scene-list header, that lists every segment
in the script and lets the user:

- **Rename** a segment (inline edit).
- **Recolour** a segment by choosing its **type** (Montage/Flashback/Dream/Fantasy/Title Card),
  shown as labelled colour swatches — colour is derived from type, reusing the existing
  timeline palette.
- **Reorder** segments (up/down) via `display_order`.
- **Delete** a segment (with confirmation); member scenes fall back to the numeric timeline.
- **Create** a new segment (name + type) not tied to a specific scene.

Each row also shows how many scenes are in the segment.

## Non-Goals

- No custom hex colour independent of type (colour = type, decided in brainstorming).
- No drag-and-drop reordering (up/down arrows are enough for v1).
- No bulk scene reassignment from this panel (that stays in `SceneDetail`).

## Architecture

A new modal component `SegmentManager`, following the established `LocationManager` pattern
(a self-contained manager opened from a toolbar/header button, using `useToast` for feedback,
`useConfirmDialog` for destructive actions, and an `onChanged` callback to resync the app).

- **File:** `frontend/src/components/scenes/SegmentManager.jsx` (+ `SegmentManager.css`).
- **Props:** `{ scriptId, scenes, onClose, onChanged }`.
  - `scenes` is the already-loaded scene list from `SceneViewer` — used to compute each
    segment's scene count client-side (no new count endpoint).
- **Opened from:** a new "Segments" button in `SceneViewer`'s `.sidebar-header-actions`,
  beside the "All Days" filter and the PDF toggle. The button shows a count of segments.
- **On any successful change:** call `onChanged()` (wired to `SceneViewer.refreshScenes`) and
  `notifyStoryDayChange(scriptId)` so every view (list, board, schedule, reports) resyncs.

### Panel layout (per row)

```
[●type]  Segment name (inline-edit)      3 scenes   [↑][↓]  [🗑]
```

- **Type swatch `[●type]`** — a coloured dot/button; clicking opens a small inline picker of
  the five types as labelled swatches. Selecting one PATCHes `segment_type`.
- **Name** — click to edit inline; Enter saves (PATCH `name`), Escape cancels.
- **Scene count** — derived from `scenes` (`scenes.filter(s => s.segment_id === seg.id).length`).
- **Up/Down** — swap `display_order` with the adjacent segment (PATCH both).
- **Delete** — `useConfirmDialog` → `deleteSegment(id, scriptId)`; member scenes fall back to
  the timeline via the existing `ON DELETE SET NULL` + recalc.

A footer row creates a new segment: a name input + type picker + "Add", calling
`createSegment(scriptId, { name, segment_type })`.

## Backend changes

1. **`update_segment` (PATCH) recalculates on rename.** After a successful update, if the
   request changed `name`, call `recalculate_story_days(segment['script_id'], start_from_order=0)`
   so member scenes' `story_day_label`s refresh. The route already resolves the segment (and thus
   its `script_id`) via `_load_segment_or_error`. Type/colour or order-only changes skip recalc
   (labels are the name, colour is derived client-side).

2. **`get_scenes` payload includes `segment_type`.** The `scenes` table does not store the
   type — it lives on `timeline_segments` — so no column is added. Instead `get_scenes` builds a
   `{segment_id: segment_type}` map from `timeline_segments` for the script (mirroring how the
   same handler already builds `scheduled_map` from `shooting_day_scenes`) and sets each scene's
   `segment_type` in the response from its `segment_id`. Display views can then colour chips by
   type.

3. **Reorder needs no new endpoint** — the frontend PATCHes `display_order` on the swapped pair
   via the existing `updateSegment`.

## Display consistency

With `segment_type` now on each scene, colour the segment chips by type
(`timeline-{segment_type}`), replacing the fixed amber, in:

- `SceneList.jsx` / `SceneList.css` (`.scene-segment-chip`)
- `board/StripCard.jsx` (`.strip-segment-chip`)
- `schedule/ScheduleSceneCard.jsx` (`.ssc-segment`)
- `reports/Stripboard.jsx` (segment row cell)

`SceneDetail`'s picker already colours by type from the loaded segments list; after a recolour,
it refetches segments so the dot updates.

## Data flow

```
Open panel → getSegments(scriptId) (ordered by display_order) + scenes (prop)
Edit (rename/recolour/reorder) → updateSegment(...) → onChanged()+notify → refetch
Delete → confirm → deleteSegment(...) → onChanged()+notify → refetch
Create → createSegment(...) → onChanged()+notify → refetch
```

The panel keeps its own `segments` state (refetched via `getSegments` after each change) so
its ordering/labels stay authoritative; `onChanged` refreshes the surrounding scene data.

## Error handling

Every mutation is wrapped; failures raise a `useToast` error toast in the interface voice
("Couldn't rename the segment. Try again.") and leave the list unchanged. Deletes require
explicit confirmation.

## Testing

- **Backend:** `update_segment` triggers `recalculate_story_days` when `name` changes and
  does **not** when only `segment_type`/`display_order`/`color` change (route test, mocking
  `db` + `recalculate_story_days` like the existing segment route tests). `get_scenes`
  includes `segment_type` for a segment scene (extend an existing scenes-route test or add a
  focused one).
- **Frontend:** gate on `npm run build`.

## Copy

- Button: `Segments`. Empty state: "No segments yet. Group flashback or montage scenes from a
  scene's detail panel, or create one below." Delete confirm: "Delete "<name>"? Its scenes
  return to the story-day timeline." Toasts use plain active-voice verbs matching the action.
