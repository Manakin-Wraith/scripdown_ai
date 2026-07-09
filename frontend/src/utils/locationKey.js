// Canonical grouping key for a scene's physical location.
// Backend populates location_canonical; fall back to raw setting.
export const locationKey = (scene) =>
    (scene && (scene.location_canonical || scene.setting)) || 'UNKNOWN';
