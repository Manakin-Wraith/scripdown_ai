# SlateOne-Daily-Production-Reporting

## Background

SlateOne currently provides a comprehensive script breakdown engine and a scheduling module that transforms screenplay data into structured production plans. These modules define what *should* happen during production — including scene scheduling, cast requirements, locations, props, and technical elements.

However, once principal photography begins, the system lacks a structured mechanism to capture what *actually* happens on set each day.

In professional film and television production, this gap is traditionally filled by a Daily Production Report (DPR) stack, which consolidates departmental logs (AD team, camera, sound, script supervisor, time sheets, incidents) into an official legal and financial record of the shoot day.

Currently, this process is handled through disconnected PDFs, spreadsheets, and manual compilation workflows. This results in:

* No structured linkage between planned schedule and actual execution
* Limited visibility into real-time schedule variance
* Manual overhead in compiling reports
* Minimal production intelligence extraction from daily data

The next logical evolution of SlateOne is to extend from pre-production planning into production-day execution tracking.

The SlateOne Daily Production Reporting feature will:

* Use scheduled scene data as the planned baseline
* Capture structured daily shoot data from departments
* Generate an automated Daily Production Report
* Compute schedule variance (planned vs actual pages, scenes, setups)
* Enable production intelligence analytics across shoot days

This transforms SlateOne from a planning platform into an end-to-end production intelligence system spanning breakdown → scheduling → execution → analytics.

---

## 1. Context Gathering Summary

### Existing Modules That Integrate

| Module | Integration Point | Status |
|--------|-------------------|--------|
| **Shooting Schedules** | `shooting_schedules` → `shooting_days` → `shooting_day_scenes`. Day status: `draft → confirmed → wrapped`. The DPR anchors to `shooting_day_id`. | ✅ Live (migration 030) |
| **Scene Breakdown** | `scenes` table with JSONB arrays (characters, props, wardrobe, etc.) + `department_items` CRUD. Provides the **planned baseline** per scene. | ✅ Live |
| **Report Engine** | `report_service.py` generates HTML → PDF via WeasyPrint. 7+ report types, filtering, presets, share links. DPR PDF generation reuses this pipeline. | ✅ Live |
| **Department Workspaces** | `departments` table, `department_items`, `department_notes`, `threads`, `activity_log`. Department logs in DPR map to existing department taxonomy. | ✅ Live |
| **Story Days** | 8 fields on `scenes` (story_day, timeline_code, etc.). Useful for DPR analytics (which story days were covered). | ✅ Live |
| **Team System** | `script_members`, invites, roles. DPR sign-off uses the existing team/role model. | ✅ Live |
| **Schedule Kanban** | `ShootingSchedulePage.jsx`, `DayColumn.jsx`, `ScheduleSceneCard.jsx`. Entry point for "File DPR" button. | ✅ Live |

### Key Observation
The `shooting_days` table already has `status IN ('draft', 'confirmed', 'wrapped')`. The transition `confirmed → wrapped` is the natural trigger for DPR creation. The **planned baseline** (what SHOULD happen) already lives in `shooting_day_scenes`. The DPR captures what **ACTUALLY** happened.

---

## 2. Industry-Standard DPR Stack (Reference)

Based on `docs/dialy_reports_feature.md`:

| Report | Owner | Priority |
|--------|-------|----------|
| **Daily Production Report (DPR)** | 2nd AD / Production Office | MANDATORY |
| Camera / Media Report | DIT / Data Manager | HIGH |
| Script Supervisor Report | Script Supervisor | HIGH |
| Sound Report | Sound Mixer | HIGH |
| Camera Log / Shot Log | 1st AC | MEDIUM |
| Departmental Wrap Reports | HODs (Art, Costume, Makeup, Locations, VFX) | MEDIUM |
| Cast & Crew Time Sheets | AD / Accounting | HIGH |
| Health & Safety / Incident Report | Safety Officer | AS NEEDED |

**Data Flow**: Departments submit → AD team consolidates → Production office compiles master DPR → Sign-off → Distribution to producers, studio, bond company, post-production.

---

## 3. Database Schema Design

### Migration: `031_daily_production_reports.sql`

#### 3.1 `daily_production_reports` — The Master DPR

