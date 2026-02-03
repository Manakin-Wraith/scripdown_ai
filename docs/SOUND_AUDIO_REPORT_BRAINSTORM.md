# Sound/Audio Report - Implementation Brainstorm

## Overview
Add a dedicated Sound/Audio Department Report to provide sound designers, composers, and audio post-production teams with a comprehensive breakdown of all audio requirements throughout the script.

**Date**: 2026-02-03  
**Status**: Brainstorming Phase  
**Priority**: Medium-High (Essential production department)

---

## Current System Analysis

### Existing Sound Data
**Database**: `scenes.sound_notes` (TEXT field) - Added in migration 022
- Stores sound effects and music requirements per scene
- Currently collected during AI extraction
- **Valid category** in ReportConfig: `"sound"` already exists in VALID_CATEGORIES

### Current Collection Points
1. **AI Extraction** (`analysis_worker.py`)
   - Extracts sound requirements during scene analysis
   - Stored in `sound_notes` field

2. **Scene Enhancement** (`scene_enhancer.py`)
   - Can enhance sound details in Pass 2

3. **Frontend Display** (`SceneDetail.jsx`)
   - Shows sound notes in scene breakdown view

---

## Sound/Audio Report Purpose

### Target Users
1. **Sound Designer** - Plans and creates sound effects
2. **Composer** - Scores music cues
3. **Sound Mixer** - Plans recording and mixing requirements
4. **Foley Artist** - Plans foley recording sessions
5. **Audio Post Supervisor** - Oversees entire audio workflow

### Key Information Needed
- **Sound Effects (SFX)**: Specific effects required (gunshots, explosions, doors, etc.)
- **Music Cues**: Where music starts/stops, mood, style
- **Dialogue Notes**: ADR requirements, voice processing
- **Ambience/Atmosphere**: Background sounds (traffic, nature, crowds)
- **Special Audio**: Voiceovers, phone calls, radio, TV audio
- **Technical Requirements**: Wireless mics, boom placement, special recording needs

---

## Report Structure Options

### Option A: Simple List Format
**Pros**: Easy to implement, quick to scan  
**Cons**: Less organized, harder to plan from

```
SOUND/AUDIO BREAKDOWN

Scene 1 - INT. COFFEE SHOP - DAY (2 3/8)
├─ Ambience: Busy coffee shop, espresso machine, chatter
├─ SFX: Door bell, coffee cup clink
├─ Music: Upbeat indie track (source music from speakers)
└─ Dialogue: Clean, intimate conversation

Scene 5 - EXT. CITY STREET - NIGHT (1 4/8)
├─ Ambience: Traffic, distant sirens, city hum
├─ SFX: Car horn, footsteps on pavement
├─ Music: Suspenseful underscore begins
└─ Technical: Wireless lav mics required (moving actors)
```

---

### Option B: Categorized by Audio Type (RECOMMENDED)
**Pros**: Organized by workflow, easier for specialists  
**Cons**: More complex to generate

