# Quickstart: Daily Production Reporting (DPR)

**Phase 1 Output** | **Date**: 2026-02-23  
**Validates**: End-to-end DPR workflow from schedule to locked PDF

---

## Prerequisites

1. **Running backend** at `http://localhost:5000`
2. **Running frontend** at `http://localhost:5173`
3. **Supabase project** `twzfaizeyqwevmhjyicz` with migrations 001–041 applied
4. **Authenticated user** with at least one script uploaded and analyzed
5. **Shooting schedule** exists with at least one shooting day containing 3+ scenes
6. **Dependencies installed**:
   - Backend: `pip install qrcode[pil]`
   - Frontend: `npm install recharts`

---

## Scenario 1: Basic DPR Lifecycle (Single Unit)

### Step 1: Create a Unit
```bash
curl -X POST http://localhost:5000/api/schedules/{SCHEDULE_ID}/units \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"name": "1st Unit", "is_main_unit": true}'
```
**Expected**: 201 with unit object

### Step 2: Create a DPR
```bash
curl -X POST http://localhost:5000/api/shooting-days/{DAY_ID}/dpr \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"unit_id": "{UNIT_ID}", "day_type": "Shoot"}'
```
**Expected**: 201 with DPR containing:
- `status: "Draft"`
- `scene_entries[]` auto-populated from schedule with "Not Shot" status
- `department_logs[]` initialized as "Pending"
- All snapshot fields populated from current scene data

### Step 3: Update Scene Entries
```bash
# Mark scene as Complete
curl -X PATCH http://localhost:5000/api/dpr-scene-entries/{ENTRY_ID} \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"status": "Complete", "actual_pages_eighths": 19, "setups": 3, "takes": 7}'
```
**Expected**: 200 with updated entry, variance recalculated

### Step 4: Enter Time Sheet
```bash
curl -X POST http://localhost:5000/api/dprs/{DPR_ID}/time-entries \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "person_name": "John Smith",
    "entry_type": "cast",
    "character_name": "DETECTIVE",
    "call_time": "2026-02-23T06:00:00Z",
    "wrap_time": "2026-02-23T19:00:00Z",
    "first_meal_start": "2026-02-23T12:00:00Z",
    "first_meal_end": "2026-02-23T13:00:00Z"
  }'
```
**Expected**: 201 with `calculated_hours: 12.0`, auto-computed `meal_penalty` and `forced_call`

### Step 5: Submit → Approve → Lock
```bash
# Submit
curl -X POST http://localhost:5000/api/dprs/{DPR_ID}/submit \
  -H "Authorization: Bearer {TOKEN}"
# Expected: status → "Submitted"

# Approve
curl -X POST http://localhost:5000/api/dprs/{DPR_ID}/approve \
  -H "Authorization: Bearer {TOKEN}"
# Expected: status → "Approved"

# Lock
curl -X POST http://localhost:5000/api/dprs/{DPR_ID}/lock \
  -H "Authorization: Bearer {TOKEN}"
# Expected: status → "Locked", locked_at set
```

### Step 6: Download PDF
```bash
curl -X GET http://localhost:5000/api/dprs/{DPR_ID}/pdf \
  -H "Authorization: Bearer {TOKEN}" \
  -o DPR_Day1_v1.pdf
```
**Expected**: PDF file with all sections, QR code in footer, version number in header

---

## Scenario 2: Version Correction

### Step 7: Unlock (creates version 2)
```bash
curl -X POST http://localhost:5000/api/dprs/{DPR_ID}/unlock \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"correction_reason": "Incorrect scene 42 page count"}'
```
**Expected**: 
- New DPR (version 2) in Draft status
- Original DPR marked `is_superseded: true`
- Audit log entry with correction reason and previous signoffs

### Step 8: Verify Version Status (public)
```bash
curl http://localhost:5000/api/dprs/{ORIGINAL_DPR_ID}/verify
```
**Expected**: `is_canonical: false`, `superseded_by: {NEW_DPR_ID}`

---

## Scenario 3: Multi-Unit Same Day

### Step 9: Create 2nd Unit + DPR
```bash
# Create unit
curl -X POST http://localhost:5000/api/schedules/{SCHEDULE_ID}/units \
  -H "Authorization: Bearer {TOKEN}" \
  -d '{"name": "2nd Unit", "is_main_unit": false}'

# Create DPR for 2nd unit on same day
curl -X POST http://localhost:5000/api/shooting-days/{SAME_DAY_ID}/dpr \
  -H "Authorization: Bearer {TOKEN}" \
  -d '{"unit_id": "{UNIT_2_ID}", "day_type": "Shoot"}'
```

### Step 10: View Combined Analytics
```bash
curl http://localhost:5000/api/schedules/{SCHEDULE_ID}/analytics \
  -H "Authorization: Bearer {TOKEN}"
```
**Expected**: Analytics showing per-unit AND combined totals, distinct-day velocity denominator

---

## Scenario 4: Frontend User Flow

1. Navigate to `/scripts/{scriptId}/schedule/{scheduleId}`
2. Click **"File DPR"** on a shooting day card
3. Select unit (if multiple) → DPR Editor opens
4. Fill in call/wrap times, weather
5. Switch to **Scenes** tab → update scene statuses, pages, takes
6. Switch to **Department Logs** tab → submit camera log with media IDs
7. Switch to **Time Tracking** tab → click "Pre-populate Cast" → fill times
8. Switch to **Summary** tab → review variance, click **Submit**
9. LP reviews → **Approve** → **Lock**
10. Click **Export PDF** → download versioned PDF with QR code
11. Navigate to `/scripts/{scriptId}/schedule/{scheduleId}/dashboard` for analytics

---

## Validation Checklist

- [ ] DPR creation auto-populates scenes with correct snapshot data
- [ ] Scene entry validation prevents inconsistent data (Complete with 0 pages)
- [ ] Status workflow enforces forward-only transitions (except revert)
- [ ] Version chain preserves original, creates new Draft with cloned data
- [ ] Overnight wrap calculates correctly (call 18:00, wrap 03:00 = 9 hours)
- [ ] Multi-unit same-day shows combined analytics without double-counting
- [ ] Strict mode blocks submission with pending required departments
- [ ] N/A department satisfies Strict mode requirement
- [ ] PDF contains QR code linking to version verification endpoint
- [ ] Burndown chart uses unique scene planned baseline (not sum of DPR snapshots)
- [ ] Main Unit Velocity differs from Combined Velocity when splinter unit exists
- [ ] Carryover = Max(0, planned - actual), surplus tracked as Page Gain
- [ ] Low bandwidth mode disables image uploads but preserves data entry