```sql
CREATE TABLE daily_production_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id UUID NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    schedule_id UUID NOT NULL REFERENCES shooting_schedules(id) ON DELETE CASCADE,
    shooting_day_id UUID NOT NULL REFERENCES shooting_days(id) ON DELETE CASCADE,
    
    -- Header
    report_date DATE NOT NULL,
    shoot_day_number INT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' 
        CHECK (status IN ('draft', 'submitted', 'approved', 'locked')),
    
    -- Times
    call_time TIME,
    first_shot_time TIME,
    lunch_start TIME,
    lunch_end TIME,
    camera_wrap_time TIME,
    company_wrap_time TIME,
    
    -- Conditions
    weather JSONB DEFAULT '{}',  -- { condition, temp_high, temp_low, notes }
    
    -- Computed Totals (cached, recomputed on scene entry changes)
    scenes_shot INT DEFAULT 0,
    scenes_partial INT DEFAULT 0,
    scenes_not_shot INT DEFAULT 0,
    added_scenes INT DEFAULT 0,
    pages_shot_eighths INT DEFAULT 0,
    planned_pages_eighths INT DEFAULT 0,
    total_setups INT DEFAULT 0,
    
    -- Notes
    general_notes TEXT,
    safety_notes TEXT,
    
    -- Sign-off
    signed_off_by JSONB DEFAULT '[]',  -- [{user_id, role, name, timestamp}]
    
    -- Audit
    created_by UUID REFERENCES auth.users(id),
    approved_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    UNIQUE (shooting_day_id)  -- One DPR per shooting day
);
```

#### 3.2 `dpr_scene_entries` — Planned vs Actual Per Scene

```sql
CREATE TABLE dpr_scene_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dpr_id UUID NOT NULL REFERENCES daily_production_reports(id) ON DELETE CASCADE,
    scene_id UUID NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    
    -- Status
    status TEXT NOT NULL DEFAULT 'not_shot'
        CHECK (status IN ('complete', 'partial', 'not_shot', 'added', 'pickup')),
    
    -- Actual data
    pages_shot_eighths INT DEFAULT 0,
    setups_count INT DEFAULT 0,
    takes_count INT DEFAULT 0,
    circle_takes JSONB DEFAULT '[]',  -- ["1A", "3B", "5A"]
    
    -- Times
    start_time TIME,
    end_time TIME,
    
    -- Notes
    notes TEXT,
    continuity_notes TEXT,
    
    -- Tracking
    sort_order INT DEFAULT 0,
    is_added BOOLEAN DEFAULT false,  -- True if scene was not originally planned
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    UNIQUE (dpr_id, scene_id)
);
```

#### 3.3 `dpr_department_logs` — Modular Department Submissions

```sql
CREATE TABLE dpr_department_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dpr_id UUID NOT NULL REFERENCES daily_production_reports(id) ON DELETE CASCADE,
    department_id UUID REFERENCES departments(id),
    
    log_type TEXT NOT NULL
        CHECK (log_type IN (
            'camera', 'sound', 'script_supervisor', 
            'art', 'costume', 'makeup', 'locations', 'vfx', 
            'stunts', 'transport', 'general'
        )),
    
    -- Structured data (schema varies by log_type)
    structured_data JSONB NOT NULL DEFAULT '{}',
    
    -- Metadata
    submitted_by UUID REFERENCES auth.users(id),
    submitted_at TIMESTAMPTZ,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'submitted')),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Camera log `structured_data` schema:**
```json
{
    "camera_rolls": [{ "camera": "A", "roll": "A001", "codec": "ARRI RAW", "resolution": "4K" }],
    "lenses_used": ["50mm", "85mm", "24-70mm"],
    "backup_status": "complete",
    "backup_notes": "LTO tape + shuttle drive",
    "data_integrity": "verified"
}
```

**Sound log `structured_data` schema:**
```json
{
    "sound_rolls": [{ "roll": "S001", "format": "WAV 48kHz/24bit" }],
    "mics_used": ["Boom Sennheiser 416", "Lav DPA 4071"],
    "sync_notes": "All synced via timecode",
    "issues": ["Aircraft noise during scene 42"]
}
```

**Script Supervisor `structured_data` schema:**
```json
{
    "circle_takes": { "42": ["3A", "5B"], "43": ["1A", "2A"] },
    "dialogue_changes": [{ "scene": "42", "change": "Line modified from..." }],
    "continuity_notes": [{ "scene": "42", "note": "Actor wearing watch on left wrist" }],
    "coverage_notes": "Need insert of letter for scene 44"
}
```

#### 3.4 `dpr_time_entries` — Cast & Crew Hours

```sql
CREATE TABLE dpr_time_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dpr_id UUID NOT NULL REFERENCES daily_production_reports(id) ON DELETE CASCADE,
    
    person_type TEXT NOT NULL CHECK (person_type IN ('cast', 'crew')),
    person_name TEXT NOT NULL,
    role_or_character TEXT,  -- Character name for cast, department/role for crew
    
    -- Times
    call_time TIME,
    on_set_time TIME,
    wrap_time TIME,
    
    -- Breaks
    meal_break_start TIME,
    meal_break_end TIME,
    second_meal_start TIME,
    second_meal_end TIME,
    
    -- Calculated
    hours_worked DECIMAL(4,2),
    overtime_hours DECIMAL(4,2) DEFAULT 0,
    travel_hours DECIMAL(4,2) DEFAULT 0,
    
    -- Flags
    meal_penalty BOOLEAN DEFAULT false,
    forced_call BOOLEAN DEFAULT false,
    
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### 3.5 `dpr_incidents` — Health & Safety

