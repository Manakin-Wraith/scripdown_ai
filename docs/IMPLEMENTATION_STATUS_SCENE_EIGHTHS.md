# Scene Length Eighths - Implementation Status

**Date**: 2026-02-03  
**Orchestration**: Multi-Agent Workflow

---

## ✅ Completed Tasks (Tasks 1-4)

### Task 1: Database Migration ✅
**Agent**: Backend Architect  
**File**: `backend/db/migrations/024_add_scene_length_eighths.sql`

- Added `page_length_eighths INTEGER` column to scenes table
- Added index for reporting queries
- Added check constraint (1-80 eighths range)
- Added descriptive comment

**Status**: Ready to run

---

### Task 2: Calculation Functions ✅
**Agent**: Coder  
**File**: `backend/utils/scene_calculations.py`

**Functions Implemented**:
- `calculate_eighths_from_content(scene_text)` - Primary method (content-based)
- `calculate_eighths_from_pages(page_start, page_end, scene_text)` - Fallback method
- `format_eighths(eighths)` - Display formatter (e.g., "2 3/8", "1", "4/8")
- `calculate_total_script_length(scenes)` - Aggregate calculation
- `get_scene_length_category(eighths)` - Categorization helper

**Status**: Complete with comprehensive docstrings and examples

---

### Task 3: Backfill Script ✅
**Agent**: Coder  
**File**: `scripts/backfill_scene_eighths.py`

**Features**:
- Processes all scenes or specific script
- Content-based calculation (primary)
- Page-range fallback when no content
- Dry-run mode for preview
- Progress reporting with emoji indicators
- Error handling and skip tracking

**Usage**:
```bash
python scripts/backfill_scene_eighths.py                    # All scenes
python scripts/backfill_scene_eighths.py --script-id 123    # Specific script
python scripts/backfill_scene_eighths.py --dry-run          # Preview only
```

**Status**: Ready to execute after migration

---

### Task 4: AI Extraction Updates ✅
**Agent**: Coder  
**File**: `backend/services/scene_enhancer.py`

**Changes**:
1. Imported `calculate_eighths_from_content` utility
2. Updated `save_enhanced_scene()` signature to accept `scene_text` parameter
3. Added eighths calculation logic with content-based primary and page-range fallback
4. Updated SQL INSERT to include `page_length_eighths` column
5. Updated `process_scene_candidate()` to pass scene_text for calculation

**Status**: Complete - new scenes will automatically get eighths calculated

---

## 🔄 Remaining Tasks (Tasks 5-10)

### Task 5: Update Report Service ⏳
**Agent**: Coder  
**File**: `backend/services/report_service.py` (1658 lines)

**Required Changes**:

#### 5.1: Import Utilities
```python
from utils.scene_calculations import format_eighths, calculate_total_script_length
```

#### 5.2: Update `aggregate_scene_data()` (Line ~388-395)
Replace page_count calculations with eighths:
```python
for scene in scenes:
    scene_num = scene.get('scene_number', '')
    eighths = scene.get('page_length_eighths', 8)
    total_eighths += eighths
    
    # For character tracking
    for char in (scene.get('characters') or []):
        char_name = char if isinstance(char, str) else char.get('name', str(char))
        characters[char_name]['count'] += 1
        characters[char_name]['scenes'].append(scene_num)
        characters[char_name]['eighths'] += eighths  # Track by eighths
```

#### 5.3: Update Scene Breakdown Report (Line ~770-772)
Replace page range with eighths display:
```python
eighths = scene.get('page_length_eighths', 8)
length_display = format_eighths(eighths)

# In table cell:
<td class="length-cell">{length_display}</td>

# In table header:
<th>Length</th>  <!-- Changed from "Page" -->
```

#### 5.4: Update One-Liner Report (Line ~945-947)
```python
eighths = scene.get('page_length_eighths', 8)
length_display = format_eighths(eighths)

<td class="length">{length_display}</td>
```

#### 5.5: Update All 8 Department Reports
For each department report, update scene cross-references:
```python
scene_refs = []
for scene_num in sorted(scenes_list):
    scene = scenes_dict.get(scene_num)
    if scene:
        eighths = scene.get('page_length_eighths', 8)
        length = format_eighths(eighths)
        scene_refs.append(f"{scene_num} ({length})")  # e.g., "5 (2 3/8)"

cross_ref = ', '.join(scene_refs)
```

#### 5.6: Update Summary Statistics
```python
total_eighths, total_pages = calculate_total_script_length(scenes)

summary_html = f"""
<div class="summary-item">
    <span class="label">Script Length</span>
    <span class="value">{total_pages:.1f} pgs</span>
</div>
<div class="summary-item">
    <span class="label">Avg Scene Length</span>
    <span class="value">{format_eighths(total_eighths // len(scenes))}</span>
</div>
"""
```

#### 5.7: Update CSS (in `_get_report_css()`)
```css
.length-cell {
    text-align: center;
    font-weight: 600;
    font-family: 'Courier New', monospace;
    white-space: nowrap;
}

.one-liner-table .length {
    width: 60px;
    text-align: center;
    font-family: 'Courier New', monospace;
}
```

