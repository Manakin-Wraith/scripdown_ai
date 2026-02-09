# Story Days Feature — Brainstorm

## What Are "Story Days"?

In production, a **story day** (a.k.a. "script day") is the narrative day within the story's timeline. For example:

| Scene | Setting | Time of Day | Story Day |
|-------|---------|-------------|-----------|
| 1 | SARAH'S APARTMENT - INT | MORNING | Day 1 |
| 2 | COFFEE SHOP - INT | DAY | Day 1 |
| 3 | OFFICE - INT | DAY | Day 1 |
| 4 | SARAH'S APARTMENT - INT | NIGHT | Day 1 |
| 5 | PARK - EXT | MORNING | Day 2 |
| 6 | COURTHOUSE - INT | DAY | Day 2 |
| 7 | BAR - INT | NIGHT | Day 2 |
| 8 | HOSPITAL - INT | DAY | Day 3 |
| — | *"THREE MONTHS LATER"* | — | — |
| 9 | PRISON - INT | DAY | Day 4 |

Story days are **critical** for production departments:

- **Wardrobe Continuity** — Characters wear the same outfit within a story day; a new day = potential wardrobe change.
- **Makeup Continuity** — Injuries, aging, bruises must match within a day.
- **Scheduling / Stripboard** — Scenes from the same story day should ideally be grouped when building the shooting schedule.
- **Cast Requirements per Story Day** — Know which characters appear on which narrative days for planning purposes.
- **Props & Set Dressing** — Some props only exist on certain story days (e.g., "birthday cake" on Day 3).

> **⚠️ IMPORTANT: Narrative Time ≠ Production Time**
>
> - **Story Days** = Narrative time (Monday, Tuesday *within the plot*).
> - **Day Out of Days (DOOD)** = Production time (Day 1 of *shooting*, Day 2 of *shooting*).
>
> A true DOOD report is derived from a **Shooting Schedule / Stripboard**, not from the script's scene order.
> You cannot generate a real DOOD until the user has reordered scenes into a shooting order
> (e.g., shooting Scene 9 before Scene 1 because they share a location).
>
> **What we can build now**: "Cast Narrative Timeline" / "Cast Requirements per Story Day".
> **What requires a Scheduling module**: Industry-standard DOOD with W/S/F/H designations.

---

## Current State Analysis

### What We Have

1. **`time_of_day`** on scenes: `DAY`, `NIGHT`, `DAWN`, `DUSK`, `CONTINUOUS`, `LATER`
   - Extracted from scene headers during regex parsing in `supabase_routes.py` (lines 611-628).
   - Also sent to AI during scene enhancement.
   - **Problem**: This is the *time within a day*, not *which* day.

2. **Scene order** (`scene_order` column): Sequential ordering of scenes.

3. **AI prompts** (`scene_enhancer.py`, `analysis_worker.py`):
   - Extract 16 breakdown categories per scene.
   - **Do NOT** extract story day or time-transition cues.

4. **Day Out of Days report** (`report_service.py` lines 822-859):
   - Currently just a character-scene matrix (character name → scene count + scene numbers).
   - **Does NOT** track actual story days — it's a "Character Out of Scenes" report, not a true DOOD.

5. **Database**: No `story_day` column exists on the `scenes` table.

### What's Missing

| Gap | Impact |
|-----|--------|
| No `story_day` column | Can't group scenes by narrative day |
| No time-transition detection | Can't infer day boundaries from "THE NEXT MORNING", "LATER", etc. |
| AI prompts don't extract story day | Missing the most reliable inference method |
| "DOOD" report is actually just a character-scene matrix | Can't generate narrative timeline reports; true DOOD requires a Scheduling module |
| Stripboard lacks day grouping | Scenes can't be grouped/colored by story day |

---

## How Story Days Can Be Detected

Story day boundaries are signaled by several cues in screenplays:

