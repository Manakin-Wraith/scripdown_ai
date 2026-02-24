# Implementation Plan: Daily Production Reporting (DPR)

**Branch**: `feature/daily-production-reporting` | **Date**: 2026-02-23 | **Spec**: `docs/SPEC_Daily_Production_Reporting.md` (Rev 4)  
**Input**: Feature specification Rev 4 — 120+ FRs, 11 entities, 37 acceptance scenarios, 25 edge cases, 27 gap fixes  
**Version**: 0.1.0

---

## Summary

Extend SlateOne from a pre-production planning tool into a production-day execution tracker. The Daily Production Report captures what actually happens on set each shoot day, compares it against the planned schedule, and generates production intelligence analytics.

**Technical approach**: Multi-table Supabase schema (11 migrations) with Flask service layer, React tabbed editor UI, WeasyPrint PDF export with QR code versioning, and materialized metrics for analytics performance.

---

## Technical Context

| Dimension | Value |
|-----------|-------|
| **Language/Version** | Python 3.11 (backend), JavaScript ES2022 (frontend) |
| **Primary Dependencies** | Flask 3.0, Supabase SDK 2.10, React 18 (Vite), WeasyPrint 62.3 |
| **Storage** | Supabase PostgreSQL (project `twzfaizeyqwevmhjyicz`, eu-west-1), Supabase Storage (attachments) |
| **Testing** | pytest (backend), manual E2E (frontend — no test framework currently) |
| **Target Platform** | Web — Desktop + tablet (touch-optimized), low-bandwidth remote locations |
| **Project Type** | Web (frontend + backend) |
| **Performance Goals** | DPR CRUD <500ms, Analytics for 60-day schedule <1000ms, PDF generation <3000ms |
| **Constraints** | Must work on Edge/3G (low-bandwidth mode), 44px min touch targets, offline deferred to future |
| **Scale/Scope** | ~50 concurrent productions, ~30 scenes/DPR, ~60-day schedules, multi-unit (2-4 units) |

### Existing Dependencies (DPR builds on)

| Module | Table/Route | Status |
|--------|------------|--------|
| Shooting Schedules | `shooting_schedules`, `shooting_days`, `shooting_day_scenes` (migration 030) | ✅ Live |
| Scene Breakdown | `scenes` table with JSONB arrays + `department_items` | ✅ Live |
| Report/PDF Engine | `report_service.py` + WeasyPrint | ✅ Live |
| Department Workspaces | `departments`, `department_items`, `department_notes` | ✅ Live |
| Team System | `script_members`, invites, roles | ✅ Live |
| Auth | `@require_auth` / `@optional_auth` decorators, JWT verification | ✅ Live |
| Notifications | `notifications` table (migration 020) | ✅ Live |

### New Dependencies Required

| Dependency | Purpose | Notes |
|-----------|---------|-------|
| `qrcode[pil]` | QR code generation for PDF footer (FR-031a) | Python package, ~50KB |
| `recharts` | Analytics charts (burndown, velocity, delays) | React charting library |

---

## Constitution Check

### Simplicity
- **Projects**: 2 (backend, frontend) — ✅ within limit
- **Using framework directly?** Yes — Flask blueprints directly, React components directly, no wrapper abstractions
- **Single data model?** Yes — Supabase tables map 1:1 to entities. No DTOs; JSON responses directly from Supabase query results
- **Avoiding patterns?** Yes — No Repository/UoW. Direct Supabase client calls in service functions (matching existing `schedule_routes.py` pattern)

