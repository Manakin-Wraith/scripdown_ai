# API Contract: Approval Configuration

**Blueprint**: `dpr_config_bp` | **Auth**: `@require_auth`

---

## GET /api/schedules/:scheduleId/approval-config

Get the approval configuration for a production/schedule.

**Response 200**:
```json
{
  "config": {
    "id": "uuid",
    "schedule_id": "uuid",
    "approval_mode": "Strict",
    "required_departments": ["Camera", "Sound", "Script Supervisor", "Locations", "VFX"],
    "required_departments_by_day_type": {
      "Shoot": ["Camera", "Sound", "Script Supervisor", "Locations", "VFX"],
      "Company Move": ["Locations", "Transport"],
      "Travel": [],
      "Prep": ["Locations"],
      "Holiday": [],
      "Dark": [],
      "Strike": ["Locations"]
    },
    "velocity_projection_basis": "main_unit",
    "main_unit_id": "uuid",
    "meal_penalty_config": {
      "first_meal_threshold_hours": 6,
      "second_meal_threshold_hours": 6,
      "penalty_duration_minutes": 30
    },
    "forced_call_config": {
      "min_turnaround_hours": 10
    },
    "max_attachment_size_mb": 25
  }
}
```

---

## PATCH /api/schedules/:scheduleId/approval-config

Update approval configuration. Changes apply to future submissions only (FR-089).

**Request**:
```json
{
  "approval_mode": "Soft",
  "required_departments": ["Camera", "Sound"],
  "velocity_projection_basis": "combined",
  "meal_penalty_config": { "first_meal_threshold_hours": 5 },
  "max_attachment_size_mb": 50
}
```

**Response 200**: Updated config object

---

## Helper: Get Required Departments for Day Type

Used internally by approval logic. Not a separate endpoint — included in the approval check.

```
get_required_departments(schedule_id, day_type):
  1. Load config
  2. If day_type in required_departments_by_day_type: return override list
  3. Else: return default required_departments list
```
