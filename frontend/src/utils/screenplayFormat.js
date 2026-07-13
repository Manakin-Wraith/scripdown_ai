/**
 * Classify raw scene text into typed screenplay blocks for rendering.
 *
 * The source text is a prose/hybrid format (slugline -> action prose ->
 * "NAME: dialogue" -> transition), not standard Hollywood layout. This turns it
 * into blocks the drawer styles as a proper screenplay page. The source text is
 * never altered — only chunked and tagged; anything unrecognised falls through
 * to `action`, so the failure mode is degraded styling, never data loss.
 *
 * @param {string} sceneText
 * @returns {Array<{ type: 'scene-heading'|'action'|'character'|'dialogue'|'transition'|'blank', text: string }>}
 */
export function parseScreenplayBlocks(sceneText) {
    if (!sceneText) return [];

    const SCENE_HEADING = /^(INT|EXT|EST|INT\.?\/EXT|I\/E)[.\s]/i;
    // All-caps line ending in a transition word (CUT TO:, FADE OUT., FADE IN:).
    const TRANSITION = /^[A-Z0-9 '().-]+(TO|OUT|IN)[:.]?$/;
    // "NAME: dialogue" — token before the first colon has no lowercase letters,
    // is short, and is followed by non-empty dialogue text.
    const CHARACTER_CUE = /^([A-Z0-9][A-Z0-9 '().-]{0,24}):\s*(\S.*)$/;

    const blocks = [];

    for (const rawLine of sceneText.split('\n')) {
        const line = rawLine.trim();

        if (!line) {
            blocks.push({ type: 'blank', text: '' });
            continue;
        }

        if (SCENE_HEADING.test(line)) {
            blocks.push({ type: 'scene-heading', text: line });
            continue;
        }

        // Transition check runs before the character check so "CUT TO:" is not
        // mis-read as a "CUT:"-style character cue.
        if (line.length <= 30 && TRANSITION.test(line)) {
            blocks.push({ type: 'transition', text: line });
            continue;
        }

        const cue = line.match(CHARACTER_CUE);
        if (cue) {
            blocks.push({ type: 'character', text: cue[1].trim() });
            blocks.push({ type: 'dialogue', text: cue[2] });
            continue;
        }

        blocks.push({ type: 'action', text: line });
    }

    return blocks;
}
