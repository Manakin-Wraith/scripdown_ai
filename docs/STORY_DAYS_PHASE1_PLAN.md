# Story Days — Phase 1 Task Decomposition

**Ticket**: Story Days Feature — Phase 1: Data Model + Previous Context Injection
**Source Spec**: `docs/STORY_DAYS_BRAINSTORM.md` → Phase 1 (Revised)
**Branch**: `feature/story-days-phase1`
**Status**: ✅ **COMPLETED** (2026-02-11)

---

## Task Graph

```json
{
  "ticket_id": "story-days-phase1",
  "title": "Story Days — Phase 1: Data Model + AI Context Injection + Timeline Calculator",
  "subtasks": [
    {
      "id": 1,
      "description": "Create Supabase migration 028_story_days.sql — add all story day columns to scenes + total_story_days to scripts",
      "agent": "Coder (Backend)",
      "dependencies": [],
      "effort": "S",
      "files": [
        "backend/db/migrations/028_story_days.sql"
      ],
      "details": "Add columns: story_day (INT nullable), story_day_label (TEXT), time_transition (TEXT), is_new_story_day (BOOL), story_day_confidence (FLOAT), story_day_is_manual (BOOL), story_day_is_locked (BOOL), timeline_code (VARCHAR DEFAULT 'PRESENT'). Add indexes. Add total_story_days to scripts table. Add column comments."
    },
    {
      "id": 2,
      "description": "Apply migration to Supabase project (twzfaizeyqwevmhjyicz)",
      "agent": "Coder (Backend)",
      "dependencies": [1],
      "effort": "S",
      "files": [],
      "details": "Run migration via Supabase MCP or SQL editor. Verify columns exist on scenes and scripts tables."
    },
    {
      "id": 3,
      "description": "Add get_scene_by_order() helper to SupabaseDB class",
      "agent": "Coder (Backend)",
      "dependencies": [2],
      "effort": "S",
      "files": [
        "backend/db/supabase_client.py"
      ],
      "details": "New method on SupabaseDB: get_scene_by_order(script_id, scene_order) → returns scene dict with id, scene_number, scene_number_original, int_ext, setting, time_of_day, description, story_day, is_new_story_day. Used to fetch Scene X-1 for context injection. Also add get_scenes_ordered(script_id) that returns all scenes ordered by scene_order with story day fields."
    },
    {
      "id": 4,
      "description": "Update enhance_scene() — inject previous scene context into prompt + add story timeline extraction fields",
      "agent": "Coder (Backend)",
      "dependencies": [3],
      "effort": "M",
      "files": [
        "backend/services/scene_enhancer.py"
      ],
      "details": "Three changes to enhance_scene():\n1. Add `prev_scene_context` parameter (optional Dict). If provided, prepend to prompt: 'CONTEXT — PREVIOUS SCENE: Scene X: INT_EXT. SETTING - TIME_OF_DAY\\n  Summary: description'\n2. Add new prompt section **STORY TIMELINE** with fields 17-19: TIME_TRANSITION, IS_NEW_STORY_DAY (bool), TIMELINE_CODE (PRESENT/FLASHBACK/DREAM).\n3. Add these 3 fields to the JSON response format example in the prompt.\n\nAlso update process_scene_candidate() to query the previous scene from DB and pass it to enhance_scene()."
    },
    {
      "id": 5,
      "description": "Update enhance_scene() return dict + extract_fallback() with new story day fields",
      "agent": "Coder (Backend)",
      "dependencies": [4],
      "effort": "S",
      "files": [
        "backend/services/scene_enhancer.py"
      ],
      "details": "Add to the return dict normalization (line ~163-180): time_transition, is_new_story_day, timeline_code. Add same fields with defaults to extract_fallback() (line ~206-223): time_transition='', is_new_story_day=False, timeline_code='PRESENT'."
    },
    {
      "id": 6,
      "description": "Update save_enhanced_scene() to persist new story day columns",
      "agent": "Coder (Backend)",
      "dependencies": [5],
      "effort": "S",
      "files": [
        "backend/services/scene_enhancer.py"
      ],
      "details": "Add to the INSERT statement (line ~259-297): time_transition, is_new_story_day, timeline_code, story_day_confidence. Map from enhancement dict. is_new_story_day is a boolean from AI. story_day_confidence defaults to 0.7 for AI-determined values."
    },
    {
      "id": 7,
      "description": "Update analyze_scene_with_gemini() Supabase path — add prev scene context + story day fields",
      "agent": "Coder (Backend)",
      "dependencies": [3],
      "effort": "M",
      "files": [
        "backend/routes/supabase_routes.py"
      ],
      "details": "Two analysis entry points in supabase_routes.py use analyze_scene_with_gemini():\n1. analyze_scene() endpoint (line ~1993) — single scene analysis from UI button\n2. analyze_scene_internal() (line ~2290) — called from bulk analyze\n\nFor both:\n- Before calling analyze_scene_with_gemini(), query the previous scene (by scene_order - 1) to get its header/time_of_day.\n- Pass prev_context to analyze_scene_with_gemini() as a new parameter.\n- Update analyze_scene_with_gemini() prompt to include prev context + story timeline fields.\n- Add time_transition, is_new_story_day, timeline_code to the update_data dict that writes back to Supabase."
    },
    {
      "id": 8,
      "description": "Create story_day_service.py with recalculate_story_days()",
      "agent": "Coder (Backend)",
      "dependencies": [3],
      "effort": "M",
      "files": [
        "backend/services/story_day_service.py"
      ],
      "details": "New service file with:\n\n1. recalculate_story_days(script_id, start_from_order=0)\n   - Fetches all scenes ordered by scene_order via SupabaseDB\n   - Iterates sequentially, incrementing day counter when is_new_story_day=True\n   - Respects story_day_is_locked (resets counter to locked value)\n   - Handles timeline_code (FLASHBACK/DREAM get labeled differently)\n   - Batch updates story_day, story_day_label for all affected scenes\n   - Updates scripts.total_story_days\n\n2. get_story_day_summary(script_id)\n   - Returns {total_days, scenes_per_day, timeline_breakdown}\n\nUses Supabase client (from db.supabase_client import db)."
    },
    {
      "id": 9,
      "description": "Wire recalculate_story_days() into post-enhancement and bulk analyze completion",
      "agent": "Coder (Backend)",
      "dependencies": [8, 6, 7],
      "effort": "S",
      "files": [
        "backend/services/scene_enhancer.py",
        "backend/routes/supabase_routes.py"
      ],
      "details": "Three wiring points:\n1. scene_enhancer.py → process_all_candidates(): After the enhancement loop completes, call recalculate_story_days(script_id).\n2. supabase_routes.py → analyze_scene() endpoint: After single-scene analysis completes, call recalculate_story_days(script_id, start_from_order=scene.scene_order).\n3. supabase_routes.py → bulk analyze job completion: After all scenes in a bulk job are analyzed, call recalculate_story_days(script_id)."
    },
    {
      "id": 10,
      "description": "Verify: upload a test script and confirm story_day, time_transition, timeline_code are populated",
      "agent": "Tester",
      "dependencies": [9],
      "effort": "S",
      "files": [],
      "details": "Manual verification:\n1. Upload a PDF script with clear day transitions (NIGHT→MORNING, 'THE NEXT DAY', CONTINUOUS).\n2. Trigger scene analysis (single + bulk).\n3. Query scenes table — verify time_transition, is_new_story_day, timeline_code columns are populated.\n4. Verify recalculate_story_days() ran — story_day integers should increment correctly.\n5. Verify scripts.total_story_days is updated.\n6. Check edge case: re-analyze a single scene and verify cascade recalculation updates subsequent scenes."
    }
  ]
}
```

