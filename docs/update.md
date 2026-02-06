# SCRIPDOWN-BREAKDOWN-UX — Scene Breakdown UI/UX Refactor

> **Ticket:** `SCRIPDOWN-BREAKDOWN-UX`  
> **Objective:** Transform the flat breakdown grid into a layered, filmmaker-centric interface with tiered rendering, department filtering, and elevated creative intelligence.  
> **Last Updated:** 2026-02-06  
> **Status:** ✅ Complete — All 6 Phases Done

---

## Pre-Implementation Checklist

### Dependencies (Frontend)
- [x] `lucide-react@^0.554.0` — Icons for all categories, stat chips, accordions *(installed)*
- [x] `react@^18.3.1` — useState, useEffect, useCallback, useMemo *(installed)*
- [x] `recharts@^3.6.0` — Available if we need the DNA strip as SVG chart *(installed, optional)*
- [x] No new packages required — all UI is achievable with existing deps + CSS

### Dependencies (Backend)
- [x] Breakdown endpoint exists: `GET /api/scripts/:id/scenes/:id/breakdown` *(live)*
- [x] Response includes: `breakdown`, `enrichment`, `total_extractions`, `avg_confidence` *(verified)*
- [x] No backend changes required — this is a pure frontend refactor

### Dependencies (Config / Shared)
- [x] `extractionClassConfig.js` exports: `SCENE_CATEGORIES` (11 categories), `CATEGORY_DEPARTMENTS` (dept mapping), `CLASS_METADATA`, `getClassMetadata()` *(verified)*
- [x] `sceneUtils.js` exports: `getSceneEighthsDisplay()`, `getSceneEighths()`, `formatEighths()` *(verified)*
- [x] CSS design tokens in `index.css`: `--bg-app`, `--bg-card`, `--bg-elevated`, `--gray-*`, `--primary-*`, `--text-*`, `--border-*`, `--shadow-*`, `--success`, `--warning`, `--danger` *(verified)*

### Files to Modify
| File | Scope of Change |
|------|-----------------|
| `frontend/src/components/scenes/SceneDetail.jsx` | **Major rewrite** — replace flat grid with layered architecture |
| `frontend/src/components/scenes/SceneDetail.css` | **Major rewrite** — new accordion, dashboard, intelligence panel styles |
| `frontend/src/config/extractionClassConfig.js` | **Minor** — may add department label mappings for the Lens bar |

### Files That Must NOT Break (Consumers of SceneDetail)
| File | Dependency |
|------|-----------|
| `SceneViewer.jsx` | Renders `<SceneDetail>` with props: `scene`, `scriptId`, `onAnalyze`, `isAnalyzing`, `pageMapping` |
| `NoteDrawer.jsx` | Opened by SceneDetail via `openDrawer(category, title)` — must preserve this interface |

### Preserved Interfaces (Do Not Change)
```
SceneDetail Props (input contract):
  scene          : Object  — scene row from Supabase (scene_number, setting, int_ext, etc.)
  scriptId       : String  — UUID
  onAnalyze      : Function(sceneId) — triggers single-scene analysis
  isAnalyzing    : Boolean — shows spinner state
  pageMapping    : Object  — page number data

Internal APIs consumed:
  getSceneBreakdown(scriptId, sceneId) → { breakdown, enrichment, avg_confidence, total_extractions }
  getScriptNotes(scriptId, { scene_id }) → { notes[] }

NoteDrawer interface (must preserve):
  openDrawer(categoryKey, categoryLabel) → opens slide-out drawer for that category
```

---

## Data Contract: Breakdown Endpoint Response

```json
{
  "script_id": "uuid",
  "scene_id": "uuid",
  "total_extractions": 42,
  "avg_confidence": 0.91,
  "breakdown": {
    "characters": [
      { "id": "uuid", "text": "JOHN", "attributes": { "name": "JOHN", "role": "protagonist" }, "confidence": 0.95 }
    ],
    "props": [...],
    "wardrobe": [...],
    "makeup_hair": [...],
    "special_fx": [...],
    "vehicles": [...],
    "locations": [...],
    "sound": [...],
    "animals": [],
    "extras": [],
    "stunts": []
  },
  "enrichment": {
    "emotion": [{ "id": "uuid", "text": "anxiety", "attributes": { "intensity": "high" }, "confidence": 0.85 }],
    "dialogue": [{ "id": "uuid", "text": "Don't move.", "attributes": { "tone": "threatening", "character": "JOHN" }, "confidence": 0.90 }],
    "relationship": [{ "id": "uuid", "text": "JOHN and SARAH", "attributes": { "dynamic": "tension" }, "confidence": 0.80 }]
  }
}
```

**Key observations for UI design:**
- `breakdown` categories may be empty objects `{}` or missing keys entirely
- `enrichment` may be `null` or `{}` if no enrichment data exists
- Each item has `.confidence` (0.0–1.0) — usable for trust indicators
- Each item has `.attributes` — variable keys per extraction class
- `avg_confidence` is pre-computed — use directly for the confidence bar
- `total_extractions` — use for complexity calculation

---

## UI/UX Considerations

### 1. Information Architecture
- **Problem**: 11 equal-weight cards + enrichment = visual overload. Empty cards waste space.
- **Solution**: 3-tier rendering (Hero/Summary/Hidden) based on item count, sorted descending.
- **Principle**: *Progressive disclosure* — show the most, hide the least, let the user expand.

### 2. Dark Theme Compliance
- All new elements must use existing CSS variables (`--bg-card`, `--gray-*`, `--text-*`)
- Confidence dots: use `--success` (green ≥0.9), `--warning` (yellow 0.7–0.89), `--danger` (orange <0.7)
- Scene DNA strip segments: use each category's `color` from `SCENE_CATEGORIES`
- Accordion borders: use `--border-color` with left-accent from category color
- Stat chips: subtle `rgba()` backgrounds matching each category color at 15% opacity

### 3. Interaction Design
- **Accordion**: Click header row to expand/collapse. Multiple can be open simultaneously.
- **Keyboard**: `Enter`/`Space` to toggle accordion. `Tab` to navigate between rows.
- **Note Drawer**: Clicking the note badge OR an "Add Note" button within expanded accordion opens the NoteDrawer — same `openDrawer(category, title)` interface.
- **Department Lens**: Pill bar filters in-place (no route change). "All" is default. Selection persists during scene navigation within the same session.
- **Scene Intelligence**: Collapsible panel, open by default if enrichment data exists.

### 4. Responsive Behavior
- **Desktop (≥1024px)**: Full layered layout within the `viewer-main` panel (currently ~70% width in split view)
- **Tablet (768–1023px)**: Stack stat chips into 2 rows; accordions remain full-width
- **Mobile (<768px)**: Single column; Department Lens becomes a horizontal scrollable pill row
- **With PDF Panel open**: SceneDetail gets narrower (~50%). Stat chips should wrap gracefully. Accordions stay full-width within their container.

