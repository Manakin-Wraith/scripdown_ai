# LangExtract for Reporting & Scheduling Features

**Date:** February 2, 2026  
**Context:** Strategic analysis of using LangExtract's rich extraction data to enhance production reporting and scheduling capabilities

---

## Executive Summary

LangExtract's **14 extraction classes** (vs. baseline's 4-6) unlock powerful new capabilities for production reporting and scheduling. The key insight: **dialogue, emotions, sounds, transitions, and relationships** are critical data points for creating accurate call sheets, shooting schedules, and department-specific reports.

**Recommendation:** Use LangExtract data as the **foundation for advanced reporting features**, positioning ScripDown AI as a comprehensive pre-production platform.

---

## Current Reporting System Analysis

### Existing Report Types (from `report_service.py`)

1. **Scene Breakdown** - Scene number, INT/EXT, setting, time, characters, props
2. **Day Out of Days** - Character appearance schedule
3. **Location Report** - All locations with scene counts
4. **Props List** - Props organized by scene
5. **Wardrobe Report** - Wardrobe items by character
6. **One-Liner/Stripboard** - Compact scene list for scheduling
7. **Full Breakdown** - Complete breakdown document

### Current Data Sources (Baseline Extraction)

```python
# From aggregate_scene_data()
- Characters (count, scenes, pages)
- Locations (count, scenes, INT/EXT, time_of_day)
- Props (count, scenes)
- Wardrobe (count, scenes, characters)
```

**Limitation:** Missing critical production data like dialogue density, emotional intensity, sound requirements, and special effects.

---

## LangExtract Enhancement Opportunities

### New Extraction Classes Available

| Class | Current Use | Reporting/Scheduling Value |
|-------|-------------|---------------------------|
| **dialogue** (66) | ❌ Not used | ✅ Dialogue density → shooting time estimates |
| **emotion** (23) | ❌ Not used | ✅ Emotional intensity → actor preparation needs |
| **action** (53) | ❌ Not used | ✅ Action complexity → stunt coordination |
| **sound** (7) | ❌ Not used | ✅ Sound requirements → sound dept. call sheets |
| **special_fx** (2) | ❌ Not used | ✅ VFX/SFX needs → effects scheduling |
| **vehicle** (5) | ❌ Not used | ✅ Vehicle logistics → transportation dept. |
| **transition** (10) | ❌ Not used | ✅ Post-production notes → editing schedule |
| **relationship** (5) | ❌ Not used | ✅ Character dynamics → blocking complexity |
| **location_detail** (12) | ❌ Not used | ✅ Set dressing specifics → art dept. prep |
| **makeup_hair** (3) | ❌ Not used | ✅ Makeup/hair needs → dept. call sheets |

---

## Enhanced Report Types with LangExtract

### 1. **Advanced Call Sheets** 🎬

**Current:** Basic scene info + characters + props  
**Enhanced with LangExtract:**

```
SCENE 12: INT. WAREHOUSE - NIGHT
Pages: 3.5 | Estimated Shoot Time: 4-5 hours

CAST:
- Mike (Lead) - High emotional intensity, 8 dialogue lines
- Sarah (Supporting) - Terrified emotional state, 6 dialogue lines

DIALOGUE DENSITY: Heavy (14 lines in 3.5 pages)
→ Recommendation: Schedule extra rehearsal time

EMOTIONAL INTENSITY: High
→ Actors: Arrive 30 min early for emotional prep
→ Director: Plan for multiple takes

SOUND REQUIREMENTS:
- Footsteps echoing (production sound)
- Distant siren (to be added in post)
- Gunshot (SFX - coordinate with sound dept)

SPECIAL EFFECTS:
- Flickering lights, casting dancing shadows
→ Gaffer: Prepare practical lighting effects

VEHICLES:
- V8 (hero car) - Must be on set by 6 AM

ACTION COMPLEXITY: Moderate
- Physical confrontation
- Gun handling (prop master + safety officer required)

PROPS (Critical):
- Flashlight (practical, working)
- Gun (prop, safety checked)

ESTIMATED CREW CALL:
- Gaffer & Electrics: 5:00 AM (lighting setup)
- Prop Master: 5:30 AM (prop check)
- Sound: 6:00 AM (mic setup)
- Cast: 6:30 AM (makeup/wardrobe)
- Rehearsal: 7:00 AM
- First Shot: 8:00 AM
```

**Impact:** More accurate time estimates, better crew coordination, fewer delays.

---

### 2. **Intelligent Shooting Schedule** 📅