```sql
CREATE TABLE dpr_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dpr_id UUID NOT NULL REFERENCES daily_production_reports(id) ON DELETE CASCADE,
    
    incident_type TEXT NOT NULL 
        CHECK (incident_type IN ('injury', 'near_miss', 'safety_violation', 'equipment_damage')),
    severity TEXT NOT NULL 
        CHECK (severity IN ('minor', 'moderate', 'serious', 'critical')),
    
    description TEXT NOT NULL,
    location TEXT,
    time_of_incident TIME,
    
    persons_involved JSONB DEFAULT '[]',  -- [{name, role, injury_description}]
    witnesses JSONB DEFAULT '[]',         -- [{name, role}]
    
    action_taken TEXT,
    follow_up_required BOOLEAN DEFAULT false,
    follow_up_notes TEXT,
    
    reported_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### 3.6 `dpr_delays` — Delay Tracking

```sql
CREATE TABLE dpr_delays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dpr_id UUID NOT NULL REFERENCES daily_production_reports(id) ON DELETE CASCADE,
    
    delay_type TEXT NOT NULL 
        CHECK (delay_type IN (
            'weather', 'technical', 'talent', 'location', 
            'medical', 'meal_penalty', 'company_move', 'other'
        )),
    
    duration_minutes INT NOT NULL,
    description TEXT,
    scene_id UUID REFERENCES scenes(id),  -- Optional: which scene was affected
    
    impact TEXT,  -- 'minor', 'moderate', 'major'
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 4. Backend Architecture

### 4.1 New Service: `backend/services/dpr_service.py`

```
class DPRService:
    # ── CRUD ──
    create_dpr(script_id, schedule_id, shooting_day_id)
        → Auto-populate scene entries from shooting_day_scenes
        → Set shooting_day.status = 'wrapped'
        → Return DPR with entries
    
    get_dpr(dpr_id)
    get_dpr_by_day(shooting_day_id)
    update_dpr(dpr_id, data)  → Header fields (times, weather, notes)
    
    # ── Scene Entries ──
    get_scene_entries(dpr_id)
    update_scene_entry(entry_id, data)  → Status, takes, pages, notes
    add_unplanned_scene(dpr_id, scene_id)  → is_added=true
    
    # ── Department Logs ──
    submit_department_log(dpr_id, department_id, log_type, data)
    get_department_logs(dpr_id)
    
    # ── Time Entries ──
    add_time_entry(dpr_id, data)
    update_time_entry(entry_id, data)
    get_time_entries(dpr_id)
    auto_populate_cast(dpr_id)  → Pre-fill from scheduled characters
    
    # ── Incidents & Delays ──
    log_incident(dpr_id, data)
    log_delay(dpr_id, data)
    get_incidents(dpr_id)
    get_delays(dpr_id)
    
    # ── Variance Engine ──
    compute_variance(dpr_id) → {
        planned_scenes, shot_scenes, partial_scenes, not_shot_scenes, added_scenes,
        planned_pages_eighths, actual_pages_eighths,
        variance_eighths, variance_percentage,
        total_setups, total_takes,
        total_delays_minutes, delay_breakdown_by_type
    }
    
    recompute_totals(dpr_id)  → Update cached totals on DPR header
    
    # ── Status Workflow ──
    submit_dpr(dpr_id, user_id)  → draft → submitted
    approve_dpr(dpr_id, user_id)  → submitted → approved
    lock_dpr(dpr_id, user_id)  → approved → locked (no further edits)
    
    # ── Production Analytics ──
    get_production_analytics(script_id, schedule_id) → {
        total_shoot_days, completed_days,
        cumulative_pages_shot, total_script_pages,
        avg_pages_per_day, avg_setups_per_day,
        projected_completion_date,
        burndown_data: [{day, planned_cumulative, actual_cumulative}],
        delay_summary: {total_minutes, by_type: {weather: N, ...}},
        schedule_health_score: 0-100
    }
    
    # ── PDF ──
    generate_dpr_pdf(dpr_id) → bytes
    generate_dpr_html(dpr_id) → str
```

