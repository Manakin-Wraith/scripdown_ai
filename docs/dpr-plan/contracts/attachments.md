# API Contract: Attachments

**Blueprint**: `dpr_sub_entity_bp` | **Auth**: `@require_auth`

---

## POST /api/dprs/:dprId/attachments

Upload a file attachment. Linked to DPR, scene entry, incident, or department log.

**Request**: `multipart/form-data`
- `file` — Binary file
- `parent_type` — One of: `dpr`, `scene_entry`, `incident`, `department_log`
- `parent_id` — UUID of the parent entity (optional if parent_type = dpr, uses dprId from URL)

**Response 201**:
```json
{
  "attachment": {
    "id": "uuid",
    "dpr_id": "uuid",
    "scene_entry_id": null,
    "incident_id": null,
    "department_log_id": null,
    "file_url": "https://twzfaizeyqwevmhjyicz.supabase.co/storage/v1/object/dpr-attachments/...",
    "file_type": "image/jpeg",
    "file_size_bytes": 245760,
    "uploader_id": "uuid",
    "upload_timestamp": "2026-02-23T18:00:00Z",
    "is_reference_copy": false,
    "source_attachment_id": null
  }
}
```

**Error 400**: `{"error": "File size exceeds maximum of 25MB"}`  
**Error 400**: `{"error": "At least one parent entity must be specified"}`

---

## GET /api/dpr-attachments/:attachmentId/url

Get a signed URL for downloading an attachment.

**Response 200**:
```json
{
  "signed_url": "https://...",
  "expires_at": "2026-02-23T19:00:00Z"
}
```

---

## DELETE /api/dpr-attachments/:attachmentId

Delete an attachment. Only the uploader or AD/LP can delete.

**Response 200**: `{"success": true}`  
**Error 403**: `{"error": "DPR is locked, attachments cannot be deleted"}`

---

## Version Clone Behavior (FR-085)

When a DPR is versioned (unlock → new version), attachments are NOT duplicated. Instead:
- New `dpr_attachments` rows are created with `is_reference_copy = true` and `source_attachment_id` pointing to the original
- `file_url` is copied (same file, no binary duplication)
- This prevents storage explosion across version chains