**Current:** Basic scene grouping by location/time  
**Enhanced with LangExtract:**

#### Scene Complexity Scoring

```python
def calculate_scene_complexity(scene_extractions):
    """
    Calculate shooting complexity based on LangExtract data.
    Returns complexity score (1-10) and time estimate.
    """
    score = 0
    
    # Dialogue density (more dialogue = more time)
    dialogue_count = len([e for e in extractions if e.class == 'dialogue'])
    score += min(dialogue_count / 5, 3)  # Max 3 points
    
    # Emotional intensity (complex emotions = more takes)
    emotions = [e for e in extractions if e.class == 'emotion']
    if any('terrified' in e.text.lower() or 'angry' in e.text.lower() for e in emotions):
        score += 2
    
    # Action complexity
    actions = [e for e in extractions if e.class == 'action']
    if len(actions) > 5:
        score += 2
    
    # Special effects (technical complexity)
    fx_count = len([e for e in extractions if e.class == 'special_fx'])
    score += fx_count * 1.5
    
    # Sound requirements (additional setup time)
    sound_count = len([e for e in extractions if e.class == 'sound'])
    score += sound_count * 0.5
    
    # Vehicles (logistics complexity)
    vehicle_count = len([e for e in extractions if e.class == 'vehicle'])
    score += vehicle_count * 1
    
    # Estimate shooting time
    base_time = scene.page_count * 60  # 60 min per page baseline
    complexity_multiplier = 1 + (score / 10)
    estimated_minutes = base_time * complexity_multiplier
    
    return {
        'complexity_score': min(score, 10),
        'estimated_minutes': estimated_minutes,
        'estimated_hours': estimated_minutes / 60,
        'factors': {
            'dialogue_heavy': dialogue_count > 10,
            'emotionally_intense': len(emotions) > 3,
            'action_heavy': len(actions) > 5,
            'technical_fx': fx_count > 0,
            'sound_intensive': sound_count > 3,
            'vehicle_logistics': vehicle_count > 0
        }
    }
```

#### Smart Scheduling Recommendations

```
DAY 1 - WAREHOUSE LOCATION
Scene 12 (INT. WAREHOUSE - NIGHT) - Complexity: 8/10
  Estimated Time: 4-5 hours
  Crew Requirements: Full crew + stunt coordinator
  Schedule: 8:00 AM - 1:00 PM

Scene 15 (INT. WAREHOUSE - NIGHT) - Complexity: 4/10
  Estimated Time: 2-3 hours
  Crew Requirements: Standard crew
  Schedule: 2:00 PM - 5:00 PM

⚠️ SCHEDULING ALERT:
- Both scenes are emotionally intense
- Recommend scheduling lighter Scene 15 first for actor warm-up
- Consider swapping order to: Scene 15 (morning), Scene 12 (afternoon)
```

---

### 3. **Department-Specific Call Sheets** 🎭

#### Sound Department Call Sheet

```
SOUND DEPARTMENT - DAY 1 CALL SHEET
Production: "The Heist" | Shoot Date: March 15, 2026

SCENES SCHEDULED: 12, 15, 18

SCENE 12: INT. WAREHOUSE - NIGHT (8:00 AM - 1:00 PM)
Sound Requirements (from LangExtract):
  ✓ Footsteps echoing - Boom mic + room tone
  ✓ Distant siren - To be added in post (note for mixer)
  ✓ Gunshot - SFX coordination with prop master
  ✓ Heavy dialogue (14 lines) - Lav mics on both actors

Equipment Needed:
  - 2x Wireless lav mics (Mike, Sarah)
  - Boom mic + pole
  - Mixer with 4-channel input
  - Backup recorder

Crew Call: 6:00 AM (2 hours before first shot)
Setup Time: 1 hour (mic check, room tone recording)

SCENE 15: INT. WAREHOUSE - NIGHT (2:00 PM - 5:00 PM)
Sound Requirements:
  ✓ Minimal dialogue (4 lines)
  ✓ Ambient warehouse sounds
  ✓ No special effects

Equipment Needed:
  - 1x Wireless lav mic
  - Boom mic

NOTES:
- Record 2 min room tone at each setup
- Coordinate with gaffer on generator noise
- Backup batteries for 8-hour shoot day
```

#### Makeup/Hair Department Call Sheet