### 5. Accessibility (a11y)
- Accordion headers: `role="button"`, `aria-expanded`, `aria-controls`
- Stat chips: `aria-label="5 Characters"` for screen readers
- Confidence dots: `title` tooltip with exact percentage
- Color is never the sole indicator — always paired with text/icon
- Department Lens pills: proper `role="tablist"` / `role="tab"` semantics

### 6. Performance
- `getCategoryItems()` already uses `useCallback` — preserve memoization
- Accordion expand/collapse: CSS `max-height` transition (no JS layout recalculation)
- Department Lens filtering: `useMemo` over breakdown data, keyed on selected department
- Scene DNA strip: pure CSS flexbox with colored divs (no SVG/canvas overhead)
- Avoid re-fetching breakdown data when only toggling accordions or switching departments

### 7. Empty & Loading States
- **No breakdown data**: Show current analyze prompt (unchanged)
- **Breakdown loading**: Subtle skeleton shimmer on accordion rows (not a full-page spinner)
- **All categories empty**: Show a friendly message: "No extraction data found for this scene"
- **Enrichment empty**: Hide Scene Intelligence panel entirely (no empty card)
- **Department Lens with no matches**: "No items for [Department] in this scene"

### 8. Transition from Current UI
- The `breakdown-grid` class and flat card layout will be **replaced**, not augmented
- All 11 `SCENE_CATEGORIES` are preserved — just rendered differently
- The `NoteDrawer` integration is preserved identically
- The `richBreakdown` / `enrichment` state management is preserved
- The `getCategoryItems()` fallback logic (rich → flat) is preserved

---

## Assumptions to Validate

| # | Assumption | Risk | Validation |
|---|-----------|------|------------|
| A1 | `avg_confidence` is always returned by the breakdown endpoint | Low | Verified in endpoint code — defaults to `0.0` if no extractions |
| A2 | `SCENE_CATEGORIES` keys always match `breakdown` response keys | Medium | Both use the same mapping via `_extraction_class_to_category()` — verified |
| A3 | `CATEGORY_DEPARTMENTS` is complete for all 11 categories | Low | Verified — all 11 categories have department mappings |
| A4 | Scene `page_length_eighths` or `page_start/page_end` is always available | Medium | Falls back via `getSceneEighths()` chain — verified |
| A5 | Enrichment `attributes` keys are consistent (`intensity`, `tone`, `dynamic`, `character`) | Medium | Depends on LangExtract prompt — may vary. UI must handle missing attrs gracefully |
| A6 | NoteDrawer accepts any `category` key from SCENE_CATEGORIES | Low | Verified — uses `note_type` field matching category keys |
| A7 | No other component imports from SceneDetail.css | Low | CSS is scoped — only SceneDetail.jsx imports it |

---

## Subtask Plan

```json
{
  "ticket_id": "SCRIPDOWN-BREAKDOWN-UX",
  "subtasks": [
    {
      "id": 1,
      "status": "✅ DONE",
      "description": "Refactor SceneDetail breakdown grid into Tiered Accordion layout — hide empty categories, sort by item count, render Hero (≥4 items expanded) / Summary (1-3 inline) / Hidden (0 items with disclosure toggle). Replace flat grid with collapsible rows. Preserve NoteDrawer integration and getCategoryItems fallback.",
      "agent": "Coder",
      "dependencies": [],
      "effort": "large",
      "phase": 1,
      "acceptance_criteria": [
        "Categories with ≥4 items render expanded by default",
        "Categories with 1-3 items render as compact single-row summaries",
        "Categories with 0 items are hidden, with a disclosure toggle showing count",
        "Categories sorted by item count (highest first)",
        "Click accordion header to expand/collapse",
        "NoteDrawer opens on note badge click within any accordion row",
        "Keyboard accessible: Enter/Space toggles, Tab navigates"
      ]
    },
    {
      "id": 2,
      "status": "✅ DONE",
      "description": "Build Scene Dashboard Header — stat chips row (icon + count per non-empty category), complexity badge (Simple/Medium/Complex), confidence indicator bar, page length display using getSceneEighthsDisplay().",
      "agent": "Coder",
      "dependencies": [1],
      "effort": "medium",
      "phase": 2,
      "acceptance_criteria": [
        "Stat chips render for each non-empty category with correct icon and color",
        "Complexity badge: Simple (≤10 extractions), Medium (11-25), Complex (>25)",
        "Confidence bar: thin colored bar reflecting avg_confidence",
        "Page length shown using existing getSceneEighthsDisplay(scene)",
        "All elements use existing CSS design tokens"
      ]
    },
    {
      "id": 3,
      "status": "✅ DONE",
      "description": "Build Scene DNA strip — thin horizontal heatmap below stat chips. Each non-empty category gets a colored segment with width proportional to item count. Pure CSS flexbox.",
      "agent": "Coder",
      "dependencies": [2],
      "effort": "small",
      "phase": 2,
      "acceptance_criteria": [
        "Strip renders only for non-empty categories",
        "Segment colors match SCENE_CATEGORIES[key].color",
        "Width is proportional to item count relative to total_extractions",
        "Tooltip on hover shows category name and count",
        "Graceful when only 1 category has data (full width, single color)"
      ]
    },
    {
      "id": 4,
      "status": "✅ DONE",
      "description": "Implement Department Lens filter bar — horizontal pill/segmented control. 'All' shows full tiered layout. Selecting a department shows only categories mapped in CATEGORY_DEPARTMENTS. Non-matching categories collapse. Persist selection in useState.",
      "agent": "Coder",
      "dependencies": [1],
      "effort": "medium",
      "phase": 3,
      "acceptance_criteria": [
        "Pill bar renders below the dashboard header",
        "Department list derived from unique values in CATEGORY_DEPARTMENTS",
        "'All' is selected by default and shows full tiered layout",
        "Selecting a department filters accordion to relevant categories only",
        "Stat chips and DNA strip also filter to match selected department",
        "Empty department filter shows: 'No items for [Dept] in this scene'",
        "Selection persists across accordion expand/collapse but resets on scene change"
      ]
    },
    {
      "id": 5,
      "status": "✅ DONE",
      "description": "Elevate Enrichment to 'Scene Intelligence' panel — collapsible section with premium styling. Emotion intensity bars (not just text), dialogue grouped by character with tone badges, relationship pairs with dynamic indicators.",
      "agent": "Coder",
      "dependencies": [1],
      "effort": "medium",
      "phase": 4,
      "acceptance_criteria": [
        "Section titled 'Scene Intelligence' with brain icon",
        "Collapsible — open by default if enrichment data exists, hidden if empty",
        "Emotions: render intensity as a small bar (high=full, medium=half, low=quarter)",
        "Dialogue: grouped by attributes.character, each line shows tone badge",
        "Relationships: render as 'CharA ↔ CharB' with dynamic label",
        "Missing attributes handled gracefully (no crash, fallback to text-only)",
        "Capped at 5 dialogue lines with '+N more' disclosure"
      ]
    },
    {
      "id": 6,
      "status": "✅ DONE",
      "description": "Add per-item Confidence Indicators — colored dot next to each extraction item. Green (≥0.9), Yellow (0.7-0.89), Orange (<0.7). Tooltip with exact percentage.",
      "agent": "Coder",
      "dependencies": [1],
      "effort": "small",
      "phase": 5,
      "acceptance_criteria": [
        "Every item in expanded accordion shows a confidence dot",
        "Color thresholds: ≥0.9 green, 0.7-0.89 yellow, <0.7 orange",
        "Dot has title attribute: 'AI Confidence: 94%'",
        "Dot is small (8px) and does not disrupt item layout",
        "Works for both rich items and flat fallback items (flat = no dot)"
      ]
    },
    {
      "id": 7,
      "status": "✅ DONE",
      "description": "UX evaluation pass — keyboard a11y, tablet responsiveness, dark theme contrast, interaction states, visual hierarchy verification across all layers.",
      "agent": "UX",
      "dependencies": [1, 2, 3, 4, 5, 6],
      "effort": "medium",
      "phase": 6,
      "acceptance_criteria": [
        "All interactive elements keyboard accessible",
        "WCAG 2.1 AA contrast ratios met for text on dark backgrounds",
        "Accordion animation is smooth (CSS transition, no jank)",
        "Layout works at 768px, 1024px, and 1440px widths",
        "With PDF panel open, SceneDetail remains usable (no overflow/clip)"
      ]
    },
    {
      "id": 8,
      "status": "✅ DONE",
      "description": "Integration testing — breakdown data flow through all layers, edge cases (0/few/many extractions), department filtering, accordion state persistence across scene changes.",
      "agent": "Tester",
      "dependencies": [7],
      "effort": "medium",
      "phase": 6,
      "acceptance_criteria": [
        "Scene with 0 extractions: shows analyze prompt correctly",
        "Scene with 3 extractions: renders summary tier only",
        "Scene with 40+ extractions: renders hero + summary tiers",
        "Department lens correctly filters categories",
        "Switching scenes resets accordion state and fetches new breakdown",
        "NoteDrawer opens/closes correctly from within accordion",
        "Enrichment panel shows/hides based on data availability"
      ]
    }
  ]
}
```

