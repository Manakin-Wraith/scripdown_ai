/** First letters of the first two words, uppercased — for avatar badges. */
export const initials = (name) =>
    (name || '?').trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join('').toUpperCase();
