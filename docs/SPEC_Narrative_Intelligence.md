# SPEC: Narrative Intelligence Dashboard

> **Status**: Spec Complete — Ready for Implementation  
> **Author**: AI-assisted  
> **Date**: 2026-02-24  
> **Route**: `/scripts/:scriptId/narrative`

---

## 1. Feature Overview

**Narrative Intelligence** is a dedicated full-page dashboard that provides AI-generated narrative analysis of an entire screenplay — theme, tone, plot structure detection (10 supported structure types), character arcs, relationship dynamics, pacing, and emotional flow.

**Target users**: Directors, writers, script consultants, producers — anyone who needs a quick story-level understanding before diving into production breakdown.

**Value proposition**: Transform raw scene data into a cinematic story map. One click to understand the soul of the script. The AI auto-detects the screenplay's plot structure (three-act, hero's journey, save the cat, etc.) and maps structural beats accordingly, with user override capability.

---

## 2. Design System Context

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-app` | `#0f172a` (gray-900) | Page background |
| `--bg-card` | `#1e293b` (gray-800) | Card backgrounds |
| `--bg-elevated` | `#334155` (gray-700) | Hover states, elevated surfaces |
| `--primary-500` | `#f59e0b` (Amber) | Primary accent, brand color |
| `--primary-400` | `#fbbf24` | Lighter amber for pills, highlights |
| `--text-primary` | `#f8fafc` (gray-50) | Main text |
| `--text-secondary` | `#94a3b8` (gray-400) | Secondary text, labels |
| `--text-muted` | `#64748b` (gray-500) | Subtle text |
| `--border-color` | `#334155` (gray-700) | Card borders |
| `--success` | `#22c55e` | Positive/calm indicators |
| `--danger` | `#ef4444` | Intense/conflict indicators |
| `--warning` | `#f59e0b` | Caution/amber indicators |
| **Font** | Inter, -apple-system stack | Body text |
| **Icons** | `lucide-react` | All iconography |
| **Card pattern** | `breakdown-card` | Header (icon + title + badges) → content |
| **Layout** | `MainLayout` → TopBar + Breadcrumb + Outlet | No sidebar (current arch) |

---

## 3. Existing Data Inventory

Data already extracted by the system that feeds this feature:

| Data Point | Source | Table/Field | Status |
|------------|--------|-------------|--------|
| Per-scene emotional_tone | Scene Enhancer AI | `scenes.emotional_tone` | ✅ Active |
| Per-scene atmosphere | Scene Enhancer AI | `scenes.atmosphere` | ✅ Active |
| Per-scene description | Scene Enhancer AI | `scenes.description` | ✅ Active |
| Story day progression | Story Day Service | `scenes.story_day`, `scenes.timeline_code` | ✅ Active |
| Time transitions | Scene Enhancer AI | `scenes.time_transition`, `scenes.is_new_story_day` | ✅ Active |
| Dialogue tone + subtext | LangExtract | `extraction_metadata` (class: dialogue) | ✅ Active |
| Emotions per scene | LangExtract | `extraction_metadata` (class: emotion) | ✅ Active |
| Relationships per scene | LangExtract | `extraction_metadata` (class: relationship) | ✅ Active |
| Action beats | LangExtract | `extraction_metadata` (class: action) | ✅ Active |
| Transitions | LangExtract | `extraction_metadata` (class: transition) | ✅ Active |
| Character speakers | ScreenPy grammar | `scenes.speakers` | ✅ Active |
| Shot types | ScreenPy grammar | `scenes.shot_type` (via scene_candidates) | ✅ Active |
| Theme/tone/conflict | Narrative Service | `scripts.narrative_analysis` JSONB (Supabase) | ✅ New |
| Character arc positions | Narrative Service | `scripts.narrative_analysis.character_arcs` (Supabase) | ✅ New |
| Act structure | Narrative Service | `scripts.narrative_analysis.act_structure` (Supabase) | ✅ New |
| Key moments (inciting incident, midpoint, climax) | Narrative Service | `scripts.narrative_analysis.key_moments` (Supabase) | ✅ New |

**Extraction Plan for New Fields**:

1. **Act Structure**: Single Gemini call analyzes sampled scenes (beginning/middle/end) to identify:
   - `act_1_end_scene`: Scene number where setup concludes
   - `act_2_midpoint_scene`: Central turning point
   - `act_2_end_scene`: "All is lost" moment
   - `climax_scene`: Final confrontation
   - `resolution_scene`: Denouement
   - `structure_type`: Detected plot structure (see supported types below)