---

## Dependency Graph

```
[1] Migration SQL
 └──► [2] Apply to Supabase
       └──► [3] get_scene_by_order() helper
             ├──► [4] enhance_scene() prompt update ──► [5] Return dict update ──► [6] save_enhanced_scene() update ──┐
             ├──► [7] analyze_scene_with_gemini() update ──────────────────────────────────────────────────────────────┤
             └──► [8] story_day_service.py ────────────────────────────────────────────────────────────────────────────┤
                                                                                                                      ▼
                                                                                                                [9] Wire triggers
                                                                                                                      │
                                                                                                                      ▼
                                                                                                               [10] Verify
```

---

## Files Modified (Summary)

| File | Change Type | Subtask |
|------|-------------|---------|
| `backend/db/migrations/028_story_days.sql` | **New** | 1 |
| `backend/db/supabase_client.py` | Modified — add 2 helper methods | 3 |
| `backend/services/scene_enhancer.py` | Modified — prompt, return dict, save logic, wiring | 4, 5, 6, 9 |
| `backend/services/story_day_service.py` | **New** — recalculation service | 8 |
| `backend/routes/supabase_routes.py` | Modified — prev context injection, new fields in update | 7, 9 |

---

## Estimated Total Effort

- **5 Small** tasks (~30 min each): 2.5 hours
- **3 Medium** tasks (~1 hour each): 3 hours
- **Total**: ~5.5 hours

---

## Acceptance Criteria

- [x] `scenes` table has all 8 new columns (`story_day`, `story_day_label`, `time_transition`, `is_new_story_day`, `story_day_confidence`, `story_day_is_manual`, `story_day_is_locked`, `timeline_code`)
- [x] `scripts` table has `total_story_days` column
- [x] AI prompt includes previous scene context (header + time_of_day + description)
- [x] AI prompt extracts `time_transition`, `is_new_story_day`, `timeline_code`
- [x] `save_enhanced_scene()` persists all new fields
- [x] `analyze_scene_with_gemini()` (Supabase path) persists all new fields
- [x] `recalculate_story_days()` service exists and correctly assigns sequential day numbers
- [x] Recalculation respects `story_day_is_locked` values
- [x] Recalculation handles `timeline_code` (FLASHBACK/DREAM get labeled differently)
- [x] Recalculation is triggered after: full enhancement, single-scene analysis, bulk analysis
- [x] `scripts.total_story_days` is updated after recalculation
- [ ] No regressions — existing scene analysis still works for scripts without story day data (requires live test)