### 1. Scene Header Cues (Regex-Detectable)
- `DAY` → `NIGHT` within the same location context = likely same day.
- `NIGHT` → `DAY` or `MORNING` = likely **new day**.
- `CONTINUOUS` / `MOMENTS LATER` = definitely same day.
- `LATER` = ambiguous (could be same day or next).
- `THE NEXT DAY` / `THE FOLLOWING MORNING` = explicit new day.

### 2. Action Line / Transition Cues (AI-Detectable)
- `"The next morning, Sarah wakes up..."` → new day.
- `"THREE WEEKS LATER"` / `"TITLE CARD: SIX MONTHS LATER"` → new day (with gap).
- `"That same afternoon..."` → same day.
- `"Dawn breaks over the city..."` → likely new day.

### 3. Contextual Inference (AI Required)
- Scene at BEDROOM + NIGHT followed by scene at KITCHEN + MORNING = new day (even without explicit text).
- Montage sequences might span multiple days.
- Flashbacks/dream sequences complicate linear day counting.

### 4. End-of-Scene Cues (V1 Gap — Acceptable)
Time jumps sometimes appear in the *last action line* of the **previous** scene, not the start of the current one:
- Scene 1 Action: `"The sun goes down. Darkness falls."` (implies next scene is Night/Next Day).
- Scene 2 Header: `INT. HOUSE - NIGHT`

The current "Per-Scene Start-Focus" strategy will miss these. Acceptable for V1; can be addressed in V2 with a whole-script pass.

### Critical Problem: Context Blindness (Per-Scene AI)