```
MAKEUP & HAIR DEPARTMENT - DAY 1 CALL SHEET

SCENE 12: INT. WAREHOUSE - NIGHT
Makeup Requirements (from LangExtract):
  - Mike: "Sweating, disheveled" (emotion: angry, threatening)
    → Continuity: Sweat spray, mussed hair
    → Touch-ups every 30 min (emotional intensity)
  
  - Sarah: "Terrified, defensive" (emotion: terrified)
    → Continuity: Tear tracks, smudged makeup
    → Touch-ups every 20 min (crying scenes)

Estimated Touch-up Frequency: High (emotional scene)
Crew Call: 6:30 AM
Actor Makeup Start: 7:00 AM (Mike), 7:30 AM (Sarah)
Ready for Rehearsal: 8:00 AM

PRODUCTS NEEDED:
- Sweat spray (glycerin-based)
- Tear stick or menthol
- Setting spray (long-lasting)
- Touch-up kit (powder, blotting papers)
```

---

### 4. **Post-Production Planning Report** 🎬

**New Report Type Enabled by LangExtract**

```
POST-PRODUCTION PLANNING REPORT
Script: "The Heist" | Generated: Feb 2, 2026

EDITING NOTES (from Transitions):
Total Transitions: 10
  - FADE OUT: 3 scenes
  - FREEZE FRAME: 1 scene (Scene 8)
  - FLASHBACK: 2 scenes (Scenes 4, 9)
  - CUT TO: 4 scenes

Editing Complexity: Moderate
Estimated Edit Time: 15-20 hours

SOUND DESIGN REQUIREMENTS (from Sound Extractions):
Total Sound Cues: 7
  - Production Sound: 4 (footsteps, ambient)
  - Post Sound: 3 (siren, gunshot reverb, warehouse echo)

Sound Design Hours: 8-10 hours
Foley Requirements: Footsteps (warehouse concrete), door creaks

VISUAL EFFECTS (from Special FX):
Total VFX Shots: 2
  - Flickering lights enhancement (Scene 12)
  - Muzzle flash (Scene 12)

VFX Complexity: Low
Estimated VFX Hours: 4-6 hours

DIALOGUE EDITING (from Dialogue Extractions):
Total Dialogue Lines: 66
Heavy Dialogue Scenes: 12, 15, 22
ADR Candidates: 3 scenes (warehouse reverb issues)

Dialogue Edit Hours: 12-15 hours

TOTAL POST-PRODUCTION ESTIMATE:
- Editing: 15-20 hours
- Sound Design: 8-10 hours
- VFX: 4-6 hours
- Dialogue/ADR: 12-15 hours
TOTAL: 39-51 hours (5-7 business days)
```

---

### 5. **Budget Estimation Report** 💰

**Enhanced with LangExtract Data**

```
BUDGET ESTIMATION REPORT
Script: "The Heist"

CREW REQUIREMENTS (derived from scene complexity):

High Complexity Scenes (8-10): 3 scenes
  - Requires: Full crew + specialists
  - Daily Rate: $8,000 - $10,000
  - Total: $24,000 - $30,000

Medium Complexity Scenes (5-7): 8 scenes
  - Requires: Standard crew
  - Daily Rate: $5,000 - $6,000
  - Total: $40,000 - $48,000

Low Complexity Scenes (1-4): 12 scenes
  - Requires: Minimal crew
  - Daily Rate: $3,000 - $4,000
  - Total: $36,000 - $48,000

SPECIAL REQUIREMENTS:

Sound Department (7 sound cues):
  - Equipment rental: $500/day × 5 days = $2,500
  - Sound designer (post): $1,500

Special Effects (2 FX shots):
  - Practical effects: $1,000
  - VFX (post): $2,000

Vehicles (5 vehicle references):
  - Hero car (V8): $1,500/day × 2 days = $3,000
  - Picture cars: $800

Stunt Coordination (action-heavy scenes):
  - Stunt coordinator: $1,200/day × 2 days = $2,400
  - Safety equipment: $500

TOTAL ESTIMATED BUDGET: $113,700 - $138,200
```

---

## Implementation Strategy

### Phase 1: Enhanced Data Aggregation (Week 1-2)

**Extend `aggregate_scene_data()` function:**