```
SOUND/AUDIO REPORT

═══════════════════════════════════════════════════
SOUND EFFECTS (SFX)
═══════════════════════════════════════════════════

Gunshots/Weapons
├─ Scene 12 (2 3/8): Pistol shots (3x), shell casings
├─ Scene 45 (1/8): Shotgun blast
└─ Scene 67 (3 4/8): Automatic rifle fire, ricochets

Vehicles
├─ Scene 3 (1 2/8): Car engine start, door slam
├─ Scene 18 (2/8): Motorcycle approach and pass
└─ Scene 34 (4/8): Helicopter overhead

Doors/Impacts
├─ Scene 1 (2 3/8): Coffee shop door bell
├─ Scene 8 (1/8): Heavy door slam
└─ Scene 22 (3/8): Glass break

═══════════════════════════════════════════════════
MUSIC CUES
═══════════════════════════════════════════════════

Source Music (Diegetic)
├─ Scene 1 (2 3/8): Upbeat indie track from cafe speakers
├─ Scene 15 (1 4/8): Car radio - classic rock
└─ Scene 28 (2/8): Live band - jazz

Score (Non-Diegetic)
├─ Scene 5 (1 4/8): Suspenseful underscore begins
├─ Scene 12 (2 3/8): Action music crescendo
└─ Scene 45 (3/8): Emotional piano theme

═══════════════════════════════════════════════════
AMBIENCE/ATMOSPHERE
═══════════════════════════════════════════════════

Urban Environments
├─ Scene 5 (1 4/8): City street - traffic, sirens
├─ Scene 9 (2/8): Subway station - trains, announcements
└─ Scene 31 (1 2/8): Office building - HVAC, phones

Natural Environments
├─ Scene 20 (3 4/8): Forest - birds, wind, leaves
├─ Scene 38 (2 3/8): Beach - waves, seagulls
└─ Scene 52 (1/8): Rain on roof

═══════════════════════════════════════════════════
DIALOGUE/VOICE
═══════════════════════════════════════════════════

ADR Requirements
├─ Scene 12 (2 3/8): Shouted dialogue during action
├─ Scene 34 (4/8): Dialogue in helicopter (heavy noise)
└─ Scene 45 (3/8): Whispered conversation (clarity needed)

Voice Processing
├─ Scene 7 (1/8): Phone call (filtered voice)
├─ Scene 19 (2/8): Radio transmission (distorted)
└─ Scene 41 (1/8): Voiceover narration

═══════════════════════════════════════════════════
TECHNICAL REQUIREMENTS
═══════════════════════════════════════════════════

Special Recording Needs
├─ Scene 5 (1 4/8): Wireless lavs (moving actors on street)
├─ Scene 12 (2 3/8): Plant mics (action sequence)
├─ Scene 34 (4/8): Helicopter mics (aerial recording)
└─ Scene 52 (1/8): Rain protection for equipment

═══════════════════════════════════════════════════
SUMMARY STATISTICS
═══════════════════════════════════════════════════

Total Scenes with Audio Notes: 45
Total SFX Cues: 127
Total Music Cues: 23
ADR Scenes: 8
Special Recording Setups: 12

Estimated Audio Post Hours: 180-220 hours
```

---

### Option C: Timeline/Chronological Format
**Pros**: Follows script order, good for spotting sessions  
**Cons**: Harder to see all instances of specific sound types

```
SOUND/AUDIO TIMELINE

[00:00:00] Scene 1 - INT. COFFEE SHOP - DAY
Duration: 2 3/8 pages (~2.5 minutes)
├─ Ambience: Coffee shop atmosphere
├─ SFX: Door bell, espresso machine
├─ Music: Source - indie track
└─ Recording: Standard boom + lavs

[00:02:30] Scene 2 - INT. APARTMENT - DAY
Duration: 1/8 page (~0.1 minutes)
├─ Ambience: Quiet apartment
└─ Recording: Standard boom

[00:02:36] Scene 3 - EXT. PARKING LOT - DAY
Duration: 1 2/8 pages (~1.25 minutes)
├─ Ambience: Outdoor, light traffic
├─ SFX: Car engine, door slam
└─ Recording: Wireless lavs (moving)
```

---

## Data Structure & Extraction

### Enhanced Sound Data Model

Instead of just `sound_notes` (TEXT), consider structured JSONB:

```json
{
  "sound_effects": [
    {
      "type": "impact",
      "description": "Door slam",
      "intensity": "loud",
      "timing": "scene_start"
    },
    {
      "type": "weapon",
      "description": "Pistol shot",
      "count": 3,
      "timing": "mid_scene"
    }
  ],
  "music": [
    {
      "type": "source",
      "description": "Upbeat indie track from cafe speakers",
      "mood": "cheerful",
      "timing": "throughout"
    }
  ],
  "ambience": {
    "primary": "Coffee shop atmosphere",
    "elements": ["espresso machine", "chatter", "dishes"]
  },
  "dialogue_notes": {
    "adr_required": false,
    "special_processing": null,
    "recording_notes": "Standard boom + lavs"
  },
  "technical": {
    "wireless_mics": true,
    "special_equipment": [],
    "recording_challenges": "Noisy environment"
  }
}
```

### AI Extraction Enhancement

Update prompts to extract structured sound data:

