# API Contract: Scene Entries

**Blueprint**: `dpr_scene_entry_bp` | **Auth**: `@require_auth`

---

## GET /api/dprs/:dprId/scene-entries

List all scene entries for a DPR.

**Response 200**:
```json
{
  "scene_entries": [
    {
      "id": "uuid",
      "dpr_id": "uuid",
      "scene_id": "uuid",
      "status": "Complete",
      "actual_pages_eighths": 19,
      "setups": 3,
      "takes": 7,
      "circle_takes": ["3A", "5B"],
      "start_time": "2026-02-23T07:30:00Z",
      "end_time": "2026-02-23T09:15:00Z",
      "notes": null,
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
  "totals": {
    "planned_pages_eighths": 66,
    "actual_pages_eighths": 47,
    "variance_pages_eighths": -19,
    "total_setups": 8,
    "total_takes": 19,
    "scenes_complete": 3,
    "scenes_partial": 1,
    "scenes_not_shot": 1,
    "scenes_added": 1,
    "scenes_pickup": 0,
    "carryover_pages_eighths": 25,
    "page_gain_eighths": 0
  }
}
```

---

## PATCH /api/dpr-scene-entries/:entryId

Update a scene entry. Validates status/page consistency (FR-093–FR-098).

**Request**:
```json
{
  "status": "Partial",
  "actual_pages_eighths": 12,
  "setups": 1,
  "takes": 3,
  "notes": "Rain delay, will continue tomorrow"
}
```

**Response 200**: Updated scene entry + recalculated totals  
**Error 400**:
```json
{
  "error": "Validation failed",
  "details": [
    { "field": "actual_pages_eighths", "issue": "Partial status requires pages > 0 and < planned (19)" }
  ]
}
```
**Error 403**: `{"error": "DPR is not in Draft status"}`

---

## POST /api/dprs/:dprId/scene-entries

Add a scene manually (status = "Added"). For unscheduled scenes.

**Request**:
```json
{
  "scene_id": "uuid",
  "notes": "Picked up from Day 3"
}
```

If `scene_id` is provided, snapshots are populated from the scene record.  
If `scene_id` is null, manual snapshot fields are required:
```json
{
  "snapshot_scene_number": "12",
  "snapshot_slugline": "INT. ELEVATOR - DAY",
  "snapshot_int_ext": "INT",
  "snapshot_location": "ELEVATOR",
  "snapshot_day_night": "DAY"
}
```

**Response 201**: Created scene entry with status "Added"

---

## DELETE /api/dpr-scene-entries/:entryId

Remove a scene entry from a DPR. Only for manually added entries.

**Response 200**: `{"success": true}`  
**Error 403**: `{"error": "Cannot delete scheduled scene entries, mark as Not Shot instead"}`