> **⚠️ GAP A: The AI analyzes scenes in isolation.**
>
> When `scene_enhancer.py` analyzes Scene X, it only sees Scene X's text.
> It does **NOT** see the previous scene's header or time of day.
>
> **Example**: `INT. BEDROOM - NIGHT` → `INT. KITCHEN - DAY`
> - A human knows this is a **new day** (night passed, it's morning now).
> - The AI analyzing the KITCHEN scene only sees: `"INT. KITCHEN - DAY. Sarah makes coffee."`
> - It has no idea the previous scene was NIGHT. It will return `is_new_story_day: false`.
>
> **Result**: ~100% of implicit NIGHT→DAY transitions will be missed without a fix.

**The Fix: Previous Scene Context Injection** (see Option C Enhanced below).

### Difficulty Spectrum (Corrected)

| Method | Accuracy | Coverage | Cost |
|--------|----------|----------|------|
| Regex on `time_of_day` transitions | ~50% | Low | Free |
| AI per-scene **without** previous context | ~40% | Medium | 1 API call/scene (already done) |
| AI per-scene **with** previous context injected | ~80% | High | 1 API call/scene (already done) |
| AI whole-script pass (dedicated) | ~95% | Very High | 1 extra API call/script |
| Manual user assignment | 100% | Full | User effort |

---

## Proposed Implementation Options

### Option A: Add to Existing Per-Scene AI Enhancement (Recommended)

**Approach**: Extend the `enhance_scene()` prompt in `scene_enhancer.py` to also extract story day signals.

**Changes Required**:

#### Database
See full revised migration in [Database Migration Plan](#database-migration-plan) below. Key columns: `story_day`, `story_day_label`, `time_transition`, `is_new_story_day`, `story_day_confidence`, `story_day_is_manual`, `story_day_is_locked`, `timeline_code`.

#### AI Prompt Addition (in `scene_enhancer.py` → `enhance_scene()`)
Add to the existing prompt:
```
**STORY TIMELINE:**
17. TIME_TRANSITION: Any time-transition cue at the START of this scene relative to the previous scene
    (e.g., "THE NEXT MORNING", "CONTINUOUS", "LATER THAT DAY", "THREE WEEKS LATER", "SAME TIME", "MOMENTS LATER")
    Return empty string "" if no transition is indicated.
18. IS_NEW_STORY_DAY: true/false — Does this scene start a NEW narrative day compared to the previous scene?
    Consider: NIGHT→MORNING = new day, CONTINUOUS = same day, explicit "NEXT DAY" = new day.
19. STORY_DAY_REASONING: Brief explanation of why this is/isn't a new day (for confidence scoring).
```

Update the JSON response format:
```json
{
    "time_transition": "THE NEXT MORNING",
    "is_new_story_day": true,
    "story_day_reasoning": "Scene transitions from previous night to morning, indicating a new day"
}
```

#### Post-Processing (New Function)
After all scenes are enhanced, run a **sequential pass** to assign story day numbers:

```python
def assign_story_days(script_id, db_conn):
    """
    Sequential pass over all scenes to assign story_day numbers.
    Must run AFTER all scenes are enhanced (needs time_transition data).
    """
    scenes = get_scenes_ordered(script_id, db_conn)
    current_day = 1
    
    for i, scene in enumerate(scenes):
        if i == 0:
            scene['story_day'] = 1
            continue
        
        if scene.get('is_new_story_day'):
            current_day += 1
        
        scene['story_day'] = current_day
        scene['story_day_label'] = f"Day {current_day}"
        
        # Adjust label for time gaps
        transition = scene.get('time_transition', '')
        if 'WEEK' in transition or 'MONTH' in transition or 'YEAR' in transition:
            scene['story_day_label'] = f"Day {current_day} ({transition})"
    
    # Batch update all scenes
    bulk_update_story_days(script_id, scenes, db_conn)
```

#### Save Logic Update (`save_enhanced_scene()`)
Add `time_transition`, `story_day_confidence` to the INSERT statement.

**Pros**:
- Zero additional API calls (rides on existing enhancement pass).
- Per-scene context is already available.
- Incremental — can re-run for individual scenes.

**Cons**:
- **CRITICAL (Gap A)**: Per-scene AI has zero cross-scene context. It cannot detect implicit NIGHT→DAY transitions because it never sees the previous scene. This results in ~50% failure rate for day boundary detection.
- Requires a post-processing step to assign sequential day numbers.
- **Not viable without fixing Gap A** — must inject previous scene context (see Option C Enhanced).

---

### Option B: Dedicated Whole-Script Story Day Pass

**Approach**: After all scenes are enhanced, run a **single AI call** with the full scene list (headers + descriptions only) to assign story days holistically.

#### New Job Type
```python
# In analysis_queue_service.py
# job_type = 'story_days'  — runs after scene_enhancement completes
```

#### Dedicated Prompt
```
Given the following scene list from a screenplay, assign each scene a "story day" number.
A story day is the narrative day in the story's timeline.

Rules:
- Day 1 starts at Scene 1 unless otherwise indicated
- NIGHT → MORNING/DAY transition = new day (usually)
- CONTINUOUS / MOMENTS LATER = same day
- Explicit cues like "THE NEXT DAY" = new day
- Time jumps ("THREE MONTHS LATER") = new day with gap

Scene List:
1. INT. SARAH'S APARTMENT - MORNING — "Sarah wakes up and gets ready for work"
2. INT. COFFEE SHOP - DAY — "Sarah meets her boss for coffee"
...

Return JSON: [{"scene_number": "1", "story_day": 1, "time_transition": "", "confidence": 0.95}, ...]
```

**Pros**:
- Holistic view — AI can see the full narrative arc.
- Higher accuracy for ambiguous transitions.
- Single API call for the entire script.

**Cons**:
- Token limits: A 120-scene script could exceed input limits (mitigated by sending headers+descriptions only, ~50 tokens/scene = ~6000 tokens).
- Adds a new job type to the queue.
- Not incremental — must re-run for entire script if one scene changes.

---

### Option C Enhanced: Hybrid with Context Injection (Recommended for V1)

Incorporates fixes for Gap A (Context Blindness), Gap B (Ripple Effect), and Gap C (DOOD Misconception).

#### Fix 1: Previous Scene Context Injection (Gap A)

When `scene_enhancer.py` builds the prompt for Scene X, it **must query Scene X-1** from the DB and prepend its header:

```python
# In scene_enhancer.py — enhance_scene() or process_scene_candidate()

prev_scene = get_scene_by_order(script_id, current_scene_order - 1, db_conn)

if prev_scene:
    prev_context = (
        f"CONTEXT — PREVIOUS SCENE:\n"
        f"  Scene {prev_scene['scene_number_original']}: "
        f"{prev_scene.get('int_ext', '')}. {prev_scene.get('setting', '')} "
        f"- {prev_scene.get('time_of_day', '')}\n"
        f"  Summary: {prev_scene.get('description', 'N/A')}\n\n"
    )
else:
    prev_context = "CONTEXT: This is the FIRST scene of the script.\n\n"

prompt = prev_context + standard_prompt
```

**Result**: The AI can now perform differential analysis. When it sees `PREVIOUS: BEDROOM - NIGHT` and `CURRENT: KITCHEN - DAY`, it correctly infers a new day.

**Implementation Note**: Since scenes are enhanced sequentially via `process_all_candidates()`, the previous scene's data is already in the DB by the time we process Scene X. No pipeline changes needed — just a DB query before building the prompt.

#### Fix 2: Timeline Calculator Service (Gap B — Cascade Updates)

Instead of a one-off function, create a **dedicated service method** that can be triggered from multiple entry points:

```python
def recalculate_story_days(script_id, start_from_order=0, db_conn=None):
    """
    Sequential pass to assign story_day numbers.
    
    Fetches all scenes from start_from_order onward.
    Respects manually locked days.
    Updates DB in batch.
    
    Triggers:
      1. After AI enhancement batch completes
      2. After user manually toggles "New Day" on a scene
      3. After user manually sets a story_day value
      4. After scene reorder / split / merge / add / delete
    """
    scenes = get_scenes_ordered(script_id, db_conn)
    
    # Determine starting day counter
    if start_from_order > 0:
        prev_scene = scenes[start_from_order - 1]
        current_day = prev_scene.get('story_day', 1)
    else:
        current_day = 1
    
    for i, scene in enumerate(scenes):
        if i < start_from_order:
            continue
        
        # Respect locked days — if user locked "Day 3", reset counter to 3
        if scene.get('story_day_is_locked') and scene.get('story_day') is not None:
            current_day = scene['story_day']
            continue
        
        if i == 0:
            scene['story_day'] = 1
            current_day = 1
        elif scene.get('is_new_story_day'):
            current_day += 1
            scene['story_day'] = current_day
        else:
            scene['story_day'] = current_day
        
        # Build label
        transition = scene.get('time_transition', '')
        if transition and ('WEEK' in transition.upper() or 'MONTH' in transition.upper() or 'YEAR' in transition.upper()):
            scene['story_day_label'] = f"Day {current_day} ({transition})"
        else:
            scene['story_day_label'] = f"Day {current_day}"
        
        # Handle timeline type
        timeline = scene.get('timeline_code', 'PRESENT')
        if timeline == 'FLASHBACK':
            scene['story_day_label'] = f"Flashback — {scene['story_day_label']}"
        elif timeline == 'DREAM':
            scene['story_day_label'] = f"Dream — {scene['story_day_label']}"
    
    # Batch update
    bulk_update_story_days(script_id, scenes[start_from_order:], db_conn)
    
    # Update script total
    total_days = len(set(s['story_day'] for s in scenes if s.get('story_day')))
    update_script_total_story_days(script_id, total_days, db_conn)
```

**Trigger Points** (all must call `recalculate_story_days`):
- After `process_all_candidates()` completes (initial analysis)
- After user toggles `is_new_story_day` on any scene (UI action)
- After user manually sets a `story_day` value (UI action)
- After scene reorder / split / merge / add / delete operations in SceneManager

#### Fix 3: Report Naming (Gap C)

| Current Name | Corrected Name | Status |
|-------------|---------------|--------|
| "Day Out of Days" | **"Cast Narrative Timeline"** or **"Cast Requirements per Story Day"** | Rename now |
| True DOOD with W/S/F/H | "Day Out of Days" | Requires Scheduling/Stripboard module (future) |

Do **not** label any report "Day Out of Days" until we build a Scheduling module that allows users to reorder scenes into a shooting order.

#### Summary: Option C Enhanced Flow

1. **During `enhance_scene()`**: Inject previous scene context + extract `time_transition` and `is_new_story_day` per scene (zero extra API calls).
2. **Post-enhancement**: Run `recalculate_story_days()` service to assign sequential day numbers, respecting locked days.
3. **On any scene edit**: Trigger cascade recalculation from the changed scene onward.
4. **Manual override**: Allow users to lock story days, toggle "New Day", edit in SceneManager.
5. **Reports**: Generate "Cast Narrative Timeline" (not DOOD). True DOOD deferred to Scheduling module.
6. **Future V2**: Add dedicated whole-script AI pass for higher accuracy on ambiguous transitions.

---

## Impact on Existing Features

### Cast Narrative Timeline Report (Replaces "Day Out of Days")
Currently `_render_day_out_of_days()` shows character × scene count. With story days, this becomes a **Cast Narrative Timeline**:

| Character | Narrative Days | First Appears | Last Appears | Total Days | Scene Numbers |
|-----------|---------------|---------------|-------------|------------|---------------|
| SARAH | 1,2,3,4 | Day 1 | Day 4 | 4 | 1,2,3,5,6,8,9 |
| JOHN | 1,2 | Day 1 | Day 2 | 2 | 2,3,6 |

> **⚠️ This is NOT a Day Out of Days (DOOD) report.**
> A true DOOD requires a Shooting Schedule where scenes are reordered into production order.
> Until we build a Scheduling module, this report shows cast requirements per *narrative* day.
> Rename `day_out_of_days` → `cast_narrative_timeline` in `REPORT_TYPES` and UI.

### Stripboard / One-Liner
Group scenes by story day with day separators:

```
═══════════════ DAY 1 ═══════════════
  1  INT  SARAH'S APARTMENT  MORNING  1/8  SARAH
  2  INT  COFFEE SHOP        DAY      2/8  SARAH, JOHN
  3  INT  OFFICE             DAY      3/8  SARAH, JOHN, BOSS
═══════════════ DAY 2 ═══════════════
  5  EXT  PARK               MORNING  1/8  SARAH
  6  INT  COURTHOUSE         DAY      4/8  SARAH, JOHN, LAWYER
```

### SceneDetail / SceneList UI
- Show story day badge on each scene card (e.g., "D1", "D2").
- Color-code scenes by story day in the scene list.
- Filter scenes by story day.

### SceneManager
- Add "Story Day" column to the management table.
- Allow manual editing (dropdown or inline edit).
- Bulk assign: "Set scenes 5-8 to Day 3."

### Analytics
- "Total story days" metric in script summary.
- "Scenes per story day" distribution chart.

---

## Database Migration Plan

```sql
-- Migration: 02X_story_days.sql

-- ============================================
-- 1. Timeline Type (handles non-linear narratives)
-- ============================================
-- Screenplays are often non-linear (flashbacks, dreams, parallel timelines).
-- A simple INTEGER story_day assumes linearity. This enum solves that.
-- UI must group by timeline_code FIRST, then by story_day.

CREATE TYPE timeline_code AS ENUM ('PRESENT', 'FLASHBACK', 'DREAM', 'FANTASY', 'MONTAGE', 'TITLE_CARD');
-- Note: If using Supabase/Postgres and the type already exists, wrap in DO block.

-- ============================================
-- 2. Add story day columns to scenes
-- ============================================
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS story_day INTEGER;
  -- Nullable: NULL = not yet determined or timeless/abstract scene.
  -- 1-based numbering for present-timeline scenes.
  -- For FLASHBACK scenes: can reference the flashback's own timeline day.

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS story_day_label TEXT;
  -- Human-readable label, e.g., "Day 1", "Flashback — Day 3", "Dream Sequence"

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS time_transition TEXT;
  -- AI-extracted transition cue from previous scene.
  -- e.g., "THE NEXT MORNING", "CONTINUOUS", "THREE MONTHS LATER", ""

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS is_new_story_day BOOLEAN DEFAULT FALSE;
  -- AI-determined: does this scene start a new narrative day?
  -- Used by recalculate_story_days() to increment the day counter.

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS story_day_confidence FLOAT DEFAULT 0.0;
  -- AI confidence in the is_new_story_day determination (0.0-1.0)

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS story_day_is_manual BOOLEAN DEFAULT FALSE;
  -- Whether the user manually set is_new_story_day (overrides AI)

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS story_day_is_locked BOOLEAN DEFAULT FALSE;
  -- Whether the user locked this scene's story_day number.
  -- recalculate_story_days() respects locked values and resets its counter.

ALTER TABLE scenes ADD COLUMN IF NOT EXISTS timeline_code VARCHAR(20) DEFAULT 'PRESENT';
  -- PRESENT | FLASHBACK | DREAM | FANTASY | MONTAGE | TITLE_CARD
  -- Determines how story_day is interpreted and displayed.

-- ============================================
-- 3. Indexes
-- ============================================
CREATE INDEX IF NOT EXISTS idx_scenes_story_day ON scenes(script_id, story_day);
CREATE INDEX IF NOT EXISTS idx_scenes_timeline ON scenes(script_id, timeline_code);

-- ============================================
-- 4. Script-level metadata
-- ============================================
ALTER TABLE scripts ADD COLUMN IF NOT EXISTS total_story_days INTEGER DEFAULT 0;

-- ============================================
-- 5. Comments
-- ============================================
COMMENT ON COLUMN scenes.story_day IS 'Narrative day number (1-based). NULL = not yet determined or timeless.';
COMMENT ON COLUMN scenes.story_day_label IS 'Human-readable day label (e.g., "Day 1", "Flashback — Day 3")';
COMMENT ON COLUMN scenes.time_transition IS 'Time transition cue from previous scene (AI-extracted)';
COMMENT ON COLUMN scenes.is_new_story_day IS 'Whether this scene starts a new narrative day (AI or manual)';
COMMENT ON COLUMN scenes.story_day_confidence IS 'AI confidence in is_new_story_day (0.0-1.0)';
COMMENT ON COLUMN scenes.story_day_is_manual IS 'Whether is_new_story_day was manually set by user';
COMMENT ON COLUMN scenes.story_day_is_locked IS 'Whether story_day number is locked (recalculate respects this)';
COMMENT ON COLUMN scenes.timeline_code IS 'Timeline type: PRESENT, FLASHBACK, DREAM, FANTASY, MONTAGE, TITLE_CARD';
COMMENT ON COLUMN scripts.total_story_days IS 'Total unique story days in script';
```

### Data Model Design Notes

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| `story_day` | INTEGER | **Yes** | NULL | Narrative day number. NULL for undetermined or abstract scenes. |
| `story_day_label` | TEXT | Yes | NULL | Display label (e.g., "Day 1", "Flashback — Day 3") |
| `time_transition` | TEXT | Yes | NULL | AI-extracted transition cue from previous scene |
| `is_new_story_day` | BOOLEAN | No | FALSE | Does this scene start a new day? (drives recalculation) |
| `story_day_confidence` | FLOAT | No | 0.0 | AI confidence in `is_new_story_day` |
| `story_day_is_manual` | BOOLEAN | No | FALSE | User override of `is_new_story_day` |
| `story_day_is_locked` | BOOLEAN | No | FALSE | Lock `story_day` number (recalculate respects it) |
| `timeline_code` | VARCHAR(20) | No | 'PRESENT' | PRESENT / FLASHBACK / DREAM / FANTASY / MONTAGE / TITLE_CARD |

**Why `timeline_code`?**
If Scene 1 is "Present Day" (Day 10 of the story), and Scene 2 is "Flashback to Childhood", what is `story_day`?
- If you put `0` or `-1`, sorting breaks.
- If you put `11`, it implies the future.
- **Solution**: `timeline_code = 'FLASHBACK'` + `story_day = NULL` (or a separate flashback-internal day count).
- The UI groups by `timeline_code` first, then sorts by `story_day` within each group.

---

## API Endpoints (New)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/scripts/:id/story-days` | Get all scenes grouped by story day + timeline_code |
| `POST` | `/api/scripts/:id/story-days/calculate` | Trigger story day calculation (runs `recalculate_story_days`) |
| `PATCH` | `/api/scripts/:id/scenes/:sceneId/story-day` | Manually set a scene's story day + triggers cascade recalc |
| `PATCH` | `/api/scripts/:id/scenes/:sceneId/toggle-new-day` | Toggle `is_new_story_day` + triggers cascade recalc |
| `PATCH` | `/api/scripts/:id/scenes/:sceneId/lock-story-day` | Lock/unlock a scene's story day number |
| `PATCH` | `/api/scripts/:id/scenes/:sceneId/timeline-code` | Set timeline_code (PRESENT/FLASHBACK/DREAM/etc.) |
| `POST` | `/api/scripts/:id/story-days/bulk-update` | Bulk update story days for multiple scenes |
| `GET` | `/api/scripts/:id/story-days/summary` | Get story day statistics |

**Important**: Any endpoint that modifies `is_new_story_day`, `story_day`, or `timeline_code` must trigger `recalculate_story_days(script_id, start_from_order=modified_scene_order)` to cascade updates to subsequent scenes.

---

## Implementation Phases (Revised)

### Phase 1: Data Model + Previous Context Injection (Backend)
- [ ] Create database migration (`02X_story_days.sql`) with all columns + `timeline_code`
- [ ] Add `get_scene_by_order()` helper to fetch Scene X-1 from DB
- [ ] **Inject previous scene context** into `enhance_scene()` prompt (Gap A fix)
- [ ] Add `time_transition`, `is_new_story_day`, `timeline_code` fields to AI prompt
- [ ] Update `save_enhanced_scene()` to store new fields
- [ ] Create `recalculate_story_days()` service (with locked-day support)
- [ ] Wire `recalculate_story_days()` to run after `process_all_candidates()` completes
- [ ] Add `total_story_days` update to `scripts` table after recalculation

### Phase 2: Cascade Updates + Manual Editing (Backend + Frontend)
- [ ] Add API endpoints (toggle-new-day, lock-story-day, timeline-code, bulk-update)
- [ ] **Wire cascade recalculation** to all scene-modifying endpoints (split, merge, reorder, add, delete)
- [ ] Add story day column + "New Day" toggle to SceneManager
- [ ] Add lock/unlock UI for story day numbers
- [ ] Add `timeline_code` selector (PRESENT/FLASHBACK/DREAM) per scene
- [ ] Add inline edit / bulk assign UI

### Phase 3: Reports + UI Enhancement
- [ ] **Rename** `day_out_of_days` → `cast_narrative_timeline` in `REPORT_TYPES` and UI
- [ ] Build "Cast Narrative Timeline" report using story days
- [ ] Add story day separators to stripboard/one-liner
- [ ] Add story day badges to SceneList/SceneDetail
- [ ] Color-code scenes by story day in scene list

### Phase 4: Advanced Features (V2)
- [ ] Dedicated whole-script AI pass for higher accuracy on ambiguous transitions
- [ ] Story day timeline visualization (grouped by `timeline_code`)
- [ ] Continuity tracker (flag wardrobe/makeup changes within same story day)
- [ ] Story day filter in scene viewer
- [ ] **Scheduling module** (prerequisite for true DOOD report)
- [ ] True Day Out of Days report (requires shooting schedule / scene reorder)

---

## Risk Assessment (Architect-Reviewed)

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Context Blindness** (NIGHT→DAY missed without prev scene) | High (100% of implicit transitions) | **High** | **MUST** inject previous scene header into AI prompt (Gap A fix). Non-negotiable. |
| **Flashback Confusion** (non-linear narrative breaks integer linearity) | Medium | Medium | Add `timeline_code` column (PRESENT/FLASHBACK/DREAM). Allow `story_day` to be NULL for abstract scenes. |
| **DOOD Report Rejection** (production managers expect shooting-order DOOD) | High | **High** | Rename report to "Cast Narrative Timeline". Do NOT call it DOOD until Scheduling module exists. |
| **Ripple Updates** (editing Scene 5's day doesn't update Scenes 6-100) | High | Medium | Build `recalculate_story_days()` service with cascade logic. Trigger on all scene-modifying operations. |
| **End-of-Scene Cues Missed** (time jump in prev scene's last action line) | Medium | Low | Acceptable V1 gap. Current "Per-Scene Start-Focus" strategy misses these. Address in V2 whole-script pass. |
| **Token Cost** | Low | Low | Adding 3 fields + prev scene context adds ~150 tokens per scene. Negligible. |
| **Existing Scripts Backfill** | Medium | Medium | Provide "Calculate Story Days" button in UI. Re-run enhancement not required — only need `recalculate_story_days()` if `time_transition` data exists. |
| **Locked Day Conflicts** | Low | Low | If user locks Day 3 on Scene 10, but AI later says Scene 8 starts Day 4 → counter resets at Scene 10. May produce non-monotonic days. UI should warn. |

### Accepted V1 Gaps

1. **End-of-scene cues**: Time jumps in the last action line of Scene X-1 will not be detected. Requires whole-script context (V2).
2. **Parallel intercut timelines**: Not supported in V1. Would need a `timeline_track` field to represent two simultaneous narrative threads.
3. **Montage spanning multiple days**: Montage scenes may be assigned a single story day. User can manually split or override.

---

## Recommendation (Revised)

**Start with Option C Enhanced (Hybrid with Context Injection)**:

1. Add columns to DB — including `timeline_code`, `is_new_story_day`, `story_day_is_locked` (cheap, non-breaking).
2. **Inject previous scene context** into `enhance_scene()` prompt (zero extra API calls, fixes the critical ~50% failure rate).
3. Build `recalculate_story_days()` as a dedicated service with locked-day support and cascade triggers.
4. Rename "Day Out of Days" → "Cast Narrative Timeline" immediately.
5. Add manual override + lock/unlock in SceneManager.
6. Iterate toward whole-script AI pass in V2.

This approach delivers **~80% accuracy** (up from ~40% without context injection) with **zero extra API cost**, handles non-linear narratives via `timeline_code`, prevents cascade bugs via the recalculation service, and avoids the DOOD naming trap.

---

## Architectural Review Log

| Date | Reviewer | Gaps Identified | Status |
|------|----------|----------------|--------|
| 2026-02-06 | Systems Architect | Gap A: Context Blindness, Gap B: Ripple Effect, Gap C: DOOD Misconception | ✅ All incorporated |
| | | Data model: integer linearity, timeline_code, locked days | ✅ All incorporated |
| | | V1 accepted gap: end-of-scene cues | ✅ Documented |
