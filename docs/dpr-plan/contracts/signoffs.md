# API Contract: Sign-Offs

**Blueprint**: `dpr_sub_entity_bp` | **Auth**: `@require_auth`

---

## POST /api/dprs/:dprId/signoffs

Add a sign-off to a DPR. Typically done on Approved or Locked DPRs.

**Request**:
```json
{
  "signer_name": "Jane Producer",
  "signer_role": "Producer"
}
```

**Response 201**:
```json
{
  "signoff": {
    "id": "uuid",
    "dpr_id": "uuid",
    "signer_name": "Jane Producer",
    "signer_role": "Producer",
    "signed_at": "2026-02-23T20:00:00Z"
  }
}
```

---

## GET /api/dprs/:dprId/signoffs

List all sign-offs for a DPR, including historical from previous versions.

**Response 200**:
```json
{
  "signoffs": [
    { "id": "uuid", "signer_name": "Jane Producer", "signer_role": "Producer", "signed_at": "..." }
  ],
  "historical_signoffs": [
    {
      "version": 1,
      "signoffs": [
        { "signer_name": "Jane Producer", "signer_role": "Producer", "signed_at": "..." }
      ],
      "correction_reason": "Incorrect scene 42 page count"
    }
  ]
}
```

---

## Version Clone Behavior

When a new DPR version is created:
- Current sign-offs are **cleared** on the new version
- Previous version's sign-offs are preserved in `dpr_audit_log.previous_version_signoffs` (FR-037a)
- Historical sign-offs accessible via the GET endpoint above