### 4.2 New Routes: `backend/routes/dpr_routes.py`

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/scripts/:id/schedules/:sid/days/:did/dpr` | Create DPR |
| GET | `/api/scripts/:id/schedules/:sid/days/:did/dpr` | Get DPR for day |
| PATCH | `/api/dpr/:dprId` | Update DPR header |
| GET | `/api/dpr/:dprId/scenes` | Get scene entries |
| PATCH | `/api/dpr/:dprId/scenes/:entryId` | Update scene entry |
| POST | `/api/dpr/:dprId/scenes/add` | Add unplanned scene |
| GET | `/api/dpr/:dprId/department-logs` | Get department logs |
| POST | `/api/dpr/:dprId/department-logs` | Submit department log |
| GET | `/api/dpr/:dprId/time-entries` | Get time entries |
| POST | `/api/dpr/:dprId/time-entries` | Add time entry |
| PATCH | `/api/dpr/:dprId/time-entries/:entryId` | Update time entry |
| POST | `/api/dpr/:dprId/time-entries/auto-populate` | Pre-fill cast from schedule |
| POST | `/api/dpr/:dprId/incidents` | Log incident |
| POST | `/api/dpr/:dprId/delays` | Log delay |
| GET | `/api/dpr/:dprId/variance` | Compute variance |
| POST | `/api/dpr/:dprId/submit` | Submit for approval |
| POST | `/api/dpr/:dprId/approve` | Approve DPR |
| POST | `/api/dpr/:dprId/lock` | Lock DPR |
| GET | `/api/dpr/:dprId/pdf` | Download DPR PDF |
| GET | `/api/dpr/:dprId/print` | Printable HTML |
| GET | `/api/scripts/:id/schedules/:sid/analytics` | Production analytics |

---

## 5. Frontend Architecture

### 5.1 Routes

```
/scripts/:scriptId/schedule/:scheduleId/day/:dayId/dpr     → DPR Editor
/scripts/:scriptId/schedule/:scheduleId/analytics           → Production Dashboard
```

### 5.2 Components

#### Core Page
- **`DPREditorPage.jsx`** — Full-page DPR editor with tab navigation
  - Route param: `dayId` → fetch DPR (or create if none exists)
  - Auto-save draft on field changes (debounced)
  - Status bar: draft/submitted/approved/locked badge

#### Tab Modules (inside DPREditor)
| Tab | Component | Description |
|-----|-----------|-------------|
| Overview | `DPROverview.jsx` | Call/wrap times, weather, conditions, general notes |
| Scene Progress | `DPRSceneTable.jsx` | Planned vs actual table with status toggles |
| Department Logs | `DPRDepartmentLogs.jsx` | Accordion per department, structured forms |
| Time Sheets | `DPRTimesheets.jsx` | Cast + crew time table |
| Incidents & Delays | `DPRIncidents.jsx` | Incident forms + delay log |
| Summary & Sign-Off | `DPRSummary.jsx` | Variance stats, sign-off buttons, PDF export |

#### Analytics
- **`ProductionDashboard.jsx`** — KPI cards, burndown chart, delay analysis, trends

#### Shared
- **`VarianceIndicator.jsx`** — Reusable ▲/▼ badge for planned vs actual
- **`TimePickerField.jsx`** — Touch-friendly time input
- **`DPRStatusBadge.jsx`** — Status pill (draft/submitted/approved/locked)

### 5.3 Entry Points

1. **`ShootingSchedulePage.jsx`** → "File DPR" button on each day card
2. **`DayColumn.jsx`** (Kanban) → DPR icon badge on wrapped days
3. **Sidebar Nav** → "Daily Reports" link (under Production section)
4. **`ScriptHeader.jsx`** → "DPR" button (when schedule exists)

### 5.4 API Service Additions (`apiService.js`)

```javascript
// DPR CRUD
createDPR(scriptId, scheduleId, dayId)
getDPR(scriptId, scheduleId, dayId)
updateDPR(dprId, data)