---

## Dependency Graph

```
[Phase 1] Tiered Accordion ✅ ────┬──> [Phase 2] Dashboard Header + DNA Strip ✅
                                  ├──> [Phase 3] Department Lens ✅
                                  ├──> [Phase 4] Scene Intelligence ✅
                                  └──> [Phase 5] Confidence Indicators ✅
                                           │
                  All Phases ──────────────> [Phase 6] UX Eval + Integration Tests ✅
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Accordion animation jank on large item lists | Medium | Low | Use CSS `max-height` + `overflow: hidden`, not JS height calculation |
| Department Lens creates confusion ("where did my data go?") | Medium | Medium | Clear "Showing: [Department]" label + easy "All" reset |
| Enrichment `attributes` keys vary between scripts | High | Low | Always check for key existence; render text-only as fallback |
| PDF panel + SceneDetail at narrow width clips content | Medium | Medium | Test at 50% width; use `min-width` on critical elements |
| Breaking NoteDrawer integration during refactor | Low | High | Preserve `openDrawer(categoryKey, label)` interface exactly |
| Flat fallback data (no extraction_metadata) renders differently | Medium | Medium | Maintain `getCategoryItems()` dual-path; test both paths |

---

## Visual Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│  SCENE DASHBOARD HEADER                                         │
│  Scene 14  ·  INT. WAREHOUSE — NIGHT           1 3/8 pg        │
│  Tone: Tense  ·  Atmosphere: Dark, industrial                   │
│                                                                 │
│  [👥5] [📦3] [👗2] [🚗1] [🔊2] [✨1]    Confidence: ██████░ 91% │
│  ▓▓▓▓▓▓▓▒▒▒▒▒░░░░░▒▒▓▓  ← Scene DNA strip                    │
│  Complexity: Medium                                              │
├─────────────────────────────────────────────────────────────────┤
│  DEPARTMENT LENS                                                 │
│  [All] [Director] [Costume] [Props] [Sound] [VFX] [Locations]  │
├─────────────────────────────────────────────────────────────────┤
│  DESCRIPTION                                                     │
│  John enters the warehouse cautiously...                         │
│  Action: Gunfire erupts from the rafters                        │
├─────────────────────────────────────────────────────────────────┤
│  TIERED ACCORDION BREAKDOWN                                     │
│                                                                 │
│  ▾ [●] Characters (5)                          [🗒️2]           │
│    JOHN       protagonist  ● 95%                                │
│    SARAH      antagonist   ● 92%                                │
│    DETECTIVE  supporting   ● 88%                                │
│    WAITRESS   background   ● 71%  ⚠                            │
│    BOUNCER    background   ● 94%                                │
│                                                                 │
│  ▸ [●] Props (3)                                [🗒️0]          │
│  ▸ [●] Wardrobe (2)                             [🗒️1]          │
│  ▸ [●] Vehicles (1)                                             │
│  ▸ [●] Sound (2)                                                │
│  ▸ [●] Special FX (1)                                           │
│                                                                 │
│  ⌄ +5 empty categories                                          │
├─────────────────────────────────────────────────────────────────┤
│  SCENE INTELLIGENCE                                    [▾]      │
│  ┌─Emotions──────┐ ┌─Dialogue────────┐ ┌─Relationships─┐       │
│  │ anxiety ████░░ │ │ JOHN:           │ │ JOHN ↔ SARAH  │       │
│  │ anger   ███░░░ │ │  "Don't move"  │ │  tension       │       │
│  └────────────────┘ │  tone: threat   │ └───────────────┘       │
│                     └────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Log

### Phase 1 — Tiered Accordion ✅ (2026-02-06)

**Files modified:**
- `frontend/src/components/scenes/SceneDetail.jsx` — Major rewrite
- `frontend/src/components/scenes/SceneDetail.css` — Major rewrite

**What was built:**
- Replaced flat `breakdown-grid` (11-card grid) with a tiered accordion layout
- `useMemo` splits `SCENE_CATEGORIES` into three tiers: `heroCategories` (≥4 items), `summaryCategories` (1-3), `emptyCategories` (0)
- Categories sorted by item count descending
- Hero rows auto-expand on scene load via `expandedCategories` state
- Summary rows show inline tag previews when collapsed (up to 3 tags + "+N" overflow)
- Empty categories hidden behind `showEmptyCategories` disclosure toggle (`Eye`/`EyeOff` icons)
- Each accordion row has: chevron, colored icon, label, count pill, rich badge, note badge (opens NoteDrawer), add-note button (hover-reveal)
- `aria-expanded`, `aria-controls`, `role="button"`, `tabIndex={0}`, `onKeyDown` (Enter/Space) for keyboard a11y
- `getCategoryItems()` fallback logic preserved (rich → flat)
- `NoteDrawer` integration preserved — `openDrawer(category, title)` interface unchanged
- Enrichment section preserved identically
- Loading skeleton with shimmer animation
- Old `.breakdown-grid`, `.breakdown-card`, `.card-header`, clickable card hover hints removed
- CSS animation `accordionSlideIn` for smooth panel reveal

**New imports:** `ChevronRight`, `ChevronDown`, `Eye`, `EyeOff`
**New state:** `expandedCategories`, `showEmptyCategories`

---

### Phase 2 — Dashboard Header + DNA Strip ✅ (2026-02-06)

**Files modified:**
- `frontend/src/components/scenes/SceneDetail.jsx` — Additive (new section between header and content)
- `frontend/src/components/scenes/SceneDetail.css` — Additive (~160 lines of new CSS)

**What was built:**

**Dashboard Header (`.scene-dashboard`):**
- Stat chips row: one chip per non-empty category, colored icon + count, using `SCENE_CATEGORIES[key].color` with alpha background
- Complexity badge: `Simple` (≤10 extractions, green), `Medium` (11-25, yellow), `Complex` (>25, red) — uses `totalExtractions` from API
- Page length badge: displays `getSceneEighthsDisplay(scene)` with monospace font
- Confidence bar: thin 4px track with colored fill — green (≥90%), yellow (70-89%), orange (<70%) — uses `avgConfidence` from API
- Responsive: stacks vertically at `≤768px`

**DNA Strip (`.dna-strip`):**
- Thin 6px horizontal heatmap below dashboard
- Each non-empty category gets a colored segment with `flex: count` (proportional width)
- Segment colors match `SCENE_CATEGORIES[key].color`
- `title` attribute on hover shows `"Category: N"`
- Graceful with single category (full width, single color)
- Rounded ends on first/last/only segments

**New imports:** `BarChart3`, `Gauge`
**New state:** `avgConfidence`, `totalExtractions`
**Data source:** `data.avg_confidence` and `data.total_extractions` from `getSceneBreakdown()` response

---

### Phase 3 — Department Lens ✅ (2026-02-06)

**Files modified:**
- `frontend/src/components/scenes/SceneDetail.jsx` — Additive (new state, memo, pill bar UI)
- `frontend/src/components/scenes/SceneDetail.css` — Additive (~55 lines of new CSS)

**What was built:**

**Department Lens (`.department-lens`):**
- Horizontal pill bar rendered between dashboard header and content
- `DEPARTMENTS` derived at module level from `CATEGORY_DEPARTMENTS` via `Set` extraction
- `DEPT_LABELS` map for human-readable names (Director, Casting, Costume, etc.)
- "All" pill selected by default — shows full tiered layout
- Selecting a department filters accordion, stat chips, and DNA strip to only relevant categories
- `filteredHero`, `filteredSummary`, `filteredEmpty` computed via `useMemo` keyed on `selectedDepartment`
- Empty department filter shows: "No items for [Dept] in this scene" with `Filter` icon
- Empty category disclosure only visible in "All" mode
- Selection resets on scene change via `setSelectedDepartment('all')` in scene reset effect
- `role="tablist"` on container, `role="tab"` + `aria-selected` on each pill
- `overflow-x: auto` with hidden scrollbar for mobile horizontal scroll
- Active pill uses `--primary-500` background with dark text

**New state:** `selectedDepartment`

---

### Phase 4 — Scene Intelligence Panel ✅ (2026-02-06)

**Files modified:**
- `frontend/src/components/scenes/SceneDetail.jsx` — Replaced enrichment section with Scene Intelligence
- `frontend/src/components/scenes/SceneDetail.css` — Replaced enrichment CSS (~180 lines of new CSS)

**What was built:**

**Scene Intelligence (`.intelligence-section`):**
- Collapsible panel with `Brain` icon and purple gradient header
- Open by default if enrichment data exists, hidden entirely if no enrichment
- `role="button"`, `aria-expanded`, `aria-controls`, `tabIndex={0}`, keyboard accessible (Enter/Space)
- Chevron indicator (down when open, right when closed)
- Smooth `accordionSlideIn` animation on reveal

**Emotions — Intensity Bars:**
- Each emotion rendered as a row with label + intensity bar + intensity label
- Bar width: `high/intense` → 100%, `medium/moderate` → 60%, `low/subtle` → 30%, unknown → 50%
- Pink gradient fill (`#db2777` → `#ec4899`)
- Confidence dot on each emotion item

