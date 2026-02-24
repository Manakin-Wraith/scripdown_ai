# Data Model: Daily Production Reporting (DPR)

**Phase 1 Output** | **Date**: 2026-02-23  
**Source**: `docs/SPEC_Daily_Production_Reporting.md` (Rev 4)

---

## Entity Relationship Diagram (Text)

```
shooting_schedules (existing)
  │
  ├─── units (NEW — 031)
  │      │
  │      └─── daily_production_reports (NEW — 032)
  │             │
  │             ├─── dpr_scene_entries (NEW — 033)
  │             │      └─── dpr_attachments (via scene_entry_id)
  │             │
  │             ├─── dpr_department_logs (NEW — 034)
  │             │      └─── dpr_attachments (via department_log_id)
  │             │
  │             ├─── dpr_time_entries (NEW — 035)
  │             │
  │             ├─── dpr_incidents (NEW — 036)
  │             │      └─── dpr_attachments (via incident_id)
  │             │
  │             ├─── dpr_delays (NEW — 036)
  │             │
  │             ├─── dpr_attachments (NEW — 037, via dpr_id)
  │             │
  │             ├─── dpr_signoffs (NEW — 038)
  │             │
  │             ├─── dpr_audit_log (NEW — 038)
  │             │
  │             └─── dpr_materialized_metrics (NEW — 039)
  │
  └─── production_approval_config (NEW — 040)

shooting_days (existing, extended — 041)
  │
  └─── daily_production_reports (FK shooting_day_id)
```

---

## Entities

### 1. Unit (Migration 031)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | |
| `schedule_id` | UUID | FK shooting_schedules(id) ON DELETE CASCADE, NOT NULL | Parent schedule |
| `name` | TEXT | NOT NULL | e.g., "1st Unit", "2nd Unit", "Splinter Unit" |
| `is_main_unit` | BOOLEAN | DEFAULT false | Designates the main unit for velocity projections (AD-7) |
| `sort_order` | INT | DEFAULT 0 | Display ordering |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | DEFAULT now() | Via trigger |

**Indexes**: `schedule_id`  
**RLS**: Via `schedule → script → auth.uid()` chain  
**Validation**: At most one `is_main_unit = true` per schedule (enforced at service level)

---

### 2. Daily Production Report (Migration 032)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `shooting_day_id` | UUID | FK shooting_days(id), NOT NULL | Which shooting day |
| `unit_id` | UUID | FK units(id), NOT NULL | Which unit (AD-1) |
| `schedule_id` | UUID | FK shooting_schedules(id), NOT NULL | Denormalized for query performance |
| `version` | INT | NOT NULL DEFAULT 1 | Version number (AD-5) |
| `parent_version_id` | UUID | FK self, NULLABLE | Previous version (if correction) |
| `is_superseded` | BOOLEAN | DEFAULT false | True if a newer version exists |
| `status` | TEXT | CHECK (Draft/Submitted/Approved/Locked), DEFAULT 'Draft' | Workflow status (FR-004) |
| `day_type` | TEXT | CHECK (Shoot/Company Move/Prep/Travel/Holiday/Dark/Strike) | Day classification (AD-3) |
| `include_in_velocity` | BOOLEAN | DEFAULT true (Shoot), false (others) | Velocity inclusion flag (AD-7) |
| `call_time` | TIMESTAMPTZ | NULLABLE | |
| `first_shot_time` | TIMESTAMPTZ | NULLABLE | |
| `lunch_start` | TIMESTAMPTZ | NULLABLE | |
| `lunch_end` | TIMESTAMPTZ | NULLABLE | |
| `camera_wrap_time` | TIMESTAMPTZ | NULLABLE | |
| `company_wrap_time` | TIMESTAMPTZ | NULLABLE | |
| `weather` | JSONB | DEFAULT '{}' | `{condition, temp_high, temp_low, notes}` |
| `notes` | TEXT | NULLABLE | General notes |
| `locked_at` | TIMESTAMPTZ | NULLABLE | Set when status → Locked |
| `created_by` | UUID | FK auth.users(id) | DPR author |
| `approved_by` | UUID | FK auth.users(id), NULLABLE | Approver |
| `approved_at` | TIMESTAMPTZ | NULLABLE | |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | DEFAULT now() | Via trigger |

**Unique**: `(shooting_day_id, unit_id) WHERE is_superseded = false` — one canonical DPR per day+unit  
**Indexes**: `shooting_day_id`, `unit_id`, `schedule_id`, `status`, `parent_version_id`  
**RLS**: Via `schedule → script → auth.uid()` chain

---

