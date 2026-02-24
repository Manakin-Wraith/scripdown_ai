# API Contract: Units

**Blueprint**: `dpr_unit_bp` | **Auth**: `@require_auth`

---

## POST /api/schedules/:scheduleId/units

Create a new unit for a schedule.

**Request**:
```json
{
  "name": "2nd Unit",
  "is_main_unit": false
}
```

**Response 201**:
```json
{
  "unit": {
    "id": "uuid",
    "schedule_id": "uuid",
    "name": "2nd Unit",
    "is_main_unit": false,
    "sort_order": 1,
    "created_at": "2026-02-23T10:00:00Z",
    "updated_at": "2026-02-23T10:00:00Z"
  }
}
```

**Error 400**: `{"error": "Name is required"}`  
**Error 409**: `{"error": "A main unit already exists for this schedule"}` (if `is_main_unit = true` and one already exists)

---

## GET /api/schedules/:scheduleId/units

List all units for a schedule.

**Response 200**:
```json
{
  "units": [
    { "id": "uuid", "name": "1st Unit", "is_main_unit": true, "sort_order": 0 },
    { "id": "uuid", "name": "2nd Unit", "is_main_unit": false, "sort_order": 1 }
  ]
}
```

---

## PATCH /api/units/:unitId

Update a unit.

**Request**:
```json
{ "name": "Splinter Unit", "sort_order": 2 }
```

**Response 200**: Updated unit object  
**Error 404**: `{"error": "Unit not found"}`

---

## DELETE /api/units/:unitId

Delete a unit. Fails if DPRs exist for this unit.

**Response 200**: `{"success": true}`  
**Error 409**: `{"error": "Cannot delete unit with existing DPRs"}`