**Dialogue — Grouped by Character:**
- Dialogue lines grouped by `attributes.character` (fallback: "Unknown")
- Character name in teal uppercase header
- Each line shows quoted text (italic) + tone badge (teal pill)
- Capped at 5 lines total with "+N more" disclosure
- Confidence dot on each dialogue line

**Relationships — Pairs with Dynamic:**
- Each relationship shows `attributes.characters` (fallback: `r.text`) as primary label
- Dynamic label in pink (capitalize)
- Type shown as `attr-pill`
- Confidence dot on each relationship

**New imports:** `Brain`, `ArrowLeftRight`
**New state:** `intelligenceOpen`
**Removed:** Old `.enrichment-section`, `.enrichment-grid`, `.enrichment-card` markup and CSS

---

### Phase 5 — Per-item Confidence Indicators ✅ (2026-02-06)

**Files modified:**
- `frontend/src/components/scenes/SceneDetail.jsx` — Added confidence dots to accordion items and intelligence items
- `frontend/src/components/scenes/SceneDetail.css` — Added `.confidence-dot` and `.rich-item-header` styles

**What was built:**

**Confidence Dots (`.confidence-dot`):**
- 8px colored circle next to each rich extraction item in expanded accordion panels
- Color thresholds: `≥0.9` → green (`--success`), `0.7–0.89` → yellow (`--warning`), `<0.7` → orange (`--danger`)
- `title` attribute: `"AI Confidence: 94%"` for screen reader / tooltip access
- Helper function `getConfidenceColor(confidence)` at module scope
- Only rendered for rich items (`typeof conf === 'number'`); flat fallback items show no dot
- Applied across all contexts: accordion items, emotion rows, dialogue lines, relationship pairs

**Structural change:**
- Accordion expanded items now wrapped in `.rich-item-header` (flex row) containing tag + confidence dot
- Preserves existing tag styling and attribute pills below

---

### Phase 6 — UX Evaluation Pass ✅ (2026-02-06)

**Scope:** Keyboard a11y, responsive behavior, dark theme compliance, visual hierarchy, dead code cleanup.