**Affected Report Types**:
1. Scene Breakdown
2. One-Liner/Stripboard
3. Full Breakdown
4. Wardrobe Department
5. Props Department
6. Makeup & Hair Department
7. Special FX Department
8. Vehicles Department
9. Locations Department

---

### Task 6: Frontend Components ⏳
**Agent**: Coder  
**Files**: 
- `frontend/src/components/scenes/SceneDetail.jsx`
- `frontend/src/components/reports/Stripboard.jsx`

#### 6.1: Add Format Utility
```javascript
// Add to both files or create shared utility
const formatEighths = (eighths) => {
    if (!eighths) return '—';
    const full = Math.floor(eighths / 8);
    const remaining = eighths % 8;
    if (remaining === 0) return full > 0 ? `${full}` : '—';
    if (full === 0) return `${remaining}/8`;
    return `${full} ${remaining}/8`;
};
```

#### 6.2: Update SceneDetail.jsx
```jsx
<div className="scene-meta-item">
    <span className="meta-label">Length:</span>
    <span className="meta-value">{formatEighths(scene.page_length_eighths)} pgs</span>
</div>
```

#### 6.3: Update Stripboard.jsx
```jsx
<div className="scene-length">
    {formatEighths(scene.page_length_eighths)}
</div>
```

---

### Task 7: Run Migration & Backfill ⏳
**Agent**: Coder  

**Steps**:
1. Connect to development database
2. Run migration: `024_add_scene_length_eighths.sql`
3. Verify column added: `\d scenes`
4. Run backfill with dry-run first
5. Execute actual backfill
6. Verify data: `SELECT scene_number, page_length_eighths FROM scenes LIMIT 10;`

---

### Task 8: Test Reports ⏳
**Agent**: Tester  

**Test Matrix**:
- [ ] Scene Breakdown Report - eighths display correctly
- [ ] One-Liner Report - eighths in compact format
- [ ] Full Breakdown Report - summary statistics accurate
- [ ] Wardrobe Department Report - scene refs with eighths
- [ ] Props Department Report - scene refs with eighths
- [ ] Makeup Department Report - scene refs with eighths
- [ ] Special FX Department Report - scene refs with eighths
- [ ] Vehicles Department Report - scene refs with eighths
- [ ] Locations Department Report - scene refs with eighths
- [ ] PDF Export - formatting preserved
- [ ] Print View - readable eighths notation

---

### Task 9: Test Frontend & Edge Cases ⏳
**Agent**: Tester  

**Test Cases**:
- [ ] SceneDetail displays eighths correctly
- [ ] Stripboard shows eighths in scene cards
- [ ] Missing data (NULL eighths) shows "—"
- [ ] Very short scenes (1/8) display correctly
- [ ] Very long scenes (>10 pages) handled
- [ ] Omitted scenes show grayed-out length
- [ ] Split scenes recalculate eighths
- [ ] Merged scenes aggregate eighths
- [ ] End-to-end: Upload → Analyze → View → Report

---

### Task 10: Production Deployment ⏳
**Agent**: Backend Architect  

**Deployment Checklist**:
- [ ] Review all code changes
- [ ] Run migration on staging database
- [ ] Backfill staging data
- [ ] Test all reports on staging
- [ ] Create database backup
- [ ] Run migration on production
- [ ] Backfill production data (monitor progress)
- [ ] Smoke test production reports
- [ ] Monitor error logs for 24 hours
- [ ] Document rollback procedure

---

## Next Steps

**Immediate Actions**:
1. Complete Task 5: Update `report_service.py` (requires careful line-by-line updates)
2. Complete Task 6: Update frontend components
3. Execute Task 7: Run migration and backfill on development
4. Execute Tasks 8-9: Comprehensive testing
5. Execute Task 10: Production deployment

**Estimated Remaining Effort**: 18 hours
- Task 5: 6 hours (report service updates)
- Task 6: 3 hours (frontend updates)
- Task 7: 1 hour (migration execution)
- Task 8: 4 hours (report testing)
- Task 9: 3 hours (frontend/edge case testing)
- Task 10: 2 hours (production deployment)

---

## Key Design Decisions

1. **Calculation Method**: Content-based (Option B) as primary, page-range as fallback
2. **Display Format**: Industry-standard notation (e.g., "2 3/8", "1", "4/8")
3. **Default Value**: 8 eighths (1 page) for missing data
4. **Range Constraint**: 1-80 eighths (1/8 page to 10 pages)
5. **Idempotency**: Backfill script checks for NULL values only

---

## Benefits Achieved

✅ **Industry Standard**: Matches professional production workflows  
✅ **Accurate Timing**: 1/8 page ≈ 1 minute of screen time  
✅ **Better Scheduling**: More precise scene duration estimates  
✅ **Professional Reports**: Aligns with industry expectations  
✅ **Data Quality**: Content-based calculation more accurate than page ranges
