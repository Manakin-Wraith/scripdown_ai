# Customizable Report Filtering — Feature Spec

> **Status:** All Phases (1–4) Complete  
> **Author:** Cascade + User Brainstorm  
> **Date:** 2026-02-11  
> **Priority:** High  
> **Estimated Effort:** ~10–12 hours across 4 phases

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current State Analysis](#current-state-analysis)
3. [Filter Dimensions](#filter-dimensions)
4. [Production Use Cases](#production-use-cases)
5. [Architecture](#architecture)
   - [Filter Schema](#filter-schema)
   - [Backend Pipeline](#backend-pipeline)
   - [Frontend UX](#frontend-ux)
6. [Implementation Phases](#implementation-phases)
   - [Phase 1: Backend Filter Engine](#phase-1-backend-filter-engine)
   - [Phase 2: Frontend Filter Panel](#phase-2-frontend-filter-panel)
   - [Phase 3: Grouped Report Renderers](#phase-3-grouped-report-renderers)
   - [Phase 4: Saved Filter Presets](#phase-4-saved-filter-presets)
7. [API Changes](#api-changes)
8. [Database Changes](#database-changes)
9. [Files to Create/Modify](#files-to-createmodify)
10. [Edge Cases & Constraints](#edge-cases--constraints)
11. [Testing Plan](#testing-plan)

---

## Problem Statement

Production departments need reports filtered by **cross-dimensional criteria** — e.g., "all props required at a specific location across multiple scenes" or "wardrobe needs for Character X on Story Day 3." The current reporting system generates reports for the **entire script** with no filtering, grouping, or cross-referencing capabilities.

---

## Current State Analysis

### What Exists

| Component | Status |
|-----------|--------|
| `ReportConfig.filter` dict with `scene_numbers`, `characters`, `locations` keys | **Defined but never consumed** |
| `aggregate_scene_data()` — fetches ALL scenes, aggregates ALL categories | **No filter parameter** |
| `ReportBuilder.jsx` — report type picker + custom title | **No filter UI** |
| Cross-reference data (props → scenes, characters → story_days, locations → INT/EXT) | **Available in aggregation** |
| `ReportConfig.group_by` field | **Defined but never used in rendering** |
| Department presets (`PRESET_WARDROBE`, `PRESET_PROPS`, etc.) | **Exist but don't filter scenes** |

### Key Files

- `backend/services/report_service.py` — `ReportService`, `ReportConfig`, `aggregate_scene_data()`
- `backend/routes/report_routes.py` — API endpoints for generate/preview/PDF/share
- `frontend/src/components/reports/ReportBuilder.jsx` — Report generation UI
- `frontend/src/services/apiService.js` — Frontend API methods

---

## Filter Dimensions

All dimensions are **already available** in the scene data model:

| Dimension | Source Field | Type | Example Values |
|-----------|-------------|------|----------------|
| **Location** | `scene.setting` | Multi-select | "HOSPITAL - ICU", "JOHN'S HOUSE" |
| **Location Hierarchy** | `scene.location_hierarchy` | Multi-select (parent) | "HOSPITAL" (parent of ICU, LOBBY, etc.) |
| **INT/EXT** | `scene.int_ext` | Toggle | INT, EXT |
| **Time of Day** | `scene.time_of_day` | Toggle | DAY, NIGHT, DAWN, DUSK |
| **Story Day** | `scene.story_day` | Multi-select chips | D1, D2, D3… |
| **Character** | `scene.characters[]` | Searchable multi-select | "SARAH", "JOHN" |
| **Scene Numbers** | `scene.scene_number` | Multi-select or range | "1", "5A", "12" |
| **Scene Range** | Computed from scene_number | Range (from/to) | 1–20 |
| **Timeline Code** | `scene.timeline_code` | Multi-select | PRESENT, FLASHBACK, DREAM, FANTASY, MONTAGE |
| **Category** | Breakdown arrays on scene | Checkboxes | props, wardrobe, makeup, vehicles, etc. |

---

## Production Use Cases

These are real workflows that department heads perform daily during pre-production:

### Props Department
- "All props needed at THE BEACH across all scenes"
- "Props for scenes 1–20 only" (for the first week's shoot)
- "Props needed on Story Day 3"

### Wardrobe Department
- "What does SARAH wear in each scene?"
- "All wardrobe items for INT scenes at JOHN'S HOUSE"
- "Wardrobe continuity for Story Day 1 → Day 2"

### Makeup & Hair
- "All makeup requirements for NIGHT scenes"
- "Makeup for CHARACTER X across the full script"

### Locations Department
- "All INT scenes at HOSPITAL — what departments need to prep?"
- "EXT DAY scenes only — for outdoor scheduling"

### Director / 1st AD
- "Full breakdown for scenes 45–60" (for a specific shooting block)
- "All FLASHBACK scenes — who's in them, what's needed?"
- "Everything needed at LOCATION X on Story Day 5"

### Production Designer
- "All vehicles + props + set dressing for POLICE STATION"
- "SFX requirements grouped by location"

---

## Architecture

### Filter Schema

Extends the existing `ReportConfig.filter` structure:

```json
{
  "filter": {
    "locations": ["HOSPITAL", "JOHN'S HOUSE - KITCHEN"],
    "location_parents": ["HOSPITAL"],
    "characters": ["SARAH", "JOHN"],
    "int_ext": ["INT"],
    "time_of_day": ["NIGHT"],
    "story_days": [1, 2, 3],
    "scene_numbers": ["1", "2", "5A"],
    "scene_range": { "from": "1", "to": "20" },
    "timeline_codes": ["PRESENT"],
    "exclude_omitted": true
  },
  "categories": ["props", "wardrobe", "characters"],
  "group_by": "location",
  "sort_by": "scene_number"
}
```

**Filter logic:** All filters are AND-combined. Multiple values within a single filter are OR-combined.

Example: `locations: ["HOSPITAL", "BEACH"]` + `time_of_day: ["NIGHT"]` =
*"Scenes at HOSPITAL **or** BEACH that are NIGHT"*

### Backend Pipeline

```
┌──────────────┐
│ Fetch Scenes  │  ← All scenes for script_id
└──────┬───────┘
       │
┌──────▼───────┐
│ Filter Scenes │  ← Apply location/character/int_ext/story_day/etc. filters
└──────┬───────┘
       │
┌──────▼────────────┐
│ Aggregate Filtered │  ← Only aggregate matching scenes (same logic, smaller set)
└──────┬────────────┘
       │
┌──────▼───────┐
│ Group Results │  ← Group by location/character/story_day/scene if requested
└──────┬───────┘
       │
┌──────▼───────┐
│ Render Report │  ← HTML/PDF with sections per group
└──────────────┘
```

**Key method additions to `ReportService`:**

```python
def _filter_scenes(self, scenes: List[Dict], filters: Dict) -> List[Dict]:
    """
    Filter scenes based on criteria. All filters AND-combined.
    Multiple values within a filter are OR-combined.
    Returns subset of scenes matching all active filters.
    """

def _group_items(self, aggregated_data: Dict, group_by: str) -> Dict:
    """
    Re-organize aggregated data into groups.
    Returns: { group_key: { items_in_that_group } }
    """

def get_filter_options(self, script_id: str) -> Dict:
    """
    Return unique values for each filter dimension.
    Used by frontend to populate dropdowns.
    """

def aggregate_scene_data(self, script_id: str, filters: Dict = None) -> Dict:
    """
    Modified: apply filters before aggregation if provided.
    Adds 'filter_summary' to response with counts.
    """
```

### Frontend UX

#### Layout: Split-Panel ReportBuilder

```
┌─────────────────────────────────────────────────────────┐
│  Generate Reports                                        │
├─────────────────────┬───────────────────────────────────┤
│                     │                                    │
│  REPORT TYPE        │  PREVIEW                           │
│  ☐ Scene Breakdown  │  ┌──────────────────────────────┐ │
│  ☐ Props            │  │ Showing 15 of 120 scenes     │ │
│  ☐ Wardrobe         │  │ Props: 23 items              │ │
│  ☐ ...              │  │ Locations: 3                  │ │
│                     │  └──────────────────────────────┘ │
│  ─────────────────  │                                    │
│  FILTERS            │  ┌──────────────────────────────┐ │
│                     │  │ Preview Table (top 10)       │ │
│  Location ▼         │  │ ...                          │ │
│  [HOSPITAL] [×]     │  └──────────────────────────────┘ │
│                     │                                    │
│  Character ▼        │  ┌──────────────────────────────┐ │
│  [All]              │  │ [Generate Report]             │ │
│                     │  │ [Clear All Filters]           │ │
│  INT/EXT            │  └──────────────────────────────┘ │
│  [ALL] [INT] [EXT]  │                                    │
│                     │                                    │
│  Time of Day        │                                    │
│  [ALL][DAY][NIGHT]  │                                    │
│                     │                                    │
│  Story Days         │                                    │
│  [D1][D2][D3]...    │                                    │
│                     │                                    │
│  Scene Range        │                                    │
│  [From: ___] [To: ] │                                    │
│                     │                                    │
│  ─────────────────  │                                    │
│  CATEGORIES         │                                    │
│  ☑ Characters       │                                    │
│  ☑ Props            │                                    │
│  ☐ Wardrobe         │                                    │
│  ☐ Makeup           │                                    │
│  ☐ ...              │                                    │
│                     │                                    │
│  GROUP BY           │                                    │
│  ○ Scene Number     │                                    │
│  ● Location         │                                    │
│  ○ Character        │                                    │
│  ○ Story Day        │                                    │
│                     │                                    │
│  ─────────────────  │                                    │
│  PRESETS            │                                    │
│  [Save Filter] [▼]  │                                    │
│                     │                                    │
└─────────────────────┴───────────────────────────────────┘
```

#### Smart Defaults Per Report Type

| Report Type | Auto-Selected Categories | Suggested Group By |
|-------------|--------------------------|-------------------|
| Props | props | location |
| Wardrobe | wardrobe, characters | character |
| Makeup | makeup, characters | character |
| SFX | special_effects | scene_number |
| Location | all | location |
| Day Out of Days | characters | story_day |
| Scene Breakdown | all | scene_number |
| Stunts | stunts, characters | scene_number |
| Vehicles | vehicles | location |
| Animals | animals | location |
| Extras | extras | location |

#### New Component: `ReportFilterPanel.jsx`

- Collapsible/expandable sidebar
- Populated from `/filter-options` endpoint on mount
- Multi-select dropdowns with search (for locations, characters)
- Toggle pill buttons (for INT/EXT, time_of_day)
- Chip-style selectors (for story days)
- Range inputs (for scene range)
- Checkbox grid (for categories)
- Radio buttons (for group_by)
- "Clear All Filters" button
- Active filter count badge
- Client-side filtering of preview data for instant feedback

---

## Implementation Phases

### Phase 1: Backend Filter Engine

**Scope:** Foundation — filter pipeline, filter-options endpoint, wiring into existing endpoints.

**Effort:** ~2–3 hours

**Changes to `report_service.py`:**

1. **Add `_filter_scenes(scenes, filters)` method:**
   ```python
   def _filter_scenes(self, scenes, filters):
       if not filters:
           return scenes
       
       filtered = scenes
       
       # Location filter (OR within, AND with others)
       if filters.get('locations'):
           locs = [l.upper() for l in filters['locations']]
           filtered = [s for s in filtered if s.get('setting', '').upper() in locs]
       
       # Location parent filter (matches if location_hierarchy contains parent)
       if filters.get('location_parents'):
           parents = [p.upper() for p in filters['location_parents']]
           filtered = [s for s in filtered 
                       if any(p in (s.get('location_hierarchy') or []) for p in parents)
                       or s.get('setting', '').upper() in parents]
       
       # Character filter (scene must contain at least one of the characters)
       if filters.get('characters'):
           chars = [c.upper() for c in filters['characters']]
           filtered = [s for s in filtered 
                       if any(c.upper() in chars for c in (s.get('characters') or []))]
       
       # INT/EXT filter
       if filters.get('int_ext'):
           filtered = [s for s in filtered if s.get('int_ext') in filters['int_ext']]
       
       # Time of day filter
       if filters.get('time_of_day'):
           filtered = [s for s in filtered if s.get('time_of_day') in filters['time_of_day']]
       
       # Story day filter
       if filters.get('story_days'):
           filtered = [s for s in filtered if s.get('story_day') in filters['story_days']]
       
       # Scene numbers filter
       if filters.get('scene_numbers'):
           filtered = [s for s in filtered if s.get('scene_number') in filters['scene_numbers']]
       
       # Scene range filter
       if filters.get('scene_range'):
           sr = filters['scene_range']
           # Numeric comparison with fallback for letter suffixes (5A, 12B)
           filtered = [s for s in filtered if _in_scene_range(s.get('scene_number', ''), sr)]
       
       # Timeline code filter
       if filters.get('timeline_codes'):
           filtered = [s for s in filtered 
                       if s.get('timeline_code', 'PRESENT') in filters['timeline_codes']]
       
       # Exclude omitted scenes (default True)
       if filters.get('exclude_omitted', True):
           filtered = [s for s in filtered if not s.get('is_omitted')]
       
       return filtered
   ```

2. **Modify `aggregate_scene_data(script_id, filters=None)`:**
   - After fetching scenes, call `_filter_scenes(scenes, filters)` before aggregation loop
   - Add `filter_summary` to return dict:
     ```python
     'filter_summary': {
         'total_scenes': len(all_scenes),
         'filtered_scenes': len(filtered_scenes),
         'active_filters': [k for k, v in (filters or {}).items() if v]
     }
     ```

3. **Add `get_filter_options(script_id)` method:**
   ```python
   def get_filter_options(self, script_id):
       scenes = self.db.get_scenes(script_id)
       return {
           'locations': sorted(set(s.get('setting', '') for s in scenes if s.get('setting'))),
           'location_parents': sorted(set(
               h[0] for s in scenes 
               for h in [s.get('location_hierarchy') or []] 
               if len(h) > 1
           )),
           'characters': sorted(set(
               c if isinstance(c, str) else c.get('name', '')
               for s in scenes 
               for c in (s.get('characters') or [])
           )),
           'int_ext_values': sorted(set(s.get('int_ext', '') for s in scenes if s.get('int_ext'))),
           'time_of_day_values': sorted(set(s.get('time_of_day', '') for s in scenes if s.get('time_of_day'))),
           'story_days': sorted(set(s.get('story_day') for s in scenes if s.get('story_day'))),
           'timeline_codes': sorted(set(s.get('timeline_code', 'PRESENT') for s in scenes)),
           'scene_numbers': [s.get('scene_number') for s in scenes],
           'total_scenes': len(scenes)
       }
   ```

**Changes to `report_routes.py`:**

4. **New endpoint: `GET /api/reports/scripts/:id/filter-options`**
5. **Modify `generate_report` and `preview_report`** to accept `filters` in request body and pass to `aggregate_scene_data()`

### Phase 2: Frontend Filter Panel

**Scope:** New filter panel component, wire into ReportBuilder, live preview updates.

**Effort:** ~3–4 hours

**New file: `frontend/src/components/reports/ReportFilterPanel.jsx`**

Key features:
- Fetches filter options from new endpoint on mount
- Multi-select dropdown for locations (with search)
- Multi-select dropdown for characters (with search)
- Toggle pill buttons for INT/EXT
- Toggle pill buttons for time of day
- Chip-style multi-select for story days
- From/To inputs for scene range
- Checkbox grid for breakdown categories
- Radio buttons for group_by
- Active filter count badge
- "Clear All" button
- Emits `onFilterChange(filters)` callback

**Modifications to `ReportBuilder.jsx`:**
- Import and render `ReportFilterPanel` in a split-panel layout
- Pass filter state to `previewReport()` calls
- Pass filter state to `generateReport()` calls
- Show filter summary in preview section ("Showing X of Y scenes")
- Apply smart defaults when report type changes

**New file: `frontend/src/components/reports/ReportFilterPanel.css`**

### Phase 3: Grouped Report Renderers

**Scope:** New render methods that section reports by group dimension.

**Effort:** ~2–3 hours

**New method: `_render_grouped_report(data, group_by, categories)`**

Grouping logic:
- **By Location:** Each unique `setting` becomes a section header. Under it: all breakdown items from scenes at that location.
- **By Character:** Each character becomes a section. Under it: scenes they appear in with relevant breakdown items.
- **By Story Day:** Each story day becomes a section. Under it: all scenes and items needed that day.
- **By Scene Number:** Default behavior — sequential scene-by-scene (existing behavior, but now with category filtering).

Output structure per group:
```html
<div class="report-group">
    <h3 class="group-header">HOSPITAL - ICU</h3>
    <p class="group-meta">4 scenes · INT · DAY/NIGHT · Story Days: D1, D3</p>
    <table>
        <!-- Only selected categories shown -->
        <tr><td>Scene 5</td><td>Props: Stethoscope, Chart</td></tr>
        <tr><td>Scene 12</td><td>Props: IV Drip, Monitors</td></tr>
    </table>
</div>
```

PDF rendering: page break between groups when printed.

### Phase 4: Saved Filter Presets

**Scope:** Persistence layer for reusable filter configurations.

**Effort:** ~1–2 hours

**New table: `report_filter_presets`**

```sql
CREATE TABLE report_filter_presets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    script_id UUID REFERENCES scripts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    filters JSONB NOT NULL DEFAULT '{}',
    categories JSONB DEFAULT '[]',
    group_by TEXT,
    sort_by TEXT DEFAULT 'scene_number',
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Default presets (seeded, `is_default = true`, no user_id):**

| Preset Name | Filters | Categories | Group By |
|-------------|---------|------------|----------|
| Props Master's View | none | props | location |
| Wardrobe Supervisor | none | wardrobe, characters | character |
| Location Manager | none | all | location |
| 1st AD Shooting Block | scene_range | all | story_day |
| Makeup & Hair HOD | none | makeup, characters | character |
| Stunt Coordinator | none | stunts, characters | scene_number |
| VFX Supervisor | none | special_effects | scene_number |
| Transport Captain | none | vehicles | location |

**API endpoints:**
- `GET /api/reports/scripts/:id/filter-presets` — Get presets (default + user's)
- `POST /api/reports/scripts/:id/filter-presets` — Save new preset
- `DELETE /api/reports/filter-presets/:id` — Delete user preset

**Frontend:**
- Preset dropdown in `ReportFilterPanel`
- "Save Current Filter" button
- Loading a preset populates all filter fields

---

## API Changes

### New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/reports/scripts/:id/filter-options` | Unique filter values for dropdowns |
| `GET` | `/api/reports/scripts/:id/filter-presets` | Saved filter presets |
| `POST` | `/api/reports/scripts/:id/filter-presets` | Save new preset |
| `DELETE` | `/api/reports/filter-presets/:id` | Delete preset |

### Modified Endpoints

| Method | Path | Change |
|--------|------|--------|
| `POST` | `/api/reports/scripts/:id/reports/generate` | Accept `filters`, `categories`, `group_by` in body |
| `POST` | `/api/reports/scripts/:id/reports/preview` | Accept `filters`, `categories`, `group_by` in body |

### Updated Request Body (generate/preview)

```json
{
    "report_type": "props",
    "title": "Props for Hospital Scenes",
    "config": {},
    "filters": {
        "locations": ["HOSPITAL - ICU", "HOSPITAL - LOBBY"],
        "int_ext": ["INT"],
        "story_days": [1, 2]
    },
    "categories": ["props", "characters"],
    "group_by": "location",
    "sort_by": "scene_number"
}
```

---

## Database Changes

### Phase 4 Only: New Table

```sql
-- Migration: XXX_report_filter_presets.sql
CREATE TABLE report_filter_presets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    script_id UUID REFERENCES scripts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    filters JSONB NOT NULL DEFAULT '{}',
    categories JSONB DEFAULT '[]',
    group_by TEXT,
    sort_by TEXT DEFAULT 'scene_number',
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS
ALTER TABLE report_filter_presets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own presets"
ON report_filter_presets FOR ALL
USING (user_id = auth.uid() OR is_default = TRUE);

-- Index
CREATE INDEX idx_filter_presets_script ON report_filter_presets(script_id);
CREATE INDEX idx_filter_presets_user ON report_filter_presets(user_id);
```

### No Schema Changes for Phases 1–3

All filter data already exists on the `scenes` table. No new columns needed.

---

## Files to Create/Modify

### Phase 1 (Backend)

| Action | File |
|--------|------|
| **Modify** | `backend/services/report_service.py` — Add `_filter_scenes()`, `get_filter_options()`, modify `aggregate_scene_data()` |
| **Modify** | `backend/routes/report_routes.py` — Add `/filter-options` endpoint, modify generate/preview to accept filters |

### Phase 2 (Frontend)

| Action | File |
|--------|------|
| **Create** | `frontend/src/components/reports/ReportFilterPanel.jsx` |
| **Create** | `frontend/src/components/reports/ReportFilterPanel.css` |
| **Modify** | `frontend/src/components/reports/ReportBuilder.jsx` — Split-panel layout, integrate filter panel |
| **Modify** | `frontend/src/components/reports/ReportBuilder.css` — Layout changes |
| **Modify** | `frontend/src/services/apiService.js` — Add `getFilterOptions()`, update `generateReport()` and `previewReport()` signatures |

### Phase 3 (Grouped Renderers)

| Action | File |
|--------|------|
| **Modify** | `backend/services/report_service.py` — Add `_render_grouped_report()`, `_group_items()` |

### Phase 4 (Presets)

| Action | File |
|--------|------|
| **Create** | `backend/db/migrations/XXX_report_filter_presets.sql` |
| **Modify** | `backend/routes/report_routes.py` — Preset CRUD endpoints |
| **Modify** | `frontend/src/components/reports/ReportFilterPanel.jsx` — Preset dropdown + save |
| **Modify** | `frontend/src/services/apiService.js` — Preset API methods |

---

## Edge Cases & Constraints

### Filtering

- **Empty filter result:** If filters produce 0 matching scenes, show a clear message: "No scenes match your filters. Try broadening your criteria."
- **Scene number ranges with letters:** Scene numbers like "5A", "12B" need numeric prefix extraction for range filtering. Use `int(re.match(r'\d+', scene_num).group())` for comparison.
- **Location hierarchy matching:** `location_parents: ["HOSPITAL"]` should match scenes at "HOSPITAL - ICU", "HOSPITAL - LOBBY", "HOSPITAL" (exact). Use prefix matching or hierarchy array membership.
- **Character name normalization:** Compare uppercase. Handle `(CONT'D)`, `(V.O.)` suffixes — match on base name.
- **OR within, AND across:** `locations: [A, B]` + `characters: [X]` = scenes at A or B that also have character X.

### Performance

- **Large scripts (200+ scenes):** Filter-then-aggregate is still fast since all data is in memory. No extra DB queries.
- **Client-side preview filtering:** For instant feedback, filter the already-fetched preview data client-side. Only hit the server for final report generation.
- **Filter options caching:** Cache `/filter-options` response in frontend state — it doesn't change unless scenes are re-analyzed.

### UX

- **Filter persistence across type changes:** When user switches report type, preserve existing filters but update smart defaults for categories/group_by.
- **URL state:** Consider encoding active filters in URL query params so filtered report views are shareable/bookmarkable.
- **Mobile/tablet:** Filter panel should collapse to a bottom sheet or modal on smaller screens.

---

## Testing Plan

### Backend Unit Tests

| Test | Description |
|------|-------------|
| `test_filter_by_location` | Filter scenes to specific location, verify only matching scenes returned |
| `test_filter_by_character` | Filter by character, verify scenes containing that character |
| `test_filter_by_int_ext` | Filter INT only, verify no EXT scenes |
| `test_filter_by_story_day` | Filter specific story days |
| `test_filter_by_scene_range` | Range 1–20, verify scene numbers within range (including "5A") |
| `test_filter_combined` | Multiple filters AND-combined |
| `test_filter_empty_result` | Filters that match nothing return empty with correct summary |
| `test_filter_none_passthrough` | No filters = all scenes (backward compatible) |
| `test_aggregate_with_filters` | Aggregation respects filters — counts only match filtered scenes |
| `test_get_filter_options` | Returns correct unique values for all dimensions |
| `test_grouped_by_location` | Items grouped correctly under location headers |
| `test_grouped_by_character` | Items grouped by character with correct scene refs |
| `test_grouped_by_story_day` | Items grouped by day with correct breakdown |

### Frontend Tests

| Test | Description |
|------|-------------|
| `test_filter_panel_renders` | All filter controls present |
| `test_filter_options_populated` | Dropdowns populated from API |
| `test_filter_change_updates_preview` | Changing filter triggers preview refresh |
| `test_smart_defaults_applied` | Switching report type sets correct defaults |
| `test_clear_all_filters` | Reset button clears all filter state |
| `test_generate_with_filters` | Generate button sends filters in request |

### Integration / E2E

| Test | Description |
|------|-------------|
| `test_filtered_pdf_generation` | Generate PDF with location filter — verify PDF content only has matching scenes |
| `test_filter_options_endpoint` | Endpoint returns correct data shape |
| `test_shared_filtered_report` | Shared report preserves filter config |

---

## Summary

This feature transforms the reporting system from "generate a report for the entire script" to "build the exact report you need with cross-dimensional filters and grouping." The architecture is additive — no breaking changes to existing reports. Phases are independent and can be delivered incrementally.

**Phase 1** (backend filter engine) unblocks everything else and can be tested via API alone.  
**Phase 2** (filter UI) delivers the full user-facing value.  
**Phase 3** (grouped renderers) makes filtered reports production-ready for print/PDF.  
**Phase 4** (presets) adds convenience and department-specific workflows.