```python
# In analysis_worker.py
"""
Extract detailed sound/audio requirements:

SOUND EFFECTS:
- List all specific sound effects needed
- Categorize: impacts, weapons, vehicles, nature, mechanical, etc.
- Note intensity (subtle, moderate, loud, extreme)

MUSIC:
- Source music (diegetic - heard by characters)
- Score (non-diegetic - underscore)
- Mood/style if specified

AMBIENCE/ATMOSPHERE:
- Primary environment sound
- Specific elements (traffic, birds, wind, etc.)

DIALOGUE NOTES:
- ADR requirements (difficult recording conditions)
- Voice processing (phone, radio, echo, etc.)
- Special vocal requirements

TECHNICAL:
- Recording challenges
- Special equipment needs
- Microphone placement notes

Return as structured JSON in sound_data field.
"""
```

---

## Implementation Plan

### Phase 1: Database Enhancement (Optional)

**Option 1A**: Keep existing `sound_notes` TEXT field
- ✅ No migration needed
- ✅ Works with current data
- ❌ Less structured
- ❌ Harder to categorize

**Option 1B**: Add structured `sound_data` JSONB field
- ✅ Better organization
- ✅ Easier to query/filter
- ❌ Requires migration
- ❌ Need to backfill existing data

**Recommendation**: Start with Option 1A (use existing field), migrate to 1B later if needed.

---

### Phase 2: Report Renderer

**File**: `backend/services/report_service.py`

