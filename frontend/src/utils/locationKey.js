// Canonical grouping key for a scene's physical location.
// Backend populates location_canonical; fall back to raw setting.
export const locationKey = (scene) =>
    (scene && (scene.location_canonical || scene.setting)) || 'UNKNOWN';

const TIME_WORDS = new Set([
    'DAY', 'NIGHT', 'DUSK', 'DAWN', 'MORNING', 'EVENING',
    'AFTERNOON', 'CONTINUOUS', 'LATER', 'SAME', 'MAGIC HOUR',
]);
const INT_EXT_TOKENS = new Set(['INT', 'EXT', 'INT/EXT', 'I/E']);
const INT_EXT_PREFIX = /^\s*(INT\.?\/EXT\.?|INT\.?|EXT\.?|I\/E\.?)(?=[\s.\-:]|$)\s*[-.:]?\s*/i;

// Sub-location label (everything under the base place), parsed from the setting
// so it stays correct after renames. Mirrors backend derive_sub_place: drop the
// INT/EXT prefix, split on dashes, drop time + INT/EXT tokens, drop the base
// (first kept part), join the rest.
export const subLocationLabel = (scene) => {
    if (!scene || !scene.setting) return '';
    const stripped = scene.setting.toUpperCase().replace(INT_EXT_PREFIX, '');
    const parts = stripped
        .split(/\s*[-–—]\s*/)
        .map((p) => p.trim())
        .filter(Boolean);
    const kept = parts.filter(
        (p) => !TIME_WORDS.has(p) && !INT_EXT_TOKENS.has(p)
    );
    return kept.slice(1).join(' - ');
};
