# API Contract: Time Entries

**Blueprint**: `dpr_time_entry_bp` | **Auth**: `@require_auth`

---

## GET /api/dprs/:dprId/time-entries

List all time entries for a DPR.

**Response 200**:
```json
{
  "time_entries": [
    {
      "id": "uuid",
      "dpr_id": "uuid",
      "person_name": "John Smith",
      "person_id": "uuid",
      "entry_type": "cast",
      "character_name": "DETECTIVE",
      "call_time": "2026-02-23T06:00:00Z",
      "on_set_time": "2026-02-23T07:30:00Z",
      "wrap_time": "2026-02-23T19:00:00Z",
      "wrap_next_day": false,
      "first_meal_start": "2026-02-23T12:00:00Z",
      "first_meal_end": "2026-02-23T13:00:00Z",
      "second_meal_start": null,
      "second_meal_end": null,
      "travel_hours": 0,
      "calculated_hours": 12.0,
      "overtime_hours": 2.0,
      "meal_penalty": false,
      "forced_call": false,
      "is_shared_resource": false,
      "notes": null
    }
  ],
  "summary": {
    "cast_count": 5,
    "crew_count": 12,
    "total_cast_hours": 60.5,
    "total_crew_hours": 144.0,
    "meal_penalties": 1,
    "forced_calls": 0,
    "shared_resources": 1
  }
}
```

---

## POST /api/dprs/:dprId/time-entries

Create a time entry. Auto-calculates hours.

**Request**:
```json
{
  "person_name": "John Smith",
  "person_id": "uuid",
  "entry_type": "cast",
  "character_name": "DETECTIVE",
  "call_time": "2026-02-23T06:00:00Z",
  "on_set_time": "2026-02-23T07:30:00Z",
  "wrap_time": "2026-02-23T19:00:00Z",
  "first_meal_start": "2026-02-23T12:00:00Z",
  "first_meal_end": "2026-02-23T13:00:00Z",
  "is_shared_resource": false
}
```

**Response 201**: Created time entry with auto-calculated `calculated_hours`, `overtime_hours`, `meal_penalty`, `forced_call`

---

## PATCH /api/dpr-time-entries/:entryId

Update a time entry. Recalculates hours.

**Response 200**: Updated time entry with recalculated fields

---

## DELETE /api/dpr-time-entries/:entryId

Delete a time entry.

**Response 200**: `{"success": true}`

---

## POST /api/dprs/:dprId/time-entries/prepopulate

Pre-populate cast time entries from scheduled scene characters (FR-021).

**Response 200**:
```json
{
  "created": 5,
  "time_entries": [
    { "person_name": "", "character_name": "DETECTIVE", "entry_type": "cast", "call_time": null, "wrap_time": null }
  ]
}
```

Creates entries with character names filled and times blank. Skips characters that already have entries.

---

## Overnight Wrap Calculation (FR-021b)

When `wrap_next_day = true`:
- `calculated_hours = (wrap_time + 24h) - call_time - breaks`
- Example: call 18:00, wrap 03:00 → 9 hours (not negative)

## Shared Resource De-duplication (FR-021c)

When aggregating for global/payroll totals across units:
- Group by `person_id`
- If person has entries on multiple DPRs with `is_shared_resource = true`:
  - Use the longest span (max wrap - min call)
  - Or sum non-overlapping segments
- Unit-level analytics keep entries separate

## Payroll Disclaimer (FR-021a)

All time entry responses include:
```json
{ "disclaimer": "Time tracking is informational only, NOT payroll-authoritative. Does not store pay rates, union categories, or tier rules." }
```
