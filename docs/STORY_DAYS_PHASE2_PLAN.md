# Story Days — Phase 2 Task Decomposition

**Ticket**: Story Days Feature — Phase 2: Cascade Updates + Manual Editing + UI Display
**Source Spec**: `docs/STORY_DAYS_BRAINSTORM.md` → Phase 2
**Depends On**: Phase 1 (✅ Completed — migration 028, story_day_service.py, AI prompt injection)
**Branch**: `feature/story-days-phase2`

---

## Task Graph

```json
{
  "ticket_id": "story-days-phase2",
  "title": "Story Days — Phase 2: Cascade Updates + Manual Editing + UI Display",
  "subtasks": [
    {
      "id": 1,
      "description": "Include story day fields in get_scenes() and get_scenes_for_management() API responses",
      "agent": "Coder (Backend)",
      "dependencies": [],
      "effort": "S",
      "files": [
        "backend/routes/supabase_routes.py"
      ],
      "details": "Add story_day, story_day_label, time_transition, is_new_story_day, story_day_confidence, story_day_is_manual, story_day_is_locked, timeline_code to both get_scenes() and get_scenes_for_management() response dicts. Also add total_story_days to the script object in management response."
    },
    {
      "id": 2,
      "description": "Create story day management API endpoints (toggle, lock, set, calculate, summary, bulk-update)",
      "agent": "Coder (Backend)",
      "dependencies": [],
      "effort": "M",
      "files": [
        "backend/routes/supabase_routes.py"
      ],
      "details": "Add 6 endpoints per brainstorm spec §API: PATCH toggle-new-day (flips is_new_story_day + sets story_day_is_manual=true + triggers recalc), PATCH lock-story-day (toggles story_day_is_locked), PATCH timeline-code (sets timeline_code + triggers recalc), PATCH story-day (manual set story_day + lock + recalc), POST calculate (triggers full recalculate_story_days), GET summary (calls get_story_day_summary). Also POST bulk-update for multi-scene story day assignment. All mutation endpoints must trigger recalculate_story_days(script_id, start_from_order=scene_order)."
    },
    {
      "id": 3,
      "description": "Wire cascade recalculation into existing scene-modifying endpoints (delete, reorder, split, merge, add)",
      "agent": "Coder (Backend)",
      "dependencies": [],
      "effort": "S",
      "files": [
        "backend/routes/supabase_routes.py"
      ],
      "details": "Add recalculate_story_days(script_id) call (wrapped in try/except, non-fatal) at the end of: delete_scene(), reorder_scenes(), split_scene(), merge_scenes(), create_scene(). This ensures story day numbering stays consistent when scenes are structurally modified."
    },
    {
      "id": 4,
      "description": "Add story day API functions to frontend apiService.js",
      "agent": "Coder (Frontend)",
      "dependencies": [2],
      "effort": "S",
      "files": [
        "frontend/src/services/apiService.js"
      ],
      "details": "Add functions: toggleNewDay(scriptId, sceneId), lockStoryDay(scriptId, sceneId, locked), setTimelineCode(scriptId, sceneId, code), setStoryDay(scriptId, sceneId, day), calculateStoryDays(scriptId), getStoryDaySummary(scriptId), bulkUpdateStoryDays(scriptId, updates). Each wraps the corresponding API endpoint."
    },
    {
      "id": 5,
      "description": "Add story day badge to SceneDetail header",
      "agent": "Coder (Frontend)",
      "dependencies": [1],
      "effort": "S",
      "files": [
        "frontend/src/components/scenes/SceneDetail.jsx",
        "frontend/src/components/scenes/SceneDetail.css"
      ],
      "details": "In the scene-header-row (next to shot_type badge and parse_method badge), add a story day badge pill showing story_day_label (e.g., 'Day 1', 'Flashback — Day 3'). Use CalendarDays icon from lucide-react. Color: teal/cyan for PRESENT, purple for FLASHBACK, blue for DREAM. Also show time_transition as a subtle label below the header if present (e.g., 'THE NEXT MORNING'). Show timeline_code as a small indicator if not PRESENT."
    },
    {
      "id": 6,
      "description": "Add story day badge to SceneList items",
      "agent": "Coder (Frontend)",
      "dependencies": [1],
      "effort": "S",
      "files": [
        "frontend/src/components/scenes/SceneList.jsx",
        "frontend/src/components/scenes/SceneList.css"
      ],
      "details": "Add a compact 'D1', 'D2' badge in each scene-item card (top-right or next to scene number). Color-code by story day (use a rotating palette of 6-8 distinct hues so adjacent days are visually distinct). Add a day separator divider between scenes when story_day changes (similar to existing transition dividers). Show 'New Day' indicator on scenes where is_new_story_day=true."
    },
    {
      "id": 7,
      "description": "Add story day column + New Day toggle to SceneManager table",
      "agent": "Coder (Frontend)",
      "dependencies": [1, 4],
      "effort": "M",
      "files": [
        "frontend/src/components/scenes/SceneManager.jsx",
        "frontend/src/components/scenes/SceneManager.css"
      ],
      "details": "Add a 'Story Day' column to the management table showing story_day_label. Add a toggle switch for 'New Day' (is_new_story_day) — clicking it calls toggleNewDay() and refreshes. Add a lock/unlock icon button for story_day_is_locked — clicking it calls lockStoryDay(). Add a timeline_code dropdown selector (PRESENT, FLASHBACK, DREAM, FANTASY, MONTAGE, TITLE_CARD) — changing it calls setTimelineCode(). All mutations should refresh the scene list after recalculation completes. Include total_story_days in the management header stats."
    },
    {
      "id": 8,
      "description": "Add story day bulk assign UI to SceneManager",
      "agent": "Coder (Frontend)",
      "dependencies": [4, 7],
      "effort": "M",
      "files": [
        "frontend/src/components/scenes/SceneManager.jsx",
        "frontend/src/components/scenes/SceneManager.css"
      ],
      "details": "When multiple scenes are selected (existing multi-select infrastructure), add a 'Set Story Day' bulk action button. Opens a small modal/popover with: story_day number input, is_new_story_day toggle, timeline_code selector. Submits via bulkUpdateStoryDays(). Also add a 'Calculate Story Days' button in the toolbar that calls calculateStoryDays() for scripts that haven't been analyzed yet or need re-calculation."
    },
    {
      "id": 9,
      "description": "Add story day filter to SceneViewer sidebar",
      "agent": "Coder (Frontend)",
      "dependencies": [1, 6],
      "effort": "S",
      "files": [
        "frontend/src/components/scenes/SceneViewer.jsx"
      ],
      "details": "Add a 'Story Days' filter dropdown or tab in the SceneViewer sidebar (alongside existing Characters/Locations tabs). When a day is selected, filter the scene list to show only scenes from that story day. Show day count badge in the filter."
    },
    {
      "id": 10,
      "description": "Verify end-to-end: story day display + manual editing + cascade recalculation",
      "agent": "Tester",
      "dependencies": [1, 2, 3, 4, 5, 6, 7, 8, 9],
      "effort": "M",
      "files": [],
      "details": "Test scenarios: (A) Upload script → analyze → verify story day badges appear in SceneList and SceneDetail. (B) Toggle 'New Day' on a mid-script scene → verify cascade updates all subsequent scenes. (C) Lock a story day → verify recalculation respects it. (D) Change timeline_code to FLASHBACK → verify label changes. (E) Split a scene → verify story days recalculate. (F) Delete a scene → verify story days recalculate. (G) Reorder scenes → verify story days recalculate. (H) Bulk assign story days → verify. (I) Filter by story day in SceneViewer."
    }
  ]
}
```