```python
def _render_sound_department(self, data: Dict) -> str:
    """
    Render Sound/Audio Department Report.
    
    Organizes sound requirements by category:
    - Sound Effects (SFX)
    - Music Cues
    - Ambience/Atmosphere
    - Dialogue/Voice
    - Technical Requirements
    """
    scenes = data.get('scenes', [])
    
    # Categorize sound elements
    sfx_items = defaultdict(list)
    music_cues = defaultdict(list)
    ambience_items = defaultdict(list)
    dialogue_notes = []
    technical_reqs = []
    
    for scene in scenes:
        sound_notes = scene.get('sound_notes', '')
        if not sound_notes:
            continue
        
        scene_num = scene.get('scene_number', '')
        eighths = scene.get('page_length_eighths', 8)
        length = self._format_eighths(eighths)
        scene_ref = f"Scene {scene_num} ({length})"
        
        # Parse sound_notes and categorize
        # (Simple keyword matching for now, can enhance with AI later)
        notes_lower = sound_notes.lower()
        
        # Detect SFX
        if any(word in notes_lower for word in ['gunshot', 'explosion', 'crash', 'slam', 'bang']):
            sfx_items['Impacts/Weapons'].append({
                'scene': scene_ref,
                'description': sound_notes
            })
        elif any(word in notes_lower for word in ['car', 'engine', 'vehicle', 'motorcycle']):
            sfx_items['Vehicles'].append({
                'scene': scene_ref,
                'description': sound_notes
            })
        elif any(word in notes_lower for word in ['door', 'window', 'glass']):
            sfx_items['Doors/Impacts'].append({
                'scene': scene_ref,
                'description': sound_notes
            })
        else:
            sfx_items['Other SFX'].append({
                'scene': scene_ref,
                'description': sound_notes
            })
        
        # Detect Music
        if any(word in notes_lower for word in ['music', 'song', 'score', 'soundtrack']):
            music_type = 'Source Music' if 'radio' in notes_lower or 'speakers' in notes_lower else 'Score'
            music_cues[music_type].append({
                'scene': scene_ref,
                'description': sound_notes
            })
        
        # Detect Ambience
        if any(word in notes_lower for word in ['ambience', 'atmosphere', 'background', 'traffic', 'birds', 'wind']):
            ambience_items['Environment'].append({
                'scene': scene_ref,
                'description': sound_notes
            })
        
        # Detect Dialogue/Technical
        if any(word in notes_lower for word in ['adr', 'dialogue', 'voice', 'phone', 'radio']):
            dialogue_notes.append({
                'scene': scene_ref,
                'description': sound_notes
            })
        
        if any(word in notes_lower for word in ['wireless', 'mic', 'boom', 'recording']):
            technical_reqs.append({
                'scene': scene_ref,
                'description': sound_notes
            })
    
    # Build HTML
    html_sections = []
    
    # SFX Section
    if sfx_items:
        sfx_html = '<h2>Sound Effects (SFX)</h2>'
        for category, items in sorted(sfx_items.items()):
            sfx_html += f'<h3>{category}</h3><table class="sound-table">'
            sfx_html += '<thead><tr><th>Scene</th><th>Description</th></tr></thead><tbody>'
            for item in items:
                sfx_html += f'<tr><td>{item["scene"]}</td><td>{item["description"]}</td></tr>'
            sfx_html += '</tbody></table>'
        html_sections.append(sfx_html)
    
    # Music Section
    if music_cues:
        music_html = '<h2>Music Cues</h2>'
        for category, items in sorted(music_cues.items()):
            music_html += f'<h3>{category}</h3><table class="sound-table">'
            music_html += '<thead><tr><th>Scene</th><th>Description</th></tr></thead><tbody>'
            for item in items:
                music_html += f'<tr><td>{item["scene"]}</td><td>{item["description"]}</td></tr>'
            music_html += '</tbody></table>'
        html_sections.append(music_html)
    
    # Ambience Section
    if ambience_items:
        amb_html = '<h2>Ambience/Atmosphere</h2>'
        for category, items in sorted(ambience_items.items()):
            amb_html += f'<h3>{category}</h3><table class="sound-table">'
            amb_html += '<thead><tr><th>Scene</th><th>Description</th></tr></thead><tbody>'
            for item in items:
                amb_html += f'<tr><td>{item["scene"]}</td><td>{item["description"]}</td></tr>'
            amb_html += '</tbody></table>'
        html_sections.append(amb_html)
    
    # Dialogue Section
    if dialogue_notes:
        dial_html = '<h2>Dialogue/Voice</h2><table class="sound-table">'
        dial_html += '<thead><tr><th>Scene</th><th>Notes</th></tr></thead><tbody>'
        for item in dialogue_notes:
            dial_html += f'<tr><td>{item["scene"]}</td><td>{item["description"]}</td></tr>'
        dial_html += '</tbody></table>'
        html_sections.append(dial_html)
    
    # Technical Section
    if technical_reqs:
        tech_html = '<h2>Technical Requirements</h2><table class="sound-table">'
        tech_html += '<thead><tr><th>Scene</th><th>Requirements</th></tr></thead><tbody>'
        for item in technical_reqs:
            tech_html += f'<tr><td>{item["scene"]}</td><td>{item["description"]}</td></tr>'
        tech_html += '</tbody></table>'
        html_sections.append(tech_html)
    
    # Summary
    total_scenes = len([s for s in scenes if s.get('sound_notes')])
    summary_html = f"""
    <div class="summary-section">
        <h2>Summary Statistics</h2>
        <div class="summary-grid">
            <div class="summary-item">
                <span class="label">Scenes with Audio Notes</span>
                <span class="value">{total_scenes}</span>
            </div>
            <div class="summary-item">
                <span class="label">Total SFX Cues</span>
                <span class="value">{sum(len(items) for items in sfx_items.values())}</span>
            </div>
            <div class="summary-item">
                <span class="label">Music Cues</span>
                <span class="value">{sum(len(items) for items in music_cues.values())}</span>
            </div>
            <div class="summary-item">
                <span class="label">Technical Setups</span>
                <span class="value">{len(technical_reqs)}</span>
            </div>
        </div>
    </div>
    """
    
    return summary_html + '\n'.join(html_sections)
```

---

### Phase 3: Add to Report Routing

```python
# In _render_report_html method
elif report_type == 'sound' or report_type == 'audio':
    body = self._render_sound_department(data)
```

---

### Phase 4: Add Preset Configuration

```python
# In report_service.py presets
PRESET_SOUND = {
    "report_type": "sound",
    "include_categories": ["sound"],
    "exclude_categories": [],
    "include_metadata": {
        "script_title": True,
        "production_company": True
    },
    "include_descriptions": {
        "description": True,
        "sound_notes": True,
        "technical_notes": True
    },
    "include_summary": True,
    "show_cross_references": True
}

# In ReportConfig.from_preset()
presets = {
    # ... existing presets ...
    "sound": PRESET_SOUND,
    "audio": PRESET_SOUND  # Alias
}

# In ReportConfig.get_available_presets()
{"name": "sound", "title": "Sound/Audio Department", 
 "description": "Sound effects, music cues, and audio requirements"}
```

