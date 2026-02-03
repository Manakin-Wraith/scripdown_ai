# Scene Length in Eighths - Implementation Plan

## Overview
Replace page numbers with scene length measured in eighths (1/8ths of a page) across all reports. This is the industry-standard measurement for screenplay scene duration.

**Date**: 2026-02-03  
**Status**: Planning Phase

---

## Current System Analysis

### Database Schema
Currently, scenes store:
- `page_start` (INTEGER) - Starting page number
- `page_end` (INTEGER) - Ending page number
- **Missing**: `page_length_eighths` or `scene_length_eighths`

### Current Calculation
```python
# backend/services/report_service.py:393
page_count = max(1, page_end - page_start + 1) if page_start else 1
```

**Problem**: This gives whole page counts (1, 2, 3 pages), not precise eighths.

### Where Page Numbers Appear in Reports

1. **Scene Breakdown Report** (`_render_scene_breakdown`)
   - Line 770-772: Shows page range (e.g., "5-7")
   
2. **One-Liner/Stripboard** (`_render_one_liner`)
   - Line 945-947: Shows page info in compact format
   
3. **Full Breakdown Report** (`_render_full_breakdown`)
   - Uses `page_count` for summary statistics
   
4. **Department Reports** (8 types)
   - Show scene cross-references with page numbers

---

## Industry Standard: Eighths

### What are Eighths?
- 1 screenplay page = 8 eighths
- Scenes are measured in 1/8th increments
- Examples:
  - 1/8 page = very short scene (few lines)
  - 2/8 (1/4) page = quarter page
  - 4/8 (1/2) page = half page
  - 8/8 (1 page) = full page
  - 12/8 (1 4/8) = one and a half pages

### Display Format
Standard notation: `2 3/8` (reads as "two and three-eighths pages")

---

## Implementation Strategy

### Phase 1: Database Schema ✅ (Add Column)

**Migration**: `024_add_scene_length_eighths.sql`

```sql
-- Add scene length in eighths column
ALTER TABLE scenes 
ADD COLUMN IF NOT EXISTS page_length_eighths INTEGER;

-- Add comment
COMMENT ON COLUMN scenes.page_length_eighths IS 
'Scene length measured in eighths of a page (1 page = 8 eighths). Industry standard for production scheduling.';

-- Add index for reporting queries
CREATE INDEX IF NOT EXISTS idx_scenes_page_length_eighths 
ON scenes(page_length_eighths) WHERE page_length_eighths IS NOT NULL;
```

---

### Phase 2: Calculation Methods

#### Option A: Calculate from Page Range (Approximate)
```python
def calculate_eighths_from_pages(page_start, page_end, scene_text=None):
    """
    Calculate scene length in eighths from page range.
    
    Args:
        page_start: Starting page number
        page_end: Ending page number
        scene_text: Optional scene text for more accurate calculation
    
    Returns:
        int: Scene length in eighths (e.g., 12 = 1 4/8 pages)
    """
    if not page_start:
        return 8  # Default to 1 page
    
    # Basic calculation: full pages * 8
    full_pages = page_end - page_start
    base_eighths = full_pages * 8
    
    # If we have scene text, calculate partial page more accurately
    if scene_text:
        # Estimate based on line count or character count
        lines = len(scene_text.split('\n'))
        # Average screenplay page = ~55 lines
        # Partial page = (lines % 55) / 55 * 8
        remaining_lines = lines % 55
        partial_eighths = round((remaining_lines / 55) * 8)
        return base_eighths + partial_eighths
    else:
        # Assume partial page is half (4/8)
        return base_eighths + 4
```

#### Option B: Calculate from Character/Line Count (More Accurate)
```python
def calculate_eighths_from_content(scene_text):
    """
    Calculate scene length in eighths from actual content.
    More accurate than page range method.
    
    Industry standard:
    - 1 page ≈ 55 lines
    - 1 page ≈ 3000 characters (with proper formatting)
    """
    if not scene_text:
        return 8
    
    # Count lines
    lines = len(scene_text.strip().split('\n'))
    
    # Calculate eighths (55 lines = 8 eighths)
    eighths = round((lines / 55) * 8)
    
    # Minimum 1/8, maximum reasonable is 80 eighths (10 pages)
    return max(1, min(eighths, 80))
```