**A11y verification:**
- ✅ All accordion headers: `role="button"`, `aria-expanded`, `aria-controls`, `tabIndex={0}`, `onKeyDown` (Enter/Space)
- ✅ Department Lens: `role="tablist"` container, `role="tab"` + `aria-selected` on pills
- ✅ Intelligence panel: `role="button"`, `aria-expanded`, `aria-controls="intelligence-panel"`, keyboard accessible
- ✅ Intelligence body: `id="intelligence-panel"`, `role="region"` for proper linkage
- ✅ Confidence dots: `title` tooltip with exact percentage — color never sole indicator
- ✅ Stat chips: `aria-label` with count + category label
- ✅ DNA strip: `aria-label` on container, `title` on each segment
- ✅ Focus-visible outlines on interactive elements (`--primary-500` outline)

**Responsive verification:**
- ✅ Dashboard row stacks vertically at `≤768px`
- ✅ Intelligence grid collapses to single column at `≤768px`
- ✅ Department Lens scrolls horizontally on narrow screens (hidden scrollbar, touch-friendly)
- ✅ Stat chips wrap gracefully with `flex-wrap: wrap`
- ✅ Accordions remain full-width in all viewports

**Dark theme compliance:**
- ✅ All new elements use CSS variables (`--bg-card`, `--bg-elevated`, `--border-color`, `--text-*`, `--gray-*`)
- ✅ Confidence colors use `--success`, `--warning`, `--danger` with fallbacks
- ✅ Intelligence panel uses subtle purple gradient that respects dark theme
- ✅ Tone badges, relationship dynamics, emotion bars all use RGBA colors for dark background compatibility

**Cleanup:**
- Removed dead `.enrichment-section`, `.enrichment-grid`, `.enrichment-card`, `.enrichment-card-header`, `.enrichment-items`, `.enrichment-item`, `.enrichment-text`, `.enrichment-more` CSS
- Replaced with comment: `/* (Legacy enrichment styles removed — replaced by Scene Intelligence panel) */`

---

### All Phases Complete ✅

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Tiered Accordion layout | ✅ Done |
| 2 | Dashboard Header + DNA Strip | ✅ Done |
| 3 | Department Lens filter bar | ✅ Done |
| 4 | Scene Intelligence panel | ✅ Done |
| 5 | Per-item Confidence Indicators | ✅ Done |
| 6 | UX Eval + Integration Tests | ✅ Done |

---

# NARRATIVE INTELLIGENCE EXPANSION

> **Objective:** Extend extraction beyond production breakdown into **story-level intelligence** — plot beats, character arcs, conflict tracking, themes, and structure mapping. This gives filmmakers creative insight alongside logistical data.

---

## What We Already Extract (Enrichment Baseline)

| Extraction Class | Attributes | Status |
|-----------------|------------|--------|
| `emotion` | character, emotion_type, intensity, trigger, manifestation | ✅ Live |
| `relationship` | characters, type, dynamic, development | ✅ Live |
| `dialogue` | character, tone, parenthetical, subtext | ✅ Live |
| `action` | type, intensity, characters, importance (`plot_critical`, `character_development`, `atmosphere`) | ✅ Live |
| `transition` | type, timing, time_jump, purpose | ✅ Live |

**Key insight:** The `action` class already has `importance: "plot_critical"` — this is essentially a beat marker. We can build on this foundation.

---

## New Extraction Classes (Tier 1 — Per-Scene via LangExtract)

These are new classes to add to `langextract_schema.py` with few-shot examples. The AI model already understands screenplay narrative structure.

### 1. `story_beat` — Turning Points & Plot Beats

The smallest unit of story change — a shift in value from positive to negative or vice versa.

```python
ExtractionClass(
    name="story_beat",
    description="Key story moments where something changes — decisions, revelations, complications, reversals",
    attributes=[
        "beat_type",          # revelation, decision, complication, confrontation, reversal, climax, resolution, setup
        "description",        # What happens in this beat
        "characters_involved",# Who participates
        "value_shift",        # positive_to_negative, negative_to_positive, neutral_to_negative, escalation
        "stakes",             # personal, relational, societal, life_death, professional
        "story_function"      # setup, escalation, midpoint, crisis, climax, denouement, subplot
    ],
    examples=[
        "Sarah discovers the forged letter — revelation, relational stakes",
        "John refuses to help — decision, value shift negative",
        "The door locks behind them — complication, escalation"
    ]
)
```

**Beat types explained:**
- **Revelation** — new information changes understanding ("She's been lying all along")
- **Decision** — character makes a choice that alters trajectory ("I'm going alone")
- **Complication** — obstacle or setback ("The bridge is out")
- **Confrontation** — characters clash directly ("You knew and said nothing!")
- **Reversal** — expectation flipped ("The ally is the villain")
- **Climax** — peak dramatic tension ("The final showdown")
- **Resolution** — conflict concludes ("They reconcile at the grave")
- **Setup** — plants information for later ("She notices the gun in the drawer")

### 2. `conflict` — Dramatic Conflict Per Scene

Every scene should have conflict — tracking it reveals dramatic structure.

```python
ExtractionClass(
    name="conflict",
    description="The central dramatic conflict in the scene — who wants what and what opposes them",
    attributes=[
        "conflict_type",      # person_vs_person, person_vs_self, person_vs_nature, person_vs_society, person_vs_fate
        "protagonists",       # Who's fighting for something
        "antagonists",        # Who/what opposes them
        "intensity",          # low, medium, high, explosive
        "resolution_status",  # unresolved, escalated, partially_resolved, resolved
        "stakes"              # what's at risk
    ],
    examples=[
        "SARAH vs JOHN — person_vs_person, escalated, relational stakes",
        "JOHN vs his guilt — person_vs_self, unresolved, personal stakes",
        "Team vs the storm — person_vs_nature, high intensity"
    ]
)
```

### 3. `theme` — Thematic Elements

What the script is "about" at a deeper level.

```python
ExtractionClass(
    name="theme",
    description="Thematic elements — abstract ideas the scene explores through its action and dialogue",
    attributes=[
        "theme_name",         # betrayal, redemption, power, identity, survival, love, justice, freedom, grief, truth
        "theme_type",         # central, supporting, emerging
        "expression",         # How it manifests in this scene
        "characters_involved" # Who embodies or confronts the theme
    ],
    examples=[
        "Betrayal (central) — manifests through the forged letter",
        "Trust (supporting) — John's refusal breaks remaining trust",
        "Redemption (emerging) — first sign of Robert's remorse"
    ]
)
```

### 4. `foreshadowing` — Setup & Payoff Markers

Track narrative setups and their eventual payoffs.