// Scene Entries
getDPRScenes(dprId)
updateDPRScene(dprId, entryId, data)
addUnplannedScene(dprId, sceneId)

// Department Logs
getDepartmentLogs(dprId)
submitDepartmentLog(dprId, logData)

// Time Entries
getTimeEntries(dprId)
addTimeEntry(dprId, data)
updateTimeEntry(dprId, entryId, data)
autoPopulateCast(dprId)

// Incidents & Delays
logIncident(dprId, data)
logDelay(dprId, data)

// Workflow
submitDPR(dprId)
approveDPR(dprId)
lockDPR(dprId)

// Analytics
getProductionAnalytics(scriptId, scheduleId)

// Export
downloadDPRPdf(dprId)
openDPRPrint(dprId)
```

---

## 6. UX/UI Design Considerations

### 6.1 Scene Progress Table (Core Innovation)

The `DPRSceneTable` is the heart of the DPR — it's where planned meets actual:

```
┌──────┬──────────────────┬─────┬──────────┬──────────┬────────┬───────┬────────┬───────┐
│ Sc#  │ Setting          │ D/N │ Planned  │ Actual   │ Status │ Takes │ Setups │ Notes │
├──────┼──────────────────┼─────┼──────────┼──────────┼────────┼───────┼────────┼───────┤
│ 42   │ HOSPITAL - ROOM  │ N   │ 2 3/8   │ 2 3/8   │  ✅    │  7    │   3    │       │
│ 43   │ HOSPITAL - HALL  │ N   │ 1 2/8   │ 1 2/8   │  ✅    │  4    │   2    │       │
│ 44   │ EXT. PARKING LOT │ N   │ 3 1/8   │ 1 4/8   │  🟡    │  3    │   1    │ Rain  │
│ 45   │ INT. CAR         │ N   │ 0 7/8   │   —     │  🔴    │  —    │   —    │ Cut   │
│ +12  │ INT. ELEVATOR    │ D   │   —     │ 1 1/8   │  🔵    │  5    │   2    │ Added │
├──────┴──────────────────┴─────┼──────────┼──────────┼────────┼───────┼────────┤───────┤
│                        TOTALS │ 8 2/8   │ 5 7/8   │ ▼-2⅜  │  19   │   8    │       │
└───────────────────────────────┴──────────┴──────────┴────────┴───────┴────────┴───────┘
```

**Status Legend:**
- ✅ `complete` — Fully shot as planned
- 🟡 `partial` — Started but not finished
- 🔴 `not_shot` — Planned but not shot (carried to next day)
- 🔵 `added` — Not originally planned, shot as bonus/pickup
- 🟣 `pickup` — Pickup from a previous day

### 6.2 Production Burndown Chart

```
Pages  ─── Planned ─── Actual
  120 ┤
  100 ┤               ╱─────
   80 ┤          ╱───╱
   60 ┤     ╱───╱  ╱
   40 ┤╱───╱   ╱──╱
   20 ┤   ╱──╱
    0 ┼──┴──┴──┴──┴──┴──┴──┴─→
      D1  D5  D10 D15 D20 D25