```python
def aggregate_langextract_data(script_id: str) -> Dict[str, Any]:
    """
    Aggregate LangExtract extraction data for reporting.
    Extends baseline aggregation with rich extraction classes.
    """
    # Get baseline data
    baseline_data = aggregate_scene_data(script_id)
    
    # Get LangExtract extractions
    extractions = db.get_scene_extractions(script_id)
    
    # Aggregate by class
    dialogue_data = defaultdict(lambda: {'count': 0, 'scenes': []})
    emotion_data = defaultdict(lambda: {'count': 0, 'scenes': [], 'intensity': []})
    sound_data = defaultdict(lambda: {'count': 0, 'scenes': [], 'type': []})
    fx_data = defaultdict(lambda: {'count': 0, 'scenes': []})
    vehicle_data = defaultdict(lambda: {'count': 0, 'scenes': []})
    
    for extraction in extractions:
        scene_id = extraction['scene_id']
        scene_num = get_scene_number(scene_id)
        
        if extraction['extraction_class'] == 'dialogue':
            char = extraction.get('attributes', {}).get('character', 'Unknown')
            dialogue_data[char]['count'] += 1
            dialogue_data[char]['scenes'].append(scene_num)
        
        elif extraction['extraction_class'] == 'emotion':
            emotion_text = extraction['extraction_text']
            emotion_data[emotion_text]['count'] += 1
            emotion_data[emotion_text]['scenes'].append(scene_num)
        
        # ... similar for other classes
    
    return {
        **baseline_data,
        'langextract': {
            'dialogue': dict(dialogue_data),
            'emotions': dict(emotion_data),
            'sounds': dict(sound_data),
            'special_fx': dict(fx_data),
            'vehicles': dict(vehicle_data),
            'scene_complexity': calculate_scene_complexity_scores(script_id)
        }
    }
```

### Phase 2: New Report Types (Week 3-4)

**Add to `REPORT_TYPES`:**

```python
REPORT_TYPES = {
    # ... existing types
    'advanced_call_sheet': {
        'name': 'Advanced Call Sheet',
        'description': 'Detailed call sheet with dialogue, emotions, and technical requirements',
        'requires_langextract': True
    },
    'shooting_schedule': {
        'name': 'Intelligent Shooting Schedule',
        'description': 'Optimized schedule based on scene complexity',
        'requires_langextract': True
    },
    'dept_call_sheet': {
        'name': 'Department Call Sheet',
        'description': 'Department-specific call sheets (Sound, Makeup, etc.)',
        'requires_langextract': True,
        'departments': ['sound', 'makeup_hair', 'props', 'wardrobe', 'vfx']
    },
    'post_production_plan': {
        'name': 'Post-Production Planning',
        'description': 'Editing, sound design, and VFX requirements',
        'requires_langextract': True
    },
    'budget_estimate': {
        'name': 'Budget Estimation',
        'description': 'Cost estimates based on scene complexity',
        'requires_langextract': True
    }
}
```

### Phase 3: UI Integration (Week 5-6)

**New Report Generation UI:**

```jsx
// ReportGenerator.jsx
const ReportGenerator = ({ scriptId }) => {
  const [reportType, setReportType] = useState('scene_breakdown');
  const [langextractEnabled, setLangextractEnabled] = useState(false);
  
  return (
    <div className="report-generator">
      <h2>Generate Report</h2>
      
      <select value={reportType} onChange={(e) => setReportType(e.target.value)}>
        <optgroup label="Standard Reports">
          <option value="scene_breakdown">Scene Breakdown</option>
          <option value="day_out_of_days">Day Out of Days</option>
          <option value="location">Location Report</option>
        </optgroup>
        
        <optgroup label="Advanced Reports (Requires Enhanced Extraction)">
          <option value="advanced_call_sheet">Advanced Call Sheet</option>
          <option value="shooting_schedule">Intelligent Shooting Schedule</option>
          <option value="dept_call_sheet">Department Call Sheets</option>
          <option value="post_production_plan">Post-Production Plan</option>
          <option value="budget_estimate">Budget Estimation</option>
        </optgroup>
      </select>
      
      {requiresLangExtract(reportType) && !langextractEnabled && (
        <div className="enhancement-prompt">
          <AlertCircle />
          <p>This report requires enhanced extraction data.</p>
          <button onClick={() => enhanceScript(scriptId)}>
            Enhance Script with LangExtract
          </button>
        </div>
      )}
      
      <button onClick={() => generateReport(scriptId, reportType)}>
        Generate Report
      </button>
    </div>
  );
};
```

---

## Business Impact

### Value Proposition Enhancement

**Current:** "AI-powered script breakdown"  
**Enhanced:** "AI-powered pre-production platform with intelligent scheduling and department coordination"

### Competitive Differentiation

