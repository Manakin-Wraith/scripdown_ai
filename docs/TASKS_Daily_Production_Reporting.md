# Tasks: Daily Production Reporting (DPR)

**Input**: `docs/SPEC_Daily_Production_Reporting.md` (Rev 4) + `docs/dpr-plan/` (plan.md, research.md, data-model.md, contracts/, quickstart.md)  
**Feature Branch**: `feature/daily-production-reporting`  
**Tech Stack**: Flask (Python) + Supabase (PostgreSQL/RLS) + React (Vite) + WeasyPrint  
**Spec Stats**: 120+ FRs, 11 entities, 25 edge cases, 27 gap fixes  
**New Dependencies**: `qrcode[pil]==7.4.2` (backend), `recharts` (frontend)

---

## Tech Stack & Conventions

- **Backend**: Flask blueprints in `backend/routes/`, services in `backend/services/`
- **Database**: Supabase PostgreSQL, migrations in `backend/db/migrations/` (next: `031_*`)
- **Auth**: `@require_auth` / `@optional_auth` decorators from `backend/middleware/auth.py`
- **Frontend**: React components in `frontend/src/components/dpr/`, API in `frontend/src/services/apiService.js`
- **PDF**: WeasyPrint via `backend/services/report_service.py` pattern
- **Tests**: `backend/tests/` (pytest), contract + integration
- **Existing deps**: Shooting schedules (`shooting_schedules`, `shooting_days`, `shooting_day_scenes` tables)

---

## Phase 0: Project Setup

- [ ] **T000a** Create feature branch `feature/daily-production-reporting` from `main`

- [ ] **T000b** [P] Add `qrcode[pil]==7.4.2` to `backend/requirements.txt`
  - Required for QR code generation in PDF footer (FR-031a)
  - Decision rationale: `docs/dpr-plan/research.md` §1

- [ ] **T000c** [P] Install `recharts` in frontend: `npm install recharts` in `frontend/`
  - Required for analytics charts (burndown, velocity, delays)
  - Decision rationale: `docs/dpr-plan/research.md` §2