```

### 6.3 Mobile/Tablet Priorities
- **Large touch targets** — All buttons ≥ 44px
- **Swipeable tabs** — Navigate between DPR sections
- **Time pickers** — Native mobile time inputs, not text fields
- **Minimal typing** — Status toggles, dropdowns, number steppers
- **Auto-save** — Draft saved every 5s of inactivity
- **Offline queue** — Changes cached in IndexedDB, synced on reconnect

---

## 7. Variance Computation Engine

### Per-Day Variance
```python
variance = {
    # Scenes
    'planned_scenes': len(planned_entries),
    'shot_scenes': count(status='complete'),
    'partial_scenes': count(status='partial'),
    'not_shot_scenes': count(status='not_shot'),
    'added_scenes': count(status='added'),
    'pickup_scenes': count(status='pickup'),
    
    # Pages (in eighths)
    'planned_pages_eighths': sum(scene.page_length_eighths for planned),
    'actual_pages_eighths': sum(entry.pages_shot_eighths for shot/partial),
    'variance_eighths': actual - planned,
    'variance_pct': (actual - planned) / planned * 100,
    
    # Efficiency
    'total_setups': sum(setups),
    'total_takes': sum(takes),
    'avg_takes_per_setup': total_takes / total_setups,
    
    # Time
    'total_shoot_hours': wrap - call - lunch_duration,
    'pages_per_hour': actual_pages / shoot_hours,
    
    # Delays
    'total_delay_minutes': sum(delays),
    'delay_breakdown': { 'weather': N, 'technical': N, ... }
}
```

### Cumulative Analytics (across shoot)
```python
analytics = {
    'total_shoot_days': count(dprs),
    'total_script_pages': script_total_eighths / 8,
    'cumulative_pages_shot': running_sum,
    'remaining_pages': total - cumulative,
    
    'avg_pages_per_day': cumulative / days_completed,
    'projected_remaining_days': remaining / avg_per_day,
    'projected_wrap_date': schedule_start + total_projected_days,
    
    'schedule_health_score': 100 * (1 - abs(variance_pct)),
    
    'burndown_series': [
        { day: 1, planned_cumulative: 5.5, actual_cumulative: 6.0 },
        { day: 2, planned_cumulative: 11.0, actual_cumulative: 10.5 },
        ...
    ]
}
```

---

## 8. PDF Generation (DPR Report)

Extend existing `report_service.py` pattern or create `dpr_report_service.py`:

### DPR PDF Sections
1. **Header** — Production title, shoot day, date, weather
2. **Call Sheet Summary** — Call time, first shot, lunch, wrap
3. **Scene Progress Table** — Full planned vs actual table with variance row
4. **Cast Time Sheet** — Character, actor, call/set/wrap, overtime
5. **Crew Summary** — Department-level hour aggregates
6. **Department Notes** — Camera, sound, script supervisor reports
7. **Incidents & Delays** — If any
8. **Daily Totals** — Pages shot, setups, takes, delays
9. **Cumulative Totals** — Running totals since Day 1
10. **Sign-Off Block** — Names, roles, timestamps

### Design
- A4 landscape for scene table (more columns)
- Industry-standard layout (EP/Movie Magic DPR format)
- Reuse existing `_get_report_css()` base styles + DPR-specific additions

---

## 9. Phased Implementation Plan

### Phase 1: Foundation & Core DPR (MVP) — ~2 weeks
**Scope**: Create DPR, scene progress tracking, basic variance, PDF export

- [ ] Migration `031_daily_production_reports.sql` (6 tables + RLS + indexes)
- [ ] `backend/services/dpr_service.py` — Core CRUD, scene entries, variance
- [ ] `backend/routes/dpr_routes.py` — DPR + scene entry endpoints
- [ ] `frontend/src/components/dpr/DPREditorPage.jsx` — Page shell + tabs
- [ ] `frontend/src/components/dpr/DPROverview.jsx` — Times + weather form
- [ ] `frontend/src/components/dpr/DPRSceneTable.jsx` — Scene progress table
- [ ] `frontend/src/components/dpr/DPRSummary.jsx` — Variance stats + PDF button
- [ ] Entry point: "File DPR" button on `ShootingSchedulePage` day cards
- [ ] Basic DPR PDF generation via WeasyPrint
- [ ] `apiService.js` — DPR API functions

### Phase 2: Department Logs & Time Sheets — ~1.5 weeks
**Scope**: Structured department submissions, cast/crew time tracking

- [ ] `DPRDepartmentLogs.jsx` — Accordion per department, structured forms
- [ ] Camera/Sound/Script Supervisor log schemas
- [ ] `DPRTimesheets.jsx` — Cast call/set/wrap table with overtime calc
- [ ] Auto-populate cast from scheduled scene characters
- [ ] Import existing `department_notes` as starting data for logs
- [ ] Auto-save draft on field changes (debounced)

### Phase 3: Production Analytics Dashboard — ~1 week
**Scope**: Cross-day analytics, burndown chart, KPIs

- [ ] `ProductionDashboard.jsx` — KPI cards, charts, trends
- [ ] Burndown chart: planned vs actual cumulative pages (SVG or chart lib)
- [ ] Delay analysis: pie/bar chart by category
- [ ] Pages/day trend line
- [ ] Schedule health score computation
- [ ] Route: `/scripts/:scriptId/schedule/:scheduleId/analytics`

### Phase 4: Incidents, Delays & Sign-Off — ~1 week
**Scope**: Incident reporting, delay logging, approval workflow

- [ ] `DPRIncidents.jsx` — Incident + delay forms
- [ ] Delay categorization with duration tracking
- [ ] Digital sign-off workflow (submit → approve → lock)
- [ ] DPR status transitions with permission checks
- [ ] Audit trail for all status changes

### Phase 5: Mobile Optimization & Offline — ~1.5 weeks
**Scope**: Touch-friendly forms, offline support

- [ ] Touch-optimized time pickers and status toggles
- [ ] Large input targets (≥44px), swipeable tabs
- [ ] Service Worker for offline data entry
- [ ] IndexedDB cache → sync on reconnect
- [ ] Conflict resolution for concurrent edits

### Phase 6: Production Intelligence (Advanced) — ~1 week
**Scope**: Predictive analytics, alerts, benchmarks

- [ ] Projected completion date based on velocity
- [ ] Alert system: over-budget days, recurring delay patterns
- [ ] Industry benchmarks (avg pages/day: film ~2-3, TV ~5-8)
- [ ] Exportable analytics report PDF
- [ ] Integration with Call Sheet generation (future feature)

---

## 10. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Complexity creep** — DPR has many sub-modules | HIGH | Strict MVP: Phase 1 = scene progress only. Each phase is independently shippable. |
| **On-set usability** — Users on tablets in chaotic environments | HIGH | Large touch targets, auto-save, minimal required fields, offline support. |
| **Data integrity** — DPR is a legal document | HIGH | Lock workflow, audit trail, signed_off_by tracking, immutable after lock. |
| **Offline connectivity** — Sets often have poor signal | MEDIUM | Phase 5 addresses with Service Worker + IndexedDB. Design data model for offline-first from Phase 1. |
| **Schedule integration** — Must gracefully link to existing shooting_days | MEDIUM | DPR creation auto-sets day status to 'wrapped'. One DPR per day enforced by UNIQUE constraint. |
| **Department adoption** — HODs may not submit logs | LOW | Start with minimal required fields. Department logs are optional in Phase 1. |
| **PDF formatting** — Industry has specific DPR layouts | LOW | Research EP/Movie Magic format. Use existing WeasyPrint pipeline. |

---

## 11. Strategic Value

### Platform Evolution
```
Script Upload → Breakdown → Scheduling → [NEW] Daily Reporting → Analytics
     (Pre-Production)                    (Production)        (Post-Production)
