# API Contract: Core DPR

**Blueprint**: `dpr_bp` | **Auth**: `@require_auth`

---

## POST /api/shooting-days/:dayId/dpr

Create a DPR for a shooting day + unit. Auto-populates scene entries with snapshots.

**Request**:
```json
{
  "unit_id": "uuid",
  "day_type": "Shoot"
}
```

**Response 201**:
```json
{
  "dpr": {
    "id": "uuid",
    "shooting_day_id": "uuid",
    "unit_id": "uuid",
    "schedule_id": "uuid",
    "version": 1,
    "parent_version_id": null,
    "is_superseded": false,
    "status": "Draft",
    "day_type": "Shoot",
    "include_in_velocity": true,
    "call_time": null,
    "first_shot_time": null,
    "lunch_start": null,
    "lunch_end": null,
    "camera_wrap_time": null,
    "company_wrap_time": null,
    "weather": {},
    "notes": null,
    "locked_at": null,
    "created_by": "uuid",
    "created_at": "2026-02-23T10:00:00Z",
    "scene_entries": [
      {
        "id": "uuid",
        "scene_id": "uuid",
        "status": "Not Shot",
        "actual_pages_eighths": 0,
        "snapshot_scene_number": "42",
        "snapshot_slugline": "INT. HOSPITAL - ROOM 304 - NIGHT",
        "snapshot_int_ext": "INT",
        "snapshot_location": "HOSPITAL - ROOM 304",
        "snapshot_day_night": "NIGHT",
        "snapshot_planned_pages_eighths": 19,
        "snapshot_schedule_order": 1,
        "snapshot_unit_assignment": "1st Unit"
      }
    ],
    "department_logs": [
      { "id": "uuid", "department_type": "Camera", "submission_status": "Pending" }
    ]
  }
}
```

**Error 409**: `{"error": "DPR already exists for this day and unit"}` — returns existing DPR ID  
**Error 400**: `{"error": "No schedule found for this shooting day"}`

---

## GET /api/shooting-days/:dayId/dpr?unit_id=:unitId

Get the canonical DPR for a day + unit combination.

**Response 200**: Full DPR object with all sub-entities (scene entries, dept logs, time entries, incidents, delays, signoffs, attachments)  
**Response 404**: `{"error": "No DPR found"}`

---

## GET /api/dprs/:dprId

Get a DPR by ID with all sub-entities.

**Response 200**: Full DPR object  
**Response 404**: `{"error": "DPR not found"}`

---

## PATCH /api/dprs/:dprId

Update DPR header fields. Only allowed when status = Draft.

**Request**:
```json
{
  "call_time": "2026-02-23T06:00:00Z",
  "company_wrap_time": "2026-02-23T19:00:00Z",
  "weather": { "condition": "Overcast", "temp_high": 22, "temp_low": 15 },
  "notes": "Rain delay in morning",
  "day_type": "Shoot",
  "include_in_velocity": true
}
```

**Response 200**: Updated DPR object  
**Error 403**: `{"error": "DPR is not in Draft status"}`

---

## GET /api/schedules/:scheduleId/dprs

List all DPRs for a schedule. Supports filtering.

**Query params**: `?unit_id=uuid&status=Draft&day_type=Shoot`

**Response 200**:
```json
{
  "dprs": [
    { "id": "uuid", "shooting_day_id": "uuid", "unit_id": "uuid", "version": 1, "status": "Draft", "day_type": "Shoot", "is_superseded": false }
  ]
}
```

---

## POST /api/dprs/:dprId/submit

Transition Draft → Submitted. Validates scene entries (FR-099).

**Response 200**: `{"dpr": {..., "status": "Submitted"}}`  
**Error 400**: `{"error": "Validation failed", "details": [{"scene_entry_id": "uuid", "issue": "Complete status with 0 pages"}]}`  
**Error 403**: `{"error": "DPR is not in Draft status"}`

---

## POST /api/dprs/:dprId/approve

Transition Submitted → Approved. Checks approval requirements (AD-9).

**Response 200**: `{"dpr": {..., "status": "Approved"}}`  
**Error 400**: `{"error": "Strict mode: pending departments", "pending": ["Sound", "VFX"]}`  
**Error 403**: `{"error": "DPR is not in Submitted status"}`

---

## POST /api/dprs/:dprId/lock

Transition Approved → Locked.

**Response 200**: `{"dpr": {..., "status": "Locked", "locked_at": "..."}}`

---

## POST /api/dprs/:dprId/revert

Transition Submitted → Draft (FR-004a). No version created.

**Response 200**: `{"dpr": {..., "status": "Draft"}}`  
**Error 403**: `{"error": "Only Submitted DPRs can be reverted"}`

---

## POST /api/dprs/:dprId/unlock

Unlock a Locked DPR — creates a new version (AD-5).

**Request**:
```json
{ "correction_reason": "Incorrect scene 42 page count" }
```

**Response 201**:
```json
{
  "new_dpr": { "id": "new-uuid", "version": 2, "status": "Draft", "parent_version_id": "old-uuid" },
  "superseded_dpr_id": "old-uuid"
}
```

**Error 400**: `{"error": "Correction reason is required"}`  
**Error 403**: `{"error": "Only Locked DPRs can be unlocked"}`

---

## POST /api/dprs/:dprId/resync

Re-sync Draft DPR with current schedule (FR-053e).

**Response 200**:
```json
{
  "dpr": { "...updated DPR..." },
  "changes": {
    "updated_snapshots": 3,
    "added_scenes": 1,
    "removed_scenes_transitioned_to_added": 0
  }
}
```

**Error 403**: `{"error": "Re-sync only available for Draft DPRs"}`

---

## GET /api/dprs/:dprId/pdf

Download DPR as PDF.

**Response 200**: `Content-Type: application/pdf`, `Content-Disposition: attachment; filename="DPR_Day4_v1.pdf"`

---

## GET /api/dprs/:dprId/print

Get printable HTML view.

**Response 200**: `Content-Type: text/html` — Full DPR rendered as printable HTML

---

## GET /api/dprs/:dprId/verify

Public endpoint (no auth, rate-limited). Returns canonical version status for QR code deep link (FR-031a).

**Response 200**:
```json
{
  "dpr_id": "uuid",
  "is_canonical": true,
  "version": 2,
  "status": "Locked",
  "locked_at": "2026-02-23T20:00:00Z",
  "superseded_by": null
}
```

If superseded:
```json
{
  "dpr_id": "uuid",
  "is_canonical": false,
  "version": 1,
  "superseded_by": "new-uuid",
  "canonical_version": 2
}
```
