// Build a lookup from scene id → { dayNumber } for one schedule's shooting days.
// Pure and dependency-free so it can be verified without a test framework.
export function buildScheduledMap(days) {
  const map = new Map();
  (days || []).forEach((day) => {
    (day?.scenes || []).forEach((ds) => {
      if (ds && ds.scene_id != null) {
        map.set(ds.scene_id, { dayNumber: day.day_number });
      }
    });
  });
  return map;
}

// Group full scene objects into shoot-day blocks for one schedule.
// `days` is getShootingDays().days; `scenesById` is Map<sceneId, fullScene>.
// Returns day blocks in input order (scenes resolved + schedule-order-preserved,
// unresolved ids skipped) followed by a single trailing unscheduled bin of every
// scene not assigned to any day — emitted only when non-empty. Pure, no React.
export function buildShootDayBlocks(days, scenesById) {
  const blocks = [];
  const scheduledIds = new Set();
  (days || []).forEach((day) => {
    const scenes = [];
    (day?.scenes || []).forEach((ds) => {
      const sid = ds && ds.scene_id;
      if (sid == null) return;
      const full = scenesById.get(sid);
      if (!full) return; // stale assignment — scene no longer exists
      scenes.push(full);
      scheduledIds.add(sid);
    });
    if (scenes.length > 0) {
      blocks.push({ dayNumber: day.day_number, scenes });
    }
  });
  const unscheduled = [];
  scenesById.forEach((scene, sid) => {
    if (!scheduledIds.has(sid)) unscheduled.push(scene);
  });
  if (unscheduled.length > 0) {
    blocks.push({ unscheduled: true, scenes: unscheduled });
  }
  return blocks;
}
