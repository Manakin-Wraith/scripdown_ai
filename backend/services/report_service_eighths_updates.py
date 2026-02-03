"""
Report Service Eighths Updates - Code Snippets

This file contains the specific code changes needed for all report rendering methods.
Apply these changes to backend/services/report_service.py

IMPORTANT: These are targeted replacements for specific sections.
"""

# ============================================
# 1. Scene Breakdown Report Update
# ============================================
# Location: _render_scene_breakdown method (around line 770-850)

SCENE_BREAKDOWN_UPDATE = """
def _render_scene_breakdown(self, data: Dict) -> str:
    scenes = data.get('scenes', [])
    rows = []
    
    for scene in scenes:
        scene_num = scene.get('scene_number', '')
        int_ext = scene.get('int_ext', '')
        setting = scene.get('setting', '')
        time_of_day = scene.get('time_of_day', '')
        
        # Characters
        chars = ', '.join(scene.get('characters', [])[:10])
        if len(scene.get('characters', [])) > 10:
            chars += f" (+{len(scene.get('characters', [])) - 10} more)"
        
        # Props
        props = ', '.join(scene.get('props', [])[:5])
        if len(scene.get('props', [])) > 5:
            props += f" (+{len(scene.get('props', [])) - 5} more)"
        
        # Scene length in eighths
        eighths = scene.get('page_length_eighths', 8)
        length_display = format_eighths(eighths)
        
        rows.append(f'''
        <tr>
            <td>{scene_num}</td>
            <td>{int_ext}</td>
            <td>{setting}</td>
            <td>{time_of_day}</td>
            <td>{chars}</td>
            <td>{props}</td>
            <td class="length-cell">{length_display}</td>
        </tr>
        ''')
    
    return f'''
    <div class="report-section">
        <h2>Scene Breakdown</h2>
        <table class="breakdown-table">
            <thead>
                <tr>
                    <th>Scene</th>
                    <th>I/E</th>
                    <th>Setting</th>
                    <th>D/N</th>
                    <th>Characters</th>
                    <th>Props</th>
                    <th>Length</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    '''
"""

# ============================================
# 2. One-Liner/Stripboard Report Update
# ============================================
# Location: _render_one_liner method (around line 945-1020)

ONE_LINER_UPDATE = """
def _render_one_liner(self, data: Dict) -> str:
    scenes = data.get('scenes', [])
    rows = []
    
    for scene in scenes:
        scene_num = scene.get('scene_number', '')
        int_ext = scene.get('int_ext', '')
        setting = scene.get('setting', '')
        time_of_day = scene.get('time_of_day', '')
        description = scene.get('description', '')[:100]
        
        # Scene length in eighths
        eighths = scene.get('page_length_eighths', 8)
        length_display = format_eighths(eighths)
        
        rows.append(f'''
        <tr class="one-liner-row">
            <td class="scene-num">{scene_num}</td>
            <td class="int-ext">{int_ext}</td>
            <td class="setting">{setting}</td>
            <td class="time">{time_of_day}</td>
            <td class="description">{description}</td>
            <td class="length">{length_display}</td>
        </tr>
        ''')
    
    return f'''
    <div class="report-section">
        <h2>One-Liner / Stripboard</h2>
        <table class="one-liner-table">
            <thead>
                <tr>
                    <th>Scene</th>
                    <th>I/E</th>
                    <th>Setting</th>
                    <th>D/N</th>
                    <th>Description</th>
                    <th>Length</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    '''
"""

# ============================================
# 3. Department Reports - Scene Cross-References
# ============================================
# Apply this pattern to ALL 8 department report methods

DEPARTMENT_REPORT_PATTERN = """
# For each department report (_render_wardrobe_department, _render_props_department, etc.)
# Update the scene cross-reference section:

# Build scene references with eighths
scenes_dict = {s.get('scene_number'): s for s in data.get('scenes', [])}
scene_refs = []
for scene_num in sorted(scenes_list):
    scene = scenes_dict.get(scene_num)
    if scene:
        eighths = scene.get('page_length_eighths', 8)
        length = format_eighths(eighths)
        scene_refs.append(f"{scene_num} ({length})")

cross_ref = ', '.join(scene_refs)
"""

# ============================================
# 4. Full Breakdown Report - Summary Statistics
# ============================================
# Location: _render_full_breakdown method

FULL_BREAKDOWN_SUMMARY = """
def _render_full_breakdown(self, data: Dict) -> str:
    summary = data.get('summary', {})
    script = data.get('script', {})
    
    # Calculate script length
    total_eighths = summary.get('total_eighths', 0)
    total_pages = total_eighths / 8
    avg_scene_eighths = total_eighths // max(summary.get('total_scenes', 1), 1)
    
    summary_html = f'''
    <div class="summary-section">
        <h2>Production Summary</h2>
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
                <span class="value">{format_eighths(avg_scene_eighths)}</span>
            </div>
            <div class="summary-item">
                <span class="label">Characters</span>
                <span class="value">{summary.get('total_characters', 0)}</span>
            </div>
            <div class="summary-item">
                <span class="label">Locations</span>
                <span class="value">{summary.get('total_locations', 0)}</span>
            </div>
            <div class="summary-item">
                <span class="label">Props</span>
                <span class="value">{summary.get('total_props', 0)}</span>
            </div>
        </div>
    </div>
    '''
    
    # Include all other report sections...
    return summary_html + scene_breakdown + department_sections
"""

# ============================================
# 5. CSS Updates
# ============================================
# Location: _get_report_css method

CSS_ADDITIONS = """
/* Add to existing CSS in _get_report_css() */

.length-cell {
    text-align: center;
    font-weight: 600;
    font-family: 'Courier New', monospace;
    white-space: nowrap;
    font-size: 0.95em;
}

.one-liner-table .length {
    width: 60px;
    text-align: center;
    font-family: 'Courier New', monospace;
    font-weight: 600;
}

.breakdown-table th:last-child,
.breakdown-table td:last-child {
    width: 80px;
}
"""

# ============================================
# Implementation Notes
# ============================================
"""
PRIORITY ORDER:
1. Scene Breakdown Report - Most visible
2. One-Liner Report - Frequently used
3. Full Breakdown Summary - Overview stats
4. Department Reports (8 types) - Scene references

TESTING CHECKLIST:
- Scene Breakdown: Verify eighths column displays correctly
- One-Liner: Check compact format
- Full Breakdown: Validate summary calculations
- Each Department Report: Test scene cross-references
- PDF Export: Ensure formatting preserved
- Print View: Verify readability

EDGE CASES:
- NULL eighths: Should default to 8 (1 page)
- Very short scenes (1/8): Display as "1/8"
- Very long scenes (>10 pages): Display correctly
- Whole pages (8, 16, 24): Display as "1", "2", "3"
- Mixed (12, 20): Display as "1 4/8", "2 4/8"
"""
