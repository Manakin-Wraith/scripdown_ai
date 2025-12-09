# Script Metadata Extraction Feature

## Overview
This feature automatically extracts cover page metadata from uploaded PDF scripts and stores it in the database for display across the application.

## Backend Implementation ✅

### 1. Metadata Extractor (`utils/metadata_extractor.py`)
- **Library**: Uses `pdfplumber` for robust PDF text extraction
- **Extracted Fields**:
  - Writer name
  - Email address
  - Phone number
  - Draft version (e.g., "First Draft", "Shooting Draft")
  - Draft date
  - Copyright information
  - WGA registration number
  - Additional credits ("Based on...", "Story by...")

### 2. Database Schema
**New columns added to `scripts` table**:
```sql
writer_name TEXT
writer_email TEXT
writer_phone TEXT
draft_version TEXT
draft_date TEXT
copyright_info TEXT
wga_registration TEXT
additional_credits TEXT
```

### 3. Integration
- **Upload Flow**: `services/script_service.py` → `process_script()` now:
  1. Saves the PDF file
  2. Parses script text
  3. **Extracts cover page metadata** (NEW)
  4. Saves everything to database

### 4. API Endpoint
**New endpoint**: `GET /scripts/<script_id>/metadata`
- Returns all metadata for a specific script
- Response format:
```json
{
  "script_id": 1,
  "script_name": "BIRD_V8.pdf",
  "writer_name": "John Smith",
  "writer_email": "john@example.com",
  "writer_phone": "(555) 123-4567",
  "draft_version": "First Draft",
  "draft_date": "March 15, 2024",
  "copyright_info": "© 2024 John Smith",
  "wga_registration": "WGA #123456",
  "additional_credits": "Based on a true story",
  "upload_date": "2025-11-21 14:30:00"
}
```

## Setup Instructions

### 1. Virtual Environment (IMPORTANT)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Database Migration
The migration has already been run. To verify:
```bash
sqlite3 db/script_breakdown.db "PRAGMA table_info(scripts);"
```

### 3. Start Server
```bash
source venv/bin/activate
python app.py
```

## Testing

### Test Metadata Extraction
1. Upload a new script via the frontend
2. Check the backend logs for: `Extracted metadata: {...}`
3. Query the API: `GET http://localhost:5000/scripts/1/metadata`

### Expected Behavior
- If metadata is found on the cover page, it will be extracted and saved
- If fields are missing, they will be `null` in the database
- The extraction is non-blocking - upload will succeed even if extraction fails

## Frontend Integration (TODO)

### Planned Components
1. **Script Hero Section** - Display at top of Scene Viewer
2. **Enhanced Script Library** - Show writer name in table
3. **Metadata Editor** - Allow manual editing of extracted data
4. **Contact Actions** - Quick copy/email buttons

### API Service Function (to be added)
```javascript
// frontend/src/services/apiService.js
export const getScriptMetadata = async (scriptId) => {
  const response = await fetch(`${API_URL}/scripts/${scriptId}/metadata`);
  return response.json();
};
```

## Notes
- The SQL linter warnings about `ALTER TABLE ADD COLUMN` are false positives - this is valid SQLite syntax
- `pdfplumber` is more robust than `PyPDF2` for text extraction
- Regex patterns can be refined based on real-world script formats
- Consider adding OCR fallback for scanned PDFs in the future