```python
ExtractionClass(
    name="foreshadowing",
    description="Elements that set up future events or pay off earlier setups — Chekhov's guns, dramatic irony, symbolic parallels",
    attributes=[
        "element",            # What's being set up or paid off
        "foreshadow_type",    # chekhov_gun, dramatic_irony, symbolic, parallel, callback
        "direction",          # setup (plants), payoff (resolves)
        "significance",       # minor, moderate, major
        "linked_element"      # What it connects to (if payoff, what was the setup?)
    ],
    examples=[
        "The gun in the drawer (setup, chekhov_gun, major)",
        "Sarah mentions she can't swim (setup, dramatic_irony, moderate)",
        "The gun fires (payoff, resolves drawer setup, major)"
    ]
)
```

---

## Cross-Scene Aggregations (Tier 2 — Post-Processing)

These derive from EXISTING + NEW extraction data aggregated across all scenes. No new extraction needed — pure computation.

### 5. Character Arc (Aggregated Journey)

Combine per-character data across scenes:
- `emotion` extractions → **emotional journey timeline** (scene-by-scene emotional states)
- `dialogue.tone` → **tone progression** (how they speak across the script)
- `relationship.development` → **relationship evolution** (forming → fracturing → reconciling)
- `action` involvement → **agency tracking** (passive observer vs active driver)
- `story_beat.characters_involved` → **beat participation** (how often they drive the plot)
- Scene count + page_length_eighths → **screen time** (% of script)

**Output shape:**
```json
{
  "character": "SARAH",
  "total_scenes": 14,
  "screen_time_eighths": 46,
  "screen_time_percent": 42,
  "emotional_journey": [
    { "scene_number": 1, "emotion": "calm", "intensity": "low" },
    { "scene_number": 5, "emotion": "anxious", "intensity": "moderate" },
    { "scene_number": 12, "emotion": "enraged", "intensity": "intense" }
  ],
  "tone_progression": [
    { "scene_number": 1, "tone": "gentle" },
    { "scene_number": 5, "tone": "clipped" },
    { "scene_number": 12, "tone": "shouting" }
  ],
  "relationship_evolution": {
    "JOHN": [
      { "scene_number": 1, "dynamic": "forming", "type": "romantic" },
      { "scene_number": 12, "dynamic": "fracturing", "type": "romantic" }
    ]
  },
  "beat_participation": 8,
  "agency": "high"
}
```

### 6. Story Structure Map (Auto-Detected)

Map `story_beat` extractions by page position to auto-detect classical structure:

| Marker | Detection Rule |
|--------|---------------|
| **Inciting Incident** | First `story_beat` with `story_function: "escalation"` or `beat_type: "complication"` in first 15% |
| **Lock In / End of Act 1** | Last beat before 25% mark with `story_function: "escalation"` |
| **Midpoint** | Beat nearest 50% with highest stakes or `beat_type: "reversal"` |
| **All Is Lost** | Beat with `value_shift: "*_to_negative"` nearest 75% |
| **Climax** | Highest-intensity beat cluster in 80-95% range |
| **Resolution** | Final beats with `beat_type: "resolution"` or `story_function: "denouement"` |

**Tension Curve formula:**
```
tension_score(scene) = 
    (conflict.intensity_weight * 0.3) +
    (emotion.intensity_max * 0.2) +
    (story_beat_count * 0.25) +
    (action.intensity_max * 0.15) +
    (stakes_weight * 0.1)
```

Produces a scene-by-scene line chart — perfect for `recharts` (already installed).

### 7. Relationship Web (Network)

Aggregate `relationship` extractions across all scenes:
- **Nodes** = unique characters
- **Edges** = relationship instances with type + development
- **Timeline** = how each edge evolves across scenes

V1: Rendered as a structured table/list.  
V2: Interactive graph visualization (future).

### 8. Theme Tracker (Cross-Script Thread)

Aggregate `theme` extractions by `theme_name`:
- Count occurrences per theme
- List scenes where each theme appears
- Track which characters embody each theme
- Show theme density (heatmap strip like Scene DNA but for themes)

---

## Updated Wireframe: Scene Intelligence Panel

The Scene Intelligence panel expands from 3 sections to a tabbed layout:

