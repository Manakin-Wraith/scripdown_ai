# Screenplay-Formatted Script Preview — Design

**Date:** 2026-07-13
**Status:** Approved (design), pending implementation plan
**Area:** `frontend/src/components/breakdown/BreakdownDrawer.jsx`

## Problem

The "Script Text" panel in the breakdown drawer renders the raw scene text as a
flat list of lines on a white "page". Item names (cast, props, etc.) are
highlighted, but there is no screenplay structure — sluglines, dialogue, and
transitions all read as undifferentiated prose. The text should look like a
properly formatted screenplay page.

The source text is a prose/hybrid format, not standard Hollywood layout:

```
INT. OPEN PLAN OFFICE - JOBURG - DAY
A sea of laptops and cold brew coffee. KHANYI (28, striking, effortlessly put together) stares at her screen.
It reads: REMINDER: START MY TRAVEL BLOG!!!!
Her phone BUZZES. On screen- WhatsApp. Group name: FFEVA (Friends Forever)
SPHE: Games night Thursday. EVERYBODY IN.
KHANYI: Obviously.😍❤️
CUT TO:
```

## Goal

Render this as **full standard screenplay layout**: bold caps sluglines,
left-aligned action, centered caps character cues with indented dialogue blocks
beneath them, and right-aligned transitions — while preserving the existing
item-name highlighting and never dropping or altering the source text content.

## Non-Goals

- No backend / parser changes. This is purely a frontend rendering change of
  text the drawer already receives (`sceneText`).
- No re-flowing or rewriting of action prose (line breaks stay as the source
  provides them).
- No configuration/toggle for format style — one layout.

## Architecture

Two-step pipeline replacing the current flat `sceneText.split('\n')` rendering
in `BreakdownDrawer.jsx`'s `useMemo`:

1. **Classify** raw text into typed blocks (new pure util).
2. **Render** each block with a type-specific CSS class, applying the existing
   highlight regex to the block's text.

### 1. New util — `frontend/src/utils/screenplayFormat.js`

A pure, side-effect-free function:

```
parseScreenplayBlocks(sceneText: string) => Array<{ type, text }>
```

`type` is one of: `scene-heading`, `action`, `character`, `dialogue`,
`transition`, `blank`.

Classification is line-by-line (`sceneText.split('\n')`), each line producing
one block — except a character-cue line, which produces **two** blocks
(`character` then `dialogue`). Rules, in priority order:

| Type | Detection |
|------|-----------|
| `blank` | line is empty / whitespace only |
| `scene-heading` | trimmed line matches `/^(INT|EXT|EST|INT\.?\/EXT|I\/E)[.\s]/i` |
| `transition` | trimmed line has **no lowercase letters** and ends with `TO:`, `TO`, `OUT.`, `OUT`, or equals a `FADE IN:`-style cue (regex `/^[A-Z0-9 '().-]+(TO|OUT|IN)[:.]?$/` with a length cap, e.g. ≤ 30 chars) |
| `character` + `dialogue` | trimmed line matches `/^([A-Z0-9][A-Z0-9 '().\-]{0,24}):\s*(\S.*)$/` — i.e. the token **before the first colon** has no lowercase letters, is ≤ 25 chars, and is followed by non-empty dialogue text. Emit `{type:'character', text: name}` then `{type:'dialogue', text: dialogue}` |
| `action` | anything else (default) |

The **all-caps guard on the pre-colon token** is the key discriminator: it keeps
lines like `It reads: REMINDER...` and `...Group name: FFEVA` (lowercase before
the colon) classified as `action`, while `SPHE:` / `KHANYI:` convert to
character+dialogue. Scene-heading and transition checks run before the
character check so `CUT TO:` is not mis-read as a `CUT:`-style cue.

This function is unit-testable in isolation from React. If a JS test runner
(vitest/jest) is configured in `frontend/`, add a test file covering: slugline,
action prose containing a colon, `NAME: dialogue`, a `FFEVA`-style false colon,
`CUT TO:`, and a blank line. If no runner is configured, ship the pure function
without tests (frontend is gated on `npm run build` per repo convention).

### 2. `BreakdownDrawer.jsx` rendering

The `useMemo` keeps its current responsibilities — building the highlight regex
from AI + user item names, computing `foundNames` / `notFoundItems`, and the
`typeLookup` — unchanged. Two changes:

- Extract the current inline mark/span splitting into a local helper
  `renderHighlighted(text, keyPrefix)` that returns the array of
  `<mark>` / `<span>` nodes (identical logic to today's per-line `parts.map`).
- Replace the flat line map with: `parseScreenplayBlocks(sceneText).map(...)`,
  rendering each block in a `<div>` whose className encodes its type
  (`bd-sl-<type>`), with `renderHighlighted(block.text)` as its children.
  `blank` blocks render an empty spacer div.

`notFoundItems` continues to be computed and returned as today. The early-return
branches (no item names, or no found names) are folded into the same block
pipeline — they just render blocks with no highlight regex applied.

### 3. CSS — `frontend/src/components/breakdown/BreakdownDrawer.css`

New `.bd-sl-*` classes, indentation expressed in `%`/`em` so it scales inside
the narrow drawer page:

- `.bd-sl-scene-heading` — `font-weight: 700`, top margin, left.
- `.bd-sl-action` — full width, left.
- `.bd-sl-character` — centered, caps, top margin (small).
- `.bd-sl-dialogue` — indented block (left + right padding, e.g. `~18%` / `~15%`).
- `.bd-sl-transition` — `text-align: right`.
- `.bd-sl-blank` — fixed-height vertical spacer (~`0.6em`).

**Supersedes prior change:** the `.bd-script-lines` wrapper introduced earlier
(inline-block, centered as a unit) reverts to `display: block; width: 100%` so
per-element alignment (centered cues, right-aligned transitions, indented
dialogue) is measured against the full page width. The `text-align: center` on
`.bd-script-text-body` added earlier is removed.

## Data Flow

```
sceneText (raw string, from drawer props)
  -> parseScreenplayBlocks()            // pure classify
     -> [{type, text}, ...]
  -> BreakdownDrawer render:
       for each block:
         <div class="bd-sl-{type}">
           renderHighlighted(block.text)  // reuse regex + typeLookup
         </div>
```

The highlight regex, `foundNames`, and `notFoundItems` are computed once per
`useMemo` run exactly as today; only how the text is chunked and styled changes.

## Error Handling / Failure Modes

- Empty / missing `sceneText` → `parseScreenplayBlocks` returns `[]`; the panel
  renders nothing new (same as today's null branch).
- Heuristic misfire → a line falls through to `action` (its default). The text
  is always shown verbatim; the degradation is styling only, never data loss or
  a crash.
- Highlighting is unaffected: item marks apply to `action`, `dialogue`, and
  `character` block text alike.

## Testing / Verification

- `npm run build` in `frontend/` must pass (repo gate; `npm run lint` is known
  broken).
- Manual: open the breakdown drawer on the scene from the screenshot and confirm
  slugline is bold, `SPHE:` / `KHANYI:` become centered cues with indented
  dialogue, `It reads:` / `Group name:` stay as action, `CUT TO:` is
  right-aligned, and existing highlights still render.
- If a JS test runner exists, unit-test `parseScreenplayBlocks` per the cases
  listed above.