---

## Dependency Graph

```
[1] get_scenes() fields ────────────────────────────┐
                                                     ├──→ [5] SceneDetail badge
[2] Story day API endpoints ──→ [4] apiService.js ──├──→ [6] SceneList badge
                                                     ├──→ [7] SceneManager column + toggles
[3] Cascade wiring ────────────────────────────────  │    │
                                                     │    └──→ [8] Bulk assign UI
                                                     │
                                                     └──→ [9] Story day filter
                                                     
                                                     All ──→ [10] Verify
```

---

## Files Modified (Summary)

| File | Change Type | Subtask |
|------|-------------|---------|
| `backend/routes/supabase_routes.py` | Modified — add story day fields to responses, add 6+ endpoints, wire cascade | 1, 2, 3 |
| `frontend/src/services/apiService.js` | Modified — add 7 story day API functions | 4 |
| `frontend/src/components/scenes/SceneDetail.jsx` | Modified — story day badge in header | 5 |
| `frontend/src/components/scenes/SceneDetail.css` | Modified — badge styling | 5 |
| `frontend/src/components/scenes/SceneList.jsx` | Modified — day badge, day separators | 6 |
| `frontend/src/components/scenes/SceneList.css` | Modified — badge + separator styling | 6 |
| `frontend/src/components/scenes/SceneManager.jsx` | Modified — story day column, toggles, bulk assign | 7, 8 |
| `frontend/src/components/scenes/SceneManager.css` | Modified — new column + control styling | 7, 8 |
| `frontend/src/components/scenes/SceneViewer.jsx` | Modified — story day filter | 9 |

---

## Estimated Total Effort

- **5 Small** tasks (~30 min each): 2.5 hours
- **4 Medium** tasks (~1 hour each): 4 hours
- **Total**: ~6.5 hours

---

## Acceptance Criteria

- [ ] `get_scenes()` response includes all 8 story day fields per scene
- [ ] `get_scenes_for_management()` response includes story day fields + total_story_days on script
- [ ] All 6 story day management endpoints work (toggle, lock, set, calculate, summary, bulk)
- [ ] All mutation endpoints trigger `recalculate_story_days()` with correct `start_from_order`
- [ ] Existing scene-modifying endpoints (delete, reorder, split, merge, add) trigger recalculation
- [ ] SceneDetail shows story day badge with correct label and color
- [ ] SceneList shows compact day badge per scene + day separator dividers
- [ ] SceneManager table has Story Day column with toggle, lock, and timeline selector
- [ ] SceneManager supports bulk story day assignment via multi-select
- [ ] SceneViewer has story day filter in sidebar
- [ ] Cascade recalculation works: toggling "New Day" on Scene 5 updates Scenes 6-N
- [ ] Locked days are respected: recalculation resets counter at locked scenes
- [ ] No regressions — existing scene management operations still work