```
┌─ 🧠 Scene Intelligence ─────────────────────────────────────────────┐
│                                                                       │
│  [Beats] [Conflict] [Emotions] [Dialogue] [Relations] [Themes] [🔮]  │
│                                                                       │
│  ── Story Beats (active tab) ──────────────────────────────────────  │
│                                                                       │
│  ⚡ REVELATION                                              ● 92%    │
│     Sarah discovers the forged letter                                 │
│     value: neutral → negative  ·  stakes: relational                  │
│     function: escalation  ·  SARAH, JOHN                              │
│                                                                       │
│  ⚡ DECISION                                                ● 88%    │
│     John refuses to help                                              │
│     value: negative → worse  ·  stakes: personal                      │
│     function: crisis  ·  JOHN                                         │
│                                                                       │
│  ── Conflict (tab) ────────────────────────────────────────────────  │
│  ⚔️ Person vs Person  ·  intensity: HIGH  ·  status: ESCALATED       │
│     SARAH vs JOHN  ·  stakes: relational trust                        │
│                                                                       │
│  ── Themes (tab) ──────────────────────────────────────────────────  │
│  🏷️ Betrayal (central) — the forged letter reveals deception          │
│  🏷️ Trust (supporting) — John's refusal breaks remaining trust        │
│                                                                       │
│  ── Foreshadowing [🔮 tab] ───────────────────────────────────────  │
│  🔮 SETUP: The gun in the drawer  ·  Chekhov's Gun  ·  major         │
│  🔮 SETUP: Sarah mentions she can't swim  ·  dramatic irony          │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### Changes to Existing Wireframe

The **Tiered Accordion Breakdown** (production data) is **unchanged** — it remains the primary view for production departments.

The **Scene Intelligence Panel** below it **expands** to accommodate narrative data. The key design principle:

> **Production data lives in the Accordion. Story data lives in Scene Intelligence.**

This separation means:
- An AD scrolls through the accordion for logistics
- A director clicks Scene Intelligence for creative insight
- Both are on the same page, one scroll apart

---

## New Script-Level Pages (Cross-Scene Narrative Views)

Accessible from **ScriptHeader** buttons alongside existing "Reports", "Stripboard", "Manage":

### Page 1: Story Map (`/scripts/:id/story-map`)

```
┌─ Story Map ──────────────────────────────────────────────────────────┐
│                                                                       │
│  TENSION CURVE                                          [Export PDF]  │
│  10│              ╱╲                                                  │
│   8│         ╱╲  ╱  ╲      ╱╲                                        │
│   6│    ╱╲  ╱  ╲╱    ╲    ╱  ╲                                       │
│   4│   ╱  ╲╱          ╲  ╱    ╲                                      │
│   2│  ╱                ╲╱      ╲                                     │
│   0│──┬──┬──┬──┬──┬──┬──┬──┬──┬──╲                                   │
│     1  3  5  7  9  11 13 15 17 19 21                                 │
│    [-- Act 1 --][---- Act 2a ----][-- Act 2b --][Act 3]               │
│                                                                       │
│  STRUCTURAL MARKERS                                                   │
│  ┌────────────────────────────────────────────────────────┐           │
│  │ 📍 Inciting Incident   Sc3  (pg 8)   "Sarah finds body"│          │
│  │ 📍 Lock In             Sc7  (pg 18)  "Takes the case"  │          │
│  │ 📍 Midpoint            Sc14 (pg 55)  "Killer revealed"  │          │
│  │ 📍 All Is Lost         Sc20 (pg 78)  "Partner betrays"  │          │
│  │ 📍 Climax              Sc25 (pg 95)  "Confrontation"    │          │
│  │ 📍 Resolution          Sc28 (pg 108) "Justice served"   │          │
│  └────────────────────────────────────────────────────────┘           │
│                                                                       │
│  BEAT SHEET (all story beats, ordered by scene)                       │
│  ┌──────┬─────────────┬────────────┬───────────┬──────────┐          │
│  │ Sc#  │ Beat Type   │ Description│ Stakes    │ Function │          │
│  ├──────┼─────────────┼────────────┼───────────┼──────────┤          │
│  │ 1    │ Setup       │ Sarah at...│ personal  │ setup    │          │
│  │ 3    │ Complication│ Body found │ life_death│ escalation│         │
│  │ ...  │ ...         │ ...        │ ...       │ ...      │          │
│  └──────┴─────────────┴────────────┴───────────┴──────────┘          │
│                                                                       │
│  THEME DENSITY [heatmap strip per theme]                              │
│  Betrayal:   ░░▓▓▓░░░▓▓▓▓░░▓▓░░░▓▓▓▓▓▓░░                           │
│  Trust:      ▓▓░░░▓▓▓░░░░▓▓░░▓▓▓░░░░░░▓▓                           │
│  Redemption: ░░░░░░░░░░░░░░░░▓▓▓▓▓▓▓▓▓▓                             │
└───────────────────────────────────────────────────────────────────────┘
```

### Page 2: Character Arcs (`/scripts/:id/character-arcs`)

```
┌─ Character Arcs ─────────────────────────────────────────────────────┐
│                                                                       │
│  [SARAH ▾]  14 scenes  ·  42% screen time  ·  8 beats driven         │
│                                                                       │
│  EMOTIONAL JOURNEY                                      [Export PDF]  │
│  [recharts area chart — emotion intensity over scenes]                │
│  intense ┤    ╱╲              ╱╲                                      │
│  moderate┤   ╱  ╲     ╱╲    ╱  ╲    ╱╲                               │
│  subtle  ┤  ╱    ╲   ╱  ╲  ╱    ╲  ╱  ╲                             │
│          └──┬─────┬───┬───┬──┬────┬──┬──                              │
│            Sc1   Sc5  Sc8 Sc12 Sc15 Sc18 Sc24                        │
│          calm  anxious→ tense→ rage→ grief→ resolve                   │
│                                                                       │
│  DIALOGUE TONE SHIFT                                                  │
│  Sc1: gentle → Sc5: clipped → Sc12: shouting → Sc18: whispered →    │
│  Sc24: calm, firm                                                     │
│                                                                       │
│  KEY RELATIONSHIPS                                                    │
│  ┌────────────────────────────────────────────────────────┐           │
│  │ SARAH ↔ JOHN                                           │           │
│  │ Sc1: forming → Sc8: testing → Sc12: fracturing →       │          │
│  │ Sc20: broken → Sc24: reconciliation                     │          │
│  ├────────────────────────────────────────────────────────┤           │
│  │ SARAH ↔ BOSS                                           │           │
│  │ Sc1: professional → Sc8: tense → Sc20: adversarial     │          │
│  └────────────────────────────────────────────────────────┘           │
│                                                                       │
│  BEAT PARTICIPATION                                                   │
│  Drives: 8 beats  ·  Witnesses: 4 beats  ·  Agency: HIGH             │
└───────────────────────────────────────────────────────────────────────┘
```

### Page 3: Relationship Web (`/scripts/:id/relationships`)

```
┌─ Relationship Web ───────────────────────────────────────────────────┐
│                                                                       │
│  RELATIONSHIP MATRIX                                    [Export PDF]  │
│  ┌─────────┬─────────┬─────────┬─────────┐                           │
│  │         │ SARAH   │ JOHN    │ BOSS    │                            │
│  ├─────────┼─────────┼─────────┼─────────┤                           │
│  │ SARAH   │    —    │romantic │adversar.│                            │
│  │ JOHN    │romantic │    —    │profess. │                            │
│  │ BOSS    │adversar.│profess. │    —    │                            │
│  └─────────┴─────────┴─────────┴─────────┘                           │
│                                                                       │
│  EVOLUTION TIMELINE (click any cell above for detail)                 │
│  SARAH ↔ JOHN:                                                        │
│  Sc1 ●──forming──● Sc8 ●──testing──● Sc12 ●──fracturing──●          │
│  Sc20 ●──broken──● Sc24 ●──reconciliation──●                         │
│                                                                       │
│  RELATIONSHIP TYPES                                                   │
│  🔴 Adversarial (2)  🟢 Familial (1)  💜 Romantic (1)  🔵 Pro (2)   │
└───────────────────────────────────────────────────────────────────────┘
```

---

## New Report Types (Exportable)

Added to `report_service.py` presets and renderers:

| Report Key | Name | Data Source | Description |
|-----------|------|-------------|-------------|
| `story_beats` | Beat Sheet | `enrichment.story_beat` | All beats by scene with type, stakes, function — the writer's "beat sheet" |
| `character_arc` | Character Arc Report | Aggregated emotions + dialogue + relationships per character | Per-character journey with emotional timeline |
| `story_structure` | Story Structure Map | Aggregated beats + tension formula | Act breaks, structural markers, tension curve data |
| `conflict_report` | Conflict Tracker | `enrichment.conflict` | All conflicts across scenes with resolution status |
| `theme_analysis` | Theme Analysis | `enrichment.theme` | Thematic threads, scene density, character associations |
| `directors_vision` | Director's Vision Brief | ALL narrative data combined | **Premium flagship** — combined beat sheet + arcs + themes + tension curve. The creative brief a director takes into pre-production. |

### Director's Vision Brief (Flagship Report)

This is the standout feature — no competing tool generates this:

```
┌─ DIRECTOR'S VISION BRIEF ─────────────────────────────┐
│                                                         │
│  [Script Title]                                         │
│  by [Writer]                                            │
│                                                         │
│  1. STORY OVERVIEW                                      │
│     Tension curve chart + act structure summary          │
│                                                         │
│  2. THEMATIC ANALYSIS                                   │
│     Central + supporting themes with scene references    │
│                                                         │
│  3. CHARACTER ARCS                                       │
│     Per-character emotional journey + tone shift          │
│                                                         │
│  4. RELATIONSHIP MAP                                     │
│     Key relationships with evolution timeline            │
│                                                         │
│  5. BEAT SHEET                                           │
│     Complete scene-by-scene beat breakdown               │
│                                                         │
│  6. CONFLICT TRACKER                                     │
│     All conflicts with resolution status                 │
│                                                         │
│  7. FORESHADOWING & PAYOFF                               │
│     Setups with matched (or unmatched) payoffs           │
│                                                         │
│  8. PRODUCTION COMPLEXITY SUMMARY                        │
│     Scene-by-scene complexity scores + dept load         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Backend Changes Required

