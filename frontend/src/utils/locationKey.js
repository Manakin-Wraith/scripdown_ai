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
const LEADING_ARTICLE = /^(THE|A|AN)\s+/;

// Mirror of backend normalize_place: uppercase, collapse whitespace,
// strip a leading article, strip surrounding punctuation.
const normalizePlace = (s) =>
    (s || '')
        .toUpperCase()
        .replace(/\s+/g, ' ')
        .trim()
        .replace(LEADING_ARTICLE, '')
        .replace(/^[ .,\-–—:;]+|[ .,\-–—:;]+$/g, '');

// Sub-location label (everything under the base place), parsed from the setting
// so it stays correct after renames. Mirrors backend derive_sub_place.
export const subLocationLabel = (scene) => {
    if (!scene || !scene.setting) return '';
    const stripped = scene.setting.toUpperCase().replace(INT_EXT_PREFIX, '');
    // Sub-location separators: a comma ("TK'S HOUSE, KITCHEN") or a whitespace-
    // surrounded dash (slugline " - "). Spaces around the dash keep hyphenated
    // names intact ("C-MAX PRISON"). Mirrors backend _SEP_SPLIT.
    const parts = stripped
        .split(/\s*,\s*|\s+[-–—]\s+/)
        .map((p) => p.trim())
        .filter(Boolean);
    const kept = parts.filter(
        (p) => !TIME_WORDS.has(p) && !INT_EXT_TOKENS.has(normalizePlace(p))
    );
    return normalizePlace(kept.slice(1).join(' - '));
};
