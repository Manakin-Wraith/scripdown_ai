// Canonical grouping key for a scene's physical location.
// Backend populates location_canonical; fall back to raw setting.
export const locationKey = (scene) =>
    (scene && (scene.location_canonical || scene.setting)) || 'UNKNOWN';

const TIME_WORDS = new Set([
    'DAY', 'NIGHT', 'DUSK', 'DAWN', 'MORNING', 'EVENING',
    'AFTERNOON', 'CONTINUOUS', 'LATER', 'SAME', 'MAGIC HOUR',
]);
const INT_EXT_TOKENS = new Set(['INT', 'EXT', 'INT/EXT', 'I/E']);
const INT_EXT_PREFIX = /^\s*\/?\s*(INT\.?\/EXT\.?|INT\.?|EXT\.?|I\/E\.?)(?=[\s.\-:]|$)\s*[-.:]?\s*/i;
const LEADING_ARTICLE = /^(THE|A|AN)\s+/;
const ABBREV = new Set(['MR', 'MRS', 'MS', 'DR', 'ST', 'MT', 'PROF', 'SGT', 'DET', 'REV', 'LT', 'CAPT', 'GEN']);

// Split a place string into ordered segments on comma / spaced-dash, and on a
// period+space WITHIN each segment unless it follows an abbreviation or single-
// letter initial (protect "MRS. JONES", "ST. JOHN"). A slash is not a separator
// ("GARAGE / BACKROOM" stays one place). Mirrors backend _split_segments.
const splitSegments = (s) => {
    const out = [];
    (s || '').split(/\s*,\s*|\s+[-–—]\s+/).forEach((chunk) => {
        const segs = [];
        chunk.split(/\.\s+/).forEach((rawPart) => {
            const part = rawPart.trim();
            if (!part) return;
            if (segs.length) {
                const words = segs[segs.length - 1].split(/\s+/);
                const last = (words[words.length - 1] || '').replace(/\.+$/, '').toUpperCase();
                if (ABBREV.has(last) || last.length === 1) {
                    segs[segs.length - 1] += '. ' + part;
                    return;
                }
            }
            segs.push(part);
        });
        segs.forEach((p) => { const t = p.trim(); if (t) out.push(t); });
    });
    return out;
};

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
    const parts = splitSegments(stripped);
    const kept = parts.filter(
        (p) => !TIME_WORDS.has(p) && !INT_EXT_TOKENS.has(normalizePlace(p))
    );
    return normalizePlace(kept.slice(1).join(' - '));
};