- [ ] **T000d** [P] Create Supabase Storage bucket `dpr-attachments`
  - Public: false
  - Max file size: 25MB (configurable via approval config)
  - RLS policy: authenticated users with script access can upload
  - MIME type allowlist: image/*, application/pdf, video/*

---

## Phase 1: Database Schema & Setup

### Phase 1.1: Core Tables Migration

- [ ] **T001** Create migration `backend/db/migrations/031_dpr_units.sql`
  - `units` table: id, schedule_id (FK shooting_schedules), name, is_main_unit, sort_order, created_at, updated_at
  - RLS policies: script owner via schedule → script chain
  - Indexes on schedule_id
  - Updated_at trigger

- [ ] **T002** Create migration `backend/db/migrations/032_dpr_core.sql`
  - `daily_production_reports` table: id, shooting_day_id (FK), unit_id (FK), schedule_id (FK), version, parent_version_id (FK self), is_superseded, status (Draft/Submitted/Approved/Locked), day_type enum, include_in_velocity, call_time, first_shot_time, lunch_start, lunch_end, camera_wrap_time, company_wrap_time, weather, notes, locked_at, created_by (FK auth.users), created_at, updated_at
  - UNIQUE constraint on (shooting_day_id, unit_id) WHERE is_superseded = false
  - Status CHECK constraint
  - Day type CHECK constraint (Shoot, Company Move, Prep, Travel, Holiday, Dark, Strike)
  - RLS policies via schedule → script owner chain
  - Indexes: shooting_day_id, unit_id, schedule_id, status, parent_version_id
  - Updated_at trigger

- [ ] **T003** Create migration `backend/db/migrations/033_dpr_scene_entries.sql`
  - `dpr_scene_entries` table: id, dpr_id (FK), scene_id (FK scenes), status enum (Complete/Partial/Not Shot/Added/Pickup), actual_pages_eighths, setups, takes, circle_takes, start_time, end_time, notes
  - Snapshot fields: snapshot_scene_number, snapshot_slugline, snapshot_int_ext, snapshot_location, snapshot_day_night, snapshot_planned_pages_eighths, snapshot_schedule_order, snapshot_unit_assignment
  - RLS policies via dpr → schedule → script chain
  - Indexes: dpr_id, scene_id, status

- [ ] **T004** [P] Create migration `backend/db/migrations/034_dpr_department_logs.sql`
  - `dpr_department_logs` table: id, dpr_id (FK), department_type, submission_status (Pending/Submitted/N/A), submitted_by, submitted_at, na_reason, na_marked_by, data JSONB, notes, created_at, updated_at
  - Department type CHECK constraint
  - RLS policies
  - Indexes: dpr_id, department_type, submission_status

- [ ] **T005** [P] Create migration `backend/db/migrations/035_dpr_time_entries.sql`
  - `dpr_time_entries` table: id, dpr_id (FK), person_name, person_id (nullable FK), entry_type (cast/crew), character_name, department, role, call_time TIMESTAMPTZ, on_set_time, wrap_time TIMESTAMPTZ, wrap_next_day BOOLEAN, first_meal_start, first_meal_end, second_meal_start, second_meal_end, travel_hours, calculated_hours, overtime_hours, meal_penalty BOOLEAN, forced_call BOOLEAN, is_shared_resource BOOLEAN, notes, created_at, updated_at
  - RLS policies
  - Indexes: dpr_id, person_id, entry_type
  - UNIQUE constraint on (dpr_id, person_id) WHERE person_id IS NOT NULL — soft uniqueness

- [ ] **T006** [P] Create migration `backend/db/migrations/036_dpr_incidents_delays.sql`
  - `dpr_incidents` table: id, dpr_id (FK), type enum, severity enum, description, location, incident_time, persons_involved JSONB, witnesses JSONB, action_taken, follow_up_required BOOLEAN, follow_up_notes, created_at, updated_at
  - `dpr_delays` table: id, dpr_id (FK), type enum, duration_minutes, description, scene_entry_id (nullable FK), created_at, updated_at
  - RLS policies for both
  - Indexes

- [ ] **T007** [P] Create migration `backend/db/migrations/037_dpr_attachments.sql`
  - `dpr_attachments` table: id, dpr_id (nullable FK), scene_entry_id (nullable FK), incident_id (nullable FK), department_log_id (nullable FK), file_url, file_type, file_size_bytes, uploader_id (FK auth.users), upload_timestamp, is_reference_copy BOOLEAN DEFAULT false, source_attachment_id (nullable FK self), created_at
  - CHECK: at least one parent FK is not null
  - RLS policies
  - Indexes

### Phase 1.2: Supporting Tables & Functions

- [ ] **T008** Create migration `backend/db/migrations/038_dpr_signoffs_audit.sql`
  - `dpr_signoffs` table: id, dpr_id (FK), signer_name, signer_role, signed_at, created_at
  - `dpr_audit_log` table: id, dpr_id (FK), event_type, actor_id (FK auth.users), actor_name, details JSONB, previous_version_signoffs JSONB, correction_reason, created_at
  - RLS policies
  - Indexes

- [ ] **T009** Create migration `backend/db/migrations/039_dpr_materialized_metrics.sql`
  - `dpr_materialized_metrics` table: id, dpr_id (FK UNIQUE), total_pages_eighths, total_setups, total_takes, total_delay_minutes, planned_pages_eighths, variance_pages_eighths, carryover_pages_eighths, page_gain_eighths, scenes_complete, scenes_partial, scenes_not_shot, scenes_added, scenes_pickup, computed_at TIMESTAMPTZ, is_stale BOOLEAN DEFAULT false
  - RLS policies
  - Function: `invalidate_dpr_metrics(dpr_id)` — sets is_stale = true
  - Triggers on scene_entries, delays INSERT/UPDATE/DELETE to auto-invalidate

- [ ] **T010** Create migration `backend/db/migrations/040_dpr_approval_config.sql`
  - `production_approval_config` table: id, schedule_id (FK UNIQUE), approval_mode (Strict/Soft), required_departments JSONB, required_departments_by_day_type JSONB, velocity_projection_basis (main_unit/combined), main_unit_id (nullable FK units), meal_penalty_config JSONB, forced_call_config JSONB, max_attachment_size_mb, created_at, updated_at
  - RLS policies
  - Default config row trigger on schedule creation

- [ ] **T011** Create migration `backend/db/migrations/041_extend_shooting_days_for_dpr.sql`
  - Minimal extension per `docs/dpr-plan/research.md` §12: unit assignment is tracked via DPR scene entry snapshots, NOT on `shooting_day_scenes`
  - Add `day_type` column to `shooting_days` (default 'Shoot') if not present — allows pre-classifying day type before DPR creation
  - No other schema changes to existing schedule tables

---

## Phase 2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE Phase 3

**CRITICAL: These tests MUST be written and MUST FAIL before ANY backend implementation**

### Phase 2.1: Contract Tests — API Endpoints

- [ ] **T012** [P] Contract test: `backend/tests/contract/test_dpr_units_api.py`
  - POST /api/schedules/:id/units — create unit
  - GET /api/schedules/:id/units — list units
  - PATCH /api/units/:id — update unit
  - DELETE /api/units/:id — delete unit

- [ ] **T013** [P] Contract test: `backend/tests/contract/test_dpr_core_api.py`
  - POST /api/shooting-days/:id/dpr — create DPR (with snapshot population)
  - GET /api/shooting-days/:id/dpr — get DPR for day+unit
  - GET /api/dprs/:id — get DPR by ID (with all sub-entities)
  - PATCH /api/dprs/:id — update DPR fields
  - POST /api/dprs/:id/submit — status transition Draft→Submitted
  - POST /api/dprs/:id/approve — status transition Submitted→Approved
  - POST /api/dprs/:id/lock — status transition Approved→Locked
  - POST /api/dprs/:id/revert — Submitted→Draft (FR-004a)
  - POST /api/dprs/:id/unlock — Locked→new version (FR-065)
  - POST /api/dprs/:id/resync — Re-sync with schedule (FR-053e)
  - GET /api/dprs/:id/verify — public version verification (FR-031a, no auth)

- [ ] **T014** [P] Contract test: `backend/tests/contract/test_dpr_scene_entries_api.py`
  - GET /api/dprs/:id/scene-entries — list scene entries
  - PATCH /api/dpr-scene-entries/:id — update scene entry (status, pages, takes, setups)
  - POST /api/dprs/:id/scene-entries — add scene (manually added)
  - DELETE /api/dpr-scene-entries/:id — remove scene entry
  - Validation: Complete with 0 pages → 400, Not Shot with >0 pages → 400

- [ ] **T015** [P] Contract test: `backend/tests/contract/test_dpr_department_logs_api.py`
  - GET /api/dprs/:id/department-logs — list department logs
  - PATCH /api/dpr-department-logs/:id — update log data
  - POST /api/dpr-department-logs/:id/submit — submit log
  - POST /api/dpr-department-logs/:id/mark-na — mark as N/A (FR-014a)
  - Editability lifecycle: frozen when DPR Submitted, editable again on revert

- [ ] **T016** [P] Contract test: `backend/tests/contract/test_dpr_time_entries_api.py`
  - POST /api/dprs/:id/time-entries — create time entry
  - GET /api/dprs/:id/time-entries — list time entries with summary
  - PATCH /api/dpr-time-entries/:id — update time entry
  - DELETE /api/dpr-time-entries/:id — delete time entry
  - POST /api/dprs/:id/time-entries/prepopulate — pre-populate cast from scene characters (FR-021)
  - Overnight wrap calculation (call 18:00, wrap 03:00 = 9 hours)
  - Shared resource flag de-duplication

- [ ] **T017** [P] Contract test: `backend/tests/contract/test_dpr_incidents_delays_api.py`
  - POST /api/dprs/:id/incidents — create incident
  - POST /api/dprs/:id/delays — create delay
  - PATCH /api/dpr-incidents/:id, PATCH /api/dpr-delays/:id — update
  - DELETE endpoints
  - Severity validation (Serious/Critical require follow-up)

- [ ] **T018** [P] Contract test: `backend/tests/contract/test_dpr_attachments_api.py`
  - POST /api/dprs/:id/attachments — upload file
  - GET /api/dpr-attachments/:id/url — get signed URL
  - DELETE /api/dpr-attachments/:id — delete
  - Version clone copies references, not files

- [ ] **T019** [P] Contract test: `backend/tests/contract/test_dpr_signoffs_api.py`
  - POST /api/dprs/:id/signoffs — add signoff
  - GET /api/dprs/:id/signoffs — list signoffs
  - Signoffs cleared on version clone

- [ ] **T020** [P] Contract test: `backend/tests/contract/test_dpr_analytics_api.py`
  - GET /api/schedules/:id/analytics — cumulative analytics
  - GET /api/schedules/:id/burndown — burndown data
  - GET /api/schedules/:id/velocity — velocity (main unit + combined)
  - GET /api/schedules/:id/delays-summary — delay analysis
  - Canonical-only filtering
  - Distinct-day denominator

- [ ] **T020a** [P] Contract test: `backend/tests/contract/test_dpr_config_api.py`
  - GET /api/schedules/:id/approval-config — get approval config
  - PATCH /api/schedules/:id/approval-config — update config (Strict/Soft mode, required depts, velocity basis)
  - Default config auto-created on schedule access if none exists
  - Day-type department overrides (Shoot vs Travel vs Prep)
  - Contract ref: `docs/dpr-plan/contracts/config.md`

### Phase 2.2: Integration Tests

- [ ] **T021** [P] Integration test: `backend/tests/integration/test_dpr_workflow.py`
  - Full lifecycle: Create DPR → enter data → submit → approve → lock
  - Pre-lock reversion: Submit → revert to Draft → re-edit → re-submit
  - Post-lock versioning: Lock → unlock → new version → re-approve → re-lock
  - Snapshot immutability: schedule changes don't affect Submitted DPR

- [ ] **T022** [P] Integration test: `backend/tests/integration/test_dpr_multi_unit.py`
  - Create DPRs for 2 units on same day
  - Cross-unit pickup
  - Combined-day variance (no double-counting)
  - Shared resource time entries with de-duplication
  - Velocity with distinct-day denominator

- [ ] **T023** [P] Integration test: `backend/tests/integration/test_dpr_validation.py`
  - Scene entry status/page consistency rules (FR-093–FR-099)
  - Submission blocked with inconsistent data
  - Strict mode with pending required departments
  - N/A department satisfies Strict mode
  - Carryover = Max(0, Planned - Actual)

- [ ] **T024** [P] Integration test: `backend/tests/integration/test_dpr_snapshot_resync.py`
  - Create DPR → schedule changes → re-sync → verify snapshots updated
  - Verify actual data preserved after re-sync
  - Removed scene transitions to "Added"
  - Re-sync blocked for non-Draft DPRs

---

## Phase 3: Core Backend Implementation (ONLY after tests are failing)

### Phase 3.1: Unit Management Service + Routes

- [ ] **T025** Create `backend/services/dpr_unit_service.py`
  - `create_unit(schedule_id, name, is_main_unit)` → Unit
  - `get_units(schedule_id)` → List[Unit]
  - `update_unit(unit_id, **fields)` → Unit
  - `delete_unit(unit_id)` → bool
  - `get_main_unit(schedule_id)` → Unit | None

- [ ] **T026** Create `backend/routes/dpr_unit_routes.py`
  - Flask blueprint `dpr_unit_bp`
  - CRUD endpoints for units
  - Auth: `@require_auth`

- [ ] **T027** Register `dpr_unit_bp` in `backend/app.py`

### Phase 3.2: Core DPR Service + Routes

- [ ] **T028** Create `backend/services/dpr_service.py` — Core DPR CRUD
  - `create_dpr(shooting_day_id, unit_id, created_by)` → DPR (with auto-populated scene entries + snapshots)
  - `get_dpr(dpr_id)` → DPR with all sub-entities
  - `get_dpr_for_day_unit(shooting_day_id, unit_id)` → DPR | None
  - `update_dpr(dpr_id, **fields)` → DPR
  - `_populate_scene_snapshots(dpr_id, shooting_day_id, unit_id)` — internal helper

- [ ] **T029** Extend `backend/services/dpr_service.py` — Status workflow
  - `submit_dpr(dpr_id, actor_id)` → DPR (Draft→Submitted, validates FR-099)
  - `approve_dpr(dpr_id, actor_id)` → DPR (Submitted→Approved, checks approval mode)
  - `lock_dpr(dpr_id, actor_id)` → DPR (Approved→Locked, sets locked_at)
  - `revert_dpr(dpr_id, actor_id)` → DPR (Submitted→Draft, audit-logged, FR-004a)
  - `_check_approval_requirements(dpr_id)` — Strict/Soft mode check

- [ ] **T030** Extend `backend/services/dpr_service.py` — Versioning
  - `unlock_dpr(dpr_id, actor_id, correction_reason)` → new DPR version
  - `_clone_dpr(source_dpr_id)` — clone scene entries, dept logs, time entries, delays, incidents, attachment refs
  - `_reset_version_fields(new_dpr_id)` — status→Draft, clear signoffs/approvals
  - `_preserve_signoff_audit(new_dpr_id, source_dpr_id)` — copy signoff history to audit

- [ ] **T031** Extend `backend/services/dpr_service.py` — Snapshot Re-sync
  - `resync_with_schedule(dpr_id, actor_id)` → DPR (FR-053e)
  - Only for Draft DPRs
  - Preserve actual data, update snapshots
  - Handle added/removed scenes

- [ ] **T032** Create `backend/routes/dpr_routes.py` — Core DPR endpoints
  - Flask blueprint `dpr_bp`
  - POST /api/shooting-days/:id/dpr — create
  - GET /api/shooting-days/:id/dpr?unit_id=X — get for day+unit
  - GET /api/dprs/:id — get by ID
  - PATCH /api/dprs/:id — update fields
  - POST /api/dprs/:id/submit, /approve, /lock, /revert, /unlock, /resync
  - GET /api/schedules/:id/dprs — list all DPRs for schedule
  - Auth: `@require_auth`

- [ ] **T033** Register `dpr_bp` in `backend/app.py`

### Phase 3.3: Scene Entry Service + Routes

- [ ] **T034** Create `backend/services/dpr_scene_entry_service.py`
  - `get_scene_entries(dpr_id)` → List[SceneEntry]
  - `update_scene_entry(entry_id, **fields)` → SceneEntry (with validation FR-093–FR-099)
  - `add_scene_entry(dpr_id, scene_id=None, **fields)` → SceneEntry (manual add, status="Added")
  - `delete_scene_entry(entry_id)` → bool
  - `_validate_scene_entry(entry)` — status/page/take/setup consistency
  - `_validate_dpr_for_submission(dpr_id)` — all entries consistent (FR-099)
  - `compute_carryover(dpr_id)` → carryover_pages, page_gain (FR-074/074a)

- [ ] **T035** Create `backend/routes/dpr_scene_entry_routes.py`
  - Flask blueprint `dpr_scene_entry_bp`
  - CRUD endpoints for scene entries
  - Validation error responses with field-level detail

- [ ] **T036** Register `dpr_scene_entry_bp` in `backend/app.py`

### Phase 3.4: Department Log Service + Routes

- [ ] **T037** Create `backend/services/dpr_department_log_service.py`
  - `get_department_logs(dpr_id)` → List[DepartmentLog]
  - `update_department_log(log_id, data, actor_id)` → DepartmentLog
  - `submit_department_log(log_id, actor_id)` → DepartmentLog
  - `mark_department_na(log_id, reason, actor_id)` → DepartmentLog (FR-014a)
  - `_check_editability(log_id, dpr_status)` — lifecycle enforcement (FR-015a)
  - `get_submission_tracker(dpr_id)` → dict (which depts submitted/pending/N/A)
  - `_initialize_department_logs(dpr_id, department_list)` — create Pending logs on DPR creation

- [ ] **T038** Create `backend/routes/dpr_department_log_routes.py`
  - Flask blueprint `dpr_dept_log_bp`
  - CRUD + submit + mark-na endpoints

- [ ] **T039** Register `dpr_dept_log_bp` in `backend/app.py`

### Phase 3.5: Time Entry Service + Routes

- [ ] **T040** Create `backend/services/dpr_time_entry_service.py`
  - `create_time_entry(dpr_id, **fields)` → TimeEntry
  - `update_time_entry(entry_id, **fields)` → TimeEntry
  - `delete_time_entry(entry_id)` → bool
  - `get_time_entries(dpr_id)` → List[TimeEntry]
  - `_calculate_hours(call_time, wrap_time, wrap_next_day, breaks)` → hours, overtime (FR-021b)
  - `_check_meal_penalty(entry, config)` → bool (FR-019)
  - `_check_forced_call(entry, prev_wrap, config)` → bool (FR-020)
  - `_check_shared_resource_duplicate(dpr_id, person_id)` → bool (FR-021c)
  - `prepopulate_cast_times(dpr_id)` → List[TimeEntry] (FR-021)

- [ ] **T041** Create `backend/routes/dpr_time_entry_routes.py`
  - Flask blueprint `dpr_time_entry_bp`
  - CRUD endpoints

- [ ] **T042** Register `dpr_time_entry_bp` in `backend/app.py`

### Phase 3.6: Incidents, Delays, Attachments, Signoffs

- [ ] **T043** [P] Create `backend/services/dpr_incident_service.py`
  - CRUD for incidents
  - Severity validation (Serious/Critical require follow-up)

- [ ] **T044** [P] Create `backend/services/dpr_delay_service.py`
  - CRUD for delays
  - Type categorization, duration tracking

- [ ] **T045** [P] Create `backend/services/dpr_attachment_service.py`
  - Upload with compression, signed URL generation
  - Size limit enforcement from config
  - `clone_attachment_references(source_dpr_id, target_dpr_id)` — version clone

- [ ] **T046** [P] Create `backend/services/dpr_signoff_service.py`
  - Add/list signoffs
  - Clear signoffs on version clone
  - Preserve historical signoffs in audit trail

- [ ] **T047** Create `backend/routes/dpr_sub_entity_routes.py`
  - Flask blueprint `dpr_sub_entity_bp`
  - Endpoints for incidents, delays, attachments, signoffs

- [ ] **T048** Register `dpr_sub_entity_bp` in `backend/app.py`

### Phase 3.7: Analytics & Metrics Service

- [ ] **T049** Create `backend/services/dpr_metrics_service.py`
  - `compute_dpr_metrics(dpr_id)` → MaterializedMetrics
  - `invalidate_metrics(dpr_id)` → void
  - `get_or_compute_metrics(dpr_id)` → MaterializedMetrics (lazy recompute)

- [ ] **T050** Create `backend/services/dpr_analytics_service.py`
  - `get_schedule_analytics(schedule_id)` → cumulative totals, velocity, projections
  - `get_burndown_data(schedule_id)` → planned vs actual timeseries
  - `get_velocity(schedule_id)` → main_unit_velocity, combined_velocity (FR-073a)
  - `get_delay_analysis(schedule_id)` → delay breakdown by category
  - `_get_canonical_dprs(schedule_id)` — filter non-superseded only (FR-068)
  - `_get_distinct_shooting_days(schedule_id, included_only)` → count (FR-073)
  - `_get_schedule_planned_baseline(schedule_id)` → unique scene pages (FR-028a)

- [ ] **T051** Create `backend/routes/dpr_analytics_routes.py`
  - Flask blueprint `dpr_analytics_bp`
  - GET endpoints for analytics, burndown, velocity, delay analysis

- [ ] **T052** Register `dpr_analytics_bp` in `backend/app.py`

### Phase 3.8: Approval Config Service

- [ ] **T053** Create `backend/services/dpr_config_service.py`
  - `get_approval_config(schedule_id)` → ApprovalConfig
  - `update_approval_config(schedule_id, **fields)` → ApprovalConfig
  - `get_required_departments(schedule_id, day_type)` → List[str] (FR-086a)
  - `get_velocity_projection_basis(schedule_id)` → 'main_unit' | 'combined'

- [ ] **T054** Create `backend/routes/dpr_config_routes.py`
  - Flask blueprint `dpr_config_bp`
  - GET/PATCH for approval config

- [ ] **T055** Register `dpr_config_bp` in `backend/app.py`

### Phase 3.9: PDF Export Service

- [ ] **T056** Create `backend/services/dpr_pdf_service.py`
  - `generate_dpr_pdf(dpr_id)` → PDF bytes
  - Industry-standard DPR layout (FR-032)
  - Version number in header (FR-069)
  - Superseded notice if applicable
  - QR code / verification link in footer (FR-031a)
  - Sign-off block
  - Attachment thumbnails (optional)
  - Payroll disclaimer in footer (FR-021a)

- [ ] **T057** Create PDF template `backend/services/templates/dpr_pdf.html`
  - WeasyPrint HTML template for DPR
  - Header: production name, date, unit, day type, version
  - Sections: general info, scene progress table, time sheets, dept logs, incidents, delays, totals, sign-off
  - Footer: QR code, payroll disclaimer, page numbers

- [ ] **T058** Add PDF export endpoints to `backend/routes/dpr_routes.py`
  - GET /api/dprs/:id/pdf — download PDF
  - GET /api/dprs/:id/print — printable HTML view

### Phase 3.10: Notification Service

- [ ] **T059** Extend `backend/services/dpr_service.py` or create `backend/services/dpr_notification_service.py`
  - `notify_dpr_submitted(dpr_id)` → notify LP + Producer (FR-090)
  - `notify_dpr_approved(dpr_id)` → notify author (FR-091)
  - `notify_dpr_locked(dpr_id)` → notify author (FR-091)
  - `notify_schedule_change(shooting_day_id, change_type)` → notify AD (FR-092/092a)
  - Filter by material changes only (scene add/remove, page count, unit reassignment)

---

## Phase 4: Frontend Implementation

### Phase 4.1: API Service Functions

- [ ] **T060** Extend `frontend/src/services/apiService.js` — DPR API functions
  - Units: `getUnits`, `createUnit`, `updateUnit`, `deleteUnit`
  - DPR: `createDpr`, `getDpr`, `getDprForDayUnit`, `updateDpr`, `listScheduleDprs`
  - Status: `submitDpr`, `approveDpr`, `lockDpr`, `revertDpr`, `unlockDpr`, `resyncDpr`
  - Scene entries: `getSceneEntries`, `updateSceneEntry`, `addSceneEntry`, `deleteSceneEntry`
  - Dept logs: `getDepartmentLogs`, `updateDepartmentLog`, `submitDepartmentLog`, `markDepartmentNa`
  - Time entries: `createTimeEntry`, `updateTimeEntry`, `deleteTimeEntry`, `getTimeEntries`, `prepopulateCastTimes`
  - Incidents/Delays: CRUD functions
  - Attachments: `uploadAttachment`, `getAttachmentUrl`, `deleteAttachment`
  - Signoffs: `addSignoff`, `getSignoffs`
  - Analytics: `getScheduleAnalytics`, `getBurndownData`, `getVelocity`, `getDelayAnalysis`
  - Config: `getApprovalConfig`, `updateApprovalConfig`
  - PDF: `downloadDprPdf`, `getDprPrintView`

### Phase 4.2: Core DPR Components

- [ ] **T061** [P] Create `frontend/src/components/dpr/DprCreateButton.jsx` + `.css`
  - "File DPR" button on shooting day (FR-044)
  - Unit selector dropdown if multiple units exist
  - Opens existing DPR if one already exists (FR-045)

- [ ] **T062** Create `frontend/src/components/dpr/DprEditor.jsx` + `.css`
  - Main DPR editing interface
  - Header: date, unit, day type, weather, call/wrap times
  - Status bar with workflow actions (Submit, Approve, Lock, Revert)
  - Tabs or sections: Scenes, Department Logs, Time Tracking, Incidents & Delays
  - Auto-save (FR-042)
  - Version indicator
  - Re-sync button for Draft DPRs (FR-053e)

- [ ] **T063** [P] Create `frontend/src/components/dpr/DprStatusBar.jsx` + `.css`
  - Status pill (Draft/Submitted/Approved/Locked)
  - Action buttons based on current status and user role
  - Version number badge
  - "Superseded" banner for old versions (FR-070)

- [ ] **T064** [P] Create `frontend/src/components/dpr/DprGeneralInfo.jsx` + `.css`
  - Call time, first shot, lunch, camera wrap, company wrap
  - Weather input
  - Day type selector
  - General notes textarea

### Phase 4.3: Scene Progress Components

- [ ] **T065** Create `frontend/src/components/dpr/SceneProgressTable.jsx` + `.css`
  - Table: scene #, slugline, INT/EXT, location, planned pages, actual pages, status, setups, takes, variance indicator
  - Inline editing for status, pages, setups, takes
  - Snapshot data shown alongside actual
  - Visual variance indicator (ahead/behind)
  - "Add Scene" button for manual additions
  - Daily totals row
  - Validation error highlighting (FR-093–FR-099)

- [ ] **T066** [P] Create `frontend/src/components/dpr/SceneEntryRow.jsx` + `.css`
  - Individual scene row with inline editing
  - Status dropdown (Complete/Partial/Not Shot/Added/Pickup)
  - Pages input (eighths)
  - Setups/takes counters
  - Warning indicators for over-shot, zero-setup
  - Notes expandable

- [ ] **T067** [P] Create `frontend/src/components/dpr/DailyTotals.jsx` + `.css`
  - Computed totals: pages shot, setups, takes, variance
  - Carryover pages (≥0) and Page Gain display
  - Combined-day totals for multi-unit view

### Phase 4.4: Department Log Components

- [ ] **T068** Create `frontend/src/components/dpr/DepartmentLogPanel.jsx` + `.css`
  - Submission tracker (FR-015): which departments submitted/pending/N/A
  - Expandable sections per department
  - Camera log with extended fields (checksum, offload, LTO)
  - Sound, Script Supervisor, General log forms
  - Submit button per department
  - "Mark as N/A" button for AD/LP (FR-014a)
  - Editability state based on DPR status (FR-015a)

- [ ] **T069** [P] Create `frontend/src/components/dpr/CameraLogForm.jsx` + `.css`
  - Extended camera fields: media ID, codec, resolution, checksum, offload status, LTO backup
  - Inline validation

### Phase 4.5: Time Tracking Components

- [ ] **T070** Create `frontend/src/components/dpr/TimeTrackingPanel.jsx` + `.css`
  - Cast time sheet: person, character, call/set/wrap/breaks, hours, OT
  - Crew time sheet: person, dept/role, call/wrap/breaks, hours, OT
  - Meal penalty and forced call flags (auto-computed)
  - Overnight wrap indicator / "wrap next day" toggle (FR-021b)
  - Shared resource badge (FR-021c)
  - Pre-populate cast times button (FR-021)
  - **Payroll disclaimer banner** (FR-021a)
  - Add/remove entries

- [ ] **T071** [P] Create `frontend/src/components/dpr/TimeEntryRow.jsx` + `.css`
  - Individual time entry with native time pickers
  - Auto-calculated hours display
  - Meal penalty / forced call icons
  - Shared resource flag toggle

### Phase 4.6: Incidents, Delays, Attachments

- [ ] **T072** [P] Create `frontend/src/components/dpr/IncidentLog.jsx` + `.css`
  - Add/edit incidents with type, severity, description, persons, action taken
  - Follow-up required for Serious/Critical (FR-025)

- [ ] **T073** [P] Create `frontend/src/components/dpr/DelayLog.jsx` + `.css`
  - Add/edit delays with type, duration, description, optional scene link
  - Total delay minutes display

- [ ] **T074** [P] Create `frontend/src/components/dpr/AttachmentManager.jsx` + `.css`
  - Upload files with drag-and-drop
  - Thumbnail previews for images
  - File size limit enforcement
  - Low bandwidth mode awareness (FR-043a)

### Phase 4.7: Sign-Off & Export

- [ ] **T075** [P] Create `frontend/src/components/dpr/SignOffBlock.jsx` + `.css`
  - Add signoff (name, role, timestamp)
  - Display existing signoffs
  - Historical signoffs from previous versions (FR-037a)

- [ ] **T076** [P] Create `frontend/src/components/dpr/DprExportBar.jsx` + `.css`
  - Download PDF button
  - Print view button
  - Share link (existing mechanism)
  - Version dropdown for superseded versions

### Phase 4.8: Analytics Dashboard

- [ ] **T077** Create `frontend/src/components/dpr/AnalyticsDashboard.jsx` + `.css`
  - Cumulative totals: pages to date, average pages/day, projected wrap
  - Main Unit Velocity vs Combined Velocity display (FR-073a)
  - Projection basis selector (configurable)

- [ ] **T078** [P] Create `frontend/src/components/dpr/BurndownChart.jsx` + `.css`
  - Planned vs actual pages over time (FR-028)
  - Per-unit, per-day, per-schedule toggle
  - Chart library (recharts or similar)

- [ ] **T079** [P] Create `frontend/src/components/dpr/DelayAnalysis.jsx` + `.css`
  - Delay breakdown by category across all days
  - Bar chart visualization

- [ ] **T080** [P] Create `frontend/src/components/dpr/VelocityGauge.jsx` + `.css`
  - Main unit vs combined velocity display
  - Projected wrap date

### Phase 4.9: Configuration & List Views

- [ ] **T081** Create `frontend/src/components/dpr/ApprovalConfigPanel.jsx` + `.css`
  - Strict / Soft mode selector
  - Required departments by day type matrix
  - Meal penalty and forced call threshold config
  - Velocity projection basis selector
  - Max attachment size config

- [ ] **T082** Create `frontend/src/components/dpr/DprListView.jsx` + `.css`
  - List all DPRs for a schedule
  - Filter by unit, day type, status
  - Quick status indicators
  - Link to individual DPR editor

- [ ] **T083** Create `frontend/src/components/dpr/UnitManager.jsx` + `.css`
  - Add/edit/delete units for a production
  - Set main unit designation
  - Reorder units

### Phase 4.10: Pages & Routing

- [ ] **T084** Create `frontend/src/pages/DprEditorPage.jsx` + `.css`
  - Route: `/scripts/:scriptId/schedule/:scheduleId/dpr/:dprId`
  - Loads DPR data, renders DprEditor
  - Tablet-optimized layout (FR-043)

- [ ] **T085** Create `frontend/src/pages/DprDashboardPage.jsx` + `.css`
  - Route: `/scripts/:scriptId/schedule/:scheduleId/dashboard`
  - Analytics dashboard with burndown, velocity, delay analysis

- [ ] **T086** Register routes in `frontend/src/App.jsx`
  - Add DPR editor and dashboard routes
  - Navigation links from schedule view

### Phase 4.11: Low Bandwidth Mode

- [ ] **T087** Create `frontend/src/components/dpr/LowBandwidthToggle.jsx` + `.css`
  - Toggle for Low Bandwidth / Text-Only mode (FR-043a)
  - Persists preference in localStorage
  - Disables image uploads, heavy UI when active

- [ ] **T088** Create `frontend/src/hooks/useLowBandwidthMode.js`
  - React hook for low bandwidth state
  - Conditionally renders heavy components

---

## Phase 5: Integration

- [ ] **T089** Connect DPR creation to shooting schedule view
  - Add "File DPR" button in `frontend/src/components/schedule/` (existing)
  - Wire DprCreateButton into schedule day card

- [ ] **T090** Connect notification triggers to existing notification system
  - Wire DPR status change events to `backend/services/` notification dispatch
  - Schedule change detection for FR-092/092a

- [ ] **T091** Connect carryover flags to scheduling module
  - Surface carryover candidates in schedule view (FR-078)
  - Link from carryover indicator to source DPR

- [ ] **T092** Implement materialized metrics invalidation triggers
  - Database triggers on scene_entries, delays tables
  - Service-level invalidation on version creation, velocity flag change

- [ ] **T093** Add DPR version verification endpoint
  - GET /api/dprs/:id/verify — returns canonical status for QR code deep link (FR-031a)
  - Public endpoint (no auth) with rate limiting

---

## Phase 6: Polish

- [ ] **T094** [P] Unit tests: `backend/tests/unit/test_dpr_validation.py`
  - Scene entry validation rules (FR-093–FR-099)
  - Carryover math (Max 0, Page Gain)
  - Overnight hour calculation
  - Shared resource de-duplication logic

- [ ] **T095** [P] Unit tests: `backend/tests/unit/test_dpr_snapshot.py`
  - Snapshot population from schedule
  - Re-sync logic (added/removed scenes)
  - Snapshot immutability after Draft

- [ ] **T096** [P] Unit tests: `backend/tests/unit/test_dpr_versioning.py`
  - Clone behavior (what resets, what preserves)
  - Signoff audit trail preservation
  - Attachment reference copy (not binary)

- [ ] **T097** [P] Unit tests: `backend/tests/unit/test_dpr_analytics.py`
  - Velocity: main unit vs combined, distinct-day denominator
  - Burndown: unique scene planned baseline
  - Canonical-only filtering
  - Materialized metrics invalidation

- [ ] **T098** Performance tests: DPR API response times
  - Create/read DPR with 30 scenes: <500ms
  - Analytics aggregation for 60-day schedule: <1000ms
  - PDF generation: <3000ms
  - Materialized metrics read (hot): <100ms

- [ ] **T099** [P] Accessibility & touch optimization
  - 44px minimum touch targets (FR-043)
  - Native time pickers on mobile
  - Keyboard navigation for scene entry table

- [ ] **T100** [P] Update project documentation
  - Update `docs/README.md` with DPR feature overview
  - API endpoint documentation for DPR routes
  - Update deployment notes for QR code generation dependency

- [ ] **T101** Remove duplication
  - Consolidate shared Supabase client initialization across DPR route files
  - Extract common validation helpers
  - Ensure consistent error response format

- [ ] **T102** End-to-end manual testing checklist
  - Full workflow: create schedule → assign scenes → create DPR → enter data → submit → approve → lock
  - Multi-unit scenario
  - Version correction flow
  - PDF download and QR code verification
  - Low bandwidth mode
  - Tablet/mobile responsive check

---

## Dependencies

```
Phase 0 (T000a-T000d) → Phase 1 (T001-T011) → Phase 2 (T012-T024) → Phase 3 (T025-T059)
                                                                      → Phase 4 (T060-T088)
                                                                      → Phase 5 (T089-T093)
                                                                      → Phase 6 (T094-T102)

Within Phase 0:
  T000a → T000b, T000c, T000d (branch first, deps in parallel)

Within Phase 1:
  T001 → T002 (units before DPR core)
  T002 → T003, T004, T005, T006, T007 (core before sub-entities)
  T003-T007 → T008 (sub-entities before signoffs/audit)
  T008 → T009 (audit before metrics)
  T002 → T010 (DPR core before config)

Within Phase 2:
  T012-T020a: All 10 contract test files in parallel (different files, no deps)
  T021-T024: All 4 integration test files in parallel

Within Phase 3:
  T025-T027 → T028 (unit service before DPR service)
  T028 → T029 → T030 → T031 (DPR service sequential: CRUD → workflow → versioning → resync)
  T028 → T034, T037, T040, T043-T046 (DPR service before sub-entity services)
  T034 → T037 (scene entries before dept logs — submission tracker needs scene validation)
  T049 → T050 (metrics before analytics)
  T050 → T051 (analytics service before routes)
  T053 → T054 (config service before config routes)
  All services → T056 (PDF needs all data)

Within Phase 4:
  T060 → all components (API service before components)
  T062 → T065, T068, T070 (editor shell before content panels)
  T084-T086 → T089 (pages before integration)

Phase 5 depends on:
  Phase 3 complete + Phase 4.10 complete
  T092 depends on T009 (metrics triggers), T049 (metrics service)

Phase 6 depends on:
  Phase 3 + Phase 4 + Phase 5 complete
```

## Parallel Execution Examples

```
# Phase 0 — Parallel dependency installs (after T000a):
  T000b: qrcode[pil] in requirements.txt
  T000c: recharts in package.json
  T000d: Supabase Storage bucket

# Phase 1 — Parallel sub-entity migrations (after T002):
  T004: migration 034 (department logs)
  T005: migration 035 (time entries)
  T006: migration 036 (incidents + delays)
  T007: migration 037 (attachments)

# Phase 2 — All contract tests in parallel:
  T012-T020a: 10 contract test files (all different files, no deps)
  T021-T024: 4 integration test files (all different files)

# Phase 3 — Parallel sub-entity services:
  T043: incident service
  T044: delay service
  T045: attachment service
  T046: signoff service

# Phase 4 — Parallel component groups:
  T063: DprStatusBar
  T064: DprGeneralInfo
  T066: SceneEntryRow
  T067: DailyTotals
  T069: CameraLogForm
  T071: TimeEntryRow
  T072: IncidentLog
  T073: DelayLog
  T074: AttachmentManager
  T075: SignOffBlock
  T076: DprExportBar
```

## Validation Checklist

- [x] All 11 entities have model/table tasks (T001-T010)
- [x] All 19 FR groups have corresponding service tasks
- [x] Tests come before implementation (Phase 2 before Phase 3)
- [x] Parallel tasks are truly independent (different files, no deps)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] 27 gap fixes from Rev 2/3/4 covered in implementation tasks
- [x] All edge cases (25) addressable by combination of tasks
- [x] PDF export with QR code covered (T056-T058)
- [x] Low bandwidth mode covered (T087-T088)
- [x] Analytics (velocity split, burndown baseline, canonical filtering) covered (T050)
- [x] Approval config (Strict/Soft, N/A, day-type depts) covered (T053-T054)
- [x] **All 10 contract files have corresponding test tasks** (T012-T020a)
- [x] **Setup phase covers new dependencies** (T000b: qrcode, T000c: recharts, T000d: storage)
- [x] **Version verify endpoint tested** (T013 + T093)
- [x] **Time entry prepopulate endpoint tested** (T016)
- [x] **T011 clarified** — minimal schedule extension per research.md decision #12
- [x] **Plan artifacts referenced** in header (plan.md, research.md, data-model.md, contracts/, quickstart.md)