### 3. DPR Scene Entry (Migration 033)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `dpr_id` | UUID | FK daily_production_reports(id) ON DELETE CASCADE, NOT NULL | Parent DPR |
| `scene_id` | UUID | FK scenes(id), NULLABLE | Source scene (NULL for fully manual adds) |
| `status` | TEXT | CHECK (Complete/Partial/Not Shot/Added/Pickup), DEFAULT 'Not Shot' | Scene status (FR-007) |
| `actual_pages_eighths` | INT | DEFAULT 0 | Actual pages shot in eighths |
| `setups` | INT | DEFAULT 0 | Number of setups |
| `takes` | INT | DEFAULT 0 | Number of takes |
| `circle_takes` | JSONB | DEFAULT '[]' | Array of circle take labels |
| `start_time` | TIMESTAMPTZ | NULLABLE | |
| `end_time` | TIMESTAMPTZ | NULLABLE | |
| `notes` | TEXT | NULLABLE | |
| `snapshot_scene_number` | TEXT | | Scene number at DPR creation (FR-053) |
| `snapshot_slugline` | TEXT | | Scene heading snapshot (FR-053a) |
| `snapshot_int_ext` | TEXT | | INT/EXT snapshot (FR-053b) |
| `snapshot_location` | TEXT | | Location name snapshot (FR-053c) |
| `snapshot_day_night` | TEXT | | Day/Night snapshot (FR-053d) |
| `snapshot_planned_pages_eighths` | INT | DEFAULT 0 | Planned pages snapshot (FR-054) |
| `snapshot_schedule_order` | INT | DEFAULT 0 | Schedule order snapshot (FR-055) |
| `snapshot_unit_assignment` | TEXT | NULLABLE | Unit assignment snapshot (FR-056) |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | DEFAULT now() | Via trigger |

**Indexes**: `dpr_id`, `scene_id`, `status`  
**RLS**: Via `dpr → schedule → script → auth.uid()` chain  
**Validation Rules** (FR-093–FR-099):
- Complete: `actual_pages_eighths > 0`, `takes >= 1`
- Partial: `actual_pages_eighths > 0 AND actual_pages_eighths < snapshot_planned_pages_eighths`, `takes >= 1`
- Not Shot: `actual_pages_eighths = 0`
- Added: Any page count allowed (no planned baseline)
- Pickup: `actual_pages_eighths > 0`, `takes >= 1`

---

### 4. DPR Department Log (Migration 034)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `dpr_id` | UUID | FK daily_production_reports(id) ON DELETE CASCADE, NOT NULL | |
| `department_type` | TEXT | CHECK (Camera/Sound/Script Supervisor/Art/Costume/Makeup/Locations/VFX/Stunts/Transport/General) | |
| `submission_status` | TEXT | CHECK (Pending/Submitted/N/A), DEFAULT 'Pending' | (FR-014, FR-014a) |
| `submitted_by` | UUID | FK auth.users(id), NULLABLE | |
| `submitted_at` | TIMESTAMPTZ | NULLABLE | |
| `na_reason` | TEXT | NULLABLE | Required when status = N/A (FR-014a) |
| `na_marked_by` | UUID | FK auth.users(id), NULLABLE | AD/LP who marked N/A |
| `data` | JSONB | DEFAULT '{}' | Structured data (schema varies by department_type) |
| `notes` | TEXT | NULLABLE | |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | DEFAULT now() | Via trigger |

**Indexes**: `dpr_id`, `department_type`, `submission_status`  
**Editability Lifecycle** (FR-015a): Draft → editable; Submitted → frozen; Approved/Locked → immutable  
**Version Clone**: Preserves `submission_status` (Submitted stays Submitted) (FR-070c)

---

### 5. DPR Time Entry (Migration 035)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `dpr_id` | UUID | FK daily_production_reports(id) ON DELETE CASCADE, NOT NULL | |
| `person_name` | TEXT | NOT NULL | |
| `person_id` | UUID | NULLABLE | FK for de-duplication (FR-021c) |
| `entry_type` | TEXT | CHECK (cast/crew), NOT NULL | |
| `character_name` | TEXT | NULLABLE | For cast entries |
| `department` | TEXT | NULLABLE | For crew entries |
| `role` | TEXT | NULLABLE | For crew entries |
| `call_time` | TIMESTAMPTZ | NULLABLE | |
| `on_set_time` | TIMESTAMPTZ | NULLABLE | Cast only |
| `wrap_time` | TIMESTAMPTZ | NULLABLE | |
| `wrap_next_day` | BOOLEAN | DEFAULT false | Overnight wrap flag (FR-021b) |
| `first_meal_start` | TIMESTAMPTZ | NULLABLE | |
| `first_meal_end` | TIMESTAMPTZ | NULLABLE | |
| `second_meal_start` | TIMESTAMPTZ | NULLABLE | |
| `second_meal_end` | TIMESTAMPTZ | NULLABLE | |
| `travel_hours` | DECIMAL(4,2) | DEFAULT 0 | |
| `calculated_hours` | DECIMAL(5,2) | NULLABLE | Auto-computed |
| `overtime_hours` | DECIMAL(4,2) | DEFAULT 0 | |
| `meal_penalty` | BOOLEAN | DEFAULT false | Auto-flagged (FR-019) |
| `forced_call` | BOOLEAN | DEFAULT false | Auto-flagged (FR-020) |
| `is_shared_resource` | BOOLEAN | DEFAULT false | Multi-unit shared (FR-021c) |
| `notes` | TEXT | NULLABLE | |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | DEFAULT now() | Via trigger |

