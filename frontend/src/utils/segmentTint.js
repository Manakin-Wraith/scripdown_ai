// Single source of truth for segment (flashback/montage) colours, keyed by type.
const SEGMENT_TINTS = {
    MONTAGE:    { bg: 'rgba(245, 158, 11, 0.18)', border: 'rgba(245, 158, 11, 0.40)', color: '#fcd34d' },
    FLASHBACK:  { bg: 'rgba(168, 85, 247, 0.18)', border: 'rgba(168, 85, 247, 0.40)', color: '#d8b4fe' },
    DREAM:      { bg: 'rgba(59, 130, 246, 0.18)', border: 'rgba(59, 130, 246, 0.40)', color: '#93c5fd' },
    FANTASY:    { bg: 'rgba(236, 72, 153, 0.18)', border: 'rgba(236, 72, 153, 0.40)', color: '#f9a8d4' },
    TITLE_CARD: { bg: 'rgba(148, 163, 184, 0.18)', border: 'rgba(148, 163, 184, 0.40)', color: '#cbd5e1' },
};

const tintFor = (type) => SEGMENT_TINTS[(type || 'MONTAGE').toUpperCase()] || SEGMENT_TINTS.MONTAGE;

// Inline style for a segment chip (translucent bg + border + bright text).
export const segmentTint = (type) => {
    const t = tintFor(type);
    return { background: t.bg, border: `1px solid ${t.border}`, color: t.color };
};

// Solid bright colour for a swatch/dot.
export const segmentDotColor = (type) => tintFor(type).color;

export const SEGMENT_TYPES = [
    { code: 'MONTAGE', label: 'Montage' },
    { code: 'FLASHBACK', label: 'Flashback' },
    { code: 'DREAM', label: 'Dream' },
    { code: 'FANTASY', label: 'Fantasy' },
    { code: 'TITLE_CARD', label: 'Title Card' },
];
