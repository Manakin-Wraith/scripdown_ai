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
