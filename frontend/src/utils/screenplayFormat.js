/**
 * Classify raw scene text into typed screenplay blocks for rendering.
 *
 * The source text is AI-extracted and mixes two dialogue conventions:
 *   1. Inline   — "SPHE: Games night Thursday."         (chat-style scenes)
 *   2. Standard — a character name on its own line, with dialogue on the
 *                 following line(s):   SPHE / "It's ok, I know..."
 * Casing is unreliable (sluglines and cues arrive as "ExT.", "JessIE"), so the
 * caller-supplied `characterNames` (the scene's cast, from scenes.speakers /
 * scenes.characters) is the primary signal for detecting standalone cues — a
 * line is a cue when it matches a known cast name, which distinguishes real
 * cues ("JessIE") from mini-slugs ("THE DANCE OFF") and shouts ("HUDDLE!").
 *
 * The source text is never altered — only chunked, tagged, and (for headings /
 * cues / transitions) upper-cased for display. Anything unrecognised falls
 * through to `action`, so the failure mode is degraded styling, never data loss.
 *
 * @param {string} sceneText
 * @param {string[]} [characterNames] scene cast names used as the cue dictionary
 * @returns {Array<{ type: 'scene-heading'|'action'|'character'|'dialogue'|'parenthetical'|'transition'|'blank', text: string }>}
 */
export function parseScreenplayBlocks(sceneText, characterNames = []) {
    if (!sceneText) return [];

    const SCENE_HEADING = /^(INT|EXT|EST|INT\.?\/EXT|I\/E)[.\s]/i;
    // "NAME: dialogue" — token before the first colon is short and followed by
    // non-empty dialogue text (validated as a cue name below).
    const INLINE_CUE = /^(.{1,25}?):\s*(\S.*)$/;
    // A whole line that is only a parenthetical wryly, e.g. "(into the mic)".
    const PARENTHETICAL = /^\(.*\)$/;

    // Cue dictionary: normalise cast names to bare upper-case for exact matching.
    const castSet = new Set(
        characterNames.map(normalizeCueName).filter(Boolean)
    );

    // A line is a standalone character cue when, once any trailing extension
    // like "(O.S.)" / "(V.O.)" / "(CONT'D)" is stripped, its bare upper-case
    // form matches a cast name. With no dictionary, fall back to a heuristic:
    // no lowercase, short, no terminal punctuation.
    const isCue = (line) => {
        const bare = normalizeCueName(line);
        if (!bare) return false;
        if (castSet.size > 0) return castSet.has(bare);
        return !/[a-z]/.test(line) && bare.split(' ').length <= 5 && !/[.!?]$/.test(line.trim());
    };

    const blocks = [];
    const lines = sceneText.split('\n');

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        if (!line) { blocks.push({ type: 'blank', text: '' }); continue; }

        if (SCENE_HEADING.test(line)) {
            blocks.push({ type: 'scene-heading', text: line.toUpperCase() });
            continue;
        }

        // Transitions before cues so "CUT TO:" isn't mistaken for a cue.
        if (isTransition(line)) {
            blocks.push({ type: 'transition', text: line.toUpperCase() });
            continue;
        }

        // Inline "NAME: dialogue" — only when the name validates as a cue.
        const inline = line.match(INLINE_CUE);
        if (inline && isCue(inline[1])) {
            blocks.push({ type: 'character', text: normalizeCueName(inline[1]) });
            blocks.push({ type: 'dialogue', text: inline[2] });
            continue;
        }

        // Standalone cue: emit the cue, then absorb any wrylies plus the next
        // dialogue line, then return to action flow.
        if (isCue(line)) {
            blocks.push({ type: 'character', text: displayCue(line) });
            let j = i + 1;
            while (j < lines.length) {
                const next = lines[j].trim();
                if (!next) break;                          // blank ends the speech
                if (PARENTHETICAL.test(next)) {
                    blocks.push({ type: 'parenthetical', text: next });
                    j++;
                    continue;                              // wrylies precede dialogue
                }
                if (isCue(next) || SCENE_HEADING.test(next) || isTransition(next)) break;
                blocks.push({ type: 'dialogue', text: next });
                j++;
                break;                                     // one dialogue line per turn
            }
            i = j - 1;
            continue;
        }

        blocks.push({ type: 'action', text: line });
    }

    return blocks;
}

// Strip a trailing cue extension like " (O.S.)" / " (V.O.)" / " (CONT'D)" and
// upper-case, giving the bare name used for dictionary matching.
function normalizeCueName(name) {
    return String(name)
        .replace(/\s*\([^)]*\)\s*$/, '')
        .trim()
        .toUpperCase();
}

// Display form of a standalone cue: upper-cased, extension preserved.
function displayCue(line) {
    return line.trim().toUpperCase();
}

// Case-insensitive transition test: a short line ending in TO:/IN:/OUT that
// names a transition verb (CUT, FADE, DISSOLVE, ...). The ending anchor keeps
// prose like "SHE FADES INTO THE CROWD" from matching.
function isTransition(line) {
    const up = line.trim().toUpperCase();
    if (up.length > 30) return false;
    return /\b(CUT|FADE|DISSOLVE|SMASH|MATCH|WIPE|IRIS)\b.*\b(TO|IN|OUT)\b[:.]?$/.test(up);
}