2. **Supported Plot Structures**:
   - `three_act`: Classic setup/confrontation/resolution (default)
   - `five_act`: Shakespearean structure (exposition, rising action, climax, falling action, denouement)
   - `heros_journey`: 12-stage monomyth (call to adventure, threshold, ordeal, return, etc.)
   - `save_the_cat`: Blake Snyder's 15-beat structure
   - `seven_point`: Dan Wells' structure (hook, plot turn 1, pinch 1, midpoint, pinch 2, plot turn 2, resolution)
   - `nonlinear`: Fragmented/non-chronological narrative
   - `circular`: Story ends where it began
   - `parallel`: Multiple storylines converging
   - `episodic`: Loosely connected vignettes
   - `in_medias_res`: Starts mid-action with flashback structure

3. **Key Moments**: Same Gemini call returns array of structural beats (adapted per structure type):
   - `inciting_incident`: Catalyst that launches the story
   - `turning_point`: Major reversals (can be multiple)
   - `midpoint`: Central pivot
   - `climax`: Peak tension
   - `resolution`: Story conclusion
   - `call_to_adventure`: (Hero's Journey) Initial disruption
   - `crossing_threshold`: (Hero's Journey) Point of no return
   - `ordeal`: (Hero's Journey) Supreme challenge
   - `all_is_lost`: (Save the Cat) Darkest moment
   - `dark_night_of_soul`: (Save the Cat) Emotional low point
   - `break_into_three`: (Save the Cat) Solution discovered
   - `pinch_point`: (Seven Point) Pressure moments from antagonist

4. **Storage**: All stored in `scripts.narrative_analysis` JSONB column (Supabase), generated on-demand via `/api/scripts/:scriptId/narrative/analyze` endpoint. Structure type auto-detected by AI but can be overridden by user preference.

---

## 4. Page Layout Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  TopBar + Breadcrumb (existing)                                  │
├──────────────────────────────────────────────────────────────────┤
│  ScriptHeader (existing — with new "Narrative" button)           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─ HERO BANNER ──────────────────────────────────────────────┐  │
│  │  🎬 Script Title                                           │  │
│  │  Theme: "Redemption through sacrifice"                     │  │
│  │  Tone: Dark, atmospheric   Conflict: Man vs Self           │  │
│  │  [Protagonist: MARCUS]  [Antagonist: HAGEN]  [Ensemble: No]│  │
│  │  Structure: [Hero's Journey ▼]  Style: Nonlinear           │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─ STORY ARC VISUALIZATION (structure-adaptive) ────────────┐  │
│  │                                                            │  │
│  │  SVG curve adapts to detected structure_type:              │  │
│  │  ┌──────────╱╲─────────────────────────╱╲───────────┐      │  │
│  │  │  ACT I  ╱  ╲  ACT II              ╱  ╲  ACT III │      │  │
│  │  │───●───●╱────╲●────●────●────●───●╱────╲●────●───│      │  │
│  │  └─────────────────────────────────────────────┘      │  │
│  │  [Hero's Journey ▼]  (dropdown to override structure type)   │  │
│  │  Call to Adventure: Sc 5  |  Ordeal: Sc 42  |  Return: 87  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─ PACING HEATMAP ──────────────────────────────────────────┐  │
│  │  [▓▓░░▓▓▓▓░░▓▓▓▓▓▓▓▓░░▓▓▓▓▓▓▓▓▓▓▓▓░░▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓]   │  │
│  │   Calm                    Moderate                  Intense │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─ 2-COLUMN GRID ──────────────────────────────────────────┐   │
│  │                                                           │   │
│  │  ┌─ CHARACTER JOURNEYS ──┐  ┌─ RELATIONSHIP WEB ───────┐ │   │
│  │  │ MARCUS ●━━━━━●━━━●━●  │  │                          │ │   │
│  │  │ (Lead) hope → despair  │  │    MARCUS ── SARAH       │ │   │
│  │  │        → redemption    │  │      │  ╲     │          │ │   │
│  │  │ SARAH ●━━━━●━━━━━━●   │  │      │   ╲    │          │ │   │
│  │  │ (Supporting) fear →    │  │    HAGEN   ELENA         │ │   │
│  │  │         strength       │  │                          │ │   │
│  │  │ [See all characters]   │  │  ── ally  ─ ─ enemy     │ │   │
│  │  └────────────────────────┘  └──────────────────────────┘ │   │
│  │                                                           │   │
│  │  ┌─ TONE TIMELINE ──────┐  ┌─ KEY MOMENTS ─────────────┐ │   │
│  │  │ Tense ▒▒▒▒           │  │ ⚡ Sc 5: Marcus witnesses  │ │   │
│  │  │ Hopeful    ▒▒▒       │  │    the murder             │ │   │
│  │  │ Dark  ▒▒▒     ▒▒▒▒  │  │ 🔄 Sc 42: The betrayal   │ │   │
│  │  │ Redemptive       ▒▒▒ │  │ 🎭 Sc 87: Final sacrifice│ │   │
│  │  └────────────────────────┘  └──────────────────────────┘ │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. Component Architecture

### 5.1 Page Container

**`NarrativeDashboard.jsx`** — Route: `/scripts/:scriptId/narrative`

- Fetches narrative analysis data via single API call
- Manages loading / error / empty / stale states
- Scrollable single-page layout (no split panes)
- "Analyze Narrative" CTA if data doesn't exist yet
- Re-analyze button if scenes changed since last analysis

### 5.2 Section Components

| # | Component | Data Source | Description |
|---|-----------|-------------|-------------|
| 1 | `NarrativeHero.jsx` | theme, tone, conflict_type, protagonist, antagonist, is_ensemble, narrative_style, structure_type | Full-width banner card with cinematic gradient background, amber left border accent, structure type dropdown |
| 2 | `StoryArcViz.jsx` | act_structure, key_moments[], pacing[], structure_type | Structure-adaptive SVG curve — region bands and milestone labels change per detected structure type (3-act, hero's journey, save the cat, etc.) |
| 3 | `PacingHeatmap.jsx` | pacing[] (scene intensities) | Horizontal heatmap strip — each cell = 1 scene colored by emotional intensity |
| 4 | `CharacterJourneys.jsx` | character_arcs[] (top N by scene count) | Mini sparkline per character + role badge + arc summary text, expandable |
| 5 | `RelationshipWeb.jsx` | relationships[] aggregated across scenes | SVG radial graph — protagonist at center, typed/colored edges |
| 6 | `KeyMoments.jsx` | key_moments[], structure_type | Vertical timeline with amber connector, scene badges, descriptions — beat labels adapt per structure type (e.g. "Call to Adventure" for hero's journey, "All Is Lost" for save the cat) |

### 5.3 Shared Sub-components

| Component | Purpose |
|-----------|---------|
| `NarrativeCard.jsx` | Reusable card wrapper matching existing `breakdown-card` pattern (icon header + content slot) |
| `MiniArcLine.jsx` | Tiny SVG sparkline (~120×30px) for character journey rows |
| `ToneTag.jsx` | Colored pill for tone/emotion labels |

---

## 6. Visual Design Spec

### 6.1 Hero Banner

```
┌──────────────────────────────────────────────────────────────┐
│ ▌                                                            │
│ ▌  🎬  THE DESCENT OF MARCUS                                │
│ ▌                                                            │
│ ▌  "Redemption through sacrifice"                            │
│ ▌                                                            │
│ ▌  [Dark, atmospheric]  [Man vs Self]  [Hero's Journey ▼]   │
│ ▌                                                            │
│ ▌  👤 MARCUS (Protagonist)    👤 HAGEN (Antagonist)          │
│ ▌  Narrative style: Nonlinear with flashback interludes      │
│ ▌                                                            │
└──────────────────────────────────────────────────────────────┘
```

**Styling**:
- `background: linear-gradient(135deg, var(--gray-800) 0%, var(--gray-900) 100%)`
- `border-left: 4px solid var(--primary-500)` (amber accent)
- `border-radius: 12px`
- `padding: 2rem 2.5rem`
- Title: `font-size: 1.75rem; font-weight: 700; color: var(--text-primary)`
- Theme quote: `font-size: 1.1rem; color: var(--primary-400); font-style: italic`
- Meta pills: `border-radius: 20px; background: rgba(245, 158, 11, 0.1); color: var(--primary-400); border: 1px solid rgba(245, 158, 11, 0.2)`
- Character pills: Protagonist = amber bg tint, Antagonist = rose bg tint
- **Structure type dropdown**: Styled as a pill with `▼` chevron. Clicking opens a dropdown of the 10 supported structure types. Auto-detected value shown by default. User override triggers re-analysis of key_moments and act_structure with the chosen structure lens (POST `/api/scripts/:scriptId/narrative/analyze?structure_type=heros_journey`). Dropdown styling: `background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.3); cursor: pointer`

### 6.2 Story Arc Visualization (Structure-Adaptive)

**Visual**:
- Full-width SVG chart inside a `NarrativeCard`
- Main arc line: `stroke: var(--primary-500); stroke-width: 2.5`
- Scene dots: Small circles (r=4), colored by emotional intensity
- Milestone markers: Larger diamonds (r=7) at each key moment (labeled per structure type)
- Break lines: Vertical dashed lines at structure boundaries (`stroke: var(--gray-600); stroke-dasharray: 6,4`)
- Bottom axis: Scene numbers with adaptive label interval (same pattern as `EmotionalArcChart.jsx`)
- Hover: Tooltip with scene number + description + emotional_tone

**Structure-Adaptive Region Rendering**:

The SVG region bands and milestone labels dynamically adapt based on `structure_type`:

| Structure Type | Regions | Milestone Labels |
|---------------|---------|-----------------|
| `three_act` (default) | 3 bands: Act I (teal), Act II (amber), Act III (rose) | Inciting Incident, Midpoint, Climax, Resolution |
| `five_act` | 5 bands: Exposition, Rising Action, Climax, Falling Action, Denouement | Act break labels at each boundary |
| `heros_journey` | 3 zones: Departure (teal), Initiation (amber), Return (rose) | Call to Adventure, Crossing Threshold, Ordeal, Reward, Return |
| `save_the_cat` | 3 zones: Thesis (teal), Antithesis (amber), Synthesis (rose) | Opening Image, Catalyst, Midpoint, All Is Lost, Dark Night, Break Into Three, Final Image |
| `seven_point` | No region bands — milestone-only view | Hook, Plot Turn 1, Pinch 1, Midpoint, Pinch 2, Plot Turn 2, Resolution |
| `nonlinear` | No region bands — timeline overlay shows chronological vs narrative order | Key moments only, with arrows showing temporal displacement |
| `circular` | Single gradient band (teal→amber→teal) | Opening Mirror, Departure Point, Farthest Point, Return Mirror |
| `parallel` | Stacked lanes (one per storyline, if detected) | Convergence points marked |
| `episodic` | Evenly spaced vertical separators per episode/vignette | Episode boundaries |
| `in_medias_res` | 2 bands: Present (amber), Flashback (teal, dashed border) | Opening Action, Flashback Entry, Chronological Catch-up, Climax |

**Region band colors** (consistent across structures):
- First phase: `rgba(20, 184, 166, 0.06)` (teal tint)
- Middle phase: `rgba(245, 158, 11, 0.06)` (amber tint)
- Final phase: `rgba(244, 63, 94, 0.06)` (rose tint)
- Additional phases (5-act, save the cat): `rgba(99, 102, 241, 0.06)` (indigo tint), `rgba(168, 85, 247, 0.06)` (purple tint)

**Interactions**:
- Hover scene dot → tooltip
- Click scene dot → navigate to `/scenes/:scriptId` with that scene selected (future: deep-link query param)
- Structure type dropdown in StoryArcViz header mirrors the one in Hero (synced state) — changing either updates both + triggers re-analysis

### 6.3 Pacing Heatmap

**Visual**:
- Full-width horizontal strip inside a `NarrativeCard`
- Each cell = 1 scene, width proportional to 1/totalScenes
- Color scale: `#10b981` (calm, 1-3) → `#f59e0b` (moderate, 4-6) → `#f97316` (high, 7-8) → `#ef4444` (intense, 9-10)
- Corner radius on cells: `border-radius: 2px`
- Below strip: 3-point legend (Calm / Moderate / Intense) with colored dots

**Interactions**:
- Hover cell → tooltip with scene number + tone text
- Click cell → navigate to scene

### 6.4 Character Journeys Card

**Visual layout per character row**:
```
┌─────────────────────────────────────────────────────────┐
│  MARCUS                              [Lead]             │
│  From guilt-ridden survivor to selfless hero            │
│  ●━━━━━━●━━━━━━━━━●━━━━━●━━━━━━━━━━━━━━●              │
│  guilt   fear    desperation  resolve  sacrifice        │
├─────────────────────────────────────────────────────────┤
│  SARAH                              [Supporting]        │
│  Quiet strength emerging through crisis                 │
│  ●━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━●               │
│  fear          determination          strength          │
└─────────────────────────────────────────────────────────┘
```

- Show top 5 characters by scene count (expandable "Show all" button)
- **Name**: Bold, UPPERCASE, `var(--text-primary)`
- **Role badge**: Pill — Lead = `rgba(251, 191, 36, 0.15)` border + amber text, Supporting = `rgba(148, 163, 184, 0.15)` + silver text, Minor = `rgba(100, 116, 139, 0.1)` + muted text
- **Arc summary**: 1 sentence, `var(--text-secondary)`, `font-size: 0.85rem`
- **Sparkline**: `MiniArcLine.jsx` — 120×30px SVG, line color = `var(--primary-500)`, dots colored by intensity
- **Labels under sparkline**: Key emotion words at notable inflection points, `font-size: 0.7rem; color: var(--text-muted)`
- Click row → future CharacterProfile page (Phase 3)

### 6.5 Relationship Web

**Visual**:
- SVG inside `NarrativeCard` — minimum 400×400px
- Radial layout — protagonist at center, other characters arranged in a circle
- Node = circle with character name centered, sized by scene count (min 30px, max 60px)
- Node colors:
  - Protagonist: `var(--primary-400)` (amber fill)
  - Antagonist: `var(--danger)` (rose fill)
  - Others: `var(--gray-600)` (slate fill)
- Edge types with visual encoding:

| Relationship | Line Style | Color |
|-------------|------------|-------|
| ally | Solid, 2px | `#14b8a6` (teal) |
| enemy / adversarial | Dashed, 2px | `#f43f5e` (rose) |
| romantic | Solid, 2px | `#ec4899` (pink) |
| familial | Solid, 2px | `#fbbf24` (amber) |
| professional | Dotted, 1.5px | `#64748b` (gray) |

- Hover edge → tooltip with relationship description + dynamic
- Legend at bottom showing edge type colors

### 6.6 Key Moments Card

**Visual**:
```
┌─────────────────────────────────────────┐
│  KEY MOMENTS                            │
│                                         │
│  ○── ⚡ INCITING INCIDENT              │
│  │   Sc 5 · Marcus witnesses the murder │
│  │                                      │
│  ○── 📌 TURNING POINT                  │
│  │   Sc 18 · Sarah reveals the truth    │
│  │                                      │
│  ○── 🔄 MIDPOINT                       │
│  │   Sc 42 · The betrayal              │
│  │                                      │
│  ○── 📌 TURNING POINT                  │
│  │   Sc 65 · Hagen's ultimatum         │
│  │                                      │
│  ○── 🎭 CLIMAX                         │
│  │   Sc 87 · Final sacrifice           │
│  │                                      │
│  ○── 🏁 RESOLUTION                     │
│      Sc 92 · Dawn breaks over the city  │
└─────────────────────────────────────────┘
```

- Vertical amber connector line: `border-left: 2px solid var(--primary-500)`
- Each moment node: Circle marker on the line
- **Type icon**: Mapped per moment type (using Lucide icons):

  **Universal beat types** (all structures):
  - `inciting_incident` → `Zap`
  - `turning_point` → `GitBranch`
  - `midpoint` → `RefreshCw`
  - `climax` → `Flame`
  - `resolution` → `Flag`

  **Hero's Journey beats**:
  - `call_to_adventure` → `Compass`
  - `crossing_threshold` → `DoorOpen`
  - `ordeal` → `Skull`

  **Save the Cat beats**:
  - `all_is_lost` → `CloudRain`
  - `dark_night_of_soul` → `Moon`
  - `break_into_three` → `Lightbulb`

  **Seven Point beats**:
  - `pinch_point` → `Target`

- Beat labels display human-readable names (e.g. `call_to_adventure` → "Call to Adventure", `dark_night_of_soul` → "Dark Night of the Soul")
- The timeline only shows beats relevant to the detected/selected `structure_type` — irrelevant beats are filtered out
- **Scene badge**: `Sc 42` pill — `background: var(--bg-elevated); border-radius: 12px; font-size: 0.75rem; font-weight: 600`
- **Description**: 1 sentence, `var(--text-secondary)`, `font-size: 0.85rem`
- Click scene badge → navigate to SceneViewer with scene selected

### 6.7 Tone Timeline Card (Bonus — Phase 2)

- Horizontal stacked bar or stream graph showing which tones dominate across the script
- Grouped into story-day or scene-range buckets
- Colors mapped to tone categories (Tense = red-ish, Hopeful = green, Dark = slate, Comedic = yellow)

---

## 7. Color Palette (Narrative-Specific)

| Purpose | Color | Hex |
|---------|-------|-----|
| Primary accent | Amber | `#f59e0b` |
| Phase 1 region (Act I / Departure / Thesis) | Teal tint | `rgba(20, 184, 166, 0.06)` |
| Phase 2 region (Act II / Initiation / Antithesis) | Amber tint | `rgba(245, 158, 11, 0.06)` |
| Phase 3 region (Act III / Return / Synthesis) | Rose tint | `rgba(244, 63, 94, 0.06)` |
| Phase 4 region (5-act: Falling Action) | Indigo tint | `rgba(99, 102, 241, 0.06)` |
| Phase 5 region (5-act: Denouement) | Purple tint | `rgba(168, 85, 247, 0.06)` |
| Protagonist node | Amber | `#fbbf24` |
| Antagonist node | Rose | `#f43f5e` |
| Ally edge | Teal | `#14b8a6` |
| Enemy edge | Rose | `#f43f5e` |
| Romantic edge | Pink | `#ec4899` |
| Familial edge | Amber | `#fbbf24` |
| Professional edge | Gray | `#64748b` |
| Calm pacing | Green | `#10b981` |
| Moderate pacing | Amber | `#f59e0b` |
| High pacing | Orange | `#f97316` |
| Intense pacing | Red | `#ef4444` |

---

## 8. Backend API

### 8.1 Get Narrative Analysis

```
GET /api/scripts/:scriptId/narrative
```

**Response**:
```json
{
  "success": true,
  "narrative": {
    "theme": "Redemption through sacrifice",
    "tone": "Dark, atmospheric",
    "conflict_type": "man_vs_self",
    "protagonist": "MARCUS",
    "antagonist": "HAGEN",
    "is_ensemble": false,
    "narrative_style": "Nonlinear with flashback interludes",
    "structure_type": "heros_journey",
    "structure_type_auto_detected": true,
    "act_structure": {
      "structure_type": "heros_journey",
      "boundaries": [
        { "label": "Departure", "start_scene": 1, "end_scene": 18 },
        { "label": "Initiation", "start_scene": 19, "end_scene": 75 },
        { "label": "Return", "start_scene": 76, "end_scene": 92 }
      ],
      "act_1_end_scene": 18,
      "act_2_midpoint_scene": 42,
      "act_2_end_scene": 75,
      "climax_scene": 87,
      "resolution_scene": 92
    },
    "key_moments": [
      {
        "type": "call_to_adventure",
        "scene_number": 5,
        "scene_id": "uuid",
        "description": "Marcus witnesses the murder of his mentor"
      },
      {
        "type": "crossing_threshold",
        "scene_number": 18,
        "scene_id": "uuid",
        "description": "Marcus leaves his old life behind to pursue justice"
      },
      {
        "type": "ordeal",
        "scene_number": 42,
        "scene_id": "uuid",
        "description": "Hagen's betrayal is exposed — Marcus faces his greatest test"
      },
      {
        "type": "climax",
        "scene_number": 87,
        "scene_id": "uuid",
        "description": "Marcus makes the final sacrifice"
      },
      {
        "type": "resolution",
        "scene_number": 92,
        "scene_id": "uuid",
        "description": "Marcus returns transformed — dawn breaks over the city"
      }
    ],
    "pacing": [
      { "scene_number": 1, "scene_id": "uuid", "intensity": 3, "tone": "Contemplative" },
      { "scene_number": 2, "scene_id": "uuid", "intensity": 5, "tone": "Tense" }
    ],
    "character_arcs": [
      {
        "name": "MARCUS",
        "role_type": "Lead",
        "scene_count": 45,
        "arc_summary": "From guilt-ridden survivor to selfless hero",
        "arc_positions": [
          { "scene_number": 1, "position": "beginning", "intensity": 4, "emotion": "guilt" },
          { "scene_number": 42, "position": "rising", "intensity": 8, "emotion": "desperation" },
          { "scene_number": 87, "position": "climax", "intensity": 10, "emotion": "sacrifice" },
          { "scene_number": 92, "position": "resolution", "intensity": 6, "emotion": "peace" }
        ]
      },
      {
        "name": "SARAH",
        "role_type": "Supporting",
        "scene_count": 28,
        "arc_summary": "Quiet strength emerging through crisis",
        "arc_positions": []
      }
    ],
    "relationships": [
      {
        "from": "MARCUS",
        "to": "SARAH",
        "type": "ally",
        "dynamic": "Trust building through shared trauma",
        "development": "strengthening"
      },
      {
        "from": "MARCUS",
        "to": "HAGEN",
        "type": "adversarial",
        "dynamic": "Former friends turned enemies",
        "development": "fracturing"
      }
    ]
  },
  "generated_at": "2026-02-24T10:30:00Z",
  "scene_count_at_generation": 94
}
```

### 8.2 Trigger Narrative Analysis

```
POST /api/scripts/:scriptId/narrative/analyze
```

**Request body** (optional):
```json
{
  "structure_type": "heros_journey"
}
```
If `structure_type` is omitted, the AI auto-detects the best-fit structure. If provided, the AI analyzes through the lens of that specific structure type and maps beats accordingly. The `structure_type_auto_detected` flag in the response will be `false` when user-overridden.

**Behavior**:
1. Fetches all scenes for the script (from Supabase)
2. Samples representative scenes using existing `get_act_samples()` pattern (beginning, middle, end)
3. Aggregates LangExtract relationship + emotion data across all scenes
4. Sends a single Gemini call with scene summaries + aggregated data + optional `structure_type` hint
5. AI returns: theme, tone, conflict_type, protagonist, antagonist, structure_type, act_structure (with boundaries adapted to structure), key_moments (beat types adapted to structure), character arcs, narrative_style
6. Builds pacing array from existing `scenes.emotional_tone` data (no AI needed)
7. Aggregates relationships from existing LangExtract data (no AI needed)
8. Stores result in `narrative_analysis` JSONB column on `scripts` table

**Response**:
```json
{
  "success": true,
  "message": "Narrative analysis complete",
  "narrative": { ... }
}
```

### 8.3 Data Sourcing Strategy

| Field | Source | AI Call Needed? |
|-------|--------|------------------|
| theme, tone, conflict_type | Gemini synthesis | Yes |
| protagonist, antagonist | Gemini synthesis | Yes |
| narrative_style, is_ensemble | Gemini synthesis | Yes |
| structure_type | Gemini auto-detection (or user override) | Yes (detection) / No (override) |
| act_structure + boundaries | Gemini synthesis (adapted per structure_type) | Yes |
| key_moments (structure-specific beat types) | Gemini synthesis (adapted per structure_type) | Yes |
| character_arcs[].arc_summary | Gemini synthesis | Yes |
| character_arcs[].arc_positions | Gemini synthesis | Yes |
| character_arcs[].role_type | Gemini synthesis | Yes |
| character_arcs[].scene_count | Aggregation from scenes.characters | No |
| pacing[] | Aggregation from scenes.emotional_tone | No |
| relationships[] | Aggregation from extraction_metadata (class: relationship) | No |

**Total AI calls**: 1 (single comprehensive Gemini prompt). When user overrides `structure_type`, the same single call is made but with an explicit structure hint in the prompt — the AI maps beats to the requested structure rather than auto-detecting.

---

## 9. Database

### Option A: JSONB Column (Recommended for MVP)

Add to existing `scripts` table:
```sql
ALTER TABLE scripts ADD COLUMN narrative_analysis JSONB;
ALTER TABLE scripts ADD COLUMN narrative_analyzed_at TIMESTAMPTZ;
ALTER TABLE scripts ADD COLUMN narrative_scene_count INT;
```

Pros: No migration table, simple read/write, stores full response.

### Option B: Dedicated Table (If separating concerns)

```sql
CREATE TABLE narrative_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    analysis_data JSONB NOT NULL,
    scene_count_at_generation INT,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(script_id)
);
```

**Recommendation**: Option A for MVP. The data is tightly coupled to the script and there's no multi-version requirement.

---

## 10. File Plan

### New Files — Frontend

```
frontend/src/components/narrative/
  ├── NarrativeDashboard.jsx       # Page container, data fetching, state management
  ├── NarrativeDashboard.css       # Page-level layout styles
  ├── NarrativeHero.jsx            # Hero banner with theme/tone/characters
  ├── StoryArcViz.jsx              # SVG 3-act arc visualization
  ├── PacingHeatmap.jsx            # Emotional intensity heatmap strip
  ├── CharacterJourneys.jsx        # Character arc cards with sparklines
  ├── RelationshipWeb.jsx          # SVG radial relationship graph
  ├── KeyMoments.jsx               # Vertical timeline of turning points
  ├── NarrativeCard.jsx            # Shared card wrapper component
  └── MiniArcLine.jsx              # Reusable tiny sparkline SVG
```

### New Files — Backend

```
backend/services/narrative_service.py        # Aggregation logic + Gemini prompt
```

### Modified Files

```
frontend/src/App.jsx                                    # Add route
frontend/src/components/metadata/ScriptHeader.jsx       # Add "Narrative" button
frontend/src/services/apiService.js                     # Add getNarrative(), analyzeNarrative()
backend/routes/supabase_routes.py                       # Add GET + POST endpoints
backend/db/migrations/032_narrative_analysis.sql         # Schema change (if Option B)
```

---

## 11. Entry Point

**ScriptHeader.jsx** — Add a new button between "Reports" and "Schedule":

```jsx
<button
    className="header-action-btn primary"
    title="Narrative Intelligence"
    onClick={() => navigate(`/scripts/${scriptId}/narrative`)}
>
    <BookOpen size={18} />
    <span>Narrative</span>
</button>
```

**Icon**: `BookOpen` from lucide-react  
**Position**: After "Reports", before "Schedule"

---

## 12. UX States

| State | Visual | Behavior |
|-------|--------|----------|
| **Loading** | Skeleton cards matching each section's shape, amber shimmer animation | Auto on page load |
| **No Analysis** | Hero card area shows CTA: large BookOpen icon + "Discover your script's narrative" heading + description of insights + amber "Analyze Narrative" button | User clicks to trigger |
| **Analyzing** | Spinner in hero area + "Analyzing narrative structure..." + estimated time | Polling or SSE for completion |
| **Complete** | Full dashboard with all 6 sections | Default state |
| **Error** | Toast notification + "Retry" button in hero area | User retries |
| **Stale** | Amber banner at top: "Scenes have changed since last analysis — n new scenes" + "Re-analyze" button | Detected by comparing `narrative_scene_count` vs current scene count |

### Empty State (No Analysis) — Detailed

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│                      📖                                      │
│                                                              │
│           Discover Your Script's Narrative                   │
│                                                              │
│   AI-powered analysis of your screenplay's story structure,  │
│   character arcs, relationships, pacing, and key moments.    │
│                                                              │
│   ✦ Theme & tone identification                             │
│   ✦ Plot structure detection (10 types supported)           │
│   ✦ Character arc visualization                             │
│   ✦ Relationship dynamics                                   │
│   ✦ Pacing & emotional flow                                 │
│   ✦ Key structural beats (adapted per structure type)       │
│                                                              │
│              [ ✨ Analyze Narrative ]                        │
│                                                              │
│   Requires analyzed scenes. ~15 seconds for 100 scenes.     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 13. Responsive Behavior

| Breakpoint | Layout Changes |
|------------|----------------|
| **≥1200px** | 2-column grid for bottom 4 cards (Character Journeys + Relationship Web, Tone Timeline + Key Moments) |
| **768–1199px** | Single column, all cards stacked full-width |
| **<768px** | Hero: pills wrap to vertical stack. Arc viz: horizontally scrollable. Relationship Web: hidden (replaced by simple relationship list). Key Moments: compact list. |

---

## 14. Accessibility

- All SVG charts: `role="img"` + `aria-label` describing the visualization
- Color is never the sole indicator — shapes (dots, diamonds, dashes) differentiate data types
- Keyboard: Tab through Key Moments cards, Enter to navigate to scene
- Screen reader: Alt text for hero banner summarizing theme/tone/protagonist

---

## 15. Performance Considerations

- **Single API call** for all narrative data (no waterfall)
- **SVG rendering**: Max ~200 scene dots — well within browser SVG limits
- **Relationship Web**: Cap at 15 characters max to prevent visual overload (show top 15 by scene count)
- **Sparklines**: Pure SVG, no heavy charting library needed
- **Caching**: Narrative analysis stored server-side, only re-generated on user action
- **Stale detection**: Compare `narrative_scene_count` vs current — no extra API call

---

## 16. Phase Plan

### Phase 1: MVP (~3 days)

| Task | Component | Effort |
|------|-----------|--------|
| Backend: `narrative_service.py` + Gemini prompt + aggregation | Service | 0.5d |
| Backend: API endpoints (GET + POST) + schema migration | Routes + DB | 0.5d |
| Frontend: `NarrativeDashboard.jsx` + route + ScriptHeader button | Container | 0.5d |
| Frontend: `NarrativeHero.jsx` | Hero | 0.25d |
| Frontend: `PacingHeatmap.jsx` | Heatmap | 0.5d |
| Frontend: `KeyMoments.jsx` | Timeline | 0.5d |
| Frontend: Empty state + loading skeletons + error handling | UX states | 0.25d |

**Delivers**: Route, hero banner, pacing heatmap, key moments timeline. Functional end-to-end.

### Phase 2: Visualizations (~2 days)

| Task | Component | Effort |
|------|-----------|--------|
| Frontend: `StoryArcViz.jsx` (SVG 3-act curve) | Arc chart | 1d |
| Frontend: `CharacterJourneys.jsx` + `MiniArcLine.jsx` | Character cards | 0.75d |
| Frontend: Tone Timeline card (bonus) | Tone viz | 0.25d |

**Delivers**: Full story arc visualization, character journey sparklines.

### Phase 3: Advanced (~2 days)

| Task | Component | Effort |
|------|-----------|--------|
| Frontend: `RelationshipWeb.jsx` (SVG radial graph) | Relationship viz | 1d |
| Frontend: Click-through navigation (scene dots → SceneViewer) | Interaction | 0.25d |
| Frontend: Activate CharacterProfile page (wire existing analysis data) | Page | 0.5d |
| Frontend: Responsive polish + mobile fallbacks | Polish | 0.25d |

**Delivers**: Relationship graph, full interactivity, character profiles.

---

## 17. Dependencies

### Existing (no new installs needed)
- `lucide-react` — Icons
- `react-router-dom` — Routing
- Gemini API (via `google.generativeai`) — AI synthesis
- Supabase client — Data storage

### Potentially New
- None required for MVP. All visualizations are pure SVG.
- **Optional future**: `d3-force` for relationship web force simulation (Phase 3 only, can start with manual radial layout)

---

## 18. Success Criteria

1. User can navigate to `/scripts/:scriptId/narrative` from ScriptHeader
2. Empty state CTA triggers analysis; results render within 30 seconds
3. Hero banner displays theme, tone, conflict type, protagonist/antagonist, and auto-detected structure type
4. Structure type dropdown shows all 10 supported types; selecting one triggers re-analysis with that lens
5. Pacing heatmap renders all scenes with correct color coding
6. Key moments timeline shows structure-appropriate beats (e.g. "Call to Adventure" for hero's journey, "All Is Lost" for save the cat) with scene links
7. Story arc visualization adapts region bands and milestone labels per detected/selected structure type (Phase 2)
8. Character journeys show top 5 characters with sparklines and arc summaries (Phase 2)
9. Relationship web renders character connections with typed edges (Phase 3)
10. Stale detection correctly identifies when re-analysis is needed
11. `structure_type_auto_detected` flag correctly reflects whether AI detected or user overrode
12. Page loads in <2 seconds (cached data), analysis completes in <30 seconds (AI call)