### New Files
| File | Purpose |
|------|---------|
| `backend/services/narrative_service.py` | Cross-scene aggregation: character arcs, story structure, tension curve, relationship web |
| `backend/routes/narrative_routes.py` | API endpoints for narrative pages |

### Modified Files
| File | Changes |
|------|---------|
| `backend/services/langextract_schema.py` | Add 4 new extraction classes: `story_beat`, `conflict`, `theme`, `foreshadowing` |
| `backend/services/langextract_examples.py` | Add few-shot examples for 4 new classes |
| `backend/routes/langextract_routes.py` | Add new classes to `ENRICHMENT_CLASSES` tuple in breakdown endpoint |
| `backend/services/report_service.py` | Add 6 new presets + renderers |
| `backend/app.py` | Register `narrative_bp` blueprint |

### New API Endpoints
| Endpoint | Method | Returns |
|----------|--------|---------|
| `GET /api/scripts/:id/narrative/character-arcs` | GET | Aggregated character journeys |
| `GET /api/scripts/:id/narrative/character-arcs/:character` | GET | Single character arc detail |
| `GET /api/scripts/:id/narrative/story-structure` | GET | Structure markers + tension curve data |
| `GET /api/scripts/:id/narrative/relationships` | GET | Relationship web with evolution |
| `GET /api/scripts/:id/narrative/themes` | GET | Theme tracker across script |
| `GET /api/scripts/:id/narrative/beats` | GET | All story beats ordered by scene |

### Enrichment Classification Update
```python
# In langextract_routes.py — breakdown endpoint
ENRICHMENT_CLASSES = (
    'emotion', 'relationship', 'transition', 'dialogue', 'action',
    'story_beat', 'conflict', 'theme', 'foreshadowing'  # NEW
)
```

This means **zero changes** to the breakdown categories or accordion layout — narrative data flows entirely through the enrichment path.

---

## Frontend Changes Required

### New Files
| File | Purpose |
|------|---------|
| `frontend/src/pages/StoryMapPage.jsx` | Story Structure Map with tension curve (uses recharts) |
| `frontend/src/pages/StoryMapPage.css` | Styling |
| `frontend/src/pages/CharacterArcPage.jsx` | Character Arc viewer with emotional journey chart |
| `frontend/src/pages/CharacterArcPage.css` | Styling |
| `frontend/src/pages/RelationshipWebPage.jsx` | Relationship matrix + evolution timeline |
| `frontend/src/pages/RelationshipWebPage.css` | Styling |

### Modified Files
| File | Changes |
|------|---------|
| `frontend/src/config/extractionClassConfig.js` | Add `story_beat`, `conflict`, `theme`, `foreshadowing` to `CLASS_METADATA` and `EXTRACTION_TO_SCENE_CATEGORY` (mapped to `null` — enrichment only) |
| `frontend/src/components/scenes/SceneDetail.jsx` | Expand Scene Intelligence panel with new enrichment tabs |
| `frontend/src/components/scenes/SceneDetail.css` | Tab styles within intelligence panel |
| `frontend/src/components/metadata/ScriptHeader.jsx` | Add "Story Map", "Character Arcs", "Relationships" buttons |
| `frontend/src/services/apiService.js` | Add narrative API methods |
| `frontend/src/App.jsx` | Add routes for new pages |

---

## Implementation Phasing (Updated)

### Phase A: Extraction (Backend) — NEW extraction classes
1. Add `story_beat`, `conflict`, `theme`, `foreshadowing` to schema + examples
2. Update breakdown endpoint enrichment classification
3. Re-run LangExtract on test scripts to verify new classes extract correctly

### Phase B: Scene Intelligence Expansion (Frontend) — Per-scene narrative display
1. Add tabs to Scene Intelligence panel
2. Render story beats, conflict, themes, foreshadowing within tabs
3. Confidence indicators on all enrichment items

### Phase C: Cross-Scene Aggregation (Backend) — Narrative service
1. Create `narrative_service.py` with aggregation logic
2. Character arc computation (emotions + dialogue + relationships + beats)
3. Story structure auto-detection (tension curve + structural markers)
4. Relationship web aggregation
5. Theme tracker aggregation
6. Create API endpoints

### Phase D: Narrative Pages (Frontend) — Script-level views
1. Story Map page with tension curve (recharts) + structural markers + beat sheet
2. Character Arc page with emotional journey chart + tone progression
3. Relationship Web page with matrix + evolution timeline
4. Add ScriptHeader buttons + routes

### Phase E: Reporting (Backend + Frontend) — Export/preview
1. Add 6 new report presets + HTML renderers
2. Director's Vision Brief as flagship combined report
3. Update ReportBuilder.jsx with new report options

---

## Updated Dependency Graph

```
[Existing] Breakdown UI Refactor (Phases 1-6)
                    │
                    ▼
[Phase A] New Extraction Classes ──┬──> [Phase B] Scene Intelligence Expansion
                                   │
                                   ├──> [Phase C] Cross-Scene Aggregation
                                   │              │
                                   │              ▼
                                   │    [Phase D] Narrative Pages (Story Map, Arcs, Web)
                                   │
                                   └──> [Phase E] Reporting (Beat Sheet, Arcs, Vision Brief)
```

Phases B, C, D, E all depend on Phase A (extraction classes must exist first).
Phases C and D are sequential (backend aggregation before frontend pages).
Phase E can run in parallel with Phase D.

---

## Ready to Implement?

Before starting Phase 1 (Breakdown UI), confirm:
- [x] Wireframe / layout direction approved
- [x] Department Lens department list is correct
- [x] Enrichment attributes confirmed for existing classes

Before starting Phase A (Narrative Extraction), confirm:
- [x] New extraction classes approved: `story_beat`, `conflict`, `theme`, `foreshadowing`
- [x] Beat type taxonomy approved (revelation, decision, complication, confrontation, reversal, climax, resolution, setup)
- [x] Conflict type taxonomy approved (person_vs_person, person_vs_self, person_vs_nature, person_vs_society, person_vs_fate)
- [x] Theme taxonomy is open-ended (no fixed list — AI infers from script)
- [x] Cross-scene pages scope approved (Story Map, Character Arcs, Relationship Web)
- [x] Director's Vision Brief report concept approved as flagship
- [x] Tension curve formula and structure detection rules approved