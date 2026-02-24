# API Contract: Analytics

**Blueprint**: `dpr_analytics_bp` | **Auth**: `@require_auth`

---

## GET /api/schedules/:scheduleId/analytics

Cumulative production analytics across all canonical DPRs.

**Response 200**:
```json
{
  "analytics": {
    "total_shoot_days": 10,
    "completed_days": 8,
    "total_script_pages_eighths": 960,
    "cumulative_pages_shot_eighths": 420,
    "remaining_pages_eighths": 540,
    "main_unit_velocity": {
      "avg_pages_per_day_eighths": 48,
      "projected_remaining_days": 12,
      "projected_wrap_date": "2026-03-15"
    },
    "combined_velocity": {
      "avg_pages_per_day_eighths": 53,
      "projected_remaining_days": 11,
      "projected_wrap_date": "2026-03-14"
    },
    "projection_basis": "main_unit",
    "total_setups": 180,
    "total_takes": 450,
    "total_delay_minutes": 210,
    "total_carryover_eighths": 25,
    "total_page_gain_eighths": 8,
    "units": [
      { "id": "uuid", "name": "1st Unit", "is_main_unit": true, "dprs_count": 8, "pages_shot_eighths": 380 },
      { "id": "uuid", "name": "2nd Unit", "is_main_unit": false, "dprs_count": 3, "pages_shot_eighths": 40 }
    ]
  }
}
```

**Notes**:
- Uses only canonical (non-superseded) DPRs (FR-068)
- Velocity denominator is distinct shooting days, not DPR count (FR-073)
- Main unit velocity uses only designated main unit's DPRs (FR-073a)

---

## GET /api/schedules/:scheduleId/burndown

Burndown chart data: planned vs actual pages over time.

**Response 200**:
```json
{
  "burndown": {
    "planned_baseline_eighths": 960,
    "series": [
      {
        "shooting_day_id": "uuid",
        "day_number": 1,
        "shoot_date": "2026-02-10",
        "planned_cumulative_eighths": 66,
        "actual_cumulative_eighths": 72,
        "variance_eighths": 6
      },
      {
        "shooting_day_id": "uuid",
        "day_number": 2,
        "shoot_date": "2026-02-11",
        "planned_cumulative_eighths": 132,
        "actual_cumulative_eighths": 125,
        "variance_eighths": -7
      }
    ]
  }
}
```

**Notes**:
- Planned baseline from unique scene planned pages in schedule (FR-028a)
- Actual pages summed across all canonical DPRs per day

---

## GET /api/schedules/:scheduleId/velocity

Velocity metrics with main unit vs combined split.

**Response 200**:
```json
{
  "velocity": {
    "main_unit": {
      "unit_name": "1st Unit",
      "avg_pages_per_day_eighths": 48,
      "days_included": 8,
      "total_pages_eighths": 380
    },
    "combined": {
      "avg_pages_per_day_eighths": 53,
      "days_included": 8,
      "total_pages_eighths": 420
    },
    "projection_basis": "main_unit",
    "projected_wrap_date": "2026-03-15",
    "daily_trend": [
      { "day_number": 1, "pages_eighths": 72, "unit": "1st Unit" },
      { "day_number": 2, "pages_eighths": 53, "unit": "1st Unit" }
    ]
  }
}
```

---

## GET /api/schedules/:scheduleId/delays-summary

Delay breakdown by category across all shoot days.

**Response 200**:
```json
{
  "delays_summary": {
    "total_delay_minutes": 210,
    "by_category": {
      "Weather": 120,
      "Technical": 45,
      "Talent": 30,
      "Location": 15
    },
    "by_day": [
      { "day_number": 1, "total_minutes": 45, "primary_type": "Weather" },
      { "day_number": 3, "total_minutes": 90, "primary_type": "Weather" }
    ],
    "avg_delay_per_day_minutes": 26.25
  }
}
```
