# API Contract: Department Logs

**Blueprint**: `dpr_dept_log_bp` | **Auth**: `@require_auth`

---

## GET /api/dprs/:dprId/department-logs

List all department logs for a DPR with submission tracker.

**Response 200**:
```json
{
  "department_logs": [
    {
      "id": "uuid",
      "dpr_id": "uuid",
      "department_type": "Camera",
      "submission_status": "Submitted",
      "submitted_by": "uuid",
      "submitted_at": "2026-02-23T18:30:00Z",
      "na_reason": null,
      "data": {
        "camera_rolls": [{ "camera": "A", "roll": "A001", "codec": "ARRI RAW", "resolution": "4K" }],
        "lenses_used": ["50mm", "85mm"],
        "checksum": "abc123",
        "offload_destination": "Shuttle Drive 1",
        "offload_completed_at": "2026-02-23T19:00:00Z",
        "verified_by": "DIT Name",
        "lto_backup_completed": true,
        "lto_verification_at": "2026-02-23T20:00:00Z"
      },
      "notes": null
    }
  ],
  "submission_tracker": {
    "total_required": 5,
    "submitted": 3,
    "pending": 1,
    "na": 1,
    "departments": {
      "Camera": "Submitted",
      "Sound": "Submitted",
      "Script Supervisor": "Submitted",
      "VFX": "N/A",
      "Locations": "Pending"
    }
  }
}
```

---

## PATCH /api/dpr-department-logs/:logId

Update department log data. Respects editability lifecycle (FR-015a).

**Request**:
```json
{
  "data": { "camera_rolls": [...], "lenses_used": [...] },
  "notes": "All footage verified"
}
```

**Response 200**: Updated department log  
**Error 403**: `{"error": "Department log is frozen (DPR status: Submitted)"}`

---

## POST /api/dpr-department-logs/:logId/submit

Mark a department log as Submitted.

**Response 200**: `{"department_log": {..., "submission_status": "Submitted", "submitted_at": "..."}}`  
**Error 403**: `{"error": "DPR must be in Draft status for department submissions"}`

---

## POST /api/dpr-department-logs/:logId/mark-na

Mark a department log as Not Applicable (FR-014a). AD/LP only.

**Request**:
```json
{ "reason": "VFX not on set today" }
```

**Response 200**: `{"department_log": {..., "submission_status": "N/A", "na_reason": "VFX not on set today"}}`  
**Error 400**: `{"error": "Reason is required when marking N/A"}`  
**Error 403**: `{"error": "Only AD or Line Producer can mark departments as N/A"}`