#### Option C: AI-Assisted Calculation (Most Accurate)
```python
def calculate_eighths_with_ai(scene_text, scene_metadata):
    """
    Use AI to estimate scene length considering:
    - Dialogue density
    - Action description length
    - Formatting (sluglines, transitions)
    """
    prompt = f"""
    Estimate the screenplay page length in eighths for this scene.
    
    Scene: {scene_metadata['scene_number']}
    Setting: {scene_metadata['setting']}
    
    Content:
    {scene_text[:1000]}
    
    Return only an integer representing eighths (1-80).
    Consider standard screenplay formatting where 1 page = 8 eighths.
    """
    
    # Call AI and parse response
    eighths = call_gemini_for_eighths(prompt)
    return eighths
```

---

### Phase 3: Data Migration & Backfill

**Script**: `scripts/backfill_scene_eighths.py`

```python
def backfill_scene_eighths(script_id=None):
    """
    Backfill page_length_eighths for existing scenes.
    
    Args:
        script_id: Optional - backfill specific script, or all if None
    """
    if script_id:
        scenes = db.get_scenes(script_id)
    else:
        # Get all scenes without eighths calculated
        scenes = db.execute("""
            SELECT id, script_id, page_start, page_end, 
                   description, action_description
            FROM scenes 
            WHERE page_length_eighths IS NULL
        """)
    
    for scene in scenes:
        # Use Option B (content-based) for accuracy
        scene_text = scene.get('description', '') + '\n' + scene.get('action_description', '')
        eighths = calculate_eighths_from_content(scene_text)
        
        # Update database
        db.execute("""
            UPDATE scenes 
            SET page_length_eighths = %s 
            WHERE id = %s
        """, (eighths, scene['id']))
    
    print(f"Backfilled {len(scenes)} scenes with eighths calculation")
```

---

### Phase 4: Update AI Extraction

**Files to Update**:
- `backend/services/analysis_worker.py`
- `backend/services/scene_enhancer.py`

```python
# In extract_scenes_from_chunk() prompt:
"""
For each scene, calculate the approximate length in eighths:
- Count the number of lines in the scene
- 1 page = approximately 55 lines = 8 eighths
- Return as integer (e.g., 12 for 1 4/8 pages)

Add to JSON response:
{
    "scene_number": 1,
    "page_start": 1,
    "page_end": 2,
    "page_length_eighths": 12,  // NEW FIELD
    ...
}
"""

# In save_extracted_scene():
page_length_eighths = scene_data.get('page_length_eighths', 8)

db.execute("""
    INSERT INTO scenes (
        ..., page_start, page_end, page_length_eighths
    ) VALUES (
        ..., %s, %s, %s
    )
""", (..., page_start, page_end, page_length_eighths))
```

---

### Phase 5: Update Report Service

**File**: `backend/services/report_service.py`

#### Helper Function
```python
def format_eighths(eighths):
    """
    Format eighths as readable string.
    
    Args:
        eighths (int): Scene length in eighths
    
    Returns:
        str: Formatted string (e.g., "2 3/8", "1", "4/8")
    
    Examples:
        8 → "1"
        12 → "1 4/8"
        3 → "3/8"
        16 → "2"
    """
    if not eighths:
        return "—"
    
    full_pages = eighths // 8
    remaining_eighths = eighths % 8
    
    if remaining_eighths == 0:
        return str(full_pages) if full_pages > 0 else "—"
    elif full_pages == 0:
        return f"{remaining_eighths}/8"
    else:
        return f"{full_pages} {remaining_eighths}/8"
```

