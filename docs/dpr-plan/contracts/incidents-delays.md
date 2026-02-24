# API Contract: Incidents & Delays

**Blueprint**: `dpr_sub_entity_bp` | **Auth**: `@require_auth`

---

## POST /api/dprs/:dprId/incidents

Log an incident.

**Request**:
```json
{
  "type": "Injury",
  "severity": "Moderate",
  "description": "Crew member twisted ankle on uneven ground",
  "location": "Exterior parking lot set",
  "incident_time": "2026-02-23T14:30:00Z",
  "persons_involved": [{ "name": "Jane Doe", "role": "Grip", "injury_description": "Twisted right ankle" }],
  "witnesses": [{ "name": "Bob Smith", "role": "Gaffer" }],
  "action_taken": "First aid administered, sent to hospital",
  "follow_up_required": true,
  "follow_up_notes": "Awaiting medical clearance for return"
}
```

**Response 201**: Created incident  
**Error 400**: `{"error": "Serious/Critical severity requires follow_up_required = true"}` (FR-025)

---

## PATCH /api/dpr-incidents/:incidentId

Update an incident.

**Response 200**: Updated incident  
**Error 403**: `{"error": "DPR is not editable (status: Locked)"}`

---

## DELETE /api/dpr-incidents/:incidentId

Delete an incident.

**Response 200**: `{"success": true}`

---

## POST /api/dprs/:dprId/delays

Log a delay.

**Request**:
```json
{
  "type": "Weather",
  "duration_minutes": 45,
  "description": "Heavy rain, unable to shoot exterior",
  "scene_entry_id": "uuid"
}
```

**Response 201**: Created delay  

---

## GET /api/dprs/:dprId/incidents

List incidents for a DPR.

**Response 200**:
```json
{ "incidents": [...] }
```

---

## GET /api/dprs/:dprId/delays

List delays for a DPR with totals.

**Response 200**:
```json
{
  "delays": [...],
  "total_delay_minutes": 75,
  "breakdown": { "Weather": 45, "Technical": 30 }
}
```

---

## PATCH /api/dpr-delays/:delayId

Update a delay.

**Response 200**: Updated delay

---

## DELETE /api/dpr-delays/:delayId

Delete a delay.

**Response 200**: `{"success": true}`