### Architecture
- **EVERY feature as library?** Adapted: Each DPR concern is a separate service file (`dpr_service.py`, `dpr_metrics_service.py`, `dpr_analytics_service.py`, etc.) — reusable, testable units
- **Libraries listed**:
  - `dpr_service.py` — Core CRUD, workflow, versioning, snapshot re-sync
  - `dpr_scene_entry_service.py` — Scene entry CRUD, validation, carryover
  - `dpr_department_log_service.py` — Department log lifecycle
  - `dpr_time_entry_service.py` — Time tracking, overnight, shared resources
  - `dpr_incident_service.py` — Incident CRUD
  - `dpr_delay_service.py` — Delay CRUD
  - `dpr_attachment_service.py` — File upload, signed URLs, clone references
  - `dpr_signoff_service.py` — Sign-off management
  - `dpr_metrics_service.py` — Materialized metrics computation/invalidation
  - `dpr_analytics_service.py` — Cumulative analytics, burndown, velocity
  - `dpr_config_service.py` — Approval mode, required departments, thresholds
  - `dpr_pdf_service.py` — PDF/HTML generation
- **CLI per library**: N/A (web app, not CLI-driven)
- **Library docs**: Each service file has docstrings; API contracts documented in `contracts/`

### Testing (NON-NEGOTIABLE)
- **RED-GREEN-Refactor**: Yes — Phase 2 (tests) MUST complete before Phase 3 (implementation)
- **Order**: Contract tests → Integration tests → Implementation → Unit tests (polish)
- **Real dependencies**: Tests use Supabase client against test project (not mocks)
- **Integration tests for**: New DPR tables, workflow transitions, multi-unit aggregation, snapshot immutability

### Observability
- **Structured logging**: Python `logging` module with JSON context (existing pattern in `scene_enhancer.py`)
- **Frontend logs → backend**: Error boundary catches + reports to `/api/feedback` (existing)
- **Error context**: All service functions return structured error dicts with field-level detail

### Versioning
- **Version**: 0.1.0 (initial DPR feature)
- **BUILD increments**: Each migration is a numbered increment (031–041)
- **Breaking changes**: None — new tables only, no ALTER on existing tables (except minor `shooting_days` extension in T011)

---

## Project Structure

### Documentation (this feature)
```
docs/dpr-plan/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/           # Phase 1 output (API contracts)
    ├── units.md
    ├── dpr-core.md
    ├── scene-entries.md
    ├── department-logs.md
    ├── time-entries.md
    ├── incidents-delays.md
    ├── attachments.md
    ├── signoffs.md
    ├── analytics.md
    └── config.md
```

### Source Code (repository root)
```
backend/
├── db/migrations/
│   ├── 031_dpr_units.sql
│   ├── 032_dpr_core.sql
│   ├── 033_dpr_scene_entries.sql
│   ├── 034_dpr_department_logs.sql
│   ├── 035_dpr_time_entries.sql
│   ├── 036_dpr_incidents_delays.sql
│   ├── 037_dpr_attachments.sql
│   ├── 038_dpr_signoffs_audit.sql
│   ├── 039_dpr_materialized_metrics.sql
│   ├── 040_dpr_approval_config.sql
│   └── 041_extend_shooting_days_for_dpr.sql
├── services/
│   ├── dpr_service.py
│   ├── dpr_scene_entry_service.py
│   ├── dpr_department_log_service.py
│   ├── dpr_time_entry_service.py
│   ├── dpr_incident_service.py
│   ├── dpr_delay_service.py
│   ├── dpr_attachment_service.py
│   ├── dpr_signoff_service.py
│   ├── dpr_metrics_service.py
│   ├── dpr_analytics_service.py
│   ├── dpr_config_service.py
│   └── dpr_pdf_service.py
├── routes/
│   ├── dpr_routes.py
│   ├── dpr_unit_routes.py
│   ├── dpr_scene_entry_routes.py
│   ├── dpr_department_log_routes.py
│   ├── dpr_time_entry_routes.py
│   ├── dpr_sub_entity_routes.py
│   ├── dpr_analytics_routes.py
│   └── dpr_config_routes.py
└── tests/
    ├── contract/
    │   ├── test_dpr_units_api.py
    │   ├── test_dpr_core_api.py
    │   ├── test_dpr_scene_entries_api.py
    │   ├── test_dpr_department_logs_api.py
    │   ├── test_dpr_time_entries_api.py
    │   ├── test_dpr_incidents_delays_api.py
    │   ├── test_dpr_attachments_api.py
    │   ├── test_dpr_signoffs_api.py
    │   └── test_dpr_analytics_api.py
    ├── integration/
    │   ├── test_dpr_workflow.py
    │   ├── test_dpr_multi_unit.py
    │   ├── test_dpr_validation.py
    │   └── test_dpr_snapshot_resync.py
    └── unit/
        ├── test_dpr_validation.py
        ├── test_dpr_snapshot.py
        ├── test_dpr_versioning.py
        └── test_dpr_analytics.py

frontend/
└── src/
    ├── components/dpr/
    │   ├── DprCreateButton.jsx + .css
    │   ├── DprEditor.jsx + .css
    │   ├── DprStatusBar.jsx + .css
    │   ├── DprGeneralInfo.jsx + .css
    │   ├── SceneProgressTable.jsx + .css
    │   ├── SceneEntryRow.jsx + .css
    │   ├── DailyTotals.jsx + .css
    │   ├── DepartmentLogPanel.jsx + .css
    │   ├── CameraLogForm.jsx + .css
    │   ├── TimeTrackingPanel.jsx + .css
    │   ├── TimeEntryRow.jsx + .css
    │   ├── IncidentLog.jsx + .css
    │   ├── DelayLog.jsx + .css
    │   ├── AttachmentManager.jsx + .css
    │   ├── SignOffBlock.jsx + .css
    │   ├── DprExportBar.jsx + .css
    │   ├── AnalyticsDashboard.jsx + .css
    │   ├── BurndownChart.jsx + .css
    │   ├── DelayAnalysis.jsx + .css
    │   ├── VelocityGauge.jsx + .css
    │   ├── ApprovalConfigPanel.jsx + .css
    │   ├── DprListView.jsx + .css
    │   ├── UnitManager.jsx + .css
    │   └── LowBandwidthToggle.jsx + .css
    ├── hooks/
    │   └── useLowBandwidthMode.js
    └── pages/
        ├── DprEditorPage.jsx + .css
        └── DprDashboardPage.jsx + .css
```