#### Update aggregate_scene_data()
```python
# Line 388-395 - Replace page_count with eighths
for scene in scenes:
    scene_num = scene.get('scene_number', '')
    eighths = scene.get('page_length_eighths', 8)  # Default to 1 page
    total_eighths += eighths
    
    # For character tracking
    for char in (scene.get('characters') or []):
        char_name = char if isinstance(char, str) else char.get('name', str(char))
        characters[char_name]['count'] += 1
        characters[char_name]['scenes'].append(scene_num)
        characters[char_name]['eighths'] += eighths  # Track by eighths, not pages
```

#### Update Scene Breakdown Report
```python
# Line 770-772 - Replace page range with eighths
def _render_scene_breakdown(self, data: Dict) -> str:
    scenes = data.get('scenes', [])
    rows = []
    
    for scene in scenes:
        # ... existing code ...
        
        # Replace page_range with eighths
        eighths = scene.get('page_length_eighths', 8)
        length_display = format_eighths(eighths)
        
        rows.append(f"""
        <tr>
            <td>{scene.get('scene_number', '')}</td>
            <td>{scene.get('int_ext', '')}</td>
            <td>{scene.get('setting', '')}</td>
            <td>{scene.get('time_of_day', '')}</td>
            <td>{chars}</td>
            <td>{props}</td>
            <td class="length-cell">{length_display}</td>  <!-- Changed from page -->
        </tr>
        """)
    
    return f"""
    <table class="breakdown-table">
        <thead>
            <tr>
                <th>Scene</th>
                <th>I/E</th>
                <th>Setting</th>
                <th>D/N</th>
                <th>Characters</th>
                <th>Props</th>
                <th>Length</th>  <!-- Changed from "Page" -->
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>
    """
```

#### Update One-Liner Report
```python
# Line 945-947 - Replace page_info with eighths
def _render_one_liner(self, data: Dict) -> str:
    # ... existing code ...
    
    for scene in scenes:
        eighths = scene.get('page_length_eighths', 8)
        length_display = format_eighths(eighths)
        
        rows.append(f"""
        <tr class="one-liner-row">
            <td class="scene-num">{scene.get('scene_number', '')}</td>
            <td class="int-ext">{scene.get('int_ext', '')}</td>
            <td class="setting">{scene.get('setting', '')}</td>
            <td class="time">{scene.get('time_of_day', '')}</td>
            <td class="description">{scene.get('description', '')[:100]}</td>
            <td class="length">{length_display}</td>  <!-- Changed -->
        </tr>
        """)
```

#### Update Department Reports (8 types)
```python
# Example: _render_wardrobe_department
def _render_wardrobe_department(self, data: Dict) -> str:
    # ... existing code ...
    
    # In cross-reference display
    scene_refs = []
    for scene_num in sorted(scenes_list):
        scene = scenes_dict.get(scene_num)
        if scene:
            eighths = scene.get('page_length_eighths', 8)
            length = format_eighths(eighths)
            scene_refs.append(f"{scene_num} ({length})")  # e.g., "5 (2 3/8)"
    
    cross_ref = ', '.join(scene_refs)
```

#### Update Summary Statistics
```python
# In _render_full_breakdown
def _render_full_breakdown(self, data: Dict) -> str:
    summary = data.get('summary', {})
    
    # Calculate total script length in eighths
    total_eighths = sum(s.get('page_length_eighths', 8) for s in data.get('scenes', []))
    total_pages = total_eighths / 8  # Convert to pages for display
    
    summary_html = f"""
    <div class="summary-section">
        <h2>Summary Statistics</h2>
        <div class="summary-grid">
            <div class="summary-item">
                <span class="label">Total Scenes</span>
                <span class="value">{summary.get('total_scenes', 0)}</span>
            </div>
            <div class="summary-item">
                <span class="label">Script Length</span>
                <span class="value">{total_pages:.1f} pgs</span>
            </div>
            <div class="summary-item">
                <span class="label">Avg Scene Length</span>
                <span class="value">{format_eighths(total_eighths // summary.get('total_scenes', 1))}</span>
            </div>
            ...
        </div>
    </div>
    """
```

