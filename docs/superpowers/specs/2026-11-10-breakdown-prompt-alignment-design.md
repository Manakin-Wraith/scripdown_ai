# Breakdown Prompt Alignment: Design (draft, not yet approved)

Status: **draft for review.** Nothing in the app has been changed. This records what the `script-breakdown` skill (`.claude/skills/script-breakdown/`) showed about gaps in the production analysis prompt.

## Intent

SlateOne's value is the AI breakdown. The production prompt, `analyze_scene_with_gemini` in `backend/routes/supabase_routes.py`, is short and was written to fill app fields, not to follow professional breakdown practice. The new skill encodes that practice. This spec lists where the two differ and proposes which differences are worth closing.

## What matches already

- Eighths: 55 lines per page, 8 eighths per page (`utils/scene_calculations.py`), the same convention as the skill.
- Scene numbers come from the script text, never from the AI.
- Speaking characters come from the grammar parse; the AI adds non-speaking ones; `entity_resolver` merges duplicates.
- The previous scene is passed as context for story-day and timeline detection.

## Gaps (observed in the code and in test runs)

| # | Gap | Evidence |
|---|-----|----------|
| 1 | No categories for **stunts, set dressing, animals, special equipment**, or **VFX separate from practical SFX** | Prompt asks for props, wardrobe, special_fx, vehicles, makeup_hair, locations, sound, atmosphere only |
| 2 | **Implied items are excluded** ("Only include items ACTUALLY in the scene text"), so needs like a cup for a coffee scene are never surfaced. The legacy `gemini_service.analyze_script` prompt asked for implied items, so the two prompts disagree | `supabase_routes.py` prompt vs `gemini_service.py` |
| 3 | **No safety or sensitive-content flags** (stunts, weapons, minors, animals, intimacy, suicide/self-harm) | Absent from the prompt. In the skill test the Afrikaans excerpt opens on a suicide scene; the skill flagged it as `SENSITIVE CONTENT` |
| 4 | **Scene text truncated at 8,000 characters** (`scene_text[:8000]`), so the tail of a long scene is never analysed | One scene in the English test excerpt ran about 4 6/8 pages |
| 5 | **No explicit "don't invent" rule** for wardrobe, era or brands. Without the skill, the test run invented a look for every character | Baseline output, Afrikaans excerpt |
| 6 | **No handling for non-English scripts** (keep original terms, gloss) | Afrikaans test excerpt |
| 7 | Dead code: `gemini_service.analyze_script` (first 3 scenes only, 15,000-character cap) appears unused | Not verified; needs a reference search before removal |

## Proposal (for discussion)

1. Rewrite the prompt using the skill's rules: stated vs implied (implied items returned in a separate field or flagged), safety and sensitive-content notes, no invention, original-language terms kept.
2. Raise or remove the 8,000-character cut-off, or split long scenes and merge results.
3. Add categories only where the product has somewhere to show them.
4. Remove or reconcile `gemini_service.analyze_script` after confirming nothing calls it.

## Non-goals

- Replacing Gemini or the pipeline in `extraction_pipeline.py`.
- Changing how scene numbers or eighths are calculated.
- Treating the skill as a runtime dependency. The skill guides Claude Code sessions; the app needs its own prompt text.

## Open questions (need an owner decision)

- Do new categories (stunts, set dressing, animals, equipment, VFX) need new database columns and UI, or can they live in a flexible field? I have **not** checked the schema or the breakdown UI.
- Should implied items count as part of the breakdown by default, or sit behind a "suggested" state the user confirms? This changes what users see and what reports print.
- Do safety and sensitive-content flags appear in the stripboard and reports, or only in the scene view?
- The test sample is two excerpts. A regression set of full scenes (with a few hand-checked answers) is needed before judging any prompt change.
- This belongs with the "new version" project as much as the current app. Decide which codebase this lands in.

## Verification idea

Run old and new prompts over the same 20–30 scenes from the scripts in `backend/uploads/`, and compare item counts and a hand-check of 5 scenes. Record whether the new prompt adds real items or noise.