---

### Phase 5: Update Frontend

#### ExportOptionsModal.jsx
```jsx
// Add to preset info display
{selectedPreset === 'sound' && (
    <>
        <li>Sound effects breakdown</li>
        <li>Music cues and timing</li>
        <li>Ambience requirements</li>
        <li>Dialogue/ADR notes</li>
        <li>Technical recording needs</li>
    </>
)}
```

#### ReportBuilder.jsx
```jsx
// Add sound icon
const REPORT_ICONS = {
    // ... existing icons ...
    sound: Volume2,  // from lucide-react
    audio: Volume2
};
```

---

## Advanced Features (Future)

### 1. Sound Library Integration
- Link to sound effect libraries (e.g., Freesound, BBC Sound Effects)
- Suggest similar sounds from library
- Track which sounds have been sourced

### 2. Music Timing Calculator
- Convert eighths to timecode
- Calculate music cue durations
- Generate spotting notes for composer

### 3. ADR Detection
- AI identifies scenes likely to need ADR
- Flag noisy locations (traffic, wind, etc.)
- Estimate ADR session time

### 4. Budget Estimation
- Calculate sound effects needed
- Estimate foley recording time
- Music licensing costs
- Audio post-production hours

### 5. Sound Design Templates
- Pre-built sound palettes for genres
- Common effect combinations
- Standard ambience packages

### 6. Export Formats
- Pro Tools session markers
- Nuendo cue sheet
- Reaper project markers
- CSV for sound libraries

---

## Industry Standards Reference

### Common Sound Categories
1. **Hard Effects**: Specific, sync'd sounds (door slam, gunshot)
2. **Foley**: Footsteps, cloth movement, prop handling
3. **Ambience**: Background atmosphere (room tone, traffic)
4. **Walla**: Background voices/crowd
5. **Music**: Source (diegetic) and Score (non-diegetic)
6. **Dialogue**: Production sound, ADR, voiceover

### Standard Report Sections (Professional)
- **Spotting Notes**: Scene-by-scene breakdown
- **SFX Cue Sheet**: All effects with timecode
- **Music Cue Sheet**: All music with timing and rights info
- **ADR Notes**: Lines requiring re-recording
- **Foley Notes**: Actions requiring foley recording
- **Mix Notes**: Special mixing requirements

---

## Benefits

### For Sound Department
- **Complete Overview**: All audio requirements in one place
- **Planning**: Better pre-production planning
- **Budgeting**: Accurate cost estimates
- **Scheduling**: Plan recording sessions efficiently
- **Communication**: Share with entire audio team

### For Production
- **Professional**: Industry-standard documentation
- **Efficiency**: Reduces on-set audio issues
- **Cost Control**: Better budget management
- **Quality**: Ensures nothing is missed

---

## Implementation Timeline

### Week 1: Basic Implementation
- Add sound report renderer
- Update report routing
- Add preset configuration
- Test with existing sound_notes data

### Week 2: Enhancement
- Improve categorization logic
- Add summary statistics
- Update frontend UI
- Generate sample reports

### Week 3: Advanced Features
- Consider structured sound_data migration
- Enhanced AI extraction
- Export format options
- User testing

---

## Testing Checklist

- [ ] Sound report generates from existing sound_notes
- [ ] Categorization logic works correctly
- [ ] Cross-references show scene numbers with eighths
- [ ] Summary statistics calculate accurately
- [ ] PDF export preserves formatting
- [ ] Frontend preset selection includes sound
- [ ] Report displays properly in all browsers

---

## Conclusion

A dedicated Sound/Audio Report would:
- ✅ Complete the department report suite (9 → 10 reports)
- ✅ Serve critical production need
- ✅ Use existing data infrastructure
- ✅ Align with industry standards
- ✅ Enhance professional credibility

**Recommendation**: Implement as 10th department report using **Option B** (Categorized by Audio Type) format for maximum utility.

**Estimated Implementation**: 1-2 weeks for full feature