---

### Phase 6: Update CSS for Length Column

```css
/* backend/services/report_service.py - _get_report_css() */

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

---

### Phase 7: Frontend Updates

#### SceneDetail Component
```jsx
// frontend/src/components/scenes/SceneDetail.jsx

// Add eighths display
const formatEighths = (eighths) => {
    if (!eighths) return '—';
    const full = Math.floor(eighths / 8);
    const remaining = eighths % 8;
    if (remaining === 0) return full > 0 ? `${full}` : '—';
    if (full === 0) return `${remaining}/8`;
    return `${full} ${remaining}/8`;
};

// In render
<div className="scene-meta-item">
    <span className="meta-label">Length:</span>
    <span className="meta-value">{formatEighths(scene.page_length_eighths)} pgs</span>
</div>
```

#### Stripboard Component
```jsx
// frontend/src/components/reports/Stripboard.jsx

// Update scene card to show eighths instead of page range
<div className="scene-length">
    {formatEighths(scene.page_length_eighths)}
</div>
```

---

## Benefits

### Production Scheduling
- **Accurate timing**: 1/8 page ≈ 1 minute of screen time
- **Better budgeting**: More precise scene duration estimates
- **Industry standard**: Matches professional production workflows

### Report Clarity
- **Precise measurements**: "2 3/8" is more accurate than "2-3 pages"
- **Consistent format**: All reports use same measurement
- **Professional appearance**: Matches industry expectations

### Data Analysis
- **Better metrics**: Track average scene length accurately
- **Trend analysis**: Identify pacing issues (too many long/short scenes)
- **Character screen time**: Calculate more accurate character presence

---

## Testing Checklist

- [ ] Database migration runs successfully
- [ ] Backfill script calculates eighths correctly
- [ ] AI extraction includes eighths in new scenes
- [ ] All 9 report types display eighths correctly
- [ ] Frontend components show eighths properly
- [ ] Summary statistics calculate totals accurately
- [ ] Export to PDF preserves eighths formatting
- [ ] Stripboard displays eighths in scene cards

---

## Rollout Plan

### Week 1: Backend Foundation
1. Create and run database migration
2. Implement calculation functions
3. Update AI extraction prompts
4. Run backfill script on existing data

### Week 2: Report Updates
1. Update report_service.py with eighths logic
2. Test all 9 report types
3. Update CSS for proper display
4. Generate sample PDFs for review

### Week 3: Frontend Integration
1. Update SceneDetail component
2. Update Stripboard component
3. Add eighths to scene editing UI
4. Test end-to-end workflow

### Week 4: Testing & Polish
1. User acceptance testing
2. Fix any calculation edge cases
3. Documentation updates
4. Production deployment

---

## Edge Cases to Handle

1. **Missing Data**: Scenes without page_start/page_end
   - Default to 8 eighths (1 page)
   
2. **Very Short Scenes**: Less than 1/8 page
   - Round up to 1/8 (minimum)
   
3. **Very Long Scenes**: More than 10 pages
   - Cap at 80 eighths or allow larger values?
   
4. **Omitted Scenes**: Should they show length?
   - Display with strikethrough or grayed out
   
5. **Split/Merged Scenes**: How to handle length?
   - Recalculate on split/merge operations

---

## Future Enhancements

1. **Manual Override**: Allow users to manually adjust eighths
2. **Visual Indicators**: Color-code scenes by length (short/medium/long)
3. **Timing Estimates**: Convert eighths to estimated screen time
4. **Day Out of Days**: Use eighths for more accurate scheduling
5. **Budget Integration**: Calculate costs based on scene length

---

## Conclusion

Replacing page numbers with eighths throughout the reporting system will:
- Align with industry standards
- Provide more accurate production data
- Improve scheduling and budgeting
- Enhance professional credibility

**Recommended Approach**: Start with **Option B** (content-based calculation) for accuracy, with **Option A** as fallback for scenes without full text data.