**Structure Decision**: Option 2 (Web application) — frontend + backend already established.

---

## Phase 2: Task Generation Approach

**IMPORTANT**: This section describes what the `/tasks` command will do — NOT executed by `/plan`.

### Task Generation Strategy
- Load existing `docs/TASKS_Daily_Production_Reporting.md` as reference (already contains 102 tasks)
- Validate task coverage against Phase 1 design docs (contracts, data model, quickstart)
- Each contract endpoint → contract test task [P where independent]
- Each entity → migration task
- Each service → implementation task
- Each component → frontend task
- TDD order enforced: tests (Phase 2) before implementation (Phase 3)

### Ordering Strategy
- **Dependency order**: Migrations → Tests → Services → Routes → Frontend API → Components → Pages
- **Parallel markers** [P] on independent files
- **Critical path**: Schema → Core DPR service → Scene entries → Department logs → Analytics → PDF → Frontend

### Estimated Output
- 102 tasks already decomposed in existing tasks file
- 6 phases with dependency graph
- ~8-10 weeks total effort for 1 senior full-stack engineer

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| 11 migrations (exceeds typical 3) | DPR has 11 distinct entities with different RLS policies, each needing its own migration for clean rollback | Single migration would be 500+ lines, impossible to partially roll back |
| 12 service files | Each DPR sub-domain (scenes, dept logs, time, incidents, etc.) has distinct business rules and validation | Monolithic service would be 2000+ lines, untestable |
| Multi-level analytics aggregation | Production requirement: per-unit, per-day, per-schedule analytics with canonical version filtering | Single-level aggregation wouldn't serve multi-unit productions |

---

## Status

- [x] Spec loaded (Rev 4, 724 lines)
- [x] Technical Context filled (no NEEDS CLARIFICATION)
- [x] Constitution Check passed
- [x] Phase 0: Research complete → `research.md`
- [x] Phase 1: Design complete → `data-model.md`, `contracts/`, `quickstart.md`
- [x] Post-design Constitution Check passed
- [x] Phase 2 approach described
- **STOP** — Ready for `/tasks` command