**Indexes**: `dpr_id`, `person_id`, `entry_type`  
**Soft unique**: `(dpr_id, person_id) WHERE person_id IS NOT NULL`  
**Overnight calc**: If `wrap_next_day = true`, hours = (wrap + 24h) - call - breaks

---

### 6. DPR Incident (Migration 036)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `dpr_id` | UUID | FK ON DELETE CASCADE, NOT NULL | |
| `type` | TEXT | CHECK (Injury/Near Miss/Safety Violation/Equipment Damage) | |
| `severity` | TEXT | CHECK (Minor/Moderate/Serious/Critical) | |
| `description` | TEXT | NOT NULL | |
| `location` | TEXT | NULLABLE | |
| `incident_time` | TIMESTAMPTZ | NULLABLE | |
| `persons_involved` | JSONB | DEFAULT '[]' | `[{name, role, injury_description}]` |
| `witnesses` | JSONB | DEFAULT '[]' | `[{name, role}]` |
| `action_taken` | TEXT | NULLABLE | |
| `follow_up_required` | BOOLEAN | DEFAULT false | Required for Serious/Critical (FR-025) |
| `follow_up_notes` | TEXT | NULLABLE | |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | DEFAULT now() | Via trigger |

**Validation**: Serious/Critical severity requires `follow_up_required = true`

---

### 7. DPR Delay (Migration 036)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `dpr_id` | UUID | FK ON DELETE CASCADE, NOT NULL | |
| `type` | TEXT | CHECK (Weather/Technical/Talent/Location/Medical/Meal Penalty/Company Move/Other) | |
| `duration_minutes` | INT | NOT NULL | |
| `description` | TEXT | NULLABLE | |
| `scene_entry_id` | UUID | FK dpr_scene_entries(id), NULLABLE | Optional scene association |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | DEFAULT now() | Via trigger |

**Indexes**: `dpr_id`, `type`

---

### 8. DPR Attachment (Migration 037)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `dpr_id` | UUID | FK, NULLABLE | General DPR attachment |
| `scene_entry_id` | UUID | FK, NULLABLE | Scene entry attachment |
| `incident_id` | UUID | FK, NULLABLE | Incident attachment |
| `department_log_id` | UUID | FK, NULLABLE | Dept log attachment |
| `file_url` | TEXT | NOT NULL | Supabase Storage URL |
| `file_type` | TEXT | NOT NULL | MIME type |
| `file_size_bytes` | BIGINT | NOT NULL | |
| `uploader_id` | UUID | FK auth.users(id) | |
| `upload_timestamp` | TIMESTAMPTZ | DEFAULT now() | |
| `is_reference_copy` | BOOLEAN | DEFAULT false | True if copied during version clone (FR-085) |
| `source_attachment_id` | UUID | FK self, NULLABLE | Points to original if reference copy |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |

**CHECK**: At least one parent FK is not null  
**Version clone**: Copies references only (not binaries) — `is_reference_copy = true`

---

### 9. DPR Sign-Off (Migration 038)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `dpr_id` | UUID | FK ON DELETE CASCADE, NOT NULL | |
| `signer_name` | TEXT | NOT NULL | |
| `signer_role` | TEXT | NOT NULL | |
| `signed_at` | TIMESTAMPTZ | DEFAULT now() | |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |

**Version clone**: Sign-offs are cleared on new version; historical preserved in audit log

---

### 10. DPR Audit Log (Migration 038)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `dpr_id` | UUID | FK ON DELETE CASCADE, NOT NULL | |
| `event_type` | TEXT | NOT NULL | e.g., `status_change`, `version_created`, `resync`, `na_marked` |
| `actor_id` | UUID | FK auth.users(id) | Who performed the action |
| `actor_name` | TEXT | NULLABLE | Denormalized for display |
| `details` | JSONB | DEFAULT '{}' | Event-specific data |
| `previous_version_signoffs` | JSONB | NULLABLE | Preserved from parent version (FR-037a) |
| `correction_reason` | TEXT | NULLABLE | Required for unlock/version create |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |

---