```

### Business Impact
- **Daily engagement** — Users return every shoot day to file DPR (not just pre-production)
- **Team stickiness** — Multiple departments submit logs → entire crew depends on platform
- **Premium upsell** — Analytics dashboard as a premium/enterprise tier feature
- **Legal compliance** — DPR as official production record → mandatory tool, not optional
- **Data moat** — Accumulated DPR data across productions = industry intelligence

### Natural Extension Path
- **Call Sheets** — The "plan" counterpart to DPR "reality" (inverse data flow)
- **Wrap Reports** — End-of-production compilation from all DPRs
- **Budget Tracking** — Time sheet data feeds into cost reporting
- **Post-Production Handoff** — Circle takes + continuity notes → editorial workflow

---

## 12. Open Questions

1. **Real-time collaboration** — Should multiple users edit the same DPR simultaneously? (Supabase Realtime is already wired for department workspaces.)
2. **Notification triggers** — Should DPR submission trigger email/push to producers? (Email service already exists.)
3. **Call Sheet integration** — Should the DPR auto-generate next day's call sheet based on carried scenes?
4. **Photo attachments** — Should incidents/department logs support image uploads? (Supabase Storage already configured for avatars.)
5. **Multi-unit support** — Some productions have 2nd unit shooting simultaneously. Should DPR support multiple units per day?

---

**Status: Brainstorm Complete** ✅  
Ready for review → task decomposition → implementation.