| Feature | Competitors | ScripDown AI (with LangExtract) |
|---------|-------------|--------------------------------|
| Scene breakdown | ✅ | ✅ |
| Character tracking | ✅ | ✅ |
| Props/wardrobe lists | ✅ | ✅ |
| **Dialogue density analysis** | ❌ | ✅ |
| **Emotional intensity tracking** | ❌ | ✅ |
| **Sound requirements extraction** | ❌ | ✅ |
| **Intelligent time estimation** | ❌ | ✅ |
| **Department-specific call sheets** | ❌ | ✅ |
| **Post-production planning** | ❌ | ✅ |
| **Complexity-based budgeting** | ❌ | ✅ |

### Pricing Strategy

**Standard Tier:** Baseline reports ($29/month)
- Scene breakdown
- Character tracking
- Props/wardrobe lists
- Basic call sheets

**Professional Tier:** Enhanced reports ($79/month)
- All standard reports
- Advanced call sheets with dialogue/emotion data
- Intelligent shooting schedules
- Department call sheets
- Scene complexity scoring

**Studio Tier:** Complete pre-production suite ($199/month)
- All professional reports
- Post-production planning
- Budget estimation
- Custom report templates
- API access for integration

---

## Technical Requirements

### Database Schema Extensions

```sql
-- Store scene complexity scores
ALTER TABLE scenes
ADD COLUMN complexity_score FLOAT,
ADD COLUMN estimated_shoot_minutes INTEGER,
ADD COLUMN dialogue_density TEXT, -- 'light', 'moderate', 'heavy'
ADD COLUMN emotional_intensity TEXT, -- 'low', 'medium', 'high'
ADD COLUMN technical_complexity TEXT; -- 'simple', 'moderate', 'complex'

-- Store department requirements
CREATE TABLE scene_dept_requirements (
    id UUID PRIMARY KEY,
    scene_id UUID REFERENCES scenes(id),
    department TEXT, -- 'sound', 'makeup', 'vfx', etc.
    requirements JSONB,
    estimated_prep_time INTEGER,
    crew_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### API Endpoints

```typescript
// Scene complexity analysis
GET /api/scenes/:sceneId/complexity
POST /api/scripts/:scriptId/analyze-complexity

// Department requirements
GET /api/scenes/:sceneId/dept-requirements
GET /api/scripts/:scriptId/dept-requirements/:department

// Enhanced reports
POST /api/reports/scripts/:scriptId/reports/generate-advanced
GET /api/reports/scripts/:scriptId/shooting-schedule
GET /api/reports/scripts/:scriptId/dept-call-sheet/:department
```

---

## Success Metrics

### User Engagement
- **Report generation increase:** Target 3x more reports generated per user
- **Advanced report adoption:** Target 40% of users upgrade to Professional tier
- **Time savings:** Target 50% reduction in manual call sheet creation time

### Business Metrics
- **ARPU increase:** $29 → $79 (2.7x) for Professional tier adopters
- **Churn reduction:** Better value = lower churn (target 15% reduction)
- **Market differentiation:** Unique features drive word-of-mouth growth

### Production Metrics
- **Scheduling accuracy:** Target 80% accuracy in time estimates
- **Budget variance:** Target ±15% variance in budget estimates
- **User satisfaction:** Target 4.5/5 stars for advanced reports

---

## Risks & Mitigation

### Risk 1: Complexity Overwhelms Users
**Mitigation:** Progressive disclosure UI, start with simple reports, offer advanced as opt-in

### Risk 2: Inaccurate Time/Budget Estimates
**Mitigation:** Machine learning refinement based on actual production data, user feedback loop

### Risk 3: LangExtract Cost at Scale
**Mitigation:** Selective enhancement model (only enhance when generating advanced reports), caching

### Risk 4: Integration Complexity
**Mitigation:** Phased rollout, start with 2-3 advanced reports, expand based on feedback

---

## Conclusion

LangExtract's rich extraction data transforms ScripDown AI from a **script breakdown tool** into a **comprehensive pre-production platform**. The 14 extraction classes enable:

1. **Smarter scheduling** with complexity-based time estimates
2. **Better coordination** with department-specific call sheets
3. **Accurate budgeting** based on technical requirements
4. **Post-production planning** with editing/sound/VFX notes

**Recommendation:** Implement enhanced reporting as a **Professional tier feature**, using the hybrid workflow (baseline for speed, LangExtract for depth) to balance cost and value.

**Next Steps:**
1. Prototype advanced call sheet report
2. Build scene complexity scoring algorithm
3. User test with 5-10 production coordinators
4. Refine based on feedback
5. Launch as beta feature in Professional tier
