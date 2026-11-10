---
name: script-breakdown
description: Perform a professional film/TV script breakdown the way a 1st AD or line producer would — scene sheets with page length in eighths, and every production element (cast, extras, stunts, vehicles, props, set dressing, wardrobe, makeup/hair, SFX, VFX, sound, animals, special equipment, notes) tagged by category. Use this skill whenever the user shares a screenplay, scene, or sides and asks for a breakdown, to "break down" a script, tag or extract production elements, build a props/wardrobe/cast list from a script, estimate scene length, or prepare for scheduling or budgeting — even if they never say "breakdown" explicitly.
---

# Script Breakdown

A breakdown turns a screenplay into the list of everything that must exist, be hired, or be arranged to shoot each scene. Its readers are the people who schedule, budget, and prep the film, so the cost of a missed item is real: a forgotten prop is a delayed shoot day, a missed stunt is a safety and insurance problem. Aim to be complete first, then precise.

## Workflow

1. **Read the whole script before tagging anything.** Elements recur and change across scenes (a wound that appears in scene 12 affects makeup in 13–20), and you can't judge continuity or implied needs from one scene alone.
2. **Split into scenes** at each slugline (INT./EXT. LOCATION – TIME). Use the scene numbers printed in the script. If there are none, number sequentially and say so. Never renumber a script that already has numbers, because every downstream document keys off them.
3. **Fill a scene sheet per scene** using the template below.
4. **Tag elements by category** using `references/categories.md` for definitions and edge cases. Read it when a category is unclear or an item could fit two places.
5. **Add a continuity pass** across scenes (story days, recurring wardrobe/makeup states).
6. **List open questions** for anything ambiguous, rather than silently guessing.

## Scene sheet template

Use this exact structure for each scene so output is consistent and machine-parseable:

```
SCENE <number>   <INT|EXT|INT/EXT>   <SET / LOCATION>   <DAY|NIGHT|DAWN|DUSK|…>
Pages: <start>–<end>   Length: <n> 8ths   Story day: <Day N>
Synopsis: <one or two sentences, present tense>

CAST (speaking):      1. NAME, 2. NAME …
CAST (non-speaking):  NAME …
EXTRAS / ATMOSPHERE:  <count or description, e.g. "~30 diners">
STUNTS:               …
VEHICLES:             …
PROPS:                …
SET DRESSING:         …
WARDROBE:             <character: item>
MAKEUP / HAIR:        <character: item>
SPECIAL EFFECTS (practical): …
VISUAL EFFECTS:       …
SOUND / MUSIC:        …
ANIMALS:              …
SPECIAL EQUIPMENT:    …
NOTES:                <permits, minors, intimacy, weapons, weather dependence …>
```

Omit a category line only if it is truly empty; write "—" so the reader knows you checked.

**Incomplete scenes.** If the text ends at a slugline (an excerpt cut off mid-script), don't fill a sheet with "Unknown" lines. Write the header line, one line saying the content is missing, and a NOTES line: "Do not schedule from this sheet." A sheet of placeholders looks like a finished breakdown and invites someone to schedule from it.

## Page length

Measure each scene in **eighths of a page** (one page = 8/8). A scene that runs from one-third down page 4 to the top of page 5 is roughly 5/8 + 1/8 ≈ 6/8. Count lines against the page, not word count, because dialogue and action take different space. A scene under 1/8 is written "1/8". Round up when unsure; schedulers prefer a safe estimate.

## Judgement rules

- **Stated vs. implied.** Tag items explicitly written in the script as stated. Tag items the action clearly requires but doesn't name (someone pours coffee → cup, pot; someone is "drenched" → rain or water source) as *implied*, and mark them `(implied)` so the reader can decide. Don't pad with speculative items the scene doesn't need.
- **Speaking vs. non-speaking cast.** Speaking roles get a cast number in order of first appearance. Named characters with no lines are non-speaking cast, and unnamed background people are extras. The distinction drives contracts and pay.
- **Safety-critical flags go in NOTES, loudly.** Stunts, fire, weapons or firearms, water work, heights, children, animals, vehicles in motion, nudity or intimacy, and anything needing a permit or specialist. Also flag sensitive content that needs a depiction plan and on-set welfare support: suicide or self-harm, sexual violence, child endangerment. Mark it `SENSITIVE CONTENT` so it can't be missed. These change crew, insurance, and schedule, so never bury them.
- **Cross-category items.** Put an item in the category that determines who supplies it. A gun the actor fires is a prop (armorer-supplied) *and* a safety note; a gunshot's muzzle flash is SFX or VFX depending on whether it's practical.
- **Use script language.** Keep character names in UPPERCASE as written. Don't rename, merge, or invent characters. If two names look like the same person, flag it as a question.
- **Don't invent.** If the script doesn't say a character's clothing, leave wardrobe empty rather than fabricating a look; note "unspecified" if it matters. The same goes for era, furniture, brands and car models: a breakdown that fills gaps with plausible guesses can't be told apart from one built on the script, and the costume or art department will act on it. Put the gap in Open questions instead.
- **Other languages.** Keep the script's own terms and character names, with a short bracketed English gloss on first use where it affects production (`stootwaentjie [pram]`). Don't translate names, and flag spelling variants of the same name or place as a question.

## Continuity

Track **story days** separately from scene order: scripts jump in time ("THE NEXT MORNING", "THREE WEEKS LATER", flashbacks, dreams, montage). Increment the story day when time clearly advances; treat CONTINUOUS and "MOMENTS LATER" as the same day. Mark flashbacks and dreams as their own timeline, not the present. For each recurring character, note changes that must carry across scenes (injuries, costume changes, hair, props they hold) so makeup, wardrobe, and script supervision can plan them.

## Output

Deliver the scene sheets in script order, followed by:

1. **Cast list** — all speaking roles numbered, with scene counts.
2. **Open questions** — ambiguities you could not resolve from the text (unclear scene numbers, possible duplicate characters, vague locations, unspecified quantities of extras).

**If the user asks for specific lists** (for example "props, wardrobe and cast list"), still do the scene sheets, because the lists are built from them, but lead with or clearly separate the consolidated lists they asked for, one row per item with the scene numbers it appears in and its stated/implied status. Add other consolidated lists only if they cost nothing.

**Estimated lengths.** Text pasted from a PDF is often double-spaced or has header blocks, so line counts overstate page length. Say that the eighths are estimates and should be re-measured on the formatted script. Don't count title-page or company header text as script pages.

Keep the output focused. The user wants the breakdown, not commentary on the script's quality or scheduling advice they didn't ask for.