### 11. DPR Materialized Metrics (Migration 039)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `dpr_id` | UUID | FK UNIQUE ON DELETE CASCADE, NOT NULL | One metrics row per DPR |
| `total_pages_eighths` | INT | DEFAULT 0 | Sum actual pages |
| `total_setups` | INT | DEFAULT 0 | |
| `total_takes` | INT | DEFAULT 0 | |
| `total_delay_minutes` | INT | DEFAULT 0 | |
| `planned_pages_eighths` | INT | DEFAULT 0 | Sum snapshot planned |
| `variance_pages_eighths` | INT | DEFAULT 0 | actual - planned |
| `carryover_pages_eighths` | INT | DEFAULT 0 | Max(0, planned - actual) (FR-074) |
| `page_gain_eighths` | INT | DEFAULT 0 | Max(0, actual - planned) (FR-074a) |
| `scenes_complete` | INT | DEFAULT 0 | |
| `scenes_partial` | INT | DEFAULT 0 | |
| `scenes_not_shot` | INT | DEFAULT 0 | |
| `scenes_added` | INT | DEFAULT 0 | |
| `scenes_pickup` | INT | DEFAULT 0 | |
| `computed_at` | TIMESTAMPTZ | | Last computation time |
| `is_stale` | BOOLEAN | DEFAULT false | Set true by triggers |

**Invalidation triggers**: INSERT/UPDATE/DELETE on `dpr_scene_entries`, `dpr_delays`

---

### 12. Production Approval Config (Migration 040)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | |
| `schedule_id` | UUID | FK UNIQUE shooting_schedules(id) | One config per schedule |
| `approval_mode` | TEXT | CHECK (Strict/Soft), DEFAULT 'Soft' | (AD-9) |
| `required_departments` | JSONB | DEFAULT '[]' | Default required departments |
| `required_departments_by_day_type` | JSONB | DEFAULT '{}' | `{Shoot: [...], Travel: [...]}` overrides |
| `velocity_projection_basis` | TEXT | CHECK (main_unit/combined), DEFAULT 'main_unit' | (FR-073a) |
| `main_unit_id` | UUID | FK units(id), NULLABLE | Which unit is "main" |
| `meal_penalty_config` | JSONB | DEFAULT '{}' | `{threshold_hours, penalty_duration}` |
| `forced_call_config` | JSONB | DEFAULT '{}' | `{min_turnaround_hours}` |
| `max_attachment_size_mb` | INT | DEFAULT 25 | |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | DEFAULT now() | Via trigger |

---

## State Machine: DPR Status Workflow

```
                    ┌──────────────────────┐
                    │                      │
    ┌───────┐  create  ┌───────┐  submit  ┌───────────┐  approve  ┌──────────┐  lock  ┌────────┐
    │ (new) │────────→│ Draft │────────→│ Submitted │─────────→│ Approved │──────→│ Locked │
    └───────┘         └───┬───┘         └─────┬─────┘          └──────────┘       └───┬────┘
                          │                   │                                       │
                          │    ┌───────────────┘                                      │
                          │    │ revert (FR-004a)                                     │
                          │    │ No version created                                   │
                          │    ↓                                                      │
                          │  Draft ←── revert ──                                     │
                          │                                                           │
                          │                              unlock (AD-5) ───────────────┘
                          │                              Creates NEW version
                          │                              Original → is_superseded = true
                          │                              New DPR → Draft (version N+1)
                          ↓
                    Re-sync (FR-053e)
                    Only in Draft status
                    Updates snapshots, preserves actual data
```

---

## Carryover Computation (AD-4, FR-074)

```
Per scene entry:
  if status = 'Complete':     carryover = 0, gain = max(0, actual - planned)
  if status = 'Partial':      carryover = max(0, planned - actual), gain = 0
  if status = 'Not Shot':     carryover = planned, gain = 0
  if status = 'Added':        carryover = 0, gain = 0 (no baseline)
  if status = 'Pickup':       carryover = 0, gain = max(0, actual - planned)

Per DPR:
  carryover_pages = sum(per-scene carryover)
  page_gain = sum(per-scene gain)
```

---

## Analytics Aggregation Levels

| Level | Scope | Denominator | Planned Baseline |
|-------|-------|-------------|------------------|
| **Per Unit** | Single DPR | N/A | DPR scene entry snapshots |
| **Per Day (Combined)** | All unit DPRs for one shooting_day_id | N/A | Sum snapshots across units (not sum of variances) |
| **Per Schedule (Burndown)** | All canonical DPRs | Distinct shooting days with ≥1 included DPR | Unique scene planned pages from schedule |
| **Velocity (Main Unit)** | Main unit DPRs only | Distinct shooting days (main unit) | N/A |
| **Velocity (Combined)** | All unit DPRs | Distinct shooting days (all units) | N/A |
